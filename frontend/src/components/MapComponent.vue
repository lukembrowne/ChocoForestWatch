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

    const initMap = () => {
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
    };

    const loadRaster = (raster) => {
      // Implement raster loading logic here
      console.log('Loading raster:', raster);
    };

    const loadVector = (vector) => {
      // Implement vector loading logic here
      console.log('Loading vector:', vector);
    };

    onMounted(() => {
      initMap();
    });

    watch(() => props.selectedRaster, (newRaster) => {
      if (newRaster) {
        loadRaster(newRaster);
      }
    });

    watch(() => props.selectedVector, (newVector) => {
      if (newVector) {
        loadVector(newVector);
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
      error
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
