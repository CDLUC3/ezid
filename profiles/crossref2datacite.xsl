<?xml version="1.0"?>

<!-- ==========================================================================

Converts a CrossRef Deposit Schema document
<http://help.crossref.org/deposit_schema> to a DataCite Metadata
Schema record <http://schema.datacite.org/>.

This transform focuses on populating just the required DataCite
elements (creator, title, publisher, publication year) and the
resource type element.  It makes the same assumption that EZID makes
in general: that there is exactly one <doi_data> element in the input
document.  It attempts to always generate a valid output record; where
suitable conversion values aren't found, the (:unav) code is inserted
instead.

A general limitation of this transform is that it does not look higher
in the document tree for conversion values that are inherited by lower
levels.  For example, a <content_item> within a <book> does not
inherit the book's publisher or publication date, though it probably
should.  In defense of this limitation, the higher-level inherited
values need not always be specified, and may be completely absent such
as in the case of a <sa_component>.  In short, this transform simply
does not have the benefit of the backing of CrossRef's database.

This transform accepts the following optional external parameters:

  _idType (defaults to "DOI")
  _id
  datacite.creator
  datacite.title
  datacite.publisher
  datacite.publicationyear
  datacite.resourcetype

If a parameter is supplied, it overrides the conversion value(s) that
would otherwise be used.  Note that parameter values must be quoted so
that they are valid XPath string literals, e.g., a value "foo" must be
supplied as "'foo'".  Sadly, there is no mechanism for escaping
internal quotes.

The conversion is based on CrossRef version 4.3.4 and DataCite version
3.1.

The XPath expressions are written the convoluted way they are to allow
this transform to operate independently of the XML namespace (which
differs depending on the version of the input document).

Greg Janee <gjanee@ucop.edu>

Copyright (c) 2014, Regents of the University of California
http://creativecommons.org/licenses/BSD/

=========================================================================== -->

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://datacite.org/schema/kernel-3"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

<xsl:param name="_idType" select="'DOI'"/>
<xsl:param name="_id" select="'(:unav)'"/>
<xsl:param name="datacite.creator" select="'(:unav)'"/>
<xsl:param name="datacite.title" select="'(:unav)'"/>
<xsl:param name="datacite.publisher" select="'(:unav)'"/>
<xsl:param name="datacite.publicationyear" select="'(:unav)'"/>
<xsl:param name="datacite.resourcetype" select="'(:unav)'"/>

<xsl:output method="xml" omit-xml-declaration="yes"/>

<xsl:template match="/">
  <resource xsi:schemaLocation="http://datacite.org/schema/kernel-3
    http://schema.datacite.org/meta/kernel-3/metadata.xsd">
    <xsl:apply-templates select="//*[local-name()='doi_data']"/>
  </resource>
</xsl:template>

