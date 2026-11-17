from pathlib import Path

import impl.datacite_xml

# happy path: datacite example full xml -> form elements
def test_full_datacite_example_converts_to_form_elements():
    xml_path = Path(__file__).parent / "test_docs" / "datacite-example-full-v4.xml"
    form_data = impl.datacite_xml.dataciteXmlToFormElements(
        xml_path.read_text(encoding="utf-8")
    )

    assert form_data.resourceType["resourceType-resourceTypeGeneral"] == "Dataset"
    assert form_data.creators is not None
    assert form_data.relids is not None

    # Datacite 4.7 new fields and values are supported in the form elements
    # resource types: Poster, Presentation
    # relatedIdentifier types: RAiD, SWHID
    # relationTypeInformation requires relatedIdentifierType and relationType to be present

    # <relatedIdentifier relatedIdentifierType="RAiD" relationType="IsPartOf" resourceTypeGeneral="Project">https://raid.org/10.26259/5c43ca8f</relatedIdentifier>
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-16-relatedIdentifier"] == "https://raid.org/10.26259/5c43ca8f"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-16-relatedIdentifierType"] == "RAiD"

    # <relatedIdentifier relatedIdentifierType="SWHID" relationType="IsReferencedBy" resourceTypeGeneral="Software">swh:1:cnt:94a9ed024d3859793618152ea559a168bbcbb5e2</relatedIdentifier>
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-18-relatedIdentifier"] == "swh:1:cnt:94a9ed024d3859793618152ea559a168bbcbb5e2"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-18-relatedIdentifierType"] == "SWHID"

    # <relatedIdentifier relatedIdentifierType="DOI" relationType="IsCompiledBy" resourceTypeGeneral="Poster">10.1016/j.epsl.2011.11.037</relatedIdentifier>
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-23-relatedIdentifier"] == "10.1016/j.epsl.2011.11.037"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-23-resourceTypeGeneral"] == "Poster"

    # <relatedIdentifier relatedIdentifierType="DOI" relationType="Compiles" resourceTypeGeneral="Presentation">10.1016/j.epsl.2011.11.037</relatedIdentifier>
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-24-relatedIdentifier"] == "10.1016/j.epsl.2011.11.037"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-24-resourceTypeGeneral"] == "Presentation"

    # <relatedIdentifier relatedIdentifierType="DOI" relationType="Other" resourceTypeGeneral="Other" relationTypeInformation="Example relationTypeInformation">10.1016/j.epsl.2011.11.037</relatedIdentifier>
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-40-relatedIdentifier"] == "10.1016/j.epsl.2011.11.037"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-40-relatedIdentifierType"] == "DOI"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-40-resourceTypeGeneral"] == "Other"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-40-relationType"] == "Other"
    assert form_data.relids["relatedIdentifiers-relatedIdentifier-40-relationTypeInformation"] == "Example relationTypeInformation"
