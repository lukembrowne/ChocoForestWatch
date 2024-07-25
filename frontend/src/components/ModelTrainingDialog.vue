<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 800px; max-width: 90vw;">
      <q-card-section>
        <div class="text-h6">XGBoost Model Training Options</div>
      </q-card-section>

      <q-card-section>
        <q-input v-model="modelName" label="Model Name" :rules="[val => !!val || 'Model name is required']" />
      </q-card-section>

      <q-card-section>
        <div class="text-subtitle2 q-mb-sm">Select Training Datasets</div>
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
      </q-card-section>

      <q-card-section>
        <q-form @submit="trainModel">
          <div class="q-mb-md">
            <div class="text-subtitle2">Number of Estimators</div>
            <q-slider v-model="options.n_estimators" :min="10" :max="1000" :step="10" label label-always
              color="primary" />
            <div class="text-caption">The number of trees in the forest. Higher values generally improve performance but
              increase training time.</div>
          </div>

          <div class="q-mb-md">
            <div class="text-subtitle2">Max Depth</div>
            <q-slider v-model="options.max_depth" :min="1" :max="10" :step="1" label label-always color="primary" />
            <div class="text-caption">Maximum depth of the trees. Higher values make the model more complex and prone to
              overfitting.</div>
          </div>

          <div class="q-mb-md">
            <div class="text-subtitle2">Learning Rate</div>
            <q-slider v-model="options.learning_rate" :min="0.01" :max="0.3" :step="0.01" label label-always
              color="primary" />
            <div class="text-caption">Step size shrinkage used to prevent overfitting. Lower values are generally better
              but
              require more iterations.</div>
          </div>

          <div class="q-mb-md">
            <div class="text-subtitle2">Min Child Weight</div>
            <q-slider v-model="options.min_child_weight" :min="1" :max="10" :step="1" label label-always
              color="primary" />
            <div class="text-caption">Minimum sum of instance weight needed in a child. Higher values make the model
              more
              conservative.</div>
          </div>

          <div class="q-mb-md">
            <div class="text-subtitle2">Gamma</div>
            <q-slider v-model="options.gamma" :min="0" :max="1" :step="0.1" label label-always color="primary" />
            <div class="text-caption">Minimum loss reduction required to make a further partition. Higher values make
              the
              model more conservative.</div>
          </div>
        </q-form>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn label="Cancel" color="primary" flat v-close-popup />
        <q-btn label="Train Model" color="primary" @click="trainModel" :disable="selectedTrainingSets.length === 0" />
      </q-card-actions>
    </q-card>


    <training-progress :show="isTraining" :progress="trainingProgress" :progressMessage="trainingProgressMessage"
      :error="trainingError" />

  </q-dialog>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
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

    const modelName = ref(`Model_${new Date().toISOString().slice(0, 10)}`)
    const trainingSets = ref([])
    const selectedTrainingSets = ref([])
    const filter = ref('')
    const isTraining = ref(false)
    const trainingProgress = ref(0)
    const trainingProgressMessage = ref('')
    const trainingError = ref('')
    const socket = io('http://127.0.0.1:5000');


    const options = ref({
      n_estimators: 100,
      max_depth: 3,
      learning_rate: 0.1,
      min_child_weight: 1,
      gamma: 0,
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
          trainingSetIds: selectedTrainingSets.value.map(set => set.id),
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


    onUnmounted(() => {
      socket.off('training_update');
      socket.disconnect();
    });


    return {
      dialogRef,
      onDialogHide,
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      modelName,
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
    }
  }
}
</script>