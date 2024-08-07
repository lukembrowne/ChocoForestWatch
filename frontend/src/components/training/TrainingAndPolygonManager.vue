<template>
    <div class="training-and-polygon-manager">
        <q-card class="manager-card">
            <q-card-section>
                <div class="text-h6">Training Set Manager</div>
                <div v-if="!currentTrainingSet">
                    <q-btn label="Load Training Set" @click="openLoadDialog" color="primary"
                        class="q-mb-sm full-width" />
                    <q-btn label="Save New Training Set" @click="openSaveDialog('new')" color="secondary"
                        class="full-width" />
                </div>
                <div v-else>
                    <div class="text-h6 q-mb-sm">Current Training Set: {{ currentTrainingSet.name }}</div>

                    <q-btn label="Save Changes" color="positive" @click="openSaveDialog('update')"
                        class="q-mb-sm full-width" :disable="!selectedBasemapDate" />
                    <q-btn label="Save As New" color="secondary" @click="openSaveDialog('new')"
                        :disable="!selectedBasemapDate" class="q-mb-sm full-width" />
                    <q-btn label="Load Different Set" @click="openLoadDialog" color="primary"
                        class="q-mb-sm full-width" />

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

            </q-card-section>

            <q-separator />
        </q-card>


        <q-card v-if="drawnPolygons.length > 0" class="polygon-list-card">
            <q-card-section class="q-pa-sm">
                <div class="text-h6">Training Polygons</div>
                <div class="summary q-gutter-xs">
                    <div v-for="(summary, className) in classSummary" :key="className">
                        {{ className }}: {{ summary.count }} features, {{ summary.area.toFixed(1) }} ha
                    </div>
                </div>
            </q-card-section>
            <q-separator />
            <p>Polygon list</p>
            <q-card-section class="polygon-list q-pa-none">
                <q-list dense>
                    <q-item v-for="(polygon, index) in drawnPolygons" :key="index" class="q-py-xs">
                        <q-item-section avatar>
                            <q-icon name="lens" :style="{ color: getClassColor(polygon.properties.classLabel) }"
                                size="xs" />
                        </q-item-section>
                        <q-item-section>
                            <q-item-label>{{ polygon.properties.classLabel }}</q-item-label>
                            <q-item-label caption>{{ (calculateArea(polygon) / 10000).toFixed(1) }} ha</q-item-label>
                        </q-item-section>
                        <q-item-section side>
                            <q-btn flat round dense color="negative" icon="delete" size="sm"
                                @click="deletePolygon(index)" />
                        </q-item-section>
                    </q-item>
                </q-list>
            </q-card-section>
        </q-card>



    </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'
import { useQuasar } from 'quasar'
import api from 'src/services/api'
import LoadTrainingSetDialog from './LoadTrainingSetDialog.vue'
import apiService from 'src/services/api'

export default {
    name: 'TrainingAndPolygonManager',
    setup() {
        const mapStore = useMapStore()
        const projectStore = useProjectStore()
        const $q = useQuasar()
        const currentTrainingSet = ref(null)
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)
        
        const projectId = computed(() => projectStore.currentProject?.id)
        const showSaveDialog = ref(false)
        const trainingSetName = ref('')
        const existingTrainingSet = ref(null)
        const saveMode = ref('new')
        const drawnPolygons = computed(() => mapStore.drawnPolygons)
        

        // Loading and saving training set functions
        const openLoadDialog = () => {
            $q.dialog({
                component: LoadTrainingSetDialog,
            }).onOk(async (selectedSet) => {
                try {
                    const response = await api.getSpecificTrainingPolygons(projectId.value, selectedSet.id)
                    currentTrainingSet.value = selectedSet
                    mapStore.loadPolygons(response.data)
                    existingTrainingSet.value = selectedSet
                    trainingSetName.value = selectedSet.name
                    projectStore.setCurrentTrainingSet(selectedSet)  // Update project store
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



        // Polygon list functions
        const calculateArea = (polygon) => {
            const feature = new GeoJSON().readFeature(polygon)
            return getArea(feature.getGeometry())
        }

        const classSummary = computed(() => {
            const summary = {}
            drawnPolygons.value.forEach(polygon => {
                const classLabel = polygon.properties.classLabel
                const area = calculateArea(polygon) / 10000 // Convert to hectares
                if (!summary[classLabel]) {
                    summary[classLabel] = { count: 0, area: 0 }
                }
                summary[classLabel].count++
                summary[classLabel].area += area
            })
            return summary
        })

        const deletePolygon = (index) => {
            mapStore.deletePolygon(index)
        }

        const getClassColor = (className) => {
            const classObj = projectStore.currentProject?.classes.find(cls => cls.name === className)
            return classObj ? classObj.color : '#000000'
        }




        return {
            drawnPolygons,
            calculateArea,
            classSummary,
            deletePolygon,
            getClassColor,
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

<style lang="scss" scoped>
.training-and-polygon-manager {
    position: absolute;
    top: 50px; // Adjust this value to account for the header height
    left: 0;
    bottom: 0;
    width: 350px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
}

.manager-card {
    background-color: rgba(255, 255, 255, 1.0);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
}

.full-height {
    height: 100%;
}

.polygon-list-section {
    flex-grow: 1;
    overflow-y: auto;
}

.polygon-list-card {
    background-color: rgba(255, 255, 255, 1.0);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    overflow-y: auto;
}

.summary {
    display: flex;
    flex-wrap: wrap;
    margin-bottom: 8px;
}

.polygon-list {
    max-height: calc(100vh - 200px);
    overflow-y: auto;
}
</style>