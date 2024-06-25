#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Batch download

Downloads are created by a single daemon thread. The download
creation process is designed to be restartable at any point: if the
server is restarted, the current download resumes where it left off.

When the server is reloaded, a new daemon thread gets created. Race
conditions exist between the old and new threads while the old
thread still exists, but actual conflicts should be very unlikely.
"""

import csv
import os
import os.path
import pathlib
import re
import subprocess
import time
import typing

import django.conf
import django.core.mail
import django.core.management
import django.db

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.model_util
import ezidapp.models.user
import ezidapp.models.util
import impl.anvl
import impl.download
import impl.log
import impl.policy
import impl.util
import impl.util2
import impl.s3


SUFFIX_FORMAT_DICT = {
    ezidapp.models.async_queue.DownloadQueue.ANVL: "txt",
    ezidapp.models.async_queue.DownloadQueue.CSV: "csv",
    ezidapp.models.async_queue.DownloadQueue.XML: "xml",
}


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_DOWNLOAD_ENABLED'
    queue = ezidapp.models.async_queue.DownloadQueue

    def run(self):
        """Run async processing loop forever.

        This command implements its own run loop.
        """
        doSleep = True
        while not self.terminated():
            if doSleep:
                self.sleep(django.conf.settings.DAEMONS_DOWNLOAD_PROCESSING_IDLE_SLEEP)
            try:
                # Try and retrieve a single task from the DownloadQueue
                # Tasks are ordered by sequence of creation.
                # There are several stages of work for a task, so the same
                # task may be retrieved multiple times to complete all the stages
                rs = ezidapp.models.async_queue.DownloadQueue.objects.all().order_by("seq")[:1]
                if len(rs) == 0:
                    # OK to sleep since no work to do
                    doSleep = True
                    continue
                # Process the next stage of the single task
                self._proc_stage(rs[0])
                self._remove_expired_files()
                # Don't sleep while work is in progress
                doSleep = False
            except Exception as e:
                self.log.exception('Exception')
                impl.log.otherError("download.run", e)
                doSleep = True

    def _proc_stage(self, r:ezidapp.models.async_queue.DownloadQueue):
        # Only process one download request at a time
        # Once completed, current is deleted
        if r.stage == ezidapp.models.async_queue.DownloadQueue.CREATE:
            self._createFile(r)
        elif r.stage == ezidapp.models.async_queue.DownloadQueue.HARVEST:
            self._harvest(r)
        elif r.stage == ezidapp.models.async_queue.DownloadQueue.COMPRESS:
            self._compressFile(r)
        elif r.stage == ezidapp.models.async_queue.DownloadQueue.DELETE:
            self._deleteUncompressedFile(r)
        elif r.stage == ezidapp.models.async_queue.DownloadQueue.MOVE:
            self._moveCompressedFile(r)
        elif r.stage == ezidapp.models.async_queue.DownloadQueue.NOTIFY:
            self._notifyRequestor(r)
        else:
            assert False, "unhandled case"

    def _remove_expired_files(self):
        """Generated files are available for download for a specific time period, after
        which they are deleted here.

        To reduce the chance of recursively wiping out an entire filesystem in case of
        bad settings or broken code, we are conservative here and only delete regular
        files that are direct children of the provided dirs.
        """
        now_ts = time.time()
        for download_dir_path in (
            django.conf.settings.DAEMONS_DOWNLOAD_WORK_DIR,
            django.conf.settings.DAEMONS_DOWNLOAD_PUBLIC_DIR,
        ):
            for p in list(pathlib.Path(download_dir_path).glob('*')):
                if (
                    p.is_file()
                    and p.stat().st_mtime
                    < now_ts - django.conf.settings.DAEMONS_DOWNLOAD_FILE_LIFETIME
                ):
                    p.unlink()

    def _wrapException(self, context, exception):
        m = str(exception)
        if len(m) > 0:
            m = ": " + m
        return Exception(f"batch download error: {context}: {type(exception).__name__}{m}")

    def _path(self, r: ezidapp.models.async_queue.DownloadQueue, i: int) -> str:
        # i=1: uncompressed work file
        # i=2: compressed work file
        # i=3: compressed delivery file
        # i=4: request sidecar file
        if i in [1, 2]:
            d = django.conf.settings.DAEMONS_DOWNLOAD_WORK_DIR
        else:
            d = django.conf.settings.DAEMONS_DOWNLOAD_PUBLIC_DIR
        if i == 1:
            s = impl.download.SUFFIX_FORMAT_DICT[r.format]
        elif i in [2, 3]:
            s = self._fileSuffix(r)
        else:
            s = "request"
        return os.path.join(d, f"{r.filename}.{s}")

    def _csvEncode(self, s: str) -> bytes:
        return impl.util.oneLine(s).encode("utf-8")

    def _flushFile(self, f: typing.TextIO):
        f.flush()
        os.fsync(f.fileno())

    def _createFile(self, r: ezidapp.models.async_queue.DownloadQueue):
        f = None
        self.log.debug("createFile: %s", self._path(r, 1))
        try:
            f = open(self._path(r, 1), "w", newline='', encoding="utf-8")
            if r.format == ezidapp.models.async_queue.DownloadQueue.CSV:
                w = csv.writer(f)
                row_list = [self._csvEncode(c) for c in self._decode(r.columns)]
                w.writerow([b.decode('utf-8', errors='replace') for b in row_list])
                self._flushFile(f)
            elif r.format == ezidapp.models.async_queue.DownloadQueue.XML:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<records>')
                self._flushFile(f)
            # We don't know exactly what the CSV writer wrote, so we must
            # probe the file to find its size.
            n = f.tell()
        except Exception as e:
            self.log.exception('Exception')
            raise self._wrapException("error creating file", e)
        else:
            # This is run if there's no exception thrown
            r.stage = ezidapp.models.async_queue.DownloadQueue.HARVEST
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

    def _prepareMetadata(
        self,
        id_model: ezidapp.models.identifier.SearchIdentifier,
        convertTimestamps: object,
    ) -> dict:
        d = id_model.toLegacy()
        ezidapp.models.model_util.convertLegacyToExternal(d)
        if id_model.isDoi:
            d["_shadowedby"] = id_model.arkAlias
        if convertTimestamps:
            d["_created"] = impl.util.formatTimestampZulu(int(d["_created"]))
            d["_updated"] = impl.util.formatTimestampZulu(int(d["_updated"]))
        return d

    def _writeAnvl(
        self, f: typing.TextIO, id_model: ezidapp.models.identifier.Identifier, metadata: dict
    ):
        if f.tell() > 0:
            f.write("\n")
        f.write(f":: {id_model.identifier}\n")
        # f is a text file handle, opened with utf-8 encoding
        f.write(impl.anvl.format(metadata))

    def _writeCsv(
        self,
        f: typing.TextIO,
        columns,
        id_model: ezidapp.models.identifier.SearchIdentifier,
        metadata: dict,
    ):
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
        w.writerow([self._csvEncode(c).decode('utf-8', errors='replace') for c in l])

    def _writeXml(
        self, f: typing.TextIO, id: ezidapp.models.identifier.SearchIdentifier, metadata: dict
    ):
        f.write(f'<record identifier="{impl.util.xmlEscape(id.identifier)}">')
        for k, v in list(metadata.items()):
            if k in ["datacite", "crossref"]:
                v = impl.util.removeXmlDeclaration(v)
            else:
                v = impl.util.xmlEscape(v)
            f.write(f'<element name="{impl.util.xmlEscape(k)}">{v}</element>')
        f.write("</record>")

    def _harvest1(self, r: ezidapp.models.async_queue.DownloadQueue, f: typing.TextIO):
        columns = self._decode(r.columns)
        constraints = self._decode(r.constraints)
        options = self._decode(r.options)
        _total = 0
        while not self.terminated():
            qs = (
                ezidapp.models.identifier.SearchIdentifier.objects.filter(identifier__gt=r.lastId)
                .filter(owner__pid=r.toHarvest.split(",")[r.currentIndex])
                .select_related("owner", "ownergroup", "datacenter", "profile")
                .order_by("identifier")
            )
            # self.log.debug("Query issued: %s", str(qs.query))
            ids = list(qs[:1000])
            self.log.debug("Total query matches: %s", len(ids))
            if len(ids) == 0:
                break
            try:
                for id in ids:
                    if self._satisfiesConstraints(id, constraints):
                        m = self._prepareMetadata(id, options["convertTimestamps"])
                        if r.format == ezidapp.models.async_queue.DownloadQueue.ANVL:
                            self._writeAnvl(f, id, m)
                        elif r.format == ezidapp.models.async_queue.DownloadQueue.CSV:
                            self._writeCsv(f, columns, id, m)
                        elif r.format == ezidapp.models.async_queue.DownloadQueue.XML:
                            self._writeXml(f, id, m)
                        else:
                            assert False, "unhandled case"
                        _total += 1
                self._flushFile(f)
            except Exception as e:
                self.log.exception('Exception')
                raise self._wrapException("error writing file", e)
            r.lastId = ids[-1].identifier
            r.fileSize = f.tell()
            r.save()
        if self.terminated():
            self.log.warning("Harvest terminated.")
        else:
            self.log.info("Total records exported: %s", _total)

    def _harvest(self, r: ezidapp.models.async_queue.DownloadQueue):
        f = None
        try:
            try:
                assert os.path.getsize(self._path(r, 1)) >= r.fileSize, "file is short"
                f = open(self._path(r, 1), "r+")
                f.seek(r.fileSize)
                f.truncate()
            except Exception as e:
                self.log.exception('Exception')
                raise self._wrapException("error re-opening/seeking/truncating file", e)
            start = r.currentIndex
            for i in range(r.currentIndex, len(r.toHarvest.split(","))):
                if i > start:
                    r.currentIndex = i
                    r.lastId = ""
                    r.save()
                self._harvest1(r, f)
            if r.format == ezidapp.models.async_queue.DownloadQueue.XML:
                try:
                    f.write("</records>")
                    self._flushFile(f)
                except Exception as e:
                    self.log.exception('Exception')
                    raise self._wrapException("error writing file footer", e)
            r.stage = ezidapp.models.async_queue.DownloadQueue.COMPRESS
            r.save()
        finally:
            if f:
                f.close()

    def _compressFile(self, r: ezidapp.models.async_queue.DownloadQueue):
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
            if r.compression == ezidapp.models.async_queue.DownloadQueue.GZIP:
                infile = open(self._path(r, 1))
                outfile = open(self._path(r, 2), "w")
                # noinspection PyTypeChecker
                p = subprocess.Popen(
                    [django.conf.settings.GZIP_COMMAND],
                    stdin=infile,
                    stdout=outfile,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    env={},
                )
                stderr = p.communicate()[1]
            else:
                p = subprocess.Popen(
                    [
                        django.conf.settings.ZIP_COMMAND,
                        "-jq",
                        self._path(r, 2),
                        self._path(r, 1),
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    close_fds=True,
                    env={},
                )
                stderr = p.communicate()[0]
            assert (
                p.returncode == 0 and stderr == b''
            ), f"compression command returned status code {p.returncode:d}, stderr '{stderr}'"
        except Exception as e:
            self.log.exception('Exception')
            raise self._wrapException("error compressing file", e)
        else:
            r.stage = ezidapp.models.async_queue.DownloadQueue.DELETE
            r.save()
        finally:
            if infile:
                infile.close()
            if outfile:
                outfile.close()

    def _deleteUncompressedFile(self, r: ezidapp.models.async_queue.DownloadQueue):
        try:
            if os.path.exists(self._path(r, 1)):
                os.unlink(self._path(r, 1))
        except Exception as e:
            self.log.exception('Exception')
            raise self._wrapException("error deleting uncompressed file", e)
        else:
            r.stage = ezidapp.models.async_queue.DownloadQueue.MOVE
            r.save()

    def _moveCompressedFile(self, r: ezidapp.models.async_queue.DownloadQueue):
        try:
            if os.path.exists(self._path(r, 2)):
                local_file_path = self._path(r, 2)
                filename = os.path.basename(local_file_path)
                bucket_name = django.conf.settings.S3_BUCKET
                s3_object_key = f"{django.conf.settings.S3_BUCKET_DOWNLOAD_PATH}/{filename}"
                impl.s3.upload_file(local_file_path, bucket_name, s3_object_key)
            else:
                assert os.path.exists(self._path(r, 3)), "file has disappeared"
        except Exception as e:
            self.log.exception('Exception')
            raise self._wrapException("error moving compressed file", e)
        else:
            r.stage = ezidapp.models.async_queue.DownloadQueue.NOTIFY
            r.save()

    def _notifyRequestor(self, r: ezidapp.models.async_queue.DownloadQueue):
        f = None
        try:
            f = open(self._path(r, 4), mode="w", encoding="utf-8")
            f.write(f"{ezidapp.models.util.getUserByPid(r.requestor).username}\n{r.rawRequest}\n")
        except Exception as e:
            self.log.exception('Exception')
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
                f"{salutation}Thank you for using EZID to easily create and manage "
                "your identifiers. The batch download you requested is available "
                "at:\n\n"
                f"{django.conf.settings.EZID_BASE_URL}/s3_download/{r.filename}.{self._fileSuffix(r)}\n\n"
                "The download will be deleted in 1 week.\n\n"
                "Best,\n"
                "EZID Team\n\n"
                "This is an automated email. Please do not reply.\n"
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
                self.log.exception('Exception')
                raise self._wrapException("error sending email", e)
        r.delete()

    def _unescape(self, s: str) -> str:
        return re.sub("%([0-9A-F][0-9A-F])", lambda m: chr(int(m.group(1), 16)), s)

    def _decode(self, s: str):
        '''
        Decodes DownloadQueue.constraint
        '''
        if s[0] == "B":
            # boolean
            return s[1:] == "True"
        elif s[0] == "I":
            # integer
            return int(s[1:])
        elif s[0] == "S":
            # string
            return s[1:]
        elif s[0] == "L":
            # list, from comma separated string of constraints
            if len(s) > 1:
                return [self._decode(self._unescape(i)) for i in s[1:].split(",")]
            else:
                return []
        elif s[0] == "D":
            # dict, from comma separated list of k=v
            if len(s) > 1:
                return dict(
                    list(
                        map(
                            lambda i: tuple(
                                [self._decode(self._unescape(kv)) for kv in i.split("=")]
                            ),
                            s[1:].split(","),
                        )
                    )
                )
            else:
                return {}
        else:
            assert False, "unhandled case"

    def _fileSuffix(self, r: ezidapp.models.async_queue.DownloadQueue):
        if r.compression == ezidapp.models.async_queue.DownloadQueue.GZIP:
            return SUFFIX_FORMAT_DICT[r.format] + ".gz"
        else:
            return "zip"
