<template>
  <div class="row no-wrap" style="height: 100vh;">
    <!-- Left Panel - Analysis Controls -->
    <div class="analysis-controls-container">
      <q-card class="analysis-card">
        <q-card-section>
          <div class="text-h6">Analysis Tools</div>
          
          <!-- Analysis Mode Tabs -->
          <q-tabs
            v-model="activeTab"
            dense
            class="text-grey"
            active-color="primary"
            indicator-color="primary"
            align="justify"
            narrow-indicator
          >
            <q-tab name="deforestation" label="Deforestation" icon="forest" />
            <q-tab name="verification" label="Verify Hotspots" icon="fact_check" />
          </q-tabs>

          <!-- Dynamic Content Based on Active Tab -->
          <q-tab-panels v-model="activeTab" animated>
            <!-- Deforestation Analysis Panel -->
            <q-tab-panel name="deforestation">
              <div class="text-subtitle1 q-mb-sm">Deforestation Analysis</div>
              <div class="row q-col-gutter-md q-mb-md">
                <q-select
                  v-model="startDate"
                  :options="predictionDates"
                  label="Start Date"
                  class="col"
                />
                <q-select
                  v-model="endDate"
                  :options="predictionDates"
                  label="End Date"
                  class="col"
                />
              </div>
              <q-btn 
                label="Analyze Deforestation" 
                color="primary" 
                class="q-mb-md"
                @click="analyzeDeforestation"
                :disable="!startDate || !endDate"
              />
            </q-tab-panel>

            <!-- Hotspot Verification Panel -->
            <q-tab-panel name="verification">
              <div class="text-subtitle1 q-mb-sm">Hotspot Verification</div>
              <q-select
                v-model="selectedDeforestationMap"
                :options="deforestationMaps"
                label="Select Deforestation Map"
                option-label="name"
                class="q-mb-md"
                @update:model-value="loadHotspots"
              />
              <div class="row q-col-gutter-md q-mb-md">
                <q-input
                  v-model.number="minAreaHa"
                  type="number"
                  label="Minimum Area (ha)"
                  class="col"
                />
                <q-select
                  v-model="selectedSource"
                  :options="sourceOptions"
                  label="Alert Source"
                  class="col"
                />
              </div>
              <q-scroll-area v-if="!loading && hotspots?.length" style="height: calc(100vh - 350px)">
                <q-list separator dense>
                  <q-item 
                    v-for="(hotspot, index) in hotspots" 
                    :key="index" 
                    :class="[
                      hotspot.properties.source === 'gfw' ? 'gfw-alert' : 'ml-alert',
                      {
                        'selected-hotspot': selectedHotspot === hotspot,
                        'verified': hotspot.properties.verification_status === 'verified',
                        'rejected': hotspot.properties.verification_status === 'rejected',
                        'unsure': hotspot.properties.verification_status === 'unsure'
                      }
                    ]" 
                    clickable 
                    v-ripple 
                    @click="selectHotspot(hotspot)"
                  >
                    <q-item-section>
                      <div class="row items-center no-wrap">
                        <div class="text-weight-medium">
                          #{{ index + 1 }}
                          <q-badge :color="hotspot.properties.source === 'gfw' ? 'purple' : 'primary'">
                            {{ hotspot.properties.source.toUpperCase() }}
                          </q-badge>
                          <q-badge 
                            v-if="hotspot.properties.source === 'gfw'"
                            :color="getConfidenceColor(hotspot.properties.confidence)"
                            class="q-ml-xs"
                          >
                            {{ getConfidenceLabel(hotspot.properties.confidence) }}
                          </q-badge>
                        </div>
                        <div class="q-ml-sm">
                          {{ hotspot.properties.area_ha.toFixed(1) }} ha
                        </div>
                        <div class="q-ml-auto" :class="{
                          'text-green': hotspot.properties.verification_status === 'verified',
                          'text-blue-grey': hotspot.properties.verification_status === 'rejected',
                          'text-amber': hotspot.properties.verification_status === 'unsure'
                        }">
                          {{ hotspot.properties.verification_status || 'Unverified' }}
                        </div>
                      </div>
                    </q-item-section>

                    <q-item-section side>
                      <div class="row q-gutter-xs">
                        <q-btn flat round size="sm" color="green" icon="check_circle"
                          @click.stop="verifyHotspot(hotspot, 'verified')">
                          <q-tooltip>Verify Deforestation</q-tooltip>
                        </q-btn>
                        <q-btn flat round size="sm" color="amber" icon="help"
                          @click.stop="verifyHotspot(hotspot, 'unsure')">
                          <q-tooltip>Mark as Unsure</q-tooltip>
                        </q-btn>
                        <q-btn flat round size="sm" color="blue-grey" icon="cancel"
                          @click.stop="verifyHotspot(hotspot, 'rejected')">
                          <q-tooltip>Reject Alert</q-tooltip>
                        </q-btn>
                      </div>
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-scroll-area>

              <div v-else-if="loading" class="text-center q-pa-md">
                <q-spinner-dots color="primary" size="40" />
                Loading hotspots...
              </div>

              <div v-else class="text-center q-pa-md">
                No hotspots found matching the current criteria
              </div>
            </q-tab-panel>
          </q-tab-panels>
        </q-card-section>
      </q-card>
    </div>

    <!-- Right Panel - Dual Maps -->
    <div class="comparison-container">
      <div class="comparison-maps">
        <div class="map-container">
          <div ref="primaryMap" class="comparison-map"></div>
          <div class="map-label">{{ getPrimaryMapLabel }}</div>
          <CustomLayerSwitcher mapId="primary" />
        </div>
        <div class="map-container">
          <div ref="secondaryMap" class="comparison-map"></div>
          <div class="map-label">{{ getSecondaryMapLabel }}</div>
          <CustomLayerSwitcher mapId="secondary" />
        </div>
      </div>
    </div>
  </div>

  <!-- Add after the q-tab-panels -->
  <q-btn
    v-if="activeTab !== 'verification'"
    fab
    color="primary"
    icon="analytics"
    class="stats-button"
    @click="showStats = true"
  >
    <q-tooltip>View Statistics</q-tooltip>
  </q-btn>

  <!-- Add at the end of the template, before closing div -->
  <q-dialog v-model="showStats">
    <q-card class="stats-dialog">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ getStatsTitle }}</div>
        <div class="text-caption" v-if="getStatsSubtitle">
          {{ getStatsSubtitle }}
        </div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <!-- Land Cover Stats -->
        <template v-if="activeTab === 'landcover' && selectedPrediction">
          <div class="row q-col-gutter-md">
            <div v-for="(stat, className) in landCoverStats" :key="className" class="col-4">
              <q-card class="stats-card" :style="{ borderLeft: `4px solid ${getClassColor(className)}` }">
                <q-card-section>
                  <div class="text-subtitle2">{{ className }}</div>
                  <div class="text-h6">{{ stat.area.toFixed(1) }} ha</div>
                  <div class="text-caption">{{ stat.percentage.toFixed(1) }}% of total area</div>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </template>

        <!-- Deforestation Stats -->
        <template v-if="activeTab === 'deforestation' && deforestationStats">
          <div class="row q-col-gutter-md">
            <div class="col-6">
              <q-card class="stats-card" style="border-left: 4px solid #FF5252">
                <q-card-section>
                  <div class="text-subtitle2">Total Deforested Area</div>
                  <div class="text-h6">{{ deforestationStats.deforested_area_ha.toFixed(1) }} ha</div>
                  <div class="text-caption">
                    {{ deforestationStats.deforestation_rate.toFixed(1) }}% of forest area
                  </div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-6">
              <q-card class="stats-card" style="border-left: 4px solid #4CAF50">
                <q-card-section>
                  <div class="text-subtitle2">Forest Area</div>
                  <div class="text-h6">{{ deforestationStats.total_forest_area_ha.toFixed(1) }} ha</div>
                  <div class="text-caption">
                    {{ (deforestationStats.total_forest_area_ha / projectStore.aoiAreaHa * 100).toFixed(1) }}% of AOI
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- Annual Rate -->
          <div class="row q-col-gutter-md q-mt-md">
            <div class="col-12">
              <q-card class="stats-card">
                <q-card-section>
                  <div class="text-subtitle2">Annual Deforestation Rate</div>
                  <div class="text-h6">{{ deforestationStats.annual_rate_ha.toFixed(1) }} ha/year</div>
                  <div class="text-caption">
                    {{ deforestationStats.annual_rate_percentage.toFixed(1) }}% of forest area per year
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </template>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" v-close-popup />
        <q-btn 
          flat 
          label="Export" 
          color="primary" 
          icon="download"
          @click="exportStats" 
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { useProjectStore } from 'src/stores/projectStore';
import { useQuasar } from 'quasar';
import api from 'src/services/api';
import { date } from 'quasar';
import { GeoJSON } from 'ol/format';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { Style, Fill, Stroke } from 'ol/style';
import { useRouter } from 'vue-router';
import CustomLayerSwitcher from 'components/CustomLayerSwitcher.vue';

