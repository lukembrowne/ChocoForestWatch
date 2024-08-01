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

     <!-- Save/Update buttons -->
     <div class="q-gutter-sm">
            <q-btn v-if="!existingTrainingSet" label="Save New Training Set" color="positive"
                @click="openSaveDialog('new')" :disable="drawnPolygons.length === 0 || !selectedBasemapDate" />
            <q-btn v-if="existingTrainingSet" label="Update Training Set" color="primary"
                @click="openSaveDialog('update')" :disable="drawnPolygons.length === 0 || !selectedBasemapDate" />
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
                    <q-input v-model="trainingSetName" label="Training Set Name"
                        :rules="[val => !!val || 'Name is required']" />
                </q-card-section>

                <q-card-actions align="right">
                    <q-btn flat label="Cancel" color="primary" v-close-popup />
                    <q-btn flat :label="saveMode === 'update' ? 'Update' : 'Save'" color="primary"
                        @click="saveOrUpdateTrainingSet" />
                </q-card-actions>
            </q-card>
        </q-dialog>

  </div>
</template>

<script>
import { ref, computed} from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useQuasar } from 'quasar'
import LoadTrainingSetDialog from 'components/LoadTrainingSetDialog.vue';
import api from 'src/services/api';
import { getBasemapDateOptions } from 'src/utils/dateUtils'
import { storeToRefs } from 'pinia'
import apiService from 'src/services/api'


export default {
  name: 'TrainingComponent',
  setup() {
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const $q = useQuasar()

    const { currentProject } = storeToRefs(projectStore)
    const isProjectLoaded = computed(() => !!currentProject.value)
    const drawnPolygons = computed(() => mapStore.drawnPolygons)

    const basemapDateOptions = computed(() => getBasemapDateOptions())
    const selectedBasemapDate = computed(() => mapStore.basemapDate)
    const showSaveDialog = ref(false)
    const trainingSetName = ref('')
    const existingTrainingSet = ref(null)
    const saveMode = ref('new')

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
        mapStore.updateBasemap(basemapDateOptions.value.find(option => option.value === selectedSet.basemap_date)['value'])
      } catch (error) {
        console.error('Error loading training set:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load training set',
          icon: 'error'
        });
      }
    };


    const onBasemapDateChange = async (date) => {
      console.log("Basemap date changed to: ", date)
      console.log("Updating basemap")
      mapStore.updateBasemap(date['value'])
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
          basemap_date: selectedBasemapDate.value,
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

    return {
      basemapDateOptions,
      selectedBasemapDate,
      onBasemapDateChange,
      openLoadDialog,
      openSaveDialog,
      showSaveDialog,
      saveOrUpdateTrainingSet,
      existingTrainingSet,
      saveMode,
      trainingSetName,
      isProjectLoaded,
      mapStore,
      drawnPolygons
    }
  }
}
</script>