#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""List reserved identifiers.

This command does not alter any information in the database, and should be safe to run
at any time, including a running production instance.
"""

import argparse
import csv
import json
import logging
import datetime
import zlib

import django.apps
import django.conf
import django.core.management
import django.core.serializers
import django.db.models
import django.forms
import django.forms.models

import ezidapp.models.datacenter
import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.user
import impl.noid_egg

log = logging.getLogger(__name__)

class SplitArgs(argparse.Action):
    # From: https://stackoverflow.com/questions/52132076/argparse-action-or-type-for-comma-separated-list
    def __call__(self, parser, namespace, values, option_string=None):
        # Be sure to strip, maybe they have spaces where they don't belong and wrapped the arg value in quotes
        setattr(namespace, self.dest, [value.strip() for value in values.split(",")])

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


    def handle_show(self, *args, **opts):
        def jsonable_instance(o):
            if o is None:
                return o
            res = json.loads(
                django.core.serializers.serialize(
                    'json',
                    [
                        o,
                    ],
                )
            )[0]
            return res

        def tstamp_to_text(t):
            return datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).isoformat()

        expand_fields = ['datacenter', 'owner', 'ownergroup', 'profile']
        identifier_class = ezidapp.models.identifier.SearchIdentifier
        if opts["identifier"]:
            identifier_class = ezidapp.models.identifier.Identifier
        identifiers = identifier_class.objects.filter(identifier__in=opts["identifiers"])
        if opts['expanded']:
            identifiers = identifiers.select_related(*expand_fields)
        entries = []
        for identifier in identifiers:
            # Note, it is far more efficient to just call serialize('json', identifiers, indent=2)
            # but we want to futz around with the cm section and other fields for each instance.
            entry = jsonable_instance(identifier)
            entry["isAgentPid"] = identifier.isAgentPid
            if opts["legacy"]:
                # Get the "legacy" format, which is used for sending to N2T binder
                entry["legacy"] = identifier.toLegacy()
            if opts["expanded"]:
                for field_name in expand_fields:
                    entry["fields"][field_name] = jsonable_instance(getattr(identifier, field_name))
            if opts["times"]:
                entry["fields"]["createTime"] = tstamp_to_text(entry["fields"]["createTime"])
                entry["fields"]["updateTime"] = tstamp_to_text(entry["fields"]["updateTime"])
            if opts["cm"]:
                try:
                    _cm = json.loads(zlib.decompress(identifier.cm))
                    entry['fields']['cm'] = _cm
                    # Simple test to verify the decode cm section matches the metadata section
                    _mequal = len(_cm.keys()) == len(entry['fields']['metadata'].keys())
                    for k, v in _cm.items():
                        if entry['fields']['metadata'][k] != _cm[k]:
                            _mequal = False
                            break
                    entry["cm_eq_metadata"] = _mequal
                except zlib.error:
                    log.info("No cm section in %s", identifier.identifier)
            n2t_meta = None
            if opts["N2T"]:
                # Retrieve entry from N2T
                n2t_meta = impl.noid_egg.getElements(identifier.identifier)
                entry["n2t"] = n2t_meta
            if opts["sync"]:
                _legacy = identifier.toLegacy()
                # See proc_binder.update
                # Retrieve the existing metadata from N2T
                m = n2t_meta
                if m is None:
                    m = impl.noid_egg.getElements(identifier.identifier)
                if m is None:
                    m = {}
                # First, update m with provided metadata
                for k, v in list(_legacy.items()):
                    # If the provided metadata matches existing, then ignore
                    if m.get(k) == v:
                        del m[k]
                    # Otherwise add property to list for sending back to N2T
                    else:
                        m[k] = v
                # If properties retrieved from N2T are not present in the supplied
                # update metadata, then set the value of the field to an empty string.
                # An empty value results in an "rm" (remove) operation for that field
                # being sent to N2T.
                for k in list(m.keys()):
                    if k not in _legacy:
                        m[k] = ""
                if len(m) > 0:
                    log.warning("Updating N2T metadata for %s", identifier.identifier)
                    log.info("Pending updates for %s:\n%s", identifier.identifier, m)
                    self.stdout.write(f"About to update {identifier.identifier} !")
                    response = input("Enter Y to continue, anything else aborts: ")
                    if response.strip() == 'Y':
                        impl.noid_egg.setElements(identifier.identifier, m)
                        ##
                        # Retrieve the updated metadata and add to the entry
                        entry["n2t_updated"] = impl.noid_egg.getElements(identifier.identifier)
                    else:
                        self.stdout.write("Aborted.")
                else:
                    log.info("No pending updates for %s", identifier.identifier)

            entries.append(entry)
        self.stdout.write(json.dumps(entries, indent=2, sort_keys=True))

    def handle_list(self, *args, **opts):
        def jsonable_instance(o):
            if o is None:
                return o
            res = json.loads(
                django.core.serializers.serialize(
                    'json',
                    [
                        o,
                    ],
                )
            )[0]
            return res

        def tstamp_to_text(t):
            return datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).isoformat()

        t_start = int(datetime.datetime.fromisoformat(opts['start_time']).timestamp())
        t_end = int(datetime.datetime.fromisoformat(opts['end_time']).timestamp())
        expand_fields = ['datacenter', 'owner', 'ownergroup']

        identifier_class = ezidapp.models.identifier.SearchIdentifier
        if opts["identifier"]:
            identifier_class = ezidapp.models.identifier.Identifier
        identifiers = identifier_class.objects.filter(status='R', updateTime__gte=t_start, updateTime__lt=t_end)
        identifiers = identifiers.select_related(*expand_fields)

        writer = csv.writer(self.stdout, dialect='excel')
        writer.writerow(['PID','type','created','updated','owner','ownergroup','target'])
        for identifier in identifiers:
            itype = 'ark'
            if identifier.isDoi:
                if identifier.isCrossref:
                    itype = 'crossref'
                else:
                    itype = 'datacite'
            row = [
                identifier.identifier,
                itype,
                tstamp_to_text(identifier.createTime),
                tstamp_to_text(identifier.updateTime),
                identifier.owner.username,
                identifier.ownergroup.groupname,
                identifier.resolverTarget,
            ]
            writer.writerow(row)

        '''
        dfields = _fields
        if opts.get("compare", False):
            dfields.append('n2t')
        writer = csv.DictWriter(self.stdout, dfields, dialect='excel')
        writer.writeheader()
        for identifier in identifiers:
            row = django.forms.models.model_to_dict(identifier, fields=_fields)
            if opts.get('compare', False):
                row['n2t'] = self.diff_n2t(identifier)
            writer.writerow(row)
        '''

    def handle(self, *args, **opts):
        operation = opts['operation']
        if operation == 'list':
            self.handle_list(*args, **opts)

