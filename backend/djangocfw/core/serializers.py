from rest_framework import serializers
from .models import Project, TrainingPolygonSet, TrainedModel, Prediction, DeforestationHotspot
from django.contrib.gis.geos import GEOSGeometry

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        extra_kwargs = {
            'name': {'required': False},  # Make name not required for updates
            'description': {'required': False},
            'classes': {'required': False},
            'aoi': {'required': False},
            'aoi_area_ha': {'required': False}
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.aoi:
            data['aoi'] = instance.aoi.json if instance.aoi else None
        return data

    def update(self, instance, validated_data):
        # Handle AOI update specifically
        if 'aoi' in validated_data:
            if isinstance(validated_data['aoi'], dict):
                # If AOI is provided as GeoJSON
                instance.aoi = GEOSGeometry(str(validated_data['aoi']))
            else:
                # If AOI is provided as WKT or other format
                instance.aoi = validated_data['aoi']
            
            # Calculate area if AOI is set
            if instance.aoi:
                # Area calculation in hectares
                instance.aoi_area_ha = instance.aoi.area / 10000

        # Update other fields
        for attr, value in validated_data.items():
            if attr != 'aoi':  # Skip AOI as we handled it above
                setattr(instance, attr, value)
        
        instance.save()
        return instance

class TrainingPolygonSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingPolygonSet
        fields = '__all__'

class TrainedModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainedModel
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': instance.id,
            'name': instance.name,
            'project_id': instance.project_id,
            'training_set_ids': instance.training_set_ids,
            'accuracy': instance.accuracy,
            'class_metrics': instance.class_metrics,
            'class_names': instance.class_names,
            'confusion_matrix': instance.confusion_matrix,
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
            'model_parameters': instance.model_parameters
        }

class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = '__all__'

class DeforestationHotspotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeforestationHotspot
        fields = '__all__'

# Add other serializers...