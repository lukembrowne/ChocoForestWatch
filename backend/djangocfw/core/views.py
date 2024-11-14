from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from django.utils import timezone
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot
from .serializers import (ProjectSerializer, TrainingPolygonSetSerializer, 
                         TrainedModelSerializer, PredictionSerializer, 
                         DeforestationHotspotSerializer)

@api_view(['GET'])
def health_check(request):
    return Response({
        "status": "healthy",
        "timestamp": timezone.now().isoformat()
    })

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

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
        queryset = TrainingPolygonSet.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
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

class PredictionViewSet(viewsets.ModelViewSet):
    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer

    def get_queryset(self):
        queryset = Prediction.objects.all()
        project_id = self.request.query_params.get('project_id', None)
        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        return queryset

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