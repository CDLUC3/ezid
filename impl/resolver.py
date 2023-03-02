import dataclasses
import logging
import re
import typing

import ezidapp.models.identifier
import ezidapp.models.shoulder
import impl.util

_L = logging.getLogger(__name__)

SCHEME_DOI = "doi"
SCHEME_ARK = "ark"

def convert_match_upper(match: re.match) -> str:
    return match.group().upper()


@dataclasses.dataclass
class IdentifierStruct:
    '''Represents a wild identifier structure.

    A "wild" identifier is one retrieved from an outside source, and
    so initially we only have the information parsed from the
    identifier string that was sent to us in a HTTP request.

    This class provides options for finding a matching identifier
    in our catalog.
    '''
    original: str
    '''The original, unparsed identifier string'''
    scheme: str
    '''The scheme of the identifier, always lower case. e.g. "ark:"'''
    prefix: str
    '''The portion between the scheme and the suffix'''
    suffix: typing.Optional[str] = None
    '''The portion after the prefix '''
    inflection: bool = False
    '''True if the identifier string included a pattern indicating that '''
    extra: str = ''
    '''Any characters in provided identifier that extend beyond resolved 
       identifier. Not set until find_record() is called.'''

    def __str__(self):
        if self.suffix is not None:
            return f"{self.scheme}:{self.prefix}/{self.suffix}{self.extra}"
        return f"{self.scheme}:{self.prefix}/"

    @property
    def value(self):
        if self.suffix is not None:
            return f"{self.prefix}/{self.suffix}"
        return f"{self.prefix}/"

    def align_with_found(self, found_record:str):
        '''
        Sets suffix and extra so that suffix matches the suffix portion of the
        found identifier, and extra contains any extra characters beyond the suffix.
        '''
        self_str = str(self)
        self.extra = self_str[len(found_record):]
        if len(self.extra) > 0:
            self.suffix = self.suffix[:-len(self.extra)]

    def potential_matches(self) -> typing.List[str]:
        res = []
        if self.suffix is None:
            return res
        sep = ":"
        for i in range(
            1, min(len(self.suffix), impl.util.maxIdentifierLength - len(self.prefix)) + 1
        ):
            res.append(f"{self.scheme}{sep}{self.prefix}/{self.suffix[:i]}")
        return res

    def find_record(self, fields:typing.Optional[typing.List[str]]=None) -> ezidapp.models.identifier.Identifier:
        _matches = ezidapp.models.identifier.Identifier.objects.filter(
                identifier__in=self.potential_matches()
            )
        if fields is not None:
            _matches = _matches.only(*fields)
        result = list(_matches)
        if len(result) > 0:
            matching_record =  max(result, key=lambda si: len(si.identifier))
            self.align_with_found(matching_record.identifier)
            return matching_record
        #try:
        #    res = ezidapp.models.shoulder.getLongestShoulderMatch(str(self))
        #    return res
        #except:
        #    pass
        raise ezidapp.models.identifier.Identifier.DoesNotExist()

    def find_shoulder(self) -> ezidapp.models.shoulder.Shoulder:
        result = ezidapp.models.shoulder.getLongestShoulderMatch(str(self))
        return result


class ArkIdentifierStruct(IdentifierStruct):
    def __init__(self, original:str, prefix: str, suffix: str = None, inflection: bool = False):
        super().__init__(original=original, scheme=SCHEME_ARK, prefix=prefix, suffix=suffix, inflection=inflection)

    def __str__(self):
        if self.suffix is not None:
            return f"{self.scheme}:/{self.prefix}/{self.suffix}"
        return f"{self.scheme}:/{self.prefix}/"

    def potential_matches(self) -> typing.List[str]:
        res = []
        if self.suffix is None:
            return res
        sep = ":/"
        for i in range(
            1, min(len(self.suffix), impl.util.maxIdentifierLength - len(self.prefix)) + 1
        ):
            res.append(f"{self.scheme}{sep}{self.prefix}/{self.suffix[:i]}")
        return res


