#!/usr/bin/env python2

"""N2T EggNog compatible minter for EZID

Terminology:

- Sping: Semi-opaque string. E.g., '77913/r7006t'
- Minter: Sping generator
- Shoulder: Static part of the identifier. E.g., '77913/r7'
- Expandable template: The form of the minted spings. E.g., '77913/r7{eedk}'
- Mask: Format specifier for the generated part of the sping. E.g., 'eedk'
- Type: Always 'rand', designating pseudo-random sequence of spings (as opposed to
  sequential)
- XDIG: Extended Digit. The alphabet used in the minted identifiers.

BerkeleyDB keys (EZID names / N2T names):

- combined_count / oacounter: Current combined value of all counters.
- max_combined_count / oatop: Highest possible combined value of all counters. When
  'combined_count' reaches this value, the minter template must be extended in order to
  keep using the minter.
- total_count / total: For EZID minters, total_count always matches max_combined_count.
- max_per_counter / percounter: Highest possible value for a single counter.
- base_count / basecount: Number of identifiers minted at the time the minter template
  was last extended. Will be zero if the minter template has yet to be extended. The
  total number of identifiers minted since the minter was created is always base_count +
  combined_count.
- active_counter_list / saclist: List of the currently active counters. Active counters
  have not reached their highest count values and can still be selected for minting.
- inactive_counter_list / siclist: List of the currently inactive (exhausted) counters.
  Inactive counters have reached their highest count values and are not available for
  use.
- template_str / template: Format specification for the final minted string. Contains a
  string that is identical for all identifiers minted by the given minter, and a
  description of the format for the generated, unique, part of the string and where to
  insert it. E.g., '99999/df4{eedk}'.
- mask_str / mask: Separate copy of the format description for the generated part of the
  identifier in the template. E.g., 'eedk'.
- atlast_str / atlast: Action to perform when template is exhausted. Always 'add3' for
  EZID, designating that template is expanded by repeating the first 3 characters. E.g.,
  'eedk' -> 'eedeedk' -> 'eedeedeedk'.
- counter_list: Counter top/value pairs, cN/top and cN/value, where N is a value from 0
  to max_combined_count / max_per_counter.
"""

from __future__ import absolute_import, division, print_function

import logging
import re

import nog.bdb
import nog.bdb_wrapper
import nog.id_ns

try:
    import bsddb
except ImportError:
    # noinspection PyUnresolvedReferences
    import bsddb3 as bsddb

import nog.exc

# fmt:off
XDIG_DICT = {
    # digits
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    # chars
    "b": 10, "c": 11, "d": 12, "f": 13, "g": 14, "h": 15, "j": 16, "k": 17, "m": 18,
    "n": 19, "p": 20, "q": 21, "r": 22, "s": 23, "t": 24, "v": 25, "w": 26, "x": 27,
    "z": 28,
}
# PROTO_SUPER_SHOULDER = config.get("shoulders.proto_super_shoulder")
PROTO_SUPER_SHOULDER ={
    "7286":"V1", # doi:10.7286/
    "4246":"P6", # doi:10.4246/
    "88435":"dc", # ark:/88435/
    "15697":"FK2", # doi:10.15697/
    "12345":"fk8", # ark:/12345/
}
# fmt:on
XDIG_STR = "0123456789bcdfghjkmnpqrstvwxz"
ALPHA_COUNT = len(XDIG_STR)
DIGIT_COUNT = 10

log = logging.getLogger(__name__)


def mint_id(shoulder_model, dry_run=False):
    """Mint a single identifier on an existing ARK or DOI shoulder / namespace.

    Args:
        shoulder_model (Django ORM model): Shoulder
        dry_run (bool):
            False (default): After successful minting, the BerkeleyDB database on disk,
                which stores the current state of the minter, is updated to the new
                state. This prevents the minter from returning the same ID the next
                time it is called.
            True: The minter database on disk is not updated, so the same IDs are
                returned again the next time the minter is called. This is useful for
                creating reproducible tests.

    Returns (str):
        Minted identifier containing the NAAN/Prefix, Shoulder and unique generated
        elements of the ID as specified in the minter template. E.g., '99999/fk42t0f'.
        The ID is agnostic to the type of the identifier (ARK, DOI). The caller
        completes the ID by appending the returned strings to the minter scheme.

    See Also:
        :func:`mint_ids`
    """
    for minted_ns in mint_ids(shoulder_model, 1, dry_run):
        return minted_ns


