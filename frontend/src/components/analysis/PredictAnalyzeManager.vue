<template>
  <div class="predict-analyze-container">
    <q-card class="basemap-dates-card">
      <q-card-section>
        <div class="text-h6">Predict & Analyze</div>
      </q-card-section>
      <q-scroll-area style="height: calc(100vh - 150px);">
        <q-list separator>
          <q-item v-for="prediction in predictions" :key="prediction.id" class="basemap-date-item">
            <q-item-section>
              <div class="row items-center justify-between">
                <div class="date-label">{{ prediction.basemap_date }}</div>
                <div class="button-group">
                  <q-checkbox v-model="selectedPredictions" :val="prediction" />
                  <q-btn icon="visibility" flat round size="sm" @click="displayOnMap(prediction.basemap_date)">
                    <q-tooltip>Display Prediction</q-tooltip>
                  </q-btn>
                  <q-btn icon="bar_chart" flat round size="sm" @click="showAnalysis(prediction)">
                    <q-tooltip>View Statistics</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
      <q-card-actions>
        <q-btn label="Compare Selected" color="primary" @click="compareSelected"
          :disable="selectedPredictions.length !== 2" />
      </q-card-actions>
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

      <q-card-section v-if="selectedAnalysis.results">
        <h6>Summary Statistics</h6>
        <q-table :rows="summaryStatisticsRows" :columns="summaryStatisticsColumns" row-key="class" dense flat
          :pagination="{ rowsPerPage: 0 }" />
        <div class="text-caption q-mt-sm">
          Total Area: {{ selectedAnalysis.results.total_area_km2.toFixed(2) }} km²
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" @click="closeAnalysis" />
      </q-card-actions>
    </q-card>

    <q-card v-if="changeAnalysis" class="change-analysis-card">
      <q-card-section>
        <div class="text-h6">Change Analysis</div>
        <div class="text-subtitle2">
          {{ changeAnalysis.prediction1_date }} to {{ changeAnalysis.prediction2_date }}
        </div>
      </q-card-section>

      <q-card-section>
        <h6>Land Cover Changes</h6>
        <q-table :rows="changeAnalysisRows" :columns="changeAnalysisColumns" row-key="class" dense flat
          :pagination="{ rowsPerPage: 0 }" />
      </q-card-section>

      <q-card-section>
        <div>Total area changed: {{ changeAnalysis.total_change_ha.toFixed(2) }} ha</div>
        <div>Change rate: {{ changeAnalysis.change_rate.toFixed(2) }}%</div>
      </q-card-section>

      <q-card-section>
        <h6>Confusion Matrix</h6>
        <q-table :rows="confusionMatrixRows" :columns="confusionMatrixColumns" row-key="predicted" dense flat
          :pagination="{ rowsPerPage: 0 }" />
      </q-card-section>
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
    const selectedPredictions = ref([]);
    const changeAnalysis = ref(null);



    const availableDates = computed(() => mapStore.availableDates);

    const summaryStatisticsColumns = [
      { name: 'class', align: 'left', label: 'Class', field: 'class' },
      { name: 'area', align: 'right', label: 'Area (km²)', field: 'area' },
      { name: 'percentage', align: 'right', label: 'Percentage', field: 'percentage' }
    ];

    const summaryStatisticsRows = computed(() => {
      if (!selectedAnalysis.value?.results?.class_statistics) return [];
      return Object.entries(selectedAnalysis.value.results.class_statistics).map(([classId, stats]) => ({
        class: projectStore.currentProject.classes[parseInt(classId)].name,
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

        predictions.value.sort((a, b) => new Date(a.basemap_date) - new Date(b.basemap_date));

        console.log('Predictions:', predictions.value)
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

    const showAnalysis = async (date) => {
      const prediction = predictions.value.find(p => p.basemap_date === date);
      if (prediction) {
        try {
          const results = await api.getSummaryStatistics(prediction.id);
          selectedAnalysis.value = {
            date,
            results
          };
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

    const compareSelected = async () => {
      if (selectedPredictions.value.length !== 2) return;

      try {
        const [pred1, pred2] = selectedPredictions.value;
        const results = await api.getChangeAnalysis(pred1.id, pred2.id);
        changeAnalysis.value = results;
      } catch (error) {
        console.error('Error fetching change analysis:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch change analysis',
          icon: 'error'
        });
      }
    };

    const changeAnalysisColumns = [
      { name: 'class', align: 'left', label: 'Class', field: 'class' },
      { name: 'area1', align: 'right', label: 'Area T1 (ha)', field: 'area1' },
      { name: 'area2', align: 'right', label: 'Area T2 (ha)', field: 'area2' },
      { name: 'change', align: 'right', label: 'Change (ha)', field: 'change' },
      { name: 'percentChange', align: 'right', label: 'Change (%)', field: 'percentChange' }
    ];

    const changeAnalysisRows = computed(() => {
      if (!changeAnalysis.value) return [];
      return changeAnalysis.value.class_names.map(className => ({
        class: className,
        area1: changeAnalysis.value.areas_time1_ha[className].toFixed(2),
        area2: changeAnalysis.value.areas_time2_ha[className].toFixed(2),
        change: changeAnalysis.value.changes_ha[className].toFixed(2),
        percentChange: ((changeAnalysis.value.changes_ha[className] / changeAnalysis.value.areas_time1_ha[className]) * 100).toFixed(2)
      }));
    });

    const confusionMatrixColumns = computed(() => {
      if (!changeAnalysis.value) return [];
      return [
        { name: 'predicted', align: 'left', label: 'Predicted', field: 'predicted' },
        ...changeAnalysis.value.class_names.map(className => ({
          name: className,
          align: 'right',
          label: className,
          field: className
        }))
      ];
    });

    const confusionMatrixRows = computed(() => {
      if (!changeAnalysis.value) return [];
      return changeAnalysis.value.class_names.map((className, i) => {
        const row = { predicted: className };
        changeAnalysis.value.class_names.forEach((actualClass, j) => {
          row[actualClass] = `${changeAnalysis.value.confusion_matrix[i][j]} (${changeAnalysis.value.confusion_matrix_percent[i][j].toFixed(2)}%)`;
        });
        return row;
      });
    });

    return {
      availableDates,
      selectedAnalysis,
      summaryStatisticsColumns,
      summaryStatisticsRows,
      formatDate,
      formatLabel,
      formatValue,
      hasPrediction,
      showAnalysis,
      displayOnMap,
      closeAnalysis,
      predictions,
      selectedPredictions,
      changeAnalysis,
      compareSelected,
      changeAnalysisColumns,
      changeAnalysisRows,
      confusionMatrixColumns,
      confusionMatrixRows,
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

.basemap-dates-card,
.statistics-card {
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