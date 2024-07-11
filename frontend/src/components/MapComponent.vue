<template>
  <div class="map-container">
  <div ref="mapContainer" class="map"></div>
    <div class="map-controls">
      <q-btn label="Draw Polygon" color="primary" @click="startDrawing" />
      <q-btn :label="drawing ? 'Stop Drawing' : 'Start Drawing'" :color="drawing ? 'negative' : 'primary'"
        @click="toggleDrawing" class="q-ml-sm" />
      <q-select v-model="classLabel" :options="classOptions" label="Class Label" class="q-ml-md"
        style="width: 150px;" />
    </div>
  </div>
    <!-- <div class="map-and-sidebar">
      <div ref="mapContainer" class="map"></div>
      <div class="sidebar">
        <h6>Drawn Polygons</h6>
        <q-list>
          <q-item v-for="(polygon, index) in polygons" :key="index" clickable @click="selectPolygon(polygon)"
            :active="selectedPolygon === polygon" :class="{ 'bg-primary text-white': selectedPolygon === polygon }">
            <q-item-section>
              <q-item-label>{{ index + 1 }} - {{ polygon.get('classLabel') }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn flat round icon="delete" @click.stop="deletePolygon(polygon)" />
            </q-item-section>
          </q-item>
        </q-list>
      </div>
    </div> -->
</template>

<script>
import { ref, onMounted, watch, onBeforeUnmount, onUnmounted } from 'vue';
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
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
import { fromLonLat } from 'ol/proj';
import { fromUrl } from 'geotiff';
import apiService from 'src/services/api';
import { DragPan } from 'ol/interaction';
import { useTrainingStore } from '../stores/trainingStore';
import { storeToRefs } from 'pinia';




export default {
  name: 'MapComponent',
  emits: ['polygons-drawn'],
  setup(props, { emit }) {
    const mapContainer = ref(null);
    const map = ref(null);
    const rasterLayer = ref(null);
    const vectorLayer = ref(null);
    const drawInteraction = ref(null);
    const modifyInteraction = ref(null);
    const selectInteraction = ref(null);
    const drawing = ref(false);
    const classLabel = ref('forest');
    const polygons = ref([]);
    const selectedPolygon = ref(null);
    const classOptions = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non-forest' },
    ];
    const trainingStore = useTrainingStore();
    const { selectedRaster, selectedVector, drawnPolygons } = storeToRefs(trainingStore);


    onMounted(() => {
      initMap();
      window.addEventListener('keydown', handleKeyDown);
    });

    const initMap = () => {
      map.value = new Map({
        target: mapContainer.value,
        layers: [
          new TileLayer({
            source: new XYZ({
              url: 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png'
            }),
            zIndex: 0
          })
        ],
        view: new View({
          center: fromLonLat([0, 0]),
          zoom: 2
        })
      });

      vectorLayer.value = new VectorLayer({
        source: new VectorSource(),
        style: featureStyleFunction
      });

      map.value.addLayer(vectorLayer.value);

      initInteractions();

      // Load raster and vector layers if selected
      if (selectedRaster.value) {
        loadRaster(selectedRaster.value.id);
      }

      if (selectedVector.value) {
        loadVector(selectedVector.value.id);
      }

    };

    const initInteractions = () => {
      selectInteraction.value = new Select({
        condition: click,
        style: featureStyleFunction,
        zIndex: 1 // Ensure vector layer is on top
      });

      selectInteraction.value.on('select', (event) => {
        if (event.selected.length > 0) {
          selectPolygon(event.selected[0]);
        } else {
          selectedPolygon.value = null;
        }
        updateVectorLayerStyle();
      });

      modifyInteraction.value = new Modify({
        features: selectInteraction.value.getFeatures()
      });

      map.value.addInteraction(selectInteraction.value);
      map.value.addInteraction(modifyInteraction.value);
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

    const updateVectorLayerStyle = () => {
      vectorLayer.value.setStyle(featureStyleFunction);
      vectorLayer.value.changed();
    };

    const startDrawing = () => {
      drawing.value = true;
      map.value.getInteractions().forEach((interaction) => {
        if (interaction instanceof DragPan) {
          interaction.setActive(false);
        }
      });

      drawInteraction.value = new Draw({
        source: vectorLayer.value.getSource(),
        type: 'Polygon',
        freehand: true
      });

      drawInteraction.value.on('drawend', (event) => {
        const feature = event.feature;
        feature.set('classLabel', classLabel.value);
        polygons.value.push(feature);
        updateVectorLayerStyle();
        emit('polygons-drawn', polygons.value);

        map.value.getInteractions().forEach((interaction) => {
          if (interaction instanceof DragPan) {
            interaction.setActive(true);
          }
        });

        // Don't stop drawing automatically, allow continuous drawing
        // stopDrawing();
      });

      map.value.addInteraction(drawInteraction.value);
    };


    const toggleDrawing = () => {
      if (drawing.value) {
        stopDrawing();
      } else {
        startDrawing();
      }
    };

    const stopDrawing = () => {
      if (drawInteraction.value) {
        map.value.removeInteraction(drawInteraction.value);
        drawInteraction.value = null;
      }
      map.value.getInteractions().forEach((interaction) => {
        if (interaction instanceof DragPan) {
          interaction.setActive(true);
        }
      });
      drawing.value = false;
    };


    const selectPolygon = (polygon) => {
      selectedPolygon.value = polygon;
      updateVectorLayerStyle();
    };

    const deletePolygon = (polygon) => {
      vectorLayer.value.getSource().removeFeature(polygon);
      polygons.value = polygons.value.filter(p => p !== polygon);
      if (selectedPolygon.value === polygon) {
        selectedPolygon.value = null;
      }
      updateVectorLayerStyle();
      emit('polygons-drawn', polygons.value);
    };

    const handleKeyDown = (event) => {
      if (event.key === '1') {
        classLabel.value = 'forest';
      } else if (event.key === '2') {
        classLabel.value = 'non-forest';
      } else if (event.key === 'Delete' && selectedPolygon.value) {
        deletePolygon(selectedPolygon.value);
      } else if (event.key === ' ' && !event.repeat) {
        event.preventDefault();
        toggleDrawing();
      }
    };

    const loadRaster = async (id) => {
      console.log('Loading raster:', id);
      if (!id) return;
      try {
        const response = await apiService.fetchRasterById(id);
        console.log('Raster data:', response.filepath);
        const url = `http://127.0.0.1:5000/${response.filepath}`;
        const tiff = await fromUrl(url);
        const image = await tiff.getImage();
        const bbox = image.getBoundingBox();
        const width = image.getWidth();
        const height = image.getHeight();

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
          zIndex: 0  // Place raster layer between base map and vector layer
        });

        rasterLayer.value.getSource().on('imageloaderror', () => {
          console.error('Error loading raster image:', url);
          error.value = 'Failed to load raster image';
        });

        map.value.addLayer(rasterLayer.value);
        bringVectorToFront(); // Ensure vector layer is on top
        map.value.getView().fit(extent, { duration: 1000 });
      } catch (error) {
        console.error('Error loading raster:', error);
        error.value = 'Failed to load raster: ' + error.message;
      }
    };

    const loadVector = async (id) => {
      if (!id) return;
      try {
        const vectorData = await apiService.fetchVectorById(id);
        const vectorSource = new VectorSource({
          features: new GeoJSON().readFeatures(vectorData.geojson, {
            featureProjection: 'EPSG:3857'
          })
        });

        vectorLayer.value.setSource(vectorSource);
        const extent = vectorSource.getExtent();
        map.value.getView().fit(extent, { padding: [20, 20, 20, 20] });

        polygons.value = vectorSource.getFeatures();
        updateVectorLayerStyle();
        emit('polygons-drawn', polygons.value);
      } catch (error) {
        console.error('Error loading vector:', error);
      }
    };
    const bringVectorToFront = () => {
      if (vectorLayer.value && map.value) {
        map.value.removeLayer(vectorLayer.value);
        map.value.addLayer(vectorLayer.value);
      }
    };

    watch(selectedRaster, (newRaster) => {
      loadRaster(newRaster);
    });

    watch(selectedVector, (newVector) => {
      loadVector(newVector);
    });

    onBeforeUnmount(() => {
      if (map.value) {
        map.value.setTarget(null);
      }
    });

    onUnmounted(() => {
      window.removeEventListener('keydown', handleKeyDown);
    });

    return {
      mapContainer,
      drawing,
      classLabel,
      classOptions,
      polygons,
      selectedPolygon,
      startDrawing,
      toggleDrawing,
      selectPolygon,
      deletePolygon,
      bringVectorToFront
    };
  }
};
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 600px;
  position: relative;
}
.map {
  width: 100%;
  height: 100%;
}
.map-controls {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1000;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 10px;
  border-radius: 4px;
}

.q-item.bg-primary {
  background-color: #1976D2 !important;
}
</style>