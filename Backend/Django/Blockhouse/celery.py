import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Blockhouse.settings')

app = Celery('Blockhouse')
app.conf.enable_utc = False

app.conf.update(timezone='America/New_York')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'update_summary_report_every_friday_after_market': {
        'task': 'Firms.views.tasks.update_summary_report',
        'schedule': crontab(day_of_week=5, hour=16, minute=30),     # Runs every Friday at 4:30pm aka 30 min after market close.
    }                                                       # Actually might want to consider running it on Saturday at 4:30 pm instead so we get
}                                                           # the data from Friday as well?


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')