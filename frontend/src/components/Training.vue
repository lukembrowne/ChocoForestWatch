<template>
  <div class="training-component">

    <q-separator spaced />
    <p> Load a training dataset: </p>

    <!-- Load button -->
    <q-btn label="Load Training Set" color="secondary" @click="openLoadDialog" class="q-ml-sm" />

    <q-separator spaced />

    <!-- Basemap date selection -->
    <div class="basemap-selection q-mb-md">
      <q-select v-model="selectedBasemapDate" :options="basemapDateOptions" label="Select Basemap Date"
        :rules="[val => !!val || 'Basemap date is required']" @update:model-value="onBasemapDateChange" />
    </div>

    <q-separator spaced />


    <p> Drawing controls:</p>
    <div class="class-selection q-mb-md">
      <q-item-section>
        <q-select v-model="selectedClass" :options="landCoverClasses" label="Class" dense />
      </q-item-section>
    </div>

    <div class="drawing-controls q-mb-md">
      <q-btn label="Draw Polygon" color="primary" @click="startDrawing" :disable="isDrawing" />
      <q-btn label="Stop Drawing" color="negative" @click="stopDrawing" :disable="!isDrawing" class="q-ml-sm" />
      <q-btn label="Clear All" color="warning" @click="clearDrawnPolygons" class="q-ml-sm" />
    </div>

    <!-- Save/Update buttons -->
    <div class="q-gutter-sm">
      <q-btn v-if="!existingTrainingSet" label="Save New Training Set" color="positive" @click="openSaveDialog('new')"
        :disable="drawnPolygons.length === 0 || !selectedBasemapDate" />
      <q-btn v-if="existingTrainingSet" label="Update Training Set" color="primary" @click="openSaveDialog('update')"
        :disable="drawnPolygons.length === 0 || !selectedBasemapDate" />
      <q-btn v-if="existingTrainingSet" label="Save As New" color="secondary" @click="openSaveDialog('new')"
        :disable="drawnPolygons.length === 0 || !selectedBasemapDate" />
    </div>

    <!-- Save/Update Dialog -->
    <q-dialog v-model="showSaveDialog">
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">{{ saveMode === 'update' ? 'Update' : 'Save' }} Training Set</div>
        </q-card-section>

        <q-card-section>
          <q-input v-model="trainingSetName" label="Training Set Name" :rules="[val => !!val || 'Name is required']" />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn flat :label="saveMode === 'update' ? 'Update' : 'Save'" color="primary"
            @click="saveOrUpdateTrainingSet" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <div class="polygon-list q-mb-md">
      <h6>Training Polygons</h6>
      <q-list bordered separator>
        <q-item v-for="(polygon, index) in drawnPolygons" :key="index">
          <q-item-section>
            {{ polygon.properties.classLabel }} - Area: {{ (calculateArea(polygon) / 10000).toFixed(2) }} ha
          </q-item-section>
          <q-item-section side>
            <q-btn flat round color="negative" icon="delete" @click="deletePolygon(index)" />
          </q-item-section>
        </q-item>
      </q-list>
    </div>

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
import LoadTrainingSetDialog from 'components/LoadTrainingSetDialog.vue';
import api from 'src/services/api';
import { getBasemapDateOptions } from 'src/utils/dateUtils'

export default {
  name: 'TrainingComponent',
  setup(props, { emit }) {
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const $q = useQuasar()

    const selectedClass = computed(() => mapStore.selectedClass)
    const drawnPolygons = computed(() => mapStore.drawnPolygons)

    const basemapDateOptions = computed(() => getBasemapDateOptions())
    const selectedBasemapDate = ref(null) // Setting default
    const isDrawing = computed(() => mapStore.isDrawing)

    const showTrainingOptions = ref(false)
    const showSaveDialog = ref(false)
    const trainingSetName = ref('')
    const existingTrainingSet = ref(null)
    const saveMode = ref('new')




    // Destructure to use directly in the template
    const { startDrawing, stopDrawing, clearDrawnPolygons, deletePolygon } = mapStore;


    const landCoverClasses = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non_forest' }
    ]


    onMounted(async () => {
      window.addEventListener('keydown', handleKeyDown);
    })


    const openLoadDialog = () => {
      $q.dialog({
        component: LoadTrainingSetDialog,
      }).onOk((selectedSet) => {
        // Load the selected training set
        loadTrainingSet(selectedSet);
      });
    };

    const loadTrainingSet = async (selectedSet) => {
      try {
        const response = await api.getSpecificTrainingPolygons(projectStore.currentProject.id, selectedSet.id);
        mapStore.loadPolygons(response.data);
        existingTrainingSet.value = selectedSet
        trainingSetName.value = selectedSet.name
        selectedBasemapDate.value = basemapDateOptions.value.find(option => option.value === selectedSet.basemap_date)
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


    const openSaveDialog = (mode) => {
      if (!selectedBasemapDate.value) {
        $q.notify({
          color: 'negative',
          message: 'Please select a basemap date first',
          icon: 'error'
        })
        return
      }
      saveMode.value = mode
      if (mode === 'new') {
        trainingSetName.value = existingTrainingSet.value ? `Copy of ${existingTrainingSet.value.name}` : ''
      }
      showSaveDialog.value = true
    }

    const saveOrUpdateTrainingSet = async () => {
      if (!trainingSetName.value) {
        $q.notify({
          color: 'negative',
          message: 'Please enter a name for the training set',
          icon: 'error'
        })
        return
      }

      try {
        const data = {
          project_id: projectStore.currentProject.id,
          basemap_date: selectedBasemapDate.value.value,
          polygons: mapStore.getDrawnPolygonsGeoJSON(),
          name: trainingSetName.value
        }

        if (saveMode.value === 'update' && existingTrainingSet.value) {
          data.id = existingTrainingSet.value.id
          await apiService.updateTrainingPolygons(data)
        } else {
          await apiService.saveTrainingPolygons(data)
        }

        showSaveDialog.value = false
        $q.notify({
          color: 'positive',
          message: `Training data ${saveMode.value === 'update' ? 'updated' : 'saved'} successfully`,
          icon: 'check'
        })
        // loadExistingTrainingData()
      } catch (error) {
        console.error('Error saving/updating training data:', error)
        $q.notify({
          color: 'negative',
          message: `Failed to ${saveMode.value === 'update' ? 'update' : 'save'} training data`,
          icon: 'error'
        })
      }
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

    // Watch for changes in the drawnPolygons
    watch(drawnPolygons, () => {
      // console.log("Drawn polygons changed")
      drawnPolygons.value = mapStore.drawnPolygons
    }, { immediate: true });

    // Add watcher for when basemap date changes
    watch(selectedBasemapDate, (newDate) => {
      console.log("Basemap date changed to: ", newDate)
      console.log("Updating basemap")
      mapStore.updateBasemap(newDate['value'])
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
      openLoadDialog,
      openSaveDialog,
      showSaveDialog,
      saveOrUpdateTrainingSet,
      existingTrainingSet,
      saveMode
    }
  }
}
</script>