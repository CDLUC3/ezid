"""Migrate EZID's various legacy blob formats to JSON
"""
#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import ast
import base64
import contextlib
import json
import logging
import pprint
import types

import django.apps
import django.conf
import django.contrib.auth.models
import django.core.management
import django.core.serializers.json
import django.db.models as models
import django.db.models.functions as model_fn
import django.db.transaction

import impl.enqueue
import impl.nog.counter
import impl.nog.tb
import impl.nog.util

import multiprocessing.pool
import multiprocessing

import impl.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

        subparsers = parser.add_subparsers(required=True, dest='subcommand')
        backup_parser = subparsers.add_parser(
            'backup',
            help='Copy all blob fields to backup tables',
        )
        backup_parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite any previous backups',
        )

        restore_parser = subparsers.add_parser(
            'restore',
            help='Restore all blob fields from backup tables',
        )

        migrate_parser = subparsers.add_parser(
            'migrate',
            help=(
                'Parse all blob fields using legacy parsers, then replace them with JSON '
                'formatted versions. Backups are created if they don\'t exist'
            ),
        )

        dropbackups_parser = subparsers.add_parser(
            'dropbackups', help='Drop any existing backup tables'
        )

        diff_parser = subparsers.add_parser(
            'diff', help='Show differences between originals and backups'
        )

        dumpclear_parser = subparsers.add_parser('dumpclear', help='Decode and dump blobs')

    def handle(self, *_, **opt):
        self.opt = opt = types.SimpleNamespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug, suppress_context=True)
        db = MigrateBlobs()
        impl.util.log_obj(opt, msg='opt', logger=log.debug)
        try:
            return getattr(db, opt.subcommand)(opt)
        except django.db.ProgrammingError as e:
            print(str(e))

    #     # db.migrate()
    #     # db.print_identifier('ark:/13030/c80c4tkc')
    #     # db.print_identifier('ark:/13030/c8028pmk')
    #     db.backup_blobs()
    #     # db.restore_blobs()


