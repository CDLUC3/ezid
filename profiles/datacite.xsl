<?xml version="1.0"?>

<!-- ==========================================================================

Converts a DataCite Metadata Scheme <http://schema.datacite.org/>
record to an XHTML table.

In a slight extension, this transform allows the record identifier to
be other than a DOI.

The XPath expressions are written the convoluted way they are to allow
this transform to operate independently of the XML namespace (which
differs depending on the version of the record).

Greg Janee <gjanee@ucop.edu>

Copyright (c) 2011, Regents of the University of California
http://creativecommons.org/licenses/BSD/

=========================================================================== -->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="xml" omit-xml-declaration="yes"/>

<xsl:variable name="altId" select="'alternateIdentifier'"/>
<xsl:variable name="relId" select="'relatedIdentifier'"/>

<xsl:template match="*[local-name()='resource']">
  <table class="dcms_table">
    <tr class="dcms_element dcms_identifier">
      <th class="dcms_label dcms_identifier">Identifier:</th>
      <td class="dcms_value dcms_identifier">
        <xsl:variable name="idType"
          select="*[local-name()='identifier']/@identifierType"/>
        <xsl:choose>
          <xsl:when test="$idType = 'DOI'">
            <xsl:text>doi:</xsl:text>
          </xsl:when>
          <xsl:when test="$idType = 'ARK'">
            <xsl:text>ark:/</xsl:text>
          </xsl:when>
          <xsl:when test="$idType = 'URN:UUID'">
            <xsl:text>urn:uuid:</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$idType"/>
            <xsl:text>:</xsl:text>
          </xsl:otherwise>
        </xsl:choose>
        <xsl:value-of select="*[local-name()='identifier']"/>
      </td>
    </tr>
    <tr class="dcms_element dcms_creators">
      <th class="dcms_label dcms_creators">Creators:</th>
      <td class="dcms_value dcms_creators">
        <xsl:apply-templates
          select="*[local-name()='creators']/*[local-name()='creator']"/>
      </td>
    </tr>
    <xsl:apply-templates
      select="*[local-name()='titles']/*[local-name()='title']"/>
    <tr class="dcms_element dcms_publisher">
      <th class="dcms_label dcms_publisher">Publisher:</th>
      <td class="dcms_value dcms_publisher">
        <xsl:value-of select="*[local-name()='publisher']"/>
      </td>
    </tr>
    <tr class="dcms_element dcms_publicationyear">
      <th class="dcms_label dcms_publicationyear">Publication year:</th>
      <td class="dcms_value dcms_publicationyear">
        <xsl:value-of select="*[local-name()='publicationYear']"/>
      </td>
    </tr>
    <xsl:if test="*[local-name()='language']">
      <tr class="dcms_element dcms_language">
        <th class="dcms_label dcms_language">Language:</th>
        <td class="dcms_value dcms_language">
          <xsl:value-of select="*[local-name()='language']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='resourceType']">
      <tr class="dcms_element dcms_resourcetype">
        <th class="dcms_label dcms_resourcetype">Resource type:</th>
        <td class="dcms_value dcms_resourcetype">
          <xsl:value-of
            select="*[local-name()='resourceType']/@resourceTypeGeneral"/>
          <xsl:if test="normalize-space(*[local-name()='resourceType']) != ''">
            <xsl:text>/</xsl:text>
            <xsl:value-of select="*[local-name()='resourceType']"/>
          </xsl:if>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='descriptions']/*[local-name()='description'][text()]">
      <xsl:apply-templates
        select="*[local-name()='descriptions']/*[local-name()='description']"/>
    </xsl:if>
    <xsl:if test="*[local-name()='subjects']/*[local-name()='subject']">
      <tr class="dcms_element dcms_subjects">
        <th class="dcms_label dcms_subjects">Subjects:</th>
        <td class="dcms_value dcms_subjects">
          <xsl:apply-templates
            select="*[local-name()='subjects']/*[local-name()='subject']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if
      test="*[local-name()='contributors']/*[local-name()='contributor']">
      <tr class="dcms_element dcms_contributors">
        <th class="dcms_label dcms_contributors">Contributors:</th>
        <td class="dcms_value dcms_contributors">
          <xsl:apply-templates select=
            "*[local-name()='contributors']/*[local-name()='contributor']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='dates']/*[local-name()='date']">
      <tr class="dcms_element dcms_dates">
        <th class="dcms_label dcms_dates">Dates:</th>
        <td class="dcms_value dcms_dates">
          <xsl:apply-templates
            select="*[local-name()='dates']/*[local-name()='date']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()=concat($altId, 's')]/*[local-name()=$altId]">
      <tr class="dcms_element dcms_alternateidentifiers">
        <th class=
          "dcms_label dcms_alternateidentifiers">Alternate identifiers:</th>
        <td class="dcms_value dcms_alternateidentifiers">
          <xsl:apply-templates select=
            "*[local-name()=concat($altId, 's')]/*[local-name()=$altId]"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()=concat($relId, 's')]/*[local-name()=$relId]">
      <tr class="dcms_element dcms_relatedidentifiers">
        <th class=
          "dcms_label dcms_relatedidentifiers">Related identifiers:</th>
        <td class="dcms_value dcms_relatedidentifiers">
          <xsl:apply-templates select=
            "*[local-name()=concat($relId, 's')]/*[local-name()=$relId]"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='sizes']/*[local-name()='size']">
      <tr class="dcms_element dcms_sizes">
        <th class="dcms_label dcms_sizes">Sizes:</th>
        <td class="dcms_value dcms_sizes">
          <xsl:apply-templates
            select="*[local-name()='sizes']/*[local-name()='size']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='formats']/*[local-name()='format']">
      <tr class="dcms_element dcms_formats">
        <th class="dcms_label dcms_formats">Formats:</th>
        <td class="dcms_value dcms_formats">
          <xsl:apply-templates
            select="*[local-name()='formats']/*[local-name()='format']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='version']">
      <tr class="dcms_element dcms_version">
        <th class="dcms_label dcms_version">Version:</th>
        <td class="dcms_value dcms_version">
          <xsl:value-of select="*[local-name()='version']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if test="*[local-name()='rightsList']/*[local-name()='rights']">
      <tr class="dcms_element dcms_rights">
        <th class="dcms_label dcms_rights">Rights:</th>
        <td class="dcms_value dcms_rights">
          <xsl:apply-templates
            select="*[local-name()='rightsList']/*[local-name()='rights']"/>
        </td>
      </tr>
    </xsl:if>
    <xsl:if
      test="*[local-name()='geoLocations']/*[local-name()='geoLocation']">
      <tr class="dcms_element dcms_geolocations">
        <th class="dcms_label dcms_geolocations">Geolocations:</th>
        <td class="dcms_value dcms_geolocations">
          <xsl:apply-templates select=
            "*[local-name()='geoLocations']/*[local-name()='geoLocation']"/>
        </td>
      </tr>
    </xsl:if>
  </table>
</xsl:template>

<xsl:template match="*[local-name()='creator']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="*[local-name()='creatorName']"/>
  <xsl:apply-templates select="*[local-name()='nameIdentifier']">
    <xsl:with-param name="contextclass">dcms_creators</xsl:with-param>
  </xsl:apply-templates>
</xsl:template>

<xsl:template match="*[local-name()='nameIdentifier']">
  <xsl:param name="contextclass"/>
  <xsl:text> </xsl:text>
  <xsl:element name="span">
    <xsl:attribute name="class">
      <xsl:text>dcms_subvalue </xsl:text>
      <xsl:value-of select="$contextclass"/>
    </xsl:attribute>
    <xsl:text>[</xsl:text>
    <xsl:value-of select="@nameIdentifierScheme"/>
    <xsl:text>=</xsl:text>
    <xsl:value-of select="."/>
    <xsl:text>]</xsl:text>
  </xsl:element>
</xsl:template>

<xsl:template match="*[local-name()='title']">
  <tr class="dcms_element dcms_titles">
    <th class="dcms_label dcms_titles">
      <xsl:text>Title</xsl:text>
      <xsl:if test="@titleType">
        <xsl:text> </xsl:text>
        <span class="dcms_sublabel dcms_titles">
          <xsl:text>[</xsl:text>
          <xsl:value-of select="@titleType"/>
          <xsl:text>]</xsl:text>
        </span>
      </xsl:if>
      <xsl:text>:</xsl:text>
    </th>
    <td class="dcms_value dcms_titles">
      <xsl:value-of select="."/>
    </td>
  </tr>
</xsl:template>

<xsl:template match="*[local-name()='subject']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
  <xsl:if test="@subjectScheme">
    <xsl:text> </xsl:text>
    <span class="dcms_subvalue dcms_subjects">
      <xsl:text>[</xsl:text>
      <xsl:value-of select="@subjectScheme"/>
      <xsl:text>]</xsl:text>
    </span>
  </xsl:if>
</xsl:template>

<xsl:template match="*[local-name()='contributor']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <!-- The schema says the content type is mixed, but we ignore any
       free-floating text. -->
  <xsl:value-of select="*[local-name()='contributorName']"/>
  <xsl:apply-templates select="*[local-name()='nameIdentifier']">
    <xsl:with-param name="contextclass">dcms_contributors</xsl:with-param>
  </xsl:apply-templates>
  <xsl:text> </xsl:text>
  <span class="dcms_subvalue dcms_contributors">
    <xsl:text>[</xsl:text>
    <xsl:value-of select="@contributorType"/>
    <xsl:text>]</xsl:text>
  </span>
</xsl:template>

<xsl:template match="*[local-name()='date']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
  <xsl:text> </xsl:text>
  <span class="dcms_subvalue dcms_dates">
    <xsl:text>[</xsl:text>
    <xsl:value-of select="@dateType"/>
    <xsl:text>]</xsl:text>
  </span>
</xsl:template>

<xsl:template match="*[local-name()='alternateIdentifier']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
  <xsl:text> </xsl:text>
  <span class="dcms_subvalue dcms_alternateidentifiers">
    <xsl:text>[</xsl:text>
    <xsl:value-of select="@alternateIdentifierType"/>
    <xsl:text>]</xsl:text>
  </span>
</xsl:template>

<xsl:template match="*[local-name()='relatedIdentifier']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
  <xsl:text> </xsl:text>
  <span class="dcms_subvalue dcms_relatedidentifiers">
    <xsl:text>[</xsl:text>
    <xsl:value-of select="@relatedIdentifierType"/>
    <xsl:text>]</xsl:text>
  </span>
  <xsl:text> </xsl:text>
  <span class="dcms_subvalue dcms_relatedidentifiers">
    <xsl:text>[</xsl:text>
    <xsl:value-of select="@relationType"/>
    <xsl:text>]</xsl:text>
  </span>
</xsl:template>

<xsl:template match="*[local-name()='size']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
</xsl:template>

<xsl:template match="*[local-name()='format']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
</xsl:template>

<xsl:template match="*[local-name()='rights']">
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:value-of select="."/>
  <xsl:if test="@rightsURI">
    <xsl:text> </xsl:text>
    <span class="dcms_subvalue dcms_rights">
      <xsl:text>[</xsl:text>
      <xsl:value-of select="@rightsURI"/>
      <xsl:text>]</xsl:text>
    </span>
  </xsl:if>
</xsl:template>

<xsl:template match="*[local-name()='description']">
  <tr class="dcms_element dcms_descriptions">
    <th class="dcms_label dcms_descriptions">
      <xsl:text>Description </xsl:text>
      <span class="dcms_sublabel dcms_descriptions">
        <xsl:text>[</xsl:text>
        <xsl:value-of select="@descriptionType"/>
        <xsl:text>]:</xsl:text>
      </span>
    </th>
    <td class="dcms_value dcms_descriptions">
       <xsl:value-of select="."/>
    </td>
  </tr>
</xsl:template>

<xsl:template match="*[local-name()='geoLocation']">
  <!-- We assume the location has at least one of point/box/place,
       though the schema requires nothing. -->
  <xsl:if test="position() != 1">
    <xsl:text>; </xsl:text>
  </xsl:if>
  <xsl:choose>
    <xsl:when test="*[local-name()='geoLocationPlace']">
      <xsl:value-of select="*[local-name()='geoLocationPlace']"/>
      <xsl:if test="*[local-name()='geoLocationPoint'] or
        *[local-name()='geoLocationBox']">
        <xsl:text> </xsl:text>
        <span class="dcms_subvalue dcms_geolocations">
          <xsl:text>[</xsl:text>
          <xsl:if test="*[local-name()='geoLocationPoint']">
            <xsl:text>point </xsl:text>
            <xsl:value-of select="*[local-name()='geoLocationPoint']"/>
          </xsl:if>
          <xsl:if test="*[local-name()='geoLocationBox']">
            <xsl:if test="*[local-name()='geoLocationPoint']">
              <xsl:text>; </xsl:text>
            </xsl:if>
            <xsl:text>box </xsl:text>
            <xsl:value-of select="*[local-name()='geoLocationBox']"/>
          </xsl:if>
          <xsl:text>]</xsl:text>
        </span>
      </xsl:if>
    </xsl:when>
    <xsl:otherwise>
      <xsl:text>[</xsl:text>
      <xsl:if test="*[local-name()='geoLocationPoint']">
        <xsl:text>point </xsl:text>
        <xsl:value-of select="*[local-name()='geoLocationPoint']"/>
      </xsl:if>
      <xsl:if test="*[local-name()='geoLocationBox']">
        <xsl:if test="*[local-name()='geoLocationPoint']">
          <xsl:text>; </xsl:text>
        </xsl:if>
        <xsl:text>box </xsl:text>
        <xsl:value-of select="*[local-name()='geoLocationBox']"/>
      </xsl:if>
      <xsl:text>]</xsl:text>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="*[local-name()='br']">
  <br/>
</xsl:template>

<!-- Prevent any other output. -->
<xsl:template match="*"/>

</xsl:stylesheet>
