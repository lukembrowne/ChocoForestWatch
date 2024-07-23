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
import { storeToRefs } from 'pinia';
import { fromUrl } from 'geotiff';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';
import LayerSwitcher from 'ol-layerswitcher';
import 'ol-layerswitcher/dist/ol-layerswitcher.css';




export const useMapStore = defineStore('map', () => {
  // State
  const aoi = ref(null);
  const map = ref(null);
  const mapInitialized = ref(false);
  const isLoading = ref(false);
  const isDrawing = ref(false);
  const aoiLayer = ref(null);
  const drawnPolygons = ref([])
  const selectedPolygon = ref(null);
  const predictionLayer = ref(null);
  
  // Internal state
  const projectStore = useProjectStore();
  const drawiwng = ref(false);
  const vectorLayer = ref(null);
  const drawInteraction = ref(null);
  const modifyInteraction = ref(null);
  const selectInteraction = ref(null);
  const selectedClass = ref('forest');
  const trainingPolygonsLayer = ref(null);
  
  // Actions
  const initMap = (target) => {
    map.value = new Map({
      target: target,
      layers: [
        new TileLayer({
          source: new OSM(),
          name: 'baseMap',
          visible: true
        })
      ],
      view: new View({
        center: fromLonLat([-79.81822466589962, 0.460628082970743]),
        zoom: 12
      })
    });

    // Add LayerSwitcher
    const layerSwitcher = new LayerSwitcher({
      reverse: true,
      tipLabel: 'Legend',
      groupSelectStyle: 'group',
      startActive: true,
    });
    map.value.addControl(layerSwitcher);

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
      title: "Area of Interest",
      visible: true,
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

    const newLayer = new TileLayer({
      source: newSource,
      title: `Planet Basemap ${date}`,
      type: 'base',
      visible: true
    });

    // Remove old base layers
    map.value.getLayers().getArray()
      .filter(layer => layer.get('type') === 'base')
      .forEach(layer => map.value.removeLayer(layer));

    // Add the new layer
    map.value.addLayer(newLayer);

    isLoading.value = false;
  };



  const displayPrediction = async (predictionFilePath) => {
    console.log('Displaying prediction:', predictionFilePath);
    try {
      const url = `http://127.0.0.1:5000/${predictionFilePath}`;
      const tiff = await fromUrl(url);
      const image = await tiff.getImage();
      const width = image.getWidth();
      const height = image.getHeight();
      const bbox = image.getBoundingBox();

      const rasterData = await image.readRasters();

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d');

      const imageData = context.createImageData(width, height);
      const data = imageData.data;

      for (let i = 0; i < width * height; i++) {
        const value = rasterData[0][i];
        const color = value === 0 ? [255, 255, 0, 255] : [0, 128, 0, 255]; // Yellow for non-forest, green for forest
        data[i * 4] = color[0];
        data[i * 4 + 1] = color[1];
        data[i * 4 + 2] = color[2];
        data[i * 4 + 3] = color[3];
      }
      context.putImageData(imageData, 0, 0);

      const imageUrl = canvas.toDataURL();
      const extent = bbox;

      if (predictionLayer.value) {
        map.value.removeLayer(predictionLayer.value);
      }

      predictionLayer.value = new ImageLayer({
        source: new ImageStatic({
          url: imageUrl,
          imageExtent: extent,
        }),
        title: 'Prediction Layer',
        visible: true,
        zIndex: 1,
        opacity: 0.7
      });
  

      map.value.addLayer(predictionLayer.value);
    } catch (error) {
      console.error('Error displaying prediction:', error);
      error.value = 'Failed to display prediction: ' + error.message;
    }
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
        selectedPolygon.value = event.selected[0];

      } else {
        selectedPolygon.value = null;
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
          drawnPolygons.value[index] = updatedPolygon;
        }
      });
    });

    map.value.addInteraction(selectInteraction.value);
    map.value.addInteraction(modifyInteraction.value);
  };

  const toggleDrawing = () => {
    if (drawing.value) {
      stopDrawing();
    } else {
      startDrawing();
    }
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
      feature.set('classLabel', selectedClass.value);
      feature.setId(Date.now().toString()); // Generate a unique ID
      const newPolygon = new GeoJSON().writeFeatureObject(feature, {
        dataProjection: 'EPSG:3857',
        featureProjection: 'EPSG:3857'
      });
      drawnPolygons.value.push(newPolygon);
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
      drawnPolygons.value = drawnPolygons.value.filter(p => p.id !== index);
    }
  };

  const clearDrawnPolygons = () => {
    if (vectorLayer.value) {
      vectorLayer.value.getSource().clear();
    }
    drawnPolygons.value = [];
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
    selectedClass.value = label;
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
    const geoJSONFormat = new GeoJSON();
    const features = polygonsData.features.map(feature => {
      const olFeature = geoJSONFormat.readFeature(feature);
      olFeature.setStyle(featureStyleFunction);
      return olFeature;
    });

    if (trainingPolygonsLayer.value) {
      map.value.removeLayer(trainingPolygonsLayer.value);
    }

    const vectorSource = new VectorSource({
      features: features
    });

    trainingPolygonsLayer.value = new VectorLayer({
      source: vectorSource,
      title: 'Training Polygons',
      visible: true
    });

    map.value.addLayer(trainingPolygonsLayer.value);

    drawnPolygons.value = polygonsData.features;
    

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
    selectedClass,
    selectedPolygon,
    drawnPolygons,
    predictionLayer,
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
    toggleDrawing,
    setClassLabel,
    getDrawnPolygonsGeoJSON,
    loadPolygons,
    displayPrediction,
    // Getters
    getMap
  };
});