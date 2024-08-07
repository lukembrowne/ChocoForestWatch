<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 800px; max-width: 90vw;">
      <q-card-section>
        <div class="text-h6">Make a Prediction</div>
      </q-card-section>

      <q-card-section>
        <q-stepper v-model="step" vertical color="primary" animated>
          <!-- Step 1: Prediction Name and Description -->
          <q-step :name="1" title="Name Your Prediction" icon="create" :done="step > 1">
            <p>Provide a name and description for your prediction. This will help you identify it later.</p>
            <q-input v-model="predictionName" label="Prediction Name"
              :rules="[val => !!val || 'Prediction name is required']" />
            <q-input v-model="predictionDescription" label="Prediction Description (Optional)" type="textarea" />
            <q-stepper-navigation>
              <q-btn @click="step = 2" color="primary" label="Next" />
            </q-stepper-navigation>
          </q-step>

          <!-- Step 2: Model Selection -->
          <q-step :name="2" title="Select a Model" icon="model_training" :done="step > 2">
            <p>Choose a trained model to use for this prediction. The table below shows all available models for this
              project.</p>
            <q-table :rows="modelOptions" :columns="modelColumns" row-key="id" @row-click="onModelRowClick">
              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <q-btn flat round icon="edit" @click.stop="openRenameDialog(props.row)" />
                  <q-btn flat round icon="delete" @click.stop="confirmDelete(props.row)" />
                </q-td>
              </template>
            </q-table>
            <q-stepper-navigation>
              <q-btn flat @click="step = 1" color="primary" label="Back" class="q-mr-sm" />
              <q-btn @click="step = 3" color="primary" label="Next" :disable="!selectedModel" />
            </q-stepper-navigation>
          </q-step>

          <!-- Step 3: Basemap Date Selection -->
          <q-step :name="3" title="Select Basemap Date" icon="event" :done="step > 3">
            <p>Choose the basemap date for your prediction. Dates used in training the selected model are highlighted.
            </p>
            <div class="basemap-date-selector">
              <div v-for="(yearGroup, year) in groupedDates" :key="year" class="year-group">
                <div class="year-label">{{ year }}</div>
                <div class="month-columns">
                  <div class="column">
                    <q-radio v-for="option in yearGroup.slice(0, 6)" :key="option.value" v-model="selectedBasemapDate"
                      :val="option.value" :label="option.label.split(' ')[0]"
                      :color="isTrainingDate(option.value) ? 'primary' : 'grey'" />
                  </div>
                  <div class="column">
                    <q-radio v-for="option in yearGroup.slice(6)" :key="option.value" v-model="selectedBasemapDate"
                      :val="option.value" :label="option.label.split(' ')[0]"
                      :color="isTrainingDate(option.value) ? 'primary' : 'grey'" />
                  </div>
                </div>
              </div>
            </div>
            <q-stepper-navigation>
              <q-btn flat @click="step = 2" color="primary" label="Back" class="q-mr-sm" />
              <q-btn @click="predict" color="primary" label="Make Prediction" :disable="!isFormValid" />
            </q-stepper-navigation>
          </q-step>
        </q-stepper>
      </q-card-section>
    </q-card>
  </q-dialog>

  <q-dialog v-model="showProgress" persistent>
    <q-card style="width: 300px">
      <q-card-section>
        <div class="text-h6">Prediction in Progress</div>
      </q-card-section>

      <q-card-section>
        <q-linear-progress :value="progress" color="primary" />
        <div class="q-mt-sm">{{ progressMessage }}</div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useDialogPluginComponent, useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import apiService from 'src/services/api'
import { getBasemapDateOptions } from 'src/utils/dateUtils'
import { GeoJSON } from 'ol/format'
import { transformExtent } from 'ol/proj'

