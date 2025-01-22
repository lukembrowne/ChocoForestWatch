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
    path('auth/register/', auth_views.register, name='register'),
    path('auth/login/', auth_views.login, name='login'),
    path('auth/request-reset/', auth_views.request_password_reset, name='request-reset'),
    path('auth/reset-password/<str:uidb64>/<str:token>/', auth_views.reset_password, name='reset-password'),
    path('user/settings/', views.user_settings, name='user_settings'),
    path('api/statistics/system/', views.get_system_statistics, name='system-statistics'),
]