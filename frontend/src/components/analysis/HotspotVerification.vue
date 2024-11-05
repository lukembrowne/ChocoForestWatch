<template>
  <div class="row no-wrap" style="height: 100vh;">
    <!-- Left Panel - Hotspots List -->
    <div class="hotspot-list-container">
      <q-card class="hotspot-list-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">Deforestation Hotspots</div>
          <!-- Deforestation Map Selection -->
          <q-select
            v-model="selectedDeforestationMap"
            :options="deforestationMaps"
            label="Select Deforestation Map"
            option-label="name"
            class="q-mb-md"
            @update:model-value="loadHotspots"
          />

          <!-- Move export buttons next to minimum area input -->
          <div class="row items-center q-mb-md">
            <q-input
              v-model.number="minAreaHa"
              type="number"
              label="Minimum Area (ha)"
              class="col"
              :rules="[
                val => val >= 0 || 'Area must be positive',
                val => val <= 1000 || 'Area must be less than 1000 ha'
              ]"
            >
              <template v-slot:append>
                <q-btn
                  flat
                  round
                  dense
                  icon="refresh"
                  @click="loadHotspots"
                  :disable="!selectedDeforestationMap"
                >
                  <q-tooltip>Refresh hotspots</q-tooltip>
                </q-btn>
              </template>
            </q-input>
            
            <div class="col-auto q-ml-md">
              <q-btn
                flat
                dense
                color="primary"
                icon="download"
                @click="exportHotspots('all')"
              >
                <q-tooltip>Export All Hotspots</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                color="green"
                icon="download"
                @click="exportHotspots('verified')"
              >
                <q-tooltip>Export Verified Hotspots</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                color="info"
                icon="analytics"
                @click="showStats = true"
              >
                <q-tooltip>View Statistics</q-tooltip>
              </q-btn>
            </div>
          </div>

          <!-- Hotspots List -->
          <q-scroll-area ref="scrollArea" v-if="hotspots.length" style="height: calc(100vh - 250px)">
            <q-list separator dense>
              <q-item
                v-for="(hotspot, index) in hotspots"
                :key="index"
                :class="{
                  'selected-hotspot': selectedHotspot === hotspot,
                  'verified-hotspot': hotspot.properties.verification_status === 'verified',
                  'rejected-hotspot': hotspot.properties.verification_status === 'rejected',
                  'unsure-hotspot': hotspot.properties.verification_status === 'unsure'
                }"
                clickable
                v-ripple
                @click="selectHotspot(hotspot)"
              >
                <q-item-section>
                  <div class="row items-center no-wrap">
                    <div class="text-weight-medium" :class="{ 'text-weight-bold': selectedHotspot === hotspot }">
                      #{{ index + 1 }}
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

                <!-- Verification buttons -->
                <q-item-section side>
                  <div class="row q-gutter-xs">
                    <q-btn
                      flat
                      round
                      size="sm"
                      color="green"
                      icon="check_circle"
                      @click.stop="verifyHotspot(hotspot, 'verified')"
                    >
                      <q-tooltip>Verify Deforestation</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      round
                      size="sm"
                      color="amber"
                      icon="help"
                      @click.stop="verifyHotspot(hotspot, 'unsure')"
                    >
                      <q-tooltip>Mark as Unsure</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      round
                      size="sm"
                      color="blue-grey"
                      icon="cancel"
                      @click.stop="verifyHotspot(hotspot, 'rejected')"
                    >
                      <q-tooltip>Reject Alert</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card-section>
      </q-card>
    </div>

    <!-- Right Panel - Side by Side Comparison -->
    <div class="comparison-container">
      <div class="comparison-maps">
        <div class="map-container">
          <div ref="beforeMap" class="comparison-map"></div>
          <div class="map-label">Before</div>
        </div>
        <div class="map-container">
          <div ref="afterMap" class="comparison-map"></div>
          <div class="map-label">After</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Add the statistics modal -->
  <q-dialog v-model="showStats">
    <q-card class="q-dialog-plugin" style="width: 900px; max-width: 90vw;">
      <!-- Header -->
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">Deforestation Statistics</div>
        <div class="text-caption" v-if="selectedDeforestationMap">
          Analysis Period: {{ selectedDeforestationMap.before_date }} to {{ selectedDeforestationMap.after_date }}
        </div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <!-- Overview Section -->
        <div class="text-h6 q-mb-md">Overview</div>
        <div class="row q-col-gutter-md">
          <div class="col-4">
            <q-card class="stat-card">
              <q-card-section>
                <div class="text-subtitle2">Total Hotspots</div>
                <div class="text-h5">{{ totalHotspots }}</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-4">
            <q-card class="stat-card">
              <q-card-section>
                <div class="text-subtitle2">Total Area</div>
                <div class="text-h5">{{ totalArea.toFixed(1) }} ha</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-4">
            <q-card class="stat-card">
              <q-card-section>
                <div class="text-subtitle2">Annual Rate</div>
                <div class="text-h5">{{ annualRate.toFixed(1) }} ha/year</div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <!-- Status Breakdown Section -->
        <div class="text-h6 q-mt-lg q-mb-md">Status Breakdown</div>
        <div class="row q-col-gutter-md">
          <div class="col-8">
            <q-card class="status-breakdown">
              <q-card-section>
                <div class="row q-col-gutter-md">
                  <div v-for="status in statusBreakdown" :key="status.name" class="col-6">
                    <div :class="`text-${status.color}`">
                      <div class="text-subtitle2">{{ status.name }}</div>
                      <div class="text-h6">{{ status.count }} hotspots</div>
                      <div class="text-caption">{{ status.percentage.toFixed(1) }}% of total</div>
                      <div class="text-subtitle2 q-mt-sm">{{ status.area.toFixed(1) }} ha</div>
                      <div class="text-caption">{{ status.areaPercentage.toFixed(1) }}% of total area</div>
                      <div class="text-subtitle2 q-mt-sm">{{ status.rate.toFixed(1) }} ha/year</div>
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-4">
            <q-card>
              <q-card-section>
                <div style="height: 250px">
                  <VuePie
                    :data="chartData"
                    :options="chartOptions"
                  />
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { useProjectStore } from 'src/stores/projectStore';
import { useQuasar } from 'quasar';
import api from 'src/services/api';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { GeoJSON } from 'ol/format';
import { Style, Fill, Stroke } from 'ol/style';
import OSM from 'ol/source/OSM'
import { fromLonLat, toLonLat } from 'ol/proj';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Pie as VuePie } from 'vue-chartjs';

