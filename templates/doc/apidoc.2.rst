.. role:: hl1
.. role:: hl2
.. role:: ext-icon

.. |lArr| unicode:: U+021D0 .. leftwards double arrow
.. |rArr| unicode:: U+021D2 .. rightwards double arrow
.. |X| unicode:: U+02713 .. check mark
.. |emdash| unicode:: U+2014 .. em dash

.. _ANVL: https://wiki.ucop.edu/display/Curation/Anvl
.. _Apache Commons Codec: http://commons.apache.org/codec/
.. _batch-download.sh:
   https://github.com/CDLUC3/ezid-client-tools/blob/master/batch-download.sh
.. _batch-register.py:
   https://github.com/CDLUC3/ezid-client-tools/blob/master/batch-register.py
.. _Comma-separated values (CSV):
   http://en.wikipedia.org/wiki/Comma-separated_values
.. _Contact us: /contact
.. _content negotiation: http://www.w3.org/Protocols/rfc2616/rfc2616-sec12.html
.. _cookielib: http://docs.python.org/library/cookielib.html
.. _CookieManager:
   http://download.oracle.com/javase/6/docs/api/java/net/CookieManager.html
.. _Crossref: http://www.crossref.org/
.. _Crossref Deposit Schema: http://help.crossref.org/deposit_schema
.. _curl: http://curl.haxx.se/
.. _DataCite: http://www.datacite.org/
.. _DataCite Metadata Scheme: http://schema.datacite.org/
.. _Dublin Core Metadata Element Set: http://dublincore.org/documents/dces/
.. _ERC: https://wiki.ucop.edu/display/Curation/ERC
.. _ezid3.py: https://github.com/CDLUC3/ezid-client-tools/blob/master/ezid3.py
.. _gzip: http://www.gzip.org/
.. _libwww-perl: http://search.cpan.org/dist/libwww-perl/
.. _N2T: https://n2t.net/
.. _OAI-PMH: http://www.openarchives.org/OAI/openarchivesprotocol.html
.. _percent-encoding: http://en.wikipedia.org/wiki/Percent-encoding
.. _REST-style: http://oreilly.com/catalog/9780596529260
.. _ZIP: https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT

The EZID API, Version 2
=======================

//BEGIN//

.. class:: smallfont

| **This version:** `SCHEME://HOSTNAME/doc/apidoc.2.html
  <SCHEME://HOSTNAME/doc/apidoc.2.html>`_
| **Latest version:** `SCHEME://HOSTNAME/doc/apidoc.2.html
  <SCHEME://HOSTNAME/doc/apidoc.2.html>`_
| **Previous version:** `SCHEME://HOSTNAME/doc/apidoc.1.html
  <SCHEME://HOSTNAME/doc/apidoc.1.html>`_

EZID (easy-eye-dee) provides an easy way to obtain, describe, and
manage long-term identifiers for digital objects.  It can be accessed
via a web User Interface (UI) and a web Application Programming
Interface (API).  A few account management functions can be accessed
from the UI only, but otherwise all of EZID's functionality is
available through the API.  This document describes Version 2 of the
EZID API.

Please send mail to the EZID discussion list (open to EZID customers
only) to ask questions or report problems:

  ezid-l@listserv.ucop.edu

Contents
--------

- Framework_
- `API vs. UI`_
- Authentication_
- `Request & response bodies`_
- `Error reporting`_
- `Operation: resolve identifier (EZID v3.1)`_
- `Operation: get identifier metadata (EZID v3.1)`_
- `Operation: get identifier metadata`_
- `Operation: create identifier`_
- `Operation: mint identifier`_
- `Operation: update identifier`_
- `Operation: create or update identifier`_
- `Operation: delete identifier`_
- `Suffix passthrough / prefix matching`_
- `Ownership model`_
- `Identifier status`_
- `Internal metadata`_
- `Metadata profiles`_

  - `Profile "erc"`_
  - `Profile "datacite"`_
  - `Profile "dc"`_
  - `Profile "crossref"`_

- `Metadata requirements & mapping`_
- `Crossref registration`_
- `Testing the API`_
- `Server status`_
- `Python command line tool`_
- `PHP examples`_
- `Perl examples`_
- `Java example`_
- `curl examples`_
- `Batch processing`_
- `Batch download`_

  - Overview_
  - `Download formats`_
  - Parameters_
  - `Using curl to request a download`_

- `OAI-PMH harvesting`_

Framework
---------

The EZID API is available from the base URL

  https://ezid.cdlib.org

Interaction is via REST-style_ `\ `:ext-icon: HTTP web services.  The
API's central design principle is to treat an identifier as a kind of
web resource.  Specifically, identifier `foo`:hl1: is represented as a
resource at URL \https://ezid.cdlib.org/id/`foo`:hl1:.  In this
document we will refer to this URL as the identifier's "EZID URL."  A
client manipulates an identifier by performing HTTP operations on its
EZID URL: PUT to create the identifier, GET to view it, and POST to
update it.

An identifier's EZID URL should not be confused with the identifier's
"URL form."  The former is used to manipulate the identifier, whereas
the latter is used to express the identifier as an embeddable
hyperlink that redirects to the identifier's target URL.  For DOI
identifiers:

.. class:: leftheaders

========== ====================================================
Identifier `doi:10.nnnn/suffix`:hl1:
URL form   \https://doi.org/`10.nnnn/suffix`:hl1:
EZID URL   \https://ezid.cdlib.org/id/`doi:10.nnnn/suffix`:hl1:
========== ====================================================

For ARK identifiers:

.. class:: leftheaders

========== ====================================================
Identifier `ark:/nnnnn/suffix`:hl1:
URL form   \http://n2t.net/`ark:/nnnnn/suffix`:hl1:
EZID URL   \https://ezid.cdlib.org/id/`ark:/nnnnn/suffix`:hl1:
========== ====================================================

For UUID identifiers:

.. class:: leftheaders

========== ====================================================
Identifier `uuid:suffix`:hl1:
URL form   \http://n2t.net/`uuid:suffix`:hl1:
EZID URL   \https://ezid.cdlib.org/id/`uuid:suffix`:hl1:
========== ====================================================

API vs. UI
----------

The EZID UI and API share some URLs (the base URL is the same for
both) but their behavior is different.  For example, in the API a GET
operation on an EZID URL returns client-parseable metadata (see
`Operation: get identifier metadata`_ below), but in the UI it returns
an HTML page.

To distinguish between the two interfaces EZID employs HTTP `content
negotiation`_ `\ `:ext-icon:.  If a request comes in with an HTTP
Accept header that expresses a preference for any form of HTML or XML,
the UI is invoked; otherwise, the API is invoked.  A preference for
the API can be made explicit by omitting any Accept header, or setting
the Accept header to something like "text/plain".  If using Java, it
will probably be necessary to override the default Accept header Java
sends as follows::

  import java.net.*;

  URL u = new URL("https://ezid.cdlib.org/...");
  URLConnection c = u.openConnection();
  c.setRequestProperty("Accept", "text/plain");
  c.connect();

Authentication
--------------

Most requests require authentication.  The EZID API supports two
methods of authentication:

