#!/usr/bin/env bash
celery -A tasks beat -l debug &
celery -A tasks worker --loglevel=info &
python manage.py runserver 8091 &
