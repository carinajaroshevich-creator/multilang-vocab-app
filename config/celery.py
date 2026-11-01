import os
from celery import Celery

# Устанавливаем настройки Django по умолчанию для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Читаем конфигурацию из settings.py, все настройки Celery должны начинаться с CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически ищем задачи (tasks.py) во всех зарегистрированных приложениях (apps)
app.autodiscover_tasks()