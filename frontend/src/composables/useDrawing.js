import { ref, watch, computed } from 'vue';
import { Draw, Modify, Select } from 'ol/interaction';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { click } from 'ol/events/condition';
import { Style, Fill, Stroke } from 'ol/style';
import GeoJSON from 'ol/format/GeoJSON';
import { useTrainingStore } from '../stores/trainingStore';
import { storeToRefs } from 'pinia';

export function useDrawing(baseMapRef) {
  const trainingStore = useTrainingStore();
  const { selectedPolygon } = storeToRefs(trainingStore);

  const drawing = ref(false);
  const vectorLayer = ref(null);
  const drawInteraction = ref(null);
  const modifyInteraction = ref(null);
  const selectInteraction = ref(null);
  const currentClassLabel = ref('forest');

  const map = computed(() => baseMapRef.value?.map);
  const drawnPolygons = computed(() => trainingStore.drawnPolygons);


  const initVectorLayer = () => {
    if (!map.value) return;
    
    vectorLayer.value = new VectorLayer({
      source: new VectorSource(),
      style: featureStyleFunction,
      zIndex: 100
    });
    map.value.addLayer(vectorLayer.value);

    // Load existing polygons from store
    drawnPolygons.value.forEach(polygon => {
      const feature = new GeoJSON().readFeature(polygon, {
        featureProjection: 'EPSG:3857'
      });
      vectorLayer.value.getSource().addFeature(feature);
    });
  };

  const initInteractions = () => {
    if (!map.value) return;

    selectInteraction.value = new Select({
      condition: click,
      style: featureStyleFunction
    });

    selectInteraction.value.on('select', (event) => {
      if (event.selected.length > 0) {
        trainingStore.setSelectedPolygon(event.selected[0]);
      } else {
        trainingStore.setSelectedPolygon(null);
      }
      updateVectorLayerStyle();
    });

    modifyInteraction.value = new Modify({
      features: selectInteraction.value.getFeatures()
    });

    modifyInteraction.value.on('modifyend', (event) => {
      const modifiedFeatures = event.features.getArray();
      modifiedFeatures.forEach(feature => {
        const index = drawnPolygons.value.findIndex(p => p.id === feature.getId());
        if (index !== -1) {
          const updatedPolygon = new GeoJSON().writeFeatureObject(feature, {
            dataProjection: 'EPSG:3857',
            featureProjection: 'EPSG:3857'
          });
          trainingStore.updatePolygon(index, updatedPolygon);
        }
      });
    });

    map.value.addInteraction(selectInteraction.value);
    map.value.addInteraction(modifyInteraction.value);
  };

  const startDrawing = () => {
    if (!map.value || !vectorLayer.value) return;

    drawing.value = true;
    drawInteraction.value = new Draw({
      source: vectorLayer.value.getSource(),
      type: 'Polygon',
      freehand: true
    });

    drawInteraction.value.on('drawend', (event) => {
      const feature = event.feature;
      feature.set('classLabel', currentClassLabel.value);
      feature.setId(Date.now().toString()); // Generate a unique ID
      const newPolygon = new GeoJSON().writeFeatureObject(feature, {
        dataProjection: 'EPSG:3857',
        featureProjection: 'EPSG:3857'
      });
      trainingStore.addPolygon(newPolygon);
      updateVectorLayerStyle();
    });

    map.value.addInteraction(drawInteraction.value);
  };

  const stopDrawing = () => {
    if (!map.value || !drawInteraction.value) return;

    map.value.removeInteraction(drawInteraction.value);
    drawing.value = false;
  };

  const addPolygon = (feature) => {
    const geoJSONFormat = new GeoJSON();
    const geoJSONFeature = geoJSONFormat.writeFeatureObject(feature, {
      dataProjection: 'EPSG:3857',
      featureProjection: 'EPSG:3857'
    });
    trainingStore.addPolygon(geoJSONFeature);
  };

  const deletePolygon = (index) => {
    if (index >= 0 && index < drawnPolygons.value.length) {
      const feature = vectorLayer.value.getSource().getFeatures()[index];
      vectorLayer.value.getSource().removeFeature(feature);
      trainingStore.removePolygon(index);
    }
  };

  const clearDrawnPolygons = () => {
    if (vectorLayer.value) {
      vectorLayer.value.getSource().clear();
    }
    trainingStore.clearPolygons();
  };

  const updateVectorLayerStyle = () => {
    if (vectorLayer.value) {
      vectorLayer.value.setStyle(featureStyleFunction);
      vectorLayer.value.changed();
    }
  };

  const featureStyleFunction = (feature) => {
    const classLabel = feature.get('classLabel');
    const isSelected = feature === selectedPolygon.value;

    let color, strokeColor, strokeWidth;

    if (isSelected) {
      color = classLabel === 'forest' ? 'rgba(0, 255, 0, 0.5)' : 'rgba(255, 255, 0, 0.5)';
      strokeColor = '#FF4136';
      strokeWidth = 3;
    } else {
      color = classLabel === 'forest' ? 'rgba(0, 128, 0, 0.5)' : 'rgba(255, 255, 0, 0.3)';
      strokeColor = classLabel === 'forest' ? '#008000' : '#FFFF00';
      strokeWidth = 2;
    }

    return new Style({
      fill: new Fill({ color }),
      stroke: new Stroke({ color: strokeColor, width: strokeWidth }),
    });
  };

  const setClassLabel = (label) => {
    currentClassLabel.value = label;
  };

  const getDrawnPolygonsGeoJSON = () => {
    if (!vectorLayer.value) return null;

    const features = vectorLayer.value.getSource().getFeatures();
    const geoJSONFormat = new GeoJSON();
    const featureCollection = {
      type: 'FeatureCollection',
      features: features.map(feature => {
        const geoJSONFeature = geoJSONFormat.writeFeatureObject(feature, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        });
        geoJSONFeature.properties = {
          classLabel: feature.get('classLabel')
        };
        return geoJSONFeature;
      })
    };

    return featureCollection;
  };

  const loadPolygons = (polygonsData) => {
    clearDrawnPolygons();
    const geoJSONFormat = new GeoJSON();
    polygonsData.features.forEach(feature => {
      const olFeature = geoJSONFormat.readFeature(feature, {
        featureProjection: 'EPSG:3857'
      });
      vectorLayer.value.getSource().addFeature(olFeature);
    });
    trainingStore.setDrawnPolygons(polygonsData.features);
  };


  watch(map, (newMap) => {
    if (newMap) {
      initVectorLayer();
      initInteractions();
    }
  });

  return {
    drawing,
    vectorLayer,
    startDrawing,
    stopDrawing,
    deletePolygon,
    setClassLabel,
    updateVectorLayerStyle,
    clearDrawnPolygons,
    getDrawnPolygonsGeoJSON,
    loadPolygons
  };
}