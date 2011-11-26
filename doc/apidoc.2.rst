.. role:: hl1
.. role:: hl2

.. |lArr| unicode:: U+021D0 .. leftwards double arrow
.. |rArr| unicode:: U+021D2 .. rightwards double arrow
.. |X| unicode:: U+02713 .. check mark

.. _ANVL: https://wiki.ucop.edu/display/Curation/Anvl
.. _Apache Commons Codec: http://commons.apache.org/codec/
.. _Contact UC3: http://www.cdlib.org/services/uc3/contact.html
.. _content negotiation: http://www.w3.org/Protocols/rfc2616/rfc2616-sec12.html
.. _cookielib: http://docs.python.org/library/cookielib.html
.. _CookieManager:
   http://download.oracle.com/javase/6/docs/api/java/net/CookieManager.html
.. _cURL: http://curl.haxx.se/
.. _DataCite: http://datacite.org/
.. _DataCite Metadata Scheme: http://schema.datacite.org/
.. _Dublin Core Metadata Element Set: http://dublincore.org/documents/dces/
.. _ERC: https://wiki.ucop.edu/display/Curation/ERC
.. _libwww-perl: http://search.cpan.org/dist/libwww-perl/
.. _percent-encoding: http://en.wikipedia.org/wiki/Percent-encoding
.. _REST-style: http://oreilly.com/catalog/9780596529260

The EZID API, Version 2
=======================

.. superseded warning placeholder

.. class:: smallfont

| **This version:** http://n2t.net/ezid/doc/apidoc.2.html
| **Latest version:** http://n2t.net/ezid/doc/apidoc.html
| **Previous version:** http://n2t.net/ezid/doc/apidoc.1.html

EZID (easy-eye-dee) provides an easy way to obtain, describe, and
manage long-term identifiers for digital objects.  It can be accessed
via a web User Interface (UI) and a web Application Programming
Interface (API).  A few account management functions can be accessed
from the UI only, but otherwise all of EZID's functionality is
available through the API.  This document describes Version 2 of the
EZID API.

Please send mail to the EZID discussion list to ask questions or
report problems:

  ezid-l@listserv.ucop.edu

Contents
--------

- Framework_
- `API vs. UI`_
- Authentication_
- `Request & response bodies`_
- `Error handling`_
- `Operation: get identifier metadata`_
- `Operation: create identifier`_
- `Operation: mint identifier`_
- `Operation: modify identifier`_
- `Operation: delete identifier`_
- `Ownership model`_
- `Shadow ARKs`_
- `Identifier status`_
- `Internal metadata`_
- `Metadata profiles`_
- `Testing the API`_
- `Python example`_
- `PHP examples`_
- `Perl examples`_
- `cURL examples`_

Framework
---------

The EZID API is available from the base URL

  http://n2t.net/ezid

Interaction is via REST-style_ HTTP web services.  The API's central
design principle is to treat an identifier as a kind of web resource.
Specifically, identifier `foo`:hl1: is represented as a resource at
URL \http://n2t.net/ezid/id/`foo`:hl1:.  In this document we will
refer to this URL as the identifier's "EZID URL."  A client
manipulates an identifier by performing HTTP operations on its EZID
URL: PUT to create the identifier, GET to view it, and POST to modify
it.

An identifier's EZID URL should not be confused with the identifier's
"URL form."  The former is used to manipulate the identifier, whereas
the latter is used to express the identifier as an embeddable
hyperlink that redirects to the identifier's target URL.  For DOI
identifiers:

.. class:: leftheaders

========== =================================================
Identifier `doi:10.nnnn/suffix`:hl1:
URL form   \http://dx.doi.org/`10.nnnn/suffix`:hl1:
EZID URL   \http://n2t.net/ezid/id/`doi:10.nnnn/suffix`:hl1:
========== =================================================

For ARK identifiers:

.. class:: leftheaders

========== ================================================
Identifier `ark:/nnnnn/suffix`:hl1:
URL form   \http://n2t.net/`ark:/nnnnn/suffix`:hl1:
EZID URL   \http://n2t.net/ezid/id/`ark:/nnnnn/suffix`:hl1:
========== ================================================

For URN identifiers:

.. class:: leftheaders

========== ================================================
Identifier `urn:nid:suffix`:hl1:
URL form   \http://n2t.net/`urn:nid:suffix`:hl1:
EZID URL   \http://n2t.net/ezid/id/`urn:nid:suffix`:hl1:
========== ================================================

API vs. UI
----------

The EZID UI and API share some URLs (the base URL is the same for
both) but their behavior is different.  For example, in the API a GET
operation on an EZID URL returns client-parseable metadata (see
`Operation: get identifier metadata`_ below), but in the UI it returns
an HTML page.

To distinguish between the two interfaces EZID employs HTTP `content
negotiation`_.  If a request comes in with an HTTP Accept header that
expresses a preference for any form of HTML or XML, the UI is invoked;
otherwise, the API is invoked.  A preference for the API can be made
explicit by omitting any Accept header, or setting the Accept header
to something like "text/plain".  If using Java, it will probably be
necessary to override the default Accept header Java sends as
follows::

  import java.net.*;

  URL u = new URL("http://n2t.net/ezid/...");
  URLConnection c = u.openConnection();
  c.setRequestProperty("Accept", "text/plain");
  c.connect();

Authentication
--------------

Most requests require authentication.  The EZID API supports two
methods of authentication:

