<template>
  <div class="analysis-component">
    <h2 class="text-h5 q-mb-md">Land Cover Analysis</h2>
    <q-btn label="Perform Analysis" color="primary" @click="openAnalysisDialog" />

    <q-dialog v-model="showAnalysisDialog" persistent>
      <q-card style="width: 700px; max-width: 80vw;">
        <q-card-section>
          <div class="text-h6">Select Predictions for Analysis</div>
        </q-card-section>

        <q-card-section>

          <p>Select one prediction to calculate summary statistics or two predictions for change analysis.</p>
          <q-table :rows="predictions" :columns="predictionColumns" row-key="id" selection="multiple"
            v-model:selected="selectedPredictions">
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn flat round icon="edit" @click.stop="openRenameDialog(props.row)" />
                <q-btn flat round icon="delete" @click.stop="confirmDelete(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup @click="showAnalysisDialog.value = false" />
          <q-btn flat label="Analyze" color="primary" @click="performAnalysis" :disabled="!isSelectionValid" />
        </q-card-actions>
      </q-card>
    </q-dialog>


    <!-- Rename Dialog -->
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

    <div v-if="analysisResults" class="q-mt-md">
      <h3 class="text-h6">Analysis Results</h3>
      <div class="row">
        <div class="col-md-8 col-sm-12">
          <Bar v-if="chartData.datasets.length > 0" :data="chartData" :options="chartOptions" style="height: 400px;" />
        </div>
        <div class="col-md-4 col-sm-12">
          <q-list bordered separator>
            <q-item v-for="(value, key) in analysisResults.class_statistics" :key="key">
              <q-item-section>
                <q-item-label>Class {{ key }}</q-item-label>
                <q-item-label caption>
                  Area: {{ value.area_km2.toFixed(2) }} km² ({{ value.percentage.toFixed(2) }}%)
                </q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                <q-item-label>Total Area</q-item-label>
                <q-item-label caption>
                  {{ analysisResults.total_area_km2.toFixed(2) }} km²
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import api from 'src/services/api'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

export default {
  name: 'AnalysisComponent',
  components: {
    Bar
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const showAnalysisDialog = ref(false)
    const predictions = ref([])
    const selectedPredictions = ref([])
    const analysisResults = ref(null)
    const showRenameDialog = ref(false)
    const newPredictionName = ref('')
    const predictionToRename = ref(null)


    const predictionColumns = [
      { name: 'name', required: true, label: 'Name', align: 'left', field: row => row.name, sortable: true },
      { name: 'actions', align: 'center', label: 'Actions' },
      { name: 'date', align: 'left', label: 'Date', field: 'basemap_date', sortable: true },
      { name: 'model', align: 'left', label: 'Model', field: row => row.model, sortable: true },

    ]

    const isSelectionValid = computed(() => {
      if (selectedPredictions.value.length > 0) {
        return true
      } else {
        return false
      }
    })

    onMounted(() => {
      openAnalysisDialog()
    })

    const openAnalysisDialog = async () => {
      try {
        predictions.value = await api.getPredictions(projectStore.currentProject.id)
        showAnalysisDialog.value = true
      } catch (error) {
        console.error('Error fetching predictions:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch predictions',
          icon: 'error'
        })
      }
    }

    const performAnalysis = async () => {
      try {
        if (selectedPredictions.value.length === 1) {
          analysisResults.value = await api.getSummaryStatistics(selectedPredictions.value[0].id)
        } else if (selectedPredictions.value.length === 2) {
          analysisResults.value = await api.getChangeAnalysis(selectedPredictions.value[0].id, selectedPredictions.value[1].id)
        } else if (selectedPredictions.value.length > 2) {
          console.error('Invalid number of predictions selected')
        }
        showAnalysisDialog.value = false
      } catch (error) {
        console.error('Error performing analysis:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to perform analysis',
          icon: 'error'
        })
      }
    }

    const chartData = computed(() => {
      if (!analysisResults.value || !analysisResults.value.class_statistics) {
        return { labels: [], datasets: [] }
      }

      const classStats = analysisResults.value.class_statistics
      const labels = Object.keys(classStats).map(key => `Class ${key}`)
      const areas = Object.values(classStats).map(stat => stat.area_km2)
      const percentages = Object.values(classStats).map(stat => stat.percentage)

      return {
        labels,
        datasets: [
          {
            label: 'Area (km²)',
            backgroundColor: 'rgba(75, 192, 192, 0.6)',
            data: areas,
            yAxisID: 'y-axis-area',
          },
          {
            label: 'Percentage',
            backgroundColor: 'rgba(255, 99, 132, 0.6)',
            data: percentages,
            yAxisID: 'y-axis-percentage',
          }
        ]
      }
    })

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: false,
          title: {
            display: true,
            text: 'Land Cover Classes'
          }
        },
        'y-axis-area': {
          type: 'linear',
          position: 'left',
          title: {
            display: true,
            text: 'Area (km²)'
          },
          beginAtZero: true
        },
        'y-axis-percentage': {
          type: 'linear',
          position: 'right',
          title: {
            display: true,
            text: 'Percentage (%)'
          },
          beginAtZero: true,
          max: 100
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || ''
              if (label) {
                label += ': '
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y.toFixed(2)
                if (context.dataset.label === 'Percentage') {
                  label += '%'
                } else {
                  label += ' km²'
                }
              }
              return label
            }
          }
        },
        legend: {
          display: true,
          position: 'top'
        },
        title: {
          display: true,
          text: 'Land Cover Distribution'
        }
      }
    }
    const formatLabel = (key) => {
      return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    }

    const formatValue = (value) => {
      return typeof value === 'number' ? value.toFixed(2) : value
    }


    const openRenameDialog = (prediction) => {
      predictionToRename.value = prediction
      newPredictionName.value = prediction.name
      showRenameDialog.value = true
    }

    const renamePrediction = async () => {
      try {
        await api.renamePrediction(predictionToRename.value.id, newPredictionName.value)
        const index = predictions.value.findIndex(p => p.id === predictionToRename.value.id)
        if (index !== -1) {
          predictions.value[index].name = newPredictionName.value
        }
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
          predictions.value = predictions.value.filter(p => p.id !== prediction.id)
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
      showAnalysisDialog,
      predictions,
      predictionColumns,
      selectedPredictions,
      isSelectionValid,
      analysisResults,
      openAnalysisDialog,
      performAnalysis,
      chartData,
      chartOptions,
      formatLabel,
      formatValue,
      showRenameDialog,
      newPredictionName,
      predictionToRename,
      openRenameDialog,
      renamePrediction,
      confirmDelete
    }
  }
}
</script>