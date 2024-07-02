<template>
  <div class="map-container">
    <div class="toolbar">
      <q-btn label="Draw Polygon" color="primary" @click="startDrawing" />
      <q-btn :label="drawing ? 'Stop Drawing' : 'Start Drawing'" :color="drawing ? 'negative' : 'primary'"
        @click="toggleDrawing" />
      <q-select v-model="classLabel" :options="classOptions" label="Class Label" class="q-ml-md" />
      <q-input v-model="description" :label="`Description`" class="q-mt-md" />
      <q-btn label="Save Training polygons" color="primary" @click="saveDrawnPolygons" class="q-ml-md" />
      <q-btn label="Extract Pixel Information" color="secondary" @click="extractPixels" />
    </div>
    <div class="map-and-sidebar">
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
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, onBeforeUnmount, onUnmounted } from 'vue';
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
import axios from 'axios';
import apiService from '../services/api';





export default {
  name: 'MapComponent',
  props: {
    rasterId: {
      type: String,
      required: true
    },
    polygonSetId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const mapContainer = ref(null);
    const map = ref(null);
    const error = ref(null);
    const mapInitialized = ref(false);
    const rasterLayer = ref(null);
    const vectorLayer = ref(null);
    const drawInteraction = ref(null);
    const modifyInteraction = ref(null);
    const selectInteraction = ref(null);
    const drawing = ref(false);
    const classLabel = ref('forest');
    const polygons = ref([]);
    const description = ref(null);
    const classOptions = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non-forest' },
    ];
    const selectedPolygon = ref(null);



    const initMap = () => {
      if (mapContainer.value) {
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
        loadRaster(props.rasterId);
        loadPolygons(props.polygonSetId);
        mapInitialized.value = true;
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
      console.log("Updating vector styles..");
      vectorLayer.value.setStyle(featureStyleFunction);
      vectorLayer.value.changed();
    };


    const startDrawing = () => {

      drawing.value = true;
      drawInteraction.value = new Draw({
        source: vectorLayer.value.getSource(),
        type: 'Polygon',
        freehand: true,
      });

      drawInteraction.value.on('drawend', (event) => {
        const feature = event.feature;
        feature.set('classLabel', classLabel.value);
        polygons.value.push(feature);
        bringVectorToFront(); // Ensure vector layer is on top after drawing
        updateVectorLayerStyle();
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
      map.value.removeInteraction(drawInteraction.value);
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
      vectorLayer.value.changed(); // Ensure the vector layer updates
    };

    const saveDrawnPolygons = async () => {
      console.log('Saving polygon to database:');
      const features = vectorLayer.value.getSource().getFeatures();
      const polygonsData = features.map(feature => {
        // Clone the geometry to avoid modifying the original
        const geometry = feature.getGeometry().clone();

        // Transform the geometry from EPSG:3857 to EPSG:4326
        geometry.transform('EPSG:3857', 'EPSG:4326');

        return {
          classLabel: feature.get('classLabel'),
          geometry: new GeoJSON().writeGeometryObject(geometry)
        };
      });

      try {
        const response = await axios.post('http://127.0.0.1:5000/api/save_drawn_polygons', {
          description: description.value,
          polygons: polygonsData
        });
        console.log('Polygons saved successfully:', response.data);
        // Optionally, update UI to reflect successful save
      } catch (error) {
        console.error('Error saving polygons:', error);
        // Handle error (e.g., show error message to user)
      }
    };

    const bringVectorToFront = () => {
      if (vectorLayer.value && map.value) {
        map.value.removeLayer(vectorLayer.value);
        map.value.addLayer(vectorLayer.value);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === '1') {
        classLabel.value = 'forest';
      } else if (event.key === '2') {
        classLabel.value = 'non-forest';
      } else if (event.key === 'Delete' && selectedPolygon.value) {
        deletePolygon(selectedPolygon.value);
      } else if (event.key === ' ' && !event.repeat) { // Spacebar for toggle drawing
        event.preventDefault(); // Prevent page scrolling
        toggleDrawing();
      }
    };

    const loadRaster = async (id) => {
      console.log('Loading raster by id:', id);
      error.value = null;

      // Get raster URL by id
      const rasters = await apiService.fetchRasters();
      const rastersData = rasters.data;
      const raster = rastersData.find(r => r.id === parseInt(id, 10)); // Need to convert to integer

      if (raster) {
        const filepath = raster.filepath;
        const url = `http://127.0.0.1:5000/${filepath}`;

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
      } else {
        console.error('Raster not found');
        error.value = 'Failed to load raster: Raster not found';
      }



    };

    const loadPolygons = async (vectorId) => {
      console.log('Loading vector by id:', vectorId);
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
          source: vectorSource,
          style: featureStyleFunction
        });

        map.value.addLayer(vectorLayer.value);

        const extent = vectorSource.getExtent();
        map.value.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 1000 });

        // Add to sidebar
        polygons.value = vectorSource.getFeatures();

      } catch (error) {
        console.error('Error loading vector:', error);
        error.value = 'Failed to load vector: ' + error.message;
      }
    };

    const extractPixels = async () => {
      if (polygons.value.length === 0) {
        console.error('No polygons drawn.');
        return;
      }

      try {

        const polygonsData = polygons.value.map(polygon => ({
          geometry: new GeoJSON().writeFeatureObject(polygon),
          properties: {
            classLabel: polygon.get('classLabel')
          }
        }));

        const response = await apiService.extractPixels({
          rasterId: props.rasterId,
          polygons: polygonsData
        },);

        console.log('Extracted Pixel Values:', response.data);
        // Here you can handle the extracted pixel data, e.g., display it or store it
      } catch (error) {
        console.error('Error extracting pixels:', error);
        // Handle error (e.g., show error message to user)
      }
    };

    onMounted(() => {
      initMap();
      window.addEventListener('keydown', handleKeyDown);
    });

    // Watch for changes in the rasterId prop
    watch(() => props.rasterId, (newRaster) => {
      if (newRaster) {
        loadRaster(id);
      }
    });

    // Watch for changes in the selectedVector prop
    watch(() => props.selectedVector, (newVector) => {
      if (newVector && newVector.id) {
        loadPolygons(newVector.id);
      }
    });

    onBeforeUnmount(() => {
      if (map.value) {
        map.value.setTarget(null);
        map.value = null;
      }
    });

    onUnmounted(() => {
      window.removeEventListener('keydown', handleKeyDown);
    });

    return {
      mapContainer,
      loadRaster,
      error,
      map,
      rasterLayer,
      loadPolygons,
      vectorLayer,
      mapInitialized,
      drawing,
      classLabel,
      classOptions,
      polygons,
      startDrawing,
      stopDrawing,
      selectPolygon,
      deletePolygon,
      bringVectorToFront,
      saveDrawnPolygons,
      description,
      selectedPolygon,
      toggleDrawing,
      extractPixels
    };
  }
};
</script>

<style scoped>
.map-container {
  height: 100vh;
  /* This will make the map container take the full viewport height */
  display: flex;
  flex-direction: column;
}

.map-and-sidebar {
  display: flex;
  flex-grow: 1;
}

.map {
  flex-grow: 1;
  min-height: 800px;
  /* This sets a minimum height for the map */
}

.sidebar {
  width: 250px;
  padding: 10px;
  background-color: #f0f0f0;
  overflow-y: auto;
}

.toolbar {
  padding: 10px;
  background-color: #e0e0e0;
}

.q-item.bg-primary {
  background-color: #1976D2 !important;
}
</style>