export default {
  name: 'UnifiedAnalysis',
  components: {
    CustomLayerSwitcher
  },

  setup() {
    const mapStore = useMapStore();
    const projectStore = useProjectStore();
    const $q = useQuasar();
    const router = useRouter();

    // State
    const activeTab = ref('deforestation');
    const primaryMap = ref(null);
    const secondaryMap = ref(null);
    const predictions = ref([]);
    const deforestationMaps = ref([]);
    const selectedPrediction = ref(null);
    const selectedDeforestationMap = ref(null);
    const startDate = ref(null);
    const endDate = ref(null);
    const minAreaHa = ref(1);
    const selectedSource = ref({ label: 'All Sources', value: 'all' });
    const loading = ref(false);
    const hotspots = ref([]);
    const selectedHotspot = ref(null);
    const hotspotLayers = ref({ primary: null, secondary: null });
    const showStats = ref(false);

    // Add to setup() after other state declarations
    const sourceOptions = [
      { label: 'All Sources', value: 'all' },
      { label: 'ML Predictions', value: 'ml' },
      { label: 'Global Forest Watch', value: 'gfw' }
    ];

    // Computed
    const getPrimaryMapLabel = computed(() => {
      switch (activeTab.value) {
        case 'deforestation':
          return `Land Cover (${startDate.value?.label || 'Select Date'})`;
        case 'verification':
          return selectedDeforestationMap.value ? 
            `Before (${selectedDeforestationMap.value.summary_statistics.prediction1_date})` : 
            'Before';
        default:
          return 'Primary Map';
      }
    });

    const getSecondaryMapLabel = computed(() => {
      switch (activeTab.value) {
        case 'deforestation':
          return `Land Cover (${endDate.value?.label || 'Select Date'})`;
        case 'verification':
          return selectedDeforestationMap.value ? 
            `After (${selectedDeforestationMap.value.summary_statistics.prediction2_date})` : 
            'After';
        default:
          return 'Secondary Map';
      }
    });

    // Initialize maps
    onMounted(() => {
      if (!projectStore.currentProject) {
        $q.notify({
          message: 'Please select a project first',
          color: 'warning',
          icon: 'folder',
          actions: [
            { 
              label: 'Select Project', 
              color: 'white', 
              handler: () => router.push('/')
            }
          ]
        });
        return;
      }
      mapStore.initDualMaps(primaryMap.value, secondaryMap.value);
      loadInitialData();
    });

    // Methods
    const loadInitialData = async () => {
      try {
        const response = await api.getPredictions(projectStore.currentProject.id);
        console.log("Predictions fetched:", response.data);
        predictions.value = response.data
          .filter(p => p.type === "land_cover")
          .sort((a, b) => new Date(a.basemap_date) - new Date(b.basemap_date));
        deforestationMaps.value = response.data.filter(p => p.type === "deforestation");
      } catch (error) {
        console.error('Error loading initial data:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load analysis data',
          icon: 'error'
        });
      }
    };

    // Watch for tab changes to update maps
    watch(activeTab, (newTab) => {
      // Update maps based on active tab
      updateMapsForTab(newTab);
    });

    const updateMapsForTab = async (tab) => {
      // Clear existing layers from both maps
      clearMapLayers();
      
      switch (tab) {
        case 'deforestation':
          await setupDeforestationMaps();
          break;
        case 'verification':
          await setupVerificationMaps();
          break;
      }
    };

    const clearMapLayers = () => {
      // Keep only base layers
      const primaryLayers = mapStore.maps.primary.getLayers().getArray();
      const secondaryLayers = mapStore.maps.secondary.getLayers().getArray();
      
      primaryLayers.forEach(layer => {
        if (layer.get('id') !== 'osm') {
          mapStore.maps.primary.removeLayer(layer);
        }
      });
      
      secondaryLayers.forEach(layer => {
        if (layer.get('id') !== 'osm') {
          mapStore.maps.secondary.removeLayer(layer);
        }
      });
    };

    const setupDeforestationMaps = async () => {
        console.log("Setting up deforestation maps...");
      if (!mapStore.maps.primary || !mapStore.maps.secondary) {
        console.error("Maps not properly initialized!");
        return;
      }
      
      try {
        loading.value = true;
        clearMapLayers();

        // Add AOI layers if project has AOI
        if (projectStore.currentProject?.aoi) {
          console.log("Setting up AOI layers...");
          
          // Parse AOI if it's a string
          const aoiGeojson = typeof projectStore.currentProject.aoi === 'string' 
            ? JSON.parse(projectStore.currentProject.aoi) 
            : projectStore.currentProject.aoi;
          
          console.log("AOI GeoJSON:", aoiGeojson);

          // Create AOI layers with proper projection handling
          const { layer: primaryAOILayer, source: aoiSource } = mapStore.createAOILayer(aoiGeojson);
          const { layer: secondaryAOILayer } = mapStore.createAOILayer(aoiGeojson);

          // Add layers
          mapStore.maps.primary.addLayer(primaryAOILayer);
          mapStore.maps.secondary.addLayer(secondaryAOILayer);

          // Get AOI extent
          const aoiFeature = new GeoJSON().readFeature(projectStore.currentProject.aoi);
          const extent = aoiFeature.getGeometry().getExtent();
          console.log("AOI extent:", extent);

    
          // Fit both maps to AOI extent
          mapStore.maps.primary.getView().fit(extent);

        }

        // Handle primary map (start date)
        if (startDate.value) {
          const pred1 = predictions.value.find(p => p.basemap_date === startDate.value.value);
          if (pred1) {
            // Add Planet basemap
            console.log("Adding Planet basemap for start date:", startDate.value.value);
            const beforeBasemap = mapStore.createPlanetBasemap(startDate.value.value);
            beforeBasemap.setOpacity(0.7);
            mapStore.addLayerToDualMaps(beforeBasemap, 'primary');

            // Add land cover prediction
            console.log("Adding land cover prediction for start date:", pred1.name);
            await mapStore.displayPrediction(
              pred1.file,
              `prediction-${pred1.id}`,
              pred1.name,
              'prediction',
              'primary'
            );
          }
        }

        // Handle secondary map (end date)
        if (endDate.value) {
          const pred2 = predictions.value.find(p => p.basemap_date === endDate.value.value);
          if (pred2) {
            // Add Planet basemap
            const afterBasemap = mapStore.createPlanetBasemap(endDate.value.value);
            afterBasemap.setOpacity(0.7);
            mapStore.addLayerToDualMaps(afterBasemap, 'secondary');

            // Add land cover prediction
            await mapStore.displayPrediction(
              pred2.file,
              `prediction-${pred2.id}`,
              pred2.name,
              'prediction',
              'secondary'
            );
          }
        }

        // Add opacity controls
        if (startDate.value || endDate.value) {
          const addOpacityControl = (map, position) => {
            // Remove existing control if it exists
            const existingControl = map.getViewport().querySelector('.opacity-control');
            if (existingControl) {
              existingControl.remove();
            }

            const control = document.createElement('div');
            control.className = 'opacity-control';
            control.innerHTML = `
              <div class="opacity-label">Satellite Opacity</div>
              <input type="range" min="0" max="100" value="70" />
            `;
            
            const input = control.querySelector('input');
            input.addEventListener('input', (e) => {
              const opacity = parseInt(e.target.value) / 100;
              const basemapLayer = map.getLayers().getArray().find(l => l.get('id') === 'planet-basemap');
              if (basemapLayer) {
                basemapLayer.setOpacity(opacity);
              }
            });

            map.getViewport().appendChild(control);
          };

          if (startDate.value) {
            addOpacityControl(mapStore.maps.primary, 'left');
          }
          if (endDate.value) {
            addOpacityControl(mapStore.maps.secondary, 'right');
          }
        }

      } catch (error) {
        console.error('Error setting up deforestation maps:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load maps',
          icon: 'error'
        });
      } finally {
        loading.value = false;
      }
    };

    const setupVerificationMaps = async () => {
      if (!selectedDeforestationMap.value) return;
      
      try {
        loading.value = true;
        clearMapLayers();

        // Add AOI layers if project has AOI
        if (projectStore.currentProject?.aoi) {
          const { layer: primaryAOILayer, source: aoiSource } = mapStore.createAOILayer(
            projectStore.currentProject.aoi
          );
          const { layer: secondaryAOILayer } = mapStore.createAOILayer(
            projectStore.currentProject.aoi
          );

          mapStore.maps.primary.addLayer(primaryAOILayer);
          mapStore.maps.secondary.addLayer(secondaryAOILayer);

          // Get AOI extent
          const aoiFeature = new GeoJSON().readFeature(projectStore.currentProject.aoi);
          const extent = aoiFeature.getGeometry().getExtent();

          // Fit both maps to AOI extent
          mapStore.maps.primary.getView().fit(extent, {
            padding: [50, 50, 50, 50],
            duration: 1000
          });

          // The secondary map will automatically sync due to the view synchronization,
          // but we can force it to be sure
          mapStore.maps.secondary.getView().fit(extent, {
            padding: [50, 50, 50, 50],
            duration: 1000
          });
        }

        const beforeDate = selectedDeforestationMap.value.summary_statistics.prediction1_date;
        const afterDate = selectedDeforestationMap.value.summary_statistics.prediction2_date;
        
        // Add Planet basemaps
        const beforeLayer = mapStore.createPlanetBasemap(beforeDate);
        const afterLayer = mapStore.createPlanetBasemap(afterDate);
        
        mapStore.addLayerToDualMaps(beforeLayer, 'primary');
        mapStore.addLayerToDualMaps(afterLayer, 'secondary');
        
        // Add hotspots if available
        if (hotspots.value?.length) {
          displayHotspots();
        }
      } catch (error) {
        console.error('Error setting up verification maps:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load maps',
          icon: 'error'
        });
      } finally {
        loading.value = false;
      }
    };

    const loadHotspots = async () => {
      if (!selectedDeforestationMap.value) return;

      try {
        loading.value = true;
        const response = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          minAreaHa.value,
          selectedSource.value.value
        );
        hotspots.value = response.data.features;

        // Update maps with new hotspots
        await setupVerificationMaps();
      } catch (error) {
        console.error('Error loading hotspots:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load hotspots',
          icon: 'error'
        });
      } finally {
        loading.value = false;
      }
    };

    const displayHotspots = () => {
      if (!hotspots.value?.length) return;

      // Clear existing hotspot layers
      if (hotspotLayers.value.primary) {
        mapStore.removeLayerFromDualMaps('hotspots-primary', 'primary');
        mapStore.removeLayerFromDualMaps('hotspots-secondary', 'secondary');
      }

      const hotspotsGeoJSON = {
        type: 'FeatureCollection',
        features: hotspots.value
      };

      const getHotspotStyle = (feature) => {
        const isSelected = selectedHotspot.value && 
          selectedHotspot.value.properties.id === feature.getProperties().id;
        const source = feature.getProperties().source;
        const status = feature.getProperties().verification_status;

        const style = {
          strokeColor: source === 'gfw' ? '#9C27B0' : '#1976D2',
          strokeWidth: isSelected ? 3 : 1.5,
          lineDash: isSelected ? [10, 10] : []
        };

        if (status) {
          switch (status) {
            case 'verified':
              style.strokeColor = '#4CAF50';
              break;
            case 'rejected':
              style.strokeColor = '#607D8B';
              break;
            case 'unsure':
              style.strokeColor = '#FFC107';
              break;
          }
        }

        return new Style({
          stroke: new Stroke({
            color: style.strokeColor,
            width: style.strokeWidth,
            lineDash: style.lineDash
          })
        });
      };

      // Create and add layers to both maps
      ['primary', 'secondary'].forEach(mapId => {
        const layer = new VectorLayer({
          source: new VectorSource({
            features: new GeoJSON().readFeatures(hotspotsGeoJSON)
          }),
          style: getHotspotStyle,
          title: `hotspots-${mapId}`,
          id: `hotspots-${mapId}`,
          zIndex: 2
        });

        hotspotLayers.value[mapId] = layer;
        mapStore.addLayerToDualMaps(layer, mapId);
      });
    };

    const selectHotspot = (hotspot) => {
      selectedHotspot.value = hotspot;

      // Refresh layer styles
      ['primary', 'secondary'].forEach(mapId => {
        if (hotspotLayers.value[mapId]) {
          hotspotLayers.value[mapId].changed();
        }
      });

      // Fit to hotspot extent
      const extent = new GeoJSON().readFeature(hotspot).getGeometry().getExtent();
      mapStore.maps.primary.getView().fit(extent, {
        padding: [150, 150, 150, 150],
        maxZoom: 17
      });
    };

    const verifyHotspot = async (hotspot, status) => {
      try {
        await api.verifyHotspot(hotspot.properties.id, status);
        hotspot.properties.verification_status = status;

        // Update layer styles
        ['primary', 'secondary'].forEach(mapId => {
          if (hotspotLayers.value[mapId]) {
            hotspotLayers.value[mapId].changed();
          }
        });

        $q.notify({
          color: 'positive',
          message: 'Hotspot verification updated',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error verifying hotspot:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to update hotspot verification',
          icon: 'error'
        });
      }
    };

    const getConfidenceColor = (confidence) => {
      if (confidence >= 0.8) return 'green';
      if (confidence >= 0.6) return 'amber';
      return 'red';
    };

    const getConfidenceLabel = (confidence) => {
      if (confidence >= 0.8) return 'High';
      if (confidence >= 0.6) return 'Medium';
      return 'Low';
    };

    // Add to setup()
    const predictionDates = computed(() => {
      return predictions.value.map(p => ({
        label: date.formatDate(p.basemap_date, 'MMMM YYYY'),
        value: p.basemap_date
      }));
    });

    const analyzeDeforestation = async () => {
      if (!startDate.value || !endDate.value) return;

      try {
        loading.value = true;

        const pred1 = predictions.value.find(p => p.basemap_date === startDate.value.value);
        const pred2 = predictions.value.find(p => p.basemap_date === endDate.value.value);

        if (!pred1 || !pred2) {
          throw new Error('Could not find predictions for the selected dates.');
        }

        // Parse AOI shape if it's a string
        const aoiShape = typeof projectStore.currentProject.aoi === 'string' 
          ? JSON.parse(projectStore.currentProject.aoi)
          : projectStore.currentProject.aoi;

        const results = await api.getChangeAnalysis({
          prediction1_id: pred1.id,
          prediction2_id: pred2.id,
          aoi_shape: aoiShape
        });

        // Update maps to show the deforestation results
        await setupDeforestationMaps();

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
      } finally {
        loading.value = false;
      }
    };

    // Add watch for selectedPrediction
    watch(selectedPrediction, async (newPrediction) => {
      if (newPrediction && activeTab.value === 'landcover') {
        await setupLandCoverMaps();
      }
    });

    // Replace updatePrimaryMap and updateSecondaryMap with this single function
    const updateMap = async (mapId, date) => {
      console.log('updateMap:', date.value);
      try {
        if (!date) {
          console.log('Date is not defined');
          return;
        }

        const prediction = predictions.value.find(p => p.basemap_date === date.value.value);
        console.log('adding prediction:', prediction);
        if (prediction) {
          // Clear existing layers from specified map only
          const mapLayers = mapStore.maps[mapId].getLayers().getArray();
          mapLayers.forEach(layer => {
            if (layer.get('id') !== 'osm' && !layer.get('id')?.includes('aoi')) {
              mapStore.maps[mapId].removeLayer(layer);
            }
          });

          // Add Planet basemap
          console.log(`Adding Planet basemap for ${mapId} date:`, date.value.value);
          const basemap = mapStore.createPlanetBasemap(date.value.value);
          basemap.setOpacity(0.7);
          mapStore.addLayerToDualMaps(basemap, mapId);

          // Add land cover prediction
          console.log(`Adding land cover prediction for ${mapId}:`, prediction.name);
          await mapStore.displayPrediction(
            prediction.file,
            `prediction-${prediction.id}`,
            prediction.name,
            'prediction',
            mapId
          );
        }
      } catch (error) {
        console.error(`Error updating ${mapId} map:`, error);
        throw error;
      }
    };

    // Update the watchers to use the new function
    watch(startDate, async (newDate) => {
      if (newDate && activeTab.value === 'deforestation') {
        await updateMap('primary', startDate);
      }
    });

    watch(endDate, async (newDate) => {
      if (newDate && activeTab.value === 'deforestation') {
        await updateMap('secondary', endDate);
      }
    });

    return {
      // State
      activeTab,
      primaryMap,
      secondaryMap,
      predictions,
      deforestationMaps,
      selectedPrediction,
      selectedDeforestationMap,
      startDate,
      endDate,
      minAreaHa,
      selectedSource,
      loading,
      hotspots,
      selectedHotspot,
      hotspotLayers,
      showStats,
      // Computed
      getPrimaryMapLabel,
      getSecondaryMapLabel,
      // Methods
      loadInitialData,
      loadHotspots,
      selectHotspot,
      verifyHotspot,
      getConfidenceColor,
      getConfidenceLabel,
      predictionDates,
      analyzeDeforestation,
      sourceOptions
    };
  }
};
</script>

<style lang="scss" scoped>
.analysis-controls-container {
  width: var(--app-sidebar-width);
  height: calc(100vh - var(--app-header-height));
  overflow-y: auto;
}

.analysis-card {
  height: 100%;
}

.comparison-container {
  flex: 1;
  height: calc(100vh - var(--app-header-height));
  padding: 16px;
}

.comparison-maps {
  display: flex;
  gap: 16px;
  height: 100%;
  width: 100%;
}

.map-container {
  flex: 1;
  position: relative;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.comparison-map {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.map-label {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  z-index: 1;
}
</style> 