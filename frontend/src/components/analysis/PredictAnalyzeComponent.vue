<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-card class="predict-analyze-component" style="width: 900px; max-width: 90vw;">
            <q-card-section class="row items-center q-pb-none">
                <div class="text-h6">Predict and Analyze Land Cover</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section>
                <q-btn label="New Prediction" color="primary" @click="openNewPredictionDialog" class="q-mb-md" />

                <q-table :rows="predictions" :columns="predictionColumns" row-key="id" selection="multiple"
                    v-model:selected="selectedPredictions" :pagination="{ rowsPerPage: 10 }">
                    <template v-slot:body-cell-actions="props">
                        <q-td :props="props">
                            <q-btn flat round icon="visibility" @click="loadPredictionOnMap(props.row)">
                                <q-tooltip>Load on map</q-tooltip>
                            </q-btn>
                            <q-btn flat round icon="assessment" @click="showAnalysisResults(props.row)">
                                <q-tooltip>View analysis</q-tooltip>
                            </q-btn>
                            <q-btn flat round icon="edit" @click.stop="openRenameDialog(props.row)">
                                <q-tooltip>Rename</q-tooltip>
                            </q-btn>
                            <q-btn flat round icon="delete" @click.stop="confirmDelete(props.row)">
                                <q-tooltip>Delete</q-tooltip>
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

    <!-- Nested dialogs -->

    <q-dialog v-model="showRenameDialog">
        <q-card style="min-width: 350px">
            <q-card-section>
                <div class="text-h6">Rename Prediction</div>
            </q-card-section>

            <q-card-section class="q-pt-none">
                <q-input v-model="newPredictionName" label="New Prediction Name" dense />
            </q-card-section>

            <q-card-actions align="right" class="text-primary">
                <q-btn flat label="Cancel" v-close-popup />
                <q-btn flat label="Rename" @click="renamePrediction" v-close-popup />
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
import NewPredictionDialog from './NewPredictionDialog.vue'
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
        const showPredictionDialog = ref(false)
        const showRenameDialog = ref(false)
        const newPredictionName = ref('')
        const predictionToRename = ref(null)

        const predictionColumns = [
            { name: 'name', required: true, label: 'Name', align: 'left', field: row => row.name, sortable: true },
            { name: 'actions', align: 'center', label: 'Actions' },
            { name: 'model_name', align: 'left', label: 'Model', field: 'model_name', sortable: true },
            { name: 'basemap_date', align: 'left', label: 'Basemap Date', field: 'basemap_date', sortable: true },
            { name: 'created_at', align: 'left', label: 'Created At', field: 'created_at', sortable: true },
        ]

        onMounted(async () => {
            await fetchPredictions()
        })

        const fetchPredictions = async () => {
            try {
                predictions.value = await api.getPredictions(projectStore.currentProject.id)
            } catch (error) {
                console.error('Error fetching predictions:', error)
                $q.notify({
                    color: 'negative',
                    message: 'Failed to fetch predictions',
                    icon: 'error'
                })
            }
        }

        const openNewPredictionDialog = () => {
            try {
                $q.dialog({
                    component: NewPredictionDialog,
                }).onOk(async () => {
                    await fetchPredictions()
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

        const openRenameDialog = (prediction) => {
            predictionToRename.value = prediction
            newPredictionName.value = prediction.name
            showRenameDialog.value = true
        }

        const renamePrediction = async () => {
            try {
                await api.renamePrediction(predictionToRename.value.id, newPredictionName.value)
                await fetchPredictions()
                $q.notify({
                    color: 'positive',
                    message: 'Prediction renamed successfully',
                    icon: 'check'
                })
            } catch (error) {
                console.error('Error renaming prediction:', error)
                $q.notify({
                    color: 'negative',
                    message: 'Failed to rename prediction',
                    icon: 'error'
                })
            }
        }

        const confirmDelete = (prediction) => {
            $q.dialog({
                title: 'Confirm Delete',
                message: `Are you sure you want to delete the prediction "${prediction.name}"?`,
                cancel: true,
                persistent: true
            }).onOk(async () => {
                try {
                    await api.deletePrediction(prediction.id)
                    await fetchPredictions()
                    $q.notify({
                        color: 'positive',
                        message: 'Prediction deleted successfully',
                        icon: 'check'
                    })
                } catch (error) {
                    console.error('Error deleting prediction:', error)
                    $q.notify({
                        color: 'negative',
                        message: 'Failed to delete prediction',
                        icon: 'error'
                    })
                }
            })
        }

        return {
            dialogRef,
            onDialogHide,
            onDialogOK,
            onDialogCancel,
            predictions,
            selectedPredictions,
            predictionColumns,
            showPredictionDialog,
            showRenameDialog,
            newPredictionName,
            openNewPredictionDialog,
            loadPredictionOnMap,
            showAnalysisResults,
            comparePredictions,
            openRenameDialog,
            renamePrediction,
            confirmDelete
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