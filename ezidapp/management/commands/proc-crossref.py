#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# =============================================================================
#
# EZID :: crossref.py
#
# Interface to Crossref <http://www.crossref.org/>.
#
#
# -----------------------------------------------------------------------------
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import django.conf
import django.core.mail
import django.core.management
import django.db
import django.db.models
import lxml.etree

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import ezidapp.models.identifier
import ezidapp.models.user
import ezidapp.models.util
import impl.ezid
import impl.log
import impl.nog.util
import impl.util
import impl.util2

import ezidapp.models.async_queue

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'Crossref'
    name = 'crossref'
    setting = 'DAEMONS_CROSSREF_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)
        self.queue = ezidapp.models.async_queue.CrossrefQueue

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, *_, **opt):
        maxSeq = None

        while True:
            django.db.connections["default"].close()
            django.db.connections["search"].close()

            # noinspection PyTypeChecker
            time.sleep(int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP))

            try:
                # First, a quick test to avoid retrieving the entire table if nothing needs to be
                # done.
                #
                # In the loop below, if any entry is deleted or if any identifier is processed,
                # maxSeq is set to None, thus forcing another round of processing.
                if maxSeq is not None:
                    if (
                        self.queue().objects.aggregate(django.db.models.Max("seq"))["seq__max"]
                        == maxSeq
                    ):
                        continue
                # Hopefully the queue will not grow so large that the following
                # query will cause a burden.
                query = self.queue().objects.all().order_by("seq")
                if len(query) > 0:
                    maxSeq = query[len(query) - 1].seq
                else:
                    maxSeq = None
                for r in query:
                    # If there are multiple entries for this identifier, we are
                    # necessarily looking at the first, i.e., the earliest, and
                    # the others must represent subsequent modifications.  Hence
                    # we simply delete this entry regardless of its status.
                    if self.queue().objects.filter(identifier=r.identifier).count() > 1:
                        r.delete()
                        maxSeq = None
                    else:
                        if r.status == ezidapp.models.async_queue.CrossrefQueue.UNSUBMITTED:
                            self._doDeposit(r)
                            maxSeq = None
                        elif r.status == ezidapp.models.async_queue.CrossrefQueue.SUBMITTED:
                            self._doPoll(r)
                            maxSeq = None
                        else:
                            pass
            except Exception as e:
                log.exception(' Exception as e')
                self.otherError("crossref.run", e)
                maxSeq = None

    def _notOne(self, n):
        if n == 0:
            return "no"
        else:
            return "more than one"

    def _addDeclaration(self, document):
        # We don't use lxml's xml_declaration argument because it doesn't
        # allow us to add a basic declaration without also adding an
        # encoding declaration, which we don't want.
        return '<?xml version="1.0"?>\n' + document

    def _buildDeposit(self, body, registrant, doi, targetUrl, withdrawTitles=False, bodyOnly=False):
        """Build a Crossref metadata submission document

        'body' should be a
        Crossref <body> child element as a Unicode string, and is assumed to
        have been validated and normalized per validateBody above.
        'registrant' is inserted in the header.  'doi' should be a
        scheme-less DOI identifier (e.g., "10.5060/FOO").  The return is a
        tuple (document, body, batchId) where 'document' is the entire
        submission document as a serialized Unicode string (with the DOI and
        target URL inserted), 'body' is the same but just the <body> child
        element, and 'batchId' is the submission batch identifier.
        Options: if 'withdrawTitles' is true, the title(s) corresponding to
        the DOI being defined are prepended with "WITHDRAWN:" (in 'document'
        only).  If 'bodyOnly' is true, only the body is returned.
        """
        body = lxml.etree.XML(body)
        m = self.TAG_REGEX.match(body.tag)
        namespace = m.group(1)
        version = m.group(2)
        ns = {"N": namespace}
        doiData = body.xpath("//N:doi_data", namespaces=ns)[0]
        doiElement = doiData.find("N:doi", namespaces=ns)
        doiElement.text = doi
        doiData.find("N:resource", namespaces=ns).text = targetUrl
        d1 = self._addDeclaration(lxml.etree.tostring(body, encoding="unicode"))
        if bodyOnly:
            return d1

        def q(elementName):
            return f"{{{namespace}}}{elementName}"

        root = lxml.etree.Element(q("doi_batch"), version=version)
        root.attrib[self._schemaLocation] = body.attrib[self._schemaLocation]
        head = lxml.etree.SubElement(root, q("head"))
        batchId = str(uuid.uuid1())
        lxml.etree.SubElement(head, q("doi_batch_id")).text = batchId
        lxml.etree.SubElement(head, q("timestamp")).text = str(int(time.time() * 100))
        e = lxml.etree.SubElement(head, q("depositor"))
        if version >= "4.3.4":
            lxml.etree.SubElement(
                e, q("depositor_name")
            ).text = django.conf.settings.CROSSREF_DEPOSITOR_NAME
        else:
            lxml.etree.SubElement(e, q("name")).text = django.conf.settings.CROSSREF_DEPOSITOR_NAME
        lxml.etree.SubElement(
            e, q("email_address")
        ).text = django.conf.settings.CROSSREF_DEPOSITOR_EMAIL
        lxml.etree.SubElement(head, q("registrant")).text = registrant
        e = lxml.etree.SubElement(root, q("body"))
        del body.attrib[self._schemaLocation]
        if withdrawTitles:
            for p in self.TITLE_PATH_LIST:
                for t in doiData.xpath(p, namespaces=ns):
                    if t.text is not None:
                        t.text = "WITHDRAWN: " + t.text
        e.append(body)
        d2 = self._addDeclaration(lxml.etree.tostring(root, encoding="unicode"))
        return d2, d1, batchId

    def _multipartBody(self, *parts):
        """Build a multipart/form-data (RFC 2388) document out of a list of
        constituent parts.

        Each part is either a 2-tuple (name, value) or a 4-tuple (name,
        filename, contentType, value).  Returns a tuple (document, boundary).
        """
        while True:
            boundary = f"BOUNDARY_{uuid.uuid1().hex}"
            collision = False
            for p in parts:
                for e in p:
                    if boundary in e:
                        collision = True
            if not collision:
                break
        body = []
        for p in parts:
            body.append("--" + boundary)
            if len(p) == 2:
                body.append(f'Content-Disposition: form-data; name="{p[0]}"')
                body.append("")
                body.append(p[1])
            else:
                body.append(f'Content-Disposition: form-data; name="{p[0]}"; filename="{p[1]}"')
                body.append("Content-Type: " + p[2])
                body.append("")
                body.append(p[3])
        body.append(f"--{boundary}--")
        return "\r\n".join(body), boundary

    def _wrapException(self, context, exception):
        m = str(exception)
        if len(m) > 0:
            m = ": " + m
        return Exception(f"Crossref error: {context}: {type(exception).__name__}{m}")

    def _submitDeposit(self, deposit, batchId, doi):
        """Submit a Crossref metadata submission document as built by _buildDeposit
        above.

        Returns True on success, False on (internal) error.  'doi' is the
        identifier in question.
        """
        if not django.conf.settings.CROSSREF_ENABLED:
            return True
        body, boundary = self._multipartBody(
            ("operation", "doMDUpload"),
            ("login_id", self._username),
            ("login_passwd", django.conf.settings.CROSSREF_PASSWORD),
            (
                "fname",
                batchId + ".xml",
                "application/xml; charset=utf-8",
                deposit.encode("utf-8"),
            ),
        )
        # noinspection PyUnresolvedReferences
        url = django.conf.settings.CROSSREF_DEPOSIT_URL.format(
            django.conf.settings.CROSSREF_TEST_SERVER
            if impl.util2.isTestCrossrefDoi(doi)
            else django.conf.settings.CROSSREF_REAL_SERVER
        )
        try:
            c = None
            try:
                c = urllib.request.urlopen(
                    urllib.request.Request(
                        url,
                        body.encode('utf-8'),
                        {"Content-Type": "multipart/form-data; boundary=" + boundary},
                    )
                )
                r = c.read()
                assert "Your batch submission was successfully received." in r, (
                    "unexpected return from metadata submission: " + r
                )
            except urllib.error.HTTPError as e:
                log.exception(' urllib.error.HTTPError as e')
                msg = None
                if e.fp is not None:
                    try:
                        msg = e.fp.read()
                    except Exception:
                        log.exception(' Exception')
                        pass
                raise Exception(msg) from e
            finally:
                if c:
                    c.close()
        except Exception as e:
            log.exception(' Exception as e')
            self.otherError(
                "crossref._submitDeposit",
                self._wrapException(f"error submitting deposit, doi {doi}, batch {batchId}", e),
            )
            return False
        else:
            return True

    def _pollDepositStatus(self, batchId, doi):
        """
        Poll the status of the metadata submission identified by 'batchId'.
        'doi' is the identifier in question.  The return is one of the
        tuples:

          ("submitted", message)
            'message' further indicates the status within Crossref, e.g.,
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

          Crossref message
          conflict_id=1423608
          in conflict with: 10.5072/FK2TEST1
          in conflict with: 10.5072/FK2TEST2
          ...
        """
        if not django.conf.settings.CROSSREF_ENABLED:
            return "completed successfully", None
        # noinspection PyUnresolvedReferences
        url = django.conf.settings.CROSSREF_RESULTS_URL % (
            django.conf.settings.CROSSREF_TEST_SERVER
            if impl.util2.isTestCrossrefDoi(doi)
            else django.conf.settings.CROSSREF_REAL_SERVER
        )
        try:
            c = None
            try:
                c = urllib.request.urlopen(
                    "{}?{}".format(
                        url,
                        urllib.parse.urlencode(
                            {
                                "usr": self._username,
                                "pwd": django.conf.settings.CROSSREF_PASSWORD,
                                "file_name": batchId + ".xml",
                                "type": "result",
                            }
                        ),
                    )
                )
                response = c.read()
            except urllib.error.HTTPError as e:
                log.exception(' urllib.error.HTTPError as e')
                msg = None
                if e.fp is not None:
                    try:
                        msg = e.fp.read()
                    except Exception:
                        log.exception(' Exception')
                        pass
                raise Exception(msg) from e
            finally:
                if c:
                    c.close()
            try:
                # We leave the returned XML undecoded, and let lxml decode it
                # based on the embedded encoding declaration.
                root = lxml.etree.XML(response)
            except Exception as e:
                log.exception(' Exception as e')
                assert False, "XML parse error: " + str(e)
            assert root.tag == "doi_batch_diagnostic", (
                "unexpected response root element: " + root.tag
            )
            assert "status" in root.attrib, "missing doi_batch_diagnostic/status attribute"
            if root.attrib["status"] != "completed":
                return "submitted", root.attrib["status"]
            else:
                d = root.findall("record_diagnostic")
                assert len(d) == 1, (
                    f"<doi_batch_diagnostic> element contains {self._notOne(len(d))} "
                    f"<record_diagnostic> element"
                )
                d = d[0]
                assert "status" in d.attrib, "missing record_diagnostic/status attribute"
                if d.attrib["status"] == "Success":
                    return "completed successfully", None
                elif d.attrib["status"] in ["Warning", "Failure"]:
                    m = d.findall("msg")
                    assert len(m) == 1, (
                        f"<record_diagnostic> element contains {self._notOne(len(m))} "
                        f"<msg> element"
                    )
                    m = m[0].text
                    e = d.find("conflict_id")
                    if e is not None:
                        m += "\nconflict_id=" + e.text
                    for e in d.xpath("dois_in_conflict/doi"):
                        m += "\nin conflict with: " + e.text
                    return f"completed with {d.attrib['status'].lower()}", m
                else:
                    assert False, "unexpected status value: " + d.attrib["status"]
        except Exception as e:
            log.exception(' Exception as e')
            self.otherError(
                "crossref._pollDepositStatus",
                self._wrapException(f"error polling deposit status, doi {doi}, batch {batchId}", e),
            )
            return "unknown", None

    def _doDeposit(self, r):
        m = impl.util.deblobify(r.metadata)
        if r.operation == ezidapp.models.async_queue.CrossrefQueue.DELETE:
            url = "http://datacite.org/invalidDOI"
        else:
            url = m["_t"]
        submission, body, batchId = self._buildDeposit(
            m["crossref"],
            ezidapp.models.util.getUserByPid(r.owner).username,
            r.identifier[4:],
            url,
            withdrawTitles=(
                r.operation == ezidapp.models.async_queue.CrossrefQueue.DELETE
                or m.get("_is", "public").startswith("unavailable")
            ),
        )
        if self._submitDeposit(submission, batchId, r.identifier[4:]):
            if r.operation == ezidapp.models.async_queue.CrossrefQueue.DELETE:
                # Well this is awkard.  If the identifier was deleted, there's
                # no point in polling for the status... if anything goes wrong,
                # there's no correction that could possibly be made, as the
                # identifier no longer exists as far as EZID is concerned.
                r.delete()
            else:
                r.status = ezidapp.models.async_queue.CrossrefQueue.SUBMITTED
                r.batchId = batchId
                r.submitTime = int(time.time())
                r.save()

    def _sendEmail(self, emailAddress, r):
        if r.status == ezidapp.models.async_queue.CrossrefQueue.WARNING:
            s = "warning"
        else:
            s = "error"
        l = f"{django.conf.settings.EZID_BASE_URL}/id/{urllib.parse.quote(r.identifier, ':/')}"
        m = (
            "EZID received a{} {} in registering an identifier of yours with "
            "Crossref.\n\n"
            "Identifier: {}\n\n"
            "Status: {}\n\n"
            "Crossref message: {}\n\n"
            "The identifier can be viewed in EZID at:\n"
            "{}\n\n"
            "You are receiving this message because your account is configured to "
            "receive Crossref errors and warnings.  This is an automated email.  "
            "Please do not reply.\n".format(
                "n" if s == "error" else "",
                s,
                r.identifier,
                r.get_status_display(),
                r.message if r.message != "" else "(unknown reason)",
                l,
            )
        )
        try:
            django.core.mail.send_mail(
                "Crossref registration " + s,
                m,
                django.conf.settings.SERVER_EMAIL,
                [emailAddress],
                fail_silently=True,
            )
        except Exception as e:
            log.exception(' Exception as e')
            raise self._wrapException("error sending email", e)

    def _oneline(self, s):
        return re.sub(r"\s", " ", s)

    def _doPoll(self, r):
        t = self._pollDepositStatus(r.batchId, r.identifier[4:])
        if t[0] == "submitted":
            r.message = t[1]
            r.save()
        elif t[0].startswith("completed"):
            # Deleted identifiers aren't retained in the queue, but just to
            # make it clear...
            if r.operation != ezidapp.models.async_queue.CrossrefQueue.DELETE:
                if t[0] == "completed successfully":
                    crs = ezidapp.models.identifier.Identifier.CR_SUCCESS
                    crm = ""
                else:
                    if t[0] == "completed with warning":
                        crs = ezidapp.models.identifier.Identifier.CR_WARNING
                    else:
                        crs = ezidapp.models.identifier.Identifier.CR_FAILURE
                    crm = self._oneline(t[1]).strip()
                # We update the identifier's Crossref status in the store and
                # search databases, but do so in such a way as to avoid
                # infinite loops and triggering further updates to DataCite or
                # Crossref.
                s = impl.ezid.setMetadata(
                    r.identifier,
                    ezidapp.models.util.getAdminUser(),
                    {"_crossref": f"{crs}/{crm}"},
                    updateExternalServices=False,
                )
                assert s.startswith("success:"), "ezid.setMetadata failed: " + s
            if t[0] == "completed successfully":
                r.delete()
            else:
                if t[0] == "completed with warning":
                    r.status = ezidapp.models.async_queue.CrossrefQueue.WARNING
                else:
                    r.status = ezidapp.models.async_queue.CrossrefQueue.FAILURE
                r.message = t[1]
                u = ezidapp.models.util.getUserByPid(r.owner)
                if u.crossrefEmail != "":
                    self._sendEmail(u.crossrefEmail, r)
                r.save()
        else:
            pass
