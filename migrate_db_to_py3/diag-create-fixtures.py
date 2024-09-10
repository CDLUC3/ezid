#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import pathlib
import random
import time

import django
import django.apps
import django.conf
import django.contrib.auth.models
import django.contrib.sessions.models
import django.core.management
import django.db
import django.db.transaction
import django.http.request

import ezidapp.models.async_queue
import ezidapp.models.identifier
import ezidapp.models.user
import impl.download
import impl.enqueue
import impl.log
import impl.nog_sql.filesystem
import impl.nog_sql.shoulder
import impl.nog_sql.util

APP_LABEL = 'ezidapp'

HERE_PATH = pathlib.Path(__file__).parent.resolve()
ROOT_PATH = HERE_PATH / '..'

DEFAULT_DB_KEY = 'default'

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def handle(self, *_, **opt):
        # dump_models()
        create_fixtures()


def dump_models():
    """Print a list of registered models"""
    model_dict = {model.__name__: model for model in django.apps.apps.get_models()}
    print('Registered models:')
    for k, v in sorted(model_dict.items()):
        print(f'  {k:<20} {v}')


def create_fixtures():
    fixture_dir_path = pathlib.Path(impl.nog_sql.filesystem.abs_path('../../../ezidapp/fixtures'))
    # populate_async_queue()
    # ezidapp.DownloadQueue        ezidapp_downloadqueue
    # populate_async_queue()
    # ezidapp.BinderQueue          ezidapp_binderqueue
    # ezidapp.CrossrefQueue        ezidapp_crossrefqueue
    # ezidapp.DataciteQueue        ezidapp_datacitequeue

    populate_registration_queue()





    return





    for blob_tup in django.conf.settings.BLOB_FIELD_LIST:
        if not blob_tup.is_queue:
            continue

        log.info(f'Creating fixtures for queue: {blob_tup.model}')

        # print(blob_tup.model)
        # file_name = f'{table_name.replace("queue", "_queue")}.json'
        # # file_path = HERE_PATH / '../../ezidapp/fixtures'
        # fixture_file_path = fixture_dir_path / file_name
        #
        # create_model_fixture(fixture_file_path, model_label)
        # # log.info('Writing fixture. path="{}"'.format(fixture_file_path))
        # buf = io.BytesIO()

        django.core.management.call_command(
            "dumpdata",
            f'{APP_LABEL}.{blob_tup.model}',
            # exclude=["auth.permission", "contenttypes"],
            database=DEFAULT_DB_KEY,
            # stdout=buf,
            # --indent=2 -v2 --traceback gigs
            indent=2,
            verbosity=3,
            traceback=True,
            # skip_checks=True,
        )

    # django_load_db_fixture('ezidapp/fixtures/registration_queue.json')


def create_model_fixture(path, model_name):
    n = f'{APP_LABEL}.{model_name.lower()}'
    log.info(f'Creating DB fixture: {n} -> {path.as_posix()}')
    with path.open('w', encoding='utf-8', errors='replace') as f:
        django.core.management.call_command('dumpdata', n, stdout=f, traceback=True)


# # TODO: Write directly to compressed fixture
# def create_model_fixture(path, model_name):
#     n = f'{APP_LABEL}.{model_name.lower()}'
#     log.info(f'Creating DB fixture: {n} -> {path.as_posix()}')
#     with path.open('wb') as bytes_f:
#         with bz2.BZ2File(bytes_f, mode='w', compresslevel=9) as bz2_file:
#             # bz2_file.write(b'some bytes')
#             with io.TextIOWrapper(bz2_file, encoding='utf-8') as str_f:
#                 django.core.management.call_command('dumpdata', n, stdout=str_f)

# with path.open('w') as f:
#     django.core.management.call_command('dumpdata', n, stdout=f)
#     # buf.seek(0)
#     # f.write(buf.read())
# with bz2.BZ2File(
#     fixture_file_path, "w", buffering=1024 ** 2, compresslevel=9
# ) as bz2_file:
#     bz2_file.write(buf.getvalue())


def populate_registration_queue():
    for id_model in get_rnd_identifier_list():
        print(id_model.identifier)
        impl.enqueue.enqueueBinderIdentifier(
            identifier=id_model.identifier,
            operation=random.choice(['update', 'create', 'delete']),
            blob=id_model.cm,
        )


def get_rnd_identifier_list(k=10):
    id_list = list(ezidapp.models.identifier.Identifier.objects.all())
    # print(id_list)
    return random.sample(id_list, k)


