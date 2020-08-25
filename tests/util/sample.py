import base64
import bz2
import contextlib
import json
import logging
import os
import pprint
import re
import subprocess
import tempfile
import textwrap
import traceback

import django
import django.core
import django.core.management
import filelock

import utils.filesystem

MAX_LINE_WIDTH = 130
DEFAULT_DIFF_COLUMN_WIDTH = 100


# Options are set from the root conftest.
options = {}

log = logging.getLogger(__name__)


sample_review_lock = filelock.FileLock("/tmp/sample_review_lock")
# TODO. Create individual locks per filename
sample_path_lock = filelock.FileLock("/tmp/sample_path_lock")


def start_tidy():
    """Call at start of test run to tidy the samples directory.

    Pytest will run regular session scope fixtures in parallel with test
    collection, while this function must complete before collection starts. The
    best place to call it from appears to be ./conftest.pytest_sessionstart().
    """
    log.info("Moving files to tidy dir")
    with _get_tidy_path() as tidy_dir_path:
        with _get_sample_path() as sample_dir_path:
            utils.filesystem.create_missing_directories_for_dir(sample_dir_path)
            utils.filesystem.create_missing_directories_for_dir(tidy_dir_path)
            i = 0
            for i, item_name in enumerate(os.listdir(sample_dir_path)):
                sample_path = os.path.join(sample_dir_path, item_name)
                tidy_path = os.path.join(tidy_dir_path, item_name)
                if os.path.exists(tidy_path):
                    os.unlink(tidy_path)
                os.rename(sample_path, tidy_path)
            log.info("Moved {} files".format(i))


def assert_match(
    current_obj,
    file_post_str,
    sample_ext=".sample",
    no_wrap=False,
    # column_width=DEFAULT_DIFF_COLUMN_WIDTH,
):
    file_ext_str, current_str = obj_to_pretty_str(current_obj, no_wrap=no_wrap)
    sample_file_name = _format_file_name(file_post_str, sample_ext)
    log.info('Using sample file. sample_file_name="{}"'.format(sample_file_name))
    sample_path = _get_or_create_path(sample_file_name)

    with open(sample_path) as f:
        sample_str = f.read()

    if bytes(sample_str.strip()) == bytes(current_str.strip()):
        return

    mismatch_title_str = " -- ".join(
        ["<-- CURRENT", "Sample mismatch", file_post_str, sample_ext, "SAMPLE -->",]
    )

    with sample_review_lock:
        with utils.filesystem.temp_file_for_obj(current_str) as cur_path:
            print(cur_path.as_posix())
            print(sample_path)
            out_str = subprocess.check_output(
                (
                    'meld',
                    cur_path.as_posix(),
                    sample_path,
                    '--label',
                    mismatch_title_str,
                ),
                stderr=subprocess.STDOUT,
            )
            print('Meld output: {}'.format(out_str))


@contextlib.contextmanager
def get_path(filename):
    """When tidying, get_path_list() may move samples, which can cause concurrent calls
    to receive different paths for the same file. This is resolved by serializing calls
    to get_path_list(). Regular multiprocessing.Lock() does not seem to work under
    pytest-xdist.
    """
    # noinspection PyUnresolvedReferences
    with _get_sample_path(filename) as sample_path:
        if not os.path.isfile(sample_path):
            with _get_tidy_path(filename) as tidy_file_path:
                if os.path.isfile(tidy_file_path):
                    os.rename(tidy_file_path, sample_path)
        yield sample_path


@contextlib.contextmanager
def _get_sample_path(filename=None):
    """
    ``filename==``None``: Return path to sample directory.
    """
    p = os.path.join(utils.filesystem.abs_path("../test_docs/sample"), filename or "")
    with sample_path_lock:
        yield p


@contextlib.contextmanager
def _get_tidy_path(filename=None):
    """
    ``filename==``None``: Return path to sample tidy directory.

    """
    p = os.path.join(
        utils.filesystem.abs_path("./test_docs/sample_tidy"), filename or ""
    )
    with sample_path_lock:
        yield p


def dump(o, log_func=log.debug):
    map(log_func, obj_to_pretty_str(o, no_clobber=True)[1].splitlines())


def load(filename, mode_str="rb"):
    with open(_get_or_create_path(filename), mode_str) as f:
        return f.read()


def save_path(current_str, sample_path):
    assert isinstance(current_str, str)
    log.info('Saving sample file. filename="{}"'.format(os.path.split(sample_path)[1]))
    with open(sample_path, "wb") as f:
        f.write(current_str.encode("utf-8"))


def save_obj(current_obj, filename):
    current_str = obj_to_pretty_str(current_obj)[1]
    save(current_str, filename)


def save(current_str, filename):
    path = _get_or_create_path(filename)
    save_path(current_str, path)