# noinspection PyProtectedMember
class MigrateBlobs:
    def __init__(self):
        self.exit_stack = contextlib.ExitStack()
        # self.counter = self.exit_stack.enter_context(impl.nog.counter.Counter())
        self.page_size = django.conf.settings.QUERY_PAGE_SIZE

        # class JSONEncoder(django.core.serializers.json.DjangoJSONEncoder):
        #     def default(self, o):
        #         if isinstance(o, bytes):
        #             return o.decode('utf-8', errors='replace')
        #         return super().default(o)
        #
        # self.json_encoder = JSONEncoder

    def backup(self, args):
        for blob_ns in self._blob_gen():
            if blob_ns.backup_exists:
                if args.overwrite:
                    log.warning(f'{blob_ns.ctx_str}: Overwriting previous backup')
                    self._run_query(f'drop table if exists {blob_ns.backup_table}')
                else:
                    log.warning(
                        f'{blob_ns.ctx_str}: '
                        f'Skipped: Backup already exists and --overwrite not specified'
                    )
                    continue
            self._run_query(
                f'create table {blob_ns.backup_table} '
                f'select {blob_ns.pk_name}, {blob_ns.field_name} from {blob_ns.orig_table}'
            )

    def restore(self, args):
        for blob_ns in self._blob_gen():
            if not blob_ns.backup_exists:
                log.error(f'{blob_ns.ctx_str}: No existing backup')
            else:
                self._run_query(
                    f'update {blob_ns.orig_table} a '
                    f'set a.{blob_ns.field_name} = b.{blob_ns.field_name} '
                    f'join {blob_ns.backup_table} b '
                    f'on a.{blob_ns.pk_name} = b.{blob_ns.pk_name}'
                )

    # @impl.util.log_inout()
    def dropbackups(self, args):
        for blob_ns in self._blob_gen():
            if blob_ns.backup_exists:
                self._run_query(f'drop table {blob_ns.orig_table}')
                log.warning(f'{blob_ns.ctx_str}: No existing backup')
            else:
                self._run_query(
                    f'update {blob_ns.orig_table} a '
                    f'set a.{blob_ns.field_name} = b.{blob_ns.field_name} '
                    f'join {blob_ns.backup_table} b '
                    f'on a.{blob_ns.pk_name} = b.{blob_ns.pk_name}'
                )
                log.info(f'{blob_ns.ctx_str}: Dropped')

    # @impl.util.log_inout()
    def diff(self, args):
        with impl.nog.counter.Counter(out_fn=log.info) as counter:
            for blob_ns in self._blob_gen():
                if not blob_ns.backup_exists:
                    log.warning(f'{blob_ns.ctx_str}: No existing backup')
                    continue
                for obj_a, obj_b in self._run_query(
                    f'select a.{blob_ns.field_name} as "orig_blob", b.{blob_ns.field_name} as "backup_blob" '
                    f'from {blob_ns.orig_table} a '
                    f'join {blob_ns.backup_table} b '
                    f'on a.{blob_ns.pk_name} = b.{blob_ns.pk_name}'
                ):
                    if obj_a != obj_b:

                        log.error('Diff:')
                        log.error(f'  Original: {self._decode(obj_a)}')
                        log.error(f'  Backup:   {self._decode(obj_b)}')

                        counter.count('', 'total - different')
                        counter.count('', f'{blob_ns.mod_field_str} - different')
                    else:
                        counter.count('', 'total - identical')
                        counter.count('', f'{blob_ns.mod_field_str} - identical')

    # @impl.util.log_inout()
    def dumpclear(self, args):
        with impl.nog.counter.Counter(out_fn=log.info) as counter:
            for obj in self.decoded_blob_gen():
                print(obj)

    # @impl.util.log_inout()
    def _blob_gen(self):
        for blob_tup in django.conf.settings.BLOB_FIELD_LIST:
            model_name, field_name, is_queue = blob_tup
            model = django.apps.apps.get_model('ezidapp', model_name)
            orig_table = model._meta.db_table
            backup_table = f'backup_{orig_table}'
            pk_name = self._get_primary_key_name(model)
            backup_exists = self._backup_exists(backup_table)
            blob_ns = types.SimpleNamespace(
                mod_field_str=f'{model_name}.{field_name}',
                ctx_str=f'{model_name}.{field_name} {backup_table}',
                model_name=model_name,
                field_name=field_name,
                model=model,
                pk_name=pk_name,
                orig_table=orig_table,
                backup_table=backup_table,
                backup_exists=backup_exists,
            )
            impl.util.log_obj(blob_ns, msg='blob_ns', logger=log.debug)
            yield blob_ns

    # @impl.util.log_inout()
    def decoded_blob_gen(self):
        with impl.nog.counter.Counter(out_fn=log.info) as counter:

            class ExtractBinary(models.Model):
                raw_bytes = models.BinaryField(null=True, blank=True)

            for blob_ns in self._blob_gen():
                # log.error('5'*100)
                # continue
                # self.decoded_blob_gen_multiproc(counter, blob_ns)
                row_count = blob_ns.model.objects.aggregate(django.db.models.Count('pk'))[
                    'pk__count'
                ]
                if not row_count:
                    log.info(f'{blob_ns.model_name} is empty')
                    return
                min_pk = blob_ns.model.objects.aggregate(
                    min_pk=model_fn.Coalesce(models.Min('pk'), models.Value(0))
                )['min_pk']
                max_pk = blob_ns.model.objects.aggregate(
                    max_pk=model_fn.Coalesce(models.Max('pk'), models.Value(0))
                )['max_pk']
                ceil_int = 1 if row_count % self.page_size else 0
                page_count = row_count // self.page_size + ceil_int
                idx_offset = min_pk
                idx_inc = (max_pk - min_pk) // page_count + ceil_int
                pk_name = self._get_primary_key_name(blob_ns.model)

                # log.debug(
                #     f'row_count={row_count:,} '
                #     f'pk_name={pk_name:,} '
                #     f'min_pk={min_pk:,} '
                #     f'max_pk={max_pk:,} '
                #     f'ceil_int={ceil_int:,} '
                #     f'page_count={page_count:,} '
                #     f'idx_offset={idx_offset:,} '
                #     f'idx_inc={idx_inc:,} '
                # )

                idx = 0

                pool = multiprocessing.pool.Pool(8 * multiprocessing.cpu_count())

                for i in range(page_count):
                    log.info(f'{i + 1} / {page_count}  {idx} - {idx + idx_inc}')

                    query_str = (
                        f'select {pk_name} as id, {blob_ns.field_name} as raw_bytes '
                        f'from {blob_ns.model._meta.db_table} '
                        f'where {pk_name} >= {idx + idx_offset} '
                        f'and {pk_name} < {idx + idx_offset + idx_inc}'
                        # model.objects.filter(pk__gte=idx, pk__lt=idx + self.page_size)
                        #  .all()
                        #  .values(field_name)
                    )

                    try:
                        qs = ExtractBinary.objects.raw(query_str)
                        for res_tup in pool.imap_unordered(
                            self.decode_blob,
                            qs,
                            chunksize=100,
                        ):
                            yield blob_ns, res_tup
                    except Exception as e:
                        print(str(e))

                    idx += idx_inc

    # @impl.util.log_inout()
    def add_to_counters(self, blob_ns, clear_len, compressed_len, counter, op_list):
        counter.count('', f'{blob_ns.model_name} - rows in model')
        counter.count('', f'{blob_ns.model_name} - compressed bytes', delta_int=compressed_len)
        counter.count('', f'{blob_ns.model_name} - clear bytes', delta_int=clear_len)
        counter.count('', f'total rows in model')
        counter.count('', f'total compressed bytes', delta_int=compressed_len)
        counter.count('', f'total clear bytes', delta_int=clear_len)
        counter.count('', f'conversion: {" ".join(s for s in op_list)}')

    # @impl.util.log_inout()
    def decode_blob(self, raw_bytes):
        class JSONEncoder(django.core.serializers.json.DjangoJSONEncoder):
            def default(self, o):
                if isinstance(o, bytes):
                    return o.decode('utf-8', errors='replace')
                return super().default(o)

        try:
            obj, op_list = self._decode(raw_bytes)
            clear_json_str = self._encode(obj, JSONEncoder)
            return clear_json_str, op_list  # len(raw_bytes), len(clear_json_str), op_list
        except Exception as e:
            print(str(e))

    # @impl.util.log_inout()
    def _backup_exists(self, backup_table):
        r = self._run_query(
            """
            select if ((
            select count( *)
            from information_schema.tables
            where table_name = %s) = 1, 1, 0)
            as "exists"
        """,
            backup_table,
        )
        return bool(r[0][0])

    # def migrate(self):
    #     with impl.nog.counter.Counter() as counter:
    #         for (
    #             model_name,
    #             field_name,
    #             is_queue,
    #         ) in django.conf.settings.BLOB_FIELD_LIST:
    #             log.info(f'{model_name}.{field_name}: is_queue={is_queue}')
    #             model = django.apps.apps.get_model('ezidapp', model_name)
    #             self.migrate_field(counter, model, model_name, field_name)
    #
    # def migrate_field(self, counter, model, model_name, field_name):
    #     row_count = model.objects.aggregate(django.db.models.Count('pk'))['pk__count']
    #     if not row_count:
    #         log.info(f'{model_name} is empty')
    #         return
    #     min_pk = model.objects.aggregate(
    #         min_pk=model_fn.Coalesce(models.Min('pk'), models.Value(0))
    #     )['min_pk']
    #     max_pk = model.objects.aggregate(
    #         max_pk=model_fn.Coalesce(models.Max('pk'), models.Value(0))
    #     )['max_pk']
    #     ceil_int = 1 if row_count % self.page_size else 0
    #     page_count = row_count // self.page_size + ceil_int
    #     idx_offset = min_pk
    #     idx_inc = (max_pk - min_pk) // page_count + ceil_int
    #     log.info(
    #         f'row_count={row_count:,} '
    #         f'min_pk={min_pk:,} '
    #         f'max_pk={max_pk:,} '
    #         f'ceil_int={ceil_int:,} '
    #         f'page_count={page_count:,} '
    #         f'idx_offset={idx_offset:,} '
    #         f'idx_inc={idx_inc:,} '
    #     )
    #
    #     pk_name = self._get_primary_key_name(model)
    #
    #     class ExtractBinary(models.Model):
    #         raw_bytes = models.BinaryField(null=True, blank=True)
    #
    #     idx = 0
    #
    #     pool = multiprocessing.pool.Pool(8 * multiprocessing.cpu_count())
    #     counter_lock = multiprocessing.RLock()
    #     for i in range(page_count):
    #         log.info(f'{i + 1} / {page_count}  {idx} - {idx + idx_inc}')
    #         query_str = (
    #             f'select {pk_name} as id, {field_name} as raw_bytes '
    #             f'from {model._meta.db_table} '
    #             f'where {pk_name} >= {idx + idx_offset} '
    #             f'and {pk_name} < {idx + idx_offset + idx_inc}'
    #             # model.objects.filter(pk__gte=idx, pk__lt=idx + self.page_size)
    #             #         .all()
    #             #         .values(field_name)
    #         )
    #         log.info(query_str)
    #         qs = ExtractBinary.objects.raw(query_str)
    #         for compressed_len, clear_len, op_list in pool.imap_unordered(
    #             self._proc_model, qs, chunksize=100
    #         ):
    #             counter.count('', f'{model_name} - rows in model')
    #             counter.count('', f'{model_name} - compressed bytes', delta_int=compressed_len)
    #             counter.count('', f'{model_name} - clear bytes', delta_int=clear_len)
    #
    #             counter.count('', f'total rows in model')
    #             counter.count('', f'total compressed bytes', delta_int=compressed_len)
    #             counter.count('', f'total clear bytes', delta_int=clear_len)
    #
    #             counter.count('', f'conversion: {" ".join(s for s in op_list)}')
    #
    #         idx += idx_inc

    # @impl.util.log_inout()
    def _run_query(self, query_str, *params):
        impl.util.log_obj(query_str, msg='query', logger=log.debug)
        impl.util.log_obj(params, msg='params', logger=log.debug)
        cursor = django.db.connection.cursor()
        try:
            cursor.execute(query_str, params=params)
            return cursor.fetchall()
        finally:
            django.db.transaction.commit()

    # @impl.util.log_inout()
    def _get_primary_key_name(self, model):
        for field in model._meta.fields:
            if field.primary_key:
                pk_name = field.name
                break
        else:
            raise AssertionError()
        return pk_name

    # def _proc_model(self, r):
    #     class JSONEncoder(django.core.serializers.json.DjangoJSONEncoder):
    #         def default(self, o):
    #             if isinstance(o, bytes):
    #                 return o.decode('utf-8', errors='replace')
    #             return super().default(o)
    #
    #     v = r.raw_bytes
    #     obj, op_list = self._decode(v)
    #     clear_json_str = self._encode(obj, JSONEncoder)
    #     return len(v), len(clear_json_str), op_list
    #
    #     # blob_str = f'{model_name}.{field_name} type {r!r}'
    #     # log.info(blob_str)
    #     # field_obj = getattr(r, field_name)

    def _decode(self, obj):
        """
        Decode
        all
        blob
        formats
        used in previous and current
        EZID
        """

        op_list = []

        @contextlib.contextmanager
        def w(obj, op_str):
            # impl.util.log_obj(obj, msg=f'Before "{op_str}"')
            with contextlib.suppress(Exception):
                yield
                op_list.append(op_str)

        if not obj or self._is_orm(obj):
            return obj, op_list

        if not isinstance(obj, bytes):
            with w(obj, f'{obj.__class__.__name__}-to-bytes'):
                obj = self._to_bytes(obj)
        with w(obj, 'decompress'):
            obj = zlib.decompress(obj)
        with w(obj, 'bytes-to-str'):
            obj = obj.decode('utf-8', errors='replace')
        # with w(obj, 'decode'):
        #     obj = obj.decode('utf-8', errors='replace')
        with w(obj, 'from-base64'):
            obj = base64.b64decode(obj, validate=True)
        with w(obj, 'from-json'):
            obj = next(django.core.serializers.deserialize("json", obj))
        with w(obj, 'from-python-str'):
            obj = ast.literal_eval(obj)
        if isinstance(obj, str):
            with w(obj, 'from-nested-python-str'):
                obj = ast.literal_eval(obj)
        with w(obj, 'from-json'):
            obj = json.loads(obj)
        op_list.append(f'to-{obj.__class__.__name__}')
        # if not isinstance(obj, dict):
        #     log.error(f'FINAL: {type(obj)}: {obj!r}')
        return obj, op_list

    # @impl.util.log_inout()
    def _encode(self, obj, json_encoder):
        if self._is_orm(obj):
            return django.core.serializers.serialize("json", [obj])
        return json.dumps(obj, cls=json_encoder)

    # @impl.util.log_inout()
    def _is_orm(self, obj):
        return obj is None or isinstance(
            obj,
            (models.Model, models.Field),
        )

    # @impl.util.log_inout()
    def _to_bytes(self, obj):
        if obj is None:
            return None
        elif isinstance(obj, bytes):
            return obj
        elif isinstance(obj, str):
            return obj.encode('utf-8', errors='replace')
        elif isinstance(obj, memoryview):
            return obj.tobytes()
        else:
            raise AssertionError(f'Unexpected type: {obj!r}')

    # @impl.util.log_inout()
    def _to_str(self, obj):
        obj = self._to_bytes(obj)
        obj = obj.decode('utf-8', errors='replace')
        return obj

    # @impl.util.log_inout()
    def print_model_overview(self):
        # row_list = []
        row_list = [('MODEL', 'TABLE', 'ROWS')]
        for m in django.apps.apps.get_models(include_auto_created=True, include_swapped=True):
            row_list.append(
                (
                    m._meta.label,
                    m._meta.db_table,
                    m.objects.count(),
                    # ','.join(s.name for s in m._meta.fields),
                )
            )
        impl.nog.util.print_table(row_list, log.info)