1. **HTTP Basic authentication**.  With this method, the client
   supplies HTTP Basic authentication credentials on every request.
   The authentication realm is "EZID".  For example, credentials can
   be added manually in Python as follows:

   .. parsed-literal::

     import base64, urllib2
     r = urllib.request.Request("\https://ezid.cdlib.org/...")
     r.add_header("Authorization", "Basic " + \
     base64.b64encode("`username`:hl2::`password`:hl2:"))

   But most programming libraries provide higher-level support for
   authentication.  For example, Python provides HTTPBasicAuthHandler:

   .. parsed-literal::

     import urllib2
     h = urllib.request.HTTPBasicAuthHandler()
     h.add_password("EZID", "\https://ezid.cdlib.org/", "`username`:hl2:", \
     "`password`:hl2:")
     o = urllib.request.build_opener(h)
     o.open("\https://ezid.cdlib.org/...")

   The downside of using higher-level authentication mechanisms is
   that they often do not supply credentials initially, but only in
   response to a challenge from EZID, thus doubling the number of HTTP
   transactions.

   To manually provide credentials in Java, using `Apache Commons
   Codec`_ `\ `:ext-icon: to do the Base64 encoding:

   .. parsed-literal::

     import java.net.*;
     import org.apache.commons.codec.binary.*;

     URL u = new URL("\https://ezid.cdlib.org/...);
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

2. **One-time login**.  Perform a GET operation on
   \https://ezid.cdlib.org/login and supply HTTP Basic credentials as
   above.  In response, EZID returns a session cookie.  Subsequent
   requests can be made without authentication by supplying the
   session cookie in HTTP Cookie headers.  Here's an example
   interaction:

   .. parsed-literal::

     |rArr| GET /login HTTP/1.1
     |rArr| Host: ezid.cdlib.org
     |rArr| Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

     |lArr| HTTP/1.1 200 OK
     |lArr| Set-Cookie: sessionid=403a1ea3b03b74f663c1cd7fc877f495; expires...
     |lArr| Content-Type: text/plain; charset=UTF-8
     |lArr| Content-Length: 32
     |lArr|
     |lArr| success: session cookie returned

   In Python, cookies can be managed using cookielib_ `\ `:ext-icon:,
   or manually captured and set using code similar to the following:

   .. parsed-literal::

     import urllib2
     c = urllib.request.urlopen("\https://ezid.cdlib.org/login")
     `cookie`:hl2: = c.headers["Set-Cookie"].split(";")[0]
     ...
     r = urllib.request.Request("\https://ezid.cdlib.org/...")
     r.add_header("Cookie", `cookie`:hl2:)

   In Java, cookies can be manually captured and set using code
   analogous to the Python code above or, in Java 1.6 and newer,
   CookieManager_ `\ `:ext-icon: can be used to manage cookies.

   Perform a GET operation on \https://ezid.cdlib.org/logout to
   invalidate a session.

If authentication is required and credentials are either missing or
invalid, EZID returns a 401 HTTP status code and the status line
"error: unauthorized" (see `Error reporting`_ below).  If
authentication is successful but the request is still not authorized,
EZID returns a 403 HTTP status code and the status line "error:
forbidden".

Request & response bodies
-------------------------

Request and response bodies are used to transmit identifier metadata.
The HTTP content type for all bodies is "text/plain" using UTF-8
charset encoding.  In request bodies, if no charset encoding is
declared in the HTTP Content-Type header, it is assumed to be UTF-8.

EZID's data model for metadata is a dictionary of element name/value
pairs.  The dictionary is single-valued: an element name may not be
repeated.  Names and values are strings.  Leading and trailing
whitespace in names and values is not significant.  Neither element
names nor element values may be empty.  (When updating an identifier,
an uploaded empty value is treated as a command to delete the element
entirely.)

Metadata dictionaries are serialized using a subset of `A Name-Value
Language (ANVL)`__ `\ `:ext-icon: rules:

__ ANVL_

- One element name/value pair per line.

- Names separated from values by colons.

For example::

  who: Proust, Marcel
  what: Remembrance of Things Past
  when: 1922

In addition, two ANVL features may be used when uploading metadata to
EZID (but clients can safely assume that EZID will never use these
features when returning metadata):

- A line beginning with a number sign ("#", U+0023) is a comment and
  will be ignored.

- A line beginning with whitespace continues the previous line (the
  intervening line terminator and whitespace are converted to a single
  space).

For example:

.. parsed-literal ::

  # The following two elements are identical:
  who: Proust,
    Marcel
  who: Proust, Marcel

Care must be taken to escape structural characters that appear in
element names and values, specifically, line terminators (both
newlines ("\\n", U+000A) and carriage returns ("\\r", U+000D)) and, in
element names, colons (":", U+003A).  EZID employs `percent-encoding`_
`\ `:ext-icon: as the escaping mechanism, and thus percent signs ("%",
U+0025) must be escaped as well.  In Python, a dictionary of Unicode
metadata element names and values, `metadata`:hl1:, is serialized into
a UTF-8 encoded string, `anvl`:hl1:, with the following code:

.. parsed-literal::

  import re

  def escape (s):
    return re.sub("[%:\\r\\n]", lambda c: "%%%02X" % ord(c.group(0)), s)

  `anvl`:hl2: = "\\n".join("%s: %s" % (escape(name), escape(value)) for name,
    value in list(`metadata`:hl2:.items())).encode("UTF-8")

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

Error reporting
---------------

An error is indicated by both an HTTP status code and an error status
line of the form "error: `reason`:hl1:".  For example:

.. parsed-literal::

  |rArr| GET /id/ark:/99999/bogus HTTP/1.1
  |rArr| Host: ezid.cdlib.org

  |lArr| HTTP/1.1 400 BAD REQUEST
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 39
  |lArr|
  |lArr| error: bad request - no such identifier

Some programming libraries make it a little difficult to read the
content following an error status code.  For example, from Java, it is
necessary to explicitly switch between the input and error streams
based on the status code:

.. parsed-literal::

  java.net.HttpURLConnection c;
  java.io.InputStream s;
  ...
  if (c.getResponseCode() < 400) {
    s = c.getInputStream();
  } else {
    s = c.getErrorStream();
  }
  // read from s...


Operation: resolve identifier (EZID v3.1)
-----------------------------------------

EZID 3.1 and later supports identifier resolution, which is a service
that provides the location of a resource referenced by a persistent
identifier such as an ARK or DOI.

EZID forwards DOI identifier resolution to the ``doi.org`` service.

ARK identifier resolution is handled by finding the longest matching
identifier in EZID and redirecting the client to the ``location``
registered with the identifier.

The resolve identifier service is located at the EZID Base URL, and
is invoked using HTTP GET.

For example given the identifier ``ark:/87278/s63x8hrv``, a resolve
request can be made by sending a HTTP GET request to
``{BaseURL}/ark:/87278/s63x8hrv`` such as in the ``curl`` example
below:

.. parsed-literal::

    $ curl -v "SCHEME://HOSTNAME/ark:/87278/s63x8hrv"

    > GET /ark:/87278/s63x8hrv HTTP/1.1
    > Host: localhost:8000
    > User-Agent: curl/7.86.0
    > Accept: */*
    >
    < HTTP/1.1 302 Found
    < Date: Wed, 15 Mar 2023 13:32:40 GMT
    < Server: WSGIServer/0.2 CPython/3.9.5
    < Last-Modified: Tue, 15 Oct 2013 17:30:39 GMT
    < Content-Type: text/plain; charset=utf-8
    < Location: http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791
    < Vary: Accept-Language
    < Content-Language: en
    < Content-Length: 206
    <
    request_id: ark:/87278/s63x8hrv
    id: ark:/87278/s63x8hrv
    extra:
    location: http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791
    modified: 2013-10-15T17:30:39+00:00

The 302 status of the response indicates the client is to be redirected
to the URL listed in the ``Location:`` response header, in this case:
http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791. Note that
a brief body is included in the response to provide some minimal
metadata about the identifier. The properties are:

``request_id``
    The identifier in the resolve request URL.
``id``
    The matching identifier found in EZID.
``extra``
    Any additional characters in the ``request_id`` beyond the found ``id``.
``location``
    The registered location of the identifier target.
``modified``
    Time stmap indicating when the identifier was last modified.

For security reasons, this body is not normally accessible to a browser based
client, though a programmatic client may access this info by including a
non-standard header ``No-Redirect: true`` in the request. The default format
of the body is ANVL, however the metadata may also be serialized in JSON by
requesting that media type. For example:

.. parsed-literal::

    $ curl -v -H "No-Redirect: true" \\
        -H "Accept: application/json" \\
        "SCHEME://HOSTNAME/ark:/87278/s63x8hrv"

    > GET /ark:/87278/s63x8hrv HTTP/1.1
    > Host: localhost:8000
    > User-Agent: curl/7.86.0
    > Accept: application/json
    > No-redirect: true
    >
    < HTTP/1.1 200 OK
    < Date: Wed, 15 Mar 2023 13:54:01 GMT
    < Server: WSGIServer/0.2 CPython/3.9.5
    < Last-Modified: Tue, 15 Oct 2013 17:30:39 GMT
    < Location: http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791
    < Content-Type: application/json; charset=utf-8
    < Vary: Accept-Language
    < Content-Language: en
    < Content-Length: 201
    <
    {
      "request_id": "ark:/87278/s63x8hrv",
      "id": "ark:/87278/s63x8hrv",
      "extra": "",
      "location": "http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791",
      "modified": "2013-10-15T17:30:39Z"
    }

A live demo of the resolve operation is provided below. Enter an identifier, and click
"Resolve" to show the request and response.

.. raw:: html

   <input id="rinp_pid" type="text" size="80" placeholder="identifier" value="ark:/87278/s63x8hrv"></input>
   <span><input id="rcb_format" type="checkbox" checked="true" />
   <label for="rcb_format">As JSON</label></span>
   <span><input id="rcb_follow" type="checkbox" />
   <label for="rcb_format">Follow link</label></span>
   <br /><button id="rbt_pid">Resolve</button>
   <pre id="rpre_pid" style="white-space:pre-wrap">
   </pre>
   <script>
   function doInflection() {
     document.getElementById("rpre_pid").innerText = "Wait...";
     let pid = document.getElementById("rinp_pid").value;
     const url = `/${pid}`;
     if (document.getElementById("rcb_follow").checked) {
         document.getElementById("rpre_pid").innerText = "";
        window.location = url + "?_nocache=" + (new Date()).getTime();
        return;
     }
     let headers = {
        "Accept":"text/plain",
        "No-Redirect": "true"
     };
     let as_json = false;
     if (document.getElementById("rcb_format").checked) {
       as_json = true;
       headers["Accept"] = "application/json";
     }
     fetch(url, {
       "headers": headers,
       "cache": "no-cache"
     })
     .then((response) => {
       let msg = `Request:\nGET ${response.url}\n\nResponse:\nstatus: ${response.status}\n`;
       if (as_json) {
         response.json()
         .then((data) => {
           document.getElementById("rpre_pid").innerText = msg + JSON.stringify(data,null,2);
        })
        .catch((err) => {
            document.getElementById("rpre_pid").innerText = `${msg}Error:\n${err}`;
        });
       } else {
         response.text()
         .then((text) => {
            document.getElementById("rpre_pid").innerText = msg + text;
         });
       }
     })
     .catch((response) => {
        alert(response.status);
    });
   }
   document.getElementById("rbt_pid").onclick = doInflection;
   </script>



Operation: get identifier metadata (EZID v3.1)
----------------------------------------------

As part of the identifier resolution support for EZID version 3.1,
"inflection" as described in the `ARK documentation`_ is implemented
with additional support for JSON representation when requested by
content negotiation.

An inflection request is invoked by appending "``??``" or "``?info``" to
the end of a GET request URL to the EZID ``resolve`` service endpoint.

For example given the identifier ``ark:/87278/s63x8hrv``, an inflection
request can be made by sending a HTTP GET request to::

    {BaseURL}/ark:/87278/s63x8hrv?info

such as in the ``curl`` example below:

.. parsed-literal::

    $ curl "SCHEME://HOSTNAME/ark:/87278/s63x8hrv?info"

    erc.what: Sophonisba : or, Hannibal's overthrow
    erc.note: CONTENTdm to Rosetta workflow
    _owner: uofutah
    _ownergroup: uofutah
    _profile: erc
    _target: http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791
    _status: public
    _export: yes
    id created: 2013.10.15_10:30:39
    id updated: 2013.10.15_10:30:39

The default response is in ANVL, though a JSON response may be requested
through content negotiation, for example:

.. parsed-literal::

    $ curl -H "Accept: application/json" \\
        "SCHEME://HOSTNAME/ark:/87278/s63x8hrv?info"
    {
      "erc": {
        "what": "Sophonisba : or, Hannibal's overthrow",
        "note": "CONTENTdm to Rosetta workflow"
      },
      "_owner": "uofutah",
      "_ownergroup": "uofutah",
      "_profile": "erc",
      "_target": "http://content.lib.utah.edu/cdm/ref/collection/cjt/id/4791",
      "_status": "public",
      "_export": "yes",
      "id created": "2013-10-15T10:30:39",
      "id updated": "2013-10-15T10:30:39"
    }

Identifier records may use different metadata profiles. The example above uses the ``erc``
profile (indicated by the ``_profile`` key value and the corresponding ``erc`` key value
providing the metadata.

Similarly, Dublin Core (``dc``), DataCite (``datacite``), schema.org (``schema_org``),
and other profiles may be used. A DataCite example (truncated here for brevity):

.. parsed-literal::

    $ curl -H "Accept: application/json" \\
        "SCHEME://HOSTNAME/ark:/13030/m5qz2bmh?info"

    {
      "datacite": "<?xml version=\"1.0\"?>\n<resource xmlns=\"http://datacite.org/schema/kernel-3\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd\"><identifier identifierType=\"ARK\">13030/m5qz2bmh</identifier><creators><creator><creatorName>Zhang, Yu</creatorName></creator></creators><titles><title>Patterns of age-related water diffusion changes in human brain by concordance and discordance analysis.</title></titles><publisher>University of California, San Francisco</publisher><publicationYear>2012</publicationYear><contributors><contributor contributorType=\"ResearchGroup\"><contributorName>UCSF Center for Imaging of Neurodegenerative Diseases</contributorName></contributor></contributors><resourceType resourceTypeGeneral=\"Dataset\">Dataset</resourceType><descriptions><description descriptionType=\"Abstract\">In diffusion tensor imaging (DTI), interpreting changes in terms ...</description></descriptions></resource>",
      "mrt.creator": "ucsf_datashare",
      "erc": {
        "who": "Zhang, Yu",
        "what": "Patterns of age-related water diffusion changes in human brain by concordance and discordance analysis.",
        "where": "ark:/13030/m5qz2bmh"
      },
      "_owner": "merritt",
      "_ownergroup": "merritt",
      "_profile": "datacite",
      "_target": "http://merritt.cdlib.org/m/ark%3a%2fb7272%2fq67p8w9z",
      "_status": "public",
      "_export": "yes",
      "id created": "2012-07-09T08:33:53",
      "id updated": "2017-01-23T16:45:09"
    }

The JSON format is convenient for further processing with tools such a ``jq`` to extract the
metadata value, for example (truncated here for brevity):

.. parsed-literal::

    $ curl -H "Accept: application/json" \\
        "SCHEME://HOSTNAME/ark:/13030/m5qz2bmh?info" | jq -r '.datacite' | xml fo

    <?xml version="1.0"?>
    <resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd">
      <identifier identifierType="ARK">13030/m5qz2bmh</identifier>
      <creators>
        <creator>
          <creatorName>Zhang, Yu</creatorName>
        </creator>
      </creators>
      <titles>
        <title>Patterns of age-related water diffusion changes in human brain by concordance and discordance analysis.</title>
      </titles>
      <publisher>University of California, San Francisco</publisher>
      <publicationYear>2012</publicationYear>
      <contributors>
        <contributor contributorType="ResearchGroup">
          <contributorName>UCSF Center for Imaging of Neurodegenerative Diseases</contributorName>
        </contributor>
      </contributors>
      <resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
      <descriptions>
        <description descriptionType="Abstract">In diffusion tensor imaging (DTI), interpreting ...</description>
      </descriptions>
    </resource>

If an exact match for an identifier is not found then matching shoulders are presented (truncated for brevity):

.. parsed-literal::

    $ curl -H "Accept: application/json" \\
        "SCHEME://HOSTNAME/ark:/13030/nonexistent?info"

    {
      "ark:/13030/p8": {
        "erc.who": "Open Access Policy",
        "erc.what": "ARK",
        "erc.when": "2015-04-06"
      },
      "ark:/13030/fq": {
        "erc.who": "DPR Legacy",
        "erc.what": "ARK",
        "erc.when": "2011-12-13"
      },
      "ark:/13030/ft": {
        "erc.who": "Online Archive of California (OAC) Legacy ft",
        "erc.what": "ARK",
        "erc.when": "2007-06-01"
      },
      ...


A live demo of the inflection operation is provided below. Enter an identifier, and click
"Get Metadata" to show the request and response.

.. raw:: html

   <input id="inp_pid" type="text" size="80" placeholder="identifier" value="ark:/87278/s63x8hrv"></input>
   <span><input id="cb_format" type="checkbox" checked="true" />
   <label for="cb_format">As JSON</label></span>
   <br /><button id="bt_pid">Get Metadata</button>
   <pre id="pre_pid" style="white-space:pre-wrap">
   </pre>
   <script>
   function doInflection() {
     document.getElementById("pre_pid").innerText = "Wait...";
     let pid = document.getElementById("inp_pid").value;
     const url = `/${pid}?info`
     let headers = {"Accept":"text/plain"};
     let as_json = false;
     if (document.getElementById("cb_format").checked) {
       as_json = true;
       headers = {"Accept":"application/json"};
     }
     fetch(url, {
       "headers": headers,
       "cache": "no-cache"
     })
     .then((response) => {
       let msg = `Request:\nGET ${response.url}\n\nResponse:\nstatus: ${response.status}\n`;
       if (as_json) {
         response.json()
         .then((data) => {
           document.getElementById("pre_pid").innerText = msg + JSON.stringify(data,null,2);
        })
        .catch((err) => {
            document.getElementById("pre_pid").innerText = `${msg}Error:\n${err}`;
        });
       } else {
         response.text()
         .then((text) => {
            document.getElementById("pre_pid").innerText = msg + text;
         });
       }
     })
     .catch((response) => {
        alert(response.status);
    });
   }
   document.getElementById("bt_pid").onclick = doInflection;
   </script>


.. _ARK documentation: https://arks.org/about/ark-features/


Operation: get identifier metadata
----------------------------------

Metadata can be retrieved for any existing identifier; no
authentication is required.  Simply issue a GET request to the
identifier's EZID URL.  Here is a sample interaction:

.. parsed-literal::

  |rArr| GET /id/ark:/99999/fk4cz3dh0 HTTP/1.1
  |rArr| Host: ezid.cdlib.org

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
success (see `Error reporting`_ above), the remainder of the status
line echoes the canonical form of the requested identifier.

The remaining lines are metadata element name/value pairs serialized
per ANVL rules; see `Request & response bodies`_ above.  The order of
elements is undefined.  Element names beginning with an underscore
("_", U+005F) are reserved for use by EZID; their meanings are
described in `Internal metadata`_ below.  Some elements may be drawn
from citation metadata standards; see `Metadata profiles`_ below.

EZID also supports a more flexible identifier lookup operation; see
`Suffix passthrough / prefix matching`_ below.


Operation: create identifier
----------------------------

An identifier can be "created" by sending a PUT request to the
identifier's EZID URL.  Here, identifier creation means establishing a
record of the identifier in EZID (to be successful, no such record can
already exist).  Authentication is required, and the user must have
permission to create identifiers in the namespace (or "shoulder")
named by the identifier's prefix.  Users can view the namespaces
available to them by visiting the EZID UI and navigating to the Create
ID tab.  For example, if the user has permission to create identifiers
in the general EZID ARK (ark:/13030/c7) namespace, then the user may
create identifiers beginning with "ark:/13030/c7".

A request body is optional; if present, it defines the identifier's
starting metadata.  There are no restrictions on what metadata
elements can be submitted, but a convention has been established for
naming metadata elements, and EZID has built-in support for certain
sets of metadata elements; see `Metadata profiles`_ below.  A few of
the internal EZID metadata elements may be set; see `Internal
metadata`_ below.

Here's a sample interaction creating an ARK identifier:

.. parsed-literal::

  |rArr| PUT /id/ark:/99999/fk4test HTTP/1.1
  |rArr| Host: ezid.cdlib.org
  |rArr| Content-Type: text/plain; charset=UTF-8
  |rArr| Content-Length: 30
  |rArr|
  |rArr| _target: \http://www.cdlib.org/

  |lArr| HTTP/1.1 201 CREATED
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 27
  |lArr|
  |lArr| success: ark:/99999/fk4test

The return is a status line.  The normalized form of the identifier is
returned as shown above, but if a DOI was created, the status line
also includes, separated by a pipe character ("|", U+007C), the
identifier's "shadow ARK" (an ARK identifier that is an alias for the
created identifier; deprecated).  Note that different identifier
schemes have different normalization rules (e.g., DOIs are normalized
to all uppercase letters).  Here's a sample interaction creating a DOI
identifier:

.. parsed-literal::

  |rArr| PUT /id/doi:10.9999/test HTTP/1.1
  |rArr| Host: ezid.cdlib.org

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
\https://ezid.cdlib.org/shoulder/`shoulder`:hl1: where `shoulder`:hl1:
is the desired namespace.  For example:

.. parsed-literal::

  |rArr| POST /shoulder/`ark:/13030/c7`:hl2: HTTP/1.1
  |rArr| Host: ezid.cdlib.org
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
Create ID tab.  The request and response bodies are identical.

EZID automatically embeds the newly-minted identifier in certain types
of uploaded metadata.  See `Metadata profiles`_ below for when this is
performed.  Additionally, EZID replaces all occurrences of the string
"${identifier}" in the target URL with the newly-minted identifier.

Operation: update identifier
----------------------------

An identifier's metadata can be updated by sending a POST request to
the identifier's EZID URL.  Authentication is required; only the
identifier's owner and certain other users may update the identifier
(see `Ownership model`_ below).

Metadata elements are operated on individually.  If the identifier
already has a value for a metadata element included in the request
body, the value is overwritten, otherwise the element and its value
are added.  Only a few of the reserved EZID metadata elements may be
updated; see `Internal metadata`_ below.  Here's a sample interaction:

.. parsed-literal::

  |rArr| POST /id/ark:/99999/fk4cz3dh0 HTTP/1.1
  |rArr| Host: ezid.cdlib.org
  |rArr| Content-Type: text/plain; charset=UTF-8
  |rArr| Content-Length: 30
  |rArr|
  |rArr| _target: \http://www.cdlib.org/

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 29
  |lArr|
  |lArr| success: ark:/99999/fk4cz3dh0

The return is a status line.  Assuming success (see `Error reporting`_
above), the remainder of the status line echoes the canonical form of
the identifier in question.

To delete a metadata element, set its value to the empty string.

Operation: create or update identifier
--------------------------------------

An identifier can be created or updated in one interaction; the
specific operation performed will depend on whether the identifier
already exists or not.  To do so, issue a create operation as
described under `Operation: create identifier`_ above, but add an
update_if_exists=yes URL query parameter to the PUT request.  EZID
returns a 201 HTTP status code if the identifier was created or a 200
HTTP status code if the identifier already existed and was
successfully updated.  The response body is a status line as described
previously.  Here's a sample request:

.. parsed-literal::

  |rArr| PUT /id/ark:/99999/fk4test?update_if_exists=yes HTTP/1.1
  |rArr| Host: ezid.cdlib.org
  |rArr| Content-Type: text/plain; charset=UTF-8
  |rArr| Content-Length: 30
  |rArr|
  |rArr| _target: \http://www.cdlib.org/

Operation: delete identifier
----------------------------

An identifier that has only been reserved can be deleted by sending a
DELETE request to the identifier's EZID URL.  We emphasize that only
*reserved* identifiers may be deleted; see `Identifier status`_ below.
Authentication is required; only the identifier's owner and certain
other users may delete the identifier (see `Ownership model`_ below).

Here's a sample interaction:

.. parsed-literal::

  |rArr| DELETE /id/ark:/99999/fk4cz3dh0 HTTP/1.1
  |rArr| Host: ezid.cdlib.org

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 29
  |lArr|
  |lArr| success: ark:/99999/fk4cz3dh0

The return is a status line.  Assuming success (see `Error reporting`_
above), the remainder of the status line echoes the canonical form of
the identifier just deleted.

Suffix passthrough / prefix matching
------------------------------------

The N2T_ `\ `:ext-icon: resolver\ |emdash|\ the principal resolver for
ARK identifiers\ |emdash|\ supports "suffix passthrough," a capability
that allows an identifier to be resolved even if it has not been
explicitly registered, so long as some prefix of the identifier has.
In such a case, N2T locates the longest matching prefix (the "root"
identifier) and appends the extra characters in the supplied
identifier (the "suffix") to the root identifier's target URL before
redirecting.  For example, if identifier ark:/99999/fk4/root has been
registered with EZID and has target URL http://www.cdlib.org, then N2T
resolves ark:/99999/fk4/root\ `/andmore`:hl1: to
\http://www.cdlib.org\ `/andmore`:hl1:.  The capability is so-named
because the suffix is effectively "passed through" to the receiving
server.

EZID supports a similar capability.  If a request to view identifier
metadata (see `Operation: get identifier metadata`_ above) is
accompanied by a prefix_match=yes URL query parameter, then EZID
returns metadata for the longest matching identifier (if there is
one).  If an identifier other than the one requested is returned, the
status line includes a note to that effect.  Here is a sample
interaction that continues the previous example:

.. parsed-literal::

  |rArr| GET /id/ark:/99999/fk4/root/andmore?prefix_match=yes HTTP/1.1
  |rArr| Host: ezid.cdlib.org

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 244
  |lArr|
  |lArr| success: ark:/99999/fk4/root in_lieu_of ark:/99999/fk4/root/andmore
  |lArr| _target: \http://www.cdlib.org
  |lArr| ...

Ownership model
---------------

EZID maintains ownership information about identifiers and uses that
information to enforce access control.

The ownership model employed by EZID is hierarchical: each identifier
has one owner, which is an EZID user; each EZID user belongs to one
group; and each group belongs to one realm.  Permission to create
identifiers is governed by the namespaces (or "shoulders") that have
been assigned to a user by an EZID administrator.  But once created,
permission to subsequently update an identifier is governed solely by
the identifier's ownership.  An identifier may be updated only by its
owner, with two exceptions:

- **Proxies**.  A user (the "proxied user") may name another EZID user
  as its "proxy".  A user may have multiple proxies, and a user may be
  a proxy for multiple other users.  Generally speaking, a proxy may
  operate on behalf of the proxied user.  Specifically, a proxy may:

  - create identifiers under any shoulder available to the proxied
    user;

  - create identifiers owned by the proxied user, by setting the
    "_owner" reserved metadata element (see `Internal metadata`_
    below);

  - update existing identifiers owned by the proxied user;

  - change the ownership of identifiers owned by the proxied user to
    itself or to any other user on whose behalf the proxy may operate,
    and vice versa;

  - search over the proxied user's identifiers;

  - view statistics regarding the proxied user's identifiers; and

  - download the proxied user's identifiers (see `Batch download`_
    below).

- **Group administrators**.  An EZID user may be appointed an
  "administrator" of its group.  A group may have zero, one, or more
  than one administrator.  Generally speaking, a group administrator
  may operate on behalf of any other member of the group;
  equivalently, a group administrator is a proxy for the group's
  members, and as such its specific abilities include the list given
  above.  In addition, a group administrator may:

  - search over all the group's identifiers;

  - view group-level identifier statistics; and

  - download all the group's identifiers.

Proxies can be set up and managed in the EZID UI, Account Settings
tab.  Group administrators can be appointed only by an EZID
administrator.

Proxies and group administrators are independent concepts.  A group
administrator may also be a proxy, and may also have proxies.

Identifier status
-----------------

Each identifier in EZID has a status.  The status is recorded as the
value of the "_status" reserved metadata element (see `Internal
metadata`_ below) and may be one of:

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

* A public identifier may be marked as unavailable.  At this time the
  identifier will be removed from resolvers and external services to
  the extent possible.

* An unavailable identifier may be returned to public status.  At this
  time the identifier will be re-registered with resolvers and other
  external services.

Internal metadata
-----------------

Metadata element names beginning with an underscore ("_", U+005F) are
reserved for use by EZID.  The reserved elements below are returned by
the EZID API, and have the following meanings.  A check mark in the
first column indicates the element is updatable by clients.

  === =========== ============================================ ================
  |X| Element     Definition                                   Example
  === =========== ============================================ ================
  |X| _owner      The identifier's owner.  Only certain        jsmith
                  ownership changes are permitted; see
                  `Ownership model`_ above.
  \   _ownergroup The identifier's owning group, which is      ucla
                  currently restricted to be the identifier's
                  owner's group.
  \   _created    The time the identifier was created          1300812337
                  expressed as a Unix timestamp.
  \   _updated    The time the identifier was last updated     1300913550
                  expressed as a Unix timestamp.
  |X| _target     The identifier's target URL.  Defaults to the identifier's
                  EZID URL.  That is, the default target URL for identifier
                  `foo`:hl1: is the self-referential URL
                  \https://ezid.cdlib.org/id/`foo`:hl1:.  Note that creating or
                  updating the target URL of a DOI identifier may take up to
                  30 minutes to take effect in the Handle System.
  --- ----------- -------------------------------------------------------------
  |X| _profile    The identifier's preferred metadata profile  erc
                  (see `Metadata profiles`_ next).
  |X| _status     The identifier's status (see                 unavailable |
                  `Identifier status`_ above).                 withdrawn by
                                                               author
  |X| _export     Determines if the identifier is publicized   yes
                  by exporting it to external indexing and
                  harvesting services.  Must be "yes" or "no";
                  defaults to "yes".
  \   _datacenter DataCite DOIs only.  The datacenter at which CDL.CDL
                  the identifier is registered (or will be
                  registered, in the case of a reserved
                  identifier).
  |X| _crossref   If returned, indicates that the identifier   yes |
                  is registered with Crossref (or, in the case successfully
                  of a reserved identifier, will be            registered
                  registered), and also indicates the status
                  of the registration process.  When setting,
                  must be set to "yes".  See
                  `Crossref registration`_ below for more
                  information.
  === =========== ============================================ ================

Metadata profiles
-----------------

EZID allows "citation metadata" to be stored with an identifier, i.e.,
metadata that describes the object referenced by the identifier or
that otherwise gives the meaning of the identifier.  In certain cases
certain metadata elements are required to be present; see `Metadata
requirements & mapping`_ below.  This section describes only the
general structure and naming of citation metadata in EZID.

EZID supports several citation metadata "profiles," or standard sets
of citation metadata elements.  By convention, a metadata profile is
referred to using a simple, lowercase name, e.g., "erc", and elements
belonging to that profile are referred to using the syntax
"`profile`:hl1:.\ `element`:hl1:", e.g., "erc.who".

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

.. _Profile "erc":

1. **Profile "erc"**.  These elements are drawn from `Kernel Metadata
   and Electronic Resource Citations (ERCs)`__ `\ `:ext-icon:.  This
   profile aims at universal citations: any kind of object (digital,
   physical, abstract) or agent (person, group, software, satellite)
   for any purpose (research, education, entertainment,
   administration), any subject focus (oceanography, sales, religion,
   archiving), and any medium (television, newspaper, database, book).
   This is the default profile for ARK and UUID identifiers.

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

   As a special case, an entire ANVL_ `\ `:ext-icon: document
   containing ERC metadata may be bound to the metadata element "erc".
   Care should be taken to escape line terminators in the document (as
   is true for all metadata element values; see `Request & response
   bodies`_ above).  For example, the ANVL document::

     who: Proust, Marcel
     what: Remembrance of Things Past

   would be expressed as the single value::

     erc: who: Proust, Marcel%0Awhat: Remembrance of Things Past

.. _Profile "datacite":

2. **Profile "datacite"**.  These elements are drawn from the
   `DataCite Metadata Scheme for the Publication and Citation of
   Research Data`__ `\ `:ext-icon:.  This is the default profile for
   DOI identifiers.

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

                            Separate multiple names with ";".
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
   datacite.resourcetype    The general type and, optionally, specific
                            type of the data.  The general type must
                            be one of the controlled vocabulary terms
                            defined in the DataCite Metadata Scheme:

                            - Audiovisual
                            - Collection
                            - Dataset
                            - Event
                            - Image
                            - InteractiveResource
                            - Model
                            - PhysicalObject
                            - Service
                            - Software
                            - Sound
                            - Text
                            - Workflow
                            - Other

                            Specific types are unconstrained.  If a
                            specific type is given, it must be
                            separated from the general type by a
                            forward slash ("/"), as in:

                            - Image/Photograph
   ======================== ===========================================

   Alternatively, an entire XML document adhering to the DataCite
   Metadata Scheme schema may be bound to the metadata element
   "datacite".  Note that EZID sets the identifier embedded in the
   document to the identifier being operated on; thus it need not be
   specified by the client.  The <identifier> element must still be
   included in the document, though, so the XML document may resemble:

   .. parsed-literal::

     <?xml version="1.0"?>
     <resource xmlns="\http://datacite.org/schema/kernel-4"
       xmlns:xsi="\http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="...">
       <identifier identifierType="DOI">(:tba)</identifier>
       ...
     </resource>

   If an XML document is bound to a non-DOI identifier then, in an
   extension to the DataCite schema, the identifier type in the
   document must be set to "ARK" or "UUID" as appropriate.

   Care should be taken to escape line terminators and percent signs
   in the document (as is true for all metadata element values; see
   `Request & response bodies`_ above).  Once properly escaped, the
   uploaded metadata will resemble:

   .. parsed-literal::

     datacite: <?xml version="1.0"?>%0A<resource...

.. _Profile "dc":

3. **Profile "dc"**.  These elements are drawn from the `Dublin Core
   Metadata Element Set`_ `\ `:ext-icon:.

..

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
   dc.type      The nature or genre of the resource.  Recommended best
                practice is to use a term from the DCMI Type
                Vocabulary:

                - Collection
                - Dataset
                - Event
                - Image
                - InteractiveResource
                - MovingImage
                - PhysicalObject
                - Service
                - Software
                - Sound
                - StillImage
                - Text
   ============ =======================================================

.. _Profile "crossref":

4. **Profile "crossref"**.  This profile consists of a single element,
"crossref", whose value is Crossref deposit metadata (an XML
document).  Care should be taken to escape line terminators and
percent signs in the document (as is true for all metadata element
values; see `Request & response bodies`_ above).  See `Crossref
registration`_ below for more information on usage of this profile and
element.

Metadata requirements & mapping
-------------------------------

DOI identifiers must satisfy specific metadata requirements.  A
DataCite DOI created by EZID must have title, creator, publisher, and
publication year metadata any time its status is not reserved (see
`Identifier status`_ above).  A Crossref DOI must have Crossref
metadata at all times (see `Crossref registration`_ below), though the
metadata need not be complete if the identifier is reserved.  Other
than that, EZID imposes no requirements on the presence or form of
citation metadata, but uploading at least minimal citation metadata to
EZID is strongly encouraged in all cases to record the identifier's
meaning and to facilitate its long-term maintenance.  Regardless of
the metadata profile used, population of the "datacite.resourcetype"
element is encouraged to support broad categorization of identifiers.

To satisfy the aforementioned DataCite DOI metadata requirements, EZID
looks in order for:

1. DataCite XML metadata bound to the "datacite" element;
2. Individual elements from the "datacite" profile as described in
   `Profile "datacite"`_ ("datacite.title", etc.); and lastly
3. Elements from the identifier's preferred metadata profile (see
   `Metadata profiles`_ above) that EZID is able to map to DataCite
   equivalents.  For example, if the preferred profile is "erc", then
   EZID will map element "erc.who" to "datacite.creator".

If no meaningful value is available for a required element, clients
are encouraged to supply a standard machine-readable code drawn from
the `Kernel Metadata and Electronic Resource Citations (ERCs)`__
`\ `:ext-icon: specification.  These codes have the common syntactic
form "(:`code`:hl1:)" and include:

__ ERC_

  ======= ================================================
  Code    Definition
  ======= ================================================
  (:unac) temporarily inaccessible
  (:unal) unallowed; intentionally suppressed
  (:unap) not applicable; makes no sense
  (:unas) unassigned (e.g., untitled)
  (:unav) unavailable; possibly unknown
  (:unkn) known to be unknown (e.g., anonymous)
  (:none) never had a value, never will
  (:null) explicitly and meaningfully empty
  (:tba)  to be assigned or announced later
  (:etal) too numerous to list (et alia)
  (:at)   the real value is at the given URL or identifier
  ======= ================================================

A code may optionally be followed by the code's human-readable
equivalent or a more specific description, as in:

.. parsed-literal::

  who: (:unkn) anonymous donor

Crossref registration
---------------------

A DOI identifier may be registered with either the `Crossref`_ `\
`:ext-icon: or the `DataCite`_ `\ `:ext-icon: registration agency.
The choice of registration agency is not selectable, but is entirely
determined by the identifier's shoulder.  This section discusses
registration with Crossref.

Once registered, an identifier cannot be removed from Crossref.  If
the identifier's status is set to unavailable (recall `Identifier
status`_, above), EZID will prepend "WITHDRAWN" to the title of the
resource associated with the identifier, but the identifier remains in
Crossref's systems.

Registering an identifier with Crossref requires three steps:

1. Optionally set the "_crossref" reserved metadata element to "yes".
2. Supply Crossref deposit metadata as the value of the "crossref"
   element.
3. Set the "_profile" reserved metadata element to "crossref" to be
   able to view the metadata in the EZID UI.

These steps are discussed in more detail next.

Crossref registration is asynchronous.  Registration is initiated by a
create, mint, or update identifier request, when the identifier's
status is public.  Setting the "_crossref" reserved metadata element
to "yes" in the request is optional.  In responses, the "_crossref"
element is always returned and has the value "yes" followed by a pipe
character ("|", U+007C) followed by the status of the registration,
e.g., "yes | registration in progress" or "yes | successfully
registered".  The status of the registration is updated automatically
by EZID and may be polled by the client.  If a warning or error
occurred during registration, the status is followed by another pipe
character and the message received from Crossref, e.g., "yes |
registration failure | xml error...".  Warnings and errors may also be
viewed in the EZID UI and may also be emailed to a specified mailbox.
Warnings and errors can be removed only by submitting new metadata and
re-registering identifiers.

Crossref deposit metadata should adhere to the `Crossref Deposit
Schema`_ `\ `:ext-icon:, version 4.3.0 or later.  The metadata should
consist of the immediate child element of a <body> element, i.e., one
of the following elements:

- <journal>
- <book>
- <conference>
- <sa_component>
- <dissertation>
- <report-paper>
- <standard>
- <database>

(If an outer element such as <doi_batch> or <body> is nevertheless
supplied, it will be stripped off.)

Although the Crossref deposit schema is quite flexible, and supports
batch operations, EZID requires that the deposit metadata specify a
single DOI identifier, i.e., a single <doi_data> element.  This
element should contain <doi> and <resource> subelements, which may be
left empty.  EZID replaces the contents of the <doi> element (if any)
with the identifier in question and the contents of the <resource>
element with the target URL.  Here is an abridged example of deposit
metadata:

.. parsed-literal::

  <?xml version="1.0"?>
  <book xmlns="\http://www.crossref.org/schema/4.3.4"
    xmlns:xsi="\http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="\http://www.crossref.org/schema/4.3.4
    \http://www.crossref.org/schema/deposit/crossref4.3.4.xsd"
    book_type="monograph">
    <book_metadata>
      <contributors>
        <person_name contributor_role="author" sequence="first">
          <given_name>Marcel</given_name>
          <surname>Proust</surname>
        </person_name>
      </contributors>
      <titles>
        <title>Remembrance of Things Past</title>
      </titles>
      ...
      <doi_data>
        <doi>(:tba)</doi>
        <resource>(:tba)</resource>
      </doi_data>
    </book_metadata>
  </book>

In supplying an XML document as the value of element "crossref", care
should be taken to escape line terminators and percent signs in the
document (as is true for all metadata element values; see `Request &
response bodies`_ above).

If the identifier's preferred metadata profile is "crossref", EZID
automatically creates a DataCite Metadata Scheme record from the
Crossref deposit metadata for display and search purposes.  Where
conversion values are missing (e.g., a journal does not have a
creator) EZID supplies the code "(:unav)".  This automatic conversion
can be overriden by supplying an entire DataCite Metadata Scheme XML
record as the value of the "datacite" element (see `Profile
"datacite"`_ above).  Additionally, individual DataCite elements
(e.g., "datacite.title") may be specified to override selected
portions of the automatic conversion.

Putting it all together, uploaded metadata in a Crossref registration
request will resemble:

.. parsed-literal::

  _crossref: yes
  _profile: crossref
  _target: \http://...
  crossref: <?xml version="1.0"?>%0A<book...

Testing the API
---------------

EZID provides three namespaces (or "shoulders") for testing purposes:
ark:/99999/fk4 for ARK identifiers, doi:10.5072/FK2 for DataCite DOI
identifiers, and doi:10.15697/ for Crossref DOI identifiers.
Identifiers in these namespaces are termed "test identifiers."  They
are ordinary long-term identifiers in almost all respects, except that
EZID deletes them after 2 weeks.

Test ARK identifiers resolve just as real ARK identifiers do through
the N2T_ resolver, but test DOI identifiers do not resolve and do not
appear in any DataCite or Crossref systems.

All user accounts are permitted to create test identifiers.  EZID also
provides an "apitest" account that is permitted to create only test
identifiers.  `Contact us`_ for the password for this account.
Additionally, please `contact us`_ before embarking on any large-scale
testing, specifically, before creating more than 10,000 test
identifiers.

Test identifiers and reserved identifiers are orthogonal concepts.  A
test identifier has a limited lifetime and is deleted by EZID when it
expires.  A reserved identifier may be deleted by the owner while
still in its reserved state, but once made public, is permanent.  As
evidence of this orthogonality, it is possible to create reserved test
identifiers.

Server status
-------------

The status of the EZID server can be probed by issuing a GET request
to the URL \https://ezid.cdlib.org/status.  If the server is up the
response will resemble the following:

.. parsed-literal::

  |rArr| GET /status HTTP/1.1
  |rArr| Host: ezid.cdlib.org

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 19
  |lArr|
  |lArr| success: EZID is up

Python command line tool
------------------------

ezid3.py_ `\ `:ext-icon: is a command line tool, written in Python,
that is capable of exercising all API functions.  It serves as an
example of how to use the API from Python, but it's also useful in its
own right as an easy, scriptable means of accessing EZID
functionality.  The general usage is:

.. parsed-literal::

  % ezid3.py `credentials`:hl2: `operation`:hl2: `[arguments...]`:hl2:

Run the tool with no command line arguments for a complete usage
statement; additional documentation is in the source code.  To give a
flavor of the tool's usage and capabilities here, a few examples
follow.

To mint a test ARK identifier and supply initial metadata:

.. parsed-literal::

  % ezid3.py `username`:hl2::`password`:hl2: mint ark:/99999/fk4 erc.who \
  'Proust, Marcel' \\
      erc.what 'Remembrance of Things Past' erc.when 1922
  success: ark:/99999/fk4gt78tq

To get identifier metadata:

.. parsed-literal::

  % ezid3.py -dt - view ark:/99999/fk4gt78tq
  success: ark:/99999/fk4gt78tq
  _created: 2013-05-17T18:17:14
  _export: yes
  _owner: `user`:hl2:
  _ownergroup: `group`:hl2:
  _profile: erc
  _status: public
  _target: \https://ezid.cdlib.org/id/ark:/99999/fk4gt78tq
  _updated: 2013-05-17T18:17:14
  erc.what: Remembrance of Things Past
  erc.when: 1922
  erc.who: Proust, Marcel

The tool provides two mechanisms in addition to the command line for
supplying metadata.  If a metadata element name is an at-sign ("@",
U+0040), the subsequent value is treated as a filename and metadata
elements are read from the named ANVL-formatted file.  For example, if
file metadata.txt contains::

  erc.who: Proust, Marcel
  erc.what: Remembrance of Things Past
  erc.when: 1922

Then a test ARK identifier with that metadata can be minted by
invoking:

.. parsed-literal::

  % ezid3.py `username`:hl2::`password`:hl2: mint ark:/99999/fk4 @ metadata.txt

And if a metadata element value has the form "@\ `filename`:hl1:", the
named file is read and treated as a single value.  For example, if
file metadata.xml contains a DataCite XML document, then a test DOI
identifier with that document as the value of the "datacite" element
can be minted by invoking:

.. parsed-literal::

  % ezid3.py `username`:hl2::`password`:hl2: mint doi:10.5072/FK2 \
  datacite @metadata.xml

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
  '\https://ezid.cdlib.org/id/`identifier`:hl2:');
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
  '\https://ezid.cdlib.org/id/`identifier`:hl2:');
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
  '\https://ezid.cdlib.org/shoulder/`shoulder`:hl2:');
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

Update identifier:

.. parsed-literal::

  <?php
  $input = '_target: `url`:hl2:';
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, \
  '\https://ezid.cdlib.org/id/`identifier`:hl2:');
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

The following Perl examples use the `libwww-perl (LWP)`__
`\ `:ext-icon: library.

__ libwww-perl_

To get identifier metadata, parse and decode it, and store it in a
hash, `%metadata`:hl1:\ :

.. parsed-literal::

  use LWP::UserAgent;

  $ua = LWP::UserAgent->new;
  $r = $ua->get("https://ezid.cdlib.org/id/`identifier`:hl2:");
  if ($r->is_success) {
    ($statusline, $m) = split(/\\n/, $r->decoded_content, 2);
    %metadata = map { map { s/%([0-9A-F]{2})/pack("C", hex($1))/egi; $_ }
      split(/: /, $_, 2) } split(/\\n/, $m);
  } else {
    print $r->code, $r->decoded_content;
  }

The following example creates an identifier, supplying initial
metadata values from a hash, `%metadata`:hl1:.  Note that LWP is
particular about how https URLs are expressed.  In an LWP request the
protocol should be included but not a port number
("\https://ezid.cdlib.org/..."), but conversely when supplying
credentials the https port number should be included but not a
protocol ("ezid.cdlib.org:443").

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
  $ua->credentials("ezid.cdlib.org:443", "EZID", "`username`:hl2:", \
  "`password`:hl2:");
  $r = $ua->request(PUT "\https://ezid.cdlib.org/id/`identifier`:hl2:",
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
  $ua->credentials("ezid.cdlib.org:443", "EZID", "`username`:hl2:", \
  "`password`:hl2:");
  $r = $ua->request(POST "\https://ezid.cdlib.org/shoulder/`shoulder`:hl2:",
    "Content-Type" => "text/plain; charset=UTF-8");
  if ($r->is_success) {
    $identifier = $r->decoded_content =~ m/success: ([^ ]*)/ && $1;
  } else {
    print $r->code, $r->decoded_content;
  }

To update an identifier using values from a hash, `%metadata`:hl1:\ :

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
  $ua->credentials("ezid.cdlib.org:443", "EZID", "`username`:hl2:", \
  "`password`:hl2:");
  $r = $ua->request(POST "\https://ezid.cdlib.org/id/`identifier`:hl2:",
    "Content-Type" => "text/plain; charset=UTF-8",
    Content => encode("UTF-8", join("\\n",
      map { escape($_) . ": " . escape($metadata{$_}) } keys %metadata)));
  print $r->code, $r->decoded_content unless $r->is_success;

Java example
------------

A number of Java code snippets have been presented above.  In the
example below we combine them all into a runnable, end-to-end program
that mints a test identifier and then retrieves and prints the
identifier's metadata.

.. parsed-literal::

  import java.io.*;
  import java.net.*;
  import java.util.*;

  class harness {

      static String SERVER = "\https://ezid.cdlib.org";
      static String USERNAME = "`username`:hl2:";
      static String PASSWORD = "`password`:hl2:";

      static class MyAuthenticator extends Authenticator {
          protected PasswordAuthentication getPasswordAuthentication () {
              return new PasswordAuthentication(
                  USERNAME, PASSWORD.toCharArray());
          }
      }

      static class Response {

          int responseCode;
          String status;
          String statusLineRemainder;
          HashMap<String, String> metadata;

          public String toString () {
              StringBuffer b = new StringBuffer();
              b.append("responseCode=");
              b.append(responseCode);
              b.append("\\nstatus=");
              b.append(status);
              b.append("\\nstatusLineRemainder=");
              b.append(statusLineRemainder);
              b.append("\\nmetadata");
              if (metadata != null) {
                  b.append(" follows\\n");
                  Iterator<Map.Entry<String, String>> i =
                      metadata.entrySet().iterator();
                  while (i.hasNext()) {
                      Map.Entry<String, String> e = i.next();
                      b.append(e.getKey() + ": " + e.getValue() + "\\n");
                  }
              } else {
                  b.append("=null\\n");
              }
              return b.toString();
          }

      }

      static String encode (String s) {
          return s.replace("%", "%25").replace("\\n", "%0A").
              replace("\\r", "%0D").replace(":", "%3A");
      }

      static String toAnvl (HashMap<String, String> metadata) {
          Iterator<Map.Entry<String, String>> i =
              metadata.entrySet().iterator();
          StringBuffer b = new StringBuffer();
          while (i.hasNext()) {
              Map.Entry<String, String> e = i.next();
              b.append(encode(e.getKey()) + ": " +
                       encode(e.getValue()) + "\\n");
          }
          return b.toString();
      }

      static String decode (String s) {
          StringBuffer b = new StringBuffer();
          int i;
          while ((i = s.indexOf("%")) >= 0) {
              b.append(s.substring(0, i));
              b.append((char)
                       Integer.parseInt(s.substring(i+1, i+3), 16));
              s = s.substring(i+3);
          }
          b.append(s);
          return b.toString();
      }

      static String[] parseAnvlLine (String line) {
          String[] kv = line.split(":", 2);
          kv[0] = decode(kv[0]).trim();
          kv[1] = decode(kv[1]).trim();
          return kv;
      }

      static Response issueRequest (
          String method, String path, HashMap<String, String> metadata)
          throws Exception {
          HttpURLConnection c = (HttpURLConnection)
              (new URL(SERVER + "/" + path)).openConnection();
          c.setRequestMethod(method);
          c.setRequestProperty("Accept", "text/plain");
          if (metadata != null) {
              c.setDoOutput(true);
              c.setRequestProperty("Content-Type",
                                   "text/plain; charset=UTF-8");
              OutputStreamWriter w =
                  new OutputStreamWriter(c.getOutputStream(), "UTF-8");
              w.write(toAnvl(metadata));
              w.flush();
          }
          Response r = new Response();
          r.responseCode = c.getResponseCode();
          InputStream is = r.responseCode < 400? c.getInputStream() :
              c.getErrorStream();
          if (is != null) {
              BufferedReader br = new BufferedReader(
                  new InputStreamReader(is, "UTF-8"));
              String[] kv = parseAnvlLine(br.readLine());
              r.status = kv[0];
              r.statusLineRemainder = kv[1];
              HashMap<String, String> d = new HashMap<String, String>();
              String l;
              while ((l = br.readLine()) != null) {
                  kv = parseAnvlLine(l);
                  d.put(kv[0], kv[1]);
              }
              if (d.size() > 0) r.metadata = d;
          }
          return r;
      }

      public static void main (String[] args) throws Exception {

          Authenticator.setDefault(new MyAuthenticator());

          // Sample POST request.
          System.out.println("Issuing POST request...");
          HashMap<String, String> metadata =
              new HashMap<String, String>();
          metadata.put("erc.what", "a test");
          Response r = issueRequest(
              "POST", "shoulder/ark:/99999/fk4", metadata);
          System.out.print(r);

          // Sample GET request.
          System.out.println("\\nIssuing GET request...");
          String id = r.statusLineRemainder;
          r = issueRequest("GET", "id/" + URLEncoder.encode(id, "UTF-8"),
                           null);
          System.out.print(r);

      }

  }

curl examples
-------------

The EZID API can be exercised using the curl_ `\ `:ext-icon: command
line tool.  The following examples assume metadata is UTF-8 encoded
throughout.

To get identifier metadata, obtaining text formatted as described in
`Request & response bodies`_ above:

.. parsed-literal::

  curl \https://ezid.cdlib.org/id/`identifier`:hl2:

To mint an identifier:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST \https://ezid.cdlib.org/\
  shoulder/`shoulder`:hl2:

A single metadata element can be specified on the command line.  For
example, to mint an identifier and specify a target URL at the same
time:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary '_target: `url`:hl2:' \https://ezid.cdlib.org/shoulder/\
  `shoulder`:hl2:

To specify more than one metadata element, the metadata must be placed
in a file that is formatted as described in `Request & response
bodies`_.  For example, to mint an identifier and upload metadata
contained in a file `metadata.txt`:hl1:\ :

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary @\ `metadata.txt`:hl2: \https://ezid.cdlib.org/shoulder/\
  `shoulder`:hl2:

Creating an identifier is similar to minting one, except that the HTTP
method (-X option) is changed from POST to PUT and an identifier is
specified instead of a shoulder.  Here are the three examples above,
but now creating an identifier:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X PUT \https://ezid.cdlib.org/id/\
  `identifier`:hl2:

  curl -u `username`:hl2::`password`:hl2: -X PUT -H 'Content-Type: text/plain'
    --data-binary '_target: `url`:hl2:' \https://ezid.cdlib.org/id/\
  `identifier`:hl2:

  curl -u `username`:hl2::`password`:hl2: -X PUT -H 'Content-Type: text/plain'
    --data-binary @\ `metadata.txt`:hl2: \https://ezid.cdlib.org/id/\
  `identifier`:hl2:

To update identifier metadata:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary '_target: `url`:hl2:' \https://ezid.cdlib.org/id/\
  `identifier`:hl2:

  curl -u `username`:hl2::`password`:hl2: -X POST -H 'Content-Type: text/plain'
    --data-binary @\ `metadata.txt`:hl2: \https://ezid.cdlib.org/id/\
  `identifier`:hl2:

Batch processing
----------------

The API does not directly support batch processing, but EZID does
provide two client tools, linked from this documentation, that can
simplify the work of scripting a batch job.  First and most generally,
the `Python command line tool`_ can exercise all API functions and is
straightforward to script.  For example, to mint and print 100 test
ARK identifiers:

.. parsed-literal::

  #! /bin/bash
  for i in {1..100}; do
    ezid3.py `username`:hl2::`password`:hl2: mint ark:/99999/fk4 | \
  awk '{ print $2 }'
  done

Second, the batch-register.py_ `\ `:ext-icon: script automates several
common types of batch processing.  It reads an input CSV file
containing identifier metadata, one row per identifier; transforms the
metadata into EZID metadata as directed by a configuration file of
mappings; creates or mints identifiers, or updates existing
identifiers, using that metadata; and outputs a CSV file containing
the created, minted, or updated identifiers and other information.
Detailed usage information is contained in the script itself, but to
give a taste of what it can do, given an input CSV file with columns,

.. parsed-literal::

  title,author,orcid,publisher_name,publisher_place,url

a possible complete mapping file to mint DOI identifiers is shown
below.  The mappings reference both EZID metadata elements and, using
XPath expressions, `DataCite Metadata Scheme`_ `\ `:ext-icon: elements
and attributes.

.. parsed-literal::

  _profile = datacite
  /resource/titles/title = $1
  /resource/creators/creator/creatorName = $2
  /resource/creators/creator/nameIdentifier = $3
  /resource/creators/creator/nameIdentifier\@nameIdentifierScheme = ORCID
  /resource/publisher = $4 ($5)
  /resource/publicationYear = 2018
  /resource/resourceType\@resourceTypeGeneral = Dataset
  _target = $6

For another example, to update the statuses of a batch of existing
identifiers to public, given an input file listing the identifiers
(i.e., a CSV file with just one column), a mapping file would be:

.. parsed-literal::

  _id = $1
  _status = public

Batch download
--------------

The metadata for all identifiers matching a set of constraints can be
downloaded in one batch operation.  Authentication is required, and
the scope of the identifiers that can be downloaded in this way is
implicitly restricted to those that are directly owned by or otherwise
updatable by the requestor.

Batch download and harvesting (see `OAI-PMH harvesting`_ below) are
similar but different operations.  With batch download, the
identifiers returned are restricted to those updatable by the
requestor as noted above, but within that scope it is possible to
download *all* identifiers, including reserved, unavailable, and test
identifiers.  By contrast, with harvesting, no authentication is
required and the identifiers returned are not restricted by ownership,
but only those identifiers that are public and exported and that
satisfy several other quality criteria are returned.

**Subsections**

- Overview_
- `Download formats`_
- Parameters_
- `Using curl to request a download`_

.. _Overview:

**Overview**

The batch download process is asynchronous.  A download is requested
by issuing a POST request to

  https://ezid.cdlib.org/download_request

The content type of the request body must be
"application/x-www-form-urlencoded" and the body must include one POST
parameter, "format", specifying the download format, and may include
additional parameters (see Parameters_ below) specifying search
criteria and download format and notification options.  The return is
a status line indicating either error (see `Error reporting`_ above)
or success.  If successful, the status line includes a URL from which
the download can be retrieved.  Here's a sample interaction:

.. parsed-literal::

  |rArr| POST /download_request HTTP/1.1
  |rArr| Host: ezid.cdlib.org
  |rArr| Content-Type: application/x-www-form-urlencoded
  |rArr| Content-Length: 19
  |rArr|
  |rArr| format=xml&type=ark

  |lArr| HTTP/1.1 200 OK
  |lArr| Content-Type: text/plain; charset=UTF-8
  |lArr| Content-Length: 57
  |lArr|
  |lArr| success: \https://ezid.cdlib.org/download/da543b91a0.xml.gz

The download will not be available immediately, but clients can poll
the returned URL; the server returns HTTP status code 404 (Not Found)
if the download is not yet ready.  As part of the request, clients can
also specify an email address to which a notification will be sent
when the download becomes available.  Downloads are retained for one
week.

.. _`Download formats`:

**Download formats**

Identifier metadata is returned in one of three formats; which format
is determined by the "format" parameter.  In all cases, the text
encoding is UTF-8 and the metadata is compressed with either gzip_
`\ `:ext-icon: or ZIP_ `\ `:ext-icon: as determined by the
"compression" parameter.

1. **Format "anvl"**.  This format is effectively the concatenation of
   performing a get metadata operation (see `Operation: get identifier
   metadata`_ above) on each selected identifier.  Metadata is
   returned in ANVL format and employs percent-encoding as described
   in `Request & response bodies`_.  The metadata for an identifier is
   preceded by a header line that contains two colons (":", U+003A)
   followed by the identifier.  Blocks of metadata are separated by
   blank lines.  For example:

   ::

     :: ark:/99999/fk4gt78tq
     _created: 1300812337
     _export: yes
     _owner: apitest
     _ownergroup: apitest
     _profile: erc
     _status: public
     _target: http://www.gutenberg.org/ebooks/7178
     _updated: 1300913550
     erc.what: Remembrance of Things Past
     erc.when: 1922
     erc.who: Proust, Marcel

     :: doi:10.5072/FK2S75905Q
     _created: 1421276359
     _datacenter: CDL.CDL
     _export: yes
     _owner: apitest
     _ownergroup: apitest
     _profile: datacite
     _status: public
     _target: http://www.gutenberg.org/ebooks/26014
     _updated: 1421276359
     datacite: <?xml version="1.0"?>%0A<resource xmlns="http://...

2. **Format "csv"**.  Metadata is returned as an Excel-compatible
   `Comma-separated values (CSV)`_ `\ `:ext-icon: table, one row per
   selected identifier.  A header row lists column names.  The columns
   to return must be specified using one or more "column" parameters;
   the order of columns in the table matches the parameter order.  The
   columns that can be returned include all internal EZID metadata
   elements (refer to `Internal metadata`_) and all citation metadata
   elements (refer to `Metadata profiles`_).  Additionally, the
   following columns may be requested:

   - _id

     The identifier.

   - _target

     The resolved URL (Location).

   - _mappedCreator, _mappedTitle, _mappedPublisher, _mappedDate,
     _mappedType

     Creator, title, publisher, date, and type citation metadata as
     mapped from the identifier's preferred metadata profile.

   Continuing with the previous example, if the parameters are

   ::

     format=csv&column=_id&column=_owner&column=erc.when&column=_mappedCreator

   then the following table will be returned:

   ::

     _id,_owner,erc.when,_mappedCreator
     ark:/99999/fk4gt78tq,apitest,1922,"Proust, Marcel"
     doi:10.5072/FK2S75905Q,apitest,,Montagu Browne

   Note that for the CSV format only, line terminators in metadata
   values (both newlines ("\\n", U+000A) and carriage returns ("\\r",
   U+000D)) are converted to spaces.

3. **Format "xml"**.  Metadata is returned as a single XML document.
   The root element, <records>, contains a <record> element for each
   selected identifier, and within each <record> element are <element>
   elements for each of the identifier's metadata elements.  Thus the
   returned document will have the structure:

   .. parsed-literal::

     <?xml version="1.0" encoding="UTF-8"?>
     <records>
       <record identifier="`identifier`:hl2:">
         <element name="`name`:hl2:">\ `value`:hl2: </element>
         ...
       </record>
       ...
     </records>

   As a special case, XML metadata bound to a "datacite" or "crossref"
   element is directly embedded in the containing <element> element,
   i.e., the metadata will appear as an XML subelement and not as a
   string value.

   Continuing with the previous example, the return in XML format
   would be:

   .. parsed-literal ::

     <?xml version="1.0" encoding="UTF-8"?>
     <records>
       <record identifier="ark:/99999/fk4gt78tq">
         <element name="_created">1300812337</element>
         <element name="_export">yes</element>
         <element name="_owner">apitest</element>
         <element name="_ownergroup">apitest</element>
         <element name="_profile">erc</element>
         <element name="_status">public</element>
         <element name="_target">http://www.gutenberg.org/ebooks/7178</element>
         <element name="_updated">1300913550</element>
         <element name="erc.what">Remembrance of Things Past</element>
         <element name="erc.when">1922</element>
         <element name="erc.who">Proust, Marcel</element>
       </record>
       <record identifier="doi:10.5072/FK2S75905Q">
         <element name="_created">1421276359</element>
         <element name="_datacenter">CDL.CDL</element>
         <element name="_export">yes</element>
         <element name="_owner">apitest</element>
         <element name="_ownergroup">apitest</element>
         <element name="_profile">datacite</element>
         <element name="_status">public</element>
         <element name="_target">http://www.gutenberg.org/ebooks/26014\
     </element>
         <element name="_updated">1421276359</element>
         <element name="datacite">
           <resource xmlns="http://datacite.org/schema/kernel-4">
             <identifier identifierType="DOI">10.5072/FK2S75905Q</identifier>
             <creators>
               <creator>
                 <creatorName>Montagu Browne</creatorName>
               </creator>
             </creators>
             <titles>
               <title>Practical Taxidermy</title>
             </titles>
             <publisher>Charles Scribner's Sons</publisher>
             <publicationYear>1884</publicationYear>
             <resourceType resourceTypeGeneral="Text"/>
           </resource>
         </element>
       </record>
     </records>

.. _Parameters:

**Parameters**

Unless otherwise noted, parameters are optional and *not* repeatable.

- format={anvl|csv|xml} *(required)*

  The download format, as described above.

- compression={gzip|zip}

  The compression to use, gzip_ `\ `:ext-icon: or ZIP_ `\ `:ext-icon:.
  gzip is the default.

- column=\ `c`:hl1: *(repeatable)*

  Return column `c`:hl1:.  Applies to the "csv" format only, in which
  case at least one column is required.

- notify=\ `address`:hl1: *(repeatable)*

  Send an email message to `address`:hl1: when the download becomes
  available.

- convertTimestamps={yes|no}

  If yes, convert Unix timestamp values bound to the "_created" and
  "_updated" internal metadata elements to ISO 8601
  YYYY-MM-DDTHH:MM:SSZ format.

The remaining parameters are search constraints.  Search constraints
are logically ANDed together, but search constraint parameters that
are repeated have the effect of creating a logical OR of the selected
values.  For example, parameter "status" can take on three possible
values, "reserved", "public", or "unavailable".  If no "status"
parameter is specified, there is no constraint on identifier status;
if "status=reserved" is specified, then only reserved identifiers are
returned; and if "status=reserved&status=public" is specified, then
reserved and public identifiers are returned (but not unavailable
identifiers).

- createdAfter=\ `t`:hl1:

  Return identifiers created on or after time `t`:hl1:.  The time may
  be given as a Unix timestamp or in ISO 8601 YYYY-MM-DDTHH:MM:SSZ
  format.  Note that lower time bounds are inclusive.

- createdBefore=\ `t`:hl1:

  Return identifiers created before time `t`:hl1:.  The time may be
  given as a Unix timestamp or in ISO 8601 YYYY-MM-DDTHH:MM:SSZ
  format.  Note that upper time bounds are exclusive.

- crossref={yes|no}

  Return identifiers that either are or are not registered with
  Crossref.

- datacite={yes|no}

  Return identifiers that either are or are not registered with
  DataCite.

- exported={yes|no}

  Return identifiers that either are or are not exported.

- owner=\ `u`:hl1: (*repeatable*)

  Return identifiers owned by user `u`:hl1:, where `u`:hl1: is an EZID
  username, e.g., "apitest".  All "owner" and "ownergroup" parameters
  are ORed together; if none are specified, the identifiers directly
  owned by the requestor are returned.

- ownergroup=\ `g`:hl1: *(repeatable)*

  Return identifiers owned by group `g`:hl1:, where `g`:hl1: is an
  EZID group name, e.g., "cdl".  All "owner" and "ownergroup"
  parameters are ORed together; if none are specified, the identifiers
  directly owned by the requestor are returned.

- permanence={test|real}

  Return only test identifiers or only real identifiers.

- profile=\ `p`:hl1: *(repeatable)*

  Return identifiers whose preferred metadata profile is `p`:hl1:.

- status={reserved|public|unavailable} *(repeatable)*

  Return identifiers having the specified status.

- type={ark|doi|uuid} *(repeatable)*

  Return identifiers of the specified type.

- updatedAfter=\ `t`:hl1:, updatedBefore=\ `t`:hl1:

  Constraints against update time; see the comparable "createdAfter"
  and "createdBefore" parameters above.

.. _`Using curl to request a download`:

**Using curl to request a download**

A batch download can easily be requested using the
curl_ `\ `:ext-icon: command line tool.  Use curl's "-d" option to
specify parameters, and use the "-u" option to supply credentials.
For example:

.. parsed-literal::

  curl -u `username`:hl2::`password`:hl2: -d format=anvl -d type=ark \
  -d type=doi
    -d permanence=real \https://ezid.cdlib.org/download_request

For even more convenience, a simple Bash script, batch-download.sh_
`\ `:ext-icon:, turns a batch download into a one-step operation.  The
script issues a download request using curl, waits for the request to
be processed, and when ready downloads to a file in the current
directory.  Its usage equivalent to the above example would be:

.. parsed-literal::

  % batch-download.sh `username`:hl2: `password`:hl2: format=anvl type=ark \
  type=doi permanence=real
  submitting download request...
  waiting......
  9c02f494ab.txt.gz

OAI-PMH harvesting
------------------

EZID supports harvesting of identifiers and citation metadata via `The
Open Archives Initiative Protocol for Metadata Harvesting (OAI-PMH)`__
`\ `:ext-icon:, version 2.0.  The base URL for OAI-PMH access is

__ OAI-PMH_

  https://ezid.cdlib.org/oai

Only public, exported, non-test identifiers that have non-default
target URLs and at least creator, title, and date citation metadata
(in ERC__ terms, who/what/when metadata) are made available through
OAI-PMH.

Harvesting and batch download are similar but different operations;
see `Batch download`_ for the differences.

__ `Profile "erc"`_

In returning an identifier's metadata, EZID maps citation metadata
from the identifier's preferred metadata profile (see `Metadata
profiles`_ above) to one of two delivery formats: `Dublin Core`__
`\ `:ext-icon: (as required by the protocol) or DataCite__
`\ `:ext-icon:.  In the latter case, older DataCite XML metadata
records stored in EZID are converted to version 4 of the DataCite
schema for uniformity.  Note that, in an extension to the DataCite
schema, the identifier type for non-DOI identifiers is set to "ARK" or
"UUID" as appropriate.

__ `Dublin Core Metadata Element Set`_
__ `DataCite Metadata Scheme`_

//END//
