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

      <q-separator />

      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Deforestation Maps</div>
        <q-scroll-area v-if="deforestationMaps.length > 0" style="height: 20vh;">
          <q-list separator>
            <q-item 
              v-for="map in deforestationMaps" 
              :key="map.id"
              class="map-item cursor-pointer"
              @click="displayDeforestationMap(map)"
              clickable
              v-ripple
            >
              <q-item-section>
                <div class="row items-center justify-between">
                  <div class="date-label">{{ map.name }}</div>
                  <q-icon name="visibility" size="sm">
                    <q-tooltip>View Deforestation Map</q-tooltip>
                  </q-icon>
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-scroll-area>
        <div v-else class="text-caption q-pa-md">
          No deforestation maps available. Please perform deforestation analysis first.
        </div>
      </q-card-section>

      <q-separator />

      <q-card-section v-if="changeAnalysis" class="analysis-section">
        <div class="text-subtitle1 q-mb-sm">Analysis for {{ formatDateRange(changeAnalysis.prediction1_date, changeAnalysis.prediction2_date) }}</div>
        <q-scroll-area style="height: 40vh;">
          <div v-if="changeAnalysis">
            <h6>Deforestation Statistics</h6>
            <q-table :rows="deforestationStatisticsRows" :columns="deforestationStatisticsColumns" row-key="metric" dense flat
              :pagination="{ rowsPerPage: 0 }" />
            <div class="text-caption q-mt-sm">
              Total Area Analyzed: {{ changeAnalysis.total_area_ha.toFixed(2) }} ha
            </div>
          </div>
        </q-scroll-area>
      </q-card-section>

      <q-card-section v-else class="analysis-section">
        <div class="text-subtitle1 q-mb-sm">Analysis</div>
        <p class="text-caption">Select a deforestation map to view its analysis.</p>
      </q-card-section>

      <q-separator />

      <q-card-section v-if="selectedDeforestationMap">
        <div class="text-subtitle1 q-mb-sm">Deforestation Hotspots</div>
        <div class="row q-gutter-md">
          <q-input
            v-model.number="minHotspotArea"
            type="number"
            label="Minimum Area (ha)"
            class="col"
            :rules="[val => val > 0 || 'Area must be greater than 0']"
          />
          <q-btn
            label="Detect Hotspots"
            color="warning"
            class="col"
            @click="detectHotspots"
            :loading="loadingHotspots"
          />
        </div>
        
        <!-- Hotspots List -->
        <q-scroll-area v-if="hotspots.length" style="height: 200px;" class="q-mt-md">
          <q-list separator>
            <q-item
              v-for="(hotspot, index) in hotspots"
              :key="index"
              clickable
              v-ripple
              @click="focusHotspot(hotspot)"
            >
              <q-item-section>
                <q-item-label>Hotspot #{{ index + 1 }}</q-item-label>
                <q-item-label caption>
                  Area: {{ hotspot.properties.area_ha.toFixed(2) }} ha
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  flat
                  round
                  icon="center_focus_strong"
                  @click.stop="focusHotspot(hotspot)"
                >
                  <q-tooltip>Focus on this hotspot</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-list>
        </q-scroll-area>
        
        <!-- Summary Stats -->
        <div v-if="hotspotMetadata" class="q-mt-md">
          <div class="text-caption">
            Total Hotspots: {{ hotspotMetadata.total_hotspots }}
          </div>
          <div class="text-caption">
            Total Area: {{ hotspotMetadata.total_area_ha.toFixed(2) }} ha
          </div>
        </div>
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
  name: 'DeforestationAnalysis',
  setup() {
    const mapStore = useMapStore();
    const projectStore = useProjectStore();
    const $q = useQuasar();
    const selectedAnalysis = ref(null);
    const deforestationMaps = ref([]);
    const predictions = ref([]);
    const startDate = ref(null);
    const endDate = ref(null);
    const changeAnalysis = ref(null);
    const predictionDates = computed(() => {
        return predictions.value.map(p => ({
          label: formatDate(p.basemap_date),
          value: p.basemap_date
        }));
      });

    const deforestationStatisticsColumns = [
      { name: 'metric', align: 'left', label: 'Metric', field: 'metric' },
      { name: 'value', align: 'right', label: 'Value', field: 'value' },
    ];

    const deforestationStatisticsRows = computed(() => {
      if (!changeAnalysis.value) return [];
      return [
        { metric: 'Deforested Area', value: `${changeAnalysis.value.deforested_area_ha.toFixed(2)} ha` },
        { metric: 'Deforestation Rate', value: `${changeAnalysis.value.deforestation_rate.toFixed(2)}%` },
        { metric: 'Total Forest Area (Start)', value: `${changeAnalysis.value.total_forest_area_ha.toFixed(2)} ha` },
      ];
    });

    const minHotspotArea = ref(1.0);
    const hotspots = ref([]);
    const hotspotMetadata = ref(null);
    const loadingHotspots = ref(false);
    const selectedDeforestationMap = ref(null);

    onMounted(async () => {
      await fetchPredictions();
      await fetchDeforestationMaps();
    });

    const fetchPredictions = async () => {
        try {
          predictions.value = await api.getPredictions(projectStore.currentProject.id);
          // filter to type == "land_cover"
          predictions.value = predictions.value.filter(p => p.type === "land_cover");
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
  

    const fetchDeforestationMaps = async () => {
      try {
        deforestationMaps.value = await api.getPredictions(projectStore.currentProject.id);
        // filter to type == "deforestation"
        deforestationMaps.value = deforestationMaps.value.filter(p => p.type === "deforestation");
        deforestationMaps.value.sort((a, b) => new Date(b.end_date) - new Date(a.end_date));

        console.log('Fetched deforestation maps:', deforestationMaps.value);
      } catch (error) {
        console.error('Error fetching deforestation maps:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch deforestation maps',
          icon: 'error'
        });
      }
    };

    
    const detectHotspots = async () => {
      if (!selectedDeforestationMap.value) return;
      
      loadingHotspots.value = true;
      try {
        const response = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          minHotspotArea.value
        );
        
        console.log('Deforestation hotspots:', response);
        
        hotspots.value = response.features;
        hotspotMetadata.value = response.metadata;
        
        // Add hotspots to map
        mapStore.addGeoJSON(
          `hotspots-${selectedDeforestationMap.value.id}`,
          response,
          {
            style: {
              color: '#FF4444',
              weight: 2,
              fillOpacity: 0.2
            }
          }
        );
      } catch (error) {
        console.error('Error detecting hotspots:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to detect deforestation hotspots',
          icon: 'error'
        });
      } finally {
        loadingHotspots.value = false;
      }
    };
    
    const focusHotspot = (hotspot) => {
      mapStore.fitBounds(hotspot.geometry);
    };
    
    const displayDeforestationMap = (map) => {
      console.log('Displaying deforestation map:', map);
        if (map.file_path) {
          mapStore.displayPrediction(
            map.file_path,
            `deforestation-map-${map.id}-${Date.now()}`,
            map.name,
            'deforestation'
          );
        }


      changeAnalysis.value = map.summary_statistics;
      console.log('Change analysis:', changeAnalysis.value);

      selectedDeforestationMap.value = map;
      // Clear existing hotspots when switching maps
      hotspots.value = [];
      hotspotMetadata.value = null;
      mapStore.removeLayer(`hotspots-${map.id}`);
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

          const aoiShape = projectStore.currentProject.aoi
  
          const results = await api.getChangeAnalysis({
            prediction1_id: pred1.id,
            prediction2_id: pred2.id,
            aoi_shape: aoiShape
          });

          // update changeAnalysis with results
          changeAnalysis.value = results;

          await fetchDeforestationMaps();

  
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

      const formatDate = (dateString) => {
        const [year, month] = dateString.split('-');
        const utcDate = new Date(Date.UTC(parseInt(year), parseInt(month), 1));
        return date.formatDate(utcDate, 'MMMM, YYYY');
      };
  

    const formatDateRange = (startDate, endDate) => {
      return `${date.formatDate(startDate, 'MMM YYYY')} - ${date.formatDate(endDate, 'MMM YYYY')}`;
    };


    return {
      deforestationMaps,
      selectedAnalysis,
      deforestationStatisticsColumns,
      deforestationStatisticsRows,
      formatDateRange,
      displayDeforestationMap,
      analyzeDeforestation,
      predictionDates,
      startDate,
      endDate,
      changeAnalysis,
      minHotspotArea,
      hotspots,
      hotspotMetadata,
      loadingHotspots,
      selectedDeforestationMap,
      detectHotspots,
      focusHotspot
    };
  }
};
</script>

<style lang="scss" scoped>
.deforestation-analysis-container {
  position: absolute;
  height: calc(100vh - 60px - 100px);
  width: 300px;
  overflow-y: auto;
}

.analysis-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.map-item {
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