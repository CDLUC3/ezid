# =============================================================================
#
# EZID :: crossref.py
#
# Interface to CrossRef <http://www.crossref.org/>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import django.core.mail
import django.db.models
import lxml.etree
import re
import threading
import time
import urllib
import urllib2
import uuid
import zlib

import ezid
import ezidapp.models
import config
import idmap
import log
import policy
import shoulder
import userauth
import util

_enabled = None
_depositorName = None
_depositorEmail = None
_realServer = None
_testServer = None
_depositUrl = None
_resultsUrl = None
_username = None
_password = None
_doiTestShoulder = None
_threadName = None
_idleSleep = None
_ezidUrl = None

def _loadConfig ():
  global _enabled, _depositorName, _depositorEmail, _realServer, _testServer
  global _depositUrl, _resultsUrl, _username, _password, _doiTestShoulder
  global _threadName, _idleSleep, _ezidUrl
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.config("crossref.enabled").lower() == "true"
  _depositorName = config.config("crossref.depositor_name")
  _depositorEmail = config.config("crossref.depositor_email")
  _realServer = config.config("crossref.real_server")
  _testServer = config.config("crossref.test_server")
  _depositUrl = config.config("crossref.deposit_url")
  _resultsUrl = config.config("crossref.results_url")
  _username = config.config("crossref.username")
  _password = config.config("crossref.password")
  s = shoulder.getDoiTestShoulder()
  if s != None:
    assert s.key.startswith("doi:")
    _doiTestShoulder = s.key[4:]
  else:
    # Shoulder never happen.
    _doiTestShoulder = "10.????"
  _idleSleep = int(config.config("daemons.crossref_processing_idle_sleep"))
  if _enabled:
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_daemonThread, name=_threadName)
    t.setDaemon(True)
    t.start()
  _ezidUrl = config.config("DEFAULT.ezid_base_url")

_prologRE = re.compile("<\?xml\s+version\s*=\s*['\"]([-\w.:]+)[\"']" +\
  "(\s+encoding\s*=\s*['\"]([-\w.]+)[\"'])?" +\
  "(\s+standalone\s*=\s*['\"](yes|no)[\"'])?\s*\?>\s*")
_utf8RE = re.compile("UTF-?8$", re.I)
_schemaLocation = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
_schemaLocationTemplate =\
  "http://www.crossref.org/schema/deposit/crossref%s.xsd"
_tagRE =\
  re.compile("\{(http://www\.crossref\.org/schema/(4\.3\.\d))\}([-\w.]+)$")
_rootTags = ["journal", "book", "conference", "sa_component", "dissertation",
  "report-paper", "standard", "database"]
_crossrefTestPrefix = "10.15697/"

def _notOne (n):
  if n == 0:
    return "no"
  else:
    return "more than one"

def _addDeclaration (document):
  # We don't use lxml's xml_declaration argument because it doesn't
  # allow us to add a basic declaration without also adding an
  # encoding declaration, which we don't want.
  return "<?xml version=\"1.0\"?>\n" + document

