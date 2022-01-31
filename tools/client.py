#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# noinspection SpellCheckingInspection

"""EZID command line client

Positional arguments:

  server:
    l (local server, no https)
    s (staging)
    p (production)
    http[s]://...

  credentials:
    username:password
    username (password will be prompted for)
    sessionid=... (as returned by previous login)
    - (none)

  operation:
    m[int] shoulder [element value ...]
    c[reate][!] identifier [element value ...]
      create! = create or update
    v[iew][!] identifier
      view! = match longest identifier prefix
    u[pdate] identifier [element value ...]
    d[elete] identifier
    login
    logout
    s[tatus] [detailed] [*|subsystemlist]
    V[ersion]
    p[ause] {on|off|idlewait|monitor}
    r[eload]

In the above, if an element is "@", the subsequent value is treated as a filename and
metadata elements are read from the named ANVL-formatted file. For example, if file
metadata.txt contains:

  erc.who: Proust, Marcel
  erc.what: Remembrance of Things Past
  erc.when: 1922

then an identifier with that metadata can be minted by invoking:

  client p username:password mint ark:/99999/fk4 @ metadata.txt

Otherwise, if a value has the form "@filename", a (single) value is read from the named
file. For example, if file metadata.xml contains a DataCite XML record, then an
identifier with that record as the value of the 'datacite' element can be minted by
invoking:

  client p username:password mint doi:10.5072/FK2 datacite @metadata.xml

In both of the above cases, the interpretation of @ can be defeated by doubling it.

Input metadata (from command line parameters and files) is assumed to be UTF-8 encoded,
and output metadata is UTF-8 encoded, unless overridden by the -e option. By default,
ANVL responses (currently, that's all responses) are left in %-encoded form.
"""
import argparse
import codecs
import getpass
import re
import signal
import ssl
import sys
import time
import types
import urllib.error
import urllib.parse
import urllib.request

# Suppress KeyboardInterrupt exception traceback if exited with Ctrl-C
signal.signal(signal.SIGINT, lambda signal, frame: sys.exit())

KNOWN_SERVERS = {
    'l': 'http://localhost:8000',
    's': 'https://uc3-ezidx2-stg.cdlib.org',
    'p': 'https://ezid.cdlib.org',
}


CMD_TUP = (
    'mint',
    'create',
    'view',
    'update',
    'delete',
    'login',
    'logout',
    'status',
    'Version',
)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        'server',
        help='EZID server to access. l=local (no https), s=staging, p=production, http[s]://...',
    )
    parser.add_argument(
        'credentials',
        help='username:password, username (will prompt for password), sessionid=... (as returned by previous login), - (none)',
    )
    parser.add_argument(
        'operation',
        nargs='+',
        help='m[int], c[reate], create!, v[iew], view!, u[pdate], d[elete], login, logout, s[tatus], V[ersion]',
    )

    parser.add_argument(
        '-d',
        action='store_true',
        dest='decode',
        default=False,
        help='Decode ANVL responses',
    )
    parser.add_argument(
        '-e',
        action='store',
        dest='encoding',
        default='UTF-8',
        help='Character encoding; defaults to UTF-8',
    )
    parser.add_argument(
        '-k',
        action='store_true',
        dest='disableCertificateChecking',
        default=False,
        help='Disable SSL certificate checking',
    )
    parser.add_argument(
        '-l',
        action='store_true',
        dest='disableExternalUpdates',
        default=False,
        help='Disable external service updates',
    )
    parser.add_argument(
        '-o',
        action='store_true',
        dest='oneLine',
        default=False,
        help='One line per ANVL value: convert newlines to spaces',
    )
    parser.add_argument(
        '-t',
        action='store_true',
        dest='formatTimestamps',
        default=False,
        help='Format timestamps',
    )
    parser.add_argument("--debug", action="store_true", help="Debug level logging")

    args = parser.parse_args()
    client = Client(args)
    try:
        client.operation()
    except ClientError as e:
        print(f'Error: {str(e)}')


