import pytest
import re

import impl.form_objects as form_objects


@pytest.mark.parametrize("string,expected",[
    ('2000', '2000'),
    ('200', None),
    ('2', None),
    ('x', None),
    ('yyyy', None),
    ('', None),
    (':unac', ':unac'),
    (':unal', ':unal'),
    (':unap', ':unap'),
    (':unas', ':unas'),
    (':unav', ':unav'),
    (':unkn', ':unkn'),
    (':none', ':none'),
    (':tba', ':tba'),
    (':tba', ':tba'),
    (':tba', ':tba'),
])
def test_regex_year(string, expected):
    pattern = form_objects.REGEX_4DIGITYEAR
    match = re.search(pattern, string)
    if match:
        assert match.group() == expected
    
# REGEX_GEOPOINT = '-?(\d+(\.\d*)?|\.\d+)$'
@pytest.mark.parametrize("string,expected",[
    ('-123.456', '-123.456'),
    ('123.456', '123.456'),
    ('1.', '1.'),
    ('-1.', '-1.'),
    ('12.', '12.'),
    ('.1', '.1'),
    ('-.1', '-.1'),
    ('.456', '.456'),
    ('-.456', '-.456'),
    ('.', None),
    ('x', None),
    ('yyyy', None),
    ('', None),
])
def test_regex_geopoint(string, expected):
    pattern = form_objects.REGEX_GEOPOINT
    match = re.search(pattern, string)
    if match:
        assert match.group() == expected


@pytest.mark.parametrize("resource_type", ["Poster", "Presentation"])
def test_datacite_47_resource_types(resource_type):
    form = form_objects.ResourceTypeForm(
        {"resourceType-resourceTypeGeneral": resource_type}
    )

    assert form.is_valid(), form.errors


@pytest.mark.parametrize("identifier_type", ["RAiD", "SWHID"])
def test_datacite_47_related_identifier_types(identifier_type):
    form = form_objects.RelIdForm(
        {
            "relatedIdentifier": "https://example.org/related",
            "relatedIdentifierType": identifier_type,
            "relationType": "Cites",
            "relationTypeInformation": "Additional relationship detail",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["relationTypeInformation"] == (
        "Additional relationship detail"
    )


def test_related_identifier_relation_type_information_requires_relationship_fields():
    form = form_objects.RelIdForm(
        {"relationTypeInformation": "Additional relationship detail"}
    )

    assert not form.is_valid()
    assert "relatedIdentifierType" in form.errors
    assert "relationType" in form.errors




