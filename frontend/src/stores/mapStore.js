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

import { ref, watch, computed, nextTick } from 'vue';
import { Draw, Modify, Select } from 'ol/interaction';
import { DragPan, DragZoom } from 'ol/interaction';
import { click } from 'ol/events/condition';
import { fromUrl, fromArrayBuffer } from 'geotiff';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';
import { getBasemapDateOptions } from 'src/utils/dateUtils';
import { Feature } from 'ol';
import { Polygon } from 'ol/geom';
import { fromLonLat, toLonLat } from 'ol/proj';
import { transformExtent } from 'ol/proj'
import { useQuasar } from 'quasar';

export const useMapStore = defineStore('map', () => {

  // State
  const aoi = ref(null);
  const map = ref(null);
  const maps = ref({
    primary: null,
    secondary: null
  });
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
  const hasUnsavedChanges = ref(false);
  const selectedFeature = ref(null);
  const selectedFeatureStyle = new Style({
    stroke: new Stroke({
      color: 'yellow',
      width: 3
    }),
    fill: new Fill({
      color: 'rgba(255, 255, 0, 0.1)'
    })
  });
  const sliderValue = ref(0);

  // Internal state
  const projectStore = useProjectStore();
  const drawing = ref(false);
  const modifyInteraction = ref(null);
  const selectInteraction = ref(null);
  const selectedClass = ref('Forest');
  const drawingMode = ref('square'); // 'square' or 'freehand'
  const interactionMode = ref(null); // 'draw', 'pan', or 'zoom'
  const dragPanInteraction = ref(null);
  const dragZoomInInteraction = ref(null);
  const dragZoomOutInteraction = ref(null);
  const drawInteraction = ref(null);
  const availableDates = ref([]);

  const $q = useQuasar();

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
  const initMap = (target, force = false) => {
    if (!map.value || force) {
      map.value = new Map({
        target: target,
        layers: [
          new TileLayer({
            source: new OSM(),
            name: 'baseMap',
            title: 'OpenStreetMap',
            visible: true,
            id: 'osm',
            zIndex: 0
          })
        ],
        view: new View({
          center: fromLonLat([-79.81822466589962, -0.460628082970743]),
          zoom: 8
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
      map.value.setTarget(target)
    }
  };

  function showSingleMap(targetId) {
    initMap()
    // Attach single map
    map.value.setTarget(targetId)
  }

  function hideSingleMap() {
    if (map.value) {
      map.value.setTarget(null)
    }
  }

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

  const updateLayerOpacity = (layerId, opacity, mapId = null) => {
    if (mapId && maps.value[mapId]) {
      // Dual map mode
      const layer = maps.value[mapId].getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) {
        layer.setOpacity(opacity);
      }
    } else if (map.value) {
      // Single map mode
      const layer = map.value.getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) {
        layer.setOpacity(opacity);
      }
    }
    updateLayers();
  };

  const updateLayers = () => {
    if (maps.value.primary || maps.value.secondary) {
      // Dual map mode
      const allLayers = [];

      if (maps.value.primary) {
        const primaryLayers = maps.value.primary.getLayers().getArray()
          .map(layer => ({
            id: layer.get('id'),
            title: layer.get('title'),
            zIndex: layer.getZIndex(),
            visible: layer.getVisible(),
            opacity: layer.getOpacity(),
            showOpacity: false,
            mapId: 'primary'
          }));
        allLayers.push(...primaryLayers);
      }

      if (maps.value.secondary) {
        const secondaryLayers = maps.value.secondary.getLayers().getArray()
          .map(layer => ({
            id: layer.get('id'),
            title: layer.get('title'),
            zIndex: layer.getZIndex(),
            visible: layer.getVisible(),
            opacity: layer.getOpacity(),
            showOpacity: false,
            mapId: 'secondary'
          }));
        allLayers.push(...secondaryLayers);
      }

      layers.value = allLayers.sort((a, b) => b.zIndex - a.zIndex);
    } else if (map.value) {
      // Single map mode - existing behavior
      layers.value = map.value.getLayers().getArray()
        .map(layer => ({
          id: layer.get('id'),
          title: layer.get('title'),
          zIndex: layer.getZIndex(),
          visible: layer.getVisible(),
          opacity: layer.getOpacity(),
          showOpacity: false
        }));
    }
  };

  const removeLayer = (layerId, mapId = null) => {
    if (mapId && maps.value[mapId]) {
      // Dual map mode
      const layer = maps.value[mapId].getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) {
        maps.value[mapId].removeLayer(layer);
      }
    } else if (map.value) {
      // Single map mode
      const layer = map.value.getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) {
        map.value.removeLayer(layer);
      }
    }
    updateLayers();
  };

  const clearPredictionLayers = () => {
    if (map.value) {
      const layersToRemove = map.value.getLayers().getArray().filter(layer => {
        const layerId = layer.get('id');
        return layerId && layerId.startsWith('landcover-');
      });
      layersToRemove.forEach(layer => map.value.removeLayer(layer));
      updateLayers();
    }
  };


  const toggleLayerVisibility = (layerId, mapId = null) => {
    if (mapId && maps.value[mapId]) {
      // Dual map mode
      const layer = maps.value[mapId].getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) {
        layer.setVisible(!layer.getVisible());
      }
    } else if (map.value) {
      // Single map mode
      const layer = map.value.getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) {
        layer.setVisible(!layer.getVisible());
      }
    }
    updateLayers();
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
      console.log("Project AOI set to: ", projectStore.currentProject.aoi)
      return response.data;
    } catch (error) {
      console.error('Error setting project AOI:', error);
      throw error;
    }
  };

  // Add new reusable function to create AOI layer
  const createAOILayer = (aoiGeojson) => {
    const format = new GeoJSON();
    const feature = format.readFeature(aoiGeojson);
    const vectorSource = new VectorSource({
      features: [feature]
    });

    const aoiLayer = new VectorLayer({
      source: vectorSource,
      title: "Area of Interest",
      visible: true,
      id: 'area-of-interest',
      zIndex: 3,
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

    return {
      layer: aoiLayer,
      source: vectorSource
    };
  };

  // Modify existing displayAOI to use the new function
  const displayAOI = (aoiGeojson) => {
    if (!map.value) return;

    // Remove existing AOI layer if it exists
    if (aoiLayer.value) {
      map.value.removeLayer(aoiLayer.value);
    }

    const { layer, source } = createAOILayer(aoiGeojson);
    aoiLayer.value = layer;

    // Add new AOI layer to map
    map.value.getLayers().insertAt(0, aoiLayer.value);

    // Zoom to AOI  
    map.value.getView().fit(source.getExtent(), { padding: [50, 50, 50, 50] });

    // Reinitialize interactions so that the AOI layer is not selectable
    initInteractions();
  };

  const clearAOI = () => {
    if (aoiLayer.value) {
      map.value.removeLayer(aoiLayer.value);
      aoiLayer.value = null;
    }
  };


  // Function to create a Planet Basemap layer for a given date
  const createPlanetBasemap = (date) => {
    // Retrieve the Planet API key from the environment variables
    const apiKey = process.env.VUE_APP_PLANET_API_KEY;
    // Check if the API key is defined
    if (!apiKey) {
      // Log an error if the API key is not defined
      console.error('API key is not defined. Please check your .env file.');
      // Return null if the API key is not defined
      return null;
    }

    // Create a new XYZ source for the Planet Basemap
    const source = new XYZ({
      url: `https://tiles{0-3}.planet.com/basemaps/v1/planet-tiles/planet_medres_normalized_analytic_${date}_mosaic/gmap/{z}/{x}/{y}.png?api_key=${apiKey}`,
    });

    // Return a new TileLayer for the Planet Basemap
    return new TileLayer({
      source: source,
      title: `Planet Basemap ${date}`, // Set the layer title to include the date
      type: 'base', // Set the layer type to 'base'
      visible: true, // Make the layer visible by default
      id: `planet-basemap`, // Set a unique ID for the layer
      zIndex: 1 // Set the layer's z-index to 1
    });
  };
  // Function to update the basemap layer with a new date
  const updateBasemap = (date) => {
    // Create a new Planet Basemap layer for the given date
    const planetBasemap = createPlanetBasemap(date);

    // Find the existing Planet Basemap layer by its ID
    let existingBasemap = map.value.getLayers().getArray().find(layer => layer.get('id') === 'planet-basemap');

    // If an existing layer is found, update it with the new basemap
    if (existingBasemap) {
      console.log("Updating existing planet basemap layer...");
      existingBasemap.setSource(planetBasemap.getSource());
      existingBasemap.set('title', `Planet Basemap ${date}`);
    } else {
      // If no existing layer is found, create a new one and insert it at a specific position
      console.log("Creating new planet basemap layer...");
      map.value.getLayers().insertAt(2, planetBasemap);
    }

    // Update the slider value to match the new basemap date
    const dateIndex = availableDates.value.findIndex(d => d === date);
    if (dateIndex !== -1) {
      updateSliderValue(dateIndex);
    }

    // Update the selected basemap date in the store
    selectedBasemapDate.value = date;
    // Ensure the layer order is updated in the store
    updateLayers();
  };



  // Display predictions or deforesation maps
  const displayPrediction = async (predictionFilePath, layerId, layerName, mode = 'landcover', mapId = null, visible = false) => {
    console.log(`Displaying ${mode} on map:`, mapId);
    console.log('Prediction file path:', predictionFilePath);

    try {
      // Check if predictionFilePath is valid
      if (!predictionFilePath) {
        throw new Error('Invalid prediction file path');
      }

      // const tiff = await fromUrl(predictionFilePath).catch(error => {
      //   console.error('Error loading TIFF:', error);
      //   throw new Error(`Failed to load TIFF file: ${error.message}`);
      // });

      const response = await fetch(predictionFilePath, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to fetch TIFF file: ${response.statusText}`);
      }
      const arrayBuffer = await response.arrayBuffer();
      const tiff = await fromArrayBuffer(arrayBuffer);

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
      const noDataValue = 255;

      if (mode === 'landcover') {
        const project = projectStore.currentProject;
        colorMapping = project.classes.reduce((acc, cls) => {
          acc[cls.name] = cls.color;
          return acc;
        }, {});

        console.log("Color mapping: ", colorMapping);
      } else if (mode === 'deforestation') {
        colorMapping = {
          0: '#00FF00',
          1: '#FF0000',
          [noDataValue]: '#808080'
        };
      }

      for (let i = 0; i < width * height; i++) {
        const value = rasterData[0][i];
        let color;

        if (value === noDataValue) {
          data[i * 4] = 0;
          data[i * 4 + 1] = 0;
          data[i * 4 + 2] = 0;
          data[i * 4 + 3] = 0;
          continue;
        }

        if (mode === 'landcover') {
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
        visible: visible,
        zIndex: 1,
        opacity: 0.7
      });

      // Handle layer addition based on map type
      if (mapId && maps.value[mapId]) {
        // Add to specific dual map
        maps.value[mapId].addLayer(newLayer);
      } else if (map.value) {
        // Add to single map
        map.value.addLayer(newLayer);


        // Get current number of layers
        const numLayers = map.value.getLayers().getArray().length;

        // Reorder layers to make sure the new layer is above the AOI layer
        // This takes the last layer and moves it to the top
        // Need to do numLayers - 1 because of 0 based indexing
        reorderLayers(numLayers - 1, 0) // This also updates the layers
      }
    } catch (error) {
      console.error(`Error displaying ${mode}:`, error);
      console.error('Full error details:', {
        predictionFilePath,
        layerId,
        layerName,
        mode,
        mapId
      });
      throw new Error(`Failed to display ${mode}: ${error.message}`);
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



  // Modified initTrainingLayer function
  const initTrainingLayer = () => {
    if (!map.value) return;

    trainingPolygonsLayer.value = new VectorLayer({
      source: new VectorSource(),
      style: featureStyleFunction,
      title: 'Training Polygons',
      id: 'training-polygons',
      zIndex: 2
    });

    map.value.getLayers().insertAt(0, trainingPolygonsLayer.value);

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

    if (drawingMode.value === 'freehand') {
      console.log("Freehand drawing mode");
      // Freehand drawing mode
      drawInteraction.value = new Draw({
        source: trainingPolygonsLayer.value.getSource(),
        type: 'Polygon',
        freehand: true
      });

      // This is duplicate code as below .. not great
      drawInteraction.value.on('drawend', (event) => {
        const feature = event.feature;
        feature.set('classLabel', selectedClass.value);
        feature.setId(Date.now().toString());
        trainingPolygonsLayer.value.getSource().addFeature(feature);
        const newPolygon = new GeoJSON().writeFeatureObject(feature, {
          dataProjection: 'EPSG:3857',
          featureProjection: 'EPSG:3857'
        });
        drawnPolygons.value.push(newPolygon);
        updateTrainingLayerStyle();
        hasUnsavedChanges.value = true;
      });

      // Add the interaction to the map
      map.value.addInteraction(drawInteraction.value);

    } else if (drawingMode.value === 'square') {

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
          dataProjection: 'EPSG:3857',
          featureProjection: 'EPSG:3857'
        });
        drawnPolygons.value.push(newPolygon);
        updateTrainingLayerStyle();
        // console.log("Drawn polygons: ", drawnPolygons.value);
        // console.log("Features from trainingPolygonsLayer: ", trainingPolygonsLayer.value.getSource().getFeatures());
        // console.log("Has unsaved changes changed to true: ");
        hasUnsavedChanges.value = true;
      };

      map.value.on('click', map.value.clickListener);
    }
  };

  const toggleDrawingMode = () => {
    drawingMode.value = drawingMode.value === 'square' ? 'freehand' : 'square';
    if (isDrawing.value) {
      stopDrawing();
      startDrawing();
    }
  };

  const stopDrawing = () => {
    if (!map.value) return;

    isDrawing.value = false;

    // Remove click listener (for square mode)
    if (map.value.clickListener) {
      map.value.un('click', map.value.clickListener);
      map.value.clickListener = null;
    }

    // Remove draw interaction (for freehand mode)
    if (drawInteraction.value) {
      map.value.removeInteraction(drawInteraction.value);
      drawInteraction.value = null;
    }
  };

  const setSelectedFeature = (feature) => {
    if (selectedFeature.value) {
      selectedFeature.value.setStyle(null); // Reset the previous selection
    }
    selectedFeature.value = feature;
    if (feature) {
      feature.setStyle(selectedFeatureStyle);
    }
  };

  const deleteSelectedFeature = () => {
    if (selectedFeature.value) {
      const vectorSource = map.value.getLayers().getArray().find(layer => layer.get('id') === 'training-polygons').getSource();
      vectorSource.removeFeature(selectedFeature.value);

      // Remove the feature from drawnPolygons array
      const featureId = selectedFeature.value.getId();
      drawnPolygons.value = drawnPolygons.value.filter(polygon => polygon.id !== featureId);


      selectedFeature.value = null;
      hasUnsavedChanges.value = true;
    }
  };



  const clearDrawnPolygons = (setUnsavedChanges = false) => {
    if (trainingPolygonsLayer.value) {
      trainingPolygonsLayer.value.getSource().clear();
    }
    drawnPolygons.value = [];
    if (setUnsavedChanges) {
      hasUnsavedChanges.value = true;
    }
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
    // console.log("Features from trainingPolygonsLayer: ", features)

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
      const olFeature = geoJSONFormat.readFeature(feature, {
        dataProjection: 'EPSG:3857',
        featureProjection: 'EPSG:3857'
      });
      olFeature.setStyle(featureStyleFunction);
      return olFeature;
    });

    if (trainingPolygonsLayer.value) {
      // Update existing layer instead of removing and re-adding
      trainingPolygonsLayer.value.getSource().clear();
      trainingPolygonsLayer.value.getSource().addFeatures(features);
    } else {
      // Create new layer if it doesn't exist
      const vectorSource = new VectorSource({
        features: features
      });

      trainingPolygonsLayer.value = new VectorLayer({
        source: vectorSource,
        title: 'Training Polygons',
        visible: true,
        zIndex: 2,
        id: 'training-polygons',
      });

      map.value.getLayers().insertAt(0, trainingPolygonsLayer.value);
      // map.value.addLayer(trainingPolygonsLayer.value);
    }

    drawnPolygons.value = polygonsData.features;

    // Ensure the layer order is updated in the store
    updateLayers();
  };

  // Method to set interaction mode
  const setInteractionMode = (mode) => {
    if (mode === interactionMode.value) return;

    // Remove all interactions
    stopDrawing();
    if (dragPanInteraction.value) map.value.removeInteraction(dragPanInteraction.value);
    if (dragZoomInInteraction.value) map.value.removeInteraction(dragZoomInInteraction.value);
    if (dragZoomOutInteraction.value) map.value.removeInteraction(dragZoomOutInteraction.value);

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
      hasUnsavedChanges.value = true;
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
      const trainingSet = response.data.find(set => set.basemap_date === date);
      if (trainingSet) {
        const polygons = await api.getSpecificTrainingPolygons(projectStore.currentProject.id, trainingSet.id);
        console.log("polygons within MapStore:", polygons.data[0].polygons)
        loadPolygons(polygons.data[0].polygons);
      } else {
        clearDrawnPolygons();
      }
    } catch (error) {
      console.error('Error loading training polygons:', error);
      // Handle error (e.g., show notification to user)
    }
  };

  const promptSaveChanges = async () => {
    console.log("promptSaveChanges within MapStore:", hasUnsavedChanges.value);

    if (hasUnsavedChanges.value) {
      return new Promise((resolve, reject) => {
        $q.dialog({
          title: 'Unsaved Changes',
          message: 'You have unsaved changes. Would you like to save them?',
          ok: 'Save',
          cancel: 'Discard'
        }).onOk(async () => {
          await saveCurrentTrainingPolygons(selectedBasemapDate.value);
          resolve(); // Resolve the promise after saving
        }).onCancel(() => {
          console.log('Changes discarded');
          hasUnsavedChanges.value = false;
          resolve(); // Resolve the promise even if discarded, to allow the app to move forward
        }).onDismiss(() => {
          resolve(); // Ensure the promise is resolved even if the dialog is dismissed
        });
      });
    } else {
      return Promise.resolve(); // If no unsaved changes, resolve immediately
    }
  };

  const saveCurrentTrainingPolygons = async (date) => {
    const projectStore = useProjectStore();
    const polygons = getDrawnPolygonsGeoJSON();
    try {
      console.log("Saving current training polygons for date:", date, polygons);
      // First, check if a training set for this date already exists
      const response = await api.getTrainingPolygons(projectStore.currentProject.id);
      const existingSet = response.data.find(set => set.basemap_date === date);

      if (existingSet) {
        console.log("Updating existing training set for date:", date);
        // Update existing training set - Pass id and data separately
        await api.updateTrainingPolygons(
          existingSet.id,  // Pass the ID separately
          {
            project: projectStore.currentProject.id,
            basemap_date: date,
            polygons: polygons,
            name: `Training_Set_${date}`
          }
        );
        console.log("Training set updated successfully for date:", date);
      } else {
        console.log("Creating new training set for date:", date);
        // Create new training set
        await api.saveTrainingPolygons({
          project: projectStore.currentProject.id,
          basemap_date: date,
          polygons: polygons,
          name: `Training_Set_${date}`
        });
        console.log("Training set created successfully for date:", date);
      }
      hasUnsavedChanges.value = false;

      // Re-fetch training dates to update the UI
      await projectStore.fetchTrainingDates();

    } catch (error) {
      console.error('Error saving training polygons:', error);
      throw error;
    }
  };

  // Used when loading polygons from a file
  const addPolygon = (polygonGeoJSON) => {
    // Convert GeoJSON to OpenLayers Feature
    const geojsonFormat = new GeoJSON();
    const feature = geojsonFormat.readFeature(polygonGeoJSON, {
      dataProjection: 'EPSG:3857',
      featureProjection: 'EPSG:3857'
    });

    // Add to the training polygons layer
    trainingPolygonsLayer.value.getSource().addFeature(feature);

    // Update drawnPolygons
    drawnPolygons.value.push({
      ...polygonGeoJSON,
      properties: {
        ...polygonGeoJSON.properties,
        basemapDate: polygonGeoJSON.properties.basemapDate || selectedBasemapDate.value
      }
    });

    hasUnsavedChanges.value = true;
  };

  const reorderLayers = (fromIndex, toIndex, mapId = null) => {
    if (mapId && maps.value[mapId]) {
      // Dual map mode
      const layerArray = maps.value[mapId].getLayers().getArray();
      const [movedLayer] = layerArray.splice(fromIndex, 1);
      layerArray.splice(toIndex, 0, movedLayer);

      // Update z-index for all layers
      layerArray.forEach((layer, index) => {
        layer.setZIndex(layerArray.length - index);
      });
    } else if (map.value) {
      // Single map mode - existing behavior
      const layerArray = map.value.getLayers().getArray();
      const [movedLayer] = layerArray.splice(fromIndex, 1);
      layerArray.splice(toIndex, 0, movedLayer);

      layerArray.forEach((layer, index) => {
        layer.setZIndex(layerArray.length - index);
      });
    }
    updateLayers();
  };

  const updateSliderValue = (value) => {
    sliderValue.value = value;
  };


  const addGeoJSON = (layerId, geoJSON) => {

    console.log("Adding GeoJSON to map:", geoJSON);

    // Remove existing layer if it exists
    if (layers.value[layerId]) {
      map.value.removeLayer(layers.value[layerId]);
    }

    // Create vector source from GeoJSON
    const vectorSource = new VectorSource({
      features: new GeoJSON().readFeatures(geoJSON)
    });

    // Create style based on options or defaults
    const style = new Style({
      fill: new Fill({
        color: 'rgba(255, 68, 68, 0.2)'
      }),
      stroke: new Stroke({
        color: '#FF4444',
        width: 2
      })
    });

    // Create vector layer
    const vectorLayer = new VectorLayer({
      source: vectorSource,
      style: style,
      title: layerId,
      id: layerId,
      zIndex: 1
    });

    // Add layer to map and store reference
    map.value.addLayer(vectorLayer);
    layers.value[layerId] = vectorLayer;

    return vectorLayer;
  };

  const fitBounds = (geometry) => {
    if (!map.value) return;

    // Create temporary source to get extent of geometry
    const tempSource = new VectorSource({
      features: new GeoJSON().readFeatures(geometry, {
        featureProjection: map.value.getView().getProjection()
      })
    });

    const extent = tempSource.getExtent();
    map.value.getView().fit(extent, {
      padding: [50, 50, 50, 50],
      maxZoom: 18,
      duration: 1000  // Smooth animation
    });
  };


  // Print to console every time hasUnsavedChanges is set to true
  watch(hasUnsavedChanges, (newVal) => {
    console.log("hasUnsavedChanges has been set to true");
  });


  // Getters
  const getMap = computed(() => map.value);



  // Add new methods
  const initDualMaps = (primaryTarget, secondaryTarget) => {

    // console.log('Primary target:', primaryTarget);
    // console.log('Secondary target:', secondaryTarget);

    // Initialize maps no matter what
    // if (!maps.value.primary || !maps.value.secondary) {
      console.log('Initializing dual maps!');

      // nextTick(async () => {
        // Create maps
        maps.value.primary = new Map({
          target: primaryTarget,
          layers: [
            new TileLayer({
              source: new OSM(),
              name: 'baseMap',
              title: 'OpenStreetMap',
              visible: true,
              id: 'osm',
              zIndex: 0
            })
          ],
          view: new View({
            center: fromLonLat([-79.81822466589962, 0.460628082970743]),
            zoom: 12
          })
        });

        maps.value.secondary = new Map({
          target: secondaryTarget,
          layers: [
            new TileLayer({
              source: new OSM(),
              name: 'baseMap',
              title: 'OpenStreetMap',
              visible: true,
              id: 'osm',
              zIndex: 0
            })
          ],
          view: new View({
            center: fromLonLat([-79.81822466589962, 0.460628082970743]),
            zoom: 12
          })
        });

        // Force a redraw
        maps.value.primary.updateSize();
        maps.value.secondary.updateSize();

        // Add AOI layers if project has AOI
        const projectStore = useProjectStore();
        if (projectStore.currentProject?.aoi) {
          console.log("Setting up AOI layers in dual maps...");

          // Create AOI layers
          const { layer: primaryAOILayer, source: aoiSource } = createAOILayer(
            projectStore.currentProject.aoi
          );
          const { layer: secondaryAOILayer } = createAOILayer(
            projectStore.currentProject.aoi
          );

          // Add layers
          maps.value.primary.addLayer(primaryAOILayer);
          maps.value.secondary.addLayer(secondaryAOILayer);

          // Get AOI extent and fit both maps
          const extent = aoiSource.getExtent();
          console.log('Fitting to AOI extent:', extent);

          maps.value.primary.getView().fit(extent);
          maps.value.secondary.getView().fit(extent);

          // Secondary map will sync automatically due to view synchronization
        }

        // Sync map movements
        const primaryView = maps.value.primary.getView();
        const secondaryView = maps.value.secondary.getView();

        // Sync center changes
        primaryView.on('change:center', () => {
          secondaryView.setCenter(primaryView.getCenter());
        });
        secondaryView.on('change:center', () => {
          primaryView.setCenter(secondaryView.getCenter());
        });

        // Sync zoom changes
        primaryView.on('change:resolution', () => {
          secondaryView.setResolution(primaryView.getResolution());
        });
        secondaryView.on('change:resolution', () => {
          primaryView.setResolution(secondaryView.getResolution());
        });

        // Sync rotation changes
        primaryView.on('change:rotation', () => {
          secondaryView.setRotation(primaryView.getRotation());
        });
        secondaryView.on('change:rotation', () => {
          primaryView.setRotation(secondaryView.getRotation());
        });
      // });

    // } // End if

    // Attach them
    maps.value.primary.setTarget(primaryTarget)
    maps.value.secondary.setTarget(secondaryTarget)

  };

  function hideDualMaps() {
    if (maps.value.primary) {
      maps.value.primary.setTarget(null)
    }
    if (maps.value.secondary) {
      maps.value.secondary.setTarget(null)
    }
  }

  // Add methods for managing layers on dual maps
  const addLayerToDualMaps = (layer, mapId) => {
    if (mapId === 'primary') {
      maps.value.primary.addLayer(layer);
    } else if (mapId === 'secondary') {
      maps.value.secondary.addLayer(layer);
    } else {
      // Add to both maps
      maps.value.primary.addLayer(layer.clone());
      maps.value.secondary.addLayer(layer.clone());
    }
    updateLayers();
  };

  const removeLayerFromDualMaps = (layerId, mapId) => {
    if (mapId === 'primary') {
      const layer = maps.value.primary.getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) maps.value.primary.removeLayer(layer);
    } else if (mapId === 'secondary') {
      const layer = maps.value.secondary.getLayers().getArray().find(l => l.get('id') === layerId);
      if (layer) maps.value.secondary.removeLayer(layer);
    } else {
      // Remove from both maps
      ['primary', 'secondary'].forEach(id => {
        const map = maps.value[id];
        const layer = map.getLayers().getArray().find(l => l.get('id') === layerId);
        if (layer) map.removeLayer(layer);
      });
    }
    updateLayers();
  };

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
    hasUnsavedChanges,
    selectedFeature,
    selectedFeatureStyle,
    sliderValue,
    drawingMode,
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
    promptSaveChanges,
    reorderLayers,
    setSelectedFeature,
    deleteSelectedFeature,
    updateSliderValue,
    addPolygon,
    toggleDrawingMode,
    fitBounds,
    addGeoJSON,
    createPlanetBasemap,
    createAOILayer,
    showSingleMap,
    hideSingleMap,
    hideDualMaps,
    // Getters
    getMap,
    maps,
    initDualMaps,
    addLayerToDualMaps,
    removeLayerFromDualMaps,
  };
});