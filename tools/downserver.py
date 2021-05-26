#! /usr/bin/env python

# Standalone server that mimics EZID, but only indicates that the
# system is down.  Specifically, all UI requests, regardless of HTTP
# method, return a 200 OK status and an HTML page containing the
# message "EZID is down for maintenance".  All API requests,
# regardless of HTTP method, return a 503 Service Unavailable status
# and the plain text response "error: EZID is down for maintenance".
# Additionally, API requests return a Retry-After header.  In all
# cases, a different message may be specified on the command line.
# Usage:
#
#    downserver [-ssl keyfile certfile] host port downtime [message]
#
# 'host' and 'port' are the hostname (or IP address) and port the
# server should listen on.  'downtime' is the number of seconds it is
# anticipated that EZID will be down; it is used to compute
# Retry-After headers.  If the '-ssl' option is given, an https server
# is created.
#
# If a file logo.png is found in the same directory as this script,
# the image is inserted in HTML pages.
#
# Greg Janee <gjanee@ucop.edu>
# September 2011

import http.server
import os.path
import re
import socketserver
import ssl
import sys
import time
import xml.sax.saxutils

# import BaseHTTPServer
# import SocketServer

document = """<?xml version="1.0"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>EZID</title>
<style type="text/css">
body { text-align: center; margin-top: 5em; font-family: Helvetica, sans-serif;
  font-weight: bold }
p.big { font-size: 200%% }
</style>
</head>
<body>
%s<p class="big">%s</p>
<p>EZID's regularly scheduled maintenance window is Sunday <a
href="http://www.thetimezoneconverter.com/?t=8:00am&amp;tz=Oakland">8:00am</a>&ndash;<a
href="http://www.thetimezoneconverter.com/?t=9:00am&amp;tz=Oakland">9:00am</a>
Pacific time.</p>
</body>
</html>
"""


def usageError():
    sys.stderr.write(
        "Usage: downserver [-ssl keyfile certfile] host port " + "downtime [message]\n"
    )
    sys.exit(1)


if len(sys.argv) >= 2 and sys.argv[1] == "-ssl":
    if len(sys.argv) < 4:
        usageError()
    https = True
    keyfile = sys.argv[2]
    certfile = sys.argv[3]
    del sys.argv[3]
    del sys.argv[2]
    del sys.argv[1]
else:
    https = False

if (
    len(sys.argv) not in [4, 5]
    or not re.match("\d+$", sys.argv[2])
    or not re.match("\d+$", sys.argv[3])
):
    usageError()
host = sys.argv[1]
port = int(sys.argv[2])
downtime = int(sys.argv[3])
if len(sys.argv) == 5:
    message = sys.argv[4]
else:
    message = "EZID is down for maintenance"

logoPath = os.path.join(os.path.split(sys.argv[0])[0], "logo.png")
if os.path.exists(logoPath):
    f = open(logoPath)
    logo = f.read()
    f.close()
    logoLink = "<p><img src=\"logo.png\" alt=\"EZID\"/></p>\n"
else:
    logo = None
    logoLink = ""

document %= logoLink, xml.sax.saxutils.escape(message)

startTime = int(time.time())

# The following two functions are copied from dispatch.py:


def htmlWanted(acceptHeader):
    for mt in acceptHeader.split(","):
        if mt.split(";")[0].strip() in [
            "text/html",
            "application/xml",
            "application/xhtml+xml",
        ]:
            return True
    return False


def isUiRequest(headers):
    return ("user-agent" in headers and "Mozilla" in headers["user-agent"]) or (
        "accept" in headers and htmlWanted(headers["accept"])
    )


class MyHandler(http.server.BaseHTTPRequestHandler):
    # class MyHandler (six.BaseHTTPServer. BaseHTTPRequestHandler):
    def sendResponse(self, status, type, length, content):
        self.send_response(status)
        self.send_header("Content-Type", type)
        self.send_header("Content-Length", length)
        if status == 503:
            d = startTime + downtime - int(time.time())
            if d > 0:
                self.send_header("Retry-After", str(d))
        self.end_headers()
        self.wfile.write(content)
        self.wfile.flush()

    def do_GET(self):
        if isUiRequest(self.headers):
            if (
                self.command == "GET"
                and self.path.endswith("/logo.png")
                and logo is not None
            ):
                self.sendResponse(200, "image/png", len(logo), logo)
            else:
                self.sendResponse(200, "text/html", len(document), document)
        else:
            self.sendResponse(503, "text/plain", len(message) + 7, "error: " + message)

    do_DELETE = do_GET
    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET


# class MyServer (SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
class MyServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


server = MyServer((host, port), MyHandler)
if https:
    # noinspection PyUnboundLocalVariable
    server.socket = ssl.wrap_socket(
        server.socket, keyfile=keyfile, certfile=certfile, server_side=True
    )
server.serve_forever()
