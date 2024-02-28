from django.core.management.base import BaseCommand
from celery import Celery
from django.apps import apps
import os


class Command(BaseCommand):
    help = 'Starts the celery worker and beat processes'

    def handle(self, *args, **options):
        schedule_path = os.path.abspath(os.path.join(apps.get_app_config('ezidapp').path,
                                                     '../../var/celerybeat-schedule'))
        print(schedule_path)

        # Create a Celery instance and configure it using the settings from Django.
        app = Celery('ezid')
        app.config_from_object('django.conf:settings', namespace='CELERY')

        # Auto-discover tasks in all installed apps.
        app.autodiscover_tasks()

        #
        # Start the Celery worker and beat processes.
        app.worker_main(['worker', '--loglevel=info', '-B', f'-s{schedule_path}'])