1. **HTTP Basic authentication over SSL**.  With this method, the
   client connects to EZID using HTTPS URLs (i.e.,
   \https://n2t.net/ezid/...) and supplies HTTP Basic
   authentication credentials on every request.  HTTPS URLs *must* be
   used.  The authentication realm is "EZID".  For example,
   credentials can be added manually in Python as follows:

   .. parsed-literal::

     import base64, urllib2
     r = urllib2.Request("\https://n2t.net/ezid/...")
     r.add_header("Authorization", "Basic " + \
     base64.b64encode("`username`:hl2::`password`:hl2:"))

   But most programming libraries provide higher-level support for
   authentication.  For example, Python provides HTTPBasicAuthHandler:

   .. parsed-literal::

     import urllib2
     h = urllib2.HTTPBasicAuthHandler()
     h.add_password("EZID", "\https://n2t.net/ezid/", "`username`:hl2:", \
     "`password`:hl2:")
     o = urllib2.build_opener(h)
     o.open("\https://n2t.net/ezid/...")

   The downside of using higher-level authentication mechanisms is
   that they often do not supply credentials initially, but only in
   response to a challenge from EZID, thus doubling the number of HTTP
   transactions.

   To manually provide credentials in Java, using `Apache Commons
   Codec`_ to do the Base64 encoding:

   .. parsed-literal::

     import java.net.*;
     import org.apache.commons.codec.binary.*;

     URL u = new URL("\https://n2t.net/ezid/...);
     URLConnection c = u.openConnection();
     c.setRequestProperty("Accept", "text/plain");
     c.setRequestProperty("Authorization", "Basic " +
       new String(Base64.encodeBase64("`username`:hl2::`password`:hl2:".\
     getBytes())));
     c.connect();

   Java also provides an Authenticator class:

   .. parsed-literal::

     import java.net.*;

     class MyAuthenticator extends Authenticator {
       protected PasswordAuthentication getPasswordAuthentication () {
         return new PasswordAuthentication("`username`:hl2:", \
     "`password`:hl2:".toCharArray());
       }
     }

     Authenticator.setDefault(new MyAuthenticator());

2. **One-time login over SSL**.  Perform a GET operation on
   \https://n2t.net/ezid/login and supply HTTP Basic credentials as
   above.  In response, EZID returns a session cookie.  Remaining
   requests can be made over plain HTTP as long as the session cookie
   is supplied in an HTTP Cookie header.  Here's an example
   interaction:

   .. parsed-literal::

     |rArr| GET /ezid/login HTTP/1.1
     |rArr| Host: n2t.net
     |rArr| Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

     |lArr| HTTP/1.1 200 OK
     |lArr| Set-Cookie: sessionid=403a1ea3b03b74f663c1cd7fc877f495; expires...
     |lArr| Content-Type: text/plain; charset=UTF-8
     |lArr| Content-Length: 32
     |lArr|
     |lArr| success: session cookie returned

   In Python, cookies can be managed using cookielib_, or manually
   captured and set using code similar to the following:

   .. parsed-literal::

     import urllib2
     c = urllib2.urlopen("\https://n2t.net/ezid/login")
     `cookie`:hl2: = c.headers["Set-Cookie"].split(";")[0]
     ...
     r = urllib2.Request("\http://n2t.net/ezid/...")
     r.add_header("Cookie", `cookie`:hl2:)

   In Java, cookies can be manually captured and set using code
   analogous to the Python code above or, in Java 1.6 and newer,
   CookieManager_ can be used to manage cookies.

   Perform a GET operation on \http://n2t.net/ezid/logout to
   invalidate a session.

Request & response bodies
-------------------------

Request and response bodies are used to transmit identifier metadata.
The HTTP content type for all bodies is "text/plain" using UTF-8
charset encoding.  In request bodies, if no charset encoding is
declared in the HTTP Content-Type header, it is assumed to be UTF-8.

EZID's data model for metadata is a dictionary of element name/value
pairs.  Names and values are strings.  Leading and trailing whitespace
in names and values is not significant.  Element values may be empty,
but not names.

Metadata dictionaries are serialized using a subset of `A Name-Value
Language (ANVL)`__ rules:

__ ANVL_

- One element name/value pair per line.

- Names separated from values by colons.

For example::

  who: Proust, Marcel
  what: Remembrance of Things Past
  when: 1922

Care must be taken to escape structural characters that appear in
element names and values, specifically, line terminators (both
newlines ("\\n", U+000A) and carriage returns ("\\r", U+000D)) and, in
element names, colons (":", U+003A).  EZID employs `percent-encoding`_
as the escaping mechanism, and thus percent signs ("%", U+0025) must
be escaped as well.  In Python, a dictionary of Unicode metadata
element names and values, `metadata`:hl1:, is serialized into a UTF-8
encoded string, `anvl`:hl1:, with the following code:

.. parsed-literal::

  import re

  def escape (s):
    return re.sub("[%:\\r\\n]", lambda c: "%%%02X" % ord(c.group(0)), s)

  `anvl`:hl2: = "\\n".join("%s: %s" % (escape(name), escape(value)) for name,
    value in `metadata`:hl2:.items()).encode("UTF-8")

Conversely, to parse a UTF-8 encoded string, `anvl`:hl1:, producing
a dictionary, `metadata`:hl1:\:

.. parsed-literal::

  import re

  def unescape (s):
    return re.sub("%([0-9A-Fa-f][0-9A-Fa-f])",
      lambda m: chr(int(m.group(1), 16)), s)

  `metadata`:hl2: = dict(tuple(unescape(v).strip() for v in l.split(":", 1)) \\
    for l in `anvl`:hl2:.decode("UTF-8").splitlines())

In Java, to serialize a HashMap of metadata element names and values,
`metadata`:hl1:, into an ANVL-formatted Unicode string, `anvl`:hl1:\:

.. parsed-literal::

  import java.util.*;

  String escape (String s) {
    return s.replace("%", "%25").replace("\\n", "%0A").
      replace("\\r", "%0D").replace(":", "%3A");
  }

  Iterator<Map.Entry<String, String>> i = \
  `metadata`:hl2:.entrySet().iterator();
  StringBuffer b = new StringBuffer();
  while (i.hasNext()) {
    Map.Entry<String, String> e = i.next();
    b.append(escape(e.getKey()) + ": " + escape(e.getValue()) + "\\n");
  }
  String `anvl`:hl2: = b.toString();

And conversely, to parse a Unicode ANVL-formatted string, `anvl`:hl1:,
producing a HashMap, `metadata`:hl1:\:

.. parsed-literal::

  import java.util.*;

  String unescape (String s) {
    StringBuffer b = new StringBuffer();
    int i;
    while ((i = s.indexOf("%")) >= 0) {
      b.append(s.substring(0, i));
      b.append((char) Integer.parseInt(s.substring(i+1, i+3), 16));
      s = s.substring(i+3);
    }
    b.append(s);
    return b.toString();
  }

  HashMap<String, String> `metadata`:hl2: = new HashMap<String, String>();
  for (String l : `anvl`:hl2:.split("[\\\\r\\\\n]+")) {
    String[] kv = l.split(":", 2);
    metadata.put(unescape(kv[0]).trim(), unescape(kv[1]).trim());
  }

The first line of an EZID response body is a status indicator
consisting of "success" or "error", followed by a colon, followed by
additional information.  Two examples::

  success: ark:/99999/fk4test
  error: bad request - no such identifier

Error handling
--------------

An error is indicated by both an HTTP status code and an error status
line of the form "error: `reason`:hl1:".  For example:

.. parsed-literal::

  |rArr| GET /ezid/id/ark:/99999/bogus HTTP/1.1
  |rArr| Host: n2t.net

  |lArr| HTTP/1.1 400 BAD REQUEST
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 39
  |lArr|
  |lArr| error: bad request - no such identifier

Operation: get identifier metadata
----------------------------------

Metadata can be retrieved for any existing identifier; no
authentication is required.  Simply issue a GET request to the
identifier's EZID URL.  Here is a sample interaction:

.. parsed-literal::

  |rArr| GET /ezid/id/ark:/99999/fk4cz3dh0 HTTP/1.1
  |rArr| Host: n2t.net

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 208
  |lArr|
  |lArr| success: ark:/99999/fk4cz3dh0
  |lArr| _created: 1300812337
  |lArr| _updated: 1300913550
  |lArr| _target: \http://www.gutenberg.org/ebooks/7178
  |lArr| _profile: erc
  |lArr| erc.who: Proust, Marcel
  |lArr| erc.what: Remembrance of Things Past
  |lArr| erc.when: 1922

The first line of the response body is a status line.  Assuming
success (see `Error handling`_ above), the remainder of the status
line echoes the canonical form of the requested identifier.

The remaining lines are metadata element name/value pairs serialized
per ANVL rules; see `Request & response bodies`_ above.  The order of
elements is undefined.  Element names beginning with an underscore
("_", U+005F) are reserved for use by EZID; their meanings are
described in `Internal metadata`_ below.  Some elements may be drawn
from citation metadata standards; see `Metadata profiles`_ below.

Operation: create identifier
----------------------------

An identifier can be "created" by sending a PUT request to the
identifier's EZID URL.  Here, identifier creation means establishing a
record of the identifier in EZID (to be successful, no such record can
already exist).  Authentication is required, and the user's group must
have permission to create identifiers in the namespace (or "shoulder")
named by the identifier's prefix.  Users can view the namespaces
available to their group by visiting the EZID UI and navigating to the
Create tab.  For example, if the user's group has permission to create
identifiers in the general EZID ARK (ark:/13030/c7) namespace, then
the user may create identifiers beginning with "ark:/13030/c7".

A request body is optional; if present, it defines the identifier's
starting metadata.  There are no restrictions on what metadata
elements can be submitted, but a convention has been established for
naming metadata elements, and EZID has built-in support for certain
sets of metadata elements; see `Metadata profiles`_ below.  A few of
the internal EZID metadata elements may be set; see `Internal
metadata`_ below.

Here's a sample interaction creating an ARK identifier:

.. parsed-literal::

  |rArr| PUT /ezid/id/ark:/99999/fk4test HTTP/1.1
  |rArr| Host: n2t.net
  |rArr| Content-Type: text/plain; charset=UTF-8
  |rArr| Content-Length: 30
  |rArr|
  |rArr| _target: \http://www.cdlib.org/

  |lArr| HTTP/1.1 201 CREATED
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 27
  |lArr|
  |lArr| success: ark:/99999/fk4test

The return is a status line.  If an ARK identifier was created, the
normalized form of the identifier is returned as shown above.  If an
identifier other than an ARK was created (e.g., a DOI or URN), the
status line includes the normalized form of the identifier and,
separated by a pipe character ("|", U+007C), the identifier's shadow
ARK (see `Shadow ARKs`_ for more information).  Note that different
identifier schemes have different normalization rules (e.g., DOIs are
normalized to all uppercase letters).  Here's a sample interaction
creating a DOI identifier:

.. parsed-literal::

  |rArr| PUT /ezid/id/doi:10.9999/test HTTP/1.1
  |rArr| Host: n2t.net

  |lArr| HTTP/1.1 201 CREATED
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 43
  |lArr|
  |lArr| success: doi:10.9999/TEST | ark:/b9999/test

Operation: mint identifier
--------------------------

Minting an identifier is the same as creating an identifier, but
instead of supplying a complete identifier, the client specifies only
a namespace (or "shoulder") that forms the identifier's prefix, and
EZID generates an opaque, random string for the identifier's suffix.
An identifier can be minted by sending a POST request to the URL
\http://n2t.net/ezid/shoulder/`shoulder`:hl1: where `shoulder`:hl1: is
the desired namespace.  For example:

.. parsed-literal::

  |rArr| POST /ezid/shoulder/`ark:/13030/c7`:hl2: HTTP/1.1
  |rArr| Host: n2t.net
  |rArr| Content-Type: text/plain; charset=UTF-8
  |rArr| Content-Length: 30
  |rArr|
  |rArr| _target: \http://www.cdlib.org/

  |lArr| HTTP/1.1 201 CREATED
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 29
  |lArr|
  |lArr| success: `ark:/13030/c7`:hl2:\ 9cz3dh0

Aside from specifying a complete identifier versus specifying a
shoulder only, the create and mint operations operate identically.
Authentication is required to mint an identifier; namespace permission
is required; and permissions can be viewed in the EZID UI under the
Create tab.  The request and response bodies are identical.

Operation: modify identifier
----------------------------

An identifier's metadata can be modified by sending a POST request to
the identifier's EZID URL.  Authentication is required; only the
identifier's owner and any listed co-owners may modify the identifier
(see `Ownership model`_ below).

Metadata elements are operated on individually.  If the identifier
already has a value for a metadata element included in the request
body, the value is overwritten, otherwise the element and its value
are added.  Only a few of the reserved EZID metadata elements may be
modified; see `Internal metadata`_ below.  Here's a sample
interaction:

.. parsed-literal::

  |rArr| POST /ezid/id/ark:/99999/fk4cz3dh0 HTTP/1.1
  |rArr| Host: n2t.net
  |rArr| Content-Type: text/plain; charset=UTF-8
  |rArr| Content-Length: 30
  |rArr|
  |rArr| _target: \http://www.cdlib.org/

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 29
  |lArr|
  |lArr| success: ark:/99999/fk4cz3dh0

The return is a status line.  Assuming success (see `Error handling`_
above), the remainder of the status line echoes the canonical form of
the identifier in question.

There is currently no means to delete a metadata element, but setting
an element's value to the empty string has much the same effect.

Operation: delete identifier
----------------------------

An identifier that has only been reserved can be deleted by sending a
DELETE request to the identifier's EZID URL.  We emphasize that only
*reserved* identifiers may be deleted; see `Identifier status`_ below.
Authentication is required; only an identifier's owner and any listed
co-owners may delete the identifier (see `Ownership model`_).

Here's a sample interaction:

.. parsed-literal::

  |rArr| DELETE /ezid/id/ark:/99999/fk4cz3dh0 HTTP/1.1
  |rArr| Host: n2t.net

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 29
  |lArr|
  |lArr| success: ark:/99999/fk4cz3dh0

The return is a status line.  Assuming success (see `Error handling`_
above), the remainder of the status line echoes the canonical form of
the identifier just deleted.

Ownership model
---------------

EZID maintains ownership information about identifiers and uses that
information to enforce access control.

For read access, identifiers are considered public resources, and
their EZID metadata may be retrieved by anybody, just as anybody may
submit the URL form of an identifier to a resolving service and be
redirected to the identifier's target URL.  But an identifier may be
modified only by its owner.

Additionally, an identifier may have one or more "co-owners," which
are users other than the owner who are allowed to modify the
identifier.  Co-ownership can be specified in two ways.  First, it can
be specified globally as part of a user's account profile.  For
example, assuming a repository `R`:hl1: has an EZID account (i.e.,
this is a special kind of EZID user representing a repository system),
an EZID user `U`:hl1: depositing digital objects in `R`:hl1: and using
EZID to create identifiers for those objects can name `R`:hl1: as a
co-owner of all its identifiers, past and future, thereby allowing the
repository to manage the objects' target URLs and other metadata.
Visit the EZID UI and navigate to "My account" to specify global
co-ownership.

Second, co-ownership can be specified on a per-identifier basis by
listing one or more users in the identifier's "_coowners" reserved
metadata element; see `Internal metadata`_ below.  For example,
repository `R`:hl1:, creating identifiers in EZID on behalf of EZID
user `U`:hl1:, can name `U`:hl1: as a co-owner of those identifiers,
thereby giving `U`:hl1: the right to modify identifiers created by the
repository on its behalf.  Note that any time a user modifies an
identifier that it doesn't own, EZID adds the user to the identifier's
"_coowners" element.

Shadow ARKs
-----------

When EZID creates a non-ARK identifier (e.g., a DOI identifier), it
also creates a related ARK identifier.  These special ARK identifiers
are termed "shadow ARKs."

A non-ARK identifier and its shadow ARK have the same owner and
co-owners (and hence the same access characteristics) and the same
creation time and citation metadata, but they have separate target
URLs and update times.  By sharing citation metadata, a non-ARK
identifier and its shadow ARK are intended to identify the same
digital object or conceptual entity, but having separate target URLs
allows the identifiers to address different representations of the
object.  Clients can also use shadow ARKs to exploit the different
technical characteristics between ARK and non-ARK identifiers.

Shadow ARKs are returned on the status line when creating or minting
non-ARK identifiers (see `Operation: create identifier`_ and
`Operation: mint identifier`_ above).  Also, a non-ARK identifier's
shadow ARK is returned as the value of the "_shadowedby" reserved
metadata element (see `Internal metadata`_ below).  Conversely, the
identifier shadowed by a shadow ARK is returned as the value of its
"_shadows" metadata element.

Shadow ARKs have similar names to their non-ARK counterparts (for
example, the shadow ARK for identifier doi:10.1234/FOO is
ark:/b1234/foo), but due to subtleties in identifier syntax rules,
clients should not rely on this pattern, nor should they attempt to
map between identifiers themselves.  Instead, the aforementioned
"_shadows" and "_shadowedby" metadata elements should be used to map
between non-ARK identifiers and shadow ARKs.

Identifier status
-----------------

Each identifier in EZID has a status.  In the case of a non-ARK
identifier (e.g., a DOI identifier), the identifier and its shadow ARK
share the same status.  The status is recorded as the value of the
"_status" reserved metadata element (see `Internal metadata`_ below)
and may be one of:

**public**
  The default value.

**reserved**
  The identifier is known only to EZID.  This status may be used to
  reserve an identifier name within EZID without advertising the
  identifier's existence to resolvers and other external services.  A
  reserved identifier may be deleted.

**unavailable**
  The identifier is public, but the object referenced by the
  identifier is not available.  A reason for the object's
  unavailability may optionally follow the status separated by a pipe
  character ("|", U+007C), e.g., "unavailable | withdrawn by author".
  The identifier redirects to an EZID-provided "tombstone" page (an
  HTML page that displays the identifier's citation metadata and the
  reason for the object's unavailability) regardless of its target
  URL.

An identifier's status may be changed by setting a new value for the
aforementioned "_status" metadata element.  EZID permits only certain
status transitions:

* A status of "reserved" may be specified only at identifier
  creation time.

* A reserved identifier may be made public.  At this time the
  identifier will be registered with resolvers and other external
  services.

* A public identifier may be marked as unavailable.

* An unavailable identifier may be returned to public status.

Internal metadata
-----------------

Metadata element names beginning with an underscore ("_", U+005F) are
reserved for use by EZID.  The reserved elements below are returned by
the EZID API, and have the following meanings.  A check mark in the
first column indicates the element is modifiable by clients.

  === =========== ============================================ ================
  |X| Element     Definition                                   Example
  === =========== ============================================ ================
  \   _owner      The identifier's owner.                      jsmith
  \   _ownergroup The identifier's owner's group.              ucla
  |X| _coowners   The identifier's co-owners separated by      manny ; moe ;
                  semicolons (";", U+003B).  Modifiable only   jack
                  by the identifier's owner.
  \   _created    The time the identifier was created          1300812337
                  expressed as a Unix timestamp.
  \   _updated    The time the identifier was last modified    1300913550
                  expressed as a Unix timestamp.
  |X| _target     The identifier's target URL.  Defaults to the identifier's
                  EZID URL.  That is, the default target URL for
                  identifier `foo`:hl1: is the self-referential URL
                  \http://n2t.net/ezid/id/`foo`:hl1:.
  --- ----------- -------------------------------------------------------------
  \   _shadows    Shadow ARKs only.  The shadowed identifier.  doi:10.9999/TEST
  \   _shadowedby Shadowed identifiers only.  The identifier's ark:/b9999/test
                  shadow ARK.
  |X| _profile    The identifier's preferred metadata profile  erc
                  (see `Metadata profiles`_ next).
  |X| _status     The identifier's status (see                 unavailable |
                  `Identifier status`_ above).                 withdrawn by
                                                               author
  === =========== ============================================ ================

Metadata profiles
-----------------

There is no requirement that an identifier have any citation
(descriptive) metadata, but uploading at least minimal citation
metadata to EZID is strongly encouraged to aid in the understanding of
what the identifier represents and to facilitate the identifier's
long-term maintenance.  EZID supports several citation metadata
"profiles," or standard sets of citation metadata elements.

By convention, a metadata profile is referred to using a simple,
lowercase name, e.g., "erc", and elements belonging to that profile
are referred to using the syntax "`profile`:hl1:.\ `element`:hl1:",
e.g., "erc.who".

Currently EZID treats profiles entirely separately, and thus an
identifier may have values for multiple metadata profiles
simultaneously.  However, we anticipate that EZID will provide
metadata cross-walking in the future, in which case setting a value
for an element in one profile will automatically provide a value for
equivalent elements in other profiles.  For this reason, clients are
encouraged to pick one profile to populate per identifier.

The "_profile" internal metadata element defines the identifier's
preferred metadata profile (typically the only profile for which it
has metadata).  There is no restriction on what metadata elements may
be bound to an identifier, and hence clients are free to use alternate
citation profiles or no citation profile at all.  However, EZID's UI
is, and its future metadata cross-walking support will be, limited to
those profiles that it explicitly supports.

1. **Profile "erc"**.  These elements are drawn from `Kernel Metadata
   and Electronic Resource Citations (ERCs)`__.  This profile aims at
   universal citations: any kind of object (digital, physical,
   abstract) or agent (person, group, software, satellite) for any
   purpose (research, education, entertainment, administration), any
   subject focus (oceanography, sales, religion, archiving), and any
   medium (television, newspaper, database, book).  This is the
   default profile for ARK and URN identifiers.

__ ERC_

   ======== ===========================================================
   Element  Definition
   ======== ===========================================================
   erc.who  The name of an entity (person, organization, or service)
            responsible for creating the content or making it
            available.  For an article, this could be an author.  Put
            name parts in "sort-friendly" order, such as:

            - van Gogh, Vincent,
            - Hu Jintao
            - Gilbert, William, Sir,,; Sullivan, Arthur, Sir,

            Separate multiple names with ";".  Append one or more final
            commas (",") to indicate that one or more internal commas
            can be used as inversion points to recover natural word
            order (if different from sort-friendly word order).
   erc.what A name or other human-oriented identifier given to the
            resource.  For an article, this could be a title such
            as:

            - Moby Dick
            - Scarlet Pimpernel, The,

            Use sort-friendly name parts and final commas in the same
            way as for the erc.who element.
   erc.when A point or period of time important in the lifecycle of the
            resource, often when it was created, modified, or made
            available.  For an article, this could be the date it was
            written, such as:

            - 2009.04.23
            - 1924~
            - BCE0386
            - 1998-2003; 2008-

            A date range (which can be open ended) may be useful, such
            as to indicate the years during which a periodical
            operated.  Use ";" to separate entries and "~" to indicate
            approximation.
   ======== ===========================================================

   As a special case, an entire ANVL_ document containing ERC metadata
   may be bound to the metadata element "erc".  Care should be taken
   to escape line terminators in the document (as is true for all
   metadata element values; see `Request & response bodies`_ above).
   For example, the ANVL document::

     who: Proust, Marcel
     what: Remembrance of Things Past

   would be expressed as the single value::

     erc: who: Proust, Marcel%0Awhat: Remembrance of Things Past

2. **Profile "datacite"**.  These elements are drawn from the
   `DataCite Metadata Scheme for the Publication and Citation of
   Research Data`__.  This is the default profile for DOI identifiers.

__ `DataCite Metadata Scheme`_

   ======================== ===========================================
   Element                  Definition
   ======================== ===========================================
   datacite.creator         The main researchers involved in producing
                            the data, or the authors of the publication
                            in priority order.  Each name may be a
                            corporate, institutional, or personal name.
                            In personal names list family name before
                            given name, as in:

                            - Shakespeare, William

                            Non-roman names should be transliterated
                            according to the ALA-LC schemes.
   datacite.title           A name or title by which the data or
                            publication is known.
   datacite.publisher       A holder of the data (e.g., an archive) or
                            the institution which submitted the work.
                            In the case of datasets, the publisher is
                            the entity primarily responsible for making
                            the data available to the research
                            community.
   datacite.publicationyear The year when the data was or will be made
                            publicly available.  If an embargo period
                            is in effect, use the year when the embargo
                            period ends.
   ======================== ===========================================

   As a special case, an entire XML document adhering to the DataCite
   Metadata Scheme schema may be bound to the metadata element
   "datacite".  Care should be taken to escape line terminators and
   percent signs in the document (as is true for all metadata element
   values; see `Request & response bodies`_ above).

   All DataCite Metadata Scheme metadata bound to DOI identifiers is
   automatically and immediately uploaded to DataCite_, where it may
   be made available DataCite's search system and other indexing
   services.

3. **Profile "dc"**.  These elements are drawn from the `Dublin Core
   Metadata Element Set`_.

   ============ =======================================================
   Element      Definition
   ============ =======================================================
   dc.creator   An entity primarily responsible for making the content
                of the resource.  Examples of a Creator include a
                person, an organization, or a service.  Typically, the
                name of a Creator should be used to indicate the
                entity.
   dc.title     A name given to the resource.  Typically, a Title will
                be a name by which the resource is formally known.
   dc.publisher An entity responsible for making the resource
                available.  Examples of a Publisher include a person,
                an organization, or a service.  Typically, the name of
                a Publisher should be used to indicate the entity.
   dc.date      A date associated with an event in the life cycle of
                the resource.  Typically, Date will be associated with
                the creation or availability of the resource.
                Recommended best practice for encoding the date value
                is defined in a profile of ISO 8601 and follows the
                YYYY-MM-DD format.
   ============ =======================================================

Testing the API
---------------

EZID provides two namespaces (or "shoulders") for testing purposes:
ark:/99999/fk4 for ARK identifiers and doi:10.5072/FK2 for DOI
identifiers.  Identifiers in these namespaces are termed "test
identifiers."  They are ordinary long-term identifiers in almost all
respects, including resolvability, except that EZID deletes them after
72 hours.  An additional difference is that citation metadata for test
identifiers is not uploaded to external search services.

All user accounts are permitted to create test identifiers.  EZID also
provides an "apitest" account that is permitted to create only test
identifiers.  `Contact UC3`_ for the password for this account.

Test identifiers and reserved identifiers are orthogonal concepts.  A
test identifier has a limited lifetime and is deleted by EZID when it
expires.  A reserved identifier may be deleted by the owner while
still in its reserved state, but once made public, is permanent.  As
evidence of this orthogonality, it is possible to create reserved test
identifiers.

Python example
--------------

Below is a command line EZID client capable of exercising all API
functions.  Printed output is left UTF-8 encoded.  The general usage
is:

.. parsed-literal::

  % client `credentials`:hl2: `operation`:hl2: `[arguments...]`:hl2:

For example, to view an identifier::

  % client - view ark:/99999/fk4cz3dh0

Run the client with no arguments for a complete usage statement.

::

  #! /usr/bin/python

  import re
  import sys
  import types
  import urllib2

  server = "http://n2t.net/ezid"

  operations = {
    # operation : number of arguments
    "mint" : lambda l: l%2 == 1,
    "create" : lambda l: l%2 == 1,
    "view" : 1,
    "update" : lambda l: l%2 == 1,
    "delete" : 1,
    "login" : 0,
    "logout" : 0
  }

  usageText = """Usage: client credentials operation...

    credentials
      username:password
      sessionid (as returned by previous login)
      - (none)

    operation
      m[int] shoulder [label value label value ...]
      c[reate] identifier [label value label value ...]
      v[iew] identifier
      u[pdate] identifier [label value label value ...]
      d[elete] identifier
      login
      logout
  """

  def usageError ():
    sys.stderr.write(usageText)
    sys.exit(1)

  class MyHTTPErrorProcessor (urllib2.HTTPErrorProcessor):
    def http_response (self, request, response):
      # Bizarre that Python leaves this out.
      if response.code == 201:
        return response
      else:
        return urllib2.HTTPErrorProcessor.http_response(self, request,
          response)
    https_response = http_response

  def formatAnvl (l):
    r = []
    for i in range(0, len(l), 2):
      k = re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), l[i])
      v = re.sub("[%\r\n]", lambda c: "%%%02X" % ord(c.group(0)), l[i+1])
      r.append("%s: %s" % (k, v))
    return "\n".join(r)

  if len(sys.argv) < 3: usageError()
  opener = urllib2.build_opener(MyHTTPErrorProcessor())
  if ":" in sys.argv[1]:
    server = "https" + server[4:]
    h = urllib2.HTTPBasicAuthHandler()
    h.add_password("EZID", server, *sys.argv[1].split(":", 1))
    opener.add_handler(h)
    cookie = None
  elif sys.argv[1] != "-":
    cookie = "sessionid=" + sys.argv[1]
  else:
    cookie = None
  operation = [o for o in operations if o.startswith(sys.argv[2])]
  if len(operation) != 1: usageError()
  operation = operation[0]
  if (type(operations[operation]) is int and\
    len(sys.argv)-3 != operations[operation]) or\
    (type(operations[operation]) is types.LambdaType and\
    not operations[operation](len(sys.argv)-3)): usageError()

  if operation in ["mint", "create", "update"]:
    path = "shoulder" if operation == "mint" else "id"
    request = urllib2.Request("%s/%s/%s" % (server, path, sys.argv[3]))
    request.get_method = lambda: "PUT" if operation == "create" else "POST"
    if len(sys.argv) > 4:
      request.add_header("Content-Type", "text/plain; charset=UTF-8")
      request.add_data(formatAnvl(sys.argv[4:]).encode("UTF-8"))
  elif operation == "delete":
    request = urllib2.Request("%s/id/%s" % (server, sys.argv[3]))
    request.get_method = lambda: "DELETE"
  elif operation == "view":
    request = urllib2.Request("%s/id/%s" % (server, sys.argv[3]))
  elif operation in ["login", "logout"]:
    request = urllib2.Request("%s/%s" % (server, operation))

  if cookie: request.add_header("Cookie", cookie)

  try:
    c = opener.open(request)
    output = c.read()
    if not output.endswith("\n"): output += "\n"
    if operation == "login":
      output += c.info()["set-cookie"].split(";")[0].split("=")[1] + "\n"
    print output,
  except urllib2.HTTPError, e:
    print e.code, e.msg
    print e.fp.read()

