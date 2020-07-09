"""
Minimal EZID API client lib to support testing.

This minimal client lib for the EZID API is intended for supporting integrations tests and hence is
developed using the same version of python utilized by the EZID application.

Based on https://github.com/CDLUC3/ezid-client-tools
"""

import codecs
import logging
import re
import time
import urllib
import urllib2


class EZIDHTTPErrorProcessor(urllib2.HTTPErrorProcessor):
    def http_response(self, request, response):
        # Bizarre that Python leaves this out.
        if response.code == 201:
            return response
        else:
            return urllib2.HTTPErrorProcessor.http_response(self, request, response)

    https_response = http_response


class EZIDClient(object):
    def __init__(
        self,
        server_url,
        session_id=None,
        username=None,
        password=None,
        encoding="UTF-8",
    ):
        self._L = logging.getLogger(self.__class__.__name__)
        self._server = server_url.strip("/")
        self._cookie = session_id
        self._encoding = encoding
        self._opener = urllib2.build_opener(EZIDHTTPErrorProcessor())
        self._username = username  # preserve for test validation
        if self._cookie is None:
            self._setAuthHandler(username, password)

    def _encode(self, id):
        return urllib.quote(id, ":/")

    def _setAuthHandler(self, username, password):
        h = urllib2.HTTPBasicAuthHandler()
        h.add_password("EZID", self._server, username, password)
        self._opener.add_handler(h)

    def formatAnvlRequest(self, args):
        request = []
        for i in range(0, len(args), 2):
            k = args[i].decode(self._encoding)
            if k == "@":
                f = codecs.open(args[i + 1], encoding=self._encoding)
                request += [l.strip("\r\n") for l in f.readlines()]
                f.close()
            else:
                if k == "@@":
                    k = "@"
                else:
                    k = re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), k)
                v = args[i + 1].decode(self._encoding)
                if v.startswith("@@"):
                    v = v[1:]
                elif v.startswith("@") and len(v) > 1:
                    f = codecs.open(v[1:], encoding=self._encoding)
                    v = f.read()
                    f.close()
                v = re.sub("[%\r\n]", lambda c: "%%%02X" % ord(c.group(0)), v)
                request.append("%s: %s" % (k, v))
        return "\n".join(request)

    def anvlresponseToDict(
        self, response, format_timestamps=True, decode=False, encoding="UTF-8"
    ):
        res = {"status": "unknown", "status_message": "no content", "body": ""}
        if response is None:
            return res
        response = response.splitlines()
        # Treat the first response line as the status
        K, V = response[0].split(":", 1)
        res["status"] = K
        res["status_message"] = V.strip(" ")
        for line in response[1:]:
            try:
                K, V = line.split(":", 1)
                V = V.strip()
                if format_timestamps and (K == "_created:" or K == "_updated:"):
                    ls = line.split(":")
                    V = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(ls[1])))
                if decode:
                    V = re.sub(
                        "%([0-9a-fA-F][0-9a-fA-F])",
                        lambda m: chr(int(m.group(1), 16)),
                        V,
                    )
                self._L.debug("K : V = %s : %s", K, V)
                res[K] = V
            except ValueError as e:
                res["body"] += line
        return res

    def anvlResponseToText(
        self,
        response,
        sort_lines=False,
        format_timestamps=True,
        decode=False,
        one_line=False,
        encoding="UTF-8",
    ):
        lines = []
        if response is None:
            return None
        response = response.splitlines()
        if sort_lines and len(response) >= 1:
            statusLine = response[0]
            response = response[1:]
            response.sort()
            response.insert(0, statusLine)
        for line in response:
            if format_timestamps and (
                line.startswith("_created:") or line.startswith("_updated:")
            ):
                ls = line.split(":")
                line = (
                    ls[0]
                    + ": "
                    + time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(ls[1])))
                )
            if decode:
                line = re.sub(
                    "%([0-9a-fA-F][0-9a-fA-F])",
                    lambda m: chr(int(m.group(1), 16)),
                    line,
                )
            if one_line:
                line = line.replace("\n", " ").replace("\r", " ")
            lines.append(line.encode(encoding))
        return "\n".join(lines)

    def issueRequest(self, path, method, data=None, dest_f=None):
        url = "%s/%s" % (self._server, path)
        self._L.info("sending request: %s", url)
        request = urllib2.Request(url)
        request.get_method = lambda: method
        response = None
        if data is not None:
            request.add_header("Content-Type", "text/plain; charset=UTF-8")
            request.add_data(data.encode("UTF-8"))
        if self._cookie is not None:
            request.add_header("Cookie", self._cookie)
        try:
            connection = self._opener.open(request)
            if not dest_f is None:
                while True:
                    dest_f.write(connection.read(1))
                    dest_f.flush()
            else:
                response = connection.read()
                return response.decode("UTF-8"), connection.info()
        except urllib2.HTTPError, e:
            self._L.error("%d %s" % (e.code, e.msg))
            if e.fp != None:
                response = e.fp.read()
                self._L.error(response)
        return response, {}

    def login(self, username=None, password=None):
        if not username is None:
            self._setAuthHandler(username, password)
            self._cookie = None
        response, headers = self.issueRequest("login", "GET")
        try:
            self._cookie = headers.get("set-cookie", "").split(";")[0].split("=")[1]
            response += "\nsessionid=%s\n" % self._cookie
        except IndexError as e:
            self._L.warning("No sessionid cookie in response.")
        return self.anvlresponseToDict(response)

    def logout(self):
        response, headers = self.issueRequest("logout", "GET")
        return self.anvlresponseToDict(response)

    def status(self):
        response, headers = self.issueRequest("status", "GET")
        return self.anvlresponseToDict(response)

    def mint(self, shoulder, params=None):
        if params is None:
            params = []
        data = self.formatAnvlRequest(params)
        url = "shoulder/" + self._encode(shoulder)
        response, headers = self.issueRequest(url, "POST", data=data)
        return self.anvlresponseToDict(response)

    def view(self, pid, bang=False):
        path = "id/" + self._encode(pid)
        if bang:
            path += "?prefix_match=yes"
        response, headers = self.issueRequest(path, "GET")
        return self.anvlresponseToDict(response)
