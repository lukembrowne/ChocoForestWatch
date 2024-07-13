<template>
  <q-page class="row">
    <q-drawer v-model="leftDrawerOpen" show-if-above :width="300" :breakpoint="400" bordered class="bg-grey-3">
      <q-scroll-area class="fit">
        <q-list>
          <q-item-label header>Instructions</q-item-label>
          <q-item>
            <q-item-section>
              <ol>
                <li>Choose a class from the dropdown below.</li>
                <li>Click the "Draw Polygon" button to start drawing.</li>
                <li>Click on the map to add points to your polygon.</li>
                <li>Double-click to finish drawing the polygon.</li>
                <li>Repeat for different classes as needed.</li>
              </ol>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section>
              <q-select v-model="classLabel" :options="classOptions" label="Class" />
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section>
              <q-btn label="Draw Polygon" color="primary" @click="startDrawing" class="full-width" />
            </q-item-section>
          </q-item>

          <q-item-label header>Load Saved Polygons</q-item-label>
          <q-item>
            <q-item-section>
              <q-select v-model="selectedSavedPolygons" :options="savedPolygonsOptions" label="Saved Polygons"
                @update:model-value="loadSavedPolygons" />
            </q-item-section>
          </q-item>

          <q-item-label header>Select Basemap Date</q-item-label>
          <q-item>
            <q-item-section>
              <q-select v-model="selectedBasemapDate" :options="basemapDateOptions" label="Basemap Date"
                @update:model-value="updateBasemap" />
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section>
              <q-btn label="Save Polygons" color="positive" @click="saveDrawnPolygons" class="full-width q-mt-md" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <div class="col">
      <div class="map-container" style="height: calc(100vh - 50px);">
        <BaseMapComponent ref="baseMap" @map-ready="onMapReady" @basemap-error="handleBasemapError"
          :basemapDate="selectedBasemapDate" class="full-height full-width" />
      </div>
    </div>

    <q-dialog v-model="showErrorDialog">
      <q-card>
        <q-card-section>
          <div class="text-h6">Error</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          {{ errorMessage }}
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="OK" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useDrawing } from '../composables/useDrawing';
import BaseMapComponent from 'components/BaseMapComponent.vue'
import { Draw } from 'ol/interaction'
import VectorSource from 'ol/source/Vector'
import VectorLayer from 'ol/layer/Vector'
import { GeoJSON } from 'ol/format'
import apiService from 'src/services/api'
import { Style, Fill, Stroke } from 'ol/style';
import Feature from 'ol/Feature';


