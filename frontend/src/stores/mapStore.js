import { defineStore } from 'pinia';
import api from 'src/services/api';
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'
import { Map, View } from 'ol'
import { fromLonLat } from 'ol/proj';
import 'ol/ol.css';
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import { Style, Fill, Stroke } from 'ol/style'
import XYZ from 'ol/source/XYZ';
import { useProjectStore } from './projectStore';

import { ref, watch, computed } from 'vue';
import { Draw, Modify, Select } from 'ol/interaction';
import { click } from 'ol/events/condition';
import { useTrainingStore } from '../stores/trainingStore';
import { storeToRefs } from 'pinia';


export const useMapStore = defineStore('map', () => {
  // State
  const aoi = ref(null);
  const map = ref(null);
  const mapInitialized = ref(false);
  const isLoading = ref(false);
  const isDrawing = ref(false);
  const aoiLayer = ref(null);


  // Internal state
  const projectStore = useProjectStore();
  const trainingStore = useTrainingStore();
  const drawing = ref(false);
  const vectorLayer = ref(null);
  const drawInteraction = ref(null);
  const modifyInteraction = ref(null);
  const selectInteraction = ref(null);
  const currentClassLabel = ref('forest');
  const drawnPolygons = computed(() => trainingStore.drawnPolygons);
  const { selectedPolygon } = storeToRefs(trainingStore);



  // Actions
  const initMap = (target) => {
    map.value = new Map({
      target: target,
      layers: [
        new TileLayer({
          source: new OSM(),
          name: 'baseMap'
        })
      ],
      view: new View({
        center: fromLonLat([-79.81822466589962, 0.460628082970743]),
        zoom: 12
      })
    });

    initVectorLayer();
    initInteractions();

    console.log('Map initialized in MapStore...');
    mapInitialized.value = true;
  };

  const setAOI = (geometry) => {
    aoi.value = geometry;
  };

  const setProjectAOI = async (aoiGeojson) => {
    if (!projectStore.currentProject) {
      throw new Error('No project selected');
    }
    try {
      const response = await api.setProjectAOI(projectStore.currentProject.id, aoiGeojson);
      projectStore.currentProject.aoi = response.data.aoi;
      return response.data;
    } catch (error) {
      console.error('Error setting project AOI:', error);
      throw error;
    }
  };

  const displayAOI = (aoiGeojson) => {
    if (!map.value) return;

    // Remove existing AOI layer if it exists
    if (aoiLayer.value) {
      map.value.removeLayer(aoiLayer.value);
    }

    // Create new AOI layer
    const format = new GeoJSON();
    const feature = format.readFeature(aoiGeojson);
    const vectorSource = new VectorSource({
      features: [feature]
    });
    aoiLayer.value = new VectorLayer({
      source: vectorSource,
      style: new Style({
        fill: new Fill({
          color: 'rgba(255, 255, 255, 0.2)'
        }),
        stroke: new Stroke({
          color: '#000000',
          width: 2
        })
      })
    });

    // Add new AOI layer to map
    map.value.addLayer(aoiLayer.value);

    // Zoom to AOI
    map.value.getView().fit(vectorSource.getExtent(), { padding: [50, 50, 50, 50] });
  };

  const clearAOI = () => {
    if (aoiLayer.value) {
      map.value.removeLayer(aoiLayer.value);
      aoiLayer.value = null;
    }
  };

  const updateBasemap = (date) => {
    isLoading.value = true;
    const apiKey = process.env.VUE_APP_PLANET_API_KEY;
    if (!apiKey) {
      console.error('API key is not defined. Please check your .env file.');
      return;
    }

    console.log("Updating basemap for date: ", date);
    const newSource = new XYZ({
      url: `https://tiles{0-3}.planet.com/basemaps/v1/planet-tiles/planet_medres_normalized_analytic_${date}_mosaic/gmap/{z}/{x}/{y}.png?api_key=${apiKey}`,
    });

    newSource.on('tileloaderror', () => {
      console.error('basemap-error', `Failed to load basemap for date: ${date}`);
      clearLoading();
    });

    // Find the base layer and set the new source
    map.value.getLayers().forEach(layer => {
      if (layer.get('name') === 'baseMap') {
        console.log("Setting source for updated basemap...");
        layer.setSource(newSource);
      }
    });

    isLoading.value = false;
  };

  const clearLoading = () => {
    isLoading.value = false;
  };

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

    console.log("Start drawing from within MapStore...");
    if (!map.value || !vectorLayer.value) return;

    isDrawing.value = true;
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
    console.log("Stopping drawing from within mapStore")
    if (!map.value || !drawInteraction.value) return;

    map.value.removeInteraction(drawInteraction.value);
    isDrawing.value = false;
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
          dataProjection: 'EPSG:3857',
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
    console.log(polygonsData);
    const geoJSONFormat = new GeoJSON();
    polygonsData.features.forEach(feature => {
      const olFeature = geoJSONFormat.readFeature(feature);
      vectorLayer.value.getSource().addFeature(olFeature);
    });
    trainingStore.setDrawnPolygons(polygonsData.features);
  };



  // Getters
  const getMap = computed(() => map.value);

  return {
    // State
    aoi,
    map,
    mapInitialized,
    isLoading,
    isDrawing,
    aoiLayer,
    // Actions
    initMap,
    setAOI,
    setProjectAOI,
    displayAOI,
    clearAOI,
    updateBasemap,
    startDrawing,
    stopDrawing,
    clearDrawnPolygons,
    deletePolygon,
    // Getters
    getMap
  };
});