PHP examples
------------

PHP is agnostic with respect to character sets and character set
encoding; it operates on bytes only.  The following examples assume
that input data is already UTF-8 encoded and hence can be passed
directly to EZID; if this is not the case, input data will need to be
converted to UTF-8 using the functions PHP provides for that purpose.

Get identifier metadata:

.. parsed-literal::

  <?php
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, \
  '\http://n2t.net/ezid/id/`identifier`:hl2:');
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $output = curl_exec($ch);
  print curl_getinfo($ch, CURLINFO_HTTP_CODE) . "\\n";
  print $output . "\\n";
  curl_close($ch);
  ?>

Create identifier:

.. parsed-literal::

  <?php
  $input = '_target: `url`:hl2:
  `element1`:hl2:: `value1`:hl2:
  `element2`:hl2:: `value2`:hl2:';
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, \
  '\https://n2t.net/ezid/id/`identifier`:hl2:');
  curl_setopt($ch, CURLOPT_USERPWD, \
  '`username`:hl2::`password`:hl2:');
  curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
  curl_setopt($ch, CURLOPT_HTTPHEADER,
    array('Content-Type: text/plain; charset=UTF-8',
          'Content-Length: ' . strlen($input)));
  curl_setopt($ch, CURLOPT_POSTFIELDS, $input);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $output = curl_exec($ch);
  print curl_getinfo($ch, CURLINFO_HTTP_CODE) . "\\n";
  print $output . "\\n";
  curl_close($ch);
  ?>

