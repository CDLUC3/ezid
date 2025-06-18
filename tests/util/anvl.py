#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import codecs
import logging
import re
import time

log = logging.getLogger(__name__)


ENCODING = 'utf-8'


def format_request(args):
    request = []
    for i in range(0, len(args), 2):
        k = args[i]
        if k == "@":
            f = codecs.open(args[i + 1], encoding=ENCODING)
            request += [l.strip("\r\n") for l in f.readlines()]
            f.close()
        else:
            if k == "@@":
                k = "@"
            else:
                k = re.sub("[%:\r\n]", (lambda c: f"%{ord(c.group(0)):02X}"), k)
            v = args[i + 1]
            if v.startswith("@@"):
                v = v[1:]
            elif v.startswith("@") and len(v) > 1:
                f = codecs.open(v[1:], encoding=ENCODING)
                v = f.read()
                f.close()
            v = re.sub("[%\r\n]", (lambda c: f"%{ord(c.group(0)):02X}"), v)
            request.append(f"{k}: {v}")
    return "\n".join(request)


def response_to_dict(response, format_timestamps=True, decode=False):
    res = {"status": "unknown", "status_message": "no content", "body": ""}
    if response is None:
        return res
    response = response.splitlines()
    # Treat the first response line as the status
    # success: ark:/99999/fk4989sj8r
    # success: doi:10.15697/FK2Z81B | ark:/c5697/fk2z81b
    K, V = response[0].split(b":", 1)
    res["status"] = K
    res["status_message"] = V.strip(b" ")
    for line in response[1:]:
        try:
            K, V = line.split(b":", 1)
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
            K = K.decode('utf-8')
            log.debug("K : V = %s : %s", K, V)
            res[K] = V
        except ValueError:
            res["body"] += line
    return res


def response_to_text(
    response,
    sort_lines=False,
    format_timestamps=True,
    decode=False,
    one_line=False,
    encoding="utf-8",
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
    return b"\n".join(lines)
