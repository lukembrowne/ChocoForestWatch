<template>
  <div class="training-component">
    <h6> Select basemap date:</h6>
    <div class="basemap-selection q-mb-md">
      <q-select v-model="selectedBasemapDate" :options="basemapDateOptions" label="Select Basemap Date"
        @update:model-value="onBasemapDateChange" />
    </div>
    
    <q-separator spaced />

    <p> Drawing controls</p>
    <div class="class-selection q-mb-md">
      <q-item-section>
        <q-select v-model="selectedClass" :options="landCoverClasses" label="Class" dense />
      </q-item-section>
    </div>

    <div class="drawing-controls q-mb-md">
      <q-btn label="Draw Polygon" color="primary" @click="startDrawing" :disable="isDrawing" />
      <q-btn label="Stop Drawing" color="negative" @click="stopDrawing" :disable="!isDrawing" class="q-ml-sm" />
      <q-btn label="Clear All" color="warning" @click="clearDrawnPolygons" class="q-ml-sm" />
      <q-btn label="Load Training Set" color="secondary" @click="openLoadDialog" />
    </div>

    <div class="polygon-list q-mb-md">
      <h6>Training Polygons</h6>
      <q-list bordered separator>
        <q-item v-for="(polygon, index) in drawnPolygons" :key="index">
          <q-item-section>
            {{ polygon.properties.classLabel }} - Area: {{ (calculateArea(polygon)/10000).toFixed(2) }} ha
          </q-item-section>
          <q-item-section side>
            <q-btn flat round color="negative" icon="delete" @click="deletePolygon(index)" />
          </q-item-section>
        </q-item>
      </q-list>
    </div>

    <q-btn label="Save Training Data" color="positive" @click="openSaveDialog"
  :disable="drawnPolygons.length === 0" />

  <q-dialog v-model="showSaveDialog">
    <q-card>
      <q-card-section>
        <div class="text-h6">Save Training Set</div>
      </q-card-section>

      <q-card-section>
        <q-input v-model="trainingSetName" label="Training Set Name" />
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Cancel" color="primary" v-close-popup />
        <q-btn flat label="Save" color="primary" @click="saveDrawnPolygons" />
      </q-card-actions>
    </q-card>
  </q-dialog>

    <q-btn label="Train Model" color="primary" @click="openTrainingOptions" class="q-ml-md"
      :disable="drawnPolygons.length === 0" />

    <q-dialog v-model="showTrainingOptions">
      <training-options-card @train="trainModel" @close="showTrainingOptions = false" />
    </q-dialog>

    <training-progress
      :show="isTraining"
      :progress="trainingProgress"
      :progressMessage="trainingProgressMessage"
      :error="trainingError"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, onUnmounted, h } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useQuasar } from 'quasar'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'
import apiService from 'src/services/api'
import { storeToRefs } from 'pinia';
import { store } from 'quasar/wrappers'
import { transformExtent } from 'ol/proj'
import TrainingOptionsCard from 'components/TrainingOptionsCard.vue'
import TrainingProgress from 'components/TrainingProgress.vue'
import { io } from 'socket.io-client';
import LoadTrainingSetDialog from 'components/LoadTrainingSetDialog.vue';
import api from 'src/services/api';


