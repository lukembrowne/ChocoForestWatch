<template>
  <div class="predict-analyze-container">
    <q-card class="basemap-dates-card">
      <q-card-section>
        <div class="text-h6">Predict & Analyze</div>
      </q-card-section>
      <q-card-actions>

        <q-btn label="Evaluate Model" color="primary" @click="openModelEvaluationDialog"/>

        <q-btn label="Compare Selected" color="primary" @click="compareSelected"
          :disable="selectedPredictions.length !== 2" />

          <q-btn label="Deforestation Analysis" color="primary" @click="deforestationTimeSeriesAnalysis" />
      </q-card-actions>

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
                  <q-btn icon="bar_chart" flat round size="sm" @click="showAnalysis(prediction.basemap_date)">
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
      <div class="text-h6">Deforestation Analysis</div>
      <div class="text-subtitle2">
        {{ changeAnalysis.prediction1_date }} to {{ changeAnalysis.prediction2_date }}
      </div>
    </q-card-section>

    <q-card-section>
      <div class="text-h5">Deforestation Rate: {{ changeAnalysis.deforestation_rate.toFixed(2) }}%</div>
      <div>Deforested Area: {{ changeAnalysis.deforested_area_ha.toFixed(2) }} ha</div>
      <div>Total Forest Area (initial): {{ changeAnalysis.total_forest_area_ha.toFixed(2) }} ha</div>
    </q-card-section>

    <q-card-section>
      <h6>Forest Transition Matrix</h6>
      <q-table
        :rows="forestTransitionRows"
        :columns="forestTransitionColumns"
        row-key="from"
        dense
        flat
        :pagination="{ rowsPerPage: 0 }"
      />
    </q-card-section>

    <q-card-actions align="right">
      <q-btn label="Display Deforestation Map" color="primary" @click="displayDeforestationMap" />
      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" @click="closeChangeAnalysis" />
      </q-card-actions>
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
import ModelEvaluationDialog from 'components/models/ModelEvaluationDialog.vue'


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

    const openModelEvaluationDialog = async () => {
      $q.dialog({
        component: ModelEvaluationDialog
      })
    }

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
      console.log('Showing analysis for date:', date)
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
        await mapStore.displayPrediction(prediction.file_path, `prediction-${prediction.id}`, prediction.name, 'prediction')
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

    const closeChangeAnalysis = () => {
      changeAnalysis.value = null;
    };

    const displayDeforestationMap = () => {
      if (changeAnalysis.value && changeAnalysis.value.deforestation_raster_path) {
        mapStore.displayPrediction(changeAnalysis.value.deforestation_raster_path, `deforestation-${changeAnalysis.value.prediction1_date}-${changeAnalysis.value.prediction2_date}`, `Deforestation-${changeAnalysis.value.prediction1_date}-${changeAnalysis.value.prediction2_date}`, 'deforestation');
      }
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

    const deforestationTimeSeriesAnalysis = async () => {

      try {
        const results = await api.getDeforestationAnalysis(projectStore.currentProject.id);

        console.log('Deforestation analysis:', results)

        mapStore.displayPrediction(results.deforestation_raster_path, `deforestation-time-series`, `Deforestation-time-series`, 'deforestation');
      } catch (error) {

        console.error('Error fetching deforestation analysis:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch deforestation analysis',
          icon: 'error'
        });
      }
    };
    const forestTransitionColumns = [
      { name: 'from', align: 'left', label: 'From', field: 'from' },
      { name: 'forest', align: 'right', label: 'To Forest', field: 'forest' },
      { name: 'nonForest', align: 'right', label: 'To Non-Forest', field: 'nonForest' },
    ];

    const forestTransitionRows = computed(() => {
      if (!changeAnalysis.value) return [];
      const forestIndex = changeAnalysis.value.class_names.indexOf('Forest');
      const matrix = changeAnalysis.value.confusion_matrix;
      const total = matrix[forestIndex].reduce((a, b) => a + b, 0);
      return [
        {
          from: 'Forest',
          forest: `${matrix[forestIndex][forestIndex]} (${((matrix[forestIndex][forestIndex] / total) * 100).toFixed(2)}%)`,
          nonForest: `${total - matrix[forestIndex][forestIndex]} (${(((total - matrix[forestIndex][forestIndex]) / total) * 100).toFixed(2)}%)`
        }
      ];
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
      closeChangeAnalysis,
      predictions,
      selectedPredictions,
      changeAnalysis,
      compareSelected,
      confusionMatrixColumns,
      confusionMatrixRows,
      forestTransitionColumns,
      forestTransitionRows,
      displayDeforestationMap,
      deforestationTimeSeriesAnalysis,
      openModelEvaluationDialog
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