Mint identifier:

.. parsed-literal::

  <?php
  $input = '_target: `url`:hl2:
  `element1`:hl2:: `value1`:hl2:
  `element2`:hl2:: `value2`:hl2:';
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, \
  '\https://n2t.net/ezid/shoulder/`shoulder`:hl2:');
  curl_setopt($ch, CURLOPT_USERPWD, \
  '`username`:hl2::`password`:hl2:');
  curl_setopt($ch, CURLOPT_POST, true);
  curl_setopt($ch, CURLOPT_HTTPHEADER,
    array('Content-Type: text/plain; charset=UTF-8',
          'Content-Length: ' . strlen($input)));
  curl_setopt($ch, CURLOPT_POSTFIELDS, $input);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $output = curl_exec($ch);
  print curl_getinfo($ch, CURLINFO_HTTP_CODE) . "\\n";
  print $output . "\\n";
  curl_close($ch);
  ?>

Modify identifier:

.. parsed-literal::

  <?php
  $input = '_target: `url`:hl2:';
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, \
  '\https://n2t.net/ezid/id/`identifier`:hl2:');
  curl_setopt($ch, CURLOPT_USERPWD, \
  '`username`:hl2::`password`:hl2:');
  curl_setopt($ch, CURLOPT_POST, true);
  curl_setopt($ch, CURLOPT_HTTPHEADER,
    array('Content-Type: text/plain; charset=UTF-8',
          'Content-Length: ' . strlen($input)));
  curl_setopt($ch, CURLOPT_POSTFIELDS, $input);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $output = curl_exec($ch);
  print curl_getinfo($ch, CURLINFO_HTTP_CODE) . "\\n";
  print $output . "\\n";
  curl_close($ch);
  ?>