def validateBody (body):
  """
  Validates and normalizes an immediate child element of a <body>
  element of a CrossRef metadata submission document.  'body' should
  be a Unicode string.  Either a normalized XML document is returned
  or an assertion error is raised.  Validation is limited to checking
  that 'body' is well-formed XML, that it appears to be a <body> child
  element, and that the elements that EZID cares about are present and
  well-formed.  Normalization includes stripping off any <doi_batch>
  or <body> elements enclosing the child element, and normalizing the
  one and only <doi_data> element.
  """
  # Strip off any prolog.
  m = _prologRE.match(body)
  if m:
    assert m.group(1) == "1.0", "unsupported XML version"
    if m.group(2) != None:
      assert _utf8RE.match(m.group(3)), "XML encoding must be UTF-8"
    if m.group(4) != None:
      assert m.group(5) == "yes", "XML document must be standalone"
    body = body[len(m.group(0)):]
  # Parse the document.
  try:
    root = lxml.etree.XML(body)
  except Exception, e:
    assert False, "XML parse error: " + str(e)
  m = _tagRE.match(root.tag)
  assert m is not None, "not CrossRef submission metadata"
  namespace = m.group(1)
  version = m.group(2)
  ns = { "N": namespace }
  # Locate the <body> child element.
  if m.group(3) == "doi_batch":
    root = root.find("N:body", namespaces=ns)
    assert root is not None, "malformed CrossRef submission metadata"
    m = _tagRE.match(root.tag)
  if m.group(3) == "body":
    assert len(list(root)) == 1, "malformed CrossRef submission metadata"
    root = root[0]
    m = _tagRE.match(root.tag)
    assert m is not None, "malformed CrossRef submission metadata"
  assert m.group(3) in _rootTags,\
    "XML document root is not a CrossRef <body> child element"
  # Locate and normalize the one and only <doi_data> element.
  doiData = root.xpath("//N:doi_data", namespaces=ns)
  assert len(doiData) == 1, "XML document contains %s <doi_data> element" %\
    _notOne(len(doiData))
  doiData = doiData[0]
  doi = doiData.findall("N:doi", namespaces=ns)
  assert len(doi) == 1,\
    "<doi_data> element contains %s <doi> subelement" % _notOne(len(doi))
  doi = doi[0]
  doi.text = "(:tba)"
  resource = doiData.findall("N:resource", namespaces=ns)
  assert len(resource) == 1,\
    "<doi_data> element contains %s <resource> subelement" %\
    _notOne(len(resource))
  resource = resource[0]
  resource.text = "(:tba)"
  assert doiData.find("N:collection", namespaces=ns) == None,\
    "<doi_data> element contains disallowed <collection> subelement"
  e = doiData.find("N:timestamp", namespaces=ns)
  if e != None: doiData.remove(e)
  assert doiData.find("N:timestamp", namespaces=ns) == None,\
    "<doi_data> element contains more than one <timestamp> subelement"
  # Normalize schema declarations.
  root.attrib[_schemaLocation] =\
    namespace + " " + (_schemaLocationTemplate % version)
  try:
    return _addDeclaration(lxml.etree.tostring(root, encoding="unicode"))
  except Exception, e:
    assert False, "XML serialization error: " + str(e)

def _isTestIdentifier (doi):
  return doi.startswith(_doiTestShoulder)

def _buildDeposit (body, registrant, doi, targetUrl):
  """
  Builds a CrossRef metadata submission document.  'body' should be a
  CrossRef <body> child element as a Unicode string, and is assumed to
  have been validated and normalized per validateBody above.
  'registrant' is inserted in the header.  'doi' should be a
  scheme-less DOI identifier (e.g., "10.5060/FOO").  The return is a
  tuple (document, body, batchId) where 'document' is the entire
  submission document as a serialized Unicode string (with the DOI and
  target URL inserted), 'body' is the same but just the <body> child
  element, and 'batchId' is the submission batch identifier.  If 'doi'
  is a test identifier, it is prefixed with _crossrefTestPrefix in
  'document' only.
  """
  body = lxml.etree.XML(body)
  m = _tagRE.match(body.tag)
  namespace = m.group(1)
  version = m.group(2)
  ns = { "N": namespace }
  doiData = body.xpath("//N:doi_data", namespaces=ns)[0]
  doiElement = doiData.find("N:doi", namespaces=ns)
  doiElement.text = doi
  doiData.find("N:resource", namespaces=ns).text = targetUrl
  d1 = _addDeclaration(lxml.etree.tostring(body, encoding="unicode"))
  def q (elementName):
    return "{%s}%s" % (namespace, elementName)
  root = lxml.etree.Element(q("doi_batch"), version=version)
  root.attrib[_schemaLocation] = body.attrib[_schemaLocation]
  head = lxml.etree.SubElement(root, q("head"))
  batchId = str(uuid.uuid1())
  lxml.etree.SubElement(head, q("doi_batch_id")).text = batchId
  lxml.etree.SubElement(head, q("timestamp")).text = str(int(time.time()*100))
  e = lxml.etree.SubElement(head, q("depositor"))
  if version >= "4.3.4":
    lxml.etree.SubElement(e, q("depositor_name")).text = _depositorName
  else:
    lxml.etree.SubElement(e, q("name")).text = _depositorName
  lxml.etree.SubElement(e, q("email_address")).text = _depositorEmail
  lxml.etree.SubElement(head, q("registrant")).text = registrant
  e = lxml.etree.SubElement(root, q("body"))
  del body.attrib[_schemaLocation]
  if _isTestIdentifier(doi): doiElement.text = _crossrefTestPrefix + doi
  e.append(body)
  d2 = _addDeclaration(lxml.etree.tostring(root, encoding="unicode"))
  return (d2, d1, batchId)

