<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 800px; max-width: 90vw;">
      <q-card-section>
        <div class="text-h6">XGBoost Model Training</div>
      </q-card-section>

      <q-card-section>
        <q-stepper v-model="step" vertical color="primary" animated>
          <!-- Step 1: Model Name and Description -->
          <q-step :name="1" title="Name Your Model" icon="create" :done="step > 1">
            <q-input v-model="modelName" label="Model Name" :rules="[val => !!val || 'Model name is required']" />
            <q-input v-model="modelDescription" label="Model Description (Optional)" type="textarea" />
            <q-stepper-navigation>
              <q-btn @click="step = 2" color="primary" label="Next" />
            </q-stepper-navigation>
          </q-step>

          <!-- Step 2: Select Training Data -->
          <q-step :name="2" title="Select Training Data" icon="dataset" :done="step > 2">
            <p>Select one or more training polygon sets to use for model training:</p>
            <q-table :rows="trainingSets" :columns="columns" row-key="id" selection="multiple"
              v-model:selected="selectedTrainingSets" :filter="filter">
              <template v-slot:top-right>
                <q-input borderless dense debounce="300" v-model="filter" placeholder="Search">
                  <template v-slot:append>
                    <q-icon name="search" />
                  </template>
                </q-input>
              </template>
            </q-table>
            <q-stepper-navigation>
              <q-btn flat @click="step = 1" color="primary" label="Back" class="q-mr-sm" />
              <q-btn @click="step = 3" color="primary" label="Next" />
            </q-stepper-navigation>
          </q-step>

          <!-- Step 3: Model Parameters -->
          <q-step :name="3" title="Set Model Parameters" icon="settings" :done="step > 3">
        <div class="row q-col-gutter-md">
          <div class="col-12">
            <p>Choose split method:</p>
            <q-btn-toggle
              v-model="splitMethod"
              :options="[
                {label: 'Pixel-based', value: 'pixel'},
                {label: 'Feature-based', value: 'feature'}
              ]"
              color="primary"
            />
            <p class="text-caption q-mt-sm">
              Feature-based split ensures independence between training and testing data by splitting entire polygons.
              Pixel-based split may mix pixels from the same polygon in both training and testing sets.
            </p>
          </div>
          <div class="col-12">
            <p>Adjust the train/test split:</p>
            <q-slider v-model="trainTestSplit" :min="0.1" :max="0.5" :step="0.05" label label-always
              color="primary" />
            <p class="text-caption">
              This determines the proportion of data used for testing. A value of {{ trainTestSplit }} means
              {{ (trainTestSplit * 100).toFixed(0) }}% of the {{ splitMethod === 'pixel' ? 'pixels' : 'features' }} will be used for testing, and
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
            <q-stepper-navigation>
              <q-btn flat @click="step = 2" color="primary" label="Back" class="q-mr-sm" />
              <q-btn @click="trainModel" color="primary" label="Train Model" />
            </q-stepper-navigation>
          </q-step>
        </q-stepper>
      </q-card-section>
    </q-card>
  </q-dialog>

  <training-progress :show="isTraining" :progress="trainingProgress" :progressMessage="trainingProgressMessage"
    :error="trainingError" />
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useDialogPluginComponent, useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import apiService from 'src/services/api'
import { GeoJSON } from 'ol/format'
import { transformExtent } from 'ol/proj'
import TrainingProgress from 'components/TrainingProgress.vue'
import { io } from 'socket.io-client';

export default {
  name: 'ModelTrainingDialog',
  components: {
    TrainingProgress
  },
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()

    const generateDefaultModelName = () => {
      const today = new Date();
      const dateString = today.toISOString().split('T')[0]; // YYYY-MM-DD
      const timeString = today.toTimeString().split(' ')[0].replace(/:/g, '-'); // HH-MM-SS
      return `Model_${dateString}_${timeString}`;
    };

    const step = ref(1)
    const modelName = ref(generateDefaultModelName())
    const modelDescription = ref('')
    const trainingSets = ref([])
    const selectedTrainingSets = ref([])
    const filter = ref('')
    const isTraining = ref(false)
    const trainingProgress = ref(0)
    const trainingProgressMessage = ref('')
    const trainingError = ref('')
    const socket = io('http://127.0.0.1:5000');
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

    const columns = [
      { name: 'id', align: 'left', label: 'ID', field: 'id', sortable: true },
      { name: 'name', align: 'left', label: 'Name', field: 'name', sortable: true },
      { name: 'basemap_date', align: 'left', label: 'Basemap Date', field: 'basemap_date', sortable: true },
      { name: 'feature_count', align: 'left', label: 'Feature Count', field: 'feature_count', sortable: true },
      { name: 'created_at', align: 'left', label: 'Created At', field: 'created_at', sortable: true },
    ]

    onMounted(async () => {
      try {
        const response = await apiService.getTrainingPolygons(projectStore.currentProject.id)
        trainingSets.value = response.data

        // Pre-select the current training set if it exists
        if (projectStore.currentTrainingSet) {
          selectedTrainingSets.value = [projectStore.currentTrainingSet]
        }
      } catch (error) {
        console.error('Error fetching training sets:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch training sets',
          icon: 'error'
        })
      }

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
          if (data.message === "Training complete") {
            isTraining.value = false;
            $q.notify({
              type: 'positive',
              message: 'Training completed successfully!'
            });
          }
        }
      });
    })

    const trainModel = async () => {
      if (selectedTrainingSets.value.length === 0) {
        $q.notify({
          color: 'negative',
          message: 'Please select at least one training dataset',
          icon: 'error'
        })
        return
      }

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
          aoiExtent: extentLatLon,
          modelName: modelName.value,
          modelDescription: modelDescription.value,
          trainingSetIds: selectedTrainingSets.value.map(set => set.id),
          trainTestSplit: trainTestSplit.value,
          splitMethod: splitMethod.value,  // Add this line
          ...options.value
        })

        console.log('Model training initiated:', response)
        onDialogOK(response)
        $q.notify({
          color: 'positive',
          message: 'Model training initiated successfully',
          icon: 'check'
        })
      } catch (error) {
        console.error('Error training model:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to initiate model training',
          icon: 'error'
        })
      }
    }

    // Watch for changes in the currentTrainingSet
    watch(() => projectStore.currentTrainingSet, (newSet) => {
      if (newSet) {
        // Update the selection if the current training set changes
        const isAlreadySelected = selectedTrainingSets.value.some(set => set.id === newSet.id)
        if (!isAlreadySelected) {
          selectedTrainingSets.value = [newSet, ...selectedTrainingSets.value]
        }
      }
    })

    return {
      dialogRef,
      onDialogHide,
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      step,
      modelName,
      modelDescription,
      options,
      trainModel,
      trainingSets,
      selectedTrainingSets,
      columns,
      filter,
      isTraining,
      trainingProgress,
      trainingProgressMessage,
      trainingError,
      trainTestSplit,
      splitMethod
    }
  }
}
</script>