from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot

@admin.register(Project)
class ProjectAdmin(gis_admin.GISModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(TrainingPolygonSet)
admin.site.register(TrainedModel)
admin.site.register(Prediction)
admin.site.register(DeforestationHotspot)