def _multipartBody (*parts):
  """
  Builds a multipart/form-data (RFC 2388) document out of a list of
  constituent parts.  Each part is either a 2-tuple (name, value) or a
  4-tuple (name, filename, contentType, value).  Returns a tuple
  (document, boundary).
  """
  while True:
    boundary = "BOUNDARY_%s" % uuid.uuid1().hex
    collision = False
    for p in parts:
      for e in p:
        if boundary in e: collision = True
    if not collision: break
  body = []
  for p in parts:
    body.append("--" + boundary)
    if len(p) == 2:
      body.append("Content-Disposition: form-data; name=\"%s\"" % p[0])
      body.append("")
      body.append(p[1])
    else:
      body.append(("Content-Disposition: form-data; name=\"%s\"; " +\
        "filename=\"%s\"") % (p[0], p[1]))
      body.append("Content-Type: " + p[2])
      body.append("")
      body.append(p[3])
  body.append("--%s--" % boundary)
  return ("\r\n".join(body), boundary)

def _wrapException (context, exception):
  m = str(exception)
  if len(m) > 0: m = ": " + m
  return Exception("CrossRef error: %s: %s%s" % (context,
    type(exception).__name__, m))

def _submitDeposit (deposit, batchId, doi):
  """
  Submits a CrossRef metadata submission document as built by
  _buildDeposit above.  Returns True on success, False on (internal)
  error.  'doi' is the identifier in question.
  """
  if not _enabled: return True
  body, boundary = _multipartBody(("operation", "doMDUpload"),
    ("login_id", _username), ("login_passwd", _password),
    ("fname", batchId + ".xml", "application/xml; charset=UTF-8",
    deposit.encode("UTF-8")))
  url = _depositUrl % (_testServer if _isTestIdentifier(doi) else _realServer)
  try:
    c = None
    try:
      c = urllib2.urlopen(urllib2.Request(url, body,
        { "Content-Type": "multipart/form-data; boundary=" + boundary }))
      r = c.read()
      assert "Your batch submission was successfully received." in r,\
        "unexpected return from metadata submission: " + r
    except urllib2.HTTPError, e:
      if e.fp != None:
        try:
          m = e.fp.read()
        except Exception:
          pass
        else:
          if not e.msg.endswith("\n"): e.msg += "\n"
          e.msg += m
      raise e
    finally:
      if c: c.close()
  except Exception, e:
    log.otherError("crossref._submitDeposit",
      _wrapException("error submitting deposit, doi %s, batch %s" %\
      (doi, batchId), e))
    return False
  else:
    return True

