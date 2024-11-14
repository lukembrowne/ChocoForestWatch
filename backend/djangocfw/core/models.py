from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils import timezone

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    aoi = gis_models.GeometryField(srid=4326, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    classes = models.JSONField(default=list)
    aoi_area_ha = models.FloatField(null=True)

    def __str__(self):
        return self.name