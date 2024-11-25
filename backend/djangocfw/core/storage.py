from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings

class ModelStorage(FileSystemStorage):
    def __init__(self):
        # Create base directory for models
        base_dir = './data/models'
        os.makedirs(base_dir, exist_ok=True)
        super().__init__(location=base_dir)

    def get_valid_name(self, name):
        """
        Return a filename that's allowed by the storage system.
        """
        return name

class PredictionStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PREDICTION_FILES_ROOT, base_url=settings.PREDICTION_FILES_URL)

    def get_valid_name(self, name):
        """
        Returns a filename that's suitable for use with the underlying storage system.
        """
        name = super().get_valid_name(name)
        return name

class PlanetQuadStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PLANET_QUADS_ROOT, base_url=settings.PLANET_QUADS_URL)

    def get_valid_name(self, name):
        """
        Returns a filename that's suitable for use with the underlying storage system.
        """
        name = super().get_valid_name(name)
        return name

    def get_year_month_path(self, year, month):
        """
        Returns a path for storing quads by year and month
        """
        return os.path.join(str(year), str(month).zfill(2))

    def exists(self, name):
        """
        Check if a file exists in storage
        """
        return super().exists(name)

    def path(self, name):
        """
        Returns the full filesystem path for the file
        """
        return super().path(name) 