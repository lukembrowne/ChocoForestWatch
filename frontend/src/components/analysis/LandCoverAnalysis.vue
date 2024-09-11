<!-- frontend/src/components/analysis/LandCoverMaps.vue -->
<template>
    <div class="land-cover-maps-container">
      <q-card class="predictions-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">Land Cover Predictions</div>
          <q-scroll-area style="height: calc(100vh - 150px);">
            <q-list separator>
              <q-item v-for="prediction in predictions" :key="prediction.id" class="prediction-item">
                <q-item-section>
                  <div class="row items-center justify-between">
                    <div class="date-label">{{ formatDate(prediction.basemap_date) }}</div>
                    <div class="button-group">
                      <q-btn icon="add" flat round size="sm" @click="displayOnMap(prediction.basemap_date)">
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
        </q-card-section>
      </q-card>
  
      <q-card v-if="selectedAnalysis" class="analysis-card">
        <q-card-section>
          <div class="text-h6">Analysis for {{ formatDate(selectedAnalysis.date) }}</div>
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
      const selectedAnalysis = ref(null);
      const predictions = ref([]);
  
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
  
      const showAnalysis = async (date) => {
        const prediction = predictions.value.find(p => p.basemap_date === date);
        if (prediction) {
          try {
            const results = await api.getSummaryStatistics(prediction.id);
            selectedAnalysis.value = { date, results };
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
  
      const loadPredictionOnMap = async (prediction) => {
        try {
          await mapStore.displayPrediction(prediction.file_path, `prediction-${prediction.id}`, prediction.name, 'prediction');
          $q.notify({
            color: 'positive',
            message: `Loaded prediction: ${prediction.name}`,
            icon: 'check'
          });
        } catch (error) {
          console.error('Error loading prediction on map:', error);
          $q.notify({
            color: 'negative',
            message: 'Failed to load prediction on map',
            icon: 'error'
          });
        }
      };
  
      const closeAnalysis = () => {
        selectedAnalysis.value = null;
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
      };
    }
  };
  </script>
  
  <style lang="scss" scoped>
  .land-cover-maps-container {
    position: absolute;
    display: flex;
    gap: 10px;
  }
  
  .predictions-card,
  .analysis-card {
    width: 300px;
    max-height: calc(100vh - 60px);
    border-radius: 8px;
    overflow: hidden;
  }
  
  .prediction-item {
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