Perl examples
-------------

The following Perl examples use the `libwww-perl (LWP)`__ library.

__ libwww-perl_

To get identifier metadata, parse and decode it, and store it in a
hash, `%metadata`:hl1:\ :

.. parsed-literal::

  use LWP::UserAgent;

  $ua = LWP::UserAgent->new;
  $r = $ua->get("http://n2t.net/ezid/id/`identifier`:hl2:");
  if ($r->is_success) {
    ($statusline, $m) = split(/\\n/, $r->decoded_content, 2);
    %metadata = map { map { s/%([0-9A-F]{2})/pack("C", hex($1))/egi; $_ }
      split(/: /, $_, 2) } split(/\\n/, $m);
  } else {
    print $r->code, $r->decoded_content;
  }

To create an identifier, supplying initial metadata values from a
hash, `%metadata`:hl1:\ :

.. parsed-literal::

  use Encode;
  use \HTTP::Request::Common;
  use LWP::UserAgent;
  use URI::Escape;

  sub escape {
    (my $s = $_[0]) =~ s/([%:\\r\\n])/uri_escape($1)/eg;
    return $s;
  }

  %metadata = ( "_target" => "`url`:hl2:",
    "`element1`:hl2:" => "`value1`:hl2:",
    "`element2`:hl2:" => "`value2`:hl2:" );
  $ua = LWP::UserAgent->new;
  $ua->credentials("n2t.net:443", "EZID", "`username`:hl2:", \
  "`password`:hl2:");
  $r = $ua->request(PUT "\https://n2t.net:443/ezid/id/`identifier`:hl2:",
    "Content-Type" => "text/plain; charset=UTF-8",
    Content => encode("UTF-8", join("\\n",
      map { escape($_) . ": " . escape($metadata{$_}) } keys %metadata)));
  print $r->code, $r->decoded_content unless $r->is_success;

