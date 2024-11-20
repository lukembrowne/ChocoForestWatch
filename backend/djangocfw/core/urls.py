from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet)
router.register(r'training-sets', views.TrainingPolygonSetViewSet)
router.register(r'trained-models', views.TrainedModelViewSet)
router.register(r'predictions', views.PredictionViewSet, basename='prediction')
router.register(r'hotspots', views.DeforestationHotspotViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('health/', views.health_check, name='health_check'),
    path('trained_models/<int:project_id>/metrics/', views.get_model_metrics, name='model-metrics'),
    path('analysis/change/', views.change_analysis, name='change-analysis')
]