export default {
  name: 'TrainingPage',
  components: {
    BaseMapComponent
  },
  setup() {
    const route = useRoute()
    const projectStore = useProjectStore()
    const baseMap = ref(null)
    const project = ref({})
    const trainingPolygons = ref([])
    const classLabel = ref('forest');
    const leftDrawerOpen = ref(true)
    const selectedSavedPolygons = ref(null)
    const selectedBasemapDate = ref(null)
    const $q = useQuasar()
    const showErrorDialog = ref(false)
    const errorMessage = ref('')

    // Define vector layers
    const aoiLayer = ref(null);
    const trainingLayer = ref(null);

    const classOptions = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non_forest' },
    ]

    const savedPolygonsOptions = ref([])

    const basemapDateOptions = computed(() => {
      const options = []
      for (let year = 2022; year <= 2024; year++) {
        for (let month = 1; month <= 12; month++) {
          if (year === 2024 && month > 1) break
          const date = new Date(year, month - 1)
          options.push({
            label: date.toLocaleString('default', { month: 'long', year: 'numeric' }),
            value: `${year}-${month.toString().padStart(2, '0')}`
          })
        }
      }
      return options
    })

    const {
      drawing,
      polygons,
      startDrawing,
      stopDrawing,
      getDrawnPolygonsGeoJSON,
      setClassLabel
    } = useDrawing(baseMap);

    const toggleDrawing = () => {
      if (drawing.value) {
        stopDrawing();
      } else {
        startDrawing();
      }
    };

    onMounted(async () => {
      const projectId = route.params.projectId
      // project.value = await projectStore.loadProject(projectId)
      const vectorResponse = await apiService.fetchVectors();
      trainingPolygons.value = vectorResponse.data;

      window.addEventListener('keydown', handleKeyDown);

    })

    const onMapReady = (map) => {
      /// Initialize vector layer for AOI
      const aoiSource = new VectorSource();
      aoiLayer.value = new VectorLayer({
        source: aoiSource,
        style: new Style({
          fill: new Fill({
            color: 'rgba(0, 0, 0, 0.1)',
          }),
          stroke: new Stroke({
            color: 'black',
            width: 2,
          }),
        }),
      });
      map.addLayer(aoiLayer.value);

      // Initialize vector layer for training polygons
      const trainingSource = new VectorSource();
      trainingLayer.value = new VectorLayer({
        source: trainingSource,
        style: new Style({
          fill: new Fill({
            color: 'rgba(255, 255, 255, 0.2)',
          }),
          stroke: new Stroke({
            color: '#ffcc33',
            width: 2,
          }),
        }),
      });
      map.addLayer(trainingLayer.value);

      // Set view to project AOI and display it
      if (projectStore.aoi) {
        try {
          // Convert geometry to feature
          const aoiFeature = new Feature({
            geometry: projectStore.aoi
          });
          aoiLayer.value.getSource().addFeature(aoiFeature);

          const extent = projectStore.aoi.getExtent();
          map.getView().fit(extent, { padding: [50, 50, 50, 50] });
        } catch (error) {
          console.error('Error getting AOI extent:', error);
        }
      }
    }


    const handleKeyDown = (event) => {
      if (event.key === '1') {
        console.log('Setting class label to forest');
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


    const saveDrawnPolygons = async () => {
      try {
        const geoJSONFormat = new GeoJSON();
        const features = drawnPolygons.value.map(polygon => {
          const feature = geoJSONFormat.writeFeatureObject(polygon, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          return {
            type: 'Feature',
            geometry: feature.geometry,
            properties: {
              classLabel: polygon.get('classLabel')
            }
          };
        });

        const response = await apiService.saveDrawnPolygons({
          description: 'Drawn training polygons',
          polygons: features
        });

        trainingPolygons.value.push(response.data);
        trainingStore.setSelectedVector(response.data);

        $q.notify({
          type: 'positive',
          message: 'Polygons saved successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error saving drawn polygons:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to save drawn polygons',
          icon: 'error'
        });
      }
    };


    const fetchSavedPolygons = async () => {
      try {
        const response = await apiService.getSavedPolygonSets(project.value.id)
        savedPolygonsOptions.value = response.data.map(set => ({
          label: set.name,
          value: set.id
        }))
      } catch (error) {
        console.error('Error fetching saved polygon sets:', error)
      }
    }

    const loadSavedPolygons = async () => {
      if (!selectedSavedPolygons.value) return
      try {
        const response = await apiService.getPolygonSet(selectedSavedPolygons.value)
        // Clear existing polygons
        const vectorSource = baseMap.value.map.getLayers().getArray().find(layer => layer instanceof VectorLayer).getSource()
        vectorSource.clear()
        // Add loaded polygons to the map
        response.data.polygons.forEach(polygon => {
          const feature = new GeoJSON().readFeature(polygon.geometry)
          feature.set('class', polygon.class)
          vectorSource.addFeature(feature)
        })
        // Update trainingPolygons ref
        trainingPolygons.value = response.data.polygons.map(p => ({
          id: p.id,
          feature: new GeoJSON().readFeature(p.geometry),
          class: p.class
        }))
      } catch (error) {
        console.error('Error loading saved polygons:', error)
      }
    }

    const handleBasemapError = (error) => {
      errorMessage.value = error;
      showErrorDialog.value = true;
    }

    const updateBasemap = () => {
      if (!selectedBasemapDate.value || !baseMap.value) return;
      // Show loading indicator
      // $q.loading.show({
      //   message: 'Loading basemap...'
      // });
      // Force the BaseMapComponent to update
      // baseMap.value = null;
      // nextTick(() => {
      //   baseMap.value = baseMap.value;
      //   // Hide loading indicator after a short delay
      //   setTimeout(() => {
      //     $q.loading.hide();
      //   }, 500);
      // });
    };

    const extractPixels = async () => {
      extractingPixels.value = true;
      try {
        const polygonsToUse = selectedVector.value
          ? selectedVector.value.geojson.features
          : drawnPolygons.value;

        const response = await apiService.extractPixels({
          rasterId: selectedRaster.value.id,
          polygons: polygonsToUse
        });

        pixelsExtracted.value = true;
        pixelDatasetId.value = response.data.pixel_dataset_id;
        $q.notify({
          type: 'positive',
          message: 'Pixels extracted successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error extracting pixels:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to extract pixels',
          icon: 'error'
        });
      } finally {
        extractingPixels.value = false;
      }
    };

    watch(classLabel, (newLabel) => {
      setClassLabel(newLabel);
    });

    return {
      baseMap,
      project,
      trainingPolygons,
      classLabel,
      classOptions,
      leftDrawerOpen,
      selectedSavedPolygons,
      savedPolygonsOptions,
      selectedBasemapDate,
      basemapDateOptions,
      onMapReady,
      startDrawing,
      saveDrawnPolygons,
      loadSavedPolygons,
      updateBasemap,
      extractPixels,
      setClassLabel,
      toggleDrawing,
      showErrorDialog,
      errorMessage,
      handleBasemapError
    }
  }
}
</script>

<style scoped>
.map-overlay {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 1;
}
</style>