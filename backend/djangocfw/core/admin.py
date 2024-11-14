from django.contrib import admin
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot

admin.site.register(Project)
admin.site.register(TrainingPolygonSet)
admin.site.register(TrainedModel)
admin.site.register(Prediction)
admin.site.register(DeforestationHotspot)
