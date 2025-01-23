<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 1000px; max-width: 90vw;">
      <q-card-section class="row items-center justify-between section-header">
        <div class="text-h6">{{ t(`training.modelTraining.title.${existingModel ? 'update' : 'train'}`) }}</div>
        <div class="row items-center q-gutter-sm">
          <span v-if="!isValidConfiguration" class="text-negative text-caption">
            {{ validationMessage }}
          </span>
          <div class="row q-gutter-sm">
            <q-btn flat :label="t('training.modelTraining.buttons.cancel')" color="primary" v-close-popup />
            <q-btn 
              :label="t(`training.modelTraining.buttons.${existingModel ? 'update' : 'train'}`)"
              color="primary" 
              @click="validateAndTrain"
              :disable="!isValidConfiguration"
            >
              <q-tooltip v-if="!isValidConfiguration">
                {{ validationMessage }}
              </q-tooltip>
            </q-btn>
          </div>
        </div>
      </q-card-section>

      <q-card-section v-if="trainingDataSummary" class="q-pa-sm">
        <div class="row q-col-gutter-md justify-center items-center">
          <div class="col-3">
            <q-card class="bg-primary text-white">
              <q-card-section class="q-pa-sm">
                <div class="text-h6">{{ trainingDataSummary.totalSets }}</div>
                <div class="text-subtitle2">{{ t('training.modelTraining.dataSummary.totalSets') }}</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-3">
            <q-card class="bg-secondary text-white">
              <q-card-section class="q-pa-sm">
                <div class="text-h6">{{ totalArea.toFixed(2) }} ha</div>
                <div class="text-subtitle2">{{ t('training.modelTraining.dataSummary.totalArea') }}</div>
              </q-card-section>
            </q-card>
          </div>

        <q-markup-table flat bordered dense class="q-ma-lg">
          <thead>
            <tr>
              <th class="text-left">{{ t('training.modelTraining.dataSummary.class') }}</th>
              <th class="text-right">{{ t('training.modelTraining.dataSummary.features') }}</th>
              <th class="text-right">{{ t('training.modelTraining.dataSummary.area') }}</th>
              <th class="text-right">{{ t('training.modelTraining.dataSummary.percentage') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(stats, className) in trainingDataSummary.classStats" :key="className">
              <td class="text-left">
                <q-chip dense :color="getClassColor(className)" text-color="black" square>
                  {{ className }}
                </q-chip>
              </td>
              <td class="text-right">{{ stats.featureCount }}</td>
              <td class="text-right">{{ stats.totalAreaHa.toFixed(2) }}</td>
              <td class="text-right">{{ ((stats.totalAreaHa / totalArea) * 100).toFixed(1) }}%</td>
            </tr>
          </tbody>
        </q-markup-table>
        </div>
      </q-card-section>

        <div class="q-mt-sm">
          <div class="section-header">
            <div class="text-h6">{{ t('training.modelTraining.dataSummary.trainingDates') }}</div>
          </div>
          <div class="row q-gutter-xs q-ma-sm">
            <q-chip
              v-for="date in basemapOptions"
              :key="date['value']"
              :color="getChipColor(date['value'])"
              :text-color="getChipTextColor(date['value'])"
              dense
            >
              {{ date['label'] }}
            </q-chip>
          </div>
        </div>

      <q-card-section class="section-header q-pa-sm">
        <div class="text-h6">{{ t('training.modelTraining.parameters.title')  }}</div>
      </q-card-section>

      <q-card-section>
          <div class="row q-col-gutter-md q-ma-sm">
            <div class="col-3">
              <p>{{ t('training.modelTraining.parameters.splitMethod.title') }}</p>
              <q-radio v-model="splitMethod" val="feature" 
                :label="t('training.modelTraining.parameters.splitMethod.feature')" color="primary" />
              <q-radio v-model="splitMethod" val="pixel" 
                :label="t('training.modelTraining.parameters.splitMethod.pixel')" color="primary" />
              <p class="text-caption q-mt-sm">
                {{ t('training.modelTraining.parameters.splitMethod.featureDescription') }}
              </p>
            </div>
            <div class="col-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.trainTest.title') }}</p>
              <q-slider v-model="trainTestSplit" :min="0.1" :max="0.5" :step="0.05" label label-always
                color="primary" />
              <p class="text-caption">
                {{ t('training.modelTraining.parameters.trainTest.description', {
                  value: trainTestSplit,
                  percent: (trainTestSplit * 100).toFixed(0),
                  remaining: (100 - trainTestSplit * 100).toFixed(0)
                }) }}
              </p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.estimators.title') }}:</p>
              <q-slider v-model="options.n_estimators" :min="10" :max="1000" :step="10" label label-always
                color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.estimators.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.maxDepth.title') }}:</p>
              <q-slider v-model="options.max_depth" :min="1" :max="10" :step="1" label label-always color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.maxDepth.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.learningRate.title') }}:</p>
              <q-slider v-model="options.learning_rate" :min="0.01" :max="0.3" :step="0.01" label label-always
                color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.learningRate.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.minChildWeight.title') }}:</p>
              <q-slider v-model="options.min_child_weight" :min="1" :max="10" :step="1" label label-always
                color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.minChildWeight.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.gamma.title') }}:</p>
              <q-slider v-model="options.gamma" :min="0" :max="1" :step="0.1" label label-always color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.gamma.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.subsample.title') }}:</p>
              <q-slider v-model="options.subsample" :min="0.5" :max="1" :step="0.1" label label-always
                color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.subsample.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.modelParams.colsample.title') }}:</p>
              <q-slider v-model="options.colsample_bytree" :min="0.5" :max="1" :step="0.1" label label-always
                color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.modelParams.colsample.description') }}</p>
            </div>
            <div class="col-12 col-md-3">
              <p class="q-mb-lg">{{ t('training.modelTraining.parameters.sieveFilter.title') }}</p>
              <q-slider v-model="options.sieve_size" :min="0" :max="100" :step="5" label label-always color="primary" />
              <p class="text-caption">{{ t('training.modelTraining.parameters.sieveFilter.description') }}</p>
            </div>
          </div>
      </q-card-section>
    </q-card>
  </q-dialog>

  <training-progress 
    :show="isTraining" 
    :progress="trainingProgress" 
    :progressMessage="trainingProgressMessage"
    :error="trainingError" 
    @cancel="handleCancel" 
    @complete="handleTrainingComplete" 
  />
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDialogPluginComponent, useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import apiService from 'src/services/api'
import { GeoJSON } from 'ol/format'
import { transformExtent } from 'ol/proj'
import TrainingProgress from 'components/models/TrainingProgress.vue'
import { getBasemapDateOptions } from 'src/utils/dateUtils';
import { useI18n } from 'vue-i18n'



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
    const { t } = useI18n()

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
    const splitMethod = ref('feature')  // Default to feature-based split
    const trainTestSplit = ref(0.2)

    const options = ref({
      n_estimators: 500,
      max_depth: 6,
      learning_rate: 0.1,
      min_child_weight: 1,
      gamma: 0,
      subsample: 0.8,
      colsample_bytree: 0.8,
      sieve_size: 10
    })

    const pollInterval = ref(null);
    const trainingTaskId = ref(null);


    // Clean up on component unmount
    onUnmounted(() => {
      if (pollInterval.value) {
        clearInterval(pollInterval.value);
      }
    });

    onMounted(async () => {
      await fetchTrainingDataSummary()
      await checkExistingModel()
    })


    const handleTrainingComplete = () => {
      // Clear the polling interval
      if (pollInterval.value) {
        clearInterval(pollInterval.value);
      }
      
      // Reset training state
      isTraining.value = false;
      trainingProgress.value = 0;
      trainingProgressMessage.value = '';
      trainingError.value = '';
      trainingTaskId.value = null;
      
      // Close the dialog
      dialogRef.value.hide();
      
      // Optionally refresh the model list or other data
      // You might want to emit an event or call a store action here
    };

    const startProgressPolling = async (taskId) => {
      if (!taskId) {
        console.error('No taskId provided for polling');
        return;
      }

      trainingTaskId.value = taskId;
      if (pollInterval.value) {
        clearInterval(pollInterval.value);
      }

      pollInterval.value = setInterval(async () => {
        try {
          console.log('Polling progress for task:', taskId);
          const response = await apiService.getModelTrainingProgress(taskId);
          const progress = response.data;

          isTraining.value = true;
          trainingProgress.value = progress.progress;
          trainingProgressMessage.value = progress.message;

          if (progress.error) {
            trainingError.value = progress.error;
            clearInterval(pollInterval.value);
          }

          if (progress.status === 'completed' || progress.status === 'failed') {
            clearInterval(pollInterval.value);
            if (progress.status === 'completed') {
              trainingProgress.value = 100;  // Ensure progress is 100%
              trainingProgressMessage.value = 'Training completed successfully';
              // Dialog will auto-close via TrainingProgress component
            } else {
              trainingError.value = progress.message || 'Training failed';
              $q.notify({
                type: 'negative',
                message: 'Model training failed'
              });
            }
          }
        } catch (err) {
          console.error('Error polling progress:', err);
          trainingError.value = 'Error checking training progress';
          clearInterval(pollInterval.value);
        }
      }, 2000);
    };

    const handleCancel = async () => {
      try {
        if (trainingTaskId.value) {  // Use the stored taskId
          await apiService.cancelModelTraining(trainingTaskId.value);
          clearInterval(pollInterval.value);
          isTraining.value = false;
          trainingError.value = 'Training cancelled by user';
          $q.notify({
            type: 'warning',
            message: 'Model training cancelled'
          });
        }
      } catch (err) {
        console.error('Error canceling training:', err);
        $q.notify({
          type: 'negative',
          message: 'Error canceling training'
        });
      }
    };


    async function checkExistingModel() {
      try {
        const response = await apiService.getTrainedModels(projectStore.currentProject.id)
        console.log('Existing models from checkExistingModel:', response.data)
        if (response.data.length > 0) {
          console.log('Setting existing model:', response.data[0])
          existingModel.value = response.data[0]
          modelName.value = existingModel.value.name
          modelDescription.value = existingModel.value.description

          // Populate model parameters from existing model
          if (existingModel.value.model_parameters) {
            console.log('Existing model parameters:', existingModel.value.model_parameters)
            const params = existingModel.value.model_parameters
            console.log("Params: ", params);
            console.log("Gamma: ", params.gamma);
            options.value = {
              n_estimators: params.n_estimators ? params.n_estimators : 'NA',
              max_depth: params.max_depth ? params.max_depth : 'NA',
              learning_rate: params.learning_rate ? params.learning_rate : 'NA',
              min_child_weight: params.min_child_weight ? params.min_child_weight : 'NA',
              gamma: params.gamma ?? 'NA',
              subsample: params.subsample ? params.subsample : 'NA',
              colsample_bytree: params.colsample_bytree ? params.colsample_bytree : 'NA',
              sieve_size: params.sieve_size ? params.sieve_size : 'NA'
            }

            // Set split method and train/test split if they exist
            if (params.split_method) {
              splitMethod.value = params.split_method
            }
            if (params.train_test_split) {
              trainTestSplit.value = params.train_test_split
            }
          }

          console.log('Loaded existing model parameters:', options.value)
        }
      } catch (error) {
        console.error('Error checking existing model:', error)
      }
    }

    async function fetchTrainingDataSummary() {
      try {
        const response = await apiService.getTrainingDataSummary(projectStore.currentProject.id);
        trainingDataSummary.value = response.data;
        console.log("Training data summary: ", trainingDataSummary.value);
      } catch (error) {
        console.error('Error fetching training data summary:', error);
        $q.notify({
          color: 'negative',
          message: error.response?.data?.error || 'Failed to fetch training data summary',
          icon: 'error'
        });
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

        // Get training set IDs for dates that have training data and aren't excluded
        const trainingSetIds = projectStore.trainingPolygonSets
          .filter(set => !projectStore.isDateExcluded(set.basemap_date))
          .filter(set => set.feature_count > 0)
          .map(set => set.id)

        if (trainingSetIds.length === 0) {
          throw new Error('No training data available. Please create training data first.')
        }

        const response = await apiService.trainModel({
          project_id: projectStore.currentProject.id,
          aoi_shape: geojsonString,
          aoi_extent: extent,
          aoi_extent_lat_lon: extentLatLon,
          training_set_ids: trainingSetIds,
          model_name: modelName.value,
          model_description: modelDescription.value,
          model_parameters: { 
            ...options.value, 
            train_test_split: trainTestSplit.value, 
            split_method: splitMethod.value 
          }
        })

        console.log('Model training initiated:', response)
        startProgressPolling(response.data.taskId)

      } catch (error) {
        console.error('Error training model:', error)
        isTraining.value = false
        $q.notify({
          color: 'negative',
          message: error.message || `Failed to ${existingModel.value ? 'update' : 'initiate training for'} model`,
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

      if (projectStore.hasTrainingData(date)) {
        return 'primary'
      }
      return 'grey-4'
    }

    const getChipTextColor = (date) => {
      if (projectStore.isDateExcluded(date)) {
        return 'white'
      }

      if (projectStore.hasTrainingData(date)) {
        return 'white'
      }
      return 'black'
    }

    // Modify the hasMinimumFeaturesPerClass computed property
    const hasMinimumFeaturesPerClass = computed(() => {
      if (!trainingDataSummary.value?.classStats) return false;
      
      // Check if any class has exactly 1 feature (invalid)
      for (const [className, stats] of Object.entries(trainingDataSummary.value.classStats)) {
        if (stats.featureCount === 1) {
          return false;
        }
      }
      
      // Check if we have at least two classes with features
      const classesWithFeatures = Object.values(trainingDataSummary.value.classStats)
        .filter(stats => stats.featureCount > 0)
        .length;
      
      return classesWithFeatures >= 2;
    });

    // Modify the isValidConfiguration computed property
    const isValidConfiguration = computed(() => {
      // First check if we have minimum features per class
      if (!hasMinimumFeaturesPerClass.value) {
        return false;
      }

      // Check if any option is NA or NaN
      for (const [key, value] of Object.entries(options.value)) {
        if (value === 'NA' || value === null || isNaN(value)) {
          return false;
        }
      }

      // Check if we have training data
      if (!trainingDataSummary.value?.totalSets) {
        return false;
      }

      // Validate specific parameter ranges
      return (
        options.value.n_estimators >= 10 &&
        options.value.max_depth >= 1 &&
        options.value.learning_rate > 0 &&
        options.value.min_child_weight >= 1 &&
        options.value.gamma >= 0 &&
        options.value.subsample > 0 &&
        options.value.subsample <= 1 &&
        options.value.colsample_bytree > 0 &&
        options.value.colsample_bytree <= 1
      );
    });

    // Modify the validateAndTrain method to give more specific error messages
    const validateAndTrain = async () => {
      if (!hasMinimumFeaturesPerClass.value) {
        const classesWithOneFeature = Object.entries(trainingDataSummary.value.classStats)
          .filter(([_, stats]) => stats.featureCount === 1)
          .map(([className]) => className);
          
        if (classesWithOneFeature.length > 0) {
          $q.notify({
            type: 'negative',
            message: t('training.modelTraining.validation.oneFeature'),
            caption: t('training.modelTraining.validation.oneFeatureCaption', { 
              classes: classesWithOneFeature.join(', ') 
            })
          });
          return;
        }
        
        if (classesWithFeatures < 2) {
          $q.notify({
            type: 'negative',
            message: t('training.modelTraining.validation.twoClasses'),
            caption: t('training.modelTraining.validation.twoClassesCaption')
          });
          return;
        }
      }

      if (!isValidConfiguration.value) {
        $q.notify({
          type: 'negative',
          message: t('training.modelTraining.validation.invalidConfig')
        });
        return;
      }

      // Proceed with training
      await trainModel();
    };

    const validationMessage = computed(() => {
      if (!trainingDataSummary.value?.classStats) {
        return t('training.modelTraining.validation.noData');
      }

      // Check for classes with exactly 1 feature
      const classesWithOneFeature = Object.entries(trainingDataSummary.value.classStats)
        .filter(([_, stats]) => stats.featureCount === 1)
        .map(([className]) => className);
      
      if (classesWithOneFeature.length > 0) {
        return t('training.modelTraining.validation.oneFeature');
      }

      // Check if we have at least two classes with features
      const classesWithFeatures = Object.values(trainingDataSummary.value.classStats)
        .filter(stats => stats.featureCount > 0)
        .length;
      
      if (classesWithFeatures < 2) {
        return t('training.modelTraining.validation.twoClasses');
      }

      // Check model parameters
      for (const [key, value] of Object.entries(options.value)) {
        if (value === 'NA' || value === null || isNaN(value)) {
          return t('training.modelTraining.validation.parameterErrors.invalid', {
            param: key.replace(/_/g, ' ')
          });
        }
      }

      // Validate parameter ranges
      if (options.value.n_estimators < 10) return t('training.modelTraining.validation.parameterErrors.estimators');
      if (options.value.max_depth < 1) return t('training.modelTraining.validation.parameterErrors.maxDepth');
      if (options.value.learning_rate <= 0) return t('training.modelTraining.validation.parameterErrors.learningRate');
      if (options.value.min_child_weight < 1) return t('training.modelTraining.validation.parameterErrors.minChildWeight');
      if (options.value.gamma < 0) return t('training.modelTraining.validation.parameterErrors.gamma');
      if (options.value.subsample <= 0 || options.value.subsample > 1) return t('training.modelTraining.validation.parameterErrors.subsample');
      if (options.value.colsample_bytree <= 0 || options.value.colsample_bytree > 1) return t('training.modelTraining.validation.parameterErrors.colsample');

      return '';
    });

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
      handleCancel,
      handleTrainingComplete,
      isValidConfiguration,
      validateAndTrain,
      validationMessage,
      t,
    }
  }
}
</script>

<style scoped>
.q-dialog-plugin {
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.q-card-section {
  padding: 12px;
}

/* Make the table more compact */
:deep(.q-table th), :deep(.q-table td) {
  padding: 4px 8px;
}

/* Ensure chips are compact */
:deep(.q-chip) {
  min-height: 24px;
  padding: 0 8px;
}

.text-negative {
  color: var(--q-negative);
}

.validation-message {
  font-size: 0.8rem;
  max-width: 300px;
  white-space: normal;
}
</style>