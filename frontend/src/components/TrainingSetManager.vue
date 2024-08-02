<template>
    <div class="training-set-manager">
        <div v-if="!currentTrainingSet">
            <q-btn label="Load Training Set" @click="openLoadDialog" color="primary" class="q-mb-sm full-width" />
            <q-btn label="Save New Training Set" @click="openSaveDialog('new')" color="secondary" class="full-width" />
        </div>
        <div v-else>
            <div class="text-h6 q-mb-sm">Current Training Set: {{ currentTrainingSet.name }}</div>

            <q-btn label="Save Changes" color="positive" @click="openSaveDialog('update')" class="q-mb-sm full-width"
                :disable="!selectedBasemapDate" />
            <q-btn label="Save As New" color="secondary" @click="openSaveDialog('new')" :disable="!selectedBasemapDate"
                class="q-mb-sm full-width" />
            <q-btn label="Load Different Set" @click="openLoadDialog" color="primary" class="q-mb-sm full-width" />

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
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import api from 'src/services/api'
import LoadTrainingSetDialog from './LoadTrainingSetDialog.vue'
import apiService from 'src/services/api'


export default {
    name: 'TrainingSetManager',
    setup() {
        const $q = useQuasar()
        const mapStore = useMapStore()
        const projectStore = useProjectStore()
        const currentTrainingSet = ref(null)
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)

        const projectId = computed(() => projectStore.currentProject?.id)
        const showSaveDialog = ref(false)
        const trainingSetName = ref('')
        const existingTrainingSet = ref(null)
        const saveMode = ref('new')

        const openLoadDialog = () => {
            $q.dialog({
                component: LoadTrainingSetDialog,
                componentProps: {
                    projectId: projectId.value
                }
            }).onOk(async (selectedSet) => {
                try {
                    const response = await api.getSpecificTrainingPolygons(projectId.value, selectedSet.id)
                    currentTrainingSet.value = selectedSet
                    mapStore.loadPolygons(response.data)
                    existingTrainingSet.value = selectedSet
                    trainingSetName.value = selectedSet.name

                    mapStore.setSelectedBasemapDate(selectedSet.basemap_date)

                    $q.notify({
                        color: 'positive',
                        message: 'Training set loaded successfully',
                        icon: 'check'
                    })
                } catch (error) {
                    console.error('Error loading training set:', error)
                    $q.notify({
                        color: 'negative',
                        message: 'Failed to load training set',
                        icon: 'error'
                    })
                }
            })
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
            currentTrainingSet,
            openLoadDialog,
            showSaveDialog,
            trainingSetName,
            existingTrainingSet,
            saveMode,
            openSaveDialog,
            selectedBasemapDate,
            saveOrUpdateTrainingSet
        }
    }
}
</script>