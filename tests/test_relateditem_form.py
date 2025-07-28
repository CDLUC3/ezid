import pytest

from impl.form_objects import RelatedItemForm

@pytest.mark.parametrize(
"data, expected_valid, expected_error_keys",
[
    # valid empty form
    ({ }, True, [],),
    # valid minimal fields
    (
        { 
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
        },
        True,
        [],
    ),
    # missing title field
    (
        { 
            'relatedItemType': 'Book',
            'relationType': 'Cites',
        },
        False,
        ['titles-title-0-title'],
    ),
    # Test creatorName present, minimal valid
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'creators-creator-0-creatorName': 'creator name',
        },
        True,
        [],
    ),
    # Test creatorName with valid nameType
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'creators-creator-0-creatorName': 'creator name',
            'creators-creator-0-creatorName-nameType': 'Personal',
        },
        True,
        [],
    ),
    # Test CreatorName with invalid nameType
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'creators-creator-0-creatorName': 'creator name',
            'creators-creator-0-creatorName-nameType': 'Other',
        },
        False,
        ['creators-creator-0-creatorName-nameType'],
    ),
    # CreatorName is required when familyName present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'creators-creator-0-familyName': 'creator family name',
        },
        False,
        ['creators-creator-0-creatorName'],
    ),
    # CreatorName is required when givenName present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'creators-creator-0-givenName': 'creator given name',
        },
        False,
        ['creators-creator-0-creatorName'],
    ),
    # CreatorName is required when nameType present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'creators-creator-0-creatorName-nameType': 'Personal',
        },
        False,
        ['creators-creator-0-creatorName'],
    ),

    # Test contributor present, minimal valid
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorType': 'ContactPerson',
            'contributors-contributor-0-contributorName': 'contributor name',
        },
        True,
        [],
    ),
    # Test invalid contributor type
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorType': 'Person',
            'contributors-contributor-0-contributorName': 'contributor name',
        },
        False,
        ['contributors-contributor-0-contributorType'],
    ),
    # ContributorType is required when contributorName present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorName': 'contributor name',
        },
        False,
        ['contributors-contributor-0-contributorType'],
    ),
    # ContributorName is required when contributorType present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorType': 'Editor',
        },
        False,
        ['contributors-contributor-0-contributorName'],
    ),
    # Test contributor with valid nameType
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorType': 'ContactPerson',
            'contributors-contributor-0-contributorName': 'contributor name',
            'contributors-contributor-0-contributorName-nameType': 'Organizational',
        },
        True,
        [],
    ),
    # Test Contributor with invalid nameType
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorType': 'ContactPerson',
            'contributors-contributor-0-contributorName': 'contributor name',
            'contributors-contributor-0-contributorName-nameType': 'Other',
        },
        False,
        ['contributors-contributor-0-contributorName-nameType'],
    ),
    # contributorType and contributorName are required when familyName present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-familyName': 'contributor family name',
        },
        False,
        ['contributors-contributor-0-contributorType', 'contributors-contributor-0-contributorName'],
    ),
    # contributorType and contributorName are required when givenName present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-givenName': 'contributor given name',
        },
        False,
        ['contributors-contributor-0-contributorType', 'contributors-contributor-0-contributorName'],
    ),
    # contributorType and contributorName are required when nameType present
    (
        {
            'relatedItemType': 'Book',
            'relationType': 'Cites',
            'titles-title-0-title': 'Test title',
            'contributors-contributor-0-contributorName-nameType': 'Personal',
        },
        False,
        ['contributors-contributor-0-contributorType', 'contributors-contributor-0-contributorName'],
    ),
    ],
    ids=[
        "valid_empty_form",
        "valid_minimal",
        "invalid_missing_title",
        "valid_creatorName_minimal",
        "valid_creatorName_with_nameType",
        "invalid_creatorName_nameType",
        "invalid_missing_creatorName_with_familyName",
        "invalid_missing_creatorName_with_givenName",
        "invalid_missing_creatorName_with_nameType",
        "valid_contributor_minimal",
        "valid_contributorType",
        "invalid_missing_contributorType_with_contributorName",
        "invalid_missing_contributorName_with_contributorType",
        "valid_contributor_nameType",
        "invalid_contributor_nameType",
        "invalid_missing_contributorName_with_familyName",
        "invalid_missing_contributorName_with_givenName",
        "invalid_missing_contributorName_with_nameType",
    ]
)
def test_relatedItem_form(data, expected_valid, expected_error_keys):
    form = RelatedItemForm(data=data)
    is_valid = form.is_valid()

    assert is_valid == expected_valid

    for key in expected_error_keys:
        assert key in form.errors

    if expected_valid:
        assert form.errors == {}