def mint_ids(shoulder_model, mint_count=1, dry_run=False):
    """Mint any number of identifiers on an existing ARK or DOI shoulder / namespace.

    If the minter is interrupted before completing the minting, the database is not
    updated. If the minter was minting a series of IDs when it was interrupted, the same
    series will be returned the next time the minter is called. This reflects the way
    N2T Nog operates.

    Args:
        mint_count (int, default=1): Set the number of IDs to mint. The caller must
            accept this number of IDs, in order for the generator to run to completion
            and for the minter state to be updated. be run to completion in order for
            the minter state to be updated.

    Yields (str):
        This is a generator that yields minted identifiers as described in :func:`mint_id`.

    See Also:
        :func:`mint_id`
    """
    bdb_path = nog.bdb.get_bdb_path_by_shoulder_model(shoulder_model)
    for minted_str in mint_by_bdb_path(bdb_path, mint_count, dry_run=dry_run):
        yield minted_str


def mint_by_bdb_path(bdb_path, mint_count=1, dry_run=False):
    """Like mint_ids(), but accepts the path to a BerkeleyDB nog.bdb minter file.

    Args:
        bdb_path: Path to a BerkeleyDB file.

    See Also:
        :func:`mint_ids`
    """
    with Minter(bdb_path, is_new=False, dry_run=dry_run) as minter:
        for minted_id in minter.mint(mint_count):
            yield minted_id


def create_minter_database(shoulder_ns, root_path=None, mask_str='eedk'):
    """Create a new BerkeleyDB file.

    Args:
        shoulder_ns: DOI or ARK shoulder namespace
        root_path:
        mask_str:

    Returns (path): Absolute path to the new nog.bdb file.
    """
    shoulder_ns = nog.id_ns.IdNamespace.from_str(shoulder_ns)
    bdb_path = nog.bdb.get_path(shoulder_ns, root_path, is_new=True)

    with Minter(bdb_path, is_new=True, dry_run=False) as minter:
        shoulder_val = shoulder_ns.shoulder
        if shoulder_ns.naan_prefix in PROTO_SUPER_SHOULDER and shoulder_val is None:
            shoulder_val = PROTO_SUPER_SHOULDER[shoulder_ns.naan_prefix]
        full_shoulder_str = '/'.join([shoulder_ns.naan_prefix, shoulder_val])
        minter.create(full_shoulder_str, mask_str)

    return bdb_path


