#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test impl.datacite
"""

import impl.datacite

test_records_one_creator = [
    # An item with 1 Creator, one title without lang code
    str(
        '<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier></creator></creators><titles><title>test title</title></titles><publisher>test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType></resource>'
    ),
    # An item with 1 Creator, one title with lang code
    str(
        '<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier></creator></creators><titles><title xml:lang="en-us">test title</title></titles><publisher>test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType></resource>'
    ),
    # An item with one creator which contains sub-property nameType;
    # 2 titles both with lang-code; only the 2nd one contains sub-property titleType
    # publisher contains lang-code
    str('<?xml version="1.0" encoding="UTF-8"?><resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xsi:schemaLocation="http://datacite.org/schema/kernel-4 https://schema.datacite.org/meta/kernel-4.4/metadata.xsd"><identifier identifierType="DOI">10.5072/example-full</identifier><creators><creator><creatorName nameType="Personal">test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="https://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier><affiliation>DataCite</affiliation></creator></creators><titles><title xml:lang="en-US">test title</title><title xml:lang="en-US" titleType="Subtitle">Demonstration of DataCite Properties.</title></titles><publisher xml:lang="en">test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="en-US" schemeURI="http://dewey.info/" subjectScheme="dewey" classificationCode="000">computer science</subject></subjects><language>en-US</language><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType></resource>'
        ),
    # An item with one creator which contains sub-property nameType;
    # 2 titles both with lang-code and sub-property titleType
    # publisher contains lang-code
    str('<?xml version="1.0" encoding="UTF-8"?><resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xsi:schemaLocation="http://datacite.org/schema/kernel-4 https://schema.datacite.org/meta/kernel-4.4/metadata.xsd"><identifier identifierType="DOI">10.5072/example-full</identifier><creators><creator><creatorName nameType="Personal">test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="https://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier><affiliation>DataCite</affiliation></creator></creators><titles><title xml:lang="en-US" titleType="TranslatedTitle">test title</title><title xml:lang="en-US" titleType="Subtitle">Demonstration of DataCite Properties.</title></titles><publisher xml:lang="en">test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="en-US" schemeURI="http://dewey.info/" subjectScheme="dewey" classificationCode="000">computer science</subject></subjects><language>en-US</language><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType></resource>'
        ),
]

test_records_2_creators = [
    # An item with 2 Creators, 2 titles without lang code
    str(
        '<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator><creator><creatorName>test creator 2</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator></creators><titles><title>test title</title><title>test title  2</title></titles><publisher>test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType><descriptions><description xml:lang="es-419" descriptionType="Abstract">testDescr</description><description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description><description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description></descriptions></resource>'
    ),
    # An item with 2 Creators, 2 titles with lang code
    str(
        '<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator><creator><creatorName>test creator 2</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator></creators><titles><title xml:lang="en-us">test title</title><title xml:lang="en-us">test title  2</title></titles><publisher>test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType><descriptions><description xml:lang="es-419" descriptionType="Abstract">testDescr</description><description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description><description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description></descriptions></resource>'
    ),
    # An item with 2 creators with sub-property nameType;
    # 2 titles with lang-code, the 2nd one contains property titleType
    # publisher contains lang-code
    str('<?xml version="1.0" encoding="UTF-8"?><resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xsi:schemaLocation="http://datacite.org/schema/kernel-4 https://schema.datacite.org/meta/kernel-4.4/metadata.xsd"><identifier identifierType="DOI">10.5072/example-full</identifier><creators><creator><creatorName nameType="Personal">test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="https://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier><affiliation>DataCite</affiliation></creator><creator><creatorName nameType="Organizational">California Digital Library</creatorName></creator></creators><titles><title xml:lang="en-US">test title</title><title xml:lang="en-US" titleType="Subtitle">Demonstration of DataCite Properties.</title></titles><publisher xml:lang="en">test publisher</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="en-US" schemeURI="http://dewey.info/" subjectScheme="dewey" classificationCode="000">computer science</subject></subjects><language>en-US</language><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType></resource>'
        ),
]

def test_briefDataciteRecord_1():
    for record in test_records_one_creator:
        brief_record = impl.datacite.briefDataciteRecord(record)
        assert brief_record['datacite.creator'] == 'test creator'
        assert brief_record['datacite.title'] == 'test title'
        assert brief_record['datacite.publisher'] == 'test publisher'
        assert brief_record['datacite.publicationyear'] == '1990'
        assert brief_record['datacite.resourcetype'] == 'Dataset'

def test_briefDataciteRecord_2():
    for record in test_records_2_creators:
        brief_record = impl.datacite.briefDataciteRecord(record)
        assert brief_record['datacite.creator'] == 'test creator et al.'
        assert brief_record['datacite.title'] == 'test title'
        assert brief_record['datacite.publisher'] == 'test publisher'
        assert brief_record['datacite.publicationyear'] == '1990'
        assert brief_record['datacite.resourcetype'] == 'Dataset'
