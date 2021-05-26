import random

import ezidapp.models.identifier
import ezidapp.models.update_queue
import bz2
import io
import logging
import pathlib

import django
import django.apps
import django.conf
import django.conf
import django.contrib.auth.models
import django.contrib.sessions.models
import django.core.management
import django.db
import django.db.transaction
import django.http.request

import impl.log
import impl.nog.filesystem
import impl.nog.shoulder
import impl.nog.util
import impl.noid_egg

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
    """Queue tables:

    ezidapp_binderqueue
    ezidapp_crossrefqueue
    ezidapp_datacitequeue
    ezidapp_downloadqueue
    ezidapp_updatequeue
    """
    fixture_dir_path = pathlib.Path(
        impl.nog.filesystem.abs_path('../../../ezidapp/fixtures')
    )

    populate_update_queue()


    return


    for model_label in (
        # 'BinderQueue',
        # 'CrossrefQueue',
        # 'DataciteQueue',
        # 'DownloadQueue',
        'UpdateQueue',
        # 'LinkChecker',
    ):
        table_name = model_label.lower()
        file_name = f'{table_name.replace("queue", "_queue")}.json'
        # file_path = HERE_PATH / '../../ezidapp/fixtures'
        fixture_file_path = fixture_dir_path / file_name

        create_model_fixture(fixture_file_path, model_label)
        # log.info('Writing fixture. path="{}"'.format(fixture_file_path))
        # buf = io.BytesIO()
        # django.core.management.call_command(
        #     "dumpdata",
        #     f'{APP_LABEL}.{model_label}',
        #     # exclude=["auth.permission", "contenttypes"],
        #     database=DEFAULT_DB_KEY,
        #     # stdout=buf,
        #     # --indent=2 -v2 --traceback gigs
        #     indent=2,
        #     verbosity=2,
        #     traceback='gigs',
        #     # skip_checks=True,
        # )

    # django_load_db_fixture('ezidapp/fixtures/binder_queue.json')


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


def populate_update_queue():
    """Generate UpdateQueue rows"""
    ezidapp.models.update_queue.UpdateQueue.objects.all().delete()
    id_list = [i.id for i in ezidapp.models.identifier.StoreIdentifier.objects.all()]
    rnd_list = random.sample(id_list, 5)
    for m in ezidapp.models.identifier.StoreIdentifier.objects.filter(id__in=rnd_list):
        ezidapp.models.update_queue.enqueue(
            object=m,
            operation='update',  # 'create', 'delete'
            updateExternalServices=True,
            identifier=None,
        )
    pass
