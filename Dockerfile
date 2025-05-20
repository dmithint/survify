FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей для сборки и работы приложения
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Делаем entrypoint.sh исполняемым
RUN chmod +x entrypoint.sh

# Открываем порт
EXPOSE 8000

# Запуск приложения через entrypoint скрипт
ENTRYPOINT ["/app/entrypoint.sh"]

