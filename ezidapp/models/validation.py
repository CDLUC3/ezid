#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Model validation functions
"""

import re
import time

import django.core.exceptions

import impl.util


def nonEmpty(value):
    # Validates that a string has at least one non-whitespace character.
    # (Sadly, Django's blank=False field option checks only that string
    # values are not empty; they can still be entirely whitespace.)
    if value.strip() == "":
        raise django.core.exceptions.ValidationError("This field cannot be blank.")


def anyIdentifier(identifier):
    # Validates that a string corresponds to the qualified, normalized
    # form of any known type of identifier.
    i = impl.util.validateIdentifier(identifier)
    if i is None:
        raise django.core.exceptions.ValidationError("Invalid identifier.")
    if i != identifier:
        raise django.core.exceptions.ValidationError(
            "Identifier is not in normalized form."
        )


def agentPid(pid):
    # Validates an agent (i.e., user or group) persistent identifier.
    # This function does not check that the identifier actually exists;
    # that's left to the calling code. In practice agent identifiers
    # will all fall under a particular shoulder, but for validation
    # purposes we require only that they be ARKs.
    if not pid.startswith("ark:/") or impl.util.validateArk(pid[5:]) != pid[5:]:
        raise django.core.exceptions.ValidationError(
            "Invalid agent persistent identifier: {}".format(pid)
        )


def agentPidOrEmpty(pid):
    # Validates an agent persistent identifier or empty string.
    if pid != "":
        agentPid(pid)


_crossrefDoiRE = re.compile("doi:10\\.[1-9]\\d{3,4}/[-\\w.;()/]+$")


def crossrefDoi(identifier):
    # Validates that a DOI identifier (which is assumed to have already
    # been validated and normalized as an ordinary identifier) meets the
    # additional syntactic restrictions imposed by Crossref.
    if not _crossrefDoiRE.match(identifier):
        raise django.core.exceptions.ValidationError(
            "Identifier does not satisfy Crossref syntax requirements."
        )


def shoulder(shoulder):
    # Validates a shoulder.
    if not impl.util.validateShoulder(shoulder):
        raise django.core.exceptions.ValidationError("Invalid shoulder.")


def datacenterSymbol(symbol):
    # Validates a DataCite datacenter symbol, per DataCite rules.
    if impl.util.validateDatacenter(symbol) is None:
        raise django.core.exceptions.ValidationError("Invalid datacenter symbol.")


_timespecs = [
    # fmt:off
    (4,        re.compile("(\\d{4})$"),                                                                 "%Y",                 1),
    (6,        re.compile("(\\d{6})$"),                                                                 "%Y%m",               2),
    (7,        re.compile("(\\d{4}-\\d\\d)$"),                                                            "%Y-%m",              2),
    (8,        re.compile("(\\d{8})$"),                                                                 "%Y%m%d",             3),
    (10,       re.compile("(\\d{4}-\\d\\d-\\d\\d)$"),                                                       "%Y-%m-%d",           3),
    (16,       re.compile("(\\d{4}-\\d\\d-\\d\\d \\d\\d:\\d\\d)$"),                                             "%Y-%m-%d %H:%M",     3),
    (16,       re.compile("(\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d)$"),                                             "%Y-%m-%dT%H:%M",     3),
    ((19, 26), re.compile("(\\d{4}-\\d\\d-\\d\\d \\d\\d:\\d\\d:\\d\\d)" + "( ?(Z|[-+][01]\\d:?(00|15|30|45)))?$"), "%Y-%m-%d %H:%M:%S",  3,),
    ((19, 25), re.compile("(\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d)" + "(Z|[-+][01]\\d:?(00|15|30|45))?$"),     "%Y-%m-%dT%H:%M:%S",  3,),
    (21,       re.compile("(\\d{4}-\\d\\d-\\d\\d \\d\\d:\\d\\d:\\d\\d)\\.\\d$"),                                    "%Y-%m-%d %H:%M:%S",  3),
    (21,       re.compile("(\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d)\\.\\d$"),                                    "%Y-%m-%dT%H:%M:%S",  3),
    ((8, 14),  re.compile("([a-zA-Z]+ \\d{4})$"),                                                       "%B %Y",              2),
    ((11, 18), re.compile("([a-zA-Z]+ (\\d| \\d|\\d\\d), \\d{4})$"),                                        "%B %d, %Y",          3),
    # fmt:on
]


def publicationDate(date):
    # Validates a publication date, which may be specified in a number
    # of formats (see above). Returns just the date portion of the
    # date, i.e., YYYY, YYYY-MM, or YYYY-MM-DD.
    for length, regexp, pattern, numComponents in _timespecs:
        if type(length) is tuple:
            if len(date) < length[0] or len(date) > length[1]:
                continue
        else:
            if len(date) != length:
                continue
        try:
            m = regexp.match(date)
            assert m and date[-1] != "\n"
            t = time.strptime(m.group(1), pattern)
            # Oddly, strptime works on dates before the Unix epoch, but not
            # strftime, so we avoid it.
            # return ("%04d", "%04d-%02d", "%04d-%02d-%02d")[numComponents - 1] % t[:numComponents]
            return ("{:04d}", "{:04d}-{:02d}", "{:04d}-{:02d}-{:02d}")[
                numComponents - 1
            ].format(*t[:numComponents])
        except Exception:
            pass
    raise django.core.exceptions.ValidationError(
        "Invalid publication date or unrecognized date format."
    )


# EZID borrows its resource type vocabulary from DataCite, and extends
# that vocabulary by allowing a "specific type" (in DataCite parlance)
# to follow a "general type" (or type proper) separated by a slash, as
# in "Image/Photograph". The following dictionary lists the allowable
# resource types (these are from version 4 of the DataCite Metadata
# Schema <http://schema.datacite.org/meta/kernel-4/>) and maps them to
# mnemonic codes for database storage purposes. (N.B.: the codes are
# used for ordering, so their order should match the order of the full
# terms.)

resourceTypes = {
    "Audiovisual": "A",
    "Book": "B",
    "BookChapter": "Bc",
    "Collection": "C",
    "ComputationalNotebook": "Cn",
    "ConferencePaper": "Cp",
    "ConferenceProceeding": "Cr",
    "DataPaper": "Dp",
    "Dataset": "D",
    "Dissertation": "Di",
    "Event": "E",
    "Image": "Im",
    "Instrument": "Ins",
    "InteractiveResource": "Int",
    "Journal": "J",
    "JournalArticle": "Ja",
    "Model": "M",
    "OutputManagementPlan": "O",
    "PeerReview": "Pr",
    "PhysicalObject": "P",
    "Preprint": "Pe",
    "Report": "R",
    "Service": "Se",
    "Software": "So",
    "Sound": "Su",
    "Standard": "Sta",
    "StudyRegistration": "Stu",
    "Text": "T",
    "Workflow": "W",
    "Other": "Z",
}


def resourceType(descriptor):
    # Validates a resource type that is possibly extended with a
    # specific type as described above. Returns a normalized
    # descriptor.
    descriptor = descriptor.strip()
    if "/" in descriptor:
        gt, st = descriptor.split("/", 1)
        gt = gt.strip()
        st = st.strip()
    else:
        gt = descriptor
        st = ""
    if gt not in resourceTypes:
        raise django.core.exceptions.ValidationError("Invalid resource type.")
    if st != "":
        return f"{gt}/{st}"
    else:
        return gt


def unicodeBmpOnly(s):
    # Validates that a Unicode string contains characters in the Basic
    # Multilingual Plane only (and also doesn't contain control
    # characters, byte order marks, etc.).
    if not impl.util.validateXmlSafeCharsetBmpOnly(s):
        raise django.core.exceptions.ValidationError(
            "Illegal or disallowed Unicode character."
        )
