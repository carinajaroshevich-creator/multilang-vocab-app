# Берём официальный лёгкий образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Запрещаем Python писать файлы .pyc на диск и буферизировать лог-файлы
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем зависимости системы (нужны для сборки некоторых пакетов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . /app/

# Команда по умолчанию (например, запуск Django-сервера разработки или gunicorn)
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]