<template>
  <div class="app-container">
    <div class="toolbar">
      <button @click="openFileDialog('geojson')">Upload GeoJSON</button>
      <button @click="openFileDialog('raster')">Upload Raster</button>
      <button @click="startDrawing">Draw Polygon</button>
      <button v-if="drawing" @click="stopDrawing">Stop Drawing</button>
      <div v-if="drawing" class="label-input">
        <label for="classLabel">Class Label:</label>
        <select v-model="classLabel">
          <option value="forest">Forest</option>
          <option value="non-forest">Non-Forest</option>
        </select>
        <button @click="saveLabel">Save Label</button>
      </div>
      <button @click="saveGeoJSON">Save GeoJSON</button>
      <button @click="extractPixels">Extract Pixels</button>
      <button @click="savePolygonsToLocalStorage">Save Polygons to Local Storage</button>
      <button @click="loadPolygonsFromLocalStorage">Load from Local Storage</button>

      <progress v-if="uploading" :value="uploadProgress" max="100"></progress>
    </div>
    <div class="content">
      <div class="sidebar">
        <h2>Drawn Polygons</h2>
        <ul>
          <li v-for="(polygon, index) in polygons" :key="index" @click="selectPolygon(polygon)">
            <strong>Polygon {{ index + 1 }}</strong>: {{ polygon.classLabel }}
          </li>
        </ul>
        <div v-if="selectedPolygon">
          <h3>Edit Polygon</h3>
          <label for="editClassLabel">Class Label:</label>
          <select v-model="selectedPolygon.classLabel" @change="updatePolygonStyle(selectedPolygon.feature)">
            <option value="forest">Forest</option>
            <option value="non-forest">Non-Forest</option>
          </select>
          <button @click="deletePolygon">Delete Polygon</button>
        </div>
      </div>
      <div class="map-container">
        <input type="file" ref="geojsonFileInput" @change="handleGeoJSONUpload" style="display: none;" />
        <input type="file" ref="rasterFileInput" @change="handleRasterUpload" style="display: none;" />
        <div id="map" class="map"></div>
      </div>
    </div>
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
import { fromArrayBuffer } from 'geotiff';

