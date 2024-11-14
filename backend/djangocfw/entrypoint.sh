#!/bin/sh

# Wait for database to be ready
echo "Waiting for database..."
python wait_for_db.py

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start server
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000 