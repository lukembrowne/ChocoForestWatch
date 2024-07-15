<template>
  <q-page class="flex">
    <!-- Left Drawer for Basemap Dates -->
    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      :width="250"
      :breakpoint="400"
      bordered
      class="bg-grey-3"
      side="left"
    >
      <q-scroll-area class="fit">
        <q-list padding>
          <q-item-label header>Basemap Dates</q-item-label>
          <template v-for="(dates, year) in groupedBasemapDates" :key="year">
            <q-expansion-item :label="year" header-class="text-primary" default-opened>
              <q-list dense>
                <q-item v-for="date in dates" :key="date.value" dense>
                  <q-item-section>
                    <q-btn
                      flat
                      :label="date.label.split(' ')[0]"
                      :color="date.value === selectedBasemapDate ? 'primary' : 'grey-7'"
                      @click="selectBasemapDate(date.value)"
                      class="full-width text-left"
                      :icon-right="hasPolygons(date.value) ? 'check_circle' : null"
                      size="sm"
                    />
                  </q-item-section>
                </q-item>
              </q-list>
            </q-expansion-item>
          </template>
        </q-list>
      </q-scroll-area>
    </q-drawer>

   

    <!-- Map Container -->
    <div class="col relative-position" style="height: calc(100vh - 50px);">
      <BaseMapComponent
        ref="baseMap"
        @map-ready="onMapReady"
        @basemap-error="handleBasemapError"
        :basemapDate="selectedBasemapDate"
        class="absolute-full"
      />
    </div>

    <!-- Right Drawer for Drawing Controls and Polygon List -->
   <q-drawer
      v-model="rightDrawerOpen"
      show-if-above
      :width="300"
      bordered
      class="bg-grey-3"
      side="right"
    >
      <q-scroll-area class="fit">
        <q-list padding>
          <q-item-label header>Drawing Controls</q-item-label>
          <q-item>
            <q-item-section>
              <q-select v-model="classLabel" :options="classOptions" label="Class" dense />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-btn
                :label="drawing ? 'Stop Drawing' : 'Draw Polygon'"
                :color="drawing ? 'negative' : 'primary'"
                @click="toggleDrawing"
                class="full-width"
              />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-btn label="Save Polygons" color="positive" @click="saveDrawnPolygons" class="full-width" />
            </q-item-section>
          </q-item>

          <q-separator spaced />

          <q-item-label header>Polygon Summary</q-item-label>
          <q-item v-for="(count, label) in polygonSummary" :key="label">
            <q-item-section>
              <q-item-label>{{ label }}: {{ count }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-separator spaced />

          <q-item-label header>Drawn Training Polygons</q-item-label>
          <q-item v-for="(polygon, index) in drawnPolygons" :key="index">
            <q-item-section>
              <q-item-label>Polygon {{ index + 1 }}</q-item-label>
              <q-item-label caption>Class: {{ polygon.properties.classLabel }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn flat round icon="delete" @click="deletePolygon(index)" color="negative" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <!-- Error Dialog -->
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
import { useTrainingStore } from 'src/stores/trainingStore'
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
    const trainingStore = useTrainingStore()
    const baseMap = ref(null)
    const project = ref({})
    const trainingPolygons = ref([])
    const classLabel = ref('forest');
    const leftDrawerOpen = ref(true)
    const rightDrawerOpen = ref(true)
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
    const drawnPolygons = computed(() => trainingStore.drawnPolygons)

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

    const datesWithPolygons = ref(new Set())

    const polygonSummary = computed(() => {
      const summary = {}
      drawnPolygons.value.forEach(polygon => {
        const label = polygon.properties.classLabel
        summary[label] = (summary[label] || 0) + 1
      })
      return summary
    })

    // New data structure to associate basemap dates with polygon sets
    const polygonSets = ref({})

    const {
      drawing,
      startDrawing,
      stopDrawing,
      getDrawnPolygonsGeoJSON,
      setClassLabel,
      clearDrawnPolygons,
      loadPolygons,
      deletePolygon,
    } = useDrawing(baseMap);

    const toggleDrawing = () => {
      if (drawing.value) {
        stopDrawing();
      } else {
        startDrawing();
      }
    };

    // Add this computed property for grouping dates by year
    const groupedBasemapDates = computed(() => {
      const grouped = {};
      basemapDateOptions.value.forEach(date => {
        const year = date.value.split('-')[0];
        if (!grouped[year]) {
          grouped[year] = [];
        }
        grouped[year].push(date);
      });
      return grouped;
    });

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

      await fetchExistingPolygonDates()
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
        classLabel.value = 'forest';
      } else if (event.key === '2') {
        classLabel.value = 'non-forest';
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && trainingStore.selectedPolygon !== null) {
        deletePolygon(trainingStore.selectedPolygon)
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
      // if (selectedBasemapDate.value && polygons.value.length > 0) {
      //   const shouldSave = await $q.dialog({
      //     title: 'Unsaved Changes',
      //     message: 'Do you want to save your changes before switching dates?',
      //     ok: 'Save',
      //     cancel: 'Discard'
      //   }).onOk(() => true).onCancel(() => false)

      //   if (shouldSave) {
      //     await saveDrawnPolygons()
      //   }
      // }

      selectedBasemapDate.value = date
      clearDrawnPolygons()

      if (hasPolygons(date)) {
        await loadPolygonsForDate(date)
      }

      if (baseMap.value && typeof baseMap.value.updateBasemap === 'function') {
        baseMap.value.updateBasemap(date)
      } else {
        console.error('BaseMapComponent is not properly initialized or doesn\'t have updateBasemap method')
      }
    }

    const loadPolygonsForDate = async (date) => {
      try {
        console.log('Date:', date)
        const response = await apiService.getSpecificTrainingPolygons(currentProject.value.id, date)
        console.log('Polygons:', response.data.polygons)
        console.log('response:', response)
        if (response.data) {
          loadPolygons(response.data)
        } else {
          console.warn('No polygons data found for the selected date')
          clearDrawnPolygons()
        }
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
        if (!polygonsGeoJSON || polygonsGeoJSON.features.length === 0) {
          $q.notify({
            type: 'warning',
            message: 'No polygons drawn to save',
            icon: 'warning'
          })
          return
        }

        await apiService.saveTrainingPolygons({
          project_id: currentProject.value.id,
          basemap_date: selectedBasemapDate.value,
          polygons: polygonsGeoJSON
        })

        datesWithPolygons.value.add(selectedBasemapDate.value)

        $q.notify({
          type: 'positive',
          message: 'Polygons saved successfully',
          icon: 'check'
        })
      } catch (error) {
        console.error('Error saving drawn polygons:', error)
        $q.notify({
          type: 'negative',
          message: 'Failed to save drawn polygons: ' + error.message,
          icon: 'error'
        })
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

    const fetchExistingPolygonDates = async () => {
      try {
        const response = await apiService.getTrainingPolygons(currentProject.value.id)
        datesWithPolygons.value = new Set(response.data.map(item => item.basemap_date))
      } catch (error) {
        console.error('Error fetching existing polygon dates:', error)
        $q.notify({
          type: 'negative',
          message: 'Failed to fetch existing polygon dates',
          icon: 'error'
        })
      }
    }

    const hasPolygons = (date) => {
      return datesWithPolygons.value.has(date)
    }


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
      rightDrawerOpen,
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
      selectBasemapDate,
      hasPolygons,
      groupedBasemapDates,
      drawnPolygons,
      deletePolygon,
      polygonSummary,
      drawing
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