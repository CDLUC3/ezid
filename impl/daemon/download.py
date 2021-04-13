# =============================================================================
#
# EZID :: download.py
#
# Batch download.
#
# Downloads are created by a single daemon thread.  The download
# creation process is designed to be restartable at any point: if the
# server is restarted, the current download resumes where it left off.
#
# When the server is reloaded, a new daemon thread gets created.  Race
# conditions exist between the old and new threads while the old
# thread still exists, but actual conflicts should be very unlikely.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import impl.daemon.daemon_base
import csv
import hashlib
import os
import os.path
import re
import subprocess
import threading
import time
import uuid

import django.conf
import django.core.mail
import django.db

import ezidapp.models.download_queue
import ezidapp.models.model_util
import ezidapp.models.search_identifier
import ezidapp.models.store_group
import ezidapp.models.store_user
import impl.anvl
import impl.log
import impl.policy
import impl.util
import impl.util2
import impl.daemon.daemon_base


_lock = threading.Lock()


class _ValidationException(Exception):
    pass

    # _usedFilenames = None
    #
    # _lock.acquire()
    # try:
    #     if _usedFilenames is None:
    #         _usedFilenames = [
    #             r.filename
    #             for r in ezidapp.models.download_queue.DownloadQueue.objects.all()
    #         ] + [
    #             f.split(".")[0]
    #             for f in os.listdir(django.conf.settings.DOWNLOAD_PUBLIC_DIR)
    #         ]
    # finally:
    #     _lock.release()
    #
    # _formatCode = {
    #     "anvl": ezidapp.models.download_queue.DownloadQueue.ANVL,
    #     "csv": ezidapp.models.download_queue.DownloadQueue.CSV,
    #     "xml": ezidapp.models.download_queue.DownloadQueue.XML,
    # }
    #
    # _formatSuffix = {
    #     ezidapp.models.download_queue.DownloadQueue.ANVL: "txt",
    #     ezidapp.models.download_queue.DownloadQueue.CSV: "csv",
    #     ezidapp.models.download_queue.DownloadQueue.XML: "xml",
    # }
    #
    # _compressionCode = {
    #     "gzip": ezidapp.models.download_queue.DownloadQueue.GZIP,
    #     "zip": ezidapp.models.download_queue.DownloadQueue.ZIP,
    # }
    #
    # _daemonEnabled = (
    #     django.conf.settings.DAEMON_THREADS_ENABLED
    #     and django.conf.settings.DAEMONS_DOWNLOAD_ENABLED
    # )
    # if _daemonEnabled:
    #     _threadName = uuid.uuid1().hex
    #     t = threading.Thread(target=_daemonThread, name=_threadName)
    #     t.setDaemon(True)
    #     t.start()


