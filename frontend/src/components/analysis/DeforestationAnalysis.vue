<!-- frontend/src/components/analysis/DeforestationAnalysis.vue -->
<template>
    <div class="deforestation-analysis-container">
      <q-card class="analysis-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">Deforestation Analysis</div>
          <div class="row q-gutter-md">
            <q-select v-model="startDate" :options="predictionDates" label="Start Date" class="col" />
            <q-select v-model="endDate" :options="predictionDates" label="End Date" class="col" />
          </div>
          <q-btn label="Analyze Deforestation" color="primary" class="q-mt-sm" @click="analyzeDeforestation"
            :disable="!startDate || !endDate || startDate === endDate" />
        </q-card-section>
      </q-card>
  
      <q-card v-if="changeAnalysis" class="results-card">
        <q-card-section>
          <div class="text-h6">Deforestation Analysis Results</div>
          <div class="text-subtitle2">
            {{ formatDate(changeAnalysis.prediction1_date) }} to {{ formatDate(changeAnalysis.prediction2_date) }}
          </div>
        </q-card-section>
  
        <q-card-section>
          <div class="text-h5">Deforestation Rate: {{ changeAnalysis.deforestation_rate.toFixed(2) }}%</div>
          <div>Deforested Area: {{ changeAnalysis.deforested_area_ha.toFixed(2) }} ha</div>
          <div>Total Forest Area (initial): {{ changeAnalysis.total_forest_area_ha.toFixed(2) }} ha</div>
        </q-card-section>
  
        <q-card-section>
          <h6>Forest Transition Matrix</h6>
          <q-table :rows="forestTransitionRows" :columns="forestTransitionColumns" row-key="from" dense flat
            :pagination="{ rowsPerPage: 0 }" />
        </q-card-section>
  
        <q-card-actions align="right">
          <q-btn label="Display Deforestation Map" color="primary" @click="displayDeforestationMap" />
          <q-btn flat label="Close" color="primary" @click="closeChangeAnalysis" />
        </q-card-actions>
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
    name: 'DeforestationAnalysis',
    setup() {
      const mapStore = useMapStore();
      const projectStore = useProjectStore();
      const $q = useQuasar();
      const predictions = ref([]);
      const changeAnalysis = ref(null);
      const startDate = ref(null);
      const endDate = ref(null);
  
      const predictionDates = computed(() => {
        return predictions.value.map(p => ({
          label: formatDate(p.basemap_date),
          value: p.basemap_date
        }));
      });
  
      onMounted(async () => {
        await fetchPredictions();
      });
  
      const fetchPredictions = async () => {
        try {
          predictions.value = await api.getPredictions(projectStore.currentProject.id);
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
  
      const formatDate = (dateString) => {
        const [year, month] = dateString.split('-');
        const utcDate = new Date(Date.UTC(parseInt(year), parseInt(month), 1));
        return date.formatDate(utcDate, 'MMMM, YYYY');
      };
  
      const analyzeDeforestation = async () => {
        if (!startDate.value || !endDate.value) {
          $q.notify({
            color: 'negative',
            message: 'Please select both start and end dates.'
          });
          return;
        }
  
        if (startDate.value === endDate.value) {
          $q.notify({
            color: 'negative',
            message: 'Start and end dates must be different.'
          });
          return;
        }
  
        try {
          const pred1 = predictions.value.find(p => p.basemap_date === startDate.value.value);
          const pred2 = predictions.value.find(p => p.basemap_date === endDate.value.value);
  
          if (!pred1 || !pred2) {
            $q.notify({
              color: 'negative',
              message: 'Could not find predictions for the selected dates.'
            });
            return;
          }
  
          const results = await api.getChangeAnalysis(pred1.id, pred2.id);
          changeAnalysis.value = results;
  
          $q.notify({
            color: 'positive',
            message: 'Deforestation analysis completed successfully.',
            icon: 'check'
          });
        } catch (error) {
          console.error('Error analyzing deforestation:', error);
          $q.notify({
            color: 'negative',
            message: 'Failed to analyze deforestation',
            icon: 'error'
          });
        }
      };
  
      const displayDeforestationMap = () => {
        if (changeAnalysis.value && changeAnalysis.value.deforestation_raster_path) {
          mapStore.displayPrediction(
            changeAnalysis.value.deforestation_raster_path,
            `deforestation-${changeAnalysis.value.prediction1_date}-${changeAnalysis.value.prediction2_date}`,
            `Deforestation-${changeAnalysis.value.prediction1_date}-${changeAnalysis.value.prediction2_date}`,
            'deforestation'
          );
        }
      };
  
      const closeChangeAnalysis = () => {
        changeAnalysis.value = null;
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

    return {
      startDate,
      endDate,  
      predictionDates,
      changeAnalysis,
      forestTransitionColumns,
      forestTransitionRows,
      formatDate,
      analyzeDeforestation,
      displayDeforestationMap,
      closeChangeAnalysis,
    };
  }
};
</script>

<style lang="scss" scoped>
.deforestation-analysis-container {
  position: absolute;
  display: flex;
  gap: 10px;
}

.analysis-card,
.results-card {
  width: 300px;
  max-height: calc(100vh - 60px);
  border-radius: 8px;
  overflow: hidden;
}
</style>