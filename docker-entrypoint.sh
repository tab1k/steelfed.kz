#!/bin/bash
# Останавливаем выполнение при ошибке
set -e

# Ожидаем, пока PostgreSQL не запустится
echo "Ожидание PostgreSQL..."
until pg_isready -h postgres -p 5432; do
  sleep 1
done

echo "PostgreSQL доступен, выполняем миграции..."
python src/manage.py migrate

python src/manage.py collectstatic --noinput

# Запускаем сервер Django
echo "Запускаем Django-сервер..."
exec python src/manage.py runserver 0.0.0.0:8000