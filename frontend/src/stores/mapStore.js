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
import { DragPan, DragZoom } from 'ol/interaction';
import { click } from 'ol/events/condition';
import { fromUrl } from 'geotiff';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';


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
  const trainingPolygonsLayer = ref(null);
  const layers = ref([]);
  const selectedBasemapDate = ref(null);


  // Internal state
  const projectStore = useProjectStore();
  const drawing = ref(false);
  const modifyInteraction = ref(null);
  const selectInteraction = ref(null);
  const selectedClass = ref('Forest');
  const interactionMode = ref(null); // 'draw', 'pan', or 'zoom'
  const dragPanInteraction = ref(null);
  const dragZoomInInteraction = ref(null);
  const dragZoomOutInteraction = ref(null);
  const drawInteraction = ref(null);

  // New computed property for visual indicator
  const modeIndicator = computed(() => {
    switch (interactionMode.value) {
      case 'draw':
        return { icon: 'edit', color: 'primary', label: 'Draw' };
      case 'pan':
        return { icon: 'pan_tool', color: 'secondary', label: 'Pan' };
      case 'zoom_in':
        return { icon: 'crop_free', color: 'accent', label: 'Zoom Box' }
      case 'zoom_out':
        return { icon: 'crop_free', color: 'accent', label: 'Zoom Box' }
      default:
        return { icon: 'help', color: 'grey', label: 'Unknown' };
    }
  });

  // Actions
  const initMap = (target) => {
    map.value = new Map({
      target: target,
      layers: [
        new TileLayer({
          source: new OSM(),
          name: 'baseMap',
          title: 'OpenStreetMap',
          visible: true,
          id: 'osm'
        })
      ],
      view: new View({
        center: fromLonLat([-79.81822466589962, 0.460628082970743]),
        zoom: 12
      })
    });

    initTrainingLayer();
    initInteractions();

    // Initialize layers
    updateLayers();

    // Watch for changes in the map's layers
    map.value.getLayers().on(['add', 'remove'], updateLayers);

    console.log('Map initialized in MapStore...');
    mapInitialized.value = true;
  };

  const setAOI = (geometry) => {
    aoi.value = geometry;
  };

  const getLayers = () => {
    return map.value ? map.value.getLayers().getArray() : [];
  };

  const addLayer = (layer) => {
    if (map.value) {
      map.value.addLayer(layer);
    }
  };

  const updateLayers = () => {
    if (map.value) {
      layers.value = map.value.getLayers().getArray().map(layer => ({
        id: layer.get('id'),
        title: layer.get('title'),
        visible: layer.getVisible(),
        layer: layer
      }));
    }
  };

  const removeLayer = (layerId) => {
    if (map.value) {
      const layerToRemove = map.value.getLayers().getArray().find(layer => layer.get('id') === layerId);
      if (layerToRemove) {
        map.value.removeLayer(layerToRemove);
        // updateLayers will be called automatically due to the event listener
      }
    }
  };

  const toggleLayerVisibility = (layerId) => {
    const layer = layers.value.find(l => l.id === layerId);
    if (layer) {
      layer.layer.setVisible(!layer.layer.getVisible());
      updateLayers();
    }
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

    console.log("Displaying AOI from within MapStore...");

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
      id: 'area-of-interest',
      zIndex: 100,
      style: new Style({
        fill: new Fill({
          color: 'rgba(255, 255, 255, 0)'
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

  const setSelectedBasemapDate = (date) => {
    selectedBasemapDate.value = date;
    updateBasemap(date);
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
      visible: true,
      id: `planet-basemap-${date}`,
    });

    // Remove old base layers
    map.value.getLayers().getArray()
      .filter(layer => layer.get('id').startsWith('planet-basemap-'))
      .forEach(layer => map.value.removeLayer(layer));

    // Add the new layer
    map.value.addLayer(newLayer);

    selectedBasemapDate.value = date;

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

      const project = projectStore.currentProject;
      const classColors = project.classes.reduce((acc, cls) => {
        acc[cls.name] = cls.color;
        return acc;
      }, {});

      for (let i = 0; i < width * height; i++) {
        const value = rasterData[0][i];
        const color = classColors[project.classes[value].name];
        const rgb = hexToRgb(color);
        data[i * 4] = rgb.r;
        data[i * 4 + 1] = rgb.g;
        data[i * 4 + 2] = rgb.b;
        data[i * 4 + 3] = 255;
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
        id: 'prediction-layer',
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

  // Helper function to convert hex color to RGB
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  };


  const initTrainingLayer = () => {
    if (!map.value) return;

    trainingPolygonsLayer.value = new VectorLayer({
      source: new VectorSource(),
      style: featureStyleFunction,
      zIndex: 100,
      title: 'Training Polygons',
      id: 'training-polygons'
    });
    map.value.addLayer(trainingPolygonsLayer.value);

    // Load existing polygons from store
    drawnPolygons.value.forEach(polygon => {
      const feature = new GeoJSON().readFeature(polygon, {
        featureProjection: 'EPSG:3857'
      });
      trainingPolygonsLayer.value.getSource().addFeature(feature);
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
      updateTrainingLayerStyle();
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
    if (!map.value || !trainingPolygonsLayer.value) return;

    isDrawing.value = true;
    drawInteraction.value = new Draw({
      source: trainingPolygonsLayer.value.getSource(),
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
      updateTrainingLayerStyle();
      console.log("Drawn polygons: ", drawnPolygons.value)
    });
    map.value.addInteraction(drawInteraction.value);
  };

  const stopDrawing = () => {
    if (!map.value || !drawInteraction.value) return;

    map.value.removeInteraction(drawInteraction.value);
    isDrawing.value = false;
  };

  const deletePolygon = (index) => {
    // console.log("Deleting polygon with index: ", index);
    // console.log("Drawn polygons before deletion: ", drawnPolygons.value);

    if (index >= 0 && index < drawnPolygons.value.length) {
      const feature = trainingPolygonsLayer.value.getSource().getFeatures()[index];
      trainingPolygonsLayer.value.getSource().removeFeature(feature);

      // Use splice to ensure reactivity
      drawnPolygons.value.splice(index, 1);
    }
    // console.log("Drawn polygons after deletion: ", drawnPolygons.value);
  };

  const clearDrawnPolygons = () => {
    if (trainingPolygonsLayer.value) {
      trainingPolygonsLayer.value.getSource().clear();
    }
    drawnPolygons.value = [];
  };

  const updateTrainingLayerStyle = () => {
    if (trainingPolygonsLayer.value) {
      trainingPolygonsLayer.value.setStyle(featureStyleFunction);
      trainingPolygonsLayer.value.changed();
    }
  };

  const featureStyleFunction = (feature) => {
    const projectStore = useProjectStore();
    const classLabel = feature.get('classLabel');
    const isSelected = feature === selectedPolygon.value;

    // Find the class in the project classes
    const classObj = projectStore.currentProject?.classes.find(cls => cls.name === classLabel);

    let color, strokeColor, strokeWidth;

    if (isSelected) {
      color = classObj ? `${classObj.color}80` : 'rgba(255, 255, 255, 0.5)';  // 80 is for 50% opacity
      strokeColor = '#FF4136';
      strokeWidth = 3;
    } else {
      color = classObj ? `${classObj.color}4D` : 'rgba(128, 128, 128, 0.3)';  // 4D is for 30% opacity
      strokeColor = classObj ? classObj.color : '#808080';
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
    if (!trainingPolygonsLayer.value) return null;

    const features = trainingPolygonsLayer.value.getSource().getFeatures();
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
      visible: true,
      zIndex: 1000,
      id: 'training-polygons',
    });

    map.value.addLayer(trainingPolygonsLayer.value);

    drawnPolygons.value = polygonsData.features;

  };

  // Method to set interaction mode
  const setInteractionMode = (mode) => {
    if (mode === interactionMode.value) return;

    // Remove all interactions
    stopDrawing();
    if (dragPanInteraction.value) map.value.removeInteraction(dragPanInteraction.value);
    if (dragZoomInInteraction.value) map.value.removeInteraction(dragZoomInInteraction.value);
    if (dragZoomOutInteraction.value) map.value.removeInteraction(dragZoomOutInteraction.value);
    if (drawInteraction.value) map.value.removeInteraction(drawInteraction.value);

    // Add interaction based on mode
    switch (mode) {
      case 'pan':
        console.log("Setting pan mode");
        dragPanInteraction.value = new DragPan();
        map.value.addInteraction(dragPanInteraction.value);
        break;
      case 'zoom_in':
        console.log("Setting zoom in mode");
        dragZoomInInteraction.value = new DragZoom({
          out: false,
          condition: () => true,
        });
        map.value.addInteraction(dragZoomInInteraction.value);
        break;
      case 'zoom_out':
        console.log("Setting zoom out mode");
        dragZoomOutInteraction.value = new DragZoom({
          out: true,
          condition: () => true,
        });
        map.value.addInteraction(dragZoomOutInteraction.value);
        break;
      case 'draw':
        console.log("Setting draw mode");
        startDrawing();
        break;
    }

    interactionMode.value = mode;
  };

  // Undo last drawn point or polygon
  const undoLastDraw = () => {

    // Remove the last drawn polygon
    if (drawnPolygons.value.length > 0) {
      const lastPolygon = drawnPolygons.value.pop();

      // Remove the corresponding feature from the layer
      const features = trainingPolygonsLayer.value.getSource().getFeatures();
      const lastFeature = features.find(feature => feature.getId() === lastPolygon.id);
      if (lastFeature) {
        trainingPolygonsLayer.value.getSource().removeFeature(lastFeature);
      }

      console.log("Removed last drawn polygon");
    } else {
      console.log("No polygons to remove");
    }

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
    layers,
    interactionMode,
    modeIndicator,
    selectedBasemapDate,
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
    getLayers,
    addLayer,
    removeLayer,
    toggleLayerVisibility,
    updateTrainingLayerStyle,
    setInteractionMode,
    undoLastDraw,
    setSelectedBasemapDate,
    // Getters
    getMap
  };
});