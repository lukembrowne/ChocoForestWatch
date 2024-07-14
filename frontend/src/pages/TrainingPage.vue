<template>
  <q-page class="row">
    <q-drawer v-model="leftDrawerOpen" show-if-above :width="300" :breakpoint="400" bordered class="bg-grey-3">
      <q-scroll-area class="fit">
        <q-list>
          <q-item-label header>Instructions</q-item-label>
          <q-item>
            <q-item-section>
              <ol>
                <li>Select a basemap date from the dropdown below.</li>
                <li>Choose a class from the dropdown.</li>
                <li>Click the "Draw Polygon" button to start drawing.</li>
                <li>Click on the map to add points to your polygon.</li>
                <li>Double-click to finish drawing the polygon.</li>
                <li>Repeat for different classes as needed.</li>
              </ol>
            </q-item-section>
          </q-item>

          <q-item-label header>Basemap Dates</q-item-label>
          <q-item v-for="date in basemapDateOptions" :key="date.value">
            <q-item-section>
              <q-btn :label="date.label" :color="date.hasPolygons ? 'primary' : 'grey'"
                @click="selectBasemapDate(date.value)" class="full-width">
                <q-badge v-if="date.hasPolygons" color="green" floating>✓</q-badge>
              </q-btn>
            </q-item-section>
          </q-item>

          <q-item v-if="selectedBasemapDate">
            <q-item-section>
              <q-select v-model="classLabel" :options="classOptions" label="Class" />
            </q-item-section>
          </q-item>

          <q-item v-if="selectedBasemapDate">
            <q-item-section>
              <q-btn label="Draw Polygon" color="primary" @click="startDrawing" class="full-width" />
            </q-item-section>
          </q-item>

          <q-item v-if="selectedBasemapDate">
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
import { useRouter } from 'vue-router';
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
    const router = useRouter()
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

    const currentProject = computed(() => projectStore.currentProject)

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

    const basemapDates = ref([])

    // New data structure to associate basemap dates with polygon sets
    const polygonSets = ref({})

    const {
      drawing,
      polygons,
      startDrawing,
      stopDrawing,
      getDrawnPolygonsGeoJSON,
      setClassLabel,
      clearDrawnPolygons
    } = useDrawing(baseMap);

    const toggleDrawing = () => {
      if (drawing.value) {
        stopDrawing();
      } else {
        startDrawing();
      }
    };

    onMounted(async () => {

      if (!projectStore.selectedProjectId) {
        router.push('/') // Redirect to home page if no project is selected
        return
      }

      if (!currentProject.value || currentProject.value.id !== projectStore.selectedProjectId) {
        try {
          await projectStore.loadProject(projectStore.selectedProjectId)
        } catch (error) {
          console.error('Error loading project:', error)
          router.push('/') // Redirect to home page if project loading fails
          return
        }
      }

      await fetchBasemapDates(projectStore.selectedProjectId)

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
      if (projectStore.currentProject.aoi) {
        try {

        // Saved as GEOJSON so need to convert to geometry
        const geojsonFormat = new GeoJSON();
        const geometry = geojsonFormat.readGeometry(projectStore.currentProject.aoi);
        const extent = geometry.getExtent();
        const aoiFeature = new Feature({
          geometry: geometry,
        });
        aoiLayer.value.getSource().addFeature(aoiFeature);
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

    const fetchBasemapDates = async (projectId) => {
      try {
        const response = await apiService.getTrainingPolygons(projectId)
        basemapDates.value = response.data.map(item => ({
          label: new Date(item.basemap_date).toLocaleString('default', { month: 'long', year: 'numeric' }),
          value: item.basemap_date,
          hasPolygons: item.has_polygons
        }))
      } catch (error) {
        console.error('Error fetching basemap dates:', error)
        $q.notify({
          type: 'negative',
          message: 'Failed to fetch basemap dates',
          icon: 'error'
        })
      }
    }

    const selectBasemapDate = async (date) => {
      if (selectedBasemapDate.value && polygons.value.length > 0) {
        const shouldSave = await $q.dialog({
          title: 'Unsaved Changes',
          message: 'Do you want to save your changes before switching dates?',
          ok: 'Save',
          cancel: 'Discard'
        }).onOk(() => true).onCancel(() => false)

        if (shouldSave) {
          await saveDrawnPolygons()
        }
      }

      selectedBasemapDate.value = date
      clearDrawnPolygons()
      await loadPolygonsForDate(date)
      baseMap.value.updateBasemap(date)

    }

    const loadPolygonsForDate = async (date) => {
      try {
        const response = await apiService.getSpecificTrainingPolygons(projectStore.currentProject.id, date)
        loadPolygons(response.data)
      } catch (error) {
        console.error('Error loading polygons:', error)
        $q.notify({
          type: 'negative',
          message: 'Failed to load polygons for this date',
          icon: 'error'
        })
      }
    }

    const saveDrawnPolygons = async () => {
      if (!selectedBasemapDate.value) {
        $q.notify({
          type: 'warning',
          message: 'Please select a basemap date before saving polygons',
          icon: 'warning'
        })
        return
      }

      try {
        const polygonsGeoJSON = getDrawnPolygonsGeoJSON()
        await apiService.saveTrainingPolygons({
          project_id: projectStore.currentProject.id,
          basemap_date: selectedBasemapDate.value,
          polygons: polygonsGeoJSON
        })

        // Update the basemapDates to reflect that this date now has polygons
        const dateIndex = basemapDates.value.findIndex(d => d.value === selectedBasemapDate.value)
        if (dateIndex !== -1) {
          basemapDates.value[dateIndex].hasPolygons = true
        }

        $q.notify({
          type: 'positive',
          message: 'Polygons saved successfully',
          icon: 'check'
        })
      } catch (error) {
        console.error('Error saving drawn polygons:', error)
        $q.notify({
          type: 'negative',
          message: 'Failed to save drawn polygons',
          icon: 'error'
        })
      }
    }


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

      // Clear current polygons
      clearDrawnPolygons();

      // Load polygons for the selected basemap date
      const savedPolygons = polygonSets.value[selectedBasemapDate.value] || [];
      savedPolygons.forEach(feature => {
        const olFeature = new GeoJSON().readFeature(feature, {
          featureProjection: 'EPSG:3857'
        });
        olFeature.set('classLabel', feature.properties.classLabel);
        trainingLayer.value.getSource().addFeature(olFeature);
      });

      // Update the basemap
      baseMap.value.updateBasemap(selectedBasemapDate.value);
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
      extractPixels,
      setClassLabel,
      toggleDrawing,
      showErrorDialog,
      errorMessage,
      handleBasemapError,
      updateBasemap,
      currentProject,
      basemapDates,
      selectBasemapDate
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