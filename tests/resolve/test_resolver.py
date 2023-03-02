import logging
import pytest
import impl.resolver
import ezidapp.models.identifier

_L = logging.getLogger("test_resolver")


@pytest.mark.parametrize(
    "val,expected",
    [
        (
                "ark:/99999/fk412345/foo",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345/foo", scheme="ark", prefix="99999",
                                                suffix="fk412345/foo")),
        ),
        (
                "ark:/99999/fk412345/foo%efg%1abar",
                (
                        impl.resolver.IdentifierStruct(
                            original="ark:/99999/fk412345/foo%efg%1abar",scheme="ark", prefix="99999", suffix="fk412345/foo%EFg%1Abar"
                        )
                ),
        ),
        (
                "ark:/99999/fk-4-1-2-3-4-5/f-o-o",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk-4-1-2-3-4-5/f-o-o",scheme="ark", prefix="99999", suffix="fk412345/foo")),
        ),
        (
                "ark:/99999/fk412345//foo",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345//foo",scheme="ark", prefix="99999", suffix="fk412345/foo")),
        ),
        (
                "ark:/99999/fk412345///foo",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345///foo",scheme="ark", prefix="99999", suffix="fk412345/foo")),
        ),
        (
                "ark:/99999/fk412345..foo",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345..foo",scheme="ark", prefix="99999", suffix="fk412345.foo")),
        ),
        (
                "ark:/99999/fk412345.//foo",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345.//foo",scheme="ark", prefix="99999", suffix="fk412345.foo")),
        ),
        (
                "ark:/99999/fk412345.//foo?",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345.//foo?",scheme="ark", prefix="99999", suffix="fk412345.foo", inflection=True)),
        ),
        (
                "ark:/99999/fk412345.//foo??",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345.//foo??",scheme="ark", prefix="99999", suffix="fk412345.foo", inflection=True)),
        ),
        (
                "ark:/99999/fk412345.//foo?info",
                (impl.resolver.IdentifierStruct(original="ark:/99999/fk412345.//foo?info",scheme="ark", prefix="99999", suffix="fk412345.foo", inflection=True)),
        ),
        (
                "ark:/99999/",
                (impl.resolver.IdentifierStruct(original="ark:/99999/",scheme="ark", prefix="99999", suffix=None)),
        ),
        (
                "ark:/99999",
                (impl.resolver.IdentifierStruct(original="ark:/99999",scheme="ark", prefix="99999", suffix=None)),
        ),
        (
                "99999/fk412345/foo",
                (ValueError("99999/fk412345/foo has no scheme.")),
        ),
        (
                "ark:",
                (impl.resolver.IdentifierStruct(original="ark:",scheme="ark", prefix="")),
        ),
        (
                "ark:/",
                (impl.resolver.IdentifierStruct(original="ark:/",scheme="ark", prefix="")),
        ),
        (
                "doi:10.5065/D6HM56KS",
                (impl.resolver.IdentifierStruct(original="doi:10.5065/D6HM56KS",scheme="doi", prefix="10.5065", suffix="D6HM56KS")),
        ),
    ],
)
def test_parse(val, expected):
    if isinstance(expected, Exception):
        with pytest.raises(expected.__class__):
            impl.resolver.IdentifierParser.parse(val)
    else:
        res = impl.resolver.IdentifierParser.parse(val)
        assert isinstance(res, impl.resolver.IdentifierStruct)
        assert res.scheme == expected.scheme
        assert res.prefix == expected.prefix
        assert res.suffix == expected.suffix
        assert res.inflection == expected.inflection
        print(res.potential_matches())


@pytest.mark.parametrize(
    "val,expected",
    [
        ("ark:/88122/zqfw0190", ("ark:/88122/zqfw0190", "https://www.industrydocuments.ucsf.edu/docs/zqfw0190")),
        ("ark:/88122/zqfw0190_extra", ("ark:/88122/zqfw0190", "https://www.industrydocuments.ucsf.edu/docs/zqfw0190")),
        (
        "ark:88122/zq-fw-01-90_extra", ("ark:/88122/zqfw0190", "https://www.industrydocuments.ucsf.edu/docs/zqfw0190")),
        ("ark:/88122/", (ezidapp.models.identifier.Identifier.DoesNotExist())),
    ],
)
def test_resolve(val, expected):
    pid_info = impl.resolver.IdentifierParser.parse(val)
    print(str(pid_info))
    try:
        res = pid_info.find_record()
        print(res)
        assert res.identifier == expected[0]
        assert res.target == expected[1]
        return
    except Exception as e:
        assert isinstance(e, expected.__class__)
