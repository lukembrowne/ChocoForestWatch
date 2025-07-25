from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, auth_views


router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'training-sets', views.TrainingPolygonSetViewSet)
router.register(r'trained-models', views.TrainedModelViewSet)
router.register(r'predictions', views.PredictionViewSet, basename='prediction')
router.register(r'hotspots', views.DeforestationHotspotViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('health/', views.health_check, name='health_check'),
    path('trained_models/<int:project_id>/metrics/', views.get_model_metrics, name='model-metrics'),
    path('analysis/change/', views.change_analysis, name='change-analysis'),
    path('analysis/deforestation_hotspots/<int:prediction_id>/', views.deforestation_hotspots, name='deforestation-hotspots'),
    path('random_points_collection/<str:collection_id>/', views.get_random_points_within_collection, name='random-points'),
    path('aoi_summary/', views.aoi_summary, name='aoi-summary'),
    path('auth/register/', auth_views.register, name='register'),
    path('auth/login/', auth_views.login, name='login'),
    path('auth/request-reset/', auth_views.request_password_reset, name='request-reset'),
    path('auth/reset-password/<str:uidb64>/<str:token>/', auth_views.reset_password, name='reset-password'),
    path('user/settings/', views.user_settings, name='user_settings'),
    path('api/statistics/system/', views.get_system_statistics, name='system-statistics'),
    path('western_ecuador_stats/', views.get_western_ecuador_stats, name='western-ecuador-stats'),
    path('datasets/', views.get_datasets, name='datasets'),
    path('datasets/collections/', views.get_dataset_collections, name='dataset-collections'),
]