export default {
  name: 'MapComponent',
  data() {
    return {
      map: null,
      vectorLayer: null,
      rasterLayer: null,
      drawInteraction: null,
      modifyInteraction: null,
      selectInteraction: null,
      drawing: false,
      classLabel: 'forest',
      polygons: [],
      selectedPolygon: null,
      uploading: false,
      uploadProgress: 0,
      defaultRasterPath: 'http://127.0.0.1:5000/data/568-1023_2023_04_scaled.tif' // Set the default raster file path here

    };
  },
  mounted() {
    this.initMap();
    window.addEventListener('keydown', this.handleKeyDown);
    this.loadDefaultRaster(); // Load the default raster on mount

  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleKeyDown);
  },
  methods: {
    openFileDialog(type) {
      if (type === 'geojson') {
        this.$refs.geojsonFileInput.click();
      } else if (type === 'raster') {
        this.$refs.rasterFileInput.click();
      }
    },
    handleGeoJSONUpload(event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const geojsonObject = JSON.parse(e.target.result);
          this.addGeoJSONToMap(geojsonObject);
          this.updateSidebarWithGeoJSON(geojsonObject);
        };
        reader.readAsText(file);
      }
    },
    async loadDefaultRaster() {
      try {
        const response = await fetch(this.defaultRasterPath);
        const arrayBuffer = await response.arrayBuffer();
        await this.processRaster(arrayBuffer);
        console.log('Default raster loaded.');
      } catch (error) {
        console.error('Error loading default raster:', error);
      }
    },
    async handleRasterUpload(event) {
      const file = event.target.files[0];
      if (file) {
        this.uploading = true;
        this.uploadProgress = 0;

        const reader = new FileReader();
        reader.onprogress = (e) => {
          if (e.lengthComputable) {
            this.uploadProgress = (e.loaded / e.total) * 100;
          }
        };
        reader.onload = async (e) => {
          const arrayBuffer = e.target.result;
          await this.processRaster(arrayBuffer);
          this.uploading = false;
        };
        reader.readAsArrayBuffer(file);
      }
    },
    async processRaster(arrayBuffer) {
      try {
        const tiff = await fromArrayBuffer(arrayBuffer);
        const image = await tiff.getImage();
        const rasterData = await image.readRasters({
          interleave: true, // Interleave the data for easier access
          samples: [0, 1, 2] // Only read the first three bands (RGB)
        });

        const width = image.getWidth();
        const height = image.getHeight();
        const bbox = image.getBoundingBox();

        // Create a canvas to draw the raster data
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d');

        const imageData = context.createImageData(width, height);
        const data = imageData.data;

        for (let i = 0; i < width * height; i++) {
          data[i * 4] = rasterData[i * 3];       // Red
          data[i * 4 + 1] = rasterData[i * 3 + 1];   // Green
          data[i * 4 + 2] = rasterData[i * 3 + 2];   // Blue
          data[i * 4 + 3] = 255;                // Alpha
        }
        context.putImageData(imageData, 0, 0);

        const imageUrl = canvas.toDataURL();
        const extent = [bbox[0], bbox[1], bbox[2], bbox[3]];

        if (this.rasterLayer) {
          this.map.removeLayer(this.rasterLayer);
        }

        this.rasterLayer = new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            imageExtent: extent,
            projection: this.map.getView().getProjection(),
          }),
        });

        // Add raster layer with lower z-index
        this.rasterLayer.setZIndex(0);
        this.vectorLayer.setZIndex(1);

        this.map.addLayer(this.rasterLayer);

        this.map.getView().fit(extent, { duration: 1000 });
      } catch (error) {
        console.error('Error processing GeoTIFF:', error);
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

      // Log to ensure the map and layers are initialized
      console.log('Map initialized:', this.map);
      console.log('Vector layer initialized:', this.vectorLayer);

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
    addGeoJSONToMap(geojsonObject) {
      if (this.map && this.vectorLayer) {
        const format = new GeoJSON();
        const features = format.readFeatures(geojsonObject, {
          featureProjection: 'EPSG:3857',
        });

        // Clear existing features and add new ones
        this.vectorLayer.getSource().addFeatures(features);

        // Fit the map view to the extent of the new features
        const extent = this.vectorLayer.getSource().getExtent();
        this.map.getView().fit(extent, { duration: 1000 });
      } else {
        console.error('Map or vector layer not initialized');
      }
    },

    updateSidebarWithGeoJSON(geojsonObject) {
      const format = new GeoJSON();
      const features = format.readFeatures(geojsonObject, {
        featureProjection: 'EPSG:3857',
      });
      features.forEach((feature) => {
        const classLabel = feature.get('classLabel') || 'unknown';
        this.polygons.push({ feature, classLabel });
      });
    },


    addRasterToMap(imageUrl) {
      if (this.map) {
        const extent = this.map.getView().calculateExtent(this.map.getSize());
        if (this.rasterLayer) {
          this.map.removeLayer(this.rasterLayer);
        }
        this.rasterLayer = new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            imageExtent: extent,
          }),
        });
        this.map.addLayer(this.rasterLayer);
        this.map.getView().fit(extent, { duration: 1000 });
      } else {
        console.error('Map not initialized');
      }
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
    saveLabel() {
      if (this.classLabel.trim() === '') {
        alert('Please select a class label.');
        return;
      }
      alert('Class label saved. Now draw the polygon on the map.');
    },
    selectPolygon(polygon) {
      this.selectedPolygon = polygon;
      this.selectInteraction.getFeatures().clear();
      this.selectInteraction.getFeatures().push(polygon.feature);
    },
    deletePolygon() {
      if (this.selectedPolygon) {
        this.vectorLayer.getSource().removeFeature(this.selectedPolygon.feature);
        this.polygons = this.polygons.filter(polygon => polygon !== this.selectedPolygon);
        this.selectedPolygon = null;
        this.savePolygonsToLocalStorage();
      }
    },
    updatePolygonStyle(feature) {
      const classLabel = feature.get('classLabel');
      feature.setStyle(this.getStyleForClassLabel(classLabel));
    },
    getStyleFunction() {
      return (feature) => this.getStyleForClassLabel(feature.get('classLabel'));
    },
    getStyleForClassLabel(classLabel) {
      if (classLabel === 'forest') {
        return new Style({
          fill: new Fill({
            color: 'rgba(0, 128, 0, 0.5)', // Green
          }),
          stroke: new Stroke({
            color: '#008000',
            width: 2,
          }),
        });
      } else if (classLabel === 'non-forest') {
        return new Style({
          fill: new Fill({
            color: 'rgba(255, 255, 0, 0.5)', // Yellow
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
    async extractPixels() {
      const formData = new FormData();
      formData.append('raster', this.$refs.rasterFileInput.files[0]);
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
    savePolygonsToLocalStorage() {
      const format = new GeoJSON();
      const features = this.vectorLayer.getSource().getFeatures();
      const transformedFeatures = features.map(feature => {
        const geom = feature.getGeometry();
        geom.transform('EPSG:3857', 'EPSG:4326'); // Transform to lat/long
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

        // Clear the existing features
        this.vectorLayer.getSource().clear();

        // Add the loaded features
        this.vectorLayer.getSource().addFeatures(features);

        // Log vectorLayer source features
        console.log('Features in vectorLayer after loading:', this.vectorLayer.getSource().getFeatures());

        // Clear and update the polygons array
        this.polygons = [];
        features.forEach(feature => {
          const classLabel = feature.get('classLabel') || 'unknown';
          this.polygons.push({ feature, classLabel });

          // Ensure the style is applied correctly
          this.updatePolygonStyle(feature);
        });

        // Log the current features with styles applied
        console.log('Polygons array:', this.polygons);

        // Ensure the vector layer is visible
        this.vectorLayer.setVisible(true);

        // alert('Polygons loaded from local storage.');
      } else {
        // alert('No polygons found in local storage.');
      }
    },
  },
};
</script>

<style>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.toolbar {
  display: flex;
  padding: 10px;
  background-color: #f4f4f4;
  border-bottom: 1px solid;
}

.content {
  display: flex;
  flex: 1;
}

.sidebar {
  width: 250px;
  padding: 10px;
  background-color: #f4f4f4;
  overflow-y: auto;
}

.sidebar h2 {
  margin-top: 0;
}

.sidebar ul {
  list-style-type: none;
  padding: 0;
}

.sidebar li {
  margin: 5px 0;
  cursor: pointer;
}

.sidebar li:hover {
  background-color: #ddd;
}

.sidebar h3 {
  margin-bottom: 0;
}

.map-container {
  flex: 1;
  position: relative;
}

.map-container .label-input {
  position: absolute;
  top: 50px;
  left: 10px;
  z-index: 1;
  background-color: white;
  padding: 10px;
  border: 1px solid #ccc;
}

.map {
  width: 100%;
  height: 100%;
}
</style>