class Client:
    def __init__(self, args):
        self.args = args
        self.opener = None
        self.ezid_url = None
        self.cookie = None

    def operation(self):
        args = self.args

        if args.disableCertificateChecking:
            try:
                # noinspection PyUnresolvedReferences,PyProtectedMember
                ssl._create_default_https_context = ssl._create_unverified_context
            except AttributeError:
                pass

        self.ezid_url = KNOWN_SERVERS.get(args.server, args.server)

        print(f'Using EZID URL: {self.ezid_url}', file=sys.stderr)

        self.opener = self.create_opener(args.credentials)

        op_cmd = args.operation[0]
        op_args = args.operation[1:]

        has_bang = op_cmd.endswith('!')
        if has_bang:
            op_cmd = op_cmd[:-1]

        cmd_candidate_list = [s for s in CMD_TUP if s.startswith(op_cmd)]
        if not cmd_candidate_list:
            raise ClientError(f'Unknown operation: {op_cmd}')
        if len(cmd_candidate_list) > 1:
            raise ClientError(
                f'Ambiguous operation "{op_cmd}". Could be: {", ".join(cmd_candidate_list)}'
            )

        op_cmd = cmd_candidate_list[0]

        try:
            op_fn = getattr(self, f'op_{op_cmd}')
        except AttributeError:
            raise ClientError(f'Unknown operation: {op_cmd}')

        try:
            op_fn(has_bang, op_args)
        except Exception as e:
            if self.args.debug:
                raise
            raise ClientError(str(e))

    def op_mint(self, has_bang, op_args):
        """m[int] shoulder [element value ...]"""
        self.assert_not_has_bang(has_bang)
        self.assert_at_least_one_arg(op_args)
        shoulder_str = op_args.pop(0)
        self.assert_key_value_args(op_args)
        data = self.format_anvl_request(op_args)
        r = self.issue_request('shoulder/' + self.encode(shoulder_str), 'POST', data)
        self.print_anvl_response(r)

    def op_create(self, has_bang, op_args):
        """c[reate][!] identifier [element value ...]
        create! = create or update
        """
        self.assert_at_least_one_arg(op_args)
        id_str = op_args.pop(0)
        self.assert_key_value_args(op_args)
        data = self.format_anvl_request(op_args)
        path = 'id/' + self.encode(id_str)
        if has_bang:
            path += '?update_if_exists=yes'
        r = self.issue_request(path, 'PUT', data)
        self.print_anvl_response(r)

    def op_view(self, has_bang, op_args):
        """v[iew][!] identifier
        view! = match longest identifier prefix
        """
        self.assert_single_arg(op_args)
        id_str = op_args.pop(0)
        path = 'id/' + self.encode(id_str)
        if has_bang:
            path += '?prefix_match=yes'
        r = self.issue_request(path, 'GET')
        self.print_anvl_response(r, sortLines=True)

    def op_update(self, has_bang, op_args):
        """u[pdate] identifier [element value ...]"""
        self.assert_not_has_bang(has_bang)
        self.assert_at_least_one_arg(op_args)
        id_str = op_args.pop(0)
        self.assert_key_value_args(op_args)
        data = self.format_anvl_request(op_args)
        path = 'id/' + self.encode(id_str)
        if self.args.disableExternalUpdates:
            path += '?update_external_services=no'
        r = self.issue_request(path, 'POST', data)
        self.print_anvl_response(r)

    def op_delete(self, has_bang, op_args):
        """d[elete] identifier"""
        self.assert_not_has_bang(has_bang)
        self.assert_single_arg(op_args)
        id_str = op_args.pop(0)
        path = 'id/' + self.encode(id_str)
        if self.args.disableExternalUpdates:
            path += '?update_external_services=no'
        r = self.issue_request(path, 'DELETE')
        self.print_anvl_response(r)

    def op_login(self, has_bang, op_args):
        """login"""
        self.assert_not_has_bang(has_bang)
        self.assert_no_args(op_args)
        response, headers = self.issue_request('login', 'GET', returnHeaders=True)
        session_id = headers['set-cookie'].split(';')[0].split('=')[1]
        response += f'\nsessionid={session_id}\n'
        self.print_anvl_response(response)

    def op_logout(self, has_bang, op_args):
        """logout"""
        self.assert_not_has_bang(has_bang)
        self.assert_no_args(op_args)
        r = self.issue_request('logout', 'GET')
        self.print_anvl_response(r)

    def op_status(self, has_bang, op_args):
        """s[tatus] [detailed] [*|subsystemlist]"""
        self.assert_not_has_bang(has_bang)
        query_dict = {}
        if 'detailed' in op_args:
            query_dict['detailed'] = 'yes'
            op_args.remove('detailed')
        if len(op_args) > 1:
            raise ClientError('Incorrect number of arguments for operation')
        if len(op_args):
            query_dict['subsystems'] = op_args[0]
        r = self.issue_request('status?' + urllib.parse.urlencode(query_dict), 'GET')
        self.print_anvl_response(r)

    def op_Version(self, has_bang, op_args):
        """V[ersion]"""
        self.assert_not_has_bang(has_bang)
        self.assert_no_args(op_args)
        r = self.issue_request('version', 'GET')
        self.print_anvl_response(r)

    def format_anvl_request(self, op_list):
        if not op_list:
            return None
        request = []
        for i in range(0, len(op_list), 2):
            # k = op_list[i].decode(_options.encoding)
            k = op_list[i]
            if k == '@':
                f = codecs.open(op_list[i + 1], encoding=self.args.encoding)
                request += [l.strip('\r\n') for l in f.readlines()]
                f.close()
            else:
                if k == '@@':
                    k = '@'
                else:
                    k = re.sub('[%:\r\n]', lambda c: f'%{ord(c.group(0)):02X}', k)
                # v = op_list[i + 1].decode(_options.encoding)
                v = op_list[i + 1]
                if v.startswith('@@'):
                    v = v[1:]
                elif v.startswith('@') and len(v) > 1:
                    f = codecs.open(v[1:], encoding=self.args.encoding)
                    v = f.read()
                    f.close()
                v = re.sub('[%\r\n]', lambda c: f'%{ord(c.group(0)):02X}', v)
                request.append(f'{k}: {v}')
        return '\n'.join(request)

    def encode(self, id_str):
        return urllib.parse.quote(id_str, ':/')

    def stream_write(self, src, dst):
        buffer = ''
        while True:
            buffer += src.read(1).decode(encoding='utf-8')
            status_pos = buffer.rfind('STATUS')
            if status_pos > 0:
                dst.write(f'{buffer[:status_pos].strip()}\n')
                dst.flush()
                buffer = buffer[status_pos:]

    def issue_request(self, path, method, data=None, returnHeaders=False, streamOutput=False):
        request = urllib.request.Request(f'{self.ezid_url}/{path}')
        request.get_method = lambda: method
        if data:
            request.add_header('Content-Type', 'text/plain; charset=UTF-8')
            request.data = data.encode('UTF-8')
        if self.cookie:
            request.add_header('Cookie', self.cookie)
        try:
            connection = self.opener.open(request)
            if streamOutput:
                self.stream_write(connection, sys.stdout)
            else:
                r = connection.read()
                if returnHeaders:
                    return r.decode('UTF-8'), connection.info()
                else:
                    return r.decode('UTF-8')
        except urllib.error.HTTPError as e:
            sys.stderr.write(f'{e.code:d} {str(e)}\n')
            if e.fp:
                sys.stderr.write(e.fp.read().decode(encoding='utf-8'))
            sys.exit(1)

    def print_anvl_response(self, response, sortLines=False):
        line_list = response.splitlines()
        if sortLines and len(line_list) >= 1:
            statusLine = line_list[0]
            line_list = line_list[1:]
            line_list.sort()
            line_list.insert(0, statusLine)
        for line in line_list:
            if self.args.formatTimestamps and (
                line.startswith('_created:') or line.startswith('_updated:')
            ):
                ls = line.split(':')
                line = ls[0] + ': ' + time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(int(ls[1])))
            if self.args.decode:
                line = re.sub('%([0-9a-fA-F][0-9a-fA-F])', lambda m: chr(int(m.group(1), 16)), line)
            if self.args.oneLine:
                line = line.replace('\n', ' ').replace('\r', ' ')
            # print(line.encode(_options.encoding))
            print(line)

    def create_opener(self, credentials):
        opener = urllib.request.build_opener(urllib.request.HTTPErrorProcessor())

        if credentials.startswith('sessionid='):
            self.cookie = credentials
        elif credentials != '-':
            if ':' in credentials:
                username, password = credentials.split(':', 1)
            else:
                username = credentials
                password = getpass.getpass()
            h = urllib.request.HTTPBasicAuthHandler()
            h.add_password('EZID', self.ezid_url, username, password)
            opener.add_handler(h)

        return opener

    def assert_not_has_bang(self, has_bang):
        if has_bang:
            raise ClientError('This operation does not support a bang (!) suffix')

    # def assert_correct_number_of_args(self, has_correct_number_of_args):
    #     raise ClientError('Incorrect number of arguments for operation')

    def assert_key_value_args(self, op_args):
        if len(op_args) % 2:
            raise ClientError('This operation requires arguments to be name-value pairs')

    def assert_no_args(self, op_args):
        if len(op_args):
            raise ClientError('This operation accepts no arguments')

    def assert_single_arg(self, op_args):
        if len(op_args) != 1:
            raise ClientError('This operation requires exactly one argument')

    def assert_at_least_one_arg(self, op_args):
        if not len(op_args):
            raise ClientError('This operation requires at least one argument')


class ClientError(Exception):
    pass


if __name__ == '__main__':
    sys.exit(main())
