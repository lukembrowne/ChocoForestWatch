"""
URL configuration for djangocfw project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    health_check, get_model_metrics, change_analysis, 
    deforestation_hotspots, register, login, user_settings,
    submit_feedback, get_version_info
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', register),
    path('api/auth/login/', login),
    path('api/feedback/', submit_feedback),
    path('api/version/', get_version_info),
    path('api/', include('core.urls')),
    path('api/user/settings/', user_settings),
    # Add other API endpoints here
]

if settings.DEBUG:
    urlpatterns += static(settings.PREDICTION_FILES_URL, document_root=settings.PREDICTION_FILES_ROOT)
