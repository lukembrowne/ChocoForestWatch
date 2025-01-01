FROM python:3.10

# Install system dependencies including GIS packages
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    postgresql-client \
    python3-gdal \
    binutils \
    libproj-dev \
    libgeos-dev

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Install debugpy for VS Code debugging
RUN pip install debugpy

# Set work directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files
#  RUN python manage.py collectstatic --noinput

# Make scripts executable
RUN chmod +x entrypoint.sh
RUN chmod +x wait_for_db.py

# Expose ports
EXPOSE 8000 5678

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 