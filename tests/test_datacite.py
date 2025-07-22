#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test impl.datacite
"""
from lxml import etree

import impl.datacite
import impl.datacite_xml

test_records_one_creator = [
    # An item with 1 Creator, one title without lang code
    str("""
        <resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
            xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
            <identifier identifierType="ARK"/>
            <creators>
                <creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                </creator>
            </creators>
            <titles><title>test title</title></titles>
            <publisher>test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject>
                <subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject>
            </subjects>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
        </resource>
        """
    ),
    # An item with 1 Creator, one title with lang code
    str("""
        <resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
            xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
            <identifier identifierType="ARK"/>
            <creators>
                <creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                </creator>
            </creators>
            <titles><title xml:lang="en-us">test title</title></titles>
            <publisher>test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject>
                <subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
        </resource>
        """
    ),
    # An item with one creator which contains sub-property nameType;
    # 2 titles both with lang-code; only the 2nd one contains sub-property titleType
    # publisher contains lang-code
    str("""<?xml version="1.0" encoding="UTF-8"?>
        <resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" 
                xsi:schemaLocation="http://datacite.org/schema/kernel-4 https://schema.datacite.org/meta/kernel-4.4/metadata.xsd">
            <identifier identifierType="DOI">10.5072/example-full</identifier>
            <creators>
                <creator><creatorName nameType="Personal">test creator</creatorName>
                    <givenName>Elizabeth</givenName>
                    <familyName>Miller</familyName>
                    <nameIdentifier schemeURI="https://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier>
                    <affiliation>DataCite</affiliation>
                </creator>
            </creators>
            <titles>
                <title xml:lang="en-US">test title</title>
                <title xml:lang="en-US" titleType="Subtitle">Demonstration of DataCite Properties.</title></titles>
            <publisher xml:lang="en">test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="en-US" schemeURI="http://dewey.info/" subjectScheme="dewey" classificationCode="000">computer science</subject>
            </subjects>
            <language>en-US</language>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
        </resource>
        """
        ),
    # An item with one creator which contains sub-property nameType;
    # 2 titles both with lang-code and sub-property titleType
    # publisher contains lang-code
    str("""<?xml version="1.0" encoding="UTF-8"?>
        <resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" 
                xsi:schemaLocation="http://datacite.org/schema/kernel-4 https://schema.datacite.org/meta/kernel-4.4/metadata.xsd">
            <identifier identifierType="DOI">10.5072/example-full</identifier>
            <creators>
                <creator><creatorName nameType="Personal">test creator</creatorName>
                    <givenName>Elizabeth</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="https://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier>
                    <affiliation>DataCite</affiliation>
                </creator>
            </creators>
            <titles>
                <title xml:lang="en-US" titleType="TranslatedTitle">test title</title>
                <title xml:lang="en-US" titleType="Subtitle">Demonstration of DataCite Properties.</title>
            </titles>
            <publisher xml:lang="en">test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="en-US" schemeURI="http://dewey.info/" subjectScheme="dewey" classificationCode="000">computer science</subject>
            </subjects>
            <language>en-US</language>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
        </resource>
        """
        ),
]

test_records_2_creators = [
    # An item with 2 Creators, 2 titles without lang code
    str("""
        <resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
            <identifier identifierType="ARK"/>
                <creators>
                    <creator><creatorName>test creator</creatorName>
                        <givenName>Elizabeth</givenName><familyName>Miller</familyName>
                        <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                        <affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator>
                    <creator><creatorName>test creator 2</creatorName>
                        <givenName>Elizabeth</givenName><familyName>Miller</familyName>
                        <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                        <nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier>
                        <nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier>
                        <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                        <nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier>
                        <nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier>
                        <affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation>
                    </creator>
                </creators>
            <titles><title>test title</title><title>test title  2</title></titles>
            <publisher>test publisher</publisher><publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject>
                <subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject>
            </subjects>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
            <descriptions>
                <description xml:lang="es-419" descriptionType="Abstract">testDescr</description>
                <description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description>
                <description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description>
            </descriptions>
        </resource>
        """
    ),
    # An item with 2 Creators, 2 titles with lang code
    str("""
        <resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
            <identifier identifierType="ARK"/>
            <creators>
                <creator><creatorName>test creator</creatorName><givenName>Elizabeth</givenName>
                    <familyName>Miller</familyName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                    <affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation>
                </creator>
                <creator><creatorName>test creator 2</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier>
                    <affiliation>DataCite1</affiliation>
                    <affiliation>DataCite2</affiliation>
                </creator>
            </creators>
            <titles>
                <title xml:lang="en-us">test title</title>
                <title xml:lang="en-us">test title  2</title>
            </titles>
            <publisher>test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject>
                <subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
            <descriptions>
                <description xml:lang="es-419" descriptionType="Abstract">testDescr</description>
                <description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description>
                <description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description>
            </descriptions>
        </resource>
        """
    ),
    # An item with 2 creators both contain sub-property nameType;
    # 2 titles both with lang-code; only the 2nd one contains property titleType
    # publisher contains lang-code
    str("""<?xml version="1.0" encoding="UTF-8"?>
        <resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" 
                xsi:schemaLocation="http://datacite.org/schema/kernel-4 https://schema.datacite.org/meta/kernel-4.4/metadata.xsd">
            <identifier identifierType="DOI">10.5072/example-full</identifier>
            <creators>
                <creator>
                    <creatorName nameType="Personal">test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="https://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier>
                    <affiliation>DataCite</affiliation>
                </creator>
                <creator>
                    <creatorName nameType="Organizational">California Digital Library</creatorName>
                </creator>
            </creators>
            <titles>
                <title xml:lang="en-US">test title</title>
                <title xml:lang="en-US" titleType="Subtitle">Demonstration of DataCite Properties.</title>
            </titles>
            <publisher xml:lang="en">test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="en-US" schemeURI="http://dewey.info/" subjectScheme="dewey" classificationCode="000">computer science</subject>
            </subjects>
            <language>en-US</language>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
        </resource>
        """
        ),
]

# record without namespace prefixes
test_xml_record  =  """<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:ns_1="http://www.w3.org/2001/XMLSchema-instance" ns_1:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
<identifier identifierType="ARK">99999/fk4zg85c0j</identifier>
<creators>
<creator>
<creatorName>University of California Office of the President</creatorName>
<affiliation>
University of California Office of the President
<nameIdentifier nameIdentifierScheme="ROR" nameIdentifierSchemeURI="https://ror.org">https://ror.org/00dmfq484</nameIdentifier>
</affiliation>
</creator>
</creators>
<titles>
<title>Mechanism of smoke-induced MUC5B gene expression</title>
</titles>
<publisher>UCOP</publisher>
<publicationYear>2023</publicationYear>
<resourceType resourceTypeGeneral="Other">Grant</resourceType>
<descriptions>
<description descriptionType="Abstract">Test description.</description>
</descriptions>
<contributors>
<contributor contributorType="ProjectLeader">
<contributorName>Wu Reen</contributorName>
<affiliation>
University of California, Davis
<nameIdentifier nameIdentifierScheme="ROR" nameIdentifierSchemeURI="https://ror.org">https://ror.org/05rrcem69</nameIdentifier>
</affiliation>
</contributor>
</contributors>
<dates>
<date dateType="Issued" dateInformation="n/a">7/1/01</date>
</dates>
<alternateIdentifiers>
<alternateIdentifier alternateIdentifierType="award-number">10RT-0262</alternateIdentifier>
</alternateIdentifiers>
<fundingReferences>
<fundingReference>
<funderName>University of California Office of the President</funderName>
<funderIdentifier funderIdentifierType="ROR">https://ror.org/00dmfq484</funderIdentifier>
</fundingReference>
</fundingReferences>
</resource>"""

# record with namespace ns0
test_xml_records_with_ns0  = str(
"""<ns0:resource xmlns:ns0="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
<ns0:identifier identifierType="ARK">99999/fk4zg85c0j</ns0:identifier>
<ns0:creators>
<ns0:creator>
<ns0:creatorName>University of California Office of the President</ns0:creatorName>
<ns0:affiliation>
University of California Office of the President
<ns0:nameIdentifier nameIdentifierScheme="ROR" nameIdentifierSchemeURI="https://ror.org">https://ror.org/00dmfq484</ns0:nameIdentifier>
</ns0:affiliation>
</ns0:creator>
</ns0:creators>
<ns0:titles>
<ns0:title>Mechanism of smoke-induced MUC5B gene expression</ns0:title>
</ns0:titles>
<ns0:publisher>UCOP</ns0:publisher>
<ns0:publicationYear>2023</ns0:publicationYear>
<ns0:resourceType resourceTypeGeneral="Other">Grant</ns0:resourceType>
<ns0:descriptions>
<ns0:description descriptionType="Abstract">Test description.</ns0:description>
</ns0:descriptions>
<ns0:contributors>
<ns0:contributor contributorType="ProjectLeader">
<ns0:contributorName>Wu Reen</ns0:contributorName>
<ns0:affiliation>
University of California, Davis
<ns0:nameIdentifier nameIdentifierScheme="ROR" nameIdentifierSchemeURI="https://ror.org">https://ror.org/05rrcem69</ns0:nameIdentifier>
</ns0:affiliation>
</ns0:contributor>
</ns0:contributors>
<ns0:dates>
<ns0:date dateType="Issued" dateInformation="n/a">7/1/01</ns0:date>
</ns0:dates>
<ns0:alternateIdentifiers>
<ns0:alternateIdentifier alternateIdentifierType="award-number">10RT-0262</ns0:alternateIdentifier>
</ns0:alternateIdentifiers>
<ns0:fundingReferences>
<ns0:fundingReference>
<ns0:funderName>University of California Office of the President</ns0:funderName>
<ns0:funderIdentifier funderIdentifierType="ROR">https://ror.org/00dmfq484</ns0:funderIdentifier>
</ns0:fundingReference>
</ns0:fundingReferences>
</ns0:resource>""")

# record with namespace ns1
test_xml_records_with_ns1 = str(
"""<ns1:resource xmlns:ns1="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
<ns1:identifier identifierType="ARK">99999/fk4zg85c0j</ns1:identifier>
<ns1:creators>
<ns1:creator>
<ns1:creatorName>University of California Office of the President</ns1:creatorName>
<ns1:affiliation>
University of California Office of the President
<ns1:nameIdentifier nameIdentifierScheme="ROR" nameIdentifierSchemeURI="https://ror.org">https://ror.org/00dmfq484</ns1:nameIdentifier>
</ns1:affiliation>
</ns1:creator>
</ns1:creators>
<ns1:titles>
<ns1:title>Mechanism of smoke-induced MUC5B gene expression</ns1:title>
</ns1:titles>
<ns1:publisher>UCOP</ns1:publisher>
<ns1:publicationYear>2023</ns1:publicationYear>
<ns1:resourceType resourceTypeGeneral="Other">Grant</ns1:resourceType>
<ns1:descriptions>
<ns1:description descriptionType="Abstract">Test description.</ns1:description>
</ns1:descriptions>
<ns1:contributors>
<ns1:contributor contributorType="ProjectLeader">
<ns1:contributorName>Wu Reen</ns1:contributorName>
<ns1:affiliation>
University of California, Davis
<ns1:nameIdentifier nameIdentifierScheme="ROR" nameIdentifierSchemeURI="https://ror.org">https://ror.org/05rrcem69</ns1:nameIdentifier>
</ns1:affiliation>
</ns1:contributor>
</ns1:contributors>
<ns1:dates>
<ns1:date dateType="Issued" dateInformation="n/a">7/1/01</ns1:date>
</ns1:dates>
<ns1:alternateIdentifiers>
<ns1:alternateIdentifier alternateIdentifierType="award-number">10RT-0262</ns1:alternateIdentifier>
</ns1:alternateIdentifiers>
<ns1:fundingReferences>
<ns1:fundingReference>
<ns1:funderName>University of California Office of the President</ns1:funderName>
<ns1:funderIdentifier funderIdentifierType="ROR">https://ror.org/00dmfq484</ns1:funderIdentifier>
</ns1:fundingReference>
</ns1:fundingReferences>
</ns1:resource>""")

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

def test_rm_xml_namespace_1():
    """XML records with namespace prefixes"""

    converted_rd_0 = impl.datacite.removeXMLNamespacePrefix(test_xml_records_with_ns0)
    converted_rd_1 = impl.datacite.removeXMLNamespacePrefix(test_xml_records_with_ns1)

    assert converted_rd_0 is not None
    assert converted_rd_0 != ''
    assert converted_rd_0 == converted_rd_1
    assert converted_rd_1 == test_xml_record

def  test_rm_xml_namespace_2():
    """XML records without namespace prefixes"""
    for record in test_records_one_creator:
        converted_rd = impl.datacite.removeXMLNamespacePrefix(record)
        brief_record = impl.datacite.briefDataciteRecord(converted_rd)
        assert brief_record['datacite.creator'] == 'test creator'
        assert brief_record['datacite.title'] == 'test title'
        assert brief_record['datacite.publisher'] == 'test publisher'
        assert brief_record['datacite.publicationyear'] == '1990'
        assert brief_record['datacite.resourcetype'] == 'Dataset'


# DataCite record with elements that can be created using the Advanced Create ID form.
# The record includes:
#  - Required data fields
#  - Optional data fields
#  - Two instnaces for each repeatable data fields
mockxml_datacite = """
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
    <identifier identifierType="ARK">ark:/99999/fk12345</identifier>
    <creators>
        <creator>
            <creatorName>Creator Name</creatorName>
            <givenName>CreatorGivenName</givenName>
            <familyName>CreatorFamilyName</familyName>
            <nameIdentifier nameIdentifierScheme="ORCID" schemeURI="https://orcid.org">https://orcid.org/0000-0001-5727-2427</nameIdentifier>
            <nameIdentifier nameIdentifierScheme="ROR" schemeURI="https://ror.org">https://ror.org/04wxnsj81</nameIdentifier>
            <affiliation affiliationIdentifier="https://ror.org/04wxnsj81" affiliationIdentifierScheme="ROR" schemeURI="https://ror.org">Example Affiliation for creator</affiliation>
        </creator>
        <creator>
            <creatorName>Creator Name 2</creatorName>
            <nameIdentifier nameIdentifierScheme="ORCID" schemeURI="https://orcid.org">https://orcid.org/0000-0001-5727-2222</nameIdentifier>
        </creator>
    </creators>
    <titles>
        <title xml:lang="en">test title, main</title>
        <title titleType="Subtitle" xml:lang="en">test title, subtitle</title>
    </titles>
    <publisher publisherIdentifier="https://ror.org/04z8jg394" publisherIdentifierScheme="ROR" schemeURI="https://ror.org/">test publisher</publisher>
    <publicationYear>1999</publicationYear>
    <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
    <subjects>
        <subject subjectScheme="Fields of Science and Technology (FOS)" schemeURI="http://www.oecd.org/science/inno" valueURI="http://www.oecd.org/science/inno/38235147.pd" xml:lang="en">FOS: Computer and information sciences</subject>
        <subject>Example Subject</subject>
    </subjects>
    <contributors>
        <contributor contributorType="ContactPerson">
            <contributorName>Contributor Name</contributorName>
            <givenName>ContributorGivenName</givenName>
            <familyName>ContributorFamilyName</familyName>
            <nameIdentifier nameIdentifierScheme="ORCID" schemeURI="https://orcid.org">https://orcid.org/0000-0001-5727-1234</nameIdentifier>
            <nameIdentifier nameIdentifierScheme="ORCID" schemeURI="https://orcid.org">https://orcid.org/0000-0001-5727-2427</nameIdentifier>
            <affiliation affiliationIdentifier="https://ror.org/04wxnsj81" affiliationIdentifierScheme="ROR" schemeURI="https://ror.org">ExampleAffiliation</affiliation>
        </contributor>
        <contributor contributorType="DataCollector">
            <contributorName>Contributor Name 2</contributorName>
        </contributor>
    </contributors>
    <dates>
        <date dateType="Created" dateInformation="ExampleDateInformation">2025-01-02</date>
        <date dateType="Accepted">2025-05-10</date>
    </dates>
    <language>en</language>
    <alternateIdentifiers>
        <alternateIdentifier alternateIdentifierType="Local accession number">12345</alternateIdentifier>
        <alternateIdentifier alternateIdentifierType="URL">https://example.com/567</alternateIdentifier>
    </alternateIdentifiers>
    <relatedIdentifiers>
        <relatedIdentifier relatedIdentifierType="URL" relationType="HasMetadata" relatedMetadataScheme="DDI-L" schemeURI="http://www.ddialliance.org/Specification/DDI-Lifecycle/3.1/XMLSchema/instance.xsd" schemeType="XSD">https://example.com/</relatedIdentifier>
        <relatedIdentifier relatedIdentifierType="DOI" relationType="IsCitedBy">10.21384/bar</relatedIdentifier>
    </relatedIdentifiers>
    <sizes>
        <size>1 MB</size>
        <size>90 pages</size>
    </sizes>
    <formats>
        <format>application/xml</format>
        <format>text/plain</format>
    </formats>
    <version>1</version>
    <rightsList>
        <rights rightsURI="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International</rights>
        <rights>rights 2</rights>
        </rightsList>
    <descriptions>
        <description descriptionType="Abstract" xml:lang="en">Example Abstract</description>
        <description descriptionType="Other" xml:lang="en">Description 2</description>
    </descriptions>
    <geoLocations>
        <geoLocation>
            <geoLocationPlace>Example Geo Location Place</geoLocationPlace>
            <geoLocationPoint>
                <pointLongitude>10</pointLongitude>
                <pointLatitude>20</pointLatitude>
            </geoLocationPoint>
            <geoLocationBox>
                <westBoundLongitude>8</westBoundLongitude>
                <eastBoundLongitude>12</eastBoundLongitude>
                <southBoundLatitude>18</southBoundLatitude>
                <northBoundLatitude>22</northBoundLatitude>
            </geoLocationBox>
        </geoLocation>
    </geoLocations>
    <fundingReferences>
        <fundingReference>
            <funderName>Example Funder</funderName>
            <funderIdentifier funderIdentifierType="Crossref Funder ID">https://doi.org/10.13039/501100000780</funderIdentifier>
            <awardNumber awardURI="https://example.com/example-award-uri">12345</awardNumber>
            <awardTitle>Example AwardTitle</awardTitle>
        </fundingReference>
        <fundingReference>
            <funderName>Example Funder 2</funderName>
        </fundingReference>
    </fundingReferences>
    <relatedItems>
        <relatedItem relatedItemType="Book" relationType="Cites">
            <relatedItemIdentifier relatedItemIdentifierType="ARK">ark:/99999/fk12345678</relatedItemIdentifier>
            <creators>
                <creator>
                    <creatorName nameType="Personal">related item creator name</creatorName>
                    <givenName>given name, related item creator</givenName>
                    <familyName>family name, related item creator</familyName>
                </creator>
            </creators>
            <titles>
                <title titleType="AlternativeTitle">related item title</title>
            </titles>
            <publicationYear>2022</publicationYear>
            <volume>1</volume>
            <issue>2</issue>
            <number numberType="Chapter">12</number>
            <firstPage>1</firstPage>
            <lastPage>20</lastPage>
            <publisher>related item publisher</publisher>
            <edition>related item edition</edition>
            <contributors>
                <contributor contributorType="DataManager">
                    <contributorName nameType="Personal">related item contributor name</contributorName>
                    <givenName>given name, related item contrib</givenName>
                    <familyName>family name, related item contrib</familyName>
                </contributor>
            </contributors>
        </relatedItem>
        <relatedItem relatedItemType="Collection" relationType="Collects">
            <relatedItemIdentifier relatedItemIdentifierType="URL">https://sample.com</relatedItemIdentifier>
            <creators>
                <creator>
                    <creatorName>Related item creator name 2</creatorName>
                </creator>
            </creators>
            <titles>
                <title titleType="TranslatedTitle">related item title 2</title>
            </titles>
        </relatedItem>
    </relatedItems>
