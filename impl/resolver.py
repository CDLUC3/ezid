import dataclasses
import logging
import re
import typing

import ezidapp.models.identifier
import ezidapp.models.shoulder
import impl.util

_L = logging.getLogger(__name__)


def convert_match_upper(match: re.match) -> str:
    return match.group().upper()


@dataclasses.dataclass
class IdentifierStruct:
    scheme: str
    prefix: str
    suffix: typing.Optional[str] = None
    inflection: bool = False

    def __str__(self):
        if self.suffix is not None:
            return f"{self.scheme}:{self.prefix}/{self.suffix}"
        return f"{self.scheme}:{self.prefix}/"

    @property
    def value(self):
        if self.suffix is not None:
            return f"{self.prefix}/{self.suffix}"
        return f"{self.prefix}/"

    def potential_matches(self) -> list[str]:
        res = []
        if self.suffix is None:
            return res
        sep = ":"
        for i in range(
            1, min(len(self.suffix), impl.util.maxIdentifierLength - len(self.prefix)) + 1
        ):
            res.append(f"{self.scheme}{sep}{self.prefix}/{self.suffix[:i]}")
        return res

    def find_record(self, fields:typing.Optional[list[str]]=None) -> ezidapp.models.identifier.Identifier:
        _matches = ezidapp.models.identifier.Identifier.objects.filter(
                identifier__in=self.potential_matches()
            )
        if fields is not None:
            _matches = _matches.only(*fields)
        result = list(_matches)
        if len(result) > 0:
            return max(result, key=lambda si: len(si.identifier))
        #try:
        #    res = ezidapp.models.shoulder.getLongestShoulderMatch(str(self))
        #    return res
        #except:
        #    pass
        raise ezidapp.models.identifier.Identifier.DoesNotExist()


class ArkIdentifierStruct(IdentifierStruct):
    def __init__(self, prefix: str, suffix: str = None, inflection: bool = False):
        super().__init__(scheme="ark", prefix=prefix, suffix=suffix, inflection=inflection)

    def __str__(self):
        if self.suffix is not None:
            return f"{self.scheme}:/{self.prefix}/{self.suffix}"
        return f"{self.scheme}:/{self.prefix}/"

    def potential_matches(self) -> list[str]:
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
    def __init__(self, prefix: str, suffix: str = None, inflection: bool = False):
        super().__init__(scheme="doi", prefix=prefix, suffix=suffix, inflection=inflection)


@dataclasses.dataclass
class IdentifierValueStruct:
    prefix: str
    suffix: typing.Optional[str]
    inflection: bool = False


class IdentifierValueParser:
    @classmethod
    def parse_value(cls, value: str, scheme: str) -> IdentifierStruct:
        return IdentifierStruct(scheme=scheme, prefix=value, suffix=None, inflection=False)


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
    def parse_value(cls, value: str, scheme: str = "ark") -> IdentifierStruct:
        inflection = False
        value = value.strip("/")
        value = value.replace("-", "")
        value = cls.PERCENT_MATCH.sub(convert_match_upper, value)
        value = cls.STRUCTURAL_MATCH_1.sub("/", value)
        value = cls.STRUCTURAL_MATCH_2.sub(".", value)
        value = cls.STRUCTURAL_MATCH_3.sub(".", value)
        value = cls.STRUCTURAL_MATCH_4.sub("/", value)
        value, n_matches = cls.INFLECTION_MATCH.subn("", value)
        if n_matches > 0:
            inflection = True
        parts = value.split("/", 1)
        prefix = parts[0]
        suffix = None
        prefix = prefix.lower()
        if len(parts) > 1:
            suffix = parts[1]
        return ArkIdentifierStruct(prefix=prefix, suffix=suffix, inflection=inflection)


class DoiIdentifierValueParser(IdentifierValueParser):
    @classmethod
    def parse_value(cls, value: str, scheme: str = "doi") -> IdentifierStruct:
        inflection = False
        parts = value.split("/", 1)
        prefix = parts[0]
        suffix = None
        if len(parts) > 1:
            suffix = parts[1]
        return DoiIdentifierStruct(prefix=prefix, suffix=suffix, inflection=inflection)


class IdentifierParser:

    value_parsers = {
        "__default__": IdentifierValueParser,
        "ark": ArkIdentifierValueParser,
        "doi": DoiIdentifierValueParser,
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
        return value_parser.parse_value(value)
