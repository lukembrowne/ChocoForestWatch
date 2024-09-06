<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 800px; max-width: 90vw;">
      <q-card-section>
        <div class="text-h6">{{ existingModel ? 'Update' : 'Train' }} XGBoost Model</div>
      </q-card-section>

      <q-card-section v-if="trainingDataSummary">
        <div class="text-h6 q-mb-md">Training Data Summary</div>
        <div class="row q-col-gutter-md q-mb-md">
          <div class="col-12 col-md-6">
            <q-card class="bg-primary text-white">
              <q-card-section>
                <div class="text-h6">{{ trainingDataSummary.totalSets }}</div>
                <div class="text-subtitle2">Total Training Sets</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-12 col-md-6">
            <q-card class="bg-secondary text-white">
              <q-card-section>
                <div class="text-h6">{{ totalArea.toFixed(2) }} ha</div>
                <div class="text-subtitle2">Total Area</div>
              </q-card-section>
            </q-card>
          </div>
        </div>
        <q-markup-table flat bordered>
          <thead>
            <tr>
              <th class="text-left">Class</th>
              <th class="text-right">Features</th>
              <th class="text-right">Area (ha)</th>
              <th class="text-right">Percentage</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(stats, className) in trainingDataSummary.classStats" :key="className">
              <td class="text-left">
                <q-chip :color="getClassColor(className)" text-color="black" square>
                  {{ className }}
                </q-chip>
              </td>
              <td class="text-right">{{ stats.featureCount }}</td>
              <td class="text-right">{{ stats.totalAreaHa.toFixed(2) }}</td>
              <td class="text-right">{{ ((stats.totalAreaHa / totalArea) * 100).toFixed(2) }}%</td>
            </tr>
          </tbody>
        </q-markup-table>
      </q-card-section>

      <q-card-section v-if="trainingDataSummary">
        <div class="text-subtitle1">Basemap dates with training data:</div>
        <q-chip v-for="date in basemapOptions" :key="date"
          :color="getChipColor(date['value'])"
          :text-color="getChipTextColor(date['value'])">
          {{ date['label'] }}
        </q-chip>
      </q-card-section>

      <q-card-section>
        <q-expansion-item expand-separator label="Tune Advanced Model Parameters"
          caption="Click to customize model parameters">
          <div class="row q-col-gutter-md">
            <div class="col-12">
              <p>Choose split method:</p>
              <q-radio v-model="splitMethod" val="feature" label="Feature-based" color="primary" />
              <q-radio v-model="splitMethod" val="pixel" label="Pixel-based" color="primary" />
              <p class="text-caption q-mt-sm">
                Feature-based split ensures independence between training and testing data by splitting entire
                polygons.
                Pixel-based split may mix pixels from the same polygon in both training and testing sets.
              </p>
            </div>
            <div class="col-12">
              <p>Adjust the train/test split:</p>
              <q-slider v-model="trainTestSplit" :min="0.1" :max="0.5" :step="0.05" label label-always
                color="primary" />
              <p class="text-caption">
                This determines the proportion of data used for testing. A value of {{ trainTestSplit }} means
                {{ (trainTestSplit * 100).toFixed(0) }}% of the {{ splitMethod === 'pixel' ? 'pixels' : 'features' }}
                will be used for testing, and
                {{ (100 - trainTestSplit * 100).toFixed(0) }}% for training.
              </p>
            </div>
            <div class="col-12 col-md-6">
              <p>Number of Estimators:</p>
              <q-slider v-model="options.n_estimators" :min="10" :max="1000" :step="10" label label-always
                color="primary" />
              <p class="text-caption">The number of trees in the forest. Higher values generally improve performance
                but increase training time.</p>
            </div>
            <div class="col-12 col-md-6">
              <p>Max Depth:</p>
              <q-slider v-model="options.max_depth" :min="1" :max="10" :step="1" label label-always color="primary" />
              <p class="text-caption">Maximum depth of the trees. Higher values make the model more complex and prone
                to overfitting.</p>
            </div>
            <div class="col-12 col-md-6">
              <p>Learning Rate:</p>
              <q-slider v-model="options.learning_rate" :min="0.01" :max="0.3" :step="0.01" label label-always
                color="primary" />
              <p class="text-caption">Step size shrinkage used to prevent overfitting. Lower values are generally
                better but require more iterations.</p>
            </div>
            <div class="col-12 col-md-6">
              <p>Min Child Weight:</p>
              <q-slider v-model="options.min_child_weight" :min="1" :max="10" :step="1" label label-always
                color="primary" />
              <p class="text-caption">Minimum sum of instance weight needed in a child. Higher values make the model
                more conservative.</p>
            </div>
            <div class="col-12 col-md-6">
              <p>Gamma:</p>
              <q-slider v-model="options.gamma" :min="0" :max="1" :step="0.1" label label-always color="primary" />
              <p class="text-caption">Minimum loss reduction required to make a further partition. Higher values make
                the model more conservative.</p>
            </div>
            <div class="col-12 col-md-6">
              <p>Subsample:</p>
              <q-slider v-model="options.subsample" :min="0.5" :max="1" :step="0.1" label label-always
                color="primary" />
              <p class="text-caption">Fraction of samples used for fitting the trees. Lower values can help prevent
                overfitting.</p>
            </div>
            <div class="col-12 col-md-6">
              <p>Colsample Bytree:</p>
              <q-slider v-model="options.colsample_bytree" :min="0.5" :max="1" :step="0.1" label label-always
                color="primary" />
              <p class="text-caption">Fraction of features used for building each tree. Can help in reducing
                overfitting.</p>
            </div>
          </div>
        </q-expansion-item>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Cancel" color="primary" v-close-popup />
        <q-btn :label="existingModel ? 'Update Model' : 'Train Model'" color="primary" @click="trainModel" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <training-progress :show="isTraining" :progress="trainingProgress" :progressMessage="trainingProgressMessage"
    :error="trainingError" />
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useDialogPluginComponent, useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import apiService from 'src/services/api'
import { GeoJSON } from 'ol/format'
import { transformExtent } from 'ol/proj'
import TrainingProgress from 'components/models/TrainingProgress.vue'
import { io } from 'socket.io-client'
import { getBasemapDateOptions } from 'src/utils/dateUtils';



