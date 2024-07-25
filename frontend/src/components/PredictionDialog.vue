<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 500px; max-width: 80vw;">
      <q-card-section>
        <div class="text-h6">Make a Prediction</div>
      </q-card-section>

      <q-card-section>
        <q-input v-model="predictionName" label="Prediction Name" :rules="[val => !!val || 'Name is required']" />

        <q-select v-model="selectedModel" :options="modelOptions" label="Select a model"
          :rules="[val => !!val || 'Model selection is required']" />

        <q-select v-model="selectedBasemapDate" :options="basemapDateOptions" label="Select basemap date"
          :rules="[val => !!val || 'Basemap date is required']" />
      </q-card-section>

      <q-card-actions align="right">
        <q-btn label="Cancel" color="primary" flat v-close-popup />
        <q-btn label="Predict" color="primary" @click="predict" :disable="!isFormValid" />
      </q-card-actions>
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
import { getBasemapDateOptions } from 'src/utils/dateUtils'  // Import the shared function
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

    const predictionName = ref('')
    const selectedModel = ref(null)
    const selectedBasemapDate = ref(null)
    const modelOptions = ref([])
    const basemapDateOptions = computed(() => getBasemapDateOptions())
    const showProgress = ref(false)
    const progress = ref(0)
    const progressMessage = ref('')

    const isFormValid = computed(() => {
      return predictionName.value && selectedModel.value && selectedBasemapDate.value
    })

    onMounted(async () => {
      try {
        const models = await apiService.getTrainedModels(projectStore.currentProject.id)
        modelOptions.value = models.map(model => ({
          label: model.name,
          value: model.id
        }))

      } catch (error) {
        console.error('Error fetching data:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch required data',
          icon: 'error'
        })
      }
    })

    const predict = async () => {
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
          modelId: selectedModel.value['value'],
          basemapDate: selectedBasemapDate.value['value'],
          predictionName: predictionName.value,
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
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      predictionName,
      selectedModel,
      selectedBasemapDate,
      modelOptions,
      basemapDateOptions,
      isFormValid,
      predict,
      showProgress,
      progress,
      progressMessage
    }
  }
}
</script>