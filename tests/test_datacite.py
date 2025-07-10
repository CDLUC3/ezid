#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test impl.datacite
"""
import collections

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

    
def temp_mockxml():
    return [
    # An item whose Creator has two nameIDs and two affiliations.
    # The item has multiple contributors, one with multiple nameIDs and affiliations.
    str("""
        <resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
            <identifier identifierType="ARK"/>
            <creators>
                <creator>
                    <creatorName>test creator</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier>
                    <affiliation>DataCite1</affiliation>
                    <affiliation>DataCite2</affiliation>
                </creator>
            </creators>
            <titles><title xml:lang="en-us">test title 1</title></titles>
            <publisher>test</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
                <subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject>
                <subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject>
            </subjects>
            <contributors>
                <contributor contributorType="ProjectLeader">
                    <contributorName>Starr, Joan</contributorName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-027X</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-1000</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-2222</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-3333</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-4444</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-5555</nameIdentifier>
                    <affiliation>California Digital Library</affiliation>
                    <affiliation>National SPAM Committee</affiliation>
                    <affiliation>NASCAR</affiliation>
                </contributor>
                <contributor contributorType="ProjectLeader"><contributorName>Rawls, Lou</contributorName>
                    <nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-027X</nameIdentifier>
                    <affiliation>Chicago</affiliation>
                </contributor>
            </contributors>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
            <descriptions>
                <description xml:lang="es-419" descriptionType="Abstract">testDescr</description>
                <description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description>
                <description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description>
            </descriptions>
        </resource>
               """),

    # An item with 2 Creators, both with three nameIDs
    str("""
        <resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-4/metadata.xsd">
            <identifier identifierType="ARK"/>
            <creators>
                <creator>
                    <creatorName>test creator 0</creatorName><givenName>Elizabeth 0</givenName><familyName>Miller</familyName>
                    <nameIdentifier schemeURI="http://orcid.org/0" nameIdentifierScheme="ORCID0">0000-0001-5000-0000</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/1" nameIdentifierScheme="ORCID1">0000-0001-5000-0001</nameIdentifier>
                    <nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier>
                    <affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation>
               </creator>
               <creator>
                <creatorName>test creator 1</creatorName><givenName>Elizabeth 1</givenName><familyName>Miller</familyName>
                <nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier>
                <nameIdentifier schemeURI="http://orcid.org/4" nameIdentifierScheme="ORCID4">0000-0001-5000-0004</nameIdentifier>
                <nameIdentifier schemeURI="http://orcid.org/5" nameIdentifierScheme="ORCID5">0000-0001-5000-0005</nameIdentifier>
                <affiliation>DataCite3</affiliation><affiliation>DataCite4</affiliation>
               </creator>
            </creators>
            <titles><title xml:lang="en-us">test title</title></titles>
            <publisher>test publisher</publisher>
            <publicationYear>1990</publicationYear>
            <subjects>
               <subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">test subject 0</subject>
               <subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test subject 1</subject>
            </subjects>
            <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
            <descriptions>
               <description xml:lang="es-419" descriptionType="Abstract">testDescr</description>
               <description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description>
               <description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description>
            </descriptions>
        </resource>
        """),
    ]


expected_form_collections = [
    impl.datacite_xml.FormColl(
        nonRepeating={'identifier-identifierType': 'ARK', 'publisher': 'test', 'publicationYear': '1990'},
        publisher={'publisher': 'test'},
        resourceType={'resourceType-resourceTypeGeneral': 'Dataset', 'resourceType': 'Dataset'},
        creators={
		    'creators-creator-0-creatorName': 'test creator',
            'creators-creator-0-givenName': 'Elizabeth',
            'creators-creator-0-familyName': 'Miller',
            'creators-creator-0-nameIdentifier_0-schemeURI': 'http://orcid.org/',
            'creators-creator-0-nameIdentifier_0-nameIdentifierScheme': 'ORCID',
            'creators-creator-0-nameIdentifier_0-nameIdentifier': '0000-0001-5000-0001',
            'creators-creator-0-nameIdentifier_1-schemeURI': 'http://orcid.org/2',
            'creators-creator-0-nameIdentifier_1-nameIdentifierScheme': 'ORCID2',
            'creators-creator-0-nameIdentifier_1-nameIdentifier': '0000-0001-5000-0002',
            'creators-creator-0-affiliation': 'DataCite1 ; DataCite2'},
        titles={'titles-title-0-{http://www.w3.org/XML/1998/namespace}lang': 'en-us', 'titles-title-0-title': 'test title 1'},
        descrs={
            'descriptions-description-0-{http://www.w3.org/XML/1998/namespace}lang': 'es-419',
            'descriptions-description-0-descriptionType': 'Abstract',
            'descriptions-description-0-description': 'testDescr',
            'descriptions-description-1-{http://www.w3.org/XML/1998/namespace}lang': 'zh-Hans',
            'descriptions-description-1-descriptionType': 'Other',
            'descriptions-description-1-description': 'testDescr2',
            'descriptions-description-2-{http://www.w3.org/XML/1998/namespace}lang': 'ast',
            'descriptions-description-2-descriptionType': 'SeriesInformation',
            'descriptions-description-2-description': 'testDescr3'},
        subjects={
            'subjects-subject-0-{http://www.w3.org/XML/1998/namespace}lang': 'ar-afb',
            'subjects-subject-0-schemeURI': 'testURI',
            'subjects-subject-0-subjectScheme': 'testScheme',
            'subjects-subject-0-subject': 'TESTTESTTESTTEST',
            'subjects-subject-1-{http://www.w3.org/XML/1998/namespace}lang': 'en',
            'subjects-subject-1-subjectScheme': 'testScheme2',
            'subjects-subject-1-schemeURI': 'testURI2',
            'subjects-subject-1-subject': 'test2'},
        contribs={
            'contributors-contributor-0-contributorType': 'ProjectLeader',
            'contributors-contributor-0-contributorName': 'Starr, Joan',
            'contributors-contributor-0-nameIdentifier_0-schemeURI': 'http://orcid.org/',
            'contributors-contributor-0-nameIdentifier_0-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-0-nameIdentifier_0-nameIdentifier': '0000-0002-7285-027X',
            'contributors-contributor-0-nameIdentifier_1-schemeURI': 'http://orcid.org/',
            'contributors-contributor-0-nameIdentifier_1-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-0-nameIdentifier_1-nameIdentifier': '0000-0002-7285-1000',
            'contributors-contributor-0-nameIdentifier_2-schemeURI': 'http://orcid.org/',
            'contributors-contributor-0-nameIdentifier_2-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-0-nameIdentifier_2-nameIdentifier': '0000-0002-7285-2222',
            'contributors-contributor-0-nameIdentifier_3-schemeURI': 'http://orcid.org/',
            'contributors-contributor-0-nameIdentifier_3-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-0-nameIdentifier_3-nameIdentifier': '0000-0002-7285-3333',
            'contributors-contributor-0-nameIdentifier_4-schemeURI': 'http://orcid.org/',
            'contributors-contributor-0-nameIdentifier_4-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-0-nameIdentifier_4-nameIdentifier': '0000-0002-7285-4444',
            'contributors-contributor-0-nameIdentifier_5-schemeURI': 'http://orcid.org/',
            'contributors-contributor-0-nameIdentifier_5-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-0-nameIdentifier_5-nameIdentifier': '0000-0002-7285-5555',
            'contributors-contributor-0-affiliation': 'California Digital Library ; National SPAM Committee ; NASCAR',
            'contributors-contributor-1-contributorType': 'ProjectLeader',
            'contributors-contributor-1-contributorName': 'Rawls, Lou',
            'contributors-contributor-1-nameIdentifier_0-schemeURI': 'http://orcid.org/',
            'contributors-contributor-1-nameIdentifier_0-nameIdentifierScheme': 'ORCID',
            'contributors-contributor-1-nameIdentifier_0-nameIdentifier': '0000-0002-7285-027X',
            'contributors-contributor-1-affiliation': 'Chicago'},
        dates=None, altids=None, relids=None, sizes=None, formats=None, rights=None, geoLocations=None, fundingReferences=None, relatedItems=None
            ),
    impl.datacite_xml.FormColl(
        nonRepeating={'identifier-identifierType': 'ARK', 'publisher': 'test publisher', 'publicationYear': '1990'},
        publisher={'publisher': 'test publisher'},
        resourceType={'resourceType-resourceTypeGeneral': 'Dataset', 'resourceType': 'Dataset'},
        creators={
            'creators-creator-0-creatorName': 'test creator 0',
            'creators-creator-0-givenName': 'Elizabeth 0',
            'creators-creator-0-familyName': 'Miller',
            'creators-creator-0-nameIdentifier_0-schemeURI': 'http://orcid.org/0',
            'creators-creator-0-nameIdentifier_0-nameIdentifierScheme': 'ORCID0',
            'creators-creator-0-nameIdentifier_0-nameIdentifier': '0000-0001-5000-0000',
            'creators-creator-0-nameIdentifier_1-schemeURI': 'http://orcid.org/1',
            'creators-creator-0-nameIdentifier_1-nameIdentifierScheme': 'ORCID1',
            'creators-creator-0-nameIdentifier_1-nameIdentifier': '0000-0001-5000-0001',
            'creators-creator-0-nameIdentifier_2-nameIdentifierScheme': 'ORCID2',
            'creators-creator-0-nameIdentifier_2-nameIdentifier': '0000-0001-5000-0002',
            'creators-creator-0-nameIdentifier_2-schemeURI': 'http://orcid.org/2',
            'creators-creator-0-affiliation': 'DataCite1 ; DataCite2',
            'creators-creator-1-creatorName': 'test creator 1',
            'creators-creator-1-givenName': 'Elizabeth 1',
            'creators-creator-1-familyName': 'Miller',
            'creators-creator-1-nameIdentifier_0-schemeURI': 'http://orcid.org/3',
            'creators-creator-1-nameIdentifier_0-nameIdentifierScheme': 'ORCID3',
            'creators-creator-1-nameIdentifier_0-nameIdentifier': '0000-0001-5000-0003',
            'creators-creator-1-nameIdentifier_1-schemeURI': 'http://orcid.org/4',
            'creators-creator-1-nameIdentifier_1-nameIdentifierScheme': 'ORCID4',
            'creators-creator-1-nameIdentifier_1-nameIdentifier': '0000-0001-5000-0004',
            'creators-creator-1-nameIdentifier_2-schemeURI': 'http://orcid.org/5',
            'creators-creator-1-nameIdentifier_2-nameIdentifierScheme': 'ORCID5',
            'creators-creator-1-nameIdentifier_2-nameIdentifier': '0000-0001-5000-0005',
            'creators-creator-1-affiliation': 'DataCite3 ; DataCite4'},
        titles={'titles-title-0-{http://www.w3.org/XML/1998/namespace}lang': 'en-us', 'titles-title-0-title': 'test title'},
        descrs={
            'descriptions-description-0-{http://www.w3.org/XML/1998/namespace}lang': 'es-419',
            'descriptions-description-0-descriptionType': 'Abstract',
            'descriptions-description-0-description': 'testDescr',
            'descriptions-description-1-{http://www.w3.org/XML/1998/namespace}lang': 'zh-Hans',
            'descriptions-description-1-descriptionType': 'Other',
            'descriptions-description-1-description': 'testDescr2',
            'descriptions-description-2-{http://www.w3.org/XML/1998/namespace}lang': 'ast',
            'descriptions-description-2-descriptionType': 'SeriesInformation',
            'descriptions-description-2-description': 'testDescr3'},
        subjects={
            'subjects-subject-0-{http://www.w3.org/XML/1998/namespace}lang': 'ar-afb',
            'subjects-subject-0-schemeURI': 'testURI',
            'subjects-subject-0-subjectScheme': 'testScheme',
            'subjects-subject-0-subject': 'test subject 0',
            'subjects-subject-1-{http://www.w3.org/XML/1998/namespace}lang': 'en',
            'subjects-subject-1-subjectScheme': 'testScheme2',
            'subjects-subject-1-schemeURI': 'testURI2',
            'subjects-subject-1-subject': 'test subject 1'},
        contribs=None,
        dates=None,
        altids=None,
        relids=None,
        sizes=None,
        formats=None,
        rights=None,
        geoLocations=None,
        fundingReferences=None,
        relatedItems=None),
]

def test_dataciteXmlToFormElements():
    
    for i, xml in enumerate(temp_mockxml()):
        form_coll = impl.datacite_xml.dataciteXmlToFormElements(xml)
        expected_form_coll = expected_form_collections[i]
        assert form_coll == expected_form_coll
