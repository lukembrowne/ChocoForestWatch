<template>
  <div>
    <div class="toolbar">
      <q-btn label="Draw Polygon" color="primary" @click="startDrawing" />
      <q-btn v-if="drawing" label="Stop Drawing" color="negative" @click="stopDrawing" class="q-ml-md" />
      <q-select v-if="drawing" v-model="classLabel" :options="classOptions" label="Class Label" class="q-ml-md" />
      <q-btn label="Save GeoJSON" color="primary" @click="saveGeoJSON" class="q-ml-md" />
      <q-btn label="Save Polygons to Local Storage" color="primary" @click="savePolygonsToLocalStorage"
        class="q-ml-md" />
      <q-btn label="Load from Local Storage" color="primary" @click="loadPolygonsFromLocalStorage" class="q-ml-md" />
      <q-btn label="Load Raster" color="primary" @click="loadRaster" class="q-ml-md" />
      <q-btn label="Extract Pixels" color="primary" @click="extractPixels" class="q-ml-md" />
    </div>
    <div class="map-container" id="map"></div>
    <div>Selected Raster in MapComponent: {{ selectedRaster ? selectedRaster.filename : 'None' }}</div>

  </div>
</template>

<script>
import 'ol/ol.css';
import { Map, View } from 'ol';
import TileLayer from 'ol/layer/Tile';
import XYZ from 'ol/source/XYZ';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import { Draw, Modify, Select } from 'ol/interaction';
import { click } from 'ol/events/condition';
import { Style, Fill, Stroke } from 'ol/style';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';
import { fromUrl } from 'geotiff';
import { fromLonLat } from 'ol/proj';



