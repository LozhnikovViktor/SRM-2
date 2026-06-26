# Dockerfile
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем проект
COPY . .

# Собираем статику (игнорируем ошибки, если STATIC_ROOT не настроен)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Для production используйте gunicorn, для dev можно runserver
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]