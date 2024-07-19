<template>
  <div class="training-component">
    <p> Select basemap date:</p>
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

    <q-btn label="Save Training Data" color="positive" @click="saveDrawnPolygons"
      :disable="drawnPolygons.length === 0" />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useTrainingStore } from 'src/stores/trainingStore'
import { useQuasar } from 'quasar'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'
import apiService from 'src/services/api'

export default {
  name: 'TrainingComponent',
  emits: ['step-completed'],
  setup(props, { emit }) {
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const trainingStore = useTrainingStore()
    const $q = useQuasar()

    const selectedClass = computed(() => mapStore.selectedClass)
    const drawnPolygons = computed(() => trainingStore.drawnPolygons)
    const selectedBasemapDate = ref(null)
    const isDrawing = computed(() => mapStore.isDrawing)

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


    const loadExistingTrainingData = async () => {
      try {
        const response = await apiService.getSpecificTrainingPolygons(
          projectStore.currentProject.id,
          selectedBasemapDate.value
        )
        const existingPolygons = response.data
        if (existingPolygons && existingPolygons.length > 0) {
          loadPolygons({ type: 'FeatureCollection', features: existingPolygons })
          drawnPolygons.value = existingPolygons
        } else {
          clearDrawnPolygons()
        }
      } catch (error) {
        console.error('Error loading existing training data:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to load existing training data',
          icon: 'error'
        })
      }
    }

    const onClassSelect = (classValue) => {
      selectedClass.value = classValue
      setClassLabel(classValue)
    }

    const onBasemapDateChange = async (date) => {
      console.log("Basemap date changed to: ", date)
      console.log("Updating basemap")
      mapStore.updateBasemap(date['value'])
      //await loadExistingTrainingData()
    }


    const calculateArea = (polygon) => {
      const feature = new GeoJSON().readFeature(polygon)
      return getArea(feature.getGeometry())
    }

    const saveDrawnPolygons = async () => {
      try {
        await apiService.saveTrainingPolygons({
          project_id: projectStore.currentProject.id,
          basemap_date: selectedBasemapDate.value,
          polygons: mapStore.getDrawnPolygonsGeoJSON()
        })
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
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && trainingStore.selectedPolygon !== null) {
        mapStore.deletePolygon(trainingStore.selectedPolygon)
      } else if (event.key === ' ' && !event.repeat) {
        event.preventDefault();
        mapStore.toggleDrawing();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);

    watch(selectedClass, (newLabel) => {
      mapStore.setClassLabel(newLabel);
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
      onBasemapDateChange
    }
  }
}
</script>