#!/bin/bash
set -e

echo "Waiting for database..."
while ! pg_isready -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB; do
  sleep 1
done

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating admin user if not exists..."
python manage.py shell <<END
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Admin user created")
else:
    print("Admin user already exists")
END

echo "Starting Gunicorn..."
exec gunicorn app.wsgi:application --bind 0.0.0.0:8000 --workers 4 --worker-class sync --worker-tmp-dir /dev/shm --timeout 30 --access-logfile - --error-logfile -
