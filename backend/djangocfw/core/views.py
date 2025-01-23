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
from .services.model_training import ModelTrainingService
from .services.prediction import PredictionService
from loguru import logger
import json
from django.conf import settings
from django.http import JsonResponse
from .services.deforestation import analyze_change, get_deforestation_hotspots
from rest_framework.permissions import IsAuthenticated
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

@api_view(['GET'])
def health_check(request):
    return Response({
        "status": "healthy",
        "timestamp": timezone.now().isoformat()
    })

class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    
    def get_queryset(self):
        # Filter queryset to only return projects owned by the current user
        return Project.objects.filter(owner=self.request.user)
    
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