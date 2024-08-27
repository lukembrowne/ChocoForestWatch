<template>
 <div class="predict-analyze-container">
    <q-card class="basemap-dates-card">
      <q-card-section>
        <div class="text-h6">Predict & Analyze</div>
      </q-card-section>
      <q-scroll-area style="height: calc(100vh - 150px);">
        <q-list separator>
          <q-item v-for="date in availableDates" :key="date.value" class="basemap-date-item">
            <q-item-section>
              <div class="row items-center justify-between">
                <div class="date-label">{{ date }}</div>
                <div class="button-group">
                  <q-btn v-if="!date.hasPrediction" icon="add" flat round size="sm" @click="generatePrediction(date)">
                    <q-tooltip>Generate Prediction</q-tooltip>
                  </q-btn>
                  <q-btn v-if="hasPrediction(date)" icon="visibility" flat round size="sm" @click="displayOnMap(date)">
                    <q-tooltip>Display Prediction</q-tooltip>
                  </q-btn>
                  <q-btn v-if="hasPrediction(date)" icon="bar_chart" flat round size="sm" @click="showAnalysis(date)">
                    <q-tooltip>View Statistics</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-card>

    <q-card v-if="selectedAnalysis" class="analysis-card">
      <q-card-section>
        <div class="text-h6">Analysis for {{ formatDate(selectedAnalysis.date) }}</div>
      </q-card-section>

      <q-card-section v-if="selectedAnalysis.results.summary">
        <h6>Summary Statistics</h6>
        <div v-for="(value, key) in selectedAnalysis.results.summary" :key="key" class="q-mb-sm">
          <strong>{{ formatLabel(key) }}:</strong> {{ formatValue(value) }}
        </div>
      </q-card-section>

      <q-card-section v-if="selectedAnalysis.results.class_statistics">
        <h6>Class Statistics</h6>
        <q-table :rows="classStatisticsRows" :columns="classStatisticsColumns" row-key="class" dense flat
          :pagination="{ rowsPerPage: 0 }" />
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Display on Map" color="primary" @click="displayOnMap" />
        <q-btn flat label="Close" color="primary" @click="closeAnalysis" />
      </q-card-actions>
    </q-card>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { useProjectStore } from 'src/stores/projectStore'
import { date } from 'quasar';
import api from 'src/services/api'
import { useQuasar } from 'quasar'

export default {
  name: 'PredictAnalyzeManager',
  setup() {
    const mapStore = useMapStore();
    const projectStore = useProjectStore()
    const $q = useQuasar()
    const selectedAnalysis = ref(null);
    const predictions = ref([])


    const availableDates = computed(() => mapStore.availableDates);

    const classStatisticsColumns = [
      { name: 'class', align: 'left', label: 'Class', field: 'class' },
      { name: 'area', align: 'right', label: 'Area (km²)', field: 'area' },
      { name: 'percentage', align: 'right', label: 'Percentage', field: 'percentage' }
    ];

    const classStatisticsRows = computed(() => {
      if (!selectedAnalysis.value?.results.class_statistics) return [];
      return Object.entries(selectedAnalysis.value.results.class_statistics).map(([className, stats]) => ({
        class: className,
        area: stats.area_km2.toFixed(2),
        percentage: `${stats.percentage.toFixed(2)}%`
      }));
    });

    onMounted(async () => {
      await fetchPredictions()
      console.log('Predictions:', predictions.value)
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

    const formatDate = (dateString) => {
      return date.formatDate(dateString, 'MMMM, YYYY');
    };

    const formatLabel = (key) => {
      return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    };

    const formatValue = (value) => {
      if (typeof value === 'number') {
        return value.toFixed(2);
      }
      return value;
    };

    const hasPrediction = (date) => {
      return predictions.value.some(p => p.basemap_date === date)
    };

    const generatePrediction = (date) => {
      // TODO: Implement logic to generate prediction for the given date
      console.log('Generating prediction for', date);
    };

    const showAnalysis = (date) => {
      // TODO: Fetch analysis results for the given date
      selectedAnalysis.value = {
        date,
        results: {
          // Dummy data, replace with actual fetched data
          summary: { total_area: 1000, prediction_date: date },
          class_statistics: {
            'Class A': { area_km2: 500, percentage: 50 },
            'Class B': { area_km2: 500, percentage: 50 }
          }
        }
      };
    };

    const displayOnMap = async (date) => {
      const prediction = predictions.value.find(p => p.basemap_date === date)
            if (prediction) {
                await loadPredictionOnMap(prediction)
            }
      mapStore.updateBasemap(date)
    };

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

    const closeAnalysis = () => {
      selectedAnalysis.value = null;
    };

    return {
      availableDates,
      selectedAnalysis,
      classStatisticsColumns,
      classStatisticsRows,
      formatDate,
      formatLabel,
      formatValue,
      hasPrediction,
      generatePrediction,
      showAnalysis,
      displayOnMap,
      closeAnalysis
    };
  }
};
</script>

<style lang="scss" scoped>
.predict-analyze-container {
  position: absolute;
  top: 50px;
  left: 10px;
  display: flex;
  gap: 10px;
}

.basemap-dates-card, .statistics-card {
  width: 300px;
  max-height: calc(100vh - 60px);
  border-radius: 8px;
  overflow: hidden;
}

.basemap-date-item {
  border-radius: 8px;
  margin: 8px;
  background-color: #f5f5f5;
  transition: background-color 0.3s;

  &:hover {
    background-color: #e0e0e0;
  }
}

.date-label {
  font-weight: bold;
}

.button-group {
  display: flex;
  gap: 8px;
}
</style>