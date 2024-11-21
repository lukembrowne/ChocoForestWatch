from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils import timezone
from django.contrib.auth.models import User
from .storage import ModelStorage, PredictionStorage
from django.db.models import JSONField
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import pre_save
from django.dispatch import receiver

# Add this to ensure unique emails without migration
@receiver(pre_save, sender=User)
def ensure_unique_email(sender, instance, **kwargs):
    email = instance.email.lower()  # Convert to lowercase
    if User.objects.filter(email=email).exclude(id=instance.id).exists():
        raise ValueError('Email already exists')
    instance.email = email

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    aoi = gis_models.GeometryField(srid=4326, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    classes = models.JSONField(default=list)
    aoi_area_ha = models.FloatField(null=True)
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='projects',
        null=True
    )

    def __str__(self):
        return self.name

class TrainingPolygonSet(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='training_polygon_sets'
    )
    basemap_date = models.CharField(max_length=7)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    feature_count = models.IntegerField(null=True)
    excluded = models.BooleanField(default=False)
    polygons = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} - {self.project.name}"

class TrainedModel(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='trained_models'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    training_set_ids = ArrayField(models.IntegerField())
    training_periods = models.IntegerField(null=True)
    num_training_samples = models.IntegerField(null=True)
    model_file = models.FileField(
        upload_to='models',
        storage=ModelStorage(),
        null=True,
        blank=True
    )
    model_parameters = JSONField(default=dict)
    metrics = JSONField(default=dict)
    encoders = JSONField(default=dict)
    all_class_names = JSONField(default=dict)


    def __str__(self):
        return f"{self.name} - {self.project.name}"

    def delete(self, *args, **kwargs):
        # Delete the file when the model is deleted
        if self.model_file:
            self.model_file.delete()
        super().delete(*args, **kwargs)

class Prediction(models.Model):
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='predictions'
    )
    model = models.ForeignKey(
        TrainedModel, 
        on_delete=models.CASCADE,
        related_name='predictions'
    )
    type = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    file = models.FileField(storage=PredictionStorage(), max_length=255, null=True)
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
    prediction = models.ForeignKey(
        Prediction, 
        on_delete=models.CASCADE,
        related_name='hotspots'
    )
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

class ModelTrainingTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    task_id = models.UUIDField(primary_key=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.FloatField(default=0)
    message = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
