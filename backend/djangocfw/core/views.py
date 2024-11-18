from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot
from .serializers import (ProjectSerializer, TrainingPolygonSetSerializer, 
                         TrainedModelSerializer, PredictionSerializer, 
                         DeforestationHotspotSerializer)
from .services.model_training import ModelTrainingService
from .services.prediction import PredictionService
from loguru import logger

@api_view(['GET'])
def health_check(request):
    return Response({
        "status": "healthy",
        "timestamp": timezone.now().isoformat()
    })

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

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
        project_id and set_id query parameters in the URL.
        """
        queryset = TrainingPolygonSet.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        set_id = self.request.query_params.get('id', None)

        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        if set_id is not None:
            queryset = queryset.filter(id=set_id)

        return queryset

    @action(detail=True, methods=['put'])
    def excluded(self, request, pk=None):
        training_set = self.get_object()
        excluded = request.data.get('excluded', False)
        training_set.excluded = excluded
        training_set.save()
        return Response({'message': 'Training set excluded status updated successfully'})

class TrainedModelViewSet(viewsets.ModelViewSet):
    queryset = TrainedModel.objects.all()
    serializer_class = TrainedModelSerializer

    def get_queryset(self):
        queryset = TrainedModel.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=False, methods=['post'])
    def train(self, request):
        """Train a new model"""
        try:
            project_id = request.data.get('project_id')
            model_name = request.data.get('model_name')
            model_description = request.data.get('model_description', '')
            training_set_ids = request.data.get('training_set_ids', [])
            model_params = request.data.get('model_parameters', {})

            service = ModelTrainingService(project_id)
            model, metrics = service.train_model(
                model_name,
                model_description,
                training_set_ids,
                model_params
            )

            return Response({
                'model_id': model.id,
                'metrics': metrics
            })

        except Exception as e:
            return Response({'error': str(e)}, status=400)

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