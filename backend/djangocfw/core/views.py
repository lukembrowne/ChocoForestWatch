from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, permission_classes
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot, ModelTrainingTask, UserSettings, Feedback
from .serializers import (ProjectSerializer, TrainingPolygonSetSerializer, 
                         TrainedModelSerializer, PredictionSerializer, 
                         DeforestationHotspotSerializer, UserSerializer, UserSettingsSerializer)
from loguru import logger
import json
from django.conf import settings
from django.http import JsonResponse
from .services.deforestation import analyze_change, get_deforestation_hotspots
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from djangocfw.version import __version__
from rest_framework.permissions import AllowAny
from sentry_sdk import capture_message, capture_exception
from django.db.models import Sum, Count
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
from ml_pipeline.extractor import TitilerExtractor
from datetime import datetime
import logging
import os
import random
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from pathlib import Path
import requests
from pyproj import Transformer
from shapely.ops import transform
from ml_pipeline.summary_stats import AOISummaryStats
from django.core.cache import cache

logger = logging.getLogger(__name__)

_global_boundary_polygon = None  # cache for boundary geometry
_global_boundary_polygon_wgs84 = None  # cache for boundary geometry in WGS84

DEFAULT_PUBLIC_PROJECT_ID = int(os.getenv("DEFAULT_PUBLIC_PROJECT_ID"))

# ---------------------------------------------------------------------------
# Dynamic dataset validation - collections are now managed through JSON config
# Use dataset_service.get_enabled_collection_ids() instead of hardcoded lists
# ---------------------------------------------------------------------------

def get_allowed_datasets():
    """Get enabled dataset collections from JSON configuration"""
    from .dataset_service import get_enabled_collection_ids
    return get_enabled_collection_ids()

def _load_boundary_polygon():
    """Load and cache the project boundary as a shapely geometry in Web Mercator projection."""
    global _global_boundary_polygon
    if _global_boundary_polygon is not None:
        return _global_boundary_polygon

    # Path to the GeoJSON that defines the project boundary. Allow override via env var.
    boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")

    try:
        if boundary_path.startswith("http://") or boundary_path.startswith("https://"):
            resp = requests.get(boundary_path, timeout=30)
            resp.raise_for_status()
            geojson = resp.json()
        else:
            with open(boundary_path, "r", encoding="utf-8") as f:
                geojson = json.load(f)
        
        # Load geometries and convert to Web Mercator
        # Create transformer from WGS84 to Web Mercator
        project = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
        
        # Load and transform each geometry
        geoms = []
        for feat in geojson.get("features", []):
            geom = shape(feat["geometry"])
            # Transform to Web Mercator
            geom_3857 = transform(project, geom)
            geoms.append(geom_3857)
            
        _global_boundary_polygon = unary_union(geoms)
        logger.info(f"Loaded and projected boundary polygon from {boundary_path}")
    except Exception as exc:
        logger.error(f"Failed to load boundary polygon: {exc}")
        _global_boundary_polygon = None

    return _global_boundary_polygon

def _load_boundary_polygon_wgs84():
    """Load and cache the project boundary as a shapely geometry in WGS84 projection."""
    global _global_boundary_polygon_wgs84
    if _global_boundary_polygon_wgs84 is not None:
        return _global_boundary_polygon_wgs84
    
    # Path to the GeoJSON that defines the project boundary. Allow override via env var.
    boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")
    try:
        if boundary_path.startswith("http://") or boundary_path.startswith("https://"):
            resp = requests.get(boundary_path, timeout=30)
            resp.raise_for_status()
            geojson = resp.json()
        else:
            with open(boundary_path, "r", encoding="utf-8") as f:
                geojson = json.load(f)
        
        # Load geometries in WGS84 (no transformation needed)
        geoms = []
        for feat in geojson.get("features", []):
            geom = shape(feat["geometry"])
            geoms.append(geom)
            
        _global_boundary_polygon_wgs84 = unary_union(geoms)
        logger.info(f"Loaded boundary polygon in WGS84 from {boundary_path}")
    except Exception as exc:
        logger.error(f"Failed to load boundary polygon in WGS84: {exc}")
        _global_boundary_polygon_wgs84 = None
    return _global_boundary_polygon_wgs84

@api_view(['GET'])
def health_check(request):
    return Response({
        "status": "healthy",
        "timestamp": timezone.now().isoformat()
    })