export default {
  name: 'MapComponent',
  props: {
    selectedRaster: {
      type: Object,
      default: null
    },
    selectedVector: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      map: null,
      error: null,
      mapInitialized: false,
      vectorLayer: null,
      rasterLayer: null,
      drawInteraction: null,
      modifyInteraction: null,
      selectInteraction: null,
      drawing: false,
      classLabel: 'forest',
      classOptions: [
        { label: 'Forest', value: 'forest' },
        { label: 'Non-Forest', value: 'non-forest' },
      ],
      polygons: [],
      selectedPolygon: null,
    };
  },
  watch: {
    selectedRaster: {
      handler(newRaster) {
        console.log('MapComponent - selectedRaster watcher triggered');
        console.log('New raster:', newRaster);
        if (newRaster && newRaster.filename) {
          const url = `http://127.0.0.1:5000/rasters/${newRaster.filename}`;
          this.loadRaster(url);
        } else {
          console.log('No valid raster selected');
        }
      },
      deep: true
    },
    selectedVector: {
      handler(newVector) {
        if (newVector && newVector.id) {
          this.loadVector(newVector.id);
        }
      },
      deep: true
    }
  },
  mounted() {
    this.initMap();
    this.mapInitialized = true;
    window.addEventListener('keydown', this.handleKeyDown);
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleKeyDown);
  },
  methods: {
    async loadRaster(url) {
      console.log('Loading raster:', url);
      this.error = null;

      if (!this.mapInitialized) {
        console.log('Map not initialized yet, waiting...');
        await new Promise(resolve => {
          const checkInitialization = setInterval(() => {
            if (this.mapInitialized) {
              clearInterval(checkInitialization);
              resolve();
            }
          }, 100);
        });
      }

      if (this.rasterLayer) {
        this.map.removeLayer(this.rasterLayer);
      }

      if (!url) {
        this.error = 'Invalid raster URL';
        return;
      }

      try {
        const tiff = await fromUrl(url);
        const image = await tiff.getImage();
        const width = image.getWidth();
        const height = image.getHeight();
        const bbox = image.getBoundingBox();

        const rasterData = await image.readRasters({
          interleave: true,
          samples: [0, 1, 2]
        });

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d');

        const imageData = context.createImageData(width, height);
        const data = imageData.data;

        for (let i = 0; i < width * height; i++) {
          data[i * 4] = rasterData[i * 3];
          data[i * 4 + 1] = rasterData[i * 3 + 1];
          data[i * 4 + 2] = rasterData[i * 3 + 2];
          data[i * 4 + 3] = 255;
        }
        context.putImageData(imageData, 0, 0);

        const imageUrl = canvas.toDataURL();
        const extent = bbox;

        this.rasterLayer = new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            imageExtent: extent,
          }),
        });

        this.rasterLayer.getSource().on('imageloaderror', () => {
          console.error('Error loading raster image:', url);
          this.error = 'Failed to load raster image';
        });

        this.map.addLayer(this.rasterLayer);

        this.map.getView().fit(extent, { duration: 1000 });
      } catch (error) {
        console.error('Error loading raster:', error);
        this.error = 'Failed to load raster: ' + error.message;
      }
    },

    async loadVector(vectorId) {
      if (!this.mapInitialized) {
        await new Promise(resolve => {
          const checkInitialization = setInterval(() => {
            if (this.mapInitialized) {
              clearInterval(checkInitialization);
              resolve();
            }
          }, 100);
        });
      }

      if (this.vectorLayer) {
        this.map.removeLayer(this.vectorLayer);
      }

      try {
        const response = await fetch(`http://127.0.0.1:5000/get_vector/${vectorId}`);
        const geojsonObject = await response.json();

        const vectorSource = new VectorSource({
          features: new GeoJSON().readFeatures(geojsonObject, {
            featureProjection: 'EPSG:3857'
          })
        });

        this.vectorLayer = new VectorLayer({
          source: vectorSource
        });

        this.map.addLayer(this.vectorLayer);

        const extent = vectorSource.getExtent();
        this.map.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 1000 });
      } catch (error) {
        console.error('Error loading vector:', error);
        this.error = 'Failed to load vector: ' + error.message;
      }
    },
    initMap() {
      this.vectorLayer = new VectorLayer({
        source: new VectorSource(),
        zIndex: 1,
      });

      this.map = new Map({
        target: 'map',
        layers: [
          new TileLayer({
            source: new XYZ({
              url: 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            }),
          }),
          this.vectorLayer,
        ],
        view: new View({
          center: [0, 0],
          zoom: 2,
        }),
      });

      this.initInteractions();
    },
    initInteractions() {
      this.selectInteraction = new Select({
        condition: click,
      });

      this.modifyInteraction = new Modify({
        features: this.selectInteraction.getFeatures(),
      });

      this.map.addInteraction(this.selectInteraction);
      this.map.addInteraction(this.modifyInteraction);

      this.selectInteraction.on('select', (e) => {
        const selectedFeatures = e.selected;
        if (selectedFeatures.length > 0) {
          const feature = selectedFeatures[0];
          this.selectedPolygon = this.polygons.find(polygon => polygon.feature === feature);
        } else {
          this.selectedPolygon = null;
        }
      });
    },
    startDrawing() {
      this.drawing = true;
      this.classLabel = 'forest';

      if (!this.drawInteraction) {
        this.drawInteraction = new Draw({
          source: this.vectorLayer.getSource(),
          type: 'Polygon',
          freehand: true,
        });

        this.drawInteraction.on('drawend', (event) => {
          const feature = event.feature;
          feature.set('classLabel', this.classLabel);
          this.polygons.push({ feature, classLabel: this.classLabel });
          this.updatePolygonStyle(feature);
        });

        this.map.addInteraction(this.drawInteraction);
      }
    },
    stopDrawing() {
      if (this.drawInteraction) {
        this.map.removeInteraction(this.drawInteraction);
        this.drawInteraction = null;
        this.drawing = false;
      }
    },
    saveGeoJSON() {
      const features = this.vectorLayer.getSource().getFeatures();
      const geoJSON = new GeoJSON().writeFeaturesObject(features, {
        featureProjection: 'EPSG:3857'
      });
      const blob = new Blob([JSON.stringify(geoJSON, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'polygons.geojson';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    savePolygonsToLocalStorage() {
      const format = new GeoJSON();
      const features = this.vectorLayer.getSource().getFeatures();
      const transformedFeatures = features.map(feature => {
        const geom = feature.getGeometry();
        geom.transform('EPSG:3857', 'EPSG:4326');
        return feature;
      });
      const geojson = format.writeFeaturesObject(transformedFeatures);
      localStorage.setItem('polygons', JSON.stringify(geojson));
    },
    loadPolygonsFromLocalStorage() {
      const polygons = localStorage.getItem('polygons');
      if (polygons) {
        const format = new GeoJSON();
        const features = format.readFeatures(JSON.parse(polygons), {
          featureProjection: 'EPSG:3857',
        });

        this.vectorLayer.getSource().clear();

        this.vectorLayer.getSource().addFeatures(features);

        this.polygons = [];
        features.forEach(feature => {
          const classLabel = feature.get('classLabel') || 'unknown';
          this.polygons.push({ feature, classLabel });

          this.updatePolygonStyle(feature);
        });

        this.vectorLayer.setVisible(true);
      }
    },
    updatePolygonStyle(feature) {
      const classLabel = feature.get('classLabel');
      feature.setStyle(this.getStyleForClassLabel(classLabel));
    },
    getStyleForClassLabel(classLabel) {
      if (classLabel === 'forest') {
        return new Style({
          fill: new Fill({
            color: 'rgba(0, 128, 0, 0.5)',
          }),
          stroke: new Stroke({
            color: '#008000',
            width: 2,
          }),
        });
      } else if (classLabel === 'non-forest') {
        return new Style({
          fill: new Fill({
            color: 'rgba(255, 255, 0, 0.5)',
          }),
          stroke: new Stroke({
            color: '#FFFF00',
            width: 2,
          }),
        });
      }
    },
    handleKeyDown(event) {
      if (event.key === '1') {
        this.classLabel = 'forest';
      } else if (event.key === '2') {
        this.classLabel = 'non-forest';
      }
    },
    // Existing methods
    async extractPixels() {
      if (this.polygons.length === 0) {
        console.error('No polygons drawn.');
        return;
      }

      const formData = new FormData();
      formData.append('raster', this.rasterUrl);
      formData.append('polygons', JSON.stringify(this.polygons.map(polygon => ({
        geometry: new GeoJSON().writeFeatureObject(polygon.feature)
      }))));

      try {
        const response = await fetch('http://127.0.0.1:5000/extract_pixels', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Extracted Pixel Values:', data);
      } catch (error) {
        console.error('Error extracting pixels:', error);
      }
    },
  },
};
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 600px;
}
</style>
