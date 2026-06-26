import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SRM.settings')

app = Celery('SRM')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()