def obj_to_pretty_str(o, no_clobber=False, no_wrap=False, column_width=None):
    """Serialize object to str.

    - Create a normalized string representation of the object that is suitable
      for using in a diff.
    - XML and PyXB is normalized here.
    - Serialization that breaks long lines into multiple lines is preferred,
      since multiple lines makes differences easier to spot in diffs.

    Args:
        column_width (int):
        :param o:

    """

    # noinspection PyUnreachableCode
    def serialize(o_):
        log.debug('Serializing object. type="{}"'.format(type(o_)))
        #
        # Special cases are ordered before general cases
        #
        # - Sample files are always valid UTF-8, so binary is forced to UTF-8 by
        # removing any sequences that are not valid UTF-8. This makes diffs more
        # readable in case they contain some UTF-8.
        # - In addition, a Base64 encoded version is included in order to be able to
        # verify byte by byte equivalence.
        # - It would be better to use errors='replace' here, but kdiff3 interprets
        # the Unicode replacement char <?> as invalid Unicode.
        # - Anything that looks like a memory address is clobbered later.
        if isinstance(o_, (bytes, bytearray)):
            return (
                ".txt",
                "BINARY-BYTES-AS-UTF-8:{}\nBINARY-BYTES-AS-BASE64:{}".format(
                    o_.decode("utf-8", errors="ignore"),
                    base64.standard_b64encode(o_).decode("ascii"),
                ),
            )
        # Any str
        if isinstance(o_, str):
            return ".txt", o_
        # Anything that can be converted to JSON (dict, list, set, of str, etc)
        try:
            return '.json', json.dumps(o_, indent=2, sort_keys=True)
        except Exception:
            pass
        # Everything else
        return ".txt", pprint.pformat(o_, indent=2)

    file_ext_str, obj_str = serialize(o)
    assert isinstance(obj_str, str)
    obj_str = obj_str.rstrip()

    # Replace '\n' with actual newlines since breaking text into multiple lines
    # when possible helps with diffs.
    obj_str = obj_str.replace("\\n", "\n")

    if not no_clobber:
        obj_str = _clobber_uncontrolled_volatiles(obj_str)

    if not no_wrap:
        obj_str = wrap_and_preserve_newlines(obj_str)

    if column_width:
        obj_str = textwrap.wrap(obj_str, column_width)

    return file_ext_str, obj_str


def wrap_and_preserve_newlines(s):
    return "\n".join(
        [
            "\n".join(
                textwrap.wrap(
                    line,
                    MAX_LINE_WIDTH,
                    break_long_words=False,
                    replace_whitespace=False,
                )
            )
            for line in s.splitlines()
        ]
    )


def get_test_module_name():
    for module_path, line_num, fn_name, line_str in traceback.extract_stack():
        module_name = os.path.splitext(os.path.split(module_path)[1])[0]
        if module_name.startswith("test_") and fn_name.startswith("test_"):
            return module_name


def _clobber_uncontrolled_volatiles(o_str):
    """Some volatile values in results are not controlled by freezing the time
    and/or PRNG seed. We replace those with a fixed string here.
    """
    # requests-toolbelt is using another prng for mmp docs
    o_str = re.sub(r"(?<=boundary=)[0-9a-fA-F]+", "[BOUNDARY]", o_str)
    o_str = re.sub(r"--[0-9a-f]{32}", "[BOUNDARY]", o_str)
    # entryId is based on a db sequence type
    o_str = re.sub(r"(?<=<entryId>)\d+", "[ENTRY-ID]", o_str)
    # TODO: This shouldn't be needed...
    o_str = re.sub(r"(?<=Content-Type:).*", "[CONTENT-TYPE]", o_str)
    # The uuid module uses MAC address, etc
    o_str = re.sub(r"(?<=test_fragment_volatile_)[0-9a-fA-F]+", "[UUID]", o_str)
    # ETA depends on how fast the computer is
    o_str = re.sub(r"\d{1,3}h\d{2}m\d{2}s", "[ETA-HMS]", o_str)
    # Disk space
    o_str = re.sub(r"[\s\d.]+GiB", "[DISK-SPACE]", o_str)
    # Memory address
    o_str = re.sub(r"0x[\da-fA-F]{8,}", "[MEMORY-ADDRESS]", o_str)
    # Temporary filename
    o_str = re.sub(r"tmp[\w\d]*\.", "[tmp-path].", o_str)
    # Command run timer
    o_str = re.sub(r'(?<=Parse succeeded )\(\d+\.\d+\)', '[run-timer]', o_str)

    return o_str


def _get_or_create_path(filename):
    """Get the path to a sample file and enable cleaning out unused sample
    files.

    See the test docs for usage.

    """
    with get_path(filename) as path:
        if not os.path.isfile(path):
            log.info("Write new sample file: {}".format(path))
            with open(path, "w") as f:
                f.write("<new sample file>\n")
        return path


def _format_file_name(file_post_str, file_ext_str):
    return "{}{}".format(
        utils.filesystem.get_safe_reversible_path_element(
            "_".join([get_test_module_name(), file_post_str])
        ),
        file_ext_str,
    )


@contextlib.contextmanager
def _tmp_file_pair(current_str, sample_str, file_post_str, file_ext_str):
    def format_suffix(n):
        return "{}__{}__{}".format(
            "__{}".format(file_post_str.upper()) if file_post_str else "",
            n.upper(),
            file_ext_str,
        )

    with tempfile.NamedTemporaryFile(suffix=format_suffix("CURRENT")) as current_f:
        with tempfile.NamedTemporaryFile(suffix=format_suffix("SAMPLE")) as sample_f:
            current_f.write(current_str.encode("utf-8"))
            sample_f.write(sample_str.encode("utf-8"))
            current_f.seek(0)
            sample_f.seek(0)
            yield current_f, sample_f


def save_compressed_db_fixture(filename):
    with get_path(filename) as fixture_file_path:
        log.info('Writing fixture sample. path="{}"'.format(fixture_file_path))
        with bz2.BZ2File(
            fixture_file_path, "w", buffering=1024, compresslevel=9
        ) as bz2_file:
            django.core.management.call_command("dumpdata", stdout=bz2_file)


class SampleException(Exception):
    pass
