"""celery configuration file"""
# pylint: disable=invalid-name

import os
from celery.schedules import crontab

# use local time
enable_utc = False

## Broker settings.
broker_url = os.environ['REDIS_URL']

# List of modules to import when the Celery worker starts.
imports = ('tasks',)

task_serializer = 'pickle'
accept_content = ['pickle', 'application/x-python-serialize', 'json', 'application/json']

beat_schedule = {
    "csv-export": {
        "task": "tasks.outbound-csv",
        "schedule": crontab(hour=23, minute=0) # run every day at 11pm
    },
    "csv-import": {
        "task": "tasks.inbound-csv",
        "schedule": crontab(hour=6, minute=0) # run every day at 6am
    }
}