</resource>"""


# DataCite record in form elements format
identifier = {
    'identifier-identifierType': 'ARK', 
    'identifier': 'ark:/99999/fk12345',
}
creators = {
    'creators-creator-0-affiliation': 'Example Affiliation for creator',
    'creators-creator-0-affiliation-affiliationIdentifier': 'https://ror.org/04wxnsj81',
    'creators-creator-0-affiliation-affiliationIdentifierScheme': 'ROR',
    'creators-creator-0-affiliation-schemeURI': 'https://ror.org',
    'creators-creator-0-creatorName': 'Creator Name',
    'creators-creator-0-familyName': 'CreatorFamilyName',
    'creators-creator-0-givenName': 'CreatorGivenName',
    'creators-creator-0-nameIdentifier_0-nameIdentifier': 'https://orcid.org/0000-0001-5727-2427',
    'creators-creator-0-nameIdentifier_0-nameIdentifierScheme': 'ORCID',
    'creators-creator-0-nameIdentifier_0-schemeURI': 'https://orcid.org',
    'creators-creator-0-nameIdentifier_1-nameIdentifier': 'https://ror.org/04wxnsj81',
    'creators-creator-0-nameIdentifier_1-nameIdentifierScheme': 'ROR',
    'creators-creator-0-nameIdentifier_1-schemeURI': 'https://ror.org',
    'creators-creator-1-creatorName': 'Creator Name 2',
    'creators-creator-1-nameIdentifier_0-nameIdentifier': 'https://orcid.org/0000-0001-5727-2222',
    'creators-creator-1-nameIdentifier_0-nameIdentifierScheme': 'ORCID',
    'creators-creator-1-nameIdentifier_0-schemeURI': 'https://orcid.org',
}
titles = {
    'titles-title-0-title': 'test title, main',
    'titles-title-0-{http://www.w3.org/XML/1998/namespace}lang': 'en',
    'titles-title-1-title': 'test title, subtitle',
    'titles-title-1-titleType': 'Subtitle',
    'titles-title-1-{http://www.w3.org/XML/1998/namespace}lang': 'en',
}
publisher = {
    'publisher': 'test publisher',
    'publisher-publisherIdentifier': "https://ror.org/04z8jg394",
    'publisher-publisherIdentifierScheme': 'ROR',
    'publisher-schemeURI': "https://ror.org/",
}
publicationYear = {
    'publicationYear': '1999',
}
resourceType = {
    'resourceType': 'Dataset',
    'resourceType-resourceTypeGeneral': 'Dataset',
}
subjects = {
    'subjects-subject-0-schemeURI': 'http://www.oecd.org/science/inno',
    'subjects-subject-0-subject': 'FOS: Computer and information sciences',
    'subjects-subject-0-subjectScheme': 'Fields of Science and Technology (FOS)',
    'subjects-subject-0-valueURI': 'http://www.oecd.org/science/inno/38235147.pd',
    'subjects-subject-0-{http://www.w3.org/XML/1998/namespace}lang': 'en',
    'subjects-subject-1-subject': 'Example Subject',
}
contributors = {
    'contributors-contributor-0-affiliation': 'ExampleAffiliation',
    'contributors-contributor-0-affiliation-affiliationIdentifier': 'https://ror.org/04wxnsj81',
    'contributors-contributor-0-affiliation-affiliationIdentifierScheme': 'ROR',
    'contributors-contributor-0-affiliation-schemeURI': 'https://ror.org',
    'contributors-contributor-0-contributorName': 'Contributor Name',
    'contributors-contributor-0-contributorType': 'ContactPerson',
    'contributors-contributor-0-familyName': 'ContributorFamilyName',
    'contributors-contributor-0-givenName': 'ContributorGivenName',
    'contributors-contributor-0-nameIdentifier_0-nameIdentifier': 'https://orcid.org/0000-0001-5727-1234',
    'contributors-contributor-0-nameIdentifier_0-nameIdentifierScheme': 'ORCID',
    'contributors-contributor-0-nameIdentifier_0-schemeURI': 'https://orcid.org',
    'contributors-contributor-0-nameIdentifier_1-nameIdentifier': 'https://orcid.org/0000-0001-5727-2427',
    'contributors-contributor-0-nameIdentifier_1-nameIdentifierScheme': 'ORCID',
    'contributors-contributor-0-nameIdentifier_1-schemeURI': 'https://orcid.org',
    'contributors-contributor-1-contributorName': 'Contributor Name 2',
    'contributors-contributor-1-contributorType': 'DataCollector',
}
dates = {
    'dates-date-0-date': '2025-01-02',
    'dates-date-0-dateType': 'Created',
    'dates-date-0-dateInformation': 'ExampleDateInformation',
    'dates-date-1-date': '2025-05-10',
    'dates-date-1-dateType': 'Accepted',
}
language = {
    'language': 'en',
    }
alternateIdentifiers = {
    'alternateIdentifiers-alternateIdentifier-0-alternateIdentifier': '12345',
    'alternateIdentifiers-alternateIdentifier-0-alternateIdentifierType': 'Local accession number',
    'alternateIdentifiers-alternateIdentifier-1-alternateIdentifier': 'https://example.com/567',
    'alternateIdentifiers-alternateIdentifier-1-alternateIdentifierType': 'URL',
}
relatedIdentifiers = {
    'relatedIdentifiers-relatedIdentifier-0-relatedIdentifier': 'https://example.com/',
    'relatedIdentifiers-relatedIdentifier-0-relatedIdentifierType': 'URL',
    'relatedIdentifiers-relatedIdentifier-0-relatedMetadataScheme': 'DDI-L',
    'relatedIdentifiers-relatedIdentifier-0-relationType': 'HasMetadata',
    'relatedIdentifiers-relatedIdentifier-0-schemeType': 'XSD',
    'relatedIdentifiers-relatedIdentifier-0-schemeURI': 'http://www.ddialliance.org/Specification/DDI-Lifecycle/3.1/XMLSchema/instance.xsd',
    'relatedIdentifiers-relatedIdentifier-1-relatedIdentifier': '10.21384/bar',
    'relatedIdentifiers-relatedIdentifier-1-relatedIdentifierType': 'DOI',
    'relatedIdentifiers-relatedIdentifier-1-relationType': 'IsCitedBy',
}
sizes = {
    'sizes-size-0-size': '1 MB',
    'sizes-size-1-size': '90 pages',
}
formats = {
    'formats-format-0-format': 'application/xml',
    'formats-format-1-format': 'text/plain',
}
version = {
    'version': '1',
}
rights = {
    'rightsList-rights-0-rights': 'Creative Commons Attribution 4.0 International',
    'rightsList-rights-0-rightsURI': 'https://creativecommons.org/licenses/by/4.0/',
    'rightsList-rights-1-rights': 'rights 2',
}
descriptions = {
    'descriptions-description-0-description': 'Example Abstract',
    'descriptions-description-0-descriptionType': 'Abstract',
    'descriptions-description-0-{http://www.w3.org/XML/1998/namespace}lang': 'en',
    'descriptions-description-1-description': 'Description 2',
    'descriptions-description-1-descriptionType': 'Other',
    'descriptions-description-1-{http://www.w3.org/XML/1998/namespace}lang': 'en',
}
geoLocations = {
    'geoLocations-geoLocation-0-geoLocationPlace': 'Example Geo Location Place',
    'geoLocations-geoLocation-0-geoLocationPoint-pointLongitude': '10',
    'geoLocations-geoLocation-0-geoLocationPoint-pointLatitude': '20',
    'geoLocations-geoLocation-0-geoLocationBox-westBoundLongitude': '8',
    'geoLocations-geoLocation-0-geoLocationBox-eastBoundLongitude': '12',
    'geoLocations-geoLocation-0-geoLocationBox-southBoundLatitude': '18',
    'geoLocations-geoLocation-0-geoLocationBox-northBoundLatitude': '22',
}
fundingReferences = {
    'fundingReferences-fundingReference-0-awardNumber': '12345',
    'fundingReferences-fundingReference-0-awardTitle': 'Example AwardTitle',
    'fundingReferences-fundingReference-0-awardNumber-awardURI': 'https://example.com/example-award-uri',
    'fundingReferences-fundingReference-0-funderIdentifier': 'https://doi.org/10.13039/501100000780',
    'fundingReferences-fundingReference-0-funderIdentifier-funderIdentifierType': 'Crossref Funder ID',
    'fundingReferences-fundingReference-0-funderName': 'Example Funder',
    'fundingReferences-fundingReference-1-funderName': 'Example Funder 2',
}
relatedItems = {
    'relatedItems-relatedItem-0-relatedItemType': 'Book',
    'relatedItems-relatedItem-0-relationType': 'Cites',
    'relatedItems-relatedItem-0-relatedItemIdentifier-relatedItemIdentifierType': 'ARK',
    'relatedItems-relatedItem-0-relatedItemIdentifier': 'ark:/99999/fk12345678',
    'relatedItems-relatedItem-0-creators-creator-0-creatorName': 'related item creator name',
    'relatedItems-relatedItem-0-creators-creator-0-creatorName-nameType': 'Personal',
    'relatedItems-relatedItem-0-creators-creator-0-familyName': 'family name, related item creator',
    'relatedItems-relatedItem-0-creators-creator-0-givenName': 'given name, related item creator',
    'relatedItems-relatedItem-0-titles-title-0-title': 'related item title',
    'relatedItems-relatedItem-0-titles-title-0-titleType': 'AlternativeTitle',
    'relatedItems-relatedItem-0-publicationYear': '2022',
    'relatedItems-relatedItem-0-volume': '1',
    'relatedItems-relatedItem-0-issue': '2',
    'relatedItems-relatedItem-0-number': '12',
    'relatedItems-relatedItem-0-number-numberType': 'Chapter',
    'relatedItems-relatedItem-0-firstPage': '1',
    'relatedItems-relatedItem-0-lastPage': '20',
    'relatedItems-relatedItem-0-publisher': 'related item publisher',
    'relatedItems-relatedItem-0-edition': 'related item edition',
    'relatedItems-relatedItem-0-contributors-contributor-0-contributorType': 'DataManager',
    'relatedItems-relatedItem-0-contributors-contributor-0-contributorName': 'related item contributor name',
    'relatedItems-relatedItem-0-contributors-contributor-0-contributorName-nameType': 'Personal',
    'relatedItems-relatedItem-0-contributors-contributor-0-familyName': 'family name, related item contrib',
    'relatedItems-relatedItem-0-contributors-contributor-0-givenName': 'given name, related item contrib',
    'relatedItems-relatedItem-1-relatedItemType': 'Collection',
    'relatedItems-relatedItem-1-relationType': 'Collects',
    'relatedItems-relatedItem-1-relatedItemIdentifier-relatedItemIdentifierType': 'URL',
    'relatedItems-relatedItem-1-relatedItemIdentifier': 'https://sample.com',
    'relatedItems-relatedItem-1-creators-creator-0-creatorName': 'Related item creator name 2',
    'relatedItems-relatedItem-1-titles-title-0-title': 'related item title 2',
    'relatedItems-relatedItem-1-titles-title-0-titleType': 'TranslatedTitle',
}

form_elements = creators | creators | titles | publisher | publicationYear | resourceType \
    | language | descriptions | subjects | contributors | dates \
    | alternateIdentifiers | relatedIdentifiers | sizes | formats \
    | version | rights | geoLocations | fundingReferences |relatedItems

form_collections = impl.datacite_xml.FormColl(
        nonRepeating=identifier | publisher | publicationYear | language | version,
        publisher=publisher,
        resourceType=resourceType,
        creators=creators,
        titles=titles,
        descrs=descriptions,
        subjects=subjects,
        contribs=contributors,
        dates=dates, 
        altids=alternateIdentifiers, 
        relids=relatedIdentifiers, 
        sizes=sizes, 
        formats=formats, 
        rights=rights, 
        geoLocations=geoLocations, 
        fundingReferences=fundingReferences, 
        relatedItems=relatedItems
        )


def normalize(xml_string):
    """Parse XML, remove blank text nodes, return canonical string."""
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_string.encode(), parser)
    return etree.tostring(root, method="c14n")

def test_formElementsToDataciteXml():
    returned_xml = impl.datacite_xml.formElementsToDataciteXml(form_elements, identifier='ark:/99999/fk12345')
    assert normalize(returned_xml) == normalize(mockxml_datacite)

def test_dataciteXmlToFormElements():
    returned_form_coll = impl.datacite_xml.dataciteXmlToFormElements(mockxml_datacite)
    assert returned_form_coll == form_collections