To mint an identifier (in this case supplying no metadata initially),
obtaining a new identifier, `$identifier`:hl1:\ :

.. parsed-literal::

  use \HTTP::Request::Common;
  use LWP::UserAgent;

  $ua = LWP::UserAgent->new;
  $ua->credentials("n2t.net:443", "EZID", "`username`:hl2:", \
  "`password`:hl2:");
  $r = $ua->request(POST "\https://n2t.net:443/ezid/shoulder/`shoulder`:hl2:",
    "Content-Type" => "text/plain; charset=UTF-8");
  if ($r->is_success) {
    $identifier = $r->decoded_content =~ m/success: ([^ ]*)/ && $1;
  } else {
    print $r->code, $r->decoded_content;
  }

To modify an identifier using values from a hash, `%metadata`:hl1:\ :

.. parsed-literal::

  use Encode;
  use \HTTP::Request::Common;
  use LWP::UserAgent;
  use URI::Escape;

  sub escape {
    (my $s = $_[0]) =~ s/([%:\\r\\n])/uri_escape($1)/eg;
    return $s;
  }

  %metadata = ( "_target" => "`url`:hl2:" );
  $ua = LWP::UserAgent->new;
  $ua->credentials("n2t.net:443", "EZID", "`username`:hl2:", \
  "`password`:hl2:");
  $r = $ua->request(POST "\https://n2t.net:443/ezid/id/`identifier`:hl2:",
    "Content-Type" => "text/plain; charset=UTF-8",
    Content => encode("UTF-8", join("\\n",
      map { escape($_) . ": " . escape($metadata{$_}) } keys %metadata)));
  print $r->code, $r->decoded_content unless $r->is_success;