export default {
  name: 'TrainingComponent',
  emits: ['step-completed'],
  components: {
    TrainingOptionsCard,
    TrainingProgress
  },
  setup(props, { emit }) {
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const $q = useQuasar()

    const selectedClass = computed(() => mapStore.selectedClass)
    const drawnPolygons = computed(() => mapStore.drawnPolygons)
    // const drawnPolygons = storeToRefs(mapStore.drawnPolygons)

    const selectedBasemapDate = ref(null) // Setting default
    const isDrawing = computed(() => mapStore.isDrawing)

    const showTrainingOptions = ref(false)
    const isTraining = ref(false)
    const trainingProgress = ref(0)
    const trainingProgressMessage = ref('')
    const trainingError = ref('')
    const trainingResults = ref(null)
    const socket = io('http://127.0.0.1:5000');
    const showSaveDialog = ref(false)
    const trainingSetName = ref('')


    // Destructure to use directly in the template
    const { startDrawing, stopDrawing, clearDrawnPolygons, deletePolygon} = mapStore;


    const landCoverClasses = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non_forest' }
    ]

    const basemapDateOptions = computed(() => {
      const options = []
      for (let year = 2022; year <= 2024; year++) {
        for (let month = 1; month <= 12; month++) {
          if (year === 2024 && month > 6) break
          const date = new Date(year, month - 1)
          options.push({
            label: date.toLocaleString('default', { month: 'long', year: 'numeric' }),
            value: `${year}-${month.toString().padStart(2, '0')}`
          })
        }
      }
      return options
    })

    onMounted(async () => {
      window.addEventListener('keydown', handleKeyDown);

      socket.on('training_update', (data) => {
        console.log('Received training update:', data);
        if (data.projectId === projectStore.currentProject.id) {
          trainingProgress.value = data.progress;
          trainingProgressMessage.value = data.message;
          if (data.error) {
            trainingError.value = data.error;
            isTraining.value = false;
            $q.notify({
              type: 'negative',
              message: 'Error occurred during training.'
            });
          }
          if (data.message === "Training and prediction complete") {
            mapStore.displayPrediction(data.data.prediction_filepath)
            isTraining.value = false;
            $q.notify({
              type: 'positive',
              message: 'Training and prediction completed successfully!'
            });
          }
        }
      });
    })


    const openLoadDialog = () => {
      $q.dialog({
        component: LoadTrainingSetDialog,
      }).onOk((selectedSet) => {
        // Load the selected training set
        loadTrainingSet(selectedSet.id);
      });
    };

    const loadTrainingSet = async (setId) => {
      try {
        const response = await api.getSpecificTrainingPolygons(projectStore.currentProject.id, setId);
        mapStore.loadPolygons(response.data);
      } catch (error) {
        console.error('Error loading training set:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load training set',
          icon: 'error'
        });
      }
    };

    const onClassSelect = (classValue) => {
      selectedClass.value = classValue
      setClassLabel(classValue)
    }

    const onBasemapDateChange = async (date) => {
      console.log("Basemap date changed to: ", date)
      console.log("Updating basemap")
      mapStore.updateBasemap(date['value'])
    }


    const calculateArea = (polygon) => {
      const feature = new GeoJSON().readFeature(polygon)
      return getArea(feature.getGeometry())
    }


    const openSaveDialog = () => {
      trainingSetName.value = ''  // Reset the name
      showSaveDialog.value = true
    }

    const saveDrawnPolygons = async () => {
      if (!trainingSetName.value) {
        $q.notify({
          color: 'negative',
          message: 'Please enter a name for the training set',
          icon: 'error'
        })
        return
      }

      try {
        await apiService.saveTrainingPolygons({
          project_id: projectStore.currentProject.id,
          basemap_date: selectedBasemapDate.value,
          polygons: mapStore.getDrawnPolygonsGeoJSON(),
          name: trainingSetName.value
        })
        showSaveDialog.value = false
        $q.notify({
          color: 'positive',
          message: 'Training data saved successfully',
          icon: 'check'
        })
        emit('step-completed')
      } catch (error) {
        console.error('Error saving training data:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to save training data',
          icon: 'error'
        })
      }
    }

    const openTrainingOptions = () => {
      showTrainingOptions.value = true
    }

    const trainModel = async (options) => {
      showTrainingOptions.value = false
      isTraining.value = true
      trainingProgress.value = 0
      trainingProgressMessage.value = 'Initializing training...'
      trainingError.value = ''

      const geojsonString = projectStore.currentProject.aoi
      const geojsonFormat = new GeoJSON()
      const geometry = geojsonFormat.readGeometry(geojsonString)
      const extent = geometry.getExtent()
      const extentLatLon = transformExtent(extent, 'EPSG:3857', 'EPSG:4326')

      try {
        const response = await apiService.trainModel({
          projectId: projectStore.currentProject.id,
          aoiExtent: extentLatLon,
          basemapDate: selectedBasemapDate.value.value,
          trainingPolygons: mapStore.drawnPolygons,
          ...options
        })

      } catch (error) {
        console.error('Error training model:', error)
        trainingError.value = 'An error occurred during training. Please try again.'
        $q.notify({
          color: 'negative',
          message: 'Failed to train model',
          icon: 'error'
        })
        isTraining.value = false
      } 
    }

    
    const handleKeyDown = (event) => {
      if (event.key === '1') {
        console.log("Selected class: forest")
        mapStore.setClassLabel('forest');
      } else if (event.key === '2') {
        console.log("Selected class: non-forest")
        mapStore.setClassLabel('non-forest');
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && mapStore.selectedPolygon !== null) {
        mapStore.deletePolygon(mapStore.selectedPolygon)
      } else if (event.key === ' ' && !event.repeat) {
        event.preventDefault();
        mapStore.toggleDrawing();
      }
    };
    
    watch(selectedClass, (newLabel) => {
      mapStore.setClassLabel(newLabel);
    });

    // Watch for changes in the currentProject
    watch(drawnPolygons, () => {
      console.log("Drawn polygons changed")
        drawnPolygons.value = mapStore.drawnPolygons
    }, { immediate: true });

    onUnmounted(() => {
      socket.off('training_update');
      socket.disconnect();
    });


    return {
      selectedClass,
      isDrawing,
      drawnPolygons,
      landCoverClasses,
      startDrawing,
      stopDrawing,
      clearDrawnPolygons,
      deletePolygon,
      calculateArea,
      saveDrawnPolygons,
      onClassSelect,
      basemapDateOptions,
      selectedBasemapDate,
      onBasemapDateChange,
      showTrainingOptions,
      openTrainingOptions,
      trainModel,
      isTraining,
      trainingProgress,
      trainingProgressMessage,
      trainingError,
      openLoadDialog,
      trainingSetName,
      openSaveDialog,
      showSaveDialog
    }
  }
}
</script>