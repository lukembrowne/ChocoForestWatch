import { defineStore } from 'pinia';
import api from 'src/services/api';
import authService from 'src/services/auth';
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'
import { Map, View } from 'ol'
import 'ol/ol.css';
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import { Style, Fill, Stroke, Circle as CircleStyle } from 'ol/style'
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
import { Polygon, Point } from 'ol/geom';
import { fromLonLat, toLonLat } from 'ol/proj';
import { transformExtent } from 'ol/proj'
import { useQuasar } from 'quasar';
import { getEncodedColormap } from 'src/utils/colormap';
import { createBox } from 'ol/interaction/Draw';

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
  const randomPoints = ref([]);
  const currentPointIndex = ref(-1);
  const boundaryLayer = ref(null);

  // Search (geocoder) state
  const searchResults = ref([]);
  const searchMarkerLayer = ref(null);

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

  // Summary AOI drawing
  const summaryAOILayer = ref(null);
  const summaryDrawInteraction = ref(null);
  const isDrawingSummaryAOI = ref(false);
  const summaryStats = ref(null);

  // Forest Cover Maps selection
  const availableDatasets = [
    {
      value: 'northern_choco_test_2025_06_20_2022_merged_composite',
      label: 'Choco Forest Watch 2022',
      version: '2022.01.0',
      year: '2022',
      resolution: '4.7m',
      description: 'High-resolution forest cover predictions for Choco region',
      created: '2025-06-20',
      type: 'prediction'
    },
    {
      value: 'planet-nicfi-basemap',
      label: 'Planet NICFI Basemap',
      year: '2022-2024',
      resolution: '4.7m',
      description: 'Monthly high-resolution satellite imagery from Planet Labs via Norway\'s International Climate & Forests Initiative',
      type: 'basemap-imagery'
    },
    {
      value: 'datasets-hansen-tree-cover-2022',
      label: 'Hansen Global Forest Change',
      year: '2022',
      resolution: '30m',
      description: 'Global forest change dataset from University of Maryland',
      type: 'benchmark'
    },
    {
      value: 'datasets-mapbiomes-2022',
      label: 'MapBiomas Ecuador',
      year: '2022',
      resolution: '30m',
      description: 'Annual land cover and land use mapping for Ecuador',
      type: 'benchmark'
    },
    {
      value: 'datasets-esa-landcover-2020',
      label: 'ESA WorldCover',
      year: '2020',
      resolution: '10m',
      description: 'Global land cover map from European Space Agency',
      type: 'benchmark'
    },
    {
      value: 'datasets-jrc-forestcover-2020',
      label: 'JRC Forest Cover',
      year: '2020',
      resolution: '10m',
      description: 'Forest cover map from Joint Research Centre',
      type: 'benchmark'
    },
    {
      value: 'datasets-palsar-2020',
      label: 'ALOS PALSAR Forest Map',
      year: '2020',
      resolution: '25m',
      description: 'Forest/non-forest map from ALOS PALSAR data',
      type: 'benchmark'
    },
    {
      value: 'datasets-wri-treecover-2020',
      label: 'WRI Tropical Tree Cover',
      year: '2020',
      resolution: '30m',
      description: 'Tropical tree cover from World Resources Institute',
      type: 'benchmark'
    },
    {
      value: 'datasets-gfw-integrated-alerts-2022',
      label: 'GFW Deforestation Alerts 2022',
      year: '2022',
      resolution: '10m',
      description: 'Global Forest Watch integrated deforestation alerts',
      type: 'alerts'
    },
    {
      value: 'datasets-gfw-integrated-alerts-2023',
      label: 'GFW Deforestation Alerts 2023',
      year: '2023',
      resolution: '10m',
      description: 'Global Forest Watch integrated deforestation alerts',
      type: 'alerts'
    },
    {
      value: 'datasets-gfw-integrated-alerts-2024',
      label: 'GFW Deforestation Alerts 2024',
      year: '2024',
      resolution: '10m',
      description: 'Global Forest Watch integrated deforestation alerts',
      type: 'alerts'
    },
  ];
  const selectedBenchmark = ref(availableDatasets[0].value);

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

  // Add benchmark expression mapping constant
  const benchmarkExpressionMapping = {
    'northern_choco_test_2025_06_20_2022_merged_composite': 'where((data==1),1,0)',
    'datasets-hansen-tree-cover-2022': 'where(data>=90,1,0)',
    'datasets-mapbiomes-2022': 'where((data==3)|(data==4)|(data==5)|(data==6),1,0)',
    'datasets-esa-landcover-2020': 'where(data==10,1,0)',
    'datasets-jrc-forestcover-2020': 'where(data==1,1,0)',
    'datasets-palsar-2020': 'where((data==1)|(data==2),1,0)',
    'datasets-wri-treecover-2020': 'where(data>=90,1,0)',
    // GFW alerts - use band 1 (binary alerts: 0=no alert, 1=alert, 255=missing)
    'datasets-gfw-integrated-alerts-2022': 'where(data==1,1,0)',
    'datasets-gfw-integrated-alerts-2023': 'where(data==1,1,0)',
    'datasets-gfw-integrated-alerts-2024': 'where(data==1,1,0)',
  };

  // GFW date/confidence decoder functions
  const decodeGFWDate = (value) => {
    if (value === 0) return { date: null, confidence: null };

    const encoded_str = value.toString();

    // Handle single digit values (confidence only, no date)
    if (encoded_str.length === 1) {
      return { date: null, confidence: parseInt(encoded_str) };
    }

    // Get confidence level from first digit
    const confidence = parseInt(encoded_str[0]);

    // Get days since Dec 31, 2014
    const days = parseInt(encoded_str.substring(1));

    // Calculate date
    const baseDate = new Date(2014, 11, 31); // Month is 0-indexed
    const alertDate = new Date(baseDate.getTime() + days * 24 * 60 * 60 * 1000);

    return { date: alertDate, confidence: confidence };
  };

  const formatGFWAlert = (value) => {
    const decoded = decodeGFWDate(value);
    if (!decoded.date && !decoded.confidence) return 'No alert';

    let result = '';
    if (decoded.date) {
      result += `Date: ${decoded.date.toLocaleDateString()}`;
    }
    if (decoded.confidence) {
      const confidenceLevels = {
        1: 'Low',
        2: 'Medium',
        3: 'High',
        4: 'Very High'
      };
      result += `${result ? ', ' : ''}Confidence: ${confidenceLevels[decoded.confidence] || decoded.confidence}`;
    }
    return result;
  };

  // Actions
  const initMap = (target, force = false) => {
    if (!map.value || force) {
      map.value = new Map({
        target: target,
        layers: [
          new TileLayer({
            source: new OSM({
              attributions: '© OpenStreetMap contributors'
            }),
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

      const isAdmin = authService.getCurrentUser()?.user?.is_superuser === true;
      if (isAdmin) {
        initTrainingLayer();
        initInteractions();
      }

      // Initialize layers
      updateLayers();

      // Watch for changes in the map's layers
      map.value.getLayers().on(['add', 'remove'], updateLayers);

      console.log('Map initialized in MapStore...');
      mapInitialized.value = true;
      map.value.setTarget(target)
      initBoundaryLayer();
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

    // If removing Planet imagery layer, reset the selected benchmark
    if (layerId && layerId.includes('planet')) {
      selectedBenchmark.value = null;
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
  const createBasemap = (date, type) => {

    // Type shoudl be either 'planet' or 'predictions'
    // Check to make sure type is valid
    if (type !== 'planet' && type !== 'predictions') {
      throw new Error('Invalid basemap type');
    }

    //
    // Retrieve the Planet API key from the environment variables
    const titilerURL = import.meta.env.VITE_TITILER_URL;
    console.log("Titiler URL: ", titilerURL)

    // Create a new XYZ source for titiler from single tile - works
    // const source = new XYZ({
    //   url: `http://localhost:8080/cog/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?url=file%3A%2F%2F%2Fdata%2F2022%2F01%2F570-1025_2022_01.tif&bidx=3&bidx=2&bidx=1&rescale=0,2500`,
    // });


    // Create a new XYZ source for titiler from mosaic - this works!
    // const source = new XYZ({
    //   url: `http://localhost:8080/mosaicjson/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?url=file%3A%2F%2F%2Fmosaics%2F${date}.json&bidx=3&bidx=2&bidx=1&rescale=0%2C2500`,
    // });

    // Testing out with mosaicJsons locally - this works!
    // const source = new XYZ({
    //   url: `http://localhost:8080/mosaicjson/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?url=file%3A%2F%2F%2FmosaicJsons%2F${date}-mosaic.json&bidx=3&bidx=2&bidx=1&rescale=0%2C2500`,
    // });

    // Testing out with mosaicJsons on server with base titiler - this works!
    // const source = new XYZ({
    //   url: `${titilerURL}/mosaicjson/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?url=file%3A%2F%2F%2FmosaicJsons%2F${date}-mosaic.json&bidx=3&bidx=2&bidx=1&rescale=0%2C2500`,
    // });

    // Testing out with titiler-pgstac - this works!!
    //  const source = new XYZ({
    //   url: `http://localhost:8083/collections/nicfi-2022-01/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&pixel_selection=first&bidx=3&bidx=2&bidx=1&rescale=0%2C1500`,
    // });

    // Testing out loading predictions from Spaces - this works!!

    // Python palette to JSON palette - need to find a better way to do this..
    //   palette = {
    //     "1": [0, 128, 0], "2": [255, 255, 0], "3": [255, 255, 255],
    //   "4": [0, 0, 0], "5": [0, 0, 255]
    // }
    // import urllib.parse, json

    // colormap_param = urllib.parse.quote(json.dumps(palette))


    // import urllib.parse, json

    // palette = { "1": [0, 128, 0], "0": [255, 255, 0] }
    // colormap_param = urllib.parse.quote(json.dumps(palette))



    // If planet imagery

    let source;

    if (type === 'planet') {
      const year = date.split('-')[0];
      source = new XYZ({
        url: `${titilerURL}/collections/nicfi-${date}/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&pixel_selection=first&bidx=3&bidx=2&bidx=1&rescale=0%2C1500`,
        maxZoom: 14,
        attributions: `Imagery © ${year} Planet Labs Inc. All use subject to the <a href="https://www.planet.com/terms-of-use/" target="_blank">Planet Participant License Agreement</a>`
      });
    }


    // Create a new XYZ source for predictions
    if (type === 'predictions') {

      // const colormap = encodeColormap(landcoverPalette);

      // source = new XYZ({
      //   url: `http://localhost:8083/collections/northern_choco_test_2025_06_09-pred-2022-01/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&colormap=${colormap}`,
      //   maxZoom: 14,
      // });

      // //  Composite forest cover map - old
      // const colormap =
      //   '%7B%221%22%3A%20%5B0%2C%20128%2C%200%5D%2C%20%220%22%3A%20%5B255%2C%20255%2C%200%5D%7D';

      // source = new XYZ({
      //   url: `http://localhost:8083/collections/nicfi-pred-composite-2022/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&colormap=${colormap}`,
      //   maxZoom: 14,
      // });

      // //  Composite forest cover map - new
      // const colormap = getEncodedColormap('CFWForestCoverPalette');


      // source = new XYZ({
      //   url: `${titilerURL}/collections/nicfi-pred-northern_choco_test_2025_06_20-composite-2022/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&colormap=${colormap}`,
      //   maxZoom: 14,
      // });


      // Testing out hansen tree cover benchmark
      // source = new XYZ({
      //   url: `http://localhost:8083/collections/northern_choco_test_2025_05_21-pred-2022-01/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&colormap=${colormap}`,
      //   maxZoom: 14,
      // });
    }



    // Old planet imagery tile
    // url: `https://tiles{0-3}.planet.com/basemaps/v1/planet-tiles/planet_medres_normalized_analytic_${date}_mosaic/gmap/{z}/{x}/{y}.png?api_key=${apiKey}`,


    // Return a new TileLayer for basemap

    const title = type === 'planet' ? `Planet Basemap ${date}` : `CFW Tree Cover 2022`;
    const id = type === 'planet' ? `planet-basemap` : `predictions`;
    const zIndex = type === 'planet' ? 1 : 2;
    const opacity = type === 'planet' ? 1 : 0.7;
    const visible = type === 'planet' ? true : true;

    return new TileLayer({
      source: source,
      title: title,
      type: 'base', // Set the layer type to 'base'
      visible: visible, // Make the layer visible by default
      id: id, // Set a unique ID for the layer
      zIndex: zIndex, // Set the layer's z-index to 1
      opacity: opacity // Set the layer's opacity to 0.7
    });
  };


  // Function to update the basemap layer with a new date
  const updateBasemap = (date, type) => {

    // Check to make sure type is valid
    if (type !== 'planet' && type !== 'predictions') {
      throw new Error('Invalid basemap type');
    }

    // Create a new Planet Basemap layer for the given date
    const basemap = createBasemap(date, type);

    const id = type === 'planet' ? `planet-basemap` : `predictions`;
    const title = type === 'planet' ? `Planet Basemap ${date}` : `Predictions ${date}`;

    // Find the existing  Basemap layer by its ID
    let existingBasemap = map.value.getLayers().getArray().find(layer => layer.get('id') === id);

    // If an existing layer is found, update it with the new basemap
    if (existingBasemap) {
      console.log("Updating existing basemap layer...");
      existingBasemap.setSource(basemap.getSource());
      existingBasemap.set('title', title);
    } else {
      // If no existing layer is found, create a new one and insert it at a safe position
      console.log("Creating new basemap layer...");
      const layers = map.value.getLayers();
      const layerCount = layers.getLength();

      // Insert at index 2 if we have at least 2 layers, otherwise add to the end
      if (layerCount >= 2) {
        layers.insertAt(2, basemap);
      } else {
        layers.push(basemap);
      }
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
    await updateBasemap(date, 'planet');
    const isAdmin = authService.getCurrentUser()?.user?.is_superuser === true;
    if (isAdmin) {
      await updateBasemap(date, 'predictions');
      await loadTrainingPolygonsForDate(date);
    }
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
      // Create a sorted array by z-index (descending) to match UI display order
      const sortedLayers = [...layerArray].sort((a, b) => b.getZIndex() - a.getZIndex());

      // Move the layer in the sorted array
      const [movedLayer] = sortedLayers.splice(fromIndex, 1);
      sortedLayers.splice(toIndex, 0, movedLayer);
      // Update z-index for all layers based on new order
      sortedLayers.forEach((layer, index) => {
        layer.setZIndex(sortedLayers.length - index);
      });
    } else if (map.value) {
      // Single map mode
      const layerArray = map.value.getLayers().getArray();
      // Create a sorted array by z-index (descending) to match UI display order
      const sortedLayers = [...layerArray].sort((a, b) => b.getZIndex() - a.getZIndex());

      // Move the layer in the sorted array
      const [movedLayer] = sortedLayers.splice(fromIndex, 1);
      sortedLayers.splice(toIndex, 0, movedLayer);
      // Update z-index for all layers based on new order
      sortedLayers.forEach((layer, index) => {
        layer.setZIndex(sortedLayers.length - index);
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
  const initDualMaps = async (primaryTarget, secondaryTarget) => {

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
          source: new OSM({
            attributions: '© OpenStreetMap contributors'
          }),
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
          source: new OSM({
            attributions: '© OpenStreetMap contributors'
          }),
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

    initBoundaryLayer();
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

  const loadRandomPoints = async (collectionId) => {
    try {
      const response = await api.getRandomPoints(collectionId, 1);
      randomPoints.value = response.data.points;
      currentPointIndex.value = -1; // Reset index
      return response.data;
    } catch (error) {
      console.error('Error loading random points:', error);
      throw error;
    }
  };

  const goToNextPoint = () => {
    if (randomPoints.value.length === 0) return;

    currentPointIndex.value = (currentPointIndex.value + 1) % randomPoints.value.length;
    const point = randomPoints.value[currentPointIndex.value];

    // Zoom to the point
    if (map.value) {
      const view = map.value.getView();
      view.animate({
        center: [point.x, point.y],
        zoom: 14,
        duration: 750
      });
    }

    return point;
  };

  const goToPreviousPoint = () => {
    if (randomPoints.value.length === 0) return;

    currentPointIndex.value = (currentPointIndex.value - 1 + randomPoints.value.length) % randomPoints.value.length;
    const point = randomPoints.value[currentPointIndex.value];

    // Zoom to the point
    if (map.value) {
      const view = map.value.getView();
      view.animate({
        center: [point.x, point.y],
        zoom: 14,
        duration: 750
      });
    }

    return point;
  };

  const getCurrentPoint = () => {
    if (currentPointIndex.value === -1 || randomPoints.value.length === 0) return null;
    return randomPoints.value[currentPointIndex.value];
  };

  const clearRandomPoints = () => {
    randomPoints.value = [];
    currentPointIndex.value = -1;
  };

  const initBoundaryLayer = async () => {
    if (boundaryLayer.value) return;                 // already added

    const response = await fetch('/data/Ecuador-DEM-900m-contour.geojson');
    console.log("Response:", response);
    const geojson = await response.json();

    boundaryLayer.value = new VectorLayer({
      source: new VectorSource({
        features: new GeoJSON().readFeatures(geojson, {
          featureProjection: 'EPSG:3857',
        }),
      }),
      id: 'ecuador-boundary',
      title: 'Western Ecuador Boundary',
      zIndex: 4,                           // above OSM, below polygons
      visible: true,
      style: new Style({
        stroke: new Stroke({ color: '#000000', width: 2 }),
      }),
      interactive: false,
      selectable: false,
    });

    map.value?.addLayer(boundaryLayer.value);
    maps.value.primary?.addLayer(boundaryLayer.value.clone());
    maps.value.secondary?.addLayer(boundaryLayer.value.clone());
  };

  // -------------------------------------------
  // Benchmark layers
  // -------------------------------------------

  const createBenchmarkLayer = (collectionId) => {
    const titilerURL = import.meta.env.VITE_TITILER_URL;
    const expression = benchmarkExpressionMapping[collectionId];
    if (!expression) {
      throw new Error(`No expression mapping found for collection ${collectionId}`);
    }
    const encodedExpression = encodeURIComponent(expression);
    const colormap = getEncodedColormap('CFWForestCoverPalette');

    const source = new XYZ({
      url: `${titilerURL}/collections/${collectionId}/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=data&colormap=${colormap}`,
      maxZoom: 14,
    });

    // Get readable title from availableDatasets array
    const benchmarkInfo = availableDatasets.find(b => b.value === collectionId);
    const title = benchmarkInfo ? benchmarkInfo.label : collectionId.replace('datasets-', '').replace(/-/g, ' ');

    return new TileLayer({
      source,
      title: title,
      id: `benchmark-${collectionId}`,
      visible: true,
      zIndex: 3,
      opacity: 0.7,
    });
  };

  const addBenchmarkLayer = (collectionId, mapId = null) => {
    let targetMap;
    if (mapId && maps.value[mapId]) {
      targetMap = maps.value[mapId];
    } else {
      targetMap = map.value;
    }
    if (!targetMap) return;

    // Remove any existing benchmark layers to ensure only one forest cover map at a time
    const existingBenchmarkLayers = targetMap.getLayers().getArray().filter((l) => {
      const id = l.get('id');
      return id && id.startsWith('benchmark-');
    });
    existingBenchmarkLayers.forEach(layer => targetMap.removeLayer(layer));

    // Create and add the new layer
    const newLayer = createBenchmarkLayer(collectionId);

    // Set loading state and add loading indicator
    isLoading.value = true;

    // Add layer loading listeners
    const source = newLayer.getSource();
    let tilesLoading = 0;
    let tilesLoaded = 0;

    source.on('tileloadstart', () => {
      console
      tilesLoading++;
    });

    source.on('tileloadend', () => {
      tilesLoaded++;
      if (tilesLoaded >= Math.min(tilesLoading, 10)) { // Wait for first few tiles
        isLoading.value = false;
      }
    });

    source.on('tileloaderror', () => {
      tilesLoaded++;
      if (tilesLoaded >= Math.min(tilesLoading, 10)) {
        isLoading.value = false;
      }
    });

    // Fallback timeout to clear loading state
    setTimeout(() => {
      isLoading.value = false;
    }, 5000);

    targetMap.addLayer(newLayer);
    updateLayers();
  };

  // Add Planet NICFI imagery layer
  const addPlanetImageryLayer = () => {
    if (!map.value) return;

    // Set default date for Planet imagery (January 2022)
    const defaultDate = '2022-01';
    // Create and add Planet basemap layer
    updateBasemap(defaultDate, 'planet');

    // Update the selected benchmark in the store to reflect Planet imagery is active
    selectedBenchmark.value = 'planet-nicfi-basemap';

    // Make sure the basemap date slider is visible by setting the selected date
    selectedBasemapDate.value = defaultDate;
    updateLayers();
  };

  // -------------------------------------------
  // Search functionality (Nominatim geocoder)
  // -------------------------------------------

  const searchLocation = async (query) => {
    if (!query || !query.trim()) {
      searchResults.value = [];
      return [];
    }
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(query)}`;
      const response = await fetch(url, {
        headers: {
          'Accept-Language': 'en',
          'User-Agent': 'ChocoForestWatch/0.1 (+https://chocoforestwatch.org)'
        }
      });
      const data = await response.json();
      searchResults.value = data.map((d) => ({
        label: d.display_name,
        lon: Number(d.lon),
        lat: Number(d.lat),
        bbox: d.boundingbox.map(Number)
      }));
    } catch (err) {
      console.error('Location search failed:', err);
      searchResults.value = [];
    }
    return searchResults.value;
  };

  const zoomToSearchResult = (result, zoomLevel = 14) => {
    if (!map.value || !result) return;

    // Prepare / clear marker layer
    if (!searchMarkerLayer.value) {
      searchMarkerLayer.value = new VectorLayer({
        source: new VectorSource(),
        style: new Style({
          image: new CircleStyle({
            radius: 6,
            fill: new Fill({ color: '#1976D2' }),
            stroke: new Stroke({ color: '#ffffff', width: 2 })
          })
        }),
        id: 'search-marker',
        title: 'Search Result',
        zIndex: 100
      });
      map.value.addLayer(searchMarkerLayer.value);
    } else {
      searchMarkerLayer.value.getSource().clear();
    }

    const coord3857 = fromLonLat([result.lon, result.lat]);
    searchMarkerLayer.value.getSource().addFeature(new Feature({ geometry: new Point(coord3857) }));

    if (result.bbox && result.bbox.length === 4) {
      const extent4326 = [result.bbox[2], result.bbox[0], result.bbox[3], result.bbox[1]]; // minX, minY, maxX, maxY
      const extent3857 = transformExtent(extent4326, 'EPSG:4326', map.value.getView().getProjection());
      map.value.getView().fit(extent3857, { duration: 500, maxZoom: zoomLevel });
    } else {
      map.value.getView().animate({ center: coord3857, zoom: zoomLevel, duration: 500 });
    }
  };

  // ---------------------------------------------------------------------------
  // AOI summary drawing and computation
  // ---------------------------------------------------------------------------

  const startSummaryAOIDraw = () => {
    if (!map.value) return;

    // Ensure previous summary AOI cleared
    clearSummaryAOI();

    isDrawingSummaryAOI.value = true;

    // Create vector layer to hold the rectangle
    summaryAOILayer.value = new VectorLayer({
      source: new VectorSource(),
      style: new Style({
        stroke: new Stroke({ color: '#1976D2', width: 2 }),
        fill: new Fill({ color: 'rgba(25, 118, 210, 0.1)' })
      }),
      title: 'Summary AOI',
      id: 'summary-aoi',
      zIndex: 101
    });
    map.value.addLayer(summaryAOILayer.value);

    // Box draw interaction
    summaryDrawInteraction.value = new Draw({
      source: summaryAOILayer.value.getSource(),
      type: 'Circle', // special code for box with geometryFunction
      geometryFunction: createBox(),
    });

    summaryDrawInteraction.value.on('drawend', async (evt) => {
      try {
        const geom3857 = evt.feature.getGeometry();
        // Convert to GeoJSON WGS84 (EPSG:4326)
        const geoJSONGeom = new GeoJSON().writeGeometryObject(geom3857, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857',
        });

        // Send to backend
        isLoading.value = true;
        const resp = await api.getAOISummary({ type: 'Feature', geometry: geoJSONGeom }, selectedBenchmark.value);
        summaryStats.value = resp.data;
      } catch (err) {
        console.error('Failed to compute AOI summary:', err);
        $q.notify({ type: 'negative', message: 'Failed to compute summary statistics.' });
      } finally {
        isLoading.value = false;
        stopSummaryAOIDraw();
      }
    });

    map.value.addInteraction(summaryDrawInteraction.value);
  };

  const stopSummaryAOIDraw = () => {
    if (!map.value) return;
    isDrawingSummaryAOI.value = false;
    if (summaryDrawInteraction.value) {
      map.value.removeInteraction(summaryDrawInteraction.value);
      summaryDrawInteraction.value = null;
    }
  };

  const clearSummaryAOI = () => {
    if (!map.value) return;
    stopSummaryAOIDraw();
    summaryStats.value = null;
    if (summaryAOILayer.value) {
      map.value.removeLayer(summaryAOILayer.value);
      summaryAOILayer.value = null;
    }
  };

  // Load cached western Ecuador statistics for the selected benchmark
  const loadWesternEcuadorStats = async () => {
    // Skip statistics for Planet basemap - no regional stats available
    if (selectedBenchmark.value === 'planet-nicfi-basemap') {
      summaryStats.value = null;
      return;
    }
    try {
      isLoading.value = true;
      const response = await api.getWesternEcuadorStats(selectedBenchmark.value);
      summaryStats.value = response.data;
    } catch (error) {
      console.error('Failed to load western Ecuador stats:', error);
      summaryStats.value = null; // Clear statistics on error
      $q.notify({
        type: 'negative',
        message: 'Failed to load regional statistics.',
        timeout: 4000
      });
    } finally {
      isLoading.value = false;
    }
  };

  // -------------------------------------------
  // GFW Alerts functionality  
  // -------------------------------------------

  const createGFWAlertsLayer = (collectionId, year) => {
    // Create a raster layer for GFW alerts using TiTiler
    // Use band 1 (binary alerts) for display with custom colormap for alerts only

    // Create tile URL that works for both legacy (1-band) and new (2-band) rasters

    const colormap = getEncodedColormap('AlertPalette');

    const tileUrl = `${import.meta.env.VITE_TITILER_URL || 'http://localhost:8081'}/collections/${collectionId}/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?bidx=1&assets=data&colormap=${colormap}`;
    const source = new XYZ({
      url: tileUrl,
      attributions: '© Global Forest Watch',
      crossOrigin: 'anonymous'
    });

    const layer = new TileLayer({
      source: source,
      title: `GFW Deforestation Alerts ${year}`,
      id: `gfw-alerts-${year}`,
      visible: true,
      zIndex: 4, // Higher than benchmark layers
      opacity: 0.8
    });

    // Store collection ID for later use in click queries
    layer.set('collectionId', collectionId);
    layer.set('datasetType', 'alerts');

    return layer;
  };

  const addGFWAlertsLayer = (collectionId, year, mapId = null) => {
    const layerId = `gfw-alerts-${year}`;
    let targetMap;

    if (mapId && maps.value[mapId]) {
      targetMap = maps.value[mapId];
    } else {
      targetMap = map.value;
    }

    if (!targetMap) return;

    // Avoid adding duplicate layer with same id
    const existing = targetMap.getLayers().getArray().find((l) => l.get('id') === layerId);
    if (existing) {
      existing.setVisible(true);
      updateLayers();
      return;
    }

    try {
      const newLayer = createGFWAlertsLayer(collectionId, year);
      targetMap.addLayer(newLayer);
      updateLayers();

      // Add click-to-query functionality for GFW alerts
      setupGFWClickHandler(targetMap);

      $q.notify({
        type: 'positive',
        message: `GFW Deforestation Alerts ${year} layer added successfully`,
        timeout: 2000
      });
    } catch (error) {
      console.error('Error adding GFW alerts layer:', error);
      $q.notify({
        type: 'negative',
        message: 'Failed to add GFW alerts layer',
        timeout: 3000
      });
    }
  };

  // GFW click-to-query functionality
  const setupGFWClickHandler = (targetMap) => {
    // Remove existing GFW click handler if it exists
    if (targetMap.gfwClickHandler) {
      targetMap.un('singleclick', targetMap.gfwClickHandler);
    }

    targetMap.gfwClickHandler = async (event) => {
      // Only process clicks when a GFW alerts layer is visible
      const gfwLayers = targetMap.getLayers().getArray().filter(layer =>
        layer.get('datasetType') === 'alerts' && layer.getVisible()
      );

      if (gfwLayers.length === 0) return;

      const coordinate = event.coordinate;
      const lonLat = toLonLat(coordinate);

      // Flag to track if we found any alerts
      let foundAlert = false;

      // Query each visible GFW layer
      for (const layer of gfwLayers) {
        const collectionId = layer.get('collectionId');
        if (!collectionId) continue;

        try {
          // Try band 2 first (for new 2-band rasters), fallback to band 1 (for legacy single-band rasters)
          let response = await fetch(
            `${import.meta.env.VITE_TITILER_URL || 'http://localhost:8081'}/collections/${collectionId}/point/${lonLat[0]},${lonLat[1]}?bidx=2&assets=data&asset_as_band=true`,
            { method: 'GET' }
          );

          // If band 2 doesn't exist, try band 1 (legacy format)
          if (!response.ok) {
            response = await fetch(
              `${import.meta.env.VITE_TITILER_URL || 'http://localhost:8081'}/collections/${collectionId}/point/${lonLat[0]},${lonLat[1]}?bidx=1&assets=data&asset_as_band=true`,
              { method: 'GET' }
            );
          }

          if (response.ok) {
            const data = await response.json();
            // TiTiler returns: { values: [[collection_id, [pixel_value], [asset_name]]] }
            const pixelValue = data.values?.[0]?.[1]?.[0];

            if (pixelValue && pixelValue > 0) {
              // Display alert information
              showGFWAlertPopup(coordinate, pixelValue, layer.get('title'));
              foundAlert = true;
              break; // Only show popup for first matching layer
            }
          }
        } catch (error) {
          console.error('Error querying GFW pixel value:', error);
        }
      }

      // If no alerts were found, hide any existing popup
      if (!foundAlert) {
        hideGFWAlertPopup();
      }
    };

    targetMap.on('singleclick', targetMap.gfwClickHandler);
  };

  // State for GFW alert popup
  const gfwAlertInfo = ref(null);
  const gfwAlertVisible = ref(false);

  const showGFWAlertPopup = (coordinate, pixelValue, layerTitle) => {
    const alertData = decodeGFWDate(pixelValue);
    gfwAlertInfo.value = {
      coordinate,
      layerTitle,
      ...alertData,
      pixelValue,
      formattedInfo: formatGFWAlert(pixelValue)
    };

    // Show the popup - Vue component will handle positioning
    gfwAlertVisible.value = true;
  };

  const hideGFWAlertPopup = () => {
    gfwAlertVisible.value = false;
    gfwAlertInfo.value = null;
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
    randomPoints,
    currentPointIndex,
    searchResults,
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
    createBasemap,
    createAOILayer,
    showSingleMap,
    hideSingleMap,
    hideDualMaps,
    loadRandomPoints,
    goToNextPoint,
    goToPreviousPoint,
    getCurrentPoint,
    clearRandomPoints,
    // AOI summary
    startSummaryAOIDraw,
    clearSummaryAOI,
    loadWesternEcuadorStats,
    summaryStats,
    isDrawingSummaryAOI,
    // Search actions
    searchLocation,
    zoomToSearchResult,
    // new benchmark actions
    addBenchmarkLayer,
    addGFWAlertsLayer,
    addPlanetImageryLayer,
    // GFW alerts functionality
    decodeGFWDate,
    formatGFWAlert,
    gfwAlertInfo,
    gfwAlertVisible,
    hideGFWAlertPopup,
    // Getters
    getMap,
    maps,
    initDualMaps,
    addLayerToDualMaps,
    removeLayerFromDualMaps,
    // Benchmark selection
    availableDatasets,
    selectedBenchmark,
  };
});