def _pollDepositStatus (batchId, doi):
  """
  Polls the status of the metadata submission identified by 'batchId'.
  'doi' is the identifier in question.  The return is one of the
  tuples:

    ("submitted", message)
      'message' further indicates the status within CrossRef, e.g.,
      "in_process".  The status may also be, somewhat confusingly,
      "unknown_submission", even though the submission has taken
      place.
    ("completed successfully", None)
    ("completed with warning", message)
    ("completed with failure", message)
    ("unknown", None)
      An error occurred retrieving the status.

  In each case, 'message' may be a multi-line string.  In the case of
  a conflict warning, 'message' has the form:

    CrossRef message
    conflict_id=1423608
    in conflict with: 10.5072/FK2TEST1
    in conflict with: 10.5072/FK2TEST2
    ...
  """
  if not _enabled: return ("completed successfully", None)
  url = _resultsUrl % (_testServer if _isTestIdentifier(doi) else _realServer)
  try:
    c = None
    try:
      c = urllib2.urlopen("%s?%s" % (url,
        urllib.urlencode({ "usr": _username, "pwd": _password,
        "file_name": batchId + ".xml", "type": "result" })))
      response = c.read()
    except urllib2.HTTPError, e:
      if e.fp != None:
        try:
          m = e.fp.read()
        except Exception:
          pass
        else:
          if not e.msg.endswith("\n"): e.msg += "\n"
          e.msg += m
      raise e
    finally:
      if c: c.close()
    try:
      # We leave the returned XML undecoded, and let lxml decode it
      # based on the embedded encoding declaration.
      root = lxml.etree.XML(response)
    except Exception, e:
      assert False, "XML parse error: " + str(e)
    assert root.tag == "doi_batch_diagnostic",\
      "unexpected response root element: " + root.tag
    assert "status" in root.attrib,\
      "missing doi_batch_diagnostic/status attribute"
    if root.attrib["status"] != "completed":
      return ("submitted", root.attrib["status"])
    else:
      d = root.findall("record_diagnostic")
      assert len(d) == 1, ("<doi_batch_diagnostic> element contains %s " +\
        "<record_diagnostic> element") % _notOne(len(d))
      d = d[0]
      assert "status" in d.attrib, "missing record_diagnostic/status attribute"
      if d.attrib["status"] == "Success":
        return ("completed successfully", None)
      elif d.attrib["status"] in ["Warning", "Failure"]:
        m = d.findall("msg")
        assert len(m) == 1, ("<record_diagnostic> element contains %s " +\
          "<msg> element") % _notOne(len(m))
        m = m[0].text
        e = d.find("conflict_id")
        if e != None: m += "\nconflict_id=" + e.text
        for e in d.xpath("dois_in_conflict/doi"):
          m += "\nin conflict with: " + e.text
        return ("completed with %s" % d.attrib["status"].lower(), m)
      else:
        assert False, "unexpected status value: " + d.attrib["status"]
  except Exception, e:
    log.otherError("crossref._pollDepositStatus",
      _wrapException("error polling deposit status, doi %s, batch %s" %\
      (doi, batchId), e))
    return ("unknown", None)

def _blobify (metadata):
  l = []
  for k, v in metadata.items():
    assert len(k) > 0, "empty label"
    assert len(v) > 0, "empty value"
    l.append(util.encode4(k))
    l.append(util.encode3(v))
  return zlib.compress(" ".join(l))

def _deblobify (blob):
  v = zlib.decompress(blob).split(" ")
  d = {}
  for i in range(0, len(v), 2): d[util.decode(v[i])] = util.decode(v[i+1])
  return d

def enqueueIdentifier (identifier, operation, metadata):
  """
  Adds an identifier to the CrossRef queue.  'identifier' should be
  the normalized, qualified identifier, e.g., "doi:10.5060/FOO".
  'operation' is the identifier operation as reported by the store
  module.  'metadata' is the identifier's metadata dictionary.
  """
  e = ezidapp.models.CrossrefQueue(identifier=identifier, owner=metadata["_o"],
    metadata=_blobify(metadata),
    operation=ezidapp.models.CrossrefQueue.operationLabelToCode(operation))
  e.save()

def getQueueStatistics ():
  """
  Returns a 4-tuple containing the numbers of identifiers in the
  CrossRef queue by status: (awaiting submission, submitted,
  registered with warning, registration failed).
  """
  q = ezidapp.models.CrossrefQueue.objects.values("status").\
    annotate(django.db.models.Count("status"))
  d = {}
  for r in q: d[r["status"]] = r["status__count"]
  return (d.get("U", 0), d.get("S", 0), d.get("W", 0), d.get("F", 0))

class _AbortException (Exception):
  pass

def _checkAbort ():
  # This function provides a handy way to abort processing if the
  # daemon is disabled or if a new daemon thread is started by a
  # configuration reload.  It doesn't entirely eliminate potential
  # race conditions between two daemon threads, but it should make
  # conflicts very unlikely.
  if not _enabled or threading.currentThread().getName() != _threadName:
    raise _AbortException()

def _queue ():
  _checkAbort()
  return ezidapp.models.CrossrefQueue

def _doDeposit (r):
  m = _deblobify(r.metadata)
  submission, body, batchId = _buildDeposit(m["crossref"],
    idmap.getAgent(r.owner)[0], r.identifier[4:], m["_st"])
  if _submitDeposit(submission, batchId, r.identifier[4:]):
    r.status = ezidapp.models.CrossrefQueue.SUBMITTED
    r.batchId = batchId
    r.submitTime = int(time.time())
    _checkAbort()
    r.save()

