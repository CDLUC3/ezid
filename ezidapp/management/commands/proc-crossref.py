#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Interface to Crossref <http://www.crossref.org/>

The previous version of the Crossref process would delete earlier tasks from the queue
if the queue had multiple tasks for the same identifier. We currently have not ported
this to Py3 because it has the cost of having to check forwards in the queue. The Py2
implementation retrieved the full queue, regardless of size, to do these checks. If the
situation of having multiple updates for the same identifier in the queue is common
enough that it's detrimental to simply process them all, it would be better to check for
duplicates when the tasks are being inserted in the queue, and update existing tasks
there instead of inserting new ones.
"""

import logging
import re
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
import impl.crossref
import impl.ezid
import impl.log
import impl.util
import impl.util2
from django.db.models import Q


log = logging.getLogger(__name__)
TAG_REGEX = re.compile("{(http://www\\.crossref\\.org/schema/(4\.[34]\.\d|5\.[3]\.\d))}([-\\w.]+)$")


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_CROSSREF_ENABLED'
    queue = ezidapp.models.async_queue.CrossrefQueue
    refIdentifier = ezidapp.models.identifier.RefIdentifier

    def run(self):
        """Run async processing loop forever.

        This method is not called for disabled async processes.
        """
        while not self.terminated():
            qs = self.queue.objects.filter(
                Q(status=self.queue.UNSUBMITTED)
                | Q(status=self.queue.UNCHECKED)
                | Q(status=self.queue.SUBMITTED)
            ).order_by("seq")[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]

            if not qs:
                self.sleep(django.conf.settings.DAEMONS_IDLE_SLEEP)
                continue

            for task_model in qs:
                log.info('-' * 100)
                log.info(f'Processing task: {str(task_model)}')
                try:
                    self.do_task(task_model)
                except ezidapp.management.commands.proc_base.AsyncProcessingIgnored:
                    log.debug(f'Ignored: {task_model.refIdentifier.identifier}')
                    task_model.status = self.queue.IGNORED
                except Exception as e:
                    log.error('#' * 100)
                    log.error(f'Exception when handling task "{task_model}"')
                    task_model.error = str(e)
                    # if self.is_permanent_error(e):
                    if True:
                        task_model.status = self.queue.FAILURE
                        task_model.errorIsPermanent = True

                task_model.save()

            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

    def do_task(self, task_model: ezidapp.models.async_queue.CrossrefQueue):
        if task_model.status == self.queue.UNSUBMITTED:
            self.submit(task_model)
        elif task_model.status in (self.queue.UNCHECKED, self.queue.SUBMITTED):
            self.check_status(task_model)
        else:
            raise AssertionError('Unhandled case')

    def submit(self, task_model: ezidapp.models.async_queue.CrossrefQueue):
        """Submit Create/Update/Delete to Crossref and move state from UNSUBMITTED to
        UNCHECKED.
        """
        log.debug(f'Deposit: {task_model}')
        ref_id = task_model.refIdentifier

        if not ref_id.isCrossref:
            raise ezidapp.management.commands.proc_base.AsyncProcessingIgnored

        meta_dict = ref_id.metadata
        op_str = task_model.operation
        id_base_str = ref_id.identifier[4:]

        # Use the resolveTarget property to ensure correct setting for reserved or unavailable identifiers
        # url = 'http://datacite.org/invalidDOI' if op_str == self.queue.DELETE else ref_id.target
        url = (
            'http://datacite.org/invalidDOI'
            if op_str == self.queue.DELETE
            else ref_id.resolverTarget
        )

        # withdrawTitles is set to True if:
        #  The current operation is a DELETE
        #  OR
        #  the identifier is unvailable, meaning the identified resource is not available
        submission, body, batchId = self._buildDeposit(
            meta_dict['crossref'],
            ref_id.owner.username,
            id_base_str,
            url,
            withdrawTitles=(op_str == self.queue.DELETE or ref_id.isUnavailable),
        )

        self._submitDeposit(submission, batchId, id_base_str)

        task_model.status = self.queue.UNCHECKED
        task_model.batchId = batchId
        task_model.submitTime = self.now_int()

    def _buildDeposit(
        self,
        body: str,
        registrant: str,
        doi: str,
        targetUrl: str,
        withdrawTitles: bool = False,
        bodyOnly: bool = False,
    ) -> (str, str, str):
        """Build a Crossref metadata submission document

        Args:
            body: Crossref <body> child element as a Unicode string. Assumed to have
                been validated and normalized per validateBody above.
            registrant: Is inserted in the header.
            doi: should be a scheme-less DOI identifier (e.g., "10.5060/FOO").
            targetUrl:
            withdrawTitles: If true, the title(s) corresponding to the DOI being
                defined are prepended with "WITHDRAWN:" (in 'document' only)
            bodyOnly: If true, only the body is returned.

        Returns:
            The return is a tuple (document, body, batchId) where 'document' is the
            entire submission document as a serialized Unicode string (with the DOI and
            target URL inserted), 'body' is the same but just the <body> child element,
            and 'batchId' is the submission batch identifier.
        """
        body = lxml.etree.XML(body)
        m = TAG_REGEX.match(body.tag)
        namespace = m.group(1)
        version = m.group(2)
        ns = {'N': namespace}
        doiData = body.xpath('//N:doi_data', namespaces=ns)[0]
        doiElement = doiData.find('N:doi', namespaces=ns)
        doiElement.text = doi
        doiData.find('N:resource', namespaces=ns).text = targetUrl
        d1 = self._addDeclaration(lxml.etree.tostring(body, encoding='unicode'))
        if bodyOnly:
            return d1

        def q(elementName):
            return f'{{{namespace}}}{elementName}'

        root = lxml.etree.Element(q('doi_batch'), version=version)
        root.attrib[impl.crossref.SCHEMA_LOCATION_STR] = body.attrib[
            impl.crossref.SCHEMA_LOCATION_STR
        ]
        head = lxml.etree.SubElement(root, q('head'))
        batchId = str(uuid.uuid1())
        lxml.etree.SubElement(head, q('doi_batch_id')).text = batchId
        lxml.etree.SubElement(head, q('timestamp')).text = str(int(self.now() * 100))
        e = lxml.etree.SubElement(head, q('depositor'))
        if version >= '4.3.4':
            lxml.etree.SubElement(
                e, q('depositor_name')
            ).text = django.conf.settings.CROSSREF_DEPOSITOR_NAME
        else:
            lxml.etree.SubElement(e, q('name')).text = django.conf.settings.CROSSREF_DEPOSITOR_NAME
        lxml.etree.SubElement(
            e, q('email_address')
        ).text = django.conf.settings.CROSSREF_DEPOSITOR_EMAIL
        lxml.etree.SubElement(head, q('registrant')).text = registrant
        e = lxml.etree.SubElement(root, q('body'))
        del body.attrib[impl.crossref.SCHEMA_LOCATION_STR]
        if withdrawTitles:
            for p in impl.crossref.TITLE_PATH_LIST:
                for t in doiData.xpath(p, namespaces=ns):
                    if t.text is not None:
                        t.text = 'WITHDRAWN: ' + t.text
        e.append(body)
        d2 = self._addDeclaration(lxml.etree.tostring(root, encoding='unicode'))
        return d2, d1, batchId

    def _submitDeposit(self, deposit: str, batchId: str, doi: str) -> bool:
        """Submit a Crossref metadata submission document.

        Returns True on success, False on (internal) error. 'doi' is the
        identifier in question.
        """
        body_bytes, boundary = self._multipartBody(
            ('operation', 'doMDUpload'),
            ('login_id', django.conf.settings.CROSSREF_USERNAME),
            ('login_passwd', django.conf.settings.CROSSREF_PASSWORD),
            (
                'fname',
                batchId + '.xml',
                'application/xml; charset=utf-8',
                deposit,
            ),
        )

        base_url = self.get_base_url(doi)
        url = base_url + django.conf.settings.CROSSREF_DEPOSIT_PATH
        log.debug(f'Deposit URL: {url}')

        try:
            c = None
            try:
                c = urllib.request.urlopen(
                    urllib.request.Request(
                        url,
                        body_bytes,
                        {'Content-Type': 'multipart/form-data; boundary=' + boundary},
                    ),
                    timeout=self._http_client_timeout,
                )
                r = c.read().decode('utf-8')
                assert 'Your batch submission was successfully received.' in r, (
                    'unexpected return from metadata submission: ' + r
                )
            except urllib.error.HTTPError as e:
                log.error('HTTPError')
                msg = None
                if e.fp is not None:
                    try:
                        msg = e.fp.read().decode('utf-8')
                    except Exception:
                        log.error('Exception')
                raise Exception(msg) from e
            finally:
                if c:
                    c.close()
        except Exception as e:
            log.error('Exception')
            impl.log.otherError(
                'crossref._submitDeposit',
                self._wrapException(f'error submitting deposit, doi {doi}, batch {batchId}', e),
            )
            return False
        else:
            return True

    def get_base_url(self, doi: str) -> str:
        is_test_doi = impl.util2.isTestCrossrefDoi(doi)
        # Force hitting the test server if EZID is running in DEBUG mode
        # is_test_doi |= django.conf.settings.DEBUG
        log.debug(f'isTestCrossrefDoi({doi}) or DEBUG: {is_test_doi}')
        return (
            django.conf.settings.CROSSREF_TEST_SERVER
            if is_test_doi
            else django.conf.settings.CROSSREF_REAL_SERVER
        )

    def check_status(self, task_model: ezidapp.models.async_queue.CrossrefQueue):
        """Check status of previously submitted Create/Update/Delete and move state
        from UNCHECKED/SUBMITTED to SUBMITTED/WARNING/FAILURE/SUCCESS.

        UNCHECKED: Submitted but not yet checked
        SUBMITTED: Checked but not yet completed
        WARNING/FAILURE/SUCCESS: Completed
        """
        log.debug(f'Check: {task_model}')

        ref_id = task_model.refIdentifier
        t = self._checkDepositStatus(task_model)
        status_str = t[0]
        msg_str = ''

        if status_str == 'submitted':
            task_model.status = self.queue.SUBMITTED
            id_status = ezidapp.models.identifier.Identifier.CR_WORKING
        elif status_str == 'completed successfully':
            task_model.status = self.queue.SUCCESS
            id_status = ezidapp.models.identifier.Identifier.CR_SUCCESS
        elif status_str == 'completed with warning':
            task_model.status = self.queue.WARNING
            id_status = ezidapp.models.identifier.Identifier.CR_WARNING
            msg_str = self._oneLine(t[1]).strip()
        else:
            task_model.status = self.queue.FAILURE
            id_status = ezidapp.models.identifier.Identifier.CR_FAILURE
            msg_str = self._oneLine(t[1]).strip()

        task_model.message = msg_str

        # If operation was not a delete, we have an identifier we can update.
        if task_model.operation != self.queue.DELETE:
            # Update the identifier's Crossref status in the store and search tables in
            # such a way as to avoid infinite loops and triggering further updates to
            # DataCite or Crossref.
            s = impl.ezid.setMetadata(
                ref_id.identifier,
                ezidapp.models.util.getAdminUser(),
                {'_crossref': f'{id_status}/{msg_str}'},
                updateExternalServices=False,
            )
            assert s.startswith('success:'), f'ezid.setMetadata failed: {s}'

        if task_model.status in (self.queue.WARNING, self.queue.FAILURE):
            refOwner = ref_id.owner_id
            u = ezidapp.models.util.getUserById(refOwner)
            if u.crossrefEmail:
                self._sendEmail(u.crossrefEmail, task_model)

    def _multipartBody(self, *parts) -> (bytes, str):
        """Build a multipart/form-data (RFC 2388) document out of a list of constituent
        parts.

        Each part is either a 2-tuple (name, value) or a 4-tuple (name, filename,
        contentType, value). Returns a tuple (document, boundary).

        `value` is always bytes. Other elements are always str.
        """
        boundary = f'BOUNDARY_{uuid.uuid1().hex}'
        part_list = []
        for p in parts:
            part_list.append('--' + boundary)
            if len(p) == 2:
                part_list.append(f'Content-Disposition: form-data; name="{p[0]}"')
                part_list.append('')
                part_list.append(p[1])
            else:
                part_list.append(
                    f'Content-Disposition: form-data; name="{p[0]}"; filename="{p[1]}"'
                )
                part_list.append(f'Content-Type: {p[2]}')
                part_list.append('')
                part_list.append(p[3])
        part_list.append(f'--{boundary}--')
        return (
            b'\r\n'.join([s.encode('utf-8') if isinstance(s, str) else s for s in part_list]),
            boundary,
        )

    def _checkDepositStatus(self, task_model: ezidapp.models.async_queue.CrossrefQueue):
        batchId = task_model.batchId
        ref_id = task_model.refIdentifier
        doi = ref_id.identifier[4:]

        """Check the status of the metadata submission identified by 'batchId'. 'doi' is
        the identifier in question. The return is one of the tuples:

          ("submitted", message)
            'message' further indicates the status within Crossref, e.g.,
            "in_process". The status may also be, somewhat confusingly,
            "unknown_submission", even though the submission has taken
            place.
          ("completed successfully", None)
          ("completed with warning", message)
          ("completed with failure", message)
          ("unknown", None)
            An error occurred retrieving the status.

        In each case, 'message' may be a multi-line string. In the case of a conflict
        warning, 'message' has the form:

          Crossref message
          conflict_id=1423608
          in conflict with: 10.5072/FK2TEST1
          in conflict with: 10.5072/FK2TEST2
          ...
        """
        if not django.conf.settings.CROSSREF_ENABLED:
            return 'completed successfully', None

        log.debug(f'Checking deposit status, doi {doi}, batch {batchId}')
        base_url = self.get_base_url(doi)
        url = base_url + django.conf.settings.CROSSREF_RESULTS_PATH

        c = None
        try:
            c = urllib.request.urlopen(
                '{}?{}'.format(
                    url,
                    urllib.parse.urlencode(
                        {
                            'usr': django.conf.settings.CROSSREF_USERNAME,
                            'pwd': django.conf.settings.CROSSREF_PASSWORD,
                            'file_name': batchId + '.xml',
                            'type': 'result',
                        }
                    ),
                    timeout=self._http_client_timeout,
                )
            )
            response = c.read()
        except urllib.error.HTTPError as e:
            log.error('HTTPError')
            msg = None
            if e.fp is not None:
                try:
                    msg = e.fp.read().decode('utf-8')
                except Exception:
                    log.error('Exception')
            raise Exception(msg) from e
        finally:
            if c:
                c.close()

        try:
            # We leave the returned XML undecoded, and let lxml decode it based on
            # the embedded encoding declaration.
            root = lxml.etree.XML(response)
        except Exception as e:
            log.error('Exception')
            assert False, 'XML parse error: ' + str(e)

        assert root.tag == 'doi_batch_diagnostic', 'unexpected response root element: ' + root.tag
        assert 'status' in root.attrib, 'missing doi_batch_diagnostic/status attribute'
        if root.attrib['status'] != 'completed':
            return 'submitted', root.attrib['status']
        else:
            d = root.findall('record_diagnostic')
            assert len(d) == 1, (
                f'<doi_batch_diagnostic> element contains {self._notOne(len(d))} '
                f'<record_diagnostic> element'
            )
            d = d[0]
            assert 'status' in d.attrib, 'missing record_diagnostic/status attribute'
            if d.attrib['status'] == 'Success':
                return 'completed successfully', None
            elif d.attrib['status'] in ['Warning', 'Failure']:
                m = d.findall('msg')
                assert len(m) == 1, (
                    f'<record_diagnostic> element contains {self._notOne(len(m))} ' f'<msg> element'
                )
                m = m[0].text
                e = d.find('conflict_id')
                if e is not None:
                    m += '\nconflict_id=' + e.text
                for e in d.xpath('dois_in_conflict/doi'):
                    m += '\nin conflict with: ' + e.text
                return f'completed with {d.attrib["status"].lower()}', m
            else:
                assert False, 'unexpected status value: ' + d.attrib['status']

    def _sendEmail(self, emailAddress: str, task_model: ezidapp.models.async_queue.CrossrefQueue):
        warning_or_error_str = 'warning' if task_model.status == self.queue.WARNING else 'error'
        ref_id = task_model.refIdentifier
        body_str = (
            'EZID received a{} {} in registering an identifier of yours with '
            'Crossref.\n\n'
            'Identifier: {}\n\n'
            'Status: {}\n\n'
            'Crossref message: {}\n\n'
            'The identifier can be viewed in EZID at:\n'
            '{}\n\n'
            'You are receiving this message because your account is configured to '
            'receive Crossref errors and warnings. This is an automated email. '
            'Please do not reply.\n'.format(
                'n' if warning_or_error_str == 'error' else '',
                warning_or_error_str,
                ref_id.identifier,
                ref_id.get_status_display(),
                task_model.message if task_model.message != '' else '(unknown reason)',
                f'{django.conf.settings.EZID_BASE_URL}/id/{urllib.parse.quote(ref_id.identifier, ":/")}',
            )
        )

        to_str = emailAddress
        from_str = django.conf.settings.SERVER_EMAIL
        subject_str = f'Crossref registration {warning_or_error_str}'

        if django.conf.settings.DEBUG:
            log.info(
                f'Skipped sending the following email due to running in DEBUG mode:\n'
                f'To: {to_str}\n'
                f'From: {from_str}\n'
                f'Subject: {subject_str}\n'
                f'Body: {body_str}\n'
            )
            return

        try:
            django.core.mail.send_mail(
                subject_str, body_str, from_str, [to_str], fail_silently=True
            )
        except Exception as e:
            log.error('Exception')
            raise self._wrapException('error sending email', e)

    def _wrapException(self, context, exception):
        m = str(exception)
        if len(m) > 0:
            m = ': ' + m
        return Exception(f'Crossref error: {context}: {type(exception).__name__}{m}')

    def _oneLine(self, s):
        return re.sub(r'\s', ' ', s)

    def _notOne(self, n):
        if n == 0:
            return 'no'
        else:
            return 'more than one'

    def _addDeclaration(self, document):
        # We don't use lxml's xml_declaration argument because it doesn't allow us to
        # add a basic declaration without also adding an encoding declaration, which we
        # don't want.
        return '<?xml version="1.0"?>\n' + document
