from celery import Celery
import os
from datetime import datetime
from time import sleep
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zumble.settings')
from django.conf import settings  # noqa
from django.utils import timezone

app = Celery('tasks', broker='redis://localhost:6379/0')


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(10, publish.s(), name='every 10 sec')


@app.task
def add(x, y):
    return x + y


@app.task
def publish():
    from chat.models import Room
    room = Room.objects.get(pk=2)
    if not room.current_question or (timezone.now() - room.current_question.created_at).seconds > 30:
        room.publish_new_question()
