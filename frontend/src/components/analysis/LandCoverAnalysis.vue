<!-- frontend/src/components/analysis/LandCoverMaps.vue -->
<template>
  <div class="land-cover-analysis-container">
    <q-card class="analysis-card">
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Land Cover Predictions</div>
        <!-- Scroll area to display predictions if available -->
        <q-scroll-area v-if="predictions.length > 0" style="height: 20vh;">
          <q-list separator>
            <!-- Loop through predictions and display each one as a list item -->
            <q-item 
              v-for="prediction in predictions" 
              :key="prediction.id" 
              class="prediction-item cursor-pointer"
              @click="showPrediction(prediction.basemap_date)"
              clickable
              v-ripple
            >
              <q-item-section>
                <div class="row items-center justify-between">
                  <div class="date-label">{{ formatDate(prediction.basemap_date) }}</div>
                  <q-icon name="visibility" size="sm">
                    <q-tooltip>View Prediction</q-tooltip>
                  </q-icon>
                </div>  
              </q-item-section>
            </q-item>
          </q-list>
        </q-scroll-area>
        <!-- Message to display if no predictions are available -->
        <div v-else class="text-caption q-pa-md">
          No predictions available. Please train a model and make land cover predictions first.
        </div>
      </q-card-section>

      <q-separator />

      <!-- Section to display analysis of the selected prediction -->
      <q-card-section v-if="selectedAnalysis" class="analysis-section">
        <div class="text-subtitle1 q-mb-sm">Analysis for {{ formatDate(selectedAnalysis.date) }}</div>
        <q-scroll-area style="height: 40vh;">
          <div v-if="selectedAnalysis.results">
            <h6>Summary Statistics</h6>
            <!-- Table to display summary statistics of the analysis -->
            <q-table :rows="summaryStatisticsRows" :columns="summaryStatisticsColumns" row-key="class" dense flat
              :pagination="{ rowsPerPage: 0 }" />
            <div class="text-caption q-mt-sm">
              Total Area: {{ selectedAnalysis.results.total_area_ha.toFixed(2) }} ha
            </div>
          </div>
        </q-scroll-area>
      </q-card-section>

      <!-- Message to display if no analysis is selected -->
      <q-card-section v-else class="analysis-section">
        <div class="text-subtitle1 q-mb-sm">Analysis</div>
        <p class="text-caption">Select a prediction to view its analysis.</p>
      </q-card-section>
    </q-card>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { useProjectStore } from 'src/stores/projectStore';
import { date } from 'quasar';
import api from 'src/services/api';
import { useQuasar } from 'quasar';

export default {
  name: 'LandCoverMaps',
  setup() {
    const mapStore = useMapStore();
    const projectStore = useProjectStore();
    const $q = useQuasar();
    const selectedAnalysis = ref(null); // Ref to store the selected analysis
    const predictions = ref([]); // Ref to store the list of predictions

    // Columns configuration for the summary statistics table
    const summaryStatisticsColumns = [
      { name: 'class', align: 'left', label: 'Class', field: 'class' },
      { name: 'area', align: 'right', label: 'Area (ha)', field: 'area' },
      { name: 'percentage', align: 'right', label: 'Percentage', field: 'percentage' }
    ];

    // Computed property to generate rows for the summary statistics table
    const summaryStatisticsRows = computed(() => {
      if (!selectedAnalysis.value?.results?.class_statistics) return [];
      return Object.entries(selectedAnalysis.value.results.class_statistics).map(([classId, stats]) => ({
        class: projectStore.currentProject.classes[parseInt(classId)].name,
        area: stats.area_ha.toFixed(2),
        percentage: `${stats.percentage.toFixed(2)}%`
      }));
    });

    // Fetch predictions when the component is mounted
    onMounted(async () => {
      await fetchPredictions();
    });

    // Function to fetch predictions from the API
    const fetchPredictions = async () => {
      try {
        let response = await api.getPredictions(projectStore.currentProject.id);

        predictions.value = response.data;
        console.log("Predictions fetched:", predictions.value);

        // Filter predictions to only include those of type "land_cover"
        predictions.value = predictions.value.filter(p => p.type === "land_cover");
        // Sort predictions by date
        predictions.value.sort((a, b) => new Date(a.basemap_date) - new Date(b.basemap_date));
      } catch (error) {
        console.error('Error fetching predictions:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch predictions',
          icon: 'error'
        });
      }
    };

    // Function to format a date string into "MMMM, YYYY"
    const formatDate = (dateString) => {
      const [year, month] = dateString.split('-');
      const utcDate = new Date(Date.UTC(parseInt(year), parseInt(month), 1));
      return date.formatDate(utcDate, 'MMMM, YYYY');
    };

    // Function to show analysis for a selected prediction date
    const showAnalysis = async (date) => {
      const prediction = predictions.value.find(p => p.basemap_date === date);
      if (prediction) {
        try {
          const response = await api.getSummaryStatistics(prediction.id);
          console.log("showAnalysis results:", response.data);
          selectedAnalysis.value = { date, results: response.data };
        } catch (error) {
          console.error('Error fetching summary statistics:', error);
          $q.notify({
            color: 'negative',
            message: 'Failed to fetch summary statistics',
            icon: 'error'
          });
        }
      }
    };

    // Function to display a prediction on the map
    const displayOnMap = async (date) => {
      const prediction = predictions.value.find(p => p.basemap_date === date);
      if (prediction) {
        await loadPredictionOnMap(prediction);
      }
      mapStore.updateBasemap(date);
      const dateIndex = mapStore.availableDates.findIndex(d => d === date);
      if (dateIndex !== -1) {
        mapStore.updateSliderValue(dateIndex);
      }
    };

    // Function to load a prediction on the map
    const loadPredictionOnMap = async (prediction) => {
      try {
        // Format the date for the layer title
        const date_title = formatDate(prediction.basemap_date);
        console.log("loadPredictionOnMap prediction:", prediction);
        await mapStore.displayPrediction(
          prediction.file,
          `prediction-${prediction.id}-${Date.now()}`,
          `Land Cover - ${date_title}`,
          'prediction'
        );
        
        $q.notify({
          color: 'positive',
          message: `Loaded land cover map for: ${date_title}`,
          icon: 'check' 
        });
      } catch (error) {
        console.error('Error loading prediction on map:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load land cover map',
          icon: 'error'
        });
      }
    };

    // Function to close the analysis view
    const closeAnalysis = () => {
      selectedAnalysis.value = null;
    };

    // Function to show a prediction and its analysis
    const showPrediction = async (date) => {
      await displayOnMap(date);
      await showAnalysis(date);
    };

    return {
      predictions,
      selectedAnalysis,
      summaryStatisticsColumns,
      summaryStatisticsRows,
      formatDate,
      showAnalysis,
      displayOnMap,
      closeAnalysis,
      showPrediction,
    };
  }
};
</script>

<style lang="scss" scoped>
.land-cover-analysis-container {
  position: absolute;
  height: calc(100vh - 60px - 100px); /* 20px for additional padding */
  width: 300px;
  overflow-y: auto; /* Add scrolling if content exceeds the height */
}

.analysis-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.prediction-item {
    border-radius: 8px;
    margin: 4px;
    background-color: #f5f5f5;
    transition: background-color 0.3s;
  
    &:hover {
      background-color: rgba(0, 0, 0, 0.05);
    }
  }

  .date-label {
    font-weight: bold;
  }

.analysis-section {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}
</style>