class DoiIdentifierStruct(IdentifierStruct):
    def __init__(self, original:str, prefix: str, suffix: str = None, inflection: bool = False):
        super().__init__(original=original, scheme=SCHEME_DOI, prefix=prefix, suffix=suffix, inflection=inflection)


@dataclasses.dataclass
class IdentifierValueStruct:
    prefix: str
    suffix: typing.Optional[str]
    inflection: bool = False


class IdentifierValueParser:
    @classmethod
    def parse_value(cls, original:str, value: str, scheme: str) -> IdentifierStruct:
        return IdentifierStruct(original=original, scheme=scheme, prefix=value, suffix=None, inflection=False)


class ArkIdentifierValueParser(IdentifierValueParser):
    # two chars after percent character
    # https://www.ietf.org/id/draft-kunze-ark-36.html#name-normalization-and-lexical-e
    # step 5
    PERCENT_MATCH = re.compile("(%[a-zA-Z0-9]{2})")
    STRUCTURAL_MATCH_1 = re.compile("//+")
    STRUCTURAL_MATCH_2 = re.compile("[.][.]+")
    STRUCTURAL_MATCH_3 = re.compile("[.]/")
    STRUCTURAL_MATCH_4 = re.compile("/[.]")
    INFLECTION_MATCH = re.compile("\?info|\?{2}|\?$")

    @classmethod
    def parse_value(cls, original:str, value: str, scheme: str = SCHEME_ARK) -> IdentifierStruct:
        inflection = False
        # Remove leading and trailing "/"
        value = value.strip("/")
        # Remove hyphens
        value = value.replace("-", "")
        # Convert percent encoded to upper case
        value = cls.PERCENT_MATCH.sub(convert_match_upper, value)
        # Deal with path hacks
        value = cls.STRUCTURAL_MATCH_1.sub("/", value)
        value = cls.STRUCTURAL_MATCH_2.sub(".", value)
        value = cls.STRUCTURAL_MATCH_3.sub(".", value)
        value = cls.STRUCTURAL_MATCH_4.sub("/", value)
        # Asking for identifier metadata?
        value, n_matches = cls.INFLECTION_MATCH.subn("", value)
        if n_matches > 0:
            inflection = True
        parts = value.split("/", 1)
        prefix = parts[0]
        suffix = None
        prefix = prefix.lower()
        if len(parts) > 1:
            suffix = parts[1]
        return ArkIdentifierStruct(original=original, prefix=prefix, suffix=suffix, inflection=inflection)


class DoiIdentifierValueParser(IdentifierValueParser):
    INFLECTION_MATCH = re.compile("\?info|\?{2}|\?$")

    @classmethod
    def parse_value(cls, original:str, value: str, scheme: str = SCHEME_DOI) -> IdentifierStruct:
        inflection = False
        value, n_matches = cls.INFLECTION_MATCH.subn("", value)
        if n_matches > 0:
            inflection = True
        parts = value.split("/", 1)
        prefix = parts[0]
        suffix = None
        if len(parts) > 1:
            suffix = parts[1]
        return DoiIdentifierStruct(original=original, prefix=prefix, suffix=suffix, inflection=inflection)


class IdentifierParser:

    value_parsers = {
        "__default__": IdentifierValueParser,
        SCHEME_ARK: ArkIdentifierValueParser,
        SCHEME_DOI: DoiIdentifierValueParser,
    }

    @classmethod
    def parse(cls, identifier: str) -> IdentifierStruct:
        identifier = identifier.strip()
        try:
            scheme, value = identifier.split(":", 1)
        except ValueError:
            raise ValueError(f"{identifier} has no scheme.")
        scheme = scheme.lower()
        value = value.strip()
        value_parser = IdentifierParser.value_parsers.get(
            scheme, IdentifierParser.value_parsers.get("__default__")
        )
        return value_parser.parse_value(identifier, value)
