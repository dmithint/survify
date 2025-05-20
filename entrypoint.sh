#!/bin/bash

# Применение миграций
echo "Applying migrations..."
python manage.py makemigrations accounts surveys
python manage.py migrate

# Сбор статических файлов
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Запуск сервера Django
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000