class ProjectViewSet(viewsets.ModelViewSet):
    """Projects owned by user; anonymous visitors get read-only access to a single public project."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    
    def get_queryset(self):
        """Authenticated users see their projects; anonymous users see only the public project."""
        if self.request.user and self.request.user.is_authenticated:
            return Project.objects.filter(owner=self.request.user)
        # Anonymous: expose just the default public project
        return Project.objects.filter(id=DEFAULT_PUBLIC_PROJECT_ID)
    
    def perform_create(self, serializer):
        # Automatically set the owner when creating a new project
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        try:
            logger.debug(f"Update request data: {request.data}")

            # Handle AOI update
            if 'aoi' in request.data:
                aoi_data = request.data['aoi']
                aoi_extent = request.data.get('aoi_extent_lat_lon')
                basemap_dates = request.data.get('basemap_dates')
                
                logger.debug(f"AOI data: {aoi_data}")
                logger.debug(f"AOI extent: {aoi_extent}")
                logger.debug(f"Basemap dates: {basemap_dates}")

                try:
                    # Convert the geometry data to GeoJSON format if it isn't already
                    if isinstance(aoi_data, dict):
                        geojson = {
                            'type': 'Polygon',
                            'coordinates': aoi_data['coordinates']
                        } if aoi_data.get('type') == 'Polygon' else aoi_data
                        instance.aoi = GEOSGeometry(str(geojson))
                    else:
                        instance.aoi = GEOSGeometry(aoi_data)
                    
                    if instance.aoi:
                        instance.aoi_area_ha = instance.aoi.area / 10000
                        logger.debug(f"Calculated area: {instance.aoi_area_ha} ha")
                except Exception as e:
                    logger.error(f"Error converting geometry: {str(e)}")
                    logger.error(f"Geometry data was: {aoi_data}")
                    return Response(
                        {"error": f"Invalid geometry format: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            logger.info(f"Successfully updated project {instance.id}")
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            return Response(
                {"error": f"Failed to update project: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        project = serializer.instance
        basemap_dates = request.data.get('basemap_dates', [])
        if basemap_dates:
            self.initialize_training_polygon_sets(project, basemap_dates)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def initialize_training_polygon_sets(self, project, basemap_dates):
        for date in basemap_dates:
            TrainingPolygonSet.objects.create(
                project=project,
                basemap_date=date,
                name=f"Training_Set_{date}",
                polygons={"type": "FeatureCollection", "features": []},
                feature_count=0,
                excluded=False
            )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a project with all its related data"""
        try:
            source_project = self.get_object()
            
            # Check if user has permission to view the source project
            if not self.request.user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Allow duplication if user owns the project or if it's the public project
            if (source_project.owner != self.request.user and 
                source_project.id != DEFAULT_PUBLIC_PROJECT_ID):
                return Response(
                    {"error": "Permission denied"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Duplicate the project
            new_project = Project.duplicate_project(
                source_project, 
                self.request.user
            )
            
            # Serialize the new project
            serializer = self.get_serializer(new_project)
            
            logger.info(f"Project {source_project.id} duplicated as {new_project.id} by user {self.request.user.id}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error duplicating project: {str(e)}")
            return Response(
                {"error": f"Failed to duplicate project: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class TrainingPolygonSetViewSet(viewsets.ModelViewSet):
    queryset = TrainingPolygonSet.objects.all()
    serializer_class = TrainingPolygonSetSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned training sets by filtering against
        project_id or set_id query parameters in the URL.
        """
        queryset = TrainingPolygonSet.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        set_id = self.request.query_params.get('id', None)

        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        if set_id is not None:
            queryset = queryset.filter(id=set_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override the create method to set feature_count based on polygons provided.
        """
        polygons = request.data.get('polygons', {})
        feature_count = len(polygons.get('features', []))
        request.data['feature_count'] = feature_count
        logger.debug(f"Setting feature_count to {feature_count} for new TrainingPolygonSet")

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Existing update method that sets feature_count when polygons are updated.
        """
        try:
            instance = self.get_object()
            logger.debug(f"Updating training set {instance.id} with data: {request.data}")

            # Update feature count if polygons are provided
            if 'polygons' in request.data:
                request.data['feature_count'] = len(request.data['polygons'].get('features', []))

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            logger.info(f"Successfully updated training set {instance.id}")
            return Response(serializer.data)

        except ValidationError as e:
            logger.error(f"Validation error updating training set: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating training set: {str(e)}")
            return Response(
                {"error": f"Failed to update training set: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['put'])
    def excluded(self, request, pk=None):
        training_set = self.get_object()
        excluded = request.data.get('excluded', False)
        training_set.excluded = excluded
        training_set.save()
        return Response({'message': 'Training set excluded status updated successfully'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for training data"""
        try:
            project_id = request.query_params.get('project_id')
            if not project_id:
                return Response({"error": "Project ID is required"}, status=400)

            training_sets = TrainingPolygonSet.objects.filter(
                project_id=project_id,
                excluded=False,
                feature_count__gt=0
            )
            
            summary = {
                'totalSets': training_sets.count(),
                'classStats': {},
                'trainingSetDates': []
            }

            # Get project and class names
            project = Project.objects.get(id=project_id)
            class_names = [cls['name'] for cls in project.classes]

            # Initialize class statistics
            for class_name in class_names:
                summary['classStats'][class_name] = {
                    'featureCount': 0,
                    'totalAreaHa': 0
                }

            # Process each training set
            for training_set in training_sets:
                summary['trainingSetDates'].append(training_set.basemap_date)
                
                # Process features in the training set
                for feature in training_set.polygons.get('features', []):
                    class_name = feature['properties']['classLabel']
                    summary['classStats'][class_name]['featureCount'] += 1

                    # Calculate area in hectares
                    geom = GEOSGeometry(json.dumps(feature['geometry']))
                    area_ha = geom.area / 10000  # Convert to hectares
                    summary['classStats'][class_name]['totalAreaHa'] += area_ha

            # Round area values
            for class_stats in summary['classStats'].values():
                class_stats['totalAreaHa'] = round(class_stats['totalAreaHa'], 2)

            return Response(summary)

        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating training data summary: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TrainedModelViewSet(viewsets.ModelViewSet):
    queryset = TrainedModel.objects.all()
    serializer_class = TrainedModelSerializer

    # Store active training services
    _active_services = {}

    def get_queryset(self):
        queryset = TrainedModel.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=False, methods=['post'])
    def train(self, request):
        """Train a new model and generate predictions"""
        try:
            project_id = request.data.get('project_id')
            model_name = request.data.get('model_name')
            model_description = request.data.get('model_description', '')
            training_set_ids = request.data.get('training_set_ids', [])
            model_params = request.data.get('model_parameters', {})
            
            # Validate required parameters
            if not all([project_id, model_name, training_set_ids]):
                return Response({
                    'error': 'Missing required parameters'
                }, status=400)

            # Create service and training task
            service = ModelTrainingService(project_id)
            task_id = service.create_training_task()
            
            # Store the service instance
            self._active_services[str(task_id)] = service
            
            # Start training process asynchronously - predictions will be generated after training
            service.start_training_async(
                model_name,
                model_description,
                training_set_ids,
                model_params
            )

            return Response({
                'taskId': str(task_id),
                'message': 'Training and prediction generation started'
            })

        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'], url_path='training_progress/(?P<task_id>[^/.]+)')
    def training_progress(self, request, task_id=None):
        """Get training progress for a specific task"""
        try:
            logger.debug(f"Getting training progress for task {task_id}")
            task = ModelTrainingTask.objects.get(task_id=task_id)
            return Response({
                'status': task.status,
                'progress': task.progress,
                'message': task.message,
                'error': task.error
            })
        except ModelTrainingTask.DoesNotExist:
            return Response({
                'error': 'Training task not found'
            }, status=404)

    @action(detail=False, methods=['post'], url_path='training_progress/(?P<task_id>[^/.]+)/cancel')
    def cancel_training(self, request, task_id=None):
        """Cancel a training task"""
        try:
            task = ModelTrainingTask.objects.get(task_id=task_id)
            
            # Get the service instance and cancel training
            service = self._active_services.get(str(task_id))
            if service:
                service.cancel_training()
                # Clean up the service reference
                del self._active_services[str(task_id)]
            
            task.status = 'cancelled'
            task.message = 'Training cancelled by user'
            task.save()
            
            return Response({
                'status': 'cancelled',
                'message': 'Training cancelled successfully'
            })
        except ModelTrainingTask.DoesNotExist:
            return Response({
                'error': 'Training task not found'
            }, status=404)
        except Exception as e:
            return Response({
                'error': f'Error cancelling training: {str(e)}'
            }, status=500)

class PredictionViewSet(viewsets.ModelViewSet):
    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer

    def get_queryset(self):
        queryset = Prediction.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new prediction"""
        try:
            model_id = request.data.get('model_id')
            project_id = request.data.get('project_id')
            aoi_shape = request.data.get('aoi_shape')
            basemap_date = request.data.get('basemap_date')
            prediction_name = request.data.get('name')

            service = PredictionService(model_id, project_id)
            prediction = service.generate_prediction(
                aoi_shape,
                basemap_date,
                prediction_name
            )

            return Response({
                'prediction_id': prediction.id,
                'file_path': prediction.file_path,
                'summary_statistics': prediction.summary_statistics
            })

        except Exception as e:
            return Response({'error': str(e)}, status=400)

    def get_predictions(self, request, project_id):
        predictions = Prediction.objects.filter(project_id=project_id)
        predictions_data = []
        
        for prediction in predictions:
            # Use PREDICTION_FILES_URL instead of media URL
            file_url = settings.PREDICTION_FILES_URL + prediction.file.name if prediction.file else None
            
            prediction_data = {
                'id': prediction.id,
                'basemap_date': prediction.basemap_date,
                'type': prediction.type,
                'file': request.build_absolute_uri(file_url) if file_url else None,
            }
            predictions_data.append(prediction_data)
        
        return JsonResponse({'data': predictions_data})

    @action(detail=True, methods=['GET'], url_path='summary')
    def get_summary_statistics(self, request, pk=None):
        """Get summary statistics for a prediction"""
        try:
            prediction = self.get_object()
            if not prediction.summary_statistics:
                return Response(
                    {"error": "No summary statistics available for this prediction"},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(prediction.summary_statistics)
        except Exception as e:
            return Response(
                {"error": f"Failed to get summary statistics: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class DeforestationHotspotViewSet(viewsets.ModelViewSet):
    queryset = DeforestationHotspot.objects.all()
    serializer_class = DeforestationHotspotSerializer

    @action(detail=True, methods=['put'])
    def verify(self, request, pk=None):
        hotspot = self.get_object()
        status = request.data.get('status')
        
        if status not in ['verified', 'rejected', 'unsure']:
            return Response({"error": "Invalid status"}, status=400)
            
        hotspot.verification_status = status
        hotspot.save()
        return Response({"message": "Hotspot verification updated"})

@api_view(['GET'])
def get_datasets(request):
    """Get datasets from JSON configuration"""
    from .dataset_service import get_enabled_datasets
    
    dataset_type = request.GET.get('type', None)
    datasets = get_enabled_datasets(dataset_type)
    
    return Response({'datasets': datasets})

@api_view(['GET'])
def get_dataset_collections(request):
    """Get dataset collection IDs from JSON configuration"""
    from .dataset_service import get_enabled_collection_ids
    
    dataset_type = request.GET.get('type', None)
    collections = get_enabled_collection_ids(dataset_type)
    
    return Response({'collections': collections})

@api_view(['GET'])
def get_model_metrics(request, project_id):
    """
    Retrieve metrics for the most recent trained model of a project
    """
    try:
        # Get the latest model for the project
        model = TrainedModel.objects.filter(project_id=project_id).latest('created_at')
        
        # Convert model data to dictionary format
        metrics = {
            'created_at': model.created_at.isoformat(),
            'updated_at': model.updated_at.isoformat() if model.updated_at else None,
            'accuracy': model.metrics.get('accuracy'),
            'class_metrics': model.metrics.get('class_metrics', {}),
            'confusion_matrix': model.metrics.get('confusion_matrix', []),
            'class_names': model.metrics.get('class_names', []),
            'classes_in_training': model.metrics.get('classes_in_training', []),
            'model_parameters': model.model_parameters
        }
        
        return Response(metrics)
        
    except TrainedModel.DoesNotExist:
        return Response(
            {'error': 'No model found for this project'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting model metrics: {str(e)}")
        return Response(
            {'error': 'Server error occurred', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def change_analysis(request):
    """
    Analyze change between two predictions
    """
    try:
        data = request.data
        results = analyze_change(
            prediction1_id=data['prediction1_id'],
            prediction2_id=data['prediction2_id'],
            aoi_shape=data['aoi_shape']
        )

        return Response(results)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
def deforestation_hotspots(request, prediction_id):
    """Get deforestation hotspots for a prediction"""
    try:
        min_area_ha = float(request.query_params.get('min_area_ha', 1.0))
        source = request.query_params.get('source', 'all')
        
        result = get_deforestation_hotspots(prediction_id, min_area_ha, source)
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Create user settings with preferred language
        UserSettings.objects.create(
            user=user,
            preferred_language=request.data.get('preferred_language', 'en')
        )
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'preferred_language': request.data.get('preferred_language', 'en')
            },
            'message': 'User Created Successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        # Get or create user settings
        settings, _ = UserSettings.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'preferred_language': settings.preferred_language
            }
        })
    return Response({'error': 'Invalid credentials'}, status=400)

@api_view(['GET', 'PATCH'])
def user_settings(request):
    """Get or update user settings"""
    try:
        settings = request.user.settings
    except User.settings.RelatedObjectDoesNotExist:
        settings = UserSettings.objects.create(user=request.user)

    if request.method == 'GET':
        serializer = UserSettingsSerializer(settings)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        for key, value in request.data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        settings.save()
        return Response(status=204)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    try:
        feedback = Feedback.objects.create(
            user=request.user,
            type=request.data.get('type'),
            message=request.data.get('message'),
            page_url=request.data.get('pageUrl'),
            browser_info=request.data.get('browserInfo')
        )

        # Send email notification
        subject = f'Choco Forest Watch - New Feedback: {feedback.get_type_display()}'
        message = f"""
        Type: {feedback.get_type_display()}
        User: {feedback.user.username}
        Page: {feedback.page_url}
        Message: {feedback.message}
        
        Browser Info:
        {json.dumps(feedback.browser_info, indent=2)}
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],
            fail_silently=False,
        )

        return Response({'message': 'Feedback submitted successfully'})
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_version_info(request):
    """Return version information about the API"""
    return Response({
        'version': __version__,
        'environment': 'production' if not settings.DEBUG else 'development',
        'api_root': request.build_absolute_uri('/api/'),
    })

def test_sentry(request):
    try:
        division_by_zero = 1 / 0
    except Exception as e:
        capture_exception(e)
        return JsonResponse({"status": "error sent to sentry"}, status=500)

def is_superuser(user):
    return user.is_superuser

@api_view(['GET'])
@user_passes_test(is_superuser)
def get_system_statistics(request):
    """Get system-wide statistics (superuser only)"""
    try:
        # Calculate current statistics
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Exclude example projects
        real_projects = Project.objects.exclude(name='Example Project')

        stats = {
            'total_users': User.objects.filter(is_active=True).count(),
            'total_projects': real_projects.count(),
            'total_models': TrainedModel.objects.count(),
            'total_area_ha': real_projects.aggregate(Sum('aoi_area_ha'))['aoi_area_ha__sum'] or 0,
            'total_hotspots': DeforestationHotspot.objects.count(),
            'active_users_30d': User.objects.filter(last_login__gte=thirty_days_ago).count(),
            'projects_by_class': real_projects.values('classes__name').annotate(count=Count('id')),
            'hotspots_by_status': DeforestationHotspot.objects.values('verification_status').annotate(count=Count('id')),
            'models_by_date': TrainedModel.objects.extra(
                select={'date': 'date(created_at)'}
            ).values('date').annotate(count=Count('id')).order_by('-date')[:30],
            'hotspots_by_source': DeforestationHotspot.objects.values('source').annotate(count=Count('id')),
            'hotspots_by_source_and_status': DeforestationHotspot.objects.values(
                'source', 
                'verification_status'
            ).annotate(count=Count('id')),
            'total_deforestation_area': DeforestationHotspot.objects.aggregate(
                total_area=Sum('area_ha')
            )['total_area'] or 0,
            'deforestation_by_status': DeforestationHotspot.objects.values(
                'verification_status'
            ).annotate(
                area=Sum('area_ha'),
                count=Count('id')
            ),
            'recent_activity': {
                'models_trained': TrainedModel.objects.filter(
                    updated_at__gte=thirty_days_ago
                ).count(),
                'hotspots_verified': DeforestationHotspot.objects.filter(
                    verification_status__isnull=False,
                    created_at__gte=thirty_days_ago
                ).count(),
                'new_projects': real_projects.filter(
                    created_at__gte=thirty_days_ago
                ).count(),
            }
        }
        
        return Response(stats)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
def get_random_points_within_collection(request, collection_id):
    """
    Generate multiple sets of random points within quads for a given collection.
    
    Parameters
    ----------
    collection_id : str
        The collection ID to generate points for
    count : int, optional
        Number of sets of points to generate (default: 2)

        
    Returns
    -------
    JSON response containing:
        - points: List of points with quad_id, cog_url, x, y coordinates
        - metadata: Information about the points generated
    """

    # Get count parameter from query params, default to 2
    count = int(request.query_params.get('count', 2))
    
    try:
        # Initialize the extractor with default band indexes
        extractor = TitilerExtractor(
            collection=collection_id,
            band_indexes=[1, 2, 3, 4],
            db_host="remote"
        )

        # Load boundary geometry in WGS84 for spatial filtering
        boundary_polygon_wgs84 = _load_boundary_polygon_wgs84()
        if not boundary_polygon_wgs84:
            logger.warning("Could not load boundary polygon, using all COGs in collection")
            cog_urls = list(extractor.get_all_cog_urls(collection_id))
        else:
            # Get only COG URLs that intersect with western Ecuador boundary
            cog_urls = list(extractor.get_cog_urls(boundary_polygon_wgs84, collection_id))
        
        num_quads = len(cog_urls)
        print(f"Found {len(cog_urls)} COGs intersecting with western Ecuador boundary")
        
        # Generate all points for each quad in a single pass
        all_points = []

        for cog_url in cog_urls:
            # Generate random points for this COG (already spatially filtered)
            raw_points = extractor.random_points_in_quad(
                cog_url,
                count,
                rng=random.Random(42),
            )

            # Convert Point objects to serializable format
            for pt in raw_points:
                all_points.append(
                    {
                        "quad_id": pt["quad_id"],
                        "x": pt["x"],
                        "y": pt["y"],
                        "cog_url": cog_url,
                    }
                )
        
        # Randomize the order of all points
        random.seed(42)
        random.shuffle(all_points)
        
        # Prepare response
        response = {
            "points": all_points,
            "metadata": {
                "collection_id": collection_id,
                "total_points": len(all_points),
                "sets_generated": count,
                "points_per_set": num_quads,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        return Response(response, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating random points: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def aoi_summary(request):
    """Compute forest / non-forest summary stats for a user-provided AOI.

    Payload example:
        {
            "aoi": { ... GeoJSON Polygon/Multipolygon ... }
        }

    Returns a JSON object with keys: forest_px, nonforest_px, missing_px,
    pct_forest, pct_missing, forest_ha, nonforest_ha.
    """

    try:
        logger.info("Starting AOI summary computation")
        
        aoi_geojson = request.data.get('aoi')
        if not aoi_geojson:
            logger.warning("Missing 'aoi' field in request")
            return Response({"error": "'aoi' field is required"}, status=status.HTTP_400_BAD_REQUEST)

        titiler_url = os.environ.get("TITILER_URL")
        if not titiler_url:
            logger.error("TITILER_URL environment variable not set")
            raise ValueError("TITILER_URL environment variable is not set")

        # Collection ID comes from client, fallback to first allowed entry
        allowed_collections = get_allowed_datasets()
        collection_id = request.data.get("collection_id") or allowed_collections[0]

        if collection_id not in allowed_collections:
            logger.warning(f"Invalid collection_id received: {collection_id}")
            return Response({"error": "Invalid collection_id"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Using collection ID: {collection_id}")

        logger.info("Computing summary statistics")
        stats_df = AOISummaryStats(collection_id, "remote").summary(aoi_geojson)

        # Convert single-row dataframe to plain dict
        stats_dict = stats_df.iloc[0].to_dict()
        logger.info("Successfully computed summary statistics")

        return Response(stats_dict, status=status.HTTP_200_OK)

    except Exception as exc:
        logger.error(f"AOI summary computation failed: {exc}")
        capture_exception(exc)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([AllowAny])
def get_western_ecuador_stats(request):
    """Get cached summary statistics for western Ecuador boundary polygon by collection."""
    from .services.western_ecuador_stats import get_western_ecuador_stats as get_stats
    
    try:
        collection_id = request.query_params.get('collection_id')
        if not collection_id:
            return Response({"error": "collection_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        allowed_collections = get_allowed_datasets()
        if collection_id not in allowed_collections:
            return Response({"error": "Invalid collection_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get stats using the service
        stats_dict = get_stats(collection_id)
        
        return Response(stats_dict, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.error(f"Failed to get western Ecuador stats: {exc}")
        capture_exception(exc)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)