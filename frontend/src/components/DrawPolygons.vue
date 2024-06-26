<template>
  <q-page>
    <div class="q-pa-md">
      <q-card>
        <q-card-section>
          <div class="text-h6">Land Use Classification Map</div>
          <div class="q-mt-md">
            <q-btn label="Upload GeoJSON" color="primary" @click="openFileDialog('geojson')" />
            <q-btn label="Upload Raster" color="primary" @click="openFileDialog('raster')" class="q-ml-md" />
            <q-btn label="Draw Polygon" color="primary" @click="startDrawing" class="q-ml-md" />
            <q-btn v-if="drawing" label="Stop Drawing" color="negative" @click="stopDrawing" class="q-ml-md" />
            <q-select v-if="drawing" v-model="classLabel" :options="classOptions" label="Class Label" class="q-ml-md" />
            <q-btn v-if="drawing" label="Save Label" color="primary" @click="saveLabel" class="q-ml-md" />
            <q-btn label="Save GeoJSON" color="primary" @click="saveGeoJSON" class="q-ml-md" />
            <q-btn label="Extract Pixels" color="primary" @click="extractPixels" class="q-ml-md" />
            <q-btn label="Save Polygons to Local Storage" color="primary" @click="savePolygonsToLocalStorage" class="q-ml-md" />
            <q-btn label="Load from Local Storage" color="primary" @click="loadPolygonsFromLocalStorage" class="q-ml-md" />
            <q-linear-progress v-if="uploading" :value="uploadProgress / 100" buffer-color="grey-5" color="primary" class="q-mt-md"></q-linear-progress>
          </div>
          <div class="q-mt-md row">
            <div class="col-3">
              <q-list>
                <q-item-label header>Drawn Polygons</q-item-label>
                <q-item v-for="(polygon, index) in polygons" :key="index" clickable @click="selectPolygon(polygon)">
                  <q-item-section>
                    <q-item-label><strong>Polygon {{ index + 1 }}</strong>: {{ polygon.classLabel }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-if="selectedPolygon">
                <q-item-label>Edit Polygon</q-item-label>
                <q-select v-model="selectedPolygon.classLabel" :options="classOptions" label="Class Label" @change="updatePolygonStyle(selectedPolygon.feature)" />
                <q-btn label="Delete Polygon" color="negative" @click="deletePolygon" class="q-mt-md" />
              </div>
            </div>
            <div class="col-9">
              <input type="file" ref="geojsonFileInput" @change="handleGeoJSONUpload" style="display: none;" />
              <input type="file" ref="rasterFileInput" @change="handleRasterUpload" style="display: none;" />
              <div id="map" class="map-container"></div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
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
      classOptions: [
        { label: 'Forest', value: 'forest' },
        { label: 'Non-Forest', value: 'non-forest' },
      ],
      polygons: [],
      selectedPolygon: null,
      uploading: false,
      uploadProgress: 0,
      defaultRasterPath: 'http://127.0.0.1:5000/data/568-1023_2023_04_scaled.tif',
    };
  },
  mounted() {
    this.initMap();
    window.addEventListener('keydown', this.handleKeyDown);
    this.loadDefaultRaster();
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
          interleave: true,
          samples: [0, 1, 2],
        });

        const width = image.getWidth();
        const height = image.getHeight();
        const bbox = image.getBoundingBox();

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

    this.vectorLayer.getSource().addFeatures(features);

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
    this.$q.notify({
      color: 'negative',
      position: 'top',
      message: 'Please select a class label.',
      icon: 'warning',
    });
    return;
  }
  this.$q.notify({
    color: 'positive',
    position: 'top',
    message: 'Class label saved. Now draw the polygon on the map.',
    icon: 'check_circle',
  });
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
saveGeoJSON() {
  const features = this.vectorLayer.getSource().getFeatures();
  const geoJSON = new GeoJSON().writeFeaturesObject(features, {
    featureProjection: 'EPSG:3857',
  });

  const blob = new Blob([JSON.stringify(geoJSON, null, 2)], {
    type: 'application/json',
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
    geometry: new GeoJSON().writeFeatureObject(polygon.feature),
  }))));

  try {
    const response = await fetch('http://127.0.0.1:5000/extract_pixels', {
      method: 'POST',
      body: formData,
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
},
};

</script>

<style scoped>
.map-container {
  width: 100%;
  height: 600px;
}
</style>
