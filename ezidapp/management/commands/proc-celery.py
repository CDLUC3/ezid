from django.core.management.base import BaseCommand
from celery import Celery
from django.apps import apps
import os


class Command(BaseCommand):
    help = 'Starts the celery worker and beat processes'

    def handle(self, *args, **options):
        schedule_path = os.path.abspath(os.path.join(apps.get_app_config('ezidapp').path,
                                                     '../../var/celerybeat-schedule'))

        # Create a Celery instance and configure it using the settings from Django.
        app = Celery('ezid')
        app.config_from_object('django.conf:settings', namespace='CELERY')

        # Auto-discover tasks in all installed apps.
        app.autodiscover_tasks()

        # Configure the periodic tasks -- the "add" schedule defined in celery.py doesn't run automatically when started here
        # See bug report https://github.com/celery/celery/issues/3589
        # It's added the following way instead - See comment about workaround by LaPetitSouris
        app.conf.beat_schedule = {
            'cleanup-every-hour': {
                'task': 'ezidapp.celery.cleanup_kombu_message_table',
                'schedule': 60*60, # task runs once an hour
                'args': (1,) # and limits saved messages to last day
            },
        }

        #
        # Start the Celery worker and beat processes.
        app.worker_main(['worker', '--loglevel=info', '-B', f'-s{schedule_path}'])