def _sendEmail (emailAddresses, r):
  if r.status == ezidapp.models.CrossrefQueue.WARNING:
    s = "warning"
  else:
    s = "error"
  l = "%s/id/%s" % (_ezidUrl, urllib.quote(r.identifier, ":/"))
  m = ("EZID received a%s %s in registering an identifier of yours with\n" +\
    "CrossRef.\n\n" +\
    "Identifier: %s\n" +\
    "Status: %s\n" +\
    "CrossRef message: %s\n\n" +\
    "The identifier can be viewed in EZID at:\n" +
    "%s\n\n" +\
    "You are receiving this message because your account is configured to\n" +\
    "receive CrossRef errors and warnings.  This is an automated email.\n" +\
    "Please do not reply.\n") %\
    ("n" if s == "error" else "", s, r.identifier, r.get_status_display(),
    r.message if r.message != "" else "(unknown reason)", l)
  try:
    django.core.mail.send_mail("CrossRef registration " + s, m,
      django.conf.settings.SERVER_EMAIL, emailAddresses)
  except Exception, e:
    raise _wrapException("error sending email", e)

def _oneline (s):
  return re.sub("\s", " ", s)

def _doPoll (r):
  t = _pollDepositStatus(r.batchId, r.identifier[4:])
  if t[0] == "submitted":
    r.message = t[1]
    _checkAbort()
    r.save()
  elif t[0].startswith("completed"):
    if r.operation != ezidapp.models.CrossrefQueue.DELETE:
      if t[0] == "completed successfully":
        m = "successfully registered"
      else:
        m = _oneline(t[1]).strip()
        if len(m) == 0: m = "(unknown reason)"
        if t[0] == "completed with warning":
          m = "registered with warning | " + m
        else:
          m = "registration failure | " + m
      _checkAbort()
      s = ezid.asAdmin(ezid.setMetadata, r.identifier,
        { "_cr": "yes | " + m }, False)
      assert s.startswith("success:"), "ezid.setMetadata failed: " + s
    if t[0] == "completed successfully":
      _checkAbort()
      r.delete()
    else:
      if t[0] == "completed with warning":
        r.status = ezidapp.models.CrossrefQueue.WARNING
      else:
        r.status = ezidapp.models.CrossrefQueue.FAILURE
      r.message = t[1]
      au = userauth.getAuthenticatedUser(idmap.getAgent(r.owner)[0])
      emailAddresses = policy.getCrossrefInfo(au.user, au.group)[1]
      if len(emailAddresses) > 0:
        _checkAbort()
        _sendEmail(emailAddresses, r)
      # If the operation was DELETE, a CrossRef error or warning will
      # leave an entry in the queue that refers to a nonexistent
      # identifier.  Hard to say whether that's better than ignoring
      # the CrossRef problem or not.
      _checkAbort()
      r.save()
  else:
    pass

def _daemonThread ():
  maxSeq = None
  while True:
    time.sleep(_idleSleep)
    try:
      # First, a quick test to avoid retrieving the entire table if
      # nothing needs to be done.  Note that in the loop below, if any
      # entry is deleted or if any identifier is processed, maxSeq is
      # set to None, thus forcing another round of processing.
      if maxSeq != None:
        if _queue().objects.aggregate(
          django.db.models.Max("seq"))["seq__max"] == maxSeq:
          continue
      # Hopefully the queue will not grow so large that the following
      # query will cause a burden.
      query = _queue().objects.all().order_by("seq")
      if len(query) > 0:
        maxSeq = query[len(query)-1].seq
      else:
        maxSeq = None
      for r in query:
        # If there are multiple entries for this identifier, we are
        # necessarily looking at the first, i.e., the earliest, and
        # the others must represent subsequent modifications.  Hence
        # we simply delete this entry regardless of its status.
        if _queue().objects.filter(identifier=r.identifier).count() > 1:
          r.delete()
          maxSeq = None
        else:
          if r.status == ezidapp.models.CrossrefQueue.UNSUBMITTED:
            _doDeposit(r)
            maxSeq = None
          elif r.status == ezidapp.models.CrossrefQueue.SUBMITTED:
            _doPoll(r)
            maxSeq = None
          else:
            pass
    except _AbortException:
      break
    except Exception, e:
      log.otherError("crossref._daemonThread", e)
      maxSeq = None

_loadConfig()
config.addLoader(_loadConfig)
