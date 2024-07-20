<template>
  <div class="analysis-component">
    <h2 class="text-h5 q-mb-md">Land Cover Change Analysis</h2>
    <div v-if="currentProject">
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-6">
          <q-select
            v-model="selectedPrediction1"
            :options="predictionOptions"
            label="Select first prediction"
            option-value="id"
            option-label="label"
            emit-value
            map-options
          />
        </div>
        <div class="col-12 col-md-6">
          <q-select
            v-model="selectedPrediction2"
            :options="predictionOptions"
            label="Select second prediction"
            option-value="id"
            option-label="label"
            emit-value
            map-options
          />
        </div>
      </div>
      <q-btn
        label="Analyze Change"
        color="primary"
        @click="analyzeChange"
        :disable="!selectedPrediction1 || !selectedPrediction2"
        class="q-mt-md"
      />
      <div v-if="analysisResults" class="q-mt-lg">
        <h3 class="text-h6">Analysis Results</h3>
        <p>Deforestation Rate: {{ analysisResults.deforestationRate.toFixed(2) }}%</p>
        <p>Total Area Changed: {{ analysisResults.totalAreaChanged.toFixed(2) }} sq km</p>
        <div class="q-pa-md" style="height: 400px;">
          <Bar :data="chartData" :options="chartOptions" />
        </div>
      </div>
    </div>
    <div v-else class="text-h6 text-center q-pa-md">
      Please select a project to perform analysis.
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import apiService from 'src/services/api'
import { useProjectStore } from 'src/stores/projectStore'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

export default {
  name: 'AnalysisComponent',
  components: {
    Bar
  },
  emits: ['step-completed'],
  setup(props, { emit }) {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const selectedPrediction1 = ref(null)
    const selectedPrediction2 = ref(null)
    const predictions = ref([])
    const analysisResults = ref(null)

    const currentProject = computed(() => projectStore.currentProject)

    const predictionOptions = computed(() => {
      return predictions.value.map(p => ({
        label: p.basemap_date,
        value: p.id
      }))
    })

    const fetchPredictions = async () => {
      if (!currentProject.value) return

      try {
        const response = await apiService.getPredictions(currentProject.value.id)
        predictions.value = response.map(prediction => ({
          id: prediction.id,
          basemap_date: prediction.basemap_date
        }))
      } catch (error) {
        console.error('Error fetching predictions:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch predictions',
          icon: 'error'
        })
      }
    }

    // Watch for changes in the currentProject
    watch(currentProject, (newProject) => {
      if (newProject) {
        fetchPredictions()
      } else {
        // Clear predictions when no project is selected
        predictions.value = []
        selectedPrediction1.value = null
        selectedPrediction2.value = null
        analysisResults.value = null
      }
    }, { immediate: true })

    const analyzeChange = async () => {
      if (!selectedPrediction1.value || !selectedPrediction2.value) return

      try {
        const results = await apiService.analyzeChange(selectedPrediction1.value['value'], selectedPrediction2.value['value'])
        analysisResults.value = results.data
        $q.notify({
          color: 'positive',
          message: 'Analysis completed successfully',
          icon: 'check'
        })
        emit('step-completed')
      } catch (error) {
        console.error('Error analyzing change:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to analyze change',
          icon: 'error'
        })
      }
    }

    const chartData = computed(() => {
      if (!analysisResults.value) return { labels: [], datasets: [] }

      return {
        labels: ['Forest', 'Non-Forest'],
        datasets: [
          {
            label: 'Previous',
            backgroundColor: '#8884d8',
            data: [
              analysisResults.value.previousForestArea,
              analysisResults.value.previousNonForestArea
            ]
          },
          {
            label: 'Current',
            backgroundColor: '#82ca9d',
            data: [
              analysisResults.value.currentForestArea,
              analysisResults.value.currentNonForestArea
            ]
          }
        ]
      }
    })

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Area (sq km)'
          }
        }
      }
    }

    return {
      currentProject,
      selectedPrediction1,
      selectedPrediction2,
      predictionOptions,
      analysisResults,
      analyzeChange,
      chartData,
      chartOptions
    }
  }
}
</script>