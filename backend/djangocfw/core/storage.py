from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

class ModelStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.MODEL_FILES_ROOT, base_url=settings.MODEL_FILES_URL)

    def get_valid_name(self, name):
        """
        Returns a filename that's suitable for use with the underlying storage system.
        """
        name = super().get_valid_name(name)
        return f"model_{name}"

class PredictionStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PREDICTION_FILES_ROOT, base_url=settings.PREDICTION_FILES_URL)

    def get_valid_name(self, name):
        """
        Returns a filename that's suitable for use with the underlying storage system.
        """
        name = super().get_valid_name(name)
        return f"prediction_{name}"

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