cURL examples
-------------

The EZID API can be exercised using the cURL_ command line tool.  The
following examples assume metadata is UTF-8 encoded throughout.

To get identifier metadata, obtaining text formatted as described in
`Request & response bodies`_ above:

.. parsed-literal::

  curl \http://n2t.net/ezid/id/`identifier`:hl2:

To mint an identifier:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST \https://n2t.net/ezid/\
  shoulder/`shoulder`:hl2:

A single metadata element can be specified on the command line.  For
example, to mint an identifier and specify a target URL at the same
time:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary '_target: `url`:hl2:' \https://n2t.net/ezid/shoulder/\
  `shoulder`:hl2:

To specify more than one metadata element, the metadata must be placed
in a file that is formatted as described in `Request & response
bodies`_.  For example, to mint an identifier and upload metadata
contained in a file `metadata.txt`:hl1:\ :

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary @\ `metadata.txt`:hl2: \https://n2t.net/ezid/shoulder/\
  `shoulder`:hl2:

Creating an identifier is similar to minting one, except that the HTTP
method (-X option) is changed from POST to PUT and an identifier is
specified instead of a shoulder.  Here are the three examples above,
but now creating an identifier:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X PUT \https://n2t.net/ezid/id/\
  `identifier`:hl2:

  curl -u `username`:hl2::`password`:hl2: -X PUT -H 'Content-Type: text/plain'
    --data-binary '_target: `url`:hl2:' \https://n2t.net/ezid/id/\
  `identifier`:hl2:

  curl -u `username`:hl2::`password`:hl2: -X PUT -H 'Content-Type: text/plain'
    --data-binary @\ `metadata.txt`:hl2: \https://n2t.net/ezid/id/\
  `identifier`:hl2:

To modify identifier metadata:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary '_target: `url`:hl2:' \https://n2t.net/ezid/id/\
  `identifier`:hl2:

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary @\ `metadata.txt`:hl2: \https://n2t.net/ezid/id/\
  `identifier`:hl2:
