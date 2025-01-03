#!/bin/sh

if [ "$DJANGO_DEBUG" = "True" ]; then
    echo "Starting Quasar in development mode..."
    npx quasar dev --hostname 0.0.0.0
else
    echo "Starting nginx in production mode..."
    nginx -g 'daemon off;'
fi 