def populate_async_queue():
    """Generate DownloadQueue rows"""
    ezidapp.models.async_queue.DownloadQueue.objects.all().delete()
    user_list = ezidapp.models.user.User.objects.all()
    for _ in range(10):
        r = ezidapp.models.async_queue.DownloadQueue(
            requestTime=int(time.time()),
            rawRequest='',  # request.urlencode(),
            requestor=random.choice(user_list),
            format=random.choice(
                [
                    ezidapp.models.async_queue.DownloadQueue.ANVL,
                    ezidapp.models.async_queue.DownloadQueue.CSV,
                    ezidapp.models.async_queue.DownloadQueue.XML,
                ]
            ),
            compression=random.choice(
                [
                    ezidapp.models.async_queue.DownloadQueue.GZIP,
                    ezidapp.models.async_queue.DownloadQueue.ZIP,
                ]
            ),
            columns=random.sample(
                [
                    'datacite.creator',
                    'datacite.publicationyear',
                    'datacite.publisher',
                    'datacite.title',
                    'datacite.type',
                    'dc.creator',
                    'dc.date',
                    'dc.publisher',
                    'dc.title',
                    'dc.type',
                    'erc.what',
                    'erc.what',
                    'erc.when',
                    'erc.when',
                    'erc.who',
                    'erc.who',
                ],
                k=5,
            ),
            constraints=impl.download.encode({}),
            options=impl.download.encode({"convertTimestamps": random.choice([True, False])}),
            notify=impl.download.encode(
                random.choice(
                    [
                        'email1@inv.invalid',
                        'email2@inv.invalid',
                        'email3@inv.invalid',
                        'email4@inv.invalid',
                        'email5@inv.invalid',
                    ]
                )
            ),
            filename=random.choice(
                random.choice(
                    [
                        'a/b/c/file_1.csv',
                        'a/b/c/file_2.csv',
                        'a/b/c/file_3.csv',
                        'a/b/c/file_4.csv',
                        'a/b/c/file_5.csv',
                    ]
                )
            ),
            toHarvest=",".join(random.sample([u.pid for u in user_list])),
            fileSize=random.randint(1, 10000),
        )
        r.save()


# def enqueueBinderIdentifier(identifier, operation, blob):
#     """Add an identifier to the binder asynchronous processing queue
#
#     'identifier' should be the normalized, qualified identifier, e.g.,
#     "doi:10.5060/FOO". 'operation' is the identifier operation and
#     should be one of the strings "create", "update", or "delete". 'blob'
#     is the identifier's metadata dictionary in blob form.
#     """
#     _enqueueIdentifier(
#         ezidapp.models.registration_queue.BinderQueue, identifier, operation, blob
#     )
#
#
# def enqueueCrossrefIdentifier(identifier, operation, metadata, blob):
#     """Add an identifier to the Crossref queue
#
#     'identifier' should be the normalized, qualified identifier, e.g.,
#     "doi:10.5060/FOO". 'operation' is the identifier operation and should
#     be one of the strings "create", "update", or "delete". 'metadata' is
#     the identifier's metadata dictionary; 'blob' is the same in blob form.
#     """
#     e = ezidapp.models.registration_queue.CrossrefQueue(
#         identifier=identifier,
#         owner=metadata["_o"],
#         metadata=blob,
#         operation=ezidapp.models.registration_queue.CrossrefQueue.operationLabelToCode(
#             operation
#         ),
#     )
#     e.save()
#
#
# def enqueueDataCiteIdentifier(identifier, operation, blob):
#     """Add an identifier to the DataCite asynchronous processing queue
#
#     'identifier' should be the normalized, qualified identifier, e.g.,
#     "doi:10.5060/FOO". 'operation' is the identifier operation and
#     should be one of the strings "create", "update", or "delete". 'blob'
#     is the identifier's metadata dictionary in blob form.
#     """
#     _enqueueIdentifier(
#         ezidapp.models.registration_queue.DataciteQueue, identifier, operation, blob
#     )
#
#
# def _enqueueIdentifier(model, identifier, operation, blob):
#     """Add an identifier to the asynchronous registration queue named by
#     'model'.
#
#     'identifier' should be the normalized, qualified identifier, e.g.,
#     "doi:10.5060/FOO". 'operation' is the identifier operation and
#     should be one of the strings "create", "update", or "delete".
#     'blob' is the identifier's metadata dictionary in blob form.
#     """
#     e = model(
#         enqueueTime=int(time.time()),
#         identifier=identifier,
#         metadata=blob,
#         operation=ezidapp.models.registration_queue.AsyncQueue.operationLabelToCode(
#             operation
#         ),
#     )
#     e.save()
#
#
# def assert_daemon_enabled(setting_name):
#     assert isinstance(
#         setting_name, str
#     ), 'Call with the name of a DAEMONS_*_ENABLED setting, not the value.'
#     if not django.conf.settings.DAEMONS_ENABLED:
#         return False
#     v = getattr(django.conf.settings, setting_name, None)
#     assert v is not None, f'Unknown setting: {setting_name}'
#     assert v in (
#         True,
#         False,
#     ), f'Setting must be a boolean, not {type(setting_name)}'
#     return v
