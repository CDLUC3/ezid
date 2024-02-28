import os
# even though the following import isn't used in this file, it was needed to not get errors when using the matomo_api_tracking
# middleware.

from matomo_api_tracking.tasks import send_matomo_tracking

from celery import Celery
from celery import Task
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from datetime import timedelta
from contextlib import contextmanager
from django.conf import settings

# Database cleanup is somewhat based on an example from https://github.com/mozilla/ichnaea/issues/22 but I believe
# some of the APIs for sqlalchemy have changed since then which caused confusion. Also, add explicit connect string to
# settings.py file since the strings inside Celery were sanitized of required user/pass info.


class DatabaseTask(Task):
    abstract = True
    acks_late = True
    ignore_result = False
    max_retries = 3

    def db_session(self):
        # returns a context manager

        db_engine = create_engine(settings.CELERY_DB_CONNECT)
        # db_metadata = MetaData(bind=db_engine)
        sm = sessionmaker(bind=db_engine)

        return db_worker_session(sm)


def daily_task_days(ago):
    today = datetime.utcnow().date()
    day = today - timedelta(days=ago)
    max_day = day + timedelta(days=1)
    return day, max_day


@contextmanager
def db_worker_session(session_maker, commit=True, isolation_level=None): # was database as first arg
    """
    Use a database engine usable as a context manager.

    :param commit: Should the session be committed or aborted at the end?
    :type commit: bool
    :param isolation_level: A new isolation level for this session
    """

    session = session_maker()
    try:
        # Yield the session to the code within the 'with' statement
        yield session

        # If commit is True, commit the transaction
        if commit:
            session.commit()
    except Exception:
        # If an exception occurs, rollback the transaction
        if session:
            session.rollback()
        raise
    finally:
        # Regardless of success or failure, release the session
        if session:
            session.close()


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


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # cleanup kombu message table every hour, defaults to keeping 1 day of messages
    sender.add_periodic_task(60.0, cleanup_kombu_message_table.s(1),
                             name='cleanup kombu message table every hour')


@app.task(base=DatabaseTask, ignore_result=False)
def cleanup_kombu_message_table(ago=1):
    day, max_day = daily_task_days(ago)
    stmt = text(
        'delete from kombu_message where '
        'timestamp < "%s" limit 20000;' % day.isoformat()
    )
    with cleanup_kombu_message_table.db_session() as sess:
        sess.execute(stmt)
        sess.commit()
