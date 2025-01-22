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
    admin_user = os.getenv('DJANGO_ADMIN_USER', 'admin')
    admin_email = os.getenv('DJANGO_ADMIN_EMAIL', 'admin@yourdomain.com')
    admin_password = os.getenv('DJANGO_ADMIN_PASSWORD')
    if admin_password:
        User.objects.create_superuser(admin_user, admin_email, admin_password)
        print('Superuser created with provided credentials.')
    else:
        print('WARNING: No DJANGO_ADMIN_PASSWORD provided. Skipping superuser creation.')
        print('Please set a password manually using python manage.py createsuperuser')
        print('Superuser created.')
else:
    print('Superuser already exists.')
END

# Create example project
echo "Creating example project..."
python manage.py create_template_project

# Start server
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000 