class DownloadDaemon(impl.daemon.daemon_base.DaemonBase):
    def __init__(self):
        self._params = {
            # name: (repeatable, validator)
            "column": (
                True,
                self._params._validateString,
            ),
            "convertTimestamps": (
                False,
                self._params._validateBoolean,
            ),
            "createdAfter": (
                False,
                self._params._validateTimestamp,
            ),
            "createdBefore": (
                False,
                self._params._validateTimestamp,
            ),
            "crossref": (
                False,
                self._params._validateBoolean,
            ),
            "datacite": (
                False,
                self._params._validateBoolean,
            ),
            "exported": (
                False,
                self._params._validateBoolean,
            ),
            "format": (
                False,
                lambda v: self._params._validateEnumerated(v, ["anvl", "csv", "xml"]),
            ),
            "compression": (
                False,
                lambda v: self._params._validateEnumerated(v, ["gzip", "zip"]),
            ),
            "notify": (
                True,
                self._params._validateString,
            ),
            "owner": (
                True,
                self._params._validateUser,
            ),
            "ownergroup": (
                True,
                self._params._validateGroup,
            ),
            "permanence": (
                False,
                lambda v: self._params._validateEnumerated(v, ["test", "real"]),
            ),
            "profile": (
                True,
                self._params._validateString,
            ),
            "status": (
                True,
                lambda v: self._params._validateEnumerated(
                    v, ["reserved", "public", "unavailable"]
                ),
            ),
            "type": (
                True,
                lambda v: self._params._validateEnumerated(v, ["ark", "doi", "uuid"]),
            ),
            "updatedAfter": (
                False,
                self._params._validateTimestamp,
            ),
            "updatedBefore": (
                False,
                self._params._validateTimestamp,
            ),
        }
        super(DownloadDaemon, self).__init__()

    @staticmethod
    def _validateString(self, v):
        s = v.strip()
        if s == "":
            raise _ValidationException("empty value")
        return s

    @staticmethod
    def _validateEnumerated(self, v, l):
        if v not in l:
            raise _ValidationException("invalid parameter value")
        return v

    @staticmethod
    def _validateBoolean(self, v):
        return self._validateEnumerated(v, ["yes", "no"]) == "yes"

    @staticmethod
    def _validateTimestamp(self, v):
        try:
            try:
                return impl.util.parseTimestampZulu(v)
            except Exception:
                return int(v)
        except Exception:
            raise _ValidationException("invalid timestamp")

    @staticmethod
    def _validateUser(self, v):
        u = ezidapp.models.store_user.getUserByUsername(v)
        if u is not None and not u.isAnonymous:
            return u
        else:
            raise _ValidationException("no such user")

    @staticmethod
    def _validateGroup(self, v):
        g = ezidapp.models.store_group.getGroupByGroupname(v)
        if g is not None and not g.isAnonymous:
            return g
        else:
            raise _ValidationException("no such group")

    # A simple encoding mechanism for storing Python objects as strings
    # follows.  We could use pickling, but this technique makes debugging
    # a little easier.

    def _escape(self, s):
        return re.sub("[%,=]", lambda c: f"%{ord(c.group(0)):02X}", s)

    def _encode(self, o):
        if type(o) is bool:
            return "B" + str(o)
        elif type(o) is int:
            return "I" + str(o)
        elif type(o) in [str, str]:
            return "S" + o
        elif type(o) is list:
            return "L" + ",".join([self._escape(self._encode(i)) for i in o])
        elif type(o) is dict:
            return "D" + ",".join(
                map(
                    lambda kv: f"{self._escape(self._encode(kv[0]))}={self._escape(self._encode(kv[1]))}",
                    list(o.items()),
                )
            )
        else:
            assert False, "unhandled case"

    def _unescape(self, s):
        return re.sub("%([0-9A-F][0-9A-F])", lambda m: chr(int(m.group(1), 16)), s)

    def _decode(self, s):
        if s[0] == "B":
            return s[1:] == "True"
        elif s[0] == "I":
            return int(s[1:])
        elif s[0] == "S":
            return s[1:]
        elif s[0] == "L":
            if len(s) > 1:
                return [self._decode(self._unescape(i)) for i in s[1:].split(",")]
            else:
                return []
        elif s[0] == "D":
            if len(s) > 1:
                return dict(
                    list(
                        map(
                            lambda i: tuple(
                                [
                                    self._decode(self._unescape(kv))
                                    for kv in i.split("=")
                                ]
                            ),
                            s[1:].split(","),
                        )
                    )
                )
            else:
                return {}
        else:
            assert False, "unhandled case"

    def _generateFilename(self, requestor):
        while True:
            f = hashlib.sha1(
                f"{requestor},{str(time.time())},{django.conf.settings.SECRET_KEY}"
            ).hexdigest()[::4]
            _lock.acquire()
            try:
                if f not in self._usedFilenames:
                    # noinspection PyUnresolvedReferences
                    _usedFilenames.append(f)
                    return f
            finally:
                _lock.release()

    def enqueueRequest(self, user, request):
        """Enqueues a batch download request.  The request must be authenticated;
        'user' should be a StoreUser object.  'request' should be a
        django.http.QueryDict object (from a POST request or manually created)
        containing the parameters of the request.  The available parameters are
        described in the API documentation.  One feature not mentioned in the
        documentation: for the 'notify' parameter, an email address may be a
        straight address ("fred@slate.com") or may include an addressee name ("Fred
        Flintstone <fred@slate.com>"); in the latter case a salutation line will be
        added to the email message.

        The successful return is a string that includes the download URL, as
        in:

          success: https://ezid.cdlib.org/download/da543b91a0.xml.gz

        Unsuccessful returns include the strings:

          error: forbidden
          error: bad request - subreason...
          error: internal server error
        """

        def error(s):
            return "error: bad request - " + s

        try:
            d = {}
            for k in request:
                if k not in self._params:
                    return error("invalid parameter: " + impl.util.oneLine(k))
                try:
                    if self._params[k][0]:
                        d[k] = list(map(self._params[k][1], request.getlist(k)))
                    else:
                        if len(request.getlist(k)) > 1:
                            return error("parameter is not repeatable: " + k)
                        d[k] = self._params[k][1](request[k])
                except _ValidationException as e:
                    return error(f"parameter '{k}': {str(e)}")
            if "format" not in d:
                return error("missing required parameter: format")
            format = d["format"]
            del d["format"]
            if "compression" in d:
                compression = d["compression"]
                del d["compression"]
            else:
                compression = "gzip"
            if format == "csv":
                if "column" not in d:
                    return error("format 'csv' requires at least one column")
                columns = d["column"]
                del d["column"]
            else:
                if "column" in d:
                    return error("parameter is incompatible with format: column")
                columns = []
            toHarvest = []
            if "owner" in d:
                for o in d["owner"]:
                    if not impl.policy.authorizeDownload(user, owner=o):
                        return "error: forbidden"
                    if o.pid not in toHarvest:
                        toHarvest.append(o.pid)
                del d["owner"]
            if "ownergroup" in d:
                for g in d["ownergroup"]:
                    if not impl.policy.authorizeDownload(user, ownergroup=g):
                        return "error: forbidden"
                    for u in g.users.all():
                        if u.pid not in toHarvest:
                            toHarvest.append(u.pid)
                del d["ownergroup"]
            if len(toHarvest) == 0:
                toHarvest = [user.pid]
            if "notify" in d:
                notify = d["notify"]
                del d["notify"]
            else:
                notify = []
            if "convertTimestamps" in d:
                options = {"convertTimestamps": d["convertTimestamps"]}
                del d["convertTimestamps"]
            else:
                options = {"convertTimestamps": False}
            requestor = user.pid
            filename = self._generateFilename(requestor)
            r = ezidapp.models.download_queue.DownloadQueue(
                requestTime=int(time.time()),
                rawRequest=request.urlencode(),
                requestor=requestor,
                format=self._formatCode[format],
                compression=self._compressionCode[compression],
                columns=self._encode(columns),
                constraints=self._encode(d),
                options=self._encode(options),
                notify=self._encode(notify),
                filename=filename,
                toHarvest=",".join(toHarvest),
            )
            r.save()
            return f"success: {django.conf.settings.EZID_BASE_URL}/download/{filename}.{self._fileSuffix(r)}"
        except Exception as e:
            impl.log.otherError("download.enqueueRequest", e)
            if sys.is_running_under_pytest:
                raise
            return "error: internal server error"

    def getQueueLength(self):
        """Returns the length of the batch download queue."""
        return ezidapp.models.download_queue.DownloadQueue.objects.count()

    def _checkAbort(
        self,
    ):
        # This function provides a handy way to abort processing if the
        # daemon is disabled or if a new daemon thread is started by a
        # configuration reload.  It doesn't entirely eliminate potential
        # race conditions between two daemon threads, but it should make
        # conflicts very unlikely.
        if (
            not self._daemonEnabled
            or threading.currentThread().getName() != self._threadName
        ):
            raise self._AbortException()

    def _wrapException(self, context, exception):
        m = str(exception)
        if len(m) > 0:
            m = ": " + m
        return Exception(
            f"batch download error: {context}: {type(exception).__name__}{m}"
        )

    def _fileSuffix(self, r):
        if r.compression == ezidapp.models.download_queue.DownloadQueue.GZIP:
            return self._formatSuffix[r.format] + ".gz"
        else:
            return "zip"

    def _path(self, r, i):
        # i=1: uncompressed work file
        # i=2: compressed work file
        # i=3: compressed delivery file
        # i=4: request sidecar file
        if i in [1, 2]:
            d = django.conf.settings.DOWNLOAD_WORK_DIR
        else:
            d = django.conf.settings.DOWNLOAD_PUBLIC_DIR
        if i == 1:
            s = self._formatSuffix[r.format]
        elif i in [2, 3]:
            s = self._fileSuffix(r)
        else:
            s = "request"
        return os.path.join(d, f"{r.filename}.{s}")

    def _csvEncode(self, s):
        return impl.util.oneLine(s).encode("utf-8")

    def _flushFile(self, f):
        f.flush()
        os.fsync(f.fileno())

    def _createFile(self, r):
        f = None
        try:
            f = open(self._path(r, 1), "wb")
            if r.format == ezidapp.models.download_queue.DownloadQueue.CSV:
                w = csv.writer(f)
                w.writerow([self._csvEncode(c) for c in self._decode(r.columns)])
                self._flushFile(f)
            elif r.format == ezidapp.models.download_queue.DownloadQueue.XML:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n<records>')
                self._flushFile(f)
            # We don't know exactly what the CSV writer wrote, so we must
            # probe the file to find its size.
            n = f.tell()
        except Exception as e:
            raise self._wrapException("error creating file", e)
        else:
            r.stage = ezidapp.models.download_queue.DownloadQueue.HARVEST
            r.fileSize = n
            r.save()
        finally:
            if f:
                f.close()

    def _satisfiesConstraints(self, id_model, constraints):
        for k, v in list(constraints.items()):
            if k == "createdAfter":
                if id_model.createTime < v:
                    return False
            elif k == "createdBefore":
                if id_model.createTime >= v:
                    return False
            elif k == "crossref":
                if id_model.isCrossref ^ v:
                    return False
            elif k == "datacite":
                if id_model.isDatacite ^ v:
                    return False
            elif k == "exported":
                if id_model.exported ^ v:
                    return False
            elif k == "permanence":
                if id_model.isTest ^ (v == "test"):
                    return False
            elif k == "profile":
                if id_model.profile.label not in v:
                    return False
            elif k == "status":
                if id_model.get_status_display() not in v:
                    return False
            elif k == "type":
                if id_model.type not in v:
                    return False
            elif k == "updatedAfter":
                if id_model.updateTime < v:
                    return False
            elif k == "updatedBefore":
                if id_model.updateTime >= v:
                    return False
            else:
                assert False, "unhandled case"
        return True

    def _prepareMetadata(self, id_model, convertTimestamps):
        d = id_model.toLegacy()
        ezidapp.models.model_util.convertLegacyToExternal(d)
        if id_model.isDoi:
            d["_shadowedby"] = id_model.arkAlias
        if convertTimestamps:
            d["_created"] = impl.util.formatTimestampZulu(int(d["_created"]))
            d["_updated"] = impl.util.formatTimestampZulu(int(d["_updated"]))
        return d

    def _writeAnvl(self, f, id_model, metadata):
        if f.tell() > 0:
            f.write("\n")
        f.write(f":: {id_model.identifier}\n")
        f.write(impl.anvl.format(metadata).encode("utf-8"))

    def _writeCsv(self, f, columns, id_model, metadata):
        w = csv.writer(f)
        l = []
        for c in columns:
            if c == "_id":
                l.append(id_model.identifier)
            elif c == "_mappedCreator":
                l.append(id_model.resourceCreator)
            elif c == "_mappedTitle":
                l.append(id_model.resourceTitle)
            elif c == "_mappedPublisher":
                l.append(id_model.resourcePublisher)
            elif c == "_mappedDate":
                l.append(id_model.resourcePublicationDate)
            elif c == "_mappedType":
                l.append(id_model.resourceType)
            else:
                l.append(metadata.get(c, ""))
        w.writerow([self._csvEncode(c) for c in l])

    def _writeXml(self, f, id, metadata):
        f.write(f'<record identifier="{impl.util.xmlEscape(id.identifier)}">')
        for k, v in list(metadata.items()):
            if k in ["datacite", "crossref"]:
                v = impl.util.removeXmlDeclaration(v)
            else:
                v = impl.util.xmlEscape(v)
            f.write(
                f'<element name="{impl.util.xmlEscape(k)}">{v}</element>'.encode(
                    "utf-8"
                )
            )
        f.write("</record>")

    def _harvest1(self, r, f):
        columns = self._decode(r.columns)
        constraints = self._decode(r.constraints)
        options = self._decode(r.options)
        while True:
            self._checkAbort()
            qs = (
                ezidapp.models.search_identifier.SearchIdentifier.objects.filter(
                    identifier__gt=r.lastId
                )
                .filter(owner__pid=r.toHarvest.split(",")[r.currentIndex])
                .select_related("owner", "ownergroup", "datacenter", "profile")
                .order_by("identifier")
            )
            ids = list(qs[:1000])
            if len(ids) == 0:
                break
            try:
                for id in ids:
                    self._checkAbort()
                    if self._satisfiesConstraints(id, constraints):
                        m = self._prepareMetadata(id, options["convertTimestamps"])
                        if r.format == ezidapp.models.download_queue.DownloadQueue.ANVL:
                            self._writeAnvl(f, id, m)
                        elif (
                            r.format == ezidapp.models.download_queue.DownloadQueue.CSV
                        ):
                            self._writeCsv(f, columns, id, m)
                        elif (
                            r.format == ezidapp.models.download_queue.DownloadQueue.XML
                        ):
                            self._writeXml(f, id, m)
                        else:
                            assert False, "unhandled case"
                self._checkAbort()
                self._flushFile(f)
            except self._AbortException:
                raise
            except Exception as e:
                raise self._wrapException("error writing file", e)
            r.lastId = ids[-1].identifier
            r.fileSize = f.tell()
            r.save()

    def _harvest(self, r):
        f = None
        try:
            try:
                assert os.path.getsize(self._path(r, 1)) >= r.fileSize, "file is short"
                f = open(self._path(r, 1), "r+b")
                f.seek(r.fileSize)
                f.truncate()
            except Exception as e:
                raise self._wrapException("error re-opening/seeking/truncating file", e)
            start = r.currentIndex
            for i in range(r.currentIndex, len(r.toHarvest.split(","))):
                self._checkAbort()
                if i > start:
                    r.currentIndex = i
                    r.lastId = ""
                    r.save()
                self._harvest1(r, f)
            self._checkAbort()
            if r.format == ezidapp.models.download_queue.DownloadQueue.XML:
                try:
                    f.write(b"</records>")
                    self._flushFile(f)
                except Exception as e:
                    raise self._wrapException("error writing file footer", e)
            r.stage = ezidapp.models.download_queue.DownloadQueue.COMPRESS
            r.save()
        finally:
            if f:
                f.close()

    def _compressFile(self, r):
        infile = None
        outfile = None
        try:
            # The compression command may be long-lived, and a new daemon
            # thread may be created by a server restart or reload while it is
            # still running, in which case we don't try to kill the old
            # process, but simply delete its output file and let it die a
            # natural death.
            if os.path.exists(self._path(r, 2)):
                os.unlink(self._path(r, 2))
            if r.compression == ezidapp.models.download_queue.DownloadQueue.GZIP:
                infile = open(self._path(r, 1))
                outfile = open(self._path(r, 2), "w")
                # noinspection PyTypeChecker
                p = subprocess.Popen(
                    [self._gzipCommand],
                    stdin=infile,
                    stdout=outfile,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    env={},
                )
                stderr = p.communicate()[1]
            else:
                p = subprocess.Popen(
                    [self._zipCommand, "-jq", self._path(r, 2), self._path(r, 1)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    close_fds=True,
                    env={},
                )
                stderr = p.communicate()[0]
            self._checkAbort()
            assert (
                p.returncode == 0 and stderr == ""
            ), f"compression command returned status code {p.returncode:d}, stderr '{stderr}'"
        except self._AbortException:
            raise
        except Exception as e:
            raise self._wrapException("error compressing file", e)
        else:
            r.stage = ezidapp.models.download_queue.DownloadQueue.DELETE
            r.save()
        finally:
            if infile:
                infile.close()
            if outfile:
                outfile.close()

    def _deleteUncompressedFile(self, r):
        try:
            if os.path.exists(self._path(r, 1)):
                os.unlink(self._path(r, 1))
        except Exception as e:
            raise self._wrapException("error deleting uncompressed file", e)
        else:
            r.stage = ezidapp.models.download_queue.DownloadQueue.MOVE
            r.save()

    def _moveCompressedFile(self, r):
        try:
            if os.path.exists(self._path(r, 2)):
                os.rename(self._path(r, 2), self._path(r, 3))
            else:
                assert os.path.exists(self._path(r, 3)), "file has disappeared"
        except Exception as e:
            raise self._wrapException("error moving compressed file", e)
        else:
            r.stage = ezidapp.models.download_queue.DownloadQueue.NOTIFY
            r.save()

    def _notifyRequestor(self, r):
        f = None
        try:
            f = open(self._path(r, 4), "w")
            f.write(
                f"{ezidapp.models.store_user.getUserByPid(r.requestor).username}\n{r.rawRequest.encode('utf-8')}\n"
            )
        except Exception as e:
            raise self._wrapException("error writing sidecar file", e)
        finally:
            if f:
                f.close()
        for emailAddress in self._decode(r.notify):
            m = re.match("(.*)<([^>]*)>$", emailAddress)
            if m and m.group(1).strip() != "" and m.group(2).strip() != "":
                salutation = f"Dear {m.group(1).strip()},\n\n"
                emailAddress = m.group(2).strip()
            else:
                salutation = ""
            message = (
                "%sThank you for using EZID to easily create and manage "
                "your identifiers.  The batch download you requested is available "
                "at:\n\n"
                "%s/download/%s.%s\n\n"
                "The download will be deleted in 1 week.\n\n"
                "Best,\n"
                "EZID Team\n\n"
                "This is an automated email.  Please do not reply.\n".format(
                    salutation,
                    django.conf.settings.EZID_BASE_URL,
                    r.filename,
                    self._fileSuffix(r),
                )
            )
            try:
                django.core.mail.send_mail(
                    "Your EZID batch download link",
                    message,
                    django.conf.settings.SERVER_EMAIL,
                    [emailAddress],
                    fail_silently=True,
                )
            except Exception as e:
                raise self._wrapException("error sending email", e)
        r.delete()

    def _daemonThread(
        self,
    ):
        doSleep = True
        while True:
            if doSleep:
                django.db.connections["default"].close()
                django.db.connections["search"].close()
                # noinspection PyTypeChecker
                time.sleep(django.conf.settings.DAEMONS_DOWNLOAD_PROCESSING_IDLE_SLEEP)
            try:
                self._checkAbort()
                r = ezidapp.models.download_queue.DownloadQueue.objects.all().order_by(
                    "seq"
                )[:1]
                if len(r) == 0:
                    doSleep = True
                    continue
                r = r[0]
                self._checkAbort()
                if r.stage == ezidapp.models.download_queue.DownloadQueue.CREATE:
                    self._createFile(r)
                elif r.stage == ezidapp.models.download_queue.DownloadQueue.HARVEST:
                    self._harvest(r)
                elif r.stage == ezidapp.models.download_queue.DownloadQueue.COMPRESS:
                    self._compressFile(r)
                elif r.stage == ezidapp.models.download_queue.DownloadQueue.DELETE:
                    self._deleteUncompressedFile(r)
                elif r.stage == ezidapp.models.download_queue.DownloadQueue.MOVE:
                    self._moveCompressedFile(r)
                elif r.stage == ezidapp.models.download_queue.DownloadQueue.NOTIFY:
                    self._notifyRequestor(r)
                else:
                    assert False, "unhandled case"
                doSleep = False
            except self._AbortException:
                break
            except Exception as e:
                impl.log.otherError("download._daemonThread", e)
                doSleep = True