class Minter(nog.bdb_wrapper.BdbWrapper):
    def __init__(self, bdb_path, is_new=False, dry_run=False):
        super(Minter, self).__init__(bdb_path, is_new, dry_run)
        self._dry_run = dry_run

    def __enter__(self):
        super(Minter, self).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(Minter, self).__exit__(exc_type, exc_val, exc_tb)

    def mint(self, id_count=1):
        """Generate one or more identifiers.

        Args:
            id_count (int): Number of identifiers to yield.
        """
        self._assert_ezid_compatible_minter()
        self._assert_valid_combined_count()
        self._assert_mask_matches_template()

        fmt_str = re.sub('{.*}', '{}', self.template_str)
        for _ in range(id_count):
            if self.combined_count == self.max_combined_count:
                self._extend_template()
            compounded_counter = self._next_state()
            self.combined_count += 1
            xdig_str = self._get_xdig_str(compounded_counter)
            if self.mask_str.endswith("k"):
                minted_id = fmt_str.format(xdig_str)
                xdig_str += self._get_check_char(minted_id)
            yield xdig_str

    # noinspection PyAttributeOutsideInit
    def create(self, shoulder_str, mask_str='eedk'):
        """Set minter to initial, unused state."""
        # self._bdb.clear()

        self.template_str = '{}{{}}'.format(shoulder_str, mask_str)
        self.mask_str = mask_str

        # m = re.match(r'(.*){{(.*)}}', template_str)
        # if not m:
        #     raise nog.exc.MinterError('Invalid template: {}'.format(template_str))

        self.base_count = 0
        self.combined_count = 0
        self.max_combined_count = 0
        self.total_count = 0
        self.atlast_str = 'add0'
        self._extend_template()
        self.atlast_str = 'add3'

        # Values not used by the EZID minter. We set them to increase the chance that
        # the minter can be read by N2T or other implementations.
        self._bdb.set('shoulder', shoulder_str)
        self._bdb.set('original_template', self.template_str)
        self._bdb.set('origmask', self.mask_str)

    def _next_state(self):
        """Step the minter to the next state.
        """
        rnd = _Drand48(self.combined_count)
        active_counter_idx = int(rnd.drand() * len(self.active_counter_list))
        # log.debug(
        #     'len(self.active_counter_list)={}'.format(len(self.active_counter_list))
        # )
        # log.debug('active_counter_idx={}'.format(active_counter_idx))
        counter_name = self.active_counter_list[active_counter_idx]
        counter_idx = int(counter_name[1:])
        max_int, value_int = self.counter_list[counter_idx]
        value_int += 1
        self.counter_list[counter_idx] = max_int, value_int
        n = value_int + counter_idx * self.max_per_counter
        if value_int >= max_int:
            self._deactivate_exhausted_counter(active_counter_idx)
        return n

    def _get_xdig_str(self, compounded_counter):
        """Convert compounded counter value to final sping as specified by the mask"""
        s = []
        for c in reversed(self.mask_str):
            if c == "k":
                continue
            elif c in ("e", "f"):
                divider = ALPHA_COUNT
            elif c == "d":
                divider = DIGIT_COUNT
            else:
                raise nog.exc.MinterError('Unsupported character in mask: {}'.format(c))
            compounded_counter, rem = divmod(compounded_counter, divider)
            x_char = XDIG_STR[rem]
            if c == "f" and x_char.isdigit():
                return ""
            s.append(x_char)
        return "".join(reversed(s))

    def _get_check_char(self, id_str):
        total_int = 0
        for i, c in enumerate(id_str):
            total_int += (i + 1) * XDIG_DICT.get(c, 0)
        return XDIG_STR[total_int % ALPHA_COUNT]

    def _extend_template(self):
        """Called when the minter has been used for minting the maximum number of IDs
        that is possible using the current mask (combined_count has reached
        max_combined_count). In order to use the minter again, the mask must be extended
        to accommodate longer IDs. This affects many of the values in the minter, which
        have to be recalculated based on the new mask.
        """
        self._assert_exhausted_minter()
        self._transfer_to_base_count()
        self._extend_mask()
        self._set_new_max_counts()
        self._reset_inactive_counter_list()
        self._generate_active_counter_list()

    def _generate_active_counter_list(self):
        """Generate new list of active counters and their top values after all counters
        have been exhausted.
        """
        # The total number of possible identifiers for a given mask is divided by this
        # number in order to get the max value per counter. All counters have the same
        # max value except for (usually) the last one, which receives the reminder.
        #
        # Comment about this value from N2T Nog:
        #
        # prime, a little more than 29*10. Using a prime under the theory (unverified)
        # that it may help even out distribution across the more significant digits of
        # generated strings.  In this way, for example, a method for mapping an string
        # to a pathname (eg, fk9tmb35x -> fk/9t/mb/35/x/, which could be a directory
        # holding all files related to the named object), would result in a reasonably
        # balanced filesystem tree -- no subdirectories too unevenly loaded. That's the
        # hope anyway.
        prime_factor = 293
        self.max_per_counter = int(self.total_count / prime_factor + 1)
        n = 0
        t = self.total_count
        self.counter_list = []
        self.active_counter_list = []
        while t > 0:
            self.counter_list.append(
                (self.max_per_counter if t >= self.max_per_counter else t, 0)
            )
            self.active_counter_list.append("c{}".format(n))
            t -= self.max_per_counter
            n += 1

    def _set_new_max_counts(self):
        """Calculate the number of identifiers that can be minted with the new mask.
        When this number is reached, the template must be extended again.
        """
        v = self._get_max_count()
        self.total_count = v
        self.max_combined_count = v

    def _extend_mask(self):
        """Extend the mask according to the "atlast" rule.
        """
        m = re.match(r"add(\d)$", self.atlast_str)
        add_int = int(m.group(1))
        self.mask_str = self.mask_str[:add_int] + self.mask_str
        # Insert the extended mask into the minter template.
        self.template_str = re.sub(
            r'{.*}', '{{{}}}'.format(self.mask_str), self.template_str
        )

    def _transfer_to_base_count(self):
        """Capture combined_count by adding it to the base_count, then reset it back to
        zero. The total number of identifiers minted since the minter was created is
        always base_count + combined_count.
        """
        self.base_count += self.combined_count
        self.combined_count = 0

    def _deactivate_exhausted_counter(self, counter_idx):
        """Deactivate an exhausted counter by moving it from the active to the inactive
        counter list.
        """
        counter_name = self.active_counter_list.pop(counter_idx)
        self.inactive_counter_list.append(counter_name)

    def _reset_inactive_counter_list(self):
        """Clear list of exhausted counters"""
        self.inactive_counter_list = []

    def _assert_exhausted_minter(self):
        """Check that we really have an exhausted minter.

        An exhausted minter must have no remaining counters in the active list. All the
        counters should be in the inactive list.
        """
        if not (self.combined_count == self.max_combined_count == self.total_count):
            raise nog.exc.MinterError(
                "Attempted to extend a minter that is not exhausted"
            )
        if self.active_counter_list:
            raise nog.exc.MinterError(
                "Attempted to extend a minter that still has active counters"
            )

    def _assert_ezid_compatible_minter(self):
        """Ensure that we can handle this minter. EZID uses minters that require only a
        subset of the features available on N2T. This code handles more than the
        EZID subset but not the full N2T set.
        """
        if not re.match(r"[def]+k?$", self.mask_str):
            raise nog.exc.MinterError(
                "Mask must use only 'd', 'e' and 'f' character types, "
                "ending with optional 'k' check character: {}".format(self.mask_str)
            )

        if not re.match(r"add(\d)$", self.atlast_str):
            raise nog.exc.MinterError(
                '"atlast" must be a string on form: add<digit>: {}'.format(
                    self.atlast_str
                )
            )

    def _assert_valid_combined_count(self):
        if self.combined_count > self.max_combined_count:
            raise nog.exc.MinterError(
                "Invalid counter total sum. total={} max={}".format(
                    self.combined_count, self.max_combined_count
                )
            )

    def _assert_mask_matches_template(self):
        if self.template_str.find('{{{}}}'.format(self.mask_str)) == -1:
            raise nog.exc.MinterError(
                'The mask that is embedded in the template key/value must match the '
                'mask that is stored separately in the mask key/value. '
                'template="{}" mask="{}"'.format(self.template_str, self.mask_str)
            )

    def _get_max_count(self):
        """Calculate the max number of spings that can be generated with a given mask.
        """
        max_count = 1
        for c in self.mask_str:
            if c == "k":
                continue
            elif c in ("e", "f"):
                max_count *= ALPHA_COUNT
            elif c == "d":
                max_count *= DIGIT_COUNT
            else:
                raise nog.exc.MinterError('Unsupported character in mask: {}'.format(c))
        return max_count


class _Drand48:
    """48-bit linear congruential PRNG, matching srand48() and drand48() in glibc.

    The sequence of pseudo-random numbers generated by this PRNG matches that of N2T Nog
    running on Perl, when Perl is built with GCC on Linux.
    """

    def __init__(self, seed):
        # log.debug("drand48 seed={}".format(seed))
        self.state = (seed << 16) + 0x330E

    def drand(self):
        self.state = (25214903917 * self.state + 11) & (2 ** 48 - 1)
        rnd = self.state / 2 ** 48
        # log.debug("drand48 value={}".format(rnd))
        return rnd