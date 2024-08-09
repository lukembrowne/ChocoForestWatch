<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-card class="predict-analyze-component" style="width: 900px; max-width: 90vw;">
            <q-card-section class="row items-center q-pb-none">
                <div class="text-h6">Analyze Land Cover Predictions</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section>
                <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-6">
                        <q-select v-model="selectedDate" :options="availableDates" label="Select Date"
                            @update:model-value="loadPredictionForDate" />
                    </div>
                    <div class="col-12 col-md-6">
                        <q-btn label="View Analysis" color="primary" @click="showAnalysisResults"
                            :disable="!selectedDate" />
                    </div>
                </div>

                <q-table :rows="predictions" :columns="predictionColumns" row-key="id"
                    :pagination="{ rowsPerPage: 10 }">
                    <template v-slot:body-cell-actions="props">
                        <q-td :props="props">
                            <q-btn flat round icon="visibility" @click="loadPredictionOnMap(props.row)">
                                <q-tooltip>Load on map</q-tooltip>
                            </q-btn>
                            <q-btn flat round icon="assessment" @click="showAnalysisResults(props.row)">
                                <q-tooltip>View analysis</q-tooltip>
                            </q-btn>
                        </q-td>
                    </template>
                </q-table>
            </q-card-section>

            <q-card-actions align="right">
                <q-btn flat label="Close" color="primary" v-close-popup />
                <q-btn flat label="Compare Selected" color="secondary" @click="comparePredictions"
                    :disabled="selectedPredictions.length !== 2" />
            </q-card-actions>
        </q-card>
    </q-dialog>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useQuasar, useDialogPluginComponent } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import api from 'src/services/api'
import AnalysisResultsDialog from './AnalysisResultsDialog.vue'

export default {
    name: 'PredictAnalyzeComponent',
    emits: [
        ...useDialogPluginComponent.emits
    ],
    setup() {
        const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
        const $q = useQuasar()
        const projectStore = useProjectStore()
        const mapStore = useMapStore()
        const predictions = ref([])
        const selectedPredictions = ref([])
        const availableDates = ref([])
        const selectedDate = ref(null)


        const predictionColumns = [
            { name: 'basemap_date', align: 'left', label: 'Date', field: 'basemap_date', sortable: true },
            { name: 'actions', align: 'center', label: 'Actions' }
        ]

        onMounted(async () => {
            await fetchPredictions()
        })

        const fetchPredictions = async () => {
            try {
                predictions.value = await api.getPredictions(projectStore.currentProject.id)
                availableDates.value = predictions.value.map(p => p.basemap_date).sort()

            } catch (error) {
                console.error('Error fetching predictions:', error)
                $q.notify({
                    color: 'negative',
                    message: 'Failed to fetch predictions',
                    icon: 'error'
                })
            }
        }


        const loadPredictionForDate = async (date) => {
            const prediction = predictions.value.find(p => p.basemap_date === date)
            if (prediction) {
                await loadPredictionOnMap(prediction)
            }
        }

        const loadPredictionOnMap = async (prediction) => {
            try {
                await mapStore.displayPrediction(prediction.file_path, `prediction-${prediction.id}`, prediction.name)
                $q.notify({
                    color: 'positive',
                    message: `Loaded prediction: ${prediction.name}`,
                    icon: 'check'
                })
            } catch (error) {
                console.error('Error loading prediction on map:', error)
                $q.notify({
                    color: 'negative',
                    message: 'Failed to load prediction on map',
                    icon: 'error'
                })
            }
        }

        const showAnalysisResults = async (prediction) => {
            try {
                const results = await api.getSummaryStatistics(prediction.id)
                $q.dialog({
                    component: AnalysisResultsDialog,
                    componentProps: {
                        results: results
                    }
                })
            } catch (error) {
                console.error('Error fetching analysis results:', error)
                $q.notify({
                    color: 'negative',
                    message: 'Failed to fetch analysis results',
                    icon: 'error'
                })
            }
        }

        const comparePredictions = async () => {
            if (selectedPredictions.value.length !== 2) {
                $q.notify({
                    color: 'warning',
                    message: 'Please select exactly two predictions to compare',
                    icon: 'warning'
                })
                return
            }

            try {
                const results = await api.getChangeAnalysis(selectedPredictions.value[0].id, selectedPredictions.value[1].id)
                $q.dialog({
                    component: AnalysisResultsDialog,
                    componentProps: {
                        results: results
                    }
                })
            } catch (error) {
                console.error('Error comparing predictions:', error)
                $q.notify({
                    color: 'negative',
                    message: 'Failed to compare predictions',
                    icon: 'error'
                })
            }
        }
      

        return {
            dialogRef,
            onDialogHide,
            onDialogOK,
            onDialogCancel,
            predictions,
            selectedPredictions,
            predictionColumns,
            loadPredictionOnMap,
            showAnalysisResults,
            comparePredictions,
            loadPredictionForDate,
            availableDates,
            selectedDate
        }
    }
}
</script>

<style lang="scss" scoped>
.predict-analyze-component {
    display: flex;
    flex-direction: column;
    max-height: 90vh;

    .q-card-section {
        overflow-y: auto;
    }
}
</style>