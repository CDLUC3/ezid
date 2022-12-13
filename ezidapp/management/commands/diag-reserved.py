#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""List reserved identifiers.

This command does not alter any information in the database, and should be safe to run
at any time, including a running production instance.
"""

import argparse
import csv
import datetime
import json
import logging
import time
import urllib.parse
import zlib

import django.apps
import django.conf
import django.core.management
import django.core.serializers
import django.db.models
import django.forms
import django.forms.models
import requests
import requests.auth

import ezidapp.models.datacenter
import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.shoulder
import ezidapp.models.user

log = logging.getLogger(__name__)

DATACITE_REST_API = "https://api.datacite.org/dois/"

class SplitArgs(argparse.Action):
    # From: https://stackoverflow.com/questions/52132076/argparse-action-or-type-for-comma-separated-list
    def __call__(self, parser, namespace, values, option_string=None):
        # Be sure to strip, maybe they have spaces where they don't belong and wrapped the arg value in quotes
        setattr(namespace, self.dest, [value.strip() for value in values.split(",")])

class DataCiteREST:

    def __init__(self, service_url:str=DATACITE_REST_API):
        self._service_url = service_url.rstrip("/") + "/"
        self._session = None
        self._allocators = {
            a: getattr(django.conf.settings, f"ALLOCATOR_{a}_PASSWORD")
            for a in django.conf.settings.DATACITE_ALLOCATORS.split(",")
        }

    def _auth(self, datacenter:str)->requests.auth.HTTPBasicAuth:
        allocator, center = datacenter.split(".", 1)
        return requests.auth.HTTPBasicAuth(datacenter, self._allocators.get(allocator))

    def getRecord(self, doi:str, datacenter:str)->dict:
        if self._session is None:
            self._session = requests.Session()
        if doi.startswith("doi:"):
            doi = doi[4:]
        headers = {
            "Accept":"application/vnd.api+json"
        }
        params = {}
        t0 = time.time()
        url = urllib.parse.urljoin(self._service_url, urllib.parse.quote(doi))
        response = self._session.get(url, headers=headers, params=params, auth=self._auth(datacenter))
        dt = time.time() - t0
        log.debug("%s  %s",dt, url)
        res = {
            "status": response.status_code,
            "meta":{'isActive':None, 'state': None, 'url': None}
        }
        if response.status_code == 200:
            m = response.json()
            a = m.get('data',{}).get('attributes', {})
            res["meta"] = {
                'isActive':a.get('isActive',False),
                'state': a.get('state'),
                'url':a.get('url'),
            }
        return res

    def set_isActive(self, identifier:str, datacenter:str, active:bool=True):
        data = {
            "data": {
                "type": "dois",
                "attributes": {
                    "isActive": active
                }
            }
        }
        pass

class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super().__init__()
        self.opt = None

    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser:argparse.ArgumentParser):
        subparsers = parser.add_subparsers(
            title="Operations",
            dest="operation",
            required=True
        )

        _list = subparsers.add_parser("list")
        _list.add_argument(
            "-s",
            "--start_time",
            default=(datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=1)).isoformat(),
            help="Start time for listing reserved identifiers, updatetime >= start_time",
        )
        _list.add_argument(
            "-e",
            "--end_time",
            default=datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            help="End time for listing reserved identifiers, updatetime < end_time",
        )
        _list.add_argument(
            '-I',
            '--identifier',
            action='store_true',
            help='Show Identifier instead of SearchIdentifier table entry',
        )
        _list.add_argument(
            '-p',
            '--prefix',
            default=None,
            help='Show identifiers starting with prefix (e.g. "doi:")'
        )
        _list.add_argument(
            '-S',
            '--status',
            default='R',
            help='Status code for identifier (R, P, U)'
        )
        _list.add_argument(
            '-M',
            '--metadata',
            action='store_true',
            help="Get properties from DataCite, CrossRef, or N2T"
        )

    def handle_list(self, *args, **opts):

        def tstamp_to_text(t):
            return datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).isoformat()

        DC = DataCiteREST()
        t_start = int(datetime.datetime.fromisoformat(opts['start_time']).timestamp())
        t_end = int(datetime.datetime.fromisoformat(opts['end_time']).timestamp())
        expand_fields = ['datacenter', 'owner', 'ownergroup']

        identifier_class = ezidapp.models.identifier.SearchIdentifier
        if opts["identifier"]:
            identifier_class = ezidapp.models.identifier.Identifier
        identifiers = identifier_class.objects.filter(status=opts.get('status','R'), updateTime__gte=t_start, updateTime__lt=t_end)
        _prefix = opts.get("prefix", None)
        if _prefix is not None:
            identifiers = identifiers.filter(identifier__startswith=_prefix)
        identifiers = identifiers.select_related(*expand_fields)

        writer = csv.writer(self.stdout, dialect='excel')
        csv_header = ['PID','type','status','exported','profile','owner','ownergroup','datacenter','created','updated','target','resolvertarget']
        if opts.get("metadata", False):
            csv_header += ["dcrest","dcstate","dcactive","dcurl"]
        writer.writerow(csv_header)
        for identifier in identifiers:
            itype = 'ark'
            if identifier.isDoi:
                if identifier.isCrossref:
                    itype = 'crossref'
                else:
                    itype = 'datacite'
            datacenter = identifier.datacenter
            if datacenter is None:
                if identifier.isDatacite:
                    _shoulder = ezidapp.models.shoulder.getLongestShoulderMatch(identifier.identifier)
                    datacenter = _shoulder.datacenter.symbol
            else:
                datacenter = datacenter.symbol
            m = {}
            if opts.get("metadata", False):
                if itype == "datacite":
                    m = DC.getRecord(identifier.identifier, datacenter)
            row = [
                identifier.identifier,
                itype,
                identifier.status,
                identifier.exported,
                identifier.profile,
                identifier.owner.username,
                identifier.ownergroup.groupname,
                datacenter,
                tstamp_to_text(identifier.createTime),
                tstamp_to_text(identifier.updateTime),
                identifier.target,
                identifier.resolverTarget,
            ]
            if opts.get("metadata", False):
                _m = m.get('meta', {})
                row += [m.get('status',404),_m.get('state',None),_m.get('isActive',None), _m.get('url',None)]
            writer.writerow(row)

    def handle(self, *args, **opts):
        operation = opts['operation']
        if operation == 'list':
            self.handle_list(*args, **opts)

