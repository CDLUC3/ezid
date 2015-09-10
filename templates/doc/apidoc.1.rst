The EZID API, Version 1
=======================

//BEGIN//

.. class:: superseded

THIS VERSION IS SUPERSEDED BY A NEWER VERSION

.. class:: smallfont

| **This version:** http://HOSTNAME/doc/apidoc.1.html
| **Latest version:** http://HOSTNAME/doc/apidoc.html

Modified 2010.06.24.

EZID is an interface that provides an easy way for digital object
producers and others to obtain, register, and describe long-term
identifiers for their objects.  It comes with a web user interface
(UI) and a web Application Programming Interface (API).  This document
describes Version 1 of the EZID API.

Please use the following address to report any problems:

  ezid-l@listserv.ucop.edu

Failures outside of normal working hours (08:00 to 17:00 Pacific,
Monday - Friday) will be addressed the next work day.

Framework
---------

The EZID API (and UI) is available from the base URL,

  http://n2t.net/ezid

Interaction is done via RESTful HTTP.  Message bodies of both requests
and responses are of content type "text/plain", with all text in
Unicode and encoded in UTF-8.

A message body is a set of newline-terminated (LF) text lines.  Each
line represents an element consisting of an element name, a colon, and
the element value (this is a subset of the ANVL format).

::

  Author: Proust, Marcel
  Title: Remembrance of Things Past
  _target: http://...

Some characters must be percent-encoded with three characters "%XY",
where XY is the character's hex code.  These include ':' and '.' in
element names, and ';' and '|' in element values.

Element names beginning with an underscore ('_') are reserved for
internal use by EZID.  There is one reserved element name, _target, to
hold the reidirection target URL.  In returned metadata, additional
elements with leading underscores may be returned; this is metadata
maintained by EZID.

Requests and Responses
----------------------

All requests require HTTP basic authentication except GETs on
identifiers.

Responses consist of a status line possibly followed by metadata,
depending on the operation.  A status line may be "success:" followed
by the normalized form of the identifier in question, e.g.,

::

  success: doi:10.1234/FOO

or a status line may contain some kind of error::

  error: bad request - <reason...>
  error: unauthorized
  error: internal server error
  error: method not allowed

The HTTP status code matches the status line.

Registering a DOI
-----------------

A DOI is registered with a request of the form

  PUT \http://n2t.net/ezid/id/{identifier}

This will create the supplied {identifier} in the sense that it will
bind (record) assertions about the identifier string in a place where
others can see them.  Until such assertions are shared, an identifier
is not much harder to manage than a private thought, as the identifier
string is unencumbered by others' expectations.

The body, which may be empty, should contain metadata to associate
(bind) with the identifier.  For example,

::

  C: PUT http://n2t.net/ezid/id/doi%3A10.1234/foo
  C:
  C: _target: http://...
  S: HTTP/1.1 200 OK
  S: Content-Type: text/plain
  S:
  S: success: doi:10.1234/FOO

where lines marked with a C are issued by a web client and lines
marked S are issued by the server.  The response is successful if and
only if the HTTP response returns code 200 and the response body
begins with "success:".

Example Python Client
---------------------

::

  import urllib2

  baseurl = "http://n2t.net/ezid"

  h = urllib2.HTTPBasicAuthHandler()
  h.add_password("EZID", baseurl, "username", "password")
  opener = urllib2.build_opener(h)

  # Create a DOI with an initial target and other metadata.

  r = urllib2.Request(baseurl + "/id/doi%3A10.9999/test")
  r.get_method = lambda: "PUT"
  r.add_header("Content-Type", "text/plain")
  r.add_data("_target: http://www.cnn.com/\nCreator: Francis Bacon")
  try:
    c = opener.open(r)
    print c.read()
    c.close()
  except urllib2.HTTPError, e:
    print e.code, e.msg
    print e.fp.read()

  # Add/update some metadata to a DOI.

  r = urllib2.Request(baseurl + "/id/doi%3A10.9999/test")
  r.add_header("Content-Type", "text/plain")
  r.add_data("Creator: J.K. Frimple")
  try:
    c = opener.open(r)
    print c.read()
    c.close()
  except urllib2.HTTPError, e:
    print e.code, e.msg
    print e.fp.read()

  # Retrieve a DOI's metadata.

  try:
    c = urllib2.urlopen(baseurl + "/id/doi%3A10.9999/test")
    print c.read()
    c.close()
  except urllib2.HTTPError, e:
    print e.code, e.msg
    print e.fp.read()

//END//