export default {
  name: 'ModelTrainingDialog',
  components: {
    TrainingProgress,
  },
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const $q = useQuasar()
    const projectStore = useProjectStore()

    const basemapOptions = computed(() => {
      return getBasemapDateOptions().map(option => ({
        label: option.label,
        value: option.value
      }));
    });

    const existingModel = ref(null)
    const modelName = ref(generateDefaultModelName())
    const modelDescription = ref('')
    const trainingDataSummary = ref(null)
    const availableDates = ref([])
    const trainingSetsPerDate = ref({})
    const isTraining = ref(false)
    const trainingProgress = ref(0)
    const trainingProgressMessage = ref('')
    const trainingError = ref('')
    const socket = io('http://127.0.0.1:5000')
    const splitMethod = ref('feature')  // Default to feature-based split
    const trainTestSplit = ref(0.2)

    const options = ref({
      n_estimators: 100,
      max_depth: 3,
      learning_rate: 0.1,
      min_child_weight: 1,
      gamma: 0,
      subsample: 0.8,
      colsample_bytree: 0.8
    })


    onMounted(async () => {
      await fetchTrainingDataSummary()
      await checkExistingModel()
      initializeSocket()
    })

    async function checkExistingModel() {
      try {
        const response = await apiService.getTrainedModels(projectStore.currentProject.id)
        if (response.length > 0) {
          existingModel.value = response[0]
          modelName.value = existingModel.value.name
          modelDescription.value = existingModel.value.description
          // You may want to populate other fields with existing model data
        }
      } catch (error) {
        console.error('Error checking existing model:', error)
      }
    }

    function initializeSocket() {
      socket.on('training_update', (data) => {
        if (data.projectId === projectStore.currentProject.id) {
          trainingProgress.value = data.progress
          trainingProgressMessage.value = data.message
          if (data.error) {
            trainingError.value = data.error
            isTraining.value = false
            $q.notify({
              type: 'negative',
              message: 'Error occurred during training.'
            })
          }
          if (data.message === "Training complete") {
            isTraining.value = false
            $q.notify({
              type: 'positive',
              message: 'Training completed successfully!'
            })
          }
        }
      })
    }

    async function fetchTrainingDataSummary() {
      try {
        const response = await apiService.getTrainingDataSummary(projectStore.currentProject.id)
        trainingDataSummary.value = response.data
        console.log("Training data summary: ", trainingDataSummary.value)
      } catch (error) {
        console.error('Error fetching training data summary:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch training data summary',
          icon: 'error'
        })
      }
    }

    async function trainModel() {
      try {
        isTraining.value = true
        trainingProgress.value = 0
        trainingProgressMessage.value = 'Initializing training...'
        trainingError.value = ''

        const geojsonString = projectStore.currentProject.aoi
        const geojsonFormat = new GeoJSON()
        const geometry = geojsonFormat.readGeometry(geojsonString)
        const extent = geometry.getExtent()
        const extentLatLon = transformExtent(extent, 'EPSG:3857', 'EPSG:4326')

        const response = await apiService.trainModel({
          projectId: projectStore.currentProject.id,
          aoiExtent: extent,
          aoiExtentLatLon: extentLatLon,
          basemapDates: basemapOptions.value
            .map(option => option.value)
            .filter(date => !projectStore.isDateExcluded(date)) // Exclude excluded dates
            .filter(date => projectStore.hasTrainingData(date)), // Exclude dates with no training data
          modelName: modelName.value,
          modelDescription: modelDescription.value,
          trainTestSplit: trainTestSplit.value,
          splitMethod: splitMethod.value,
          ...options.value
        })

        console.log('Model training initiated:', response)

        onDialogOK(response)
        $q.notify({
          color: 'positive',
          message: `Model ${existingModel.value ? 'updated' : 'training initiated'} successfully`,
          icon: 'check'
        })
      } catch (error) {
        console.error('Error training model:', error)
        $q.notify({
          color: 'negative',
          message: `Failed to ${existingModel.value ? 'update' : 'initiate training for'} model`,
          icon: 'error'
        })
      }
    }

    function generateDefaultModelName() {
        const today = new Date()
        const dateString = today.toISOString().split('T')[0]
        const timeString = today.toTimeString().split(' ')[0].replace(/:/g, '-')
        return `Model_${dateString}_${timeString}`
      }

      const totalArea = computed(() => {
        if (!trainingDataSummary.value) return 0
        return Object.values(trainingDataSummary.value.classStats).reduce((sum, stats) => sum + stats.totalAreaHa, 0)
      })

      const getClassColor = (className) => {
        const classObj = projectStore.currentProject?.classes.find(cls => cls.name === className)
        const col = classObj ? classObj.color : '#000000'
        return col
      }

      const getChipColor = (date) => {
        if (projectStore.isDateExcluded(date)) {
          return 'negative'
        }

        if(projectStore.hasTrainingData(date)){
          return 'primary'
        }
        return 'grey-4'
      }

      const getChipTextColor = (date) => {
        if (projectStore.isDateExcluded(date)) {
          return 'white'
        }

        if(projectStore.hasTrainingData(date)){
          return 'white'
        }
        return 'black'
      }

      return {
        dialogRef,
        onDialogHide,
        modelName,
        modelDescription,
        trainModel,
        isTraining,
        trainingProgress,
        trainingProgressMessage,
        trainingError,
        trainingDataSummary,
        availableDates,
        trainingSetsPerDate,
        options,
        splitMethod,
        trainTestSplit,
        existingModel,
        basemapOptions,
        totalArea,
        getClassColor,
        getChipColor,
        getChipTextColor,
      }
    }
  }
</script>w