ChartJS.register(ArcElement, Tooltip, Legend);

export default {
  name: 'HotspotVerification',

  components: {
    VuePie
  },

  setup() {
    const $q = useQuasar();
    const mapStore = useMapStore();
    const projectStore = useProjectStore();

    // Refs for map elements
    const beforeMap = ref(null);
    const afterMap = ref(null);
    const beforeMapInstance = ref(null);
    const afterMapInstance = ref(null);

    // State
    const deforestationMaps = ref([]);
    const selectedDeforestationMap = ref(null);
    const hotspots = ref([]);
    const selectedHotspot = ref(null);
    const hotspotLayers = ref({ before: null, after: null });
    const minAreaHa = ref(1); // Default 10 ha

    const showStats = ref(false);

    // Computed properties for statistics
    const totalHotspots = computed(() => hotspots.value.length);
    
    const totalArea = computed(() => 
      hotspots.value.reduce((sum, h) => sum + h.properties.area_ha, 0)
    );
    
    const annualRate = computed(() => {
      if (!selectedDeforestationMap.value) return 0;
      const beforeDate = new Date(selectedDeforestationMap.value.before_date);
      const afterDate = new Date(selectedDeforestationMap.value.after_date);
      const yearsDiff = (afterDate - beforeDate) / (1000 * 60 * 60 * 24 * 365.25);
      return totalArea.value / yearsDiff;
    });

    const statusBreakdown = computed(() => {
      const statuses = ['verified', 'unsure', 'rejected', 'unverified'];
      const colors = ['green', 'amber', 'blue-grey', 'purple'];
      const displayNames = ['Verified', 'Unsure', 'Rejected', 'Unverified'];
      
      return statuses.map((status, index) => {
        const hotspotsWithStatus = hotspots.value.filter(h => 
          status === 'unverified' 
            ? !h.properties.verification_status 
            : h.properties.verification_status === status
        );
        
        const count = hotspotsWithStatus.length;
        const area = hotspotsWithStatus.reduce((sum, h) => sum + h.properties.area_ha, 0);
        const rate = annualRate.value * (area / totalArea.value);
        
        return {
          name: displayNames[index],
          color: colors[index],
          count,
          percentage: (count / totalHotspots.value) * 100,
          area,
          areaPercentage: (area / totalArea.value) * 100,
          rate
        };
      });
    });

    // Chart data
    const chartData = computed(() => ({
      labels: statusBreakdown.value.map(s => s.name),
      datasets: [
        {
          data: statusBreakdown.value.map(s => s.area),
          backgroundColor: ['#4CAF50', '#FFC107', '#607D8B', '#9C27B0']
        }
      ]
    }));

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom'
        },
        title: {
          display: true,
          text: 'Area Distribution by Status'
        }
      }
    };

    // Initialize the comparison maps
    const initializeMaps = () => {
      console.log('Initializing maps');
      console.log('beforeMap element:', beforeMap.value);
      console.log('afterMap element:', afterMap.value);

      const createMap = (target) => {
        console.log('Creating map for target:', target);
        return new Map({
          target: target,
          layers: [
            new TileLayer({
              source: new OSM(),
              name: 'baseMap'
            })
          ],
          view: new View({
            center: fromLonLat([-79.81822466589962, 0.460628082970743]),
            zoom: 12
          })
        });
      };

      nextTick(() => {
        beforeMapInstance.value = createMap(beforeMap.value);
        afterMapInstance.value = createMap(afterMap.value);

        // Force a redraw
        beforeMapInstance.value.updateSize();
        afterMapInstance.value.updateSize();

        // Sync map movements
        const beforeView = beforeMapInstance.value.getView();
        const afterView = afterMapInstance.value.getView();

        // Sync center changes
        beforeView.on('change:center', () => {
          afterView.setCenter(beforeView.getCenter());
        });
        afterView.on('change:center', () => {
          beforeView.setCenter(afterView.getCenter());
        });

        // Sync zoom changes
        beforeView.on('change:resolution', () => {
          afterView.setResolution(beforeView.getResolution());
        });
        afterView.on('change:resolution', () => {
          beforeView.setResolution(afterView.getResolution());
        });

        // Sync rotation changes
        beforeView.on('change:rotation', () => {
          afterView.setRotation(beforeView.getRotation());
        });
        afterView.on('change:rotation', () => {
          beforeView.setRotation(afterView.getRotation());
        });
      });
    };

    // Load deforestation maps and hotspots
    const loadDeforestationMaps = async () => {
      try {
        const response = await api.getPredictions(projectStore.currentProject.id);
        deforestationMaps.value = response.filter(p => p.type === "deforestation");
        deforestationMaps.value.sort((a, b) => new Date(b.end_date) - new Date(a.end_date));
      } catch (error) {
        console.error('Error loading deforestation maps:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load deforestation maps',
          icon: 'error'
        });
      }
    };

    const loadHotspots = async () => {
      if (!selectedDeforestationMap.value) return;

      try {
        // Load hotspots
        const response = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          minAreaHa.value
        );
        hotspots.value = response.features;

        // Update the before/after maps with appropriate imagery and all hotspots
        updateComparisonMaps(selectedDeforestationMap.value);
        displayAllHotspots();
      } catch (error) {
        console.error('Error loading hotspots:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load hotspots',
          icon: 'error'
        });
      }
    };

    const updateComparisonMaps = async (deforestationMap) => {
      if (!beforeMapInstance.value || !afterMapInstance.value) return;

      // Clear existing layers
      beforeMapInstance.value.getLayers().forEach(layer => {
        beforeMapInstance.value.removeLayer(layer);
      });
      
      afterMapInstance.value.getLayers().forEach(layer => {
        afterMapInstance.value.removeLayer(layer);
      });

      // Add Planet basemap layers
      const beforeLayer = mapStore.createPlanetBasemap(deforestationMap.summary_statistics.prediction1_date);
      const afterLayer = mapStore.createPlanetBasemap(deforestationMap.summary_statistics.prediction2_date);

      if (beforeLayer && afterLayer) {
        beforeMapInstance.value.addLayer(beforeLayer);
        afterMapInstance.value.addLayer(afterLayer);

        // Add AOI layers if project has AOI
        if (projectStore.currentProject?.aoi) {
          const { layer: beforeAOILayer, source: beforeAOISource } = mapStore.createAOILayer(
            projectStore.currentProject.aoi
          );
          const { layer: afterAOILayer } = mapStore.createAOILayer(
            projectStore.currentProject.aoi
          );

          beforeMapInstance.value.addLayer(beforeAOILayer);
          afterMapInstance.value.addLayer(afterAOILayer);

          // Fit to AOI extent
          const extent = beforeAOISource.getExtent();
          console.log('Fitting to AOI extent:', extent);
          beforeMapInstance.value.getView().fit(extent, { padding: [50, 50, 50, 50] });
        }

        // Update labels
        const beforeLabel = document.querySelector('.map-container:first-child .map-label');
        const afterLabel = document.querySelector('.map-container:last-child .map-label');
        
        if (beforeLabel && afterLabel) {
          beforeLabel.textContent = `Before (${deforestationMap.summary_statistics.prediction1_date})`;
          afterLabel.textContent = `After (${deforestationMap.summary_statistics.prediction2_date})`;
        }
      } else {
        console.error('Failed to create Planet basemap layers');
        $q.notify({
          color: 'negative',
          message: 'Failed to load Planet imagery',
          icon: 'error'
        });
      }
    };

    const displayAllHotspots = () => {
      if (!hotspots.value.length) return;

      const hotspotsGeoJSON = {
        type: 'FeatureCollection',
        features: hotspots.value
      };

      const getHotspotStyle = (feature) => {
        const isSelected = selectedHotspot.value && 
                            feature.getId() === selectedHotspot.value.id;
        let color;
        let width = isSelected ? 1 : 0.5;

        const status = feature.get('verification_status');

        switch(status) {
          case 'verified':
            color = '#4CAF50';  // Green for verified
            break;
          case 'rejected':
            color = '#607D8B';  // Blue-grey for rejected
            break;
          case 'unsure':
            color = '#FFC107';  // Amber/yellow for unsure
            break;
          default:
            color = '#9C27B0';  // Purple for no status
            break;
        }

        return new Style({
          stroke: new Stroke({
            color: color,
            width: width,
          })
        });
      };

      // Create vector sources
      const beforeSource = new VectorSource({
        features: new GeoJSON().readFeatures(hotspotsGeoJSON)
      });
 
      const afterSource = new VectorSource({
        features: new GeoJSON().readFeatures(hotspotsGeoJSON)
      });

      // Create vector layers
      hotspotLayers.value = {
        before: new VectorLayer({
          source: beforeSource,
          style: getHotspotStyle,
          title: 'hotspots-before',
          id: 'hotspots-before',
          zIndex: 2
        }),
        after: new VectorLayer({
          source: afterSource,
          style: getHotspotStyle,
          title: 'hotspots-after',
          id: 'hotspots-after',
          zIndex: 2
        })
      };

      // Add layers to maps
      beforeMapInstance.value.addLayer(hotspotLayers.value.before);
      afterMapInstance.value.addLayer(hotspotLayers.value.after);

      console.log('Added hotspot layers:', hotspotLayers.value);
      console.log('Number of features:', beforeSource.getFeatures().length);
    };

    const selectHotspot = (hotspot) => {
      console.log('Selecting hotspot:', hotspot);
      selectedHotspot.value = hotspot;

      // Refresh the layer styles
      if (hotspotLayers.value.before) {
        hotspotLayers.value.before.changed();
        hotspotLayers.value.after.changed();
      }

      // Fit to extent with closer zoom
      const extent = new GeoJSON().readFeature(hotspot).getGeometry().getExtent();
      console.log('Fitting to extent:', extent);
      
      beforeMapInstance.value.getView().fit(extent, { padding: [50, 50, 50, 50] });
    };

    const verifyHotspot = async (hotspot, status) => {
      try {
        await api.verifyHotspot(hotspot.properties.id, status);
        
        // Update local state
        hotspot.properties.verification_status = status;

        // Force refresh of vector layers to update styles
        if (hotspotLayers.value.before) {
          const beforeFeatures = hotspotLayers.value.before.getSource().getFeatures();
          const afterFeatures = hotspotLayers.value.after.getSource().getFeatures();
          
          // Update the verification status on the feature
          beforeFeatures.forEach(feature => {
            if (feature.getId() === hotspot.properties.id) {
              feature.set('verification_status', status);
            }
          });
          
          afterFeatures.forEach(feature => {
            if (feature.getId() === hotspot.properties.id) {
              feature.set('verification_status', status);
            }
          });

          // Force style refresh
          hotspotLayers.value.before.changed();
          hotspotLayers.value.after.changed();
        }

        // Show success notification
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

    const setupKeyboardShortcuts = () => {
      const handleKeyPress = (event) => {
        // Only process if we have hotspots
        if (!hotspots.value.length) return;

        switch (event.key) {
          case 'ArrowUp':
            event.preventDefault();
            navigateHotspots('up');
            break;
          case 'ArrowDown':
            event.preventDefault();
            navigateHotspots('down');
            break;
          case '1':
            if (selectedHotspot.value) {
              verifyHotspot(selectedHotspot.value, 'verified');
            }
            break;
          case '2':
            if (selectedHotspot.value) {
              verifyHotspot(selectedHotspot.value, 'unsure');
            }
            break;
          case '3':
            if (selectedHotspot.value) {
              verifyHotspot(selectedHotspot.value, 'rejected');
            }
            break;
        }
      };

      // Add keyboard listener
      window.addEventListener('keydown', handleKeyPress);

      // Return cleanup function
      return () => {
        window.removeEventListener('keydown', handleKeyPress);
      };
    };

    const scrollArea = ref(null);

    const navigateHotspots = (direction) => {
      if (!hotspots.value.length) return;

      const currentIndex = selectedHotspot.value 
        ? hotspots.value.findIndex(h => h === selectedHotspot.value)
        : -1;

      let newIndex;
      if (direction === 'up') {
        newIndex = currentIndex <= 0 ? hotspots.value.length - 1 : currentIndex - 1;
      } else {
        newIndex = currentIndex >= hotspots.value.length - 1 ? 0 : currentIndex + 1;
      }

      selectHotspot(hotspots.value[newIndex]);

      // Scroll the selected item into view
      nextTick(() => {
        const element = scrollArea.value.$el.querySelector(`.q-item:nth-child(${newIndex + 1})`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    };

    const exportHotspots = (type) => {
      try {
        let hotspotsToExport = [];
        if (type === 'verified') {
          hotspotsToExport = hotspots.value.filter(h => 
            h.properties.verification_status === 'verified'
          );
        } else {
          hotspotsToExport = hotspots.value;
        }

        // Create GeoJSON feature collection with metadata and CRS
        const geojson = {
          type: 'FeatureCollection',
          crs: {
            type: 'name',
            properties: {
              name: 'EPSG:3857'  // Web Mercator projection
            }
          },
          metadata: {
            prediction_id: selectedDeforestationMap.value.id,
            prediction_name: selectedDeforestationMap.value.name,
            before_date: selectedDeforestationMap.value.before_date,
            after_date: selectedDeforestationMap.value.after_date,
            total_hotspots: hotspotsToExport.length,
            total_area_ha: hotspotsToExport.reduce((sum, h) => sum + h.properties.area_ha, 0),
            min_area_ha: minAreaHa.value,
            export_type: type,
            export_timestamp: new Date().toISOString(),
            projection: 'EPSG:3857',  // Also add to metadata for clarity
            projection_name: 'Web Mercator'
          },
          features: hotspotsToExport.map(h => ({
            type: 'Feature',
            geometry: h.geometry,
            properties: {
              id: h.properties.id,
              area_ha: h.properties.area_ha,
              verification_status: h.properties.verification_status
            }
          }))
        };

        // Create and trigger download
        const blob = new Blob([JSON.stringify(geojson, null, 2)], {
          type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        
        // Generate filename with timestamp
        const timestamp = new Date().toISOString().split('T')[0];
        const filename = `deforestation_hotspots_${type}_${timestamp}.geojson`;
        
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        // Show success notification
        $q.notify({
          color: 'positive',
          message: `Successfully exported ${hotspotsToExport.length} hotspots`,
          icon: 'check'
        });
      } catch (error) {
        console.error('Error exporting hotspots:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to export hotspots',
          icon: 'error'
        });
      }
    };

    onMounted(async () => {
      console.log('Component mounted');
      await loadDeforestationMaps();
      setTimeout(() => {
        initializeMaps();
      }, 100);
      
      // Setup keyboard shortcuts
      const cleanup = setupKeyboardShortcuts();
      
      // Clean up keyboard shortcuts on unmount
      onUnmounted(() => {
        cleanup();
        if (beforeMapInstance.value) beforeMapInstance.value.setTarget(null);
        if (afterMapInstance.value) afterMapInstance.value.setTarget(null);
      });
    });

    return {
      beforeMap,
      afterMap,
      deforestationMaps,
      selectedDeforestationMap,
      hotspots,
      selectedHotspot,
      loadHotspots,
      selectHotspot,
      verifyHotspot,
      minAreaHa,
      exportHotspots,
      scrollArea,
      showStats,
      totalHotspots,
      totalArea,
      annualRate,
      statusBreakdown,
      chartData,
      chartOptions
    };
  }
};
</script>

<style lang="scss" scoped>
.hotspot-list-container {
  width: 400px;
  height: calc(100vh - 50px);
  overflow-y: auto;
  z-index: 1;
}

.hotspot-list-card {
  height: 100%;
}

.comparison-container {
  flex: 1;
  height: calc(100vh - 50px);
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
  min-height: 500px;
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

.selected-hotspot {
  background: rgba(156, 39, 176, 0.3) !important;  // Purple for unverified
  border-left-width: 4px;
}

.verified-hotspot {
  background: rgba(76, 175, 80, 0.15) !important;
  border-left-color: #4CAF50 !important;
  
  &.selected-hotspot {
    background: rgba(76, 175, 80, 0.3) !important;
  }
}

.rejected-hotspot {
  background: rgba(96, 125, 139, 0.15) !important;
  border-left-color: #607D8B !important;
  
  &.selected-hotspot {
    background: rgba(96, 125, 139, 0.3) !important;
  }
}

.unsure-hotspot {
  background: rgba(255, 193, 7, 0.15) !important;
  border-left-color: #FFC107 !important;
  
  &.selected-hotspot {
    background: rgba(255, 193, 7, 0.3) !important;
  }
}

// Add hover effects for status rows
.verified-hotspot:hover {
  background: rgba(76, 175, 80, 0.15) !important;
}

.rejected-hotspot:hover {
  background: rgba(96, 125, 139, 0.15) !important;
}

.unsure-hotspot:hover {
  background: rgba(255, 193, 7, 0.15) !important;
}

.q-item {
  min-height: 40px !important;  // Make items more compact
  padding: 4px 16px;  // Reduce vertical padding
}

// Make the list denser
.q-list {
  padding: 0;
}

// Adjust text sizes
.text-weight-medium {
  font-size: 0.9rem;
}

// Status text
.q-ml-auto {
  font-size: 0.85rem;
}

.export-section {
  padding: 16px 0;
  
  .q-btn {
    min-width: 135px;  // Make buttons equal width
  }
}

.stats-modal {
  .stat-card {
    height: 100%;
    background: #f8f9fa;
    
    .text-subtitle2 {
      color: rgba(0,0,0,0.7);
    }
  }
  
  .status-breakdown {
    height: 100%;
    
    .text-subtitle2 {
      font-weight: 500;
    }
    
    .text-caption {
      opacity: 0.7;
    }
  }
}

// Color classes for status
.text-green {
  color: #4CAF50;
}

.text-amber {
  color: #FFC107;
}

.text-blue-grey {
  color: #607D8B;
}

.text-purple {
  color: #9C27B0;
}
</style> 