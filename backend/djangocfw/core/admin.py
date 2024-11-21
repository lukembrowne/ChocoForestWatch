from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot, ModelTrainingTask

@admin.register(ModelTrainingTask)
class ModelTrainingTaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'status', 'progress', 'message', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('task_id', 'message', 'error')
    readonly_fields = ('task_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Project)
class ProjectAdmin(gis_admin.GISModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TrainingPolygonSet)
class TrainingPolygonSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'basemap_date', 'feature_count', 'excluded')

@admin.register(TrainedModel)
class TrainedModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at')

@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'model', 'type', 'created_at')

@admin.register(DeforestationHotspot)
class DeforestationHotspotAdmin(admin.ModelAdmin):
    list_display = ('id', 'prediction', 'area_ha', 'verification_status')

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)

# Unregister the default UserAdmin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
