<template>
  <div>
    <div class="toolbar">
      <q-btn label="Draw Polygon" color="primary" @click="startDrawing" />
      <q-btn v-if="drawing" label="Stop Drawing" color="negative" @click="stopDrawing" class="q-ml-md" />
      <q-select v-if="drawing" v-model="classLabel" :options="classOptions" label="Class Label" class="q-ml-md" />
      <q-btn label="Save GeoJSON" color="primary" @click="saveGeoJSON" class="q-ml-md" />
      <q-btn label="Extract Pixels" color="primary" @click="extractPixels" class="q-ml-md" />
    </div>
    <div class="map-container" ref="mapContainer"></div>
    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
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
  setup(props) {
    const mapContainer = ref(null);
    const map = ref(null);
    const error = ref(null);
    const mapInitialized = ref(false);
    const rasterLayer = ref(null);
    const vectorLayer = ref(null);




    const initMap = () => {
      if (mapContainer.value) {
        map.value = new Map({
          target: mapContainer.value,
          layers: [
            new TileLayer({
              source: new XYZ({
                url: 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png'
              })
            })
          ],
          view: new View({
            center: fromLonLat([0, 0]),
            zoom: 2
          })
        });
        mapInitialized.value = true;
      }
    };

    const loadRaster = async (url) => {
      console.log('Loading raster:', url);
      error.value = null;

      if (!mapInitialized.value) {
        console.log('Map not initialized yet, waiting...');
        await new Promise(resolve => {
          const checkInitialization = setInterval(() => {
            if (mapInitialized.value) {
              clearInterval(checkInitialization);
              resolve();
            }
          }, 100);
        });
      }

      if (rasterLayer.value) {
        map.value.removeLayer(rasterLayer.value);
      }

      if (!url) {
        error.value = 'Invalid raster URL';
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

        rasterLayer.value = new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            imageExtent: extent,
          }),
        });

        rasterLayer.value.getSource().on('imageloaderror', () => {
          console.error('Error loading raster image:', url);
          error.value = 'Failed to load raster image';
        });

        map.value.addLayer(rasterLayer.value);

        map.value.getView().fit(extent, { duration: 1000 });
      } catch (error) {
        console.error('Error loading raster:', error);
        error.value = 'Failed to load raster: ' + error.message;
      }
    };

    const loadVector = async (vectorId) => {
      if (!mapInitialized.value) {
        await new Promise(resolve => {
          const checkInitialization = setInterval(() => {
            if (mapInitialized.value) {
              clearInterval(checkInitialization);
              resolve();
            }
          }, 100);
        });
      }

      if (vectorLayer.value) {
        map.value.removeLayer(vectorLayer.value);
      }

      try {
        const response = await fetch(`http://127.0.0.1:5000/api/get_vector/${vectorId}`);
        const geojsonObject = await response.json();

        const vectorSource = new VectorSource({
          features: new GeoJSON().readFeatures(geojsonObject, {
            featureProjection: 'EPSG:3857'
          })
        });

        vectorLayer.value = new VectorLayer({
          source: vectorSource
        });

        map.value.addLayer(vectorLayer.value);

        const extent = vectorSource.getExtent();
        map.value.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 1000 });
      } catch (error) {
        console.error('Error loading vector:', error);
        error.value = 'Failed to load vector: ' + error.message;
      }
    };

    onMounted(() => {
      initMap();
    });

    // Watch for changes in the selectedRaster prop
    watch(() => props.selectedRaster, (newRaster) => {
      if (newRaster && newRaster.filename) {
        const url = `http://127.0.0.1:5000/rasters/${newRaster.filename}`;
        loadRaster(url);
      }
    });

    // Watch for changes in the selectedVector prop
    watch(() => props.selectedVector, (newVector) => {
      if (newVector && newVector.id) {
        loadVector(newVector.id);
      }
    });

    onBeforeUnmount(() => {
      if (map.value) {
        map.value.setTarget(null);
        map.value = null;
      }
    });

    return {
      mapContainer,
      loadRaster,
      error,
      map,
      rasterLayer,
      loadVector,
      vectorLayer,
      mapInitialized
    };
  }
};
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 600px;
}

.error-message {
  color: red;
  margin-top: 10px;
}
</style>
