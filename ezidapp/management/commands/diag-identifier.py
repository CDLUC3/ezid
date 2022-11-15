#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Show the current state of one or more identifiers

This command works through the Django ORM and is useful for checking the current state
of an identifier.

This command does not alter any information in the database, and should be safe to run
at any time, including a running production instance.

Note however, that this command MAY alter the information in N2T when the --sync option
is used. Confirmation is requested before any metadata updates are propagated to N2T.
"""

import argparse
import copy
import csv
import datetime
import json
import logging
import time
import typing
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
import impl.datacite
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

        _show = subparsers.add_parser(
            "show",
            help=("Show available metadata for an identifier, and optionally sync the N2T record.\n"
                  "Example:\n"
                  "  Default:\n"
                  "    ./manage.py diag-identifier show ark:/62930/d1n739\n")
        )
        _show.add_argument(
            "identifiers",
            nargs="+",
            type=str,
            help="Space delimited list of identifiers to retrieve",
        )
        _show.add_argument(
            '-I',
            '--identifier',
            action='store_true',
            help='Show Identifier instead of SearchIdentifier table entry',
        )
        _show.add_argument(
            '-y',
            '--legacy',
            action='store_true',
            help='Show legacy form of identifier record',
        )
        _show.add_argument(
            '-m',
            '--cm',
            action='store_true',
            help='Decode the identifier cm zipped json section',
        )
        _show.add_argument(
            '-e',
            '--expanded',
            action='store_true',
            help='Expand related info such as owner, ownergroup, profile, and datacenter',
        )
        _show.add_argument(
            '-t',
            '--times',
            action='store_true',
            help='Convert timestamps to textual time representation',
        )
        _show.add_argument(
            '-N',
            '--N2T',
            action='store_true',
            help='Retrieve record from N2T if available',
        )
        _show.add_argument(
            '--sync',
            action='store_true',
            help="Synchronize the N2T entry with metadata from the database.",
        )

        _list = subparsers.add_parser(
            "list",
            help=("List identifiers matching a provided filter.\n"
                  "Examples:\n"
                  "  List arks created or updated since about 2022-05-20 using the identifier table:\n"
                  "    ./manage.py diag-identifier list -I \\ \n"
                  "     -W '(createTime>=1653004800 OR updateTime>=1653004800)' 'identifier like %%s:ark%%'"
                  )
        )
        _list.add_argument(
            "filter",
            nargs="+",
            type=str,
            help="Filter to select identifiers, e.g. 'createTime__gt:1653019200'. Multiple filters are combined with AND.",
        )
        _list.add_argument(
            '-I',
            '--identifier',
            action='store_true',
            help='Show Identifier instead of SearchIdentifier table entry',
        )
        _list.add_argument(
            '-W',
            '--whereclause',
            action='store_true',
            help='Filter is an SQL WHERE clause instead of ORM applied to the identifier or searchIdentifier tables.',
        )
        _list.add_argument(
            '-F',
            '--fields',
            action=SplitArgs,
            default=[],
            help="Comma separated list of fields in addition to identifier to list."
        )
        _list.add_argument(
            '--compare',
            action='store_true',
            help='Show difference between EZID and N2T metadata.',
        )
        _list.add_argument(
            '-m',
            '--max_rows',
            type=int,
            default=10,
            help='Maximum number of rows to list.'
        )

        _resolve = subparsers.add_parser(
            "resolve",
            help=("Emulate the functionality of the resolve API endpoint.")
        )
        _resolve.add_argument(
            "identifier",
            type=str,
            help="Identifier to resolve."
        )

        _metrics = subparsers.add_parser(
            "metrics",
            help=("Report number of creations or updates for a period, grouped by day and owner group.\n"
                  "Example:\n"
                  "  ./manage.py diag-identifier metrics -s 2022-05-01 | vd -f csv"
                  )
        )
        _metrics.add_argument(
            '-s',
            '--start',
            type=datetime.datetime.fromisoformat,
            default=datetime.datetime.utcnow() - datetime.timedelta(hours=24),
            help="Starting date for metrics"
        )
        _metrics.add_argument(
            '-e',
            '--end',
            type=datetime.datetime.fromisoformat,
            default=datetime.datetime.utcnow(),
            help="Ending date for metrics"
        )

        _syncmeta = subparsers.add_parser(
            "syncmeta",
            help=("Sends metadata to N2T for each row text file source. Rows starting with space or '#' are ignored.\n"
                  "Example:\n"
                  "  ./manage.py diag-identifier syncmeta -f pid_list.txt"
                  )
        )
        _syncmeta.add_argument(
            '-f',
            '--from',
            type=str,
            help="Text file with one identifier per line.",
            required=True
        )
        _syncmeta.add_argument(
            '-s',
            '--start',
            type=str,
            help="Identifier in list to start from",
            default=None
        )


    def diff_n2t(self, identifier:ezidapp.models.identifier)->dict:
        res = {}
        n2t_meta = impl.noid_egg.getElements(identifier.identifier)
        if n2t_meta is None:
            n2t_meta = {}
        _legacy = identifier.toLegacy()
        for k, v in _legacy.items():
            res[k] = [v, None]
        # If properties retrieved from N2T are not present in the supplied
        # update metadata, then set the value of the field to an empty string.
        # An empty value results in an "rm" (remove) operation for that field
        # being sent to N2T.
        for k, v in n2t_meta.items():
            if k not in res:
                res[k] = [None, v]
            else:
                res[k][1] = v
        return res


    def prepare_n2t_metadata(self, identifier:ezidapp.models.identifier, n2t_meta:typing.Optional[dict]=None)->dict:
        '''Prepare metadata for sending to N2T

        Returns a dictionary of metadata for identifier that can be sent to
        N2T using impl.noid_egg.setElements(identifier.identifier, m) to
        set or update the N2T entry for identifier.

        Metadata is sent to N2T for all states except Reserved DOIs, for which N2T is generally null.
        '''
        _legacy = identifier.toLegacy()
        # See proc_binder.update
        if n2t_meta is None:
            # Retrieve the existing metadata from N2T
            n2t_meta = impl.noid_egg.getElements(identifier.identifier)
        # if no metadata on N2T then initialize a blank for population.
        if n2t_meta is None:
            n2t_meta = {}

        if identifier.isReserved:
            #special case - reserved  - do nothing
            log.info("Reserved DOIs have null N2T metadata.")
            # To delete metadata on N2T, send keys with empty values, but we don't want to
            # delete all the keys since that has the effect of deleting the identifier from N2T.
            #for k in n2t_meta:
            #    n2t_meta[k] = ""
            #return n2t_meta
            return {}

        # First, update m with provided metadata
        for k, v in list(_legacy.items()):
            # If the provided metadata matches existing, then ignore
            if n2t_meta.get(k) == v:
                del n2t_meta[k]
            # Otherwise add property to list for sending back to N2T
            else:
                n2t_meta[k] = v
        # If properties retrieved from N2T are not present in the supplied
        # update metadata, then set the value of the field to an empty string.
        # An empty value results in an "rm" (remove) operation for that field
        # being sent to N2T.
        for k in list(n2t_meta.keys()):
            if k not in _legacy:
                n2t_meta[k] = ""
        return n2t_meta


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
                m = self.prepare_n2t_metadata(identifier, n2t_meta)
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

    def handle_list_by_where(self, *args, **opts):
        max_rows = opts.get("max_rows", 10)
        _fields = ['identifier',] + opts.get('fields', [])
        _params = []
        filter_strings = []
        for _f in opts['filter']:
            if '%s:' in _f:
                a,b = _f.split(':',1)
                filter_strings.append(a)
                _params.append(b)
            else:
                filter_strings.append(_f)
        identifiers = None
        identifier_class = ezidapp.models.identifier.SearchIdentifier
        _table = "ezidapp_searchidentifier"
        if opts["identifier"]:
            _table = "ezidapp_identifier"
            identifier_class = ezidapp.models.identifier.Identifier
        #sqlc = f"SELECT count(*) FROM {_table} WHERE {' AND '.join(filter_strings)};"
        sql = f"SELECT * FROM {_table} WHERE {' AND '.join(filter_strings)} LIMIT {max_rows};"
        log.debug("Generated SQL = " + sql)
        identifiers = identifier_class.objects.raw(sql, _params)
        log.debug(identifiers.raw_query)
        writer = csv.DictWriter(self.stdout, _fields, dialect='excel')
        writer.writeheader()
        for identifier in identifiers:
            writer.writerow(django.forms.models.model_to_dict(identifier, fields=_fields))

    def handle_list(self, *args, **opts):
        max_rows = opts.get("max_rows", 10)
        filter_strings = []
        for _f in opts['filter']:
            if _f == "recent":
                filter_strings.append(f"createTime__lte:{int(time.time())}")
            else:
                filter_strings.append(_f)
        _fields = ['identifier',] + opts.get('fields', [])
        _filter = {}
        _default_key = ""
        identifier_class = ezidapp.models.identifier.SearchIdentifier
        for filter_string in filter_strings:
            parts = filter_string.split(':', 1)
            if len(parts) > 1:
                _filter[parts[0].strip()] = parts[1].strip()
            else:
                log.warning("Expecting ':' delimiter between filter and match value, e.g. createTime__gt:1653019200, got %s",filter_string)
        self.stdout.write(f"Provided filter = {_filter}")
        if len(_filter.keys()) < 1:
            log.error("Aborting: Null filter matches all records.")
            return
        if opts["identifier"]:
            identifier_class = ezidapp.models.identifier.Identifier
        identifiers = identifier_class.objects.filter(**_filter).order_by("-createTime")[:max_rows]
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


    def handle_resolve(self, *args, **opts):
        '''Given an identifier, determine it's resolver as known by EZID.
        '''
        identifier = opts.get("identifier", None)
        if identifier is None:
            log.error("Provided identifier is NULL")
            return
        res = ezidapp.models.identifier.resolveIdentifier(identifier)
        self.stdout.write(str(res))


    def handle_metrics(self, *args, **opts):
        '''
        Generate a report of identifier creations grouped by day and owner group.
        '''
        start_date = opts.get('start', datetime.datetime.utcnow() - datetime.timedelta(hours=24))
        end_date = opts.get('end', datetime.datetime.utcnow())
        _t0 = int(start_date.timestamp())
        _t1 = int(end_date.timestamp())
        tfield = 'createTime'
        if opts.get('tmodified', False):
            tfield = 'updateTime'
        model = 'ezidapp_searchidentifier'
        identifier_class = ezidapp.models.identifier.SearchIdentifier
        if opts.get("identifier"):
            model = 'ezidapp_identifier'
            identifier_class = ezidapp.models.identifier.Identifier
        sql = (f'SELECT floor(({model}.{tfield}-%s)/86400) as day, '
               f'count(*) as n, {model}.ownergroup_id as og, ezidapp_group.groupname '
               f'FROM {model}, ezidapp_group '
               f'WHERE {model}.ownergroup_id = ezidapp_group.id '
               f'AND {model}.{tfield} > %s AND {model}.{tfield} <= %s '
               f'GROUP BY day, {model}.ownergroup_id '
               'ORDER BY day;'
               )
        with django.db.connection.cursor() as cursor:
            _fields = ['day', 'n', 'groupid', 'gname']
            writer = csv.writer(self.stdout, dialect='excel')
            writer.writerow(_fields)
            cursor.execute(sql, [_t0, _t0, _t1])
            for row in cursor.fetchall():
                writer.writerow(row)


    def handle_syncmeta(self, *args, **opts):
        '''For each line in `from`:
        update metadata
        '''
        fn_src = opts.get('from')
        fn_dst = fn_src + ".json"
        start_at = opts.get("start", None)
        log.info("Recording changes to %s", fn_dst)
        identifiers = []
        add_id = True
        if start_at is not None:
            add_id = False
            start_at = start_at.strip()
        with open(fn_src) as _src:
            for row in _src:
                if row.startswith('ark:') or row.startswith('doi:'):
                    if not add_id:
                        if row.strip() == start_at:
                            add_id = True
                    if add_id:
                        identifiers.append(row.strip())
        log.info("Loaded %s identifiers from %s", len(identifiers), fn_src)
        log.info("Loading status...")
        with open(fn_dst, 'a') as f_dest:
            for pid in identifiers:
                self.stdout.write(pid)
                result = {'pid':pid, 'original': {}, 'change': {}, 'updated':{}}
                identifier = ezidapp.models.identifier.SearchIdentifier.objects.get(identifier=pid)
                if identifier is None:
                    log.error('Identifier %s could not be loaded!', pid)
                    break
                if identifier.isDatacite:
                    # handle datacite target url
                    doi = identifier.identifier[4:]
                    datacenter = str(identifier.datacenter)
                    log.info("Setting target for %s (%s) to %s", doi, datacenter, identifier.resolverTarget)
                    r = impl.datacite.setTargetUrl(doi, identifier.resolverTarget, datacenter)
                    if r is not None:
                        # There was a failure in the request
                        log.error("Failed to set target url for DataCite DOI: %s", doi)
                    pass
                elif identifier.isCrossref:
                    # handle crossref target url
                    pass
                result['original'] = impl.noid_egg.getElements(identifier.identifier)
                n2t_meta = copy.deepcopy(result['original'])
                result['change'] = self.prepare_n2t_metadata(identifier, n2t_meta=n2t_meta)
                self.stdout.write(json.dumps(result['change']))
                if result['change'] != {}:
                    # Send update request
                    impl.noid_egg.setElements(identifier.identifier, result['change'])
                    # Retrieve the updated n2t meta
                    result['updated'] = impl.noid_egg.getElements(identifier.identifier)
                else:
                    # no change
                    result['updated'] = result['original']
                f_dest.write(json.dumps(result))
                f_dest.write("\n")
                f_dest.flush()



    def handle(self, *args, **opts):
        operation = opts['operation']
        if operation == 'show':
            self.handle_show(*args, **opts)
        elif operation == 'list':
            if opts['whereclause']:
                self.handle_list_by_where(*args, **opts)
            else:
                self.handle_list(*args, **opts)
        elif operation == 'resolve':
            self.handle_resolve(*args, **opts)
        elif operation == 'metrics':
            self.handle_metrics(*args, **opts)
        elif operation =='syncmeta':
            self.handle_syncmeta(*args, **opts)


