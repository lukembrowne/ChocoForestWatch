import { defineStore } from 'pinia';
import api from 'src/services/api';
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'
import { Map, View } from 'ol'
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
import { getBasemapDateOptions } from 'src/utils/dateUtils';
import { Feature } from 'ol';
import { Polygon } from 'ol/geom';
import { fromLonLat, toLonLat } from 'ol/proj';
import { transformExtent } from 'ol/proj'



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
  const polygonSize = ref(100); // Default size in meters


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
  const availableDates = ref([]);

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

  const updateLayerOpacity = (layerId, opacity) => {
    if (map.value) {
      const layer = map.value.getLayers().getArray().find(layer => layer.get('id') === layerId);
      if (layer) {
        layer.setOpacity(opacity);
        // Update the layers array to reflect the new opacity
        const layerIndex = layers.value.findIndex(l => l.id === layerId);
        if (layerIndex !== -1) {
          layers.value[layerIndex].opacity = opacity;
        }
      }
    }
  };

  const updateLayers = () => {
    if (map.value) {
      layers.value = map.value.getLayers().getArray().map(layer => ({
        id: layer.get('id'),
        title: layer.get('title'),
        visible: layer.getVisible(),
        opacity: layer.getOpacity(),
        showOpacity: false,
        layer: layer
      }));
    }
  };

  const removeLayer = (layerId) => {
    if (map.value) {
      const layerToRemove = map.value.getLayers().getArray().find(layer => layer.get('id') === layerId);
      if (layerToRemove) {
        map.value.removeLayer(layerToRemove);
        updateLayers();
      }
    }
  };

  const clearPredictionLayers = () => {
    if (map.value) {
      const layersToRemove = map.value.getLayers().getArray().filter(layer => {
        const layerId = layer.get('id');
        return layerId && layerId.startsWith('prediction-');
      });
      layersToRemove.forEach(layer => map.value.removeLayer(layer));
      updateLayers();
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
      console.log("AOI Geojson: ", aoiGeojson)
      // Read the geometry directly from the GeoJSON object
      const geojsonFormat = new GeoJSON();
      const geometry = geojsonFormat.readGeometry(aoiGeojson['geometry']);
      const extent = geometry.getExtent()
      const aoiExtentLatLon = transformExtent(extent, 'EPSG:3857', 'EPSG:4326')

      console.log("AOI extent in lat lon: ", aoiExtentLatLon)

      const response = await api.setProjectAOI(projectStore.currentProject.id, aoiGeojson, aoiExtentLatLon, availableDates.value);
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
      }),
      selectable: false,
      interactive: false
    });

    // Add new AOI layer to map
    map.value.addLayer(aoiLayer.value);

    // Zoom to AOI
    map.value.getView().fit(vectorSource.getExtent(), { padding: [50, 50, 50, 50] });

    // Reinitialize interactions so that the AOI layer is not selectable
    initInteractions();

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



  const displayPrediction = async (predictionFilePath, layerId, layerName, mode = 'prediction') => {
    console.log(`Displaying ${mode}:`, predictionFilePath);
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

      let colorMapping;
      if (mode === 'prediction') {
        const project = projectStore.currentProject;
        colorMapping = project.classes.reduce((acc, cls) => {
          acc[cls.name] = cls.color;
          return acc;
        }, {});
      } else if (mode === 'deforestation') {
        colorMapping = {
          0: '#00FF00',  // Green for no deforestation
          1: '#FF0000',  // Red for deforestation
          255: '#808080' // Grey for no data
        };
      }

      for (let i = 0; i < width * height; i++) {
        const value = rasterData[0][i];
        let color;
        if (mode === 'prediction') {
          color = colorMapping[projectStore.currentProject.classes[value].name];
        } else {
          color = colorMapping[value];
        }
        const rgb = hexToRgb(color);
        data[i * 4] = rgb.r;
        data[i * 4 + 1] = rgb.g;
        data[i * 4 + 2] = rgb.b;
        data[i * 4 + 3] = 255;
      }
      context.putImageData(imageData, 0, 0);

      const imageUrl = canvas.toDataURL();
      const extent = bbox;

      const newLayer = new ImageLayer({
        source: new ImageStatic({
          url: imageUrl,
          imageExtent: extent,
        }),
        title: layerName,
        id: layerId,
        visible: true,
        zIndex: 1,
        opacity: 0.7
      });

      map.value.addLayer(newLayer);
      updateLayers();
    } catch (error) {
      console.error(`Error displaying ${mode}:`, error);
      throw new Error(`Failed to display ${mode}: ` + error.message);
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

    // if (!map.value) return;

    // selectInteraction.value = new Select({
    //   condition: click,
    //   style: featureStyleFunction,
    //   layers: (layer) => {
    //     return layer !== aoiLayer.value;
    //   },
    // });

    // console.log("Select interaction: ", selectInteraction.value);


    // selectInteraction.value.on('select', (event) => {
    //   console.log("Selecting polygon from within MapStore...");
    //   if (event.selected.length > 0) {
    //     selectedPolygon.value = event.selected[0];
    //     selectedPolygon.value = event.selected[0];

    //   } else {
    //     selectedPolygon.value = null;
    //   }
    //   updateTrainingLayerStyle();
    // });

    // modifyInteraction.value = new Modify({
    //   features: selectInteraction.value.getFeatures()
    // });

    // modifyInteraction.value.on('modifyend', (event) => {
    //   const modifiedFeatures = event.features.getArray();
    //   modifiedFeatures.forEach(feature => {
    //     const index = drawnPolygons.value.findIndex(p => p.id === feature.getId());
    //     if (index !== -1) {
    //       const updatedPolygon = new GeoJSON().writeFeatureObject(feature, {
    //         dataProjection: 'EPSG:3857',
    //         featureProjection: 'EPSG:3857'
    //       });
    //       drawnPolygons.value[index] = updatedPolygon;
    //     }
    //   });
    // });

    // map.value.addInteraction(selectInteraction.value);
    // map.value.addInteraction(modifyInteraction.value);
  };

  const toggleDrawing = () => {
    if (drawing.value) {
      stopDrawing();
    } else {
      startDrawing();
    }
  };

  // const startDrawing = () => {

  //   console.log("Start drawing from within MapStore...");
  //   if (!map.value || !trainingPolygonsLayer.value) return;

  //   isDrawing.value = true;
  //   drawInteraction.value = new Draw({
  //     source: trainingPolygonsLayer.value.getSource(),
  //     type: 'Polygon',
  //     freehand: true
  //   });

  //   drawInteraction.value.on('drawend', (event) => {
  //     const feature = event.feature;
  //     feature.set('classLabel', selectedClass.value);
  //     feature.setId(Date.now().toString()); // Generate a unique ID

  //     // Explicitly add the feature to the layer's source
  //     trainingPolygonsLayer.value.getSource().addFeature(feature);

  //     const newPolygon = new GeoJSON().writeFeatureObject(feature, {
  //       dataProjection: 'EPSG:3857',
  //       featureProjection: 'EPSG:3857'
  //     });
  //     drawnPolygons.value.push(newPolygon);
  //     updateTrainingLayerStyle();
  //     console.log("Drawn polygons: ", drawnPolygons.value)
  //     console.log("Features from trainingPolygonsLayer: ", trainingPolygonsLayer.value.getSource().getFeatures())
  //   });
  //   map.value.addInteraction(drawInteraction.value);
  // };

  // const stopDrawing = () => {
  //   if (!map.value || !drawInteraction.value) return;

  //   map.value.removeInteraction(drawInteraction.value);
  //   isDrawing.value = false;
  // };

  const setPolygonSize = (size) => {
    polygonSize.value = size;
  };



  const startDrawing = () => {
    console.log("Start drawing from within MapStore...");
    if (!map.value || !trainingPolygonsLayer.value) return;

    isDrawing.value = true;

    // Remove any existing click listener
    if (map.value.clickListener) {
      map.value.un('click', map.value.clickListener);
    }

    map.value.clickListener = (event) => {
      const clickCoordinate = event.coordinate;
      const [x, y] = clickCoordinate;

      // Use polygonSize.value instead of a fixed value
      const halfSize = polygonSize.value / 2;

      const polygonCoordinates = [
        [x - halfSize, y - halfSize],
        [x + halfSize, y - halfSize],
        [x + halfSize, y + halfSize],
        [x - halfSize, y + halfSize],
        [x - halfSize, y - halfSize] // Close the polygon
      ];

      const polygonGeometry = new Polygon([polygonCoordinates]);
      const feature = new Feature({
        geometry: polygonGeometry
      });

      feature.set('classLabel', selectedClass.value);
      feature.setId(Date.now().toString()); // Generate a unique ID

      // Explicitly add the feature to the layer's source
      trainingPolygonsLayer.value.getSource().addFeature(feature);

      const newPolygon = new GeoJSON().writeFeatureObject(feature, {
        featureProjection: 'EPSG:3857'
      });
      drawnPolygons.value.push(newPolygon);
      updateTrainingLayerStyle();
      console.log("Drawn polygons: ", drawnPolygons.value);
      console.log("Features from trainingPolygonsLayer: ", trainingPolygonsLayer.value.getSource().getFeatures());
    };

    map.value.on('click', map.value.clickListener);
  };

  const stopDrawing = () => {
    if (!map.value) return;

    isDrawing.value = false;
    if (map.value.clickListener) {
      map.value.un('click', map.value.clickListener);
      map.value.clickListener = null;
    }
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
      color = classObj ? `${classObj.color}4D` : 'rgba(128, 128, 128, 0.8)';  // 4D is for 30% opacity
      strokeColor = 'rgba(0, 0, 0, 0.8)';
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
    console.log("Features from trainingPolygonsLayer: ", features)

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


  const initializeBasemapDates = async () => {
    availableDates.value = getBasemapDateOptions().map(option => option.value);
    // Set the first date in the available dates array as the selected basemap date
    // if (availableDates.value.length > 0) {
    //   await setSelectedBasemapDate(availableDates.value[0]);
    // }
  };

  const setSelectedBasemapDate = async (date) => {
    selectedBasemapDate.value = date;
    await updateBasemap(date);
    await loadTrainingPolygonsForDate(date);
  };

  const moveToNextDate = async () => {
    const currentIndex = availableDates.value.indexOf(selectedBasemapDate.value);
    if (currentIndex < availableDates.value.length - 1) {
      await setSelectedBasemapDate(availableDates.value[currentIndex + 1]);
    }
  };

  const moveToPreviousDate = async () => {
    const currentIndex = availableDates.value.indexOf(selectedBasemapDate.value);
    if (currentIndex > 0) {
      await setSelectedBasemapDate(availableDates.value[currentIndex - 1]);
    }
  };

  const loadTrainingPolygonsForDate = async (date) => {
    console.log("Loading training polygons for date within MapStore:", date);
    try {
      const response = await api.getTrainingPolygons(projectStore.currentProject.id);
      console.log(response.data)
      const trainingSet = response.data.find(set => set.basemap_date === date);
      if (trainingSet) {
        const polygons = await api.getSpecificTrainingPolygons(projectStore.currentProject.id, trainingSet.id);
        loadPolygons(polygons.data);
      } else {
        clearDrawnPolygons();
      }
    } catch (error) {
      console.error('Error loading training polygons:', error);
      // Handle error (e.g., show notification to user)
    }
  };

  const saveCurrentTrainingPolygons = async () => {
    const projectStore = useProjectStore();
    const polygons = getDrawnPolygonsGeoJSON();
    try {
      // First, check if a training set for this date already exists
      const response = await api.getTrainingPolygons(projectStore.currentProject.id);
      const existingSet = response.data.find(set => set.basemap_date === selectedBasemapDate.value);

      if (existingSet) {
        // Update existing training set
        await api.updateTrainingPolygons({
          project_id: projectStore.currentProject.id,
          id: existingSet.id,
          basemap_date: selectedBasemapDate.value,
          polygons: polygons,
          name: `Training_Set_${selectedBasemapDate.value}`
        });
      } else {
        // Create new training set
        await api.saveTrainingPolygons({
          project_id: projectStore.currentProject.id,
          basemap_date: selectedBasemapDate.value,
          polygons: polygons,
          name: `Training_Set_${selectedBasemapDate.value}`
        });
      }
    } catch (error) {
      console.error('Error saving training polygons:', error);
      // Handle error (e.g., show notification to user)
      throw error; // Rethrow the error so it can be caught in the component
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
    availableDates,
    polygonSize,
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
    clearPredictionLayers,
    updateLayerOpacity,
    initializeBasemapDates,
    moveToNextDate,
    moveToPreviousDate,
    loadTrainingPolygonsForDate,
    saveCurrentTrainingPolygons,
    setPolygonSize,
    // Getters
    getMap
  };
});