export default {
  name: 'PredictionDialog',
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()

    const step = ref(1)
    const predictionName = ref(generateDefaultPredictionName())
    const predictionDescription = ref('')
    const selectedModel = ref(null)
    const selectedBasemapDate = ref(null)
    const modelOptions = ref([])
    const groupedDates = computed(() => {
      return getBasemapDateOptions().reduce((acc, option) => {
        const year = option.value.split('-')[0]
        if (!acc[year]) {
          acc[year] = []
        }
        acc[year].push(option)
        return acc
      }, {})
    })
    const showProgress = ref(false)
    const progress = ref(0)
    const progressMessage = ref('')

    const modelColumns = [
      { name: 'name', required: true, label: 'Name', align: 'left', field: row => row.name, sortable: true },
      { name: 'actions', align: 'center', label: 'Actions' },
      { name: 'description', align: 'left', label: 'Description', field: 'description', sortable: true },
      { name: 'created_at', align: 'left', label: 'Created At', field: 'created_at', sortable: true },
      { name: 'accuracy', align: 'left', label: 'Accuracy', field: 'accuracy', sortable: true },
      { name: 'training_periods', align: 'left', label: 'Training Periods', field: 'training_periods' },
      { name: 'num_training_samples', align: 'left', label: 'Training Samples', field: 'num_training_samples', sortable: true }
    ]

    const isFormValid = computed(() => {
      return predictionName.value && selectedModel.value && selectedBasemapDate.value
    })

    function generateDefaultPredictionName() {
      const today = new Date()
      const dateString = today.toISOString().split('T')[0] // YYYY-MM-DD
      const timeString = today.toTimeString().split(' ')[0].replace(/:/g, '-') // HH-MM-SS
      return `Prediction_${dateString}_${timeString}`
    }

    onMounted(async () => {
      try {
        const models = await apiService.getTrainedModels(projectStore.currentProject.id)
        console.log('Fetched models', models)
        modelOptions.value = models
      } catch (error) {
        console.error('Error fetching models:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch trained models',
          icon: 'error'
        })
      }
    })

    function selectModel(model) {
      selectedModel.value = model;
      console.log('Selected model:', model);

      // Check and log the actual training_periods data
      if (model.training_periods && model.training_periods.length > 0) {
        console.log('Training periods:', model.training_periods);
        console.log('First training period:', model.training_periods[0]);

        // Set the basemap date if it's valid
        selectedBasemapDate.value = model.training_periods[0]; // Assuming this is the correct data object
      } else {
        console.warn('No training periods available');
      }
    }

    function onModelRowClick(evt, row) {
      selectModel(row)
    }

    function isTrainingDate(date) {
      return selectedModel.value && selectedModel.value.training_periods && selectedModel.value.training_periods.includes(date)
    }

    async function predict() {
      showProgress.value = true
      progress.value = 0
      progressMessage.value = 'Initiating prediction...'

      const geojsonString = projectStore.currentProject.aoi
      const geojsonFormat = new GeoJSON()
      const geometry = geojsonFormat.readGeometry(geojsonString)
      const extent = geometry.getExtent()
      const extentLatLon = transformExtent(extent, 'EPSG:3857', 'EPSG:4326')

      try {
        const result = await apiService.predictLandcover({
          projectId: projectStore.currentProject.id,
          modelId: selectedModel.value.id,
          basemapDate: selectedBasemapDate.value,
          predictionName: predictionName.value,
          predictionDescription: predictionDescription.value,
          aoiExtent: extent,
          aoiExtentLatLon: extentLatLon
        })

        showProgress.value = false
        onDialogOK(result)
        $q.notify({
          color: 'positive',
          message: 'Prediction completed successfully',
          icon: 'check'
        })

        // Trigger display of prediction on the map
        mapStore.displayPrediction(result.file_path)
      } catch (error) {
        console.error('Error during prediction:', error)
        showProgress.value = false
        $q.notify({
          color: 'negative',
          message: 'Failed to complete prediction',
          icon: 'error'
        })
      }
    }

    return {
      dialogRef,
      onDialogHide,
      step,
      predictionName,
      predictionDescription,
      selectedModel,
      selectedBasemapDate,
      modelOptions,
      modelColumns,
      groupedDates,
      isFormValid,
      predict,
      showProgress,
      progress,
      progressMessage,
      selectModel,
      onModelRowClick,
      isTrainingDate
    }
  }
}
</script>

<style scoped>
.basemap-date-selector {
  max-height: 300px;
  overflow-y: auto;
}

.year-group {
  margin-bottom: 20px;
}

.year-label {
  font-weight: bold;
  margin-bottom: 10px;
}

.month-columns {
  display: flex;
  justify-content: space-between;
}

.column {
  width: 48%;
}
</style>