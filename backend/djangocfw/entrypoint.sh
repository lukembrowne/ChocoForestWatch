#!/bin/sh

# Wait for database to be ready
echo "Waiting for database..."
python wait_for_db.py

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating/Verifying superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created.')
else:
    print('Superuser already exists.')
END

# Start server
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000 