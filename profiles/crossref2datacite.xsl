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
in the document tree for conversion values that are logically
inherited by lower levels.  For example, a <content_item> within a
<book> does not inherit the book's publisher or publication date,
though logically it should.  In defense of this limitation, the
higher-level inherited values need not always be specified, and may be
completely absent such as in the case of a <sa_component>.  In short,
this transform simply does not have the benefit of the backing of
CrossRef's database.

This transform accepts the following optional external parameters:

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
  <identifier identifierType="DOI">
    <xsl:value-of select="*[local-name()='doi']"/>
  </identifier>
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
  <xsl:variable name="dd" select=
    "../*[local-name()='database_date']/*[local-name()='publication_date']"/>
  <xsl:choose>
    <xsl:when test="$datacite.publicationyear != '(:unav)'">
      <publicationYear>
        <xsl:value-of select="$datacite.publicationyear"/>
      </publicationYear>
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
  <publicationYear>
    <xsl:value-of select="*[local-name()='year']"/>
  </publicationYear>
</xsl:template>

<!-- Prevent any other output. -->
<xsl:template match="*"/>

</xsl:stylesheet>
