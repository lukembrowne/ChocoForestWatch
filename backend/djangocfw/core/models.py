from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils import timezone
from .storage import ModelStorage, PredictionStorage

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

class TrainingPolygonSet(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='training_polygon_sets')
    basemap_date = models.CharField(max_length=7)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feature_count = models.IntegerField(null=True)
    excluded = models.BooleanField(default=False)
    polygons = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} - {self.project.name}"

class TrainedModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='trained_model')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    training_set_ids = models.JSONField()
    training_periods = models.JSONField(null=True)
    num_training_samples = models.IntegerField(null=True)
    accuracy = models.FloatField(null=True)
    class_metrics = models.JSONField(null=True)
    confusion_matrix = models.JSONField(null=True)
    file = models.FileField(storage=ModelStorage(), max_length=255)
    model_parameters = models.JSONField(null=True)
    class_names = models.JSONField(null=True)
    date_encoder = models.BinaryField(null=True)
    month_encoder = models.BinaryField(null=True)
    label_encoder = models.BinaryField(null=True)
    all_class_names = models.JSONField(null=True)

    def __str__(self):
        return f"{self.name} - {self.project.name}"

    def delete(self, *args, **kwargs):
        # Delete the file when the model is deleted
        if self.file:
            self.file.delete()
        super().delete(*args, **kwargs)

class Prediction(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='predictions')
    model = models.ForeignKey(TrainedModel, on_delete=models.CASCADE, related_name='predictions')
    type = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    file = models.FileField(storage=PredictionStorage(), max_length=255)
    basemap_date = models.CharField(max_length=7, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    summary_statistics = models.JSONField(null=True)

    def __str__(self):
        return f"{self.name} - {self.project.name}"

    def delete(self, *args, **kwargs):
        # Delete the file when the prediction is deleted
        if self.file:
            self.file.delete()
        super().delete(*args, **kwargs)

class DeforestationHotspot(models.Model):
    prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE, related_name='hotspots')
    geometry = models.JSONField()
    area_ha = models.FloatField()
    perimeter_m = models.FloatField()
    compactness = models.FloatField()
    edge_density = models.FloatField()
    centroid_lon = models.FloatField()
    centroid_lat = models.FloatField()
    verification_status = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=20, default='ml')
    confidence = models.IntegerField(null=True)

    def __str__(self):
        return f"Hotspot {self.id} - {self.prediction.name}"

# Add the rest of the models...