<xsl:template match="*[local-name()='doi_data']">
  <!-- identifier -->
  <xsl:element name="identifier">
    <xsl:attribute name="identifierType">
      <xsl:value-of select="$_idType"/>
    </xsl:attribute>
    <xsl:choose>
      <xsl:when test="$_id != '(:unav)'">
        <xsl:value-of select="$_id"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="*[local-name()='doi']"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:element>
  <!-- creator -->
  <creators>
    <xsl:choose>
      <xsl:when test="$datacite.creator != '(:unav)'">
        <creator>
          <creatorName>
            <xsl:value-of select="$datacite.creator"/>
          </creatorName>
        </creator>
      </xsl:when>
      <xsl:when test="../*[local-name()='contributors']/
        *[local-name()='person_name'] or ../*[local-name()='contributors']/
        *[local-name()='organization']">
        <xsl:apply-templates select="../*[local-name()='contributors']/
          *[@sequence='first']"/>
        <xsl:apply-templates select="../*[local-name()='contributors']/
          *[@sequence='additional']"/>
      </xsl:when>
      <xsl:when test="../*[local-name()='person_name']">
        <xsl:apply-templates select="../*[local-name()='person_name']"/>
      </xsl:when>
      <xsl:otherwise>
        <creator>
          <creatorName>(:unav)</creatorName>
        </creator>
      </xsl:otherwise>
    </xsl:choose>
  </creators>
  <!-- title -->
  <titles>
    <xsl:choose>
      <xsl:when test="$datacite.title != '(:unav)'">
        <title>
          <xsl:value-of select="$datacite.title"/>
        </title>
      </xsl:when>
      <xsl:when test="../*[local-name()='titles'] or
        ../*[local-name()='proceedings_title'] or
        ../*[local-name()='full_title'] or ../*[local-name()='abbrev_title']">
        <xsl:apply-templates select="../*[local-name()='titles']"/>
        <xsl:apply-templates select="../*[local-name()='proceedings_title']"/>
        <xsl:apply-templates select="../*[local-name()='full_title']"/>
        <xsl:apply-templates select="../*[local-name()='abbrev_title']"/>
      </xsl:when>
      <xsl:otherwise>
        <title>(:unav)</title>
      </xsl:otherwise>
    </xsl:choose>
  </titles>
  <!-- publisher -->
  <xsl:choose>
    <xsl:when test="$datacite.publisher != '(:unav)'">
      <publisher>
        <xsl:value-of select="$datacite.publisher"/>
      </publisher>
    </xsl:when>
    <xsl:when test="../*[local-name()='publisher']">
      <xsl:apply-templates select="../*[local-name()='publisher'][1]"/>
    </xsl:when>
    <xsl:otherwise>
      <publisher>(:unav)</publisher>
    </xsl:otherwise>
  </xsl:choose>
  <!-- publication year -->
  <xsl:variable name="dd" select=
    "../*[local-name()='database_date']/*[local-name()='publication_date']"/>
  <xsl:choose>
    <xsl:when test="$datacite.publicationyear != '(:unav)'">
      <xsl:choose>
        <xsl:when test="translate($datacite.publicationyear, '0123456789.',
          '..........-') = '....'">
          <publicationYear>
            <xsl:value-of select="$datacite.publicationyear"/>
          </publicationYear>
        </xsl:when>
        <xsl:otherwise>
          <publicationYear>0000</publicationYear>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:when>
    <xsl:when test="../*[local-name()='publication_date']">
      <xsl:apply-templates select="../*[local-name()='publication_date'][1]"/>
    </xsl:when>
    <xsl:when test="$dd">
      <xsl:apply-templates select="$dd[1]"/>
    </xsl:when>
    <xsl:otherwise>
      <publicationYear>0000</publicationYear>
    </xsl:otherwise>
  </xsl:choose>
  <!-- resource type -->
  <xsl:choose>
    <xsl:when test="$datacite.resourcetype != '(:unav)'">
      <xsl:choose>
        <xsl:when test="contains($datacite.resourcetype, '/')">
          <xsl:element name="resourceType">
            <xsl:attribute name="resourceTypeGeneral">
              <xsl:value-of
                select="substring-before($datacite.resourcetype, '/')"/>
            </xsl:attribute>
            <xsl:value-of
              select="substring-after($datacite.resourcetype, '/')"/>
          </xsl:element>
        </xsl:when>
        <xsl:otherwise>
          <xsl:element name="resourceType">
            <xsl:attribute name="resourceTypeGeneral">
              <xsl:value-of select="$datacite.resourcetype"/>
            </xsl:attribute>
          </xsl:element>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:when>
    <xsl:when test="local-name(..) = 'book_metadata'">
      <resourceType resourceTypeGeneral="Text">book</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'book_series_metadata'">
      <resourceType
        resourceTypeGeneral="Text">book, one in a series</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'book_set_metadata'">
      <resourceType
        resourceTypeGeneral="Text">book, one of a set</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'component'">
      <xsl:if test="../*[local-name()='format']/@mime_type">
        <xsl:variable name="mt" select="substring-before(
          ../*[local-name()='format']/@mime_type, '/')"/>
        <xsl:element name="resourceType">
          <xsl:attribute name="resourceTypeGeneral">
            <xsl:choose>
              <xsl:when test="$mt = 'audio'">Sound</xsl:when>
              <xsl:when test="$mt = 'image'">Image</xsl:when>
              <xsl:when test="$mt = 'model'">Model</xsl:when>
              <xsl:when test="$mt = 'text'">Text</xsl:when>
              <xsl:when test="$mt = 'video'">Audiovisual</xsl:when>
              <xsl:otherwise>Other</xsl:otherwise>
            </xsl:choose>
          </xsl:attribute>
          <xsl:value-of select="../*[local-name()='format']/@mime_type"/>
        </xsl:element>
      </xsl:if>
    </xsl:when>
    <xsl:when test="local-name(..) = 'conference_paper'">
      <resourceType resourceTypeGeneral="Text">conference paper</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'content_item'">
      <resourceType resourceTypeGeneral="Text">book content item</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'database_metadata'">
      <resourceType resourceTypeGeneral="Dataset">database</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'dataset'">
      <resourceType resourceTypeGeneral="Dataset">dataset</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'dissertation'">
      <resourceType resourceTypeGeneral="Text">dissertation</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'journal_article'">
      <resourceType resourceTypeGeneral="Text">journal article</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'journal_issue'">
      <resourceType resourceTypeGeneral="Text">journal issue</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'journal_metadata'">
      <resourceType resourceTypeGeneral="Text">journal</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'journal_volume'">
      <resourceType resourceTypeGeneral="Text">journal volume</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'proceedings_metadata'">
      <resourceType resourceTypeGeneral="Text">proceedings</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'proceedings_series_metadata'">
      <resourceType
        resourceTypeGeneral="Text">proceedings, one in a series</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'report-paper_metadata'">
      <resourceType resourceTypeGeneral="Text">report-paper</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'report-paper_series_metadata'">
      <resourceType
        resourceTypeGeneral="Text">report-paper, one in a series</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'series_metadata'">
      <resourceType resourceTypeGeneral="Text">
        <xsl:choose>
          <xsl:when test="local-name(../..) =
            'book_series_metadata'">book series</xsl:when>
          <xsl:when test="local-name(../..) =
            'proceedings_series_metadata'">proceedings series</xsl:when>
          <xsl:when test="local-name(../..) =
            'report-paper_series_metadata'">report-paper series</xsl:when>
        </xsl:choose>
      </resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'set_metadata'">
      <resourceType resourceTypeGeneral="Text">book set</resourceType>
    </xsl:when>
    <xsl:when test="local-name(..) = 'standard_metadata'">
      <resourceType resourceTypeGeneral="Text">standard</resourceType>
    </xsl:when>
  </xsl:choose>
</xsl:template>

<xsl:template match="*[local-name()='organization']">
  <creator>
    <creatorName>
      <xsl:value-of select="."/>
    </creatorName>
  </creator>
</xsl:template>

<xsl:template match="*[local-name()='person_name']">
  <creator>
    <creatorName>
      <xsl:value-of select="*[local-name()='surname']"/>
      <xsl:if test="*[local-name()='given_name']">
        <xsl:text>, </xsl:text>
        <xsl:value-of select="*[local-name()='given_name']"/>
      </xsl:if>
      <xsl:if test="*[local-name()='suffix']">
        <xsl:text>, </xsl:text>
        <xsl:value-of select="*[local-name()='suffix']"/>
      </xsl:if>
    </creatorName>
    <xsl:if test="*[local-name()='ORCID']">
      <nameIdentifier nameIdentifierScheme="ORCID"
        schemeURI="http://orcid.org">
        <xsl:value-of select="*[local-name()='ORCID']"/>
      </nameIdentifier>
    </xsl:if>
    <xsl:apply-templates select="*[local-name()='affiliation']"/>
  </creator>
</xsl:template>

<xsl:template match="*[local-name()='affiliation']">
  <affiliation>
    <xsl:value-of select="."/>
  </affiliation>
</xsl:template>

<xsl:template match="*[local-name()='titles']">
  <!-- Subtle: our conversions below intentionally strip out any
       embedded markup element tags (but not the content of embedded
       elements). -->
  <xsl:variable name="t" select="*[local-name()='title']"/>
  <xsl:variable name="olt" select="*[local-name()='original_language_title']"/>
  <xsl:element name="title">
    <xsl:if test="$olt">
      <xsl:attribute name="titleType">TranslatedTitle</xsl:attribute>
    </xsl:if>
    <xsl:value-of select="$t"/>
  </xsl:element>
  <xsl:variable name="st" select="$t/following-sibling::*[position()=1]"/>
  <xsl:if test="local-name($st) = 'subtitle'">
    <title titleType="Subtitle">
      <xsl:value-of select="$st"/>
    </title>
  </xsl:if>
  <xsl:if test="$olt">
    <xsl:element name="title">
      <xsl:if test="$olt/@language">
        <xsl:attribute name="xml:lang">
          <xsl:value-of select="$olt/@language"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:value-of select="$olt"/>
    </xsl:element>
    <xsl:variable name="olst" select="$olt/following-sibling::*"/>
    <xsl:if test="$olst">
      <title titleType="Subtitle">
        <xsl:value-of select="$olst"/>
      </title>
    </xsl:if>
  </xsl:if>
</xsl:template>

<xsl:template match="*[local-name()='proceedings_title' or
  local-name()='full_title' or local-name()='abbrev_title']">
  <title>
    <xsl:value-of select="."/>
  </title>
</xsl:template>

<xsl:template match="*[local-name()='publisher']">
  <publisher>
    <xsl:if test="*[local-name()='publisher_place']">
      <xsl:value-of select="*[local-name()='publisher_place']"/>
      <xsl:text>: </xsl:text>
    </xsl:if>
    <xsl:value-of select="*[local-name()='publisher_name']"/>
  </publisher>
</xsl:template>

<xsl:template match="*[local-name()='publication_date']">
  <xsl:choose>
    <xsl:when test="translate(normalize-space(*[local-name()='year']),
      '0123456789.', '..........-') = '....'">
      <publicationYear>
        <xsl:value-of select="normalize-space(*[local-name()='year'])"/>
      </publicationYear>
    </xsl:when>
    <xsl:otherwise>
      <publicationYear>0000</publicationYear>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<!-- Prevent any other output. -->
<xsl:template match="*"/>

</xsl:stylesheet>
