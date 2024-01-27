import os
# even though the following import isn't used in this file, it was needed to not get errors when using the matomo_api_tracking
# middleware.

from matomo_api_tracking.tasks import send_matomo_tracking

from celery import Celery

# Set the default Django settings module for the 'celery' program in setting.py file.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')

app = Celery('ezidapp')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')