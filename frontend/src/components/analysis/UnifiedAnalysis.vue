<template>
  <div class="row no-wrap" style="height: 100vh;">
    <!-- Left Panel - Analysis Controls -->
    <div class="analysis-controls-container">
      <q-card class="analysis-card">
        <!-- Analysis Header Section - Fixed height -->
        <div class="analysis-header-section">
          <q-card-section class="section-header">
            <div class="row items-center">
              <div class="text-subtitle1 text-weight-medium">{{ t('analysis.unified.deforestation.title') }}</div>
              <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
                <q-tooltip>{{ t('analysis.unified.deforestation.tooltips.help') }}</q-tooltip>
              </q-btn>
            </div>
          </q-card-section>

          <!-- Date Selection and Previous Analysis -->
          <q-card-section class="q-pa-sm">
            <div class="row q-col-gutter-sm">
              <q-select v-model="startDate" :options="predictionDates"
                :label="t('analysis.unified.deforestation.new.startDate')" class="col modern-input" dense outlined />
              <q-select v-model="endDate" :options="predictionDates"
                :label="t('analysis.unified.deforestation.new.endDate')" class="col modern-input" dense outlined />
              <div class="row justify-center q-py-sm">
                <q-btn icon="add_circle" color="primary" @click="analyzeDeforestation" :disable="!startDate || !endDate"
                  :loading="loading" unelevated />
              </div>
            </div>

            <q-separator class="q-my-sm" />
            <div class="text-subtitle2">{{ t('analysis.unified.deforestation.previous.title') }}</div>
            <div class="row q-col-gutter-sm">
              <q-select v-model="selectedDeforestationMap" :options="deforestationMaps" option-label="name"
                option-value="id" class="col modern-input" dense outlined @update:model-value="loadExistingAnalysis"
                @option-click="loadExistingAnalysis" />
              <div class="row justify-center q-py-sm">
                <q-btn icon="refresh" color="primary" dense :disable="!selectedDeforestationMap"
                  @click="loadExistingAnalysis(selectedDeforestationMap)" class="q-ml-sm">
                  <q-tooltip>{{ t('analysis.unified.deforestation.reload') }}</q-tooltip>
                </q-btn>
              </div>
            </div>
          </q-card-section>
        </div>

        <!-- Hotspots Section - Flexible height with scroll -->
        <div class="analysis-hotspots-section">
          <q-card-section class="section-header">
            <div class="row items-center">
              <div class="text-subtitle1 text-weight-medium">{{ t('analysis.unified.hotspots.title') }}</div>
              <q-badge color="primary" class="q-ml-sm">
                {{ hotspots.length }} {{ t('analysis.unified.hotspots.count', hotspots.length) }}
              </q-badge>
              <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
                <q-tooltip>{{ t('analysis.unified.hotspots.tooltips.help') }}</q-tooltip>
              </q-btn>
            </div>
          </q-card-section>

          <!-- Filtering controls -->
          <q-card-section class="q-pa-sm">
            <div class="row q-col-gutter-sm">
              <div class="col-6">
                <q-input v-model.number="minAreaHa" type="number"
                  :label="t('analysis.unified.hotspots.filters.minArea')" dense outlined class="modern-input"
                  @update:model-value="loadHotspots">
                  <template v-slot:append>
                    <q-icon name="filter_alt" />
                  </template>
                </q-input>
              </div>
              <div class="col-6">
                <q-select v-model="selectedSource" :options="sourceOptions"
                  :label="t('analysis.unified.hotspots.filters.source')" dense outlined class="modern-input"
                  @update:model-value="loadHotspots" />
              </div>
            </div>
          </q-card-section>

          <!-- Scrollable hotspots list -->
          <q-scroll-area class="hotspots-scroll-area">
            <q-list separator dense>
              <q-item v-for="(hotspot, index) in hotspots" :key="index" :class="[
                'hotspot-item',
                hotspot.properties.source === 'gfw' ? 'gfw-alert' : 'local-alert',
                {
                  'selected-hotspot': selectedHotspot === hotspot,
                  'verified': hotspot.properties.verification_status === 'verified',
                  'rejected': hotspot.properties.verification_status === 'rejected',
                  'unsure': hotspot.properties.verification_status === 'unsure'
                }
              ]" clickable v-ripple @click="selectHotspot(hotspot)">
                <q-item-section>
                  <div class="row items-center no-wrap">
                    <div class="text-weight-medium">
                      #{{ index + 1 }}
                      <q-badge :color="hotspot.properties.source === 'gfw' ? 'purple' : 'primary'">
                        {{ hotspot.properties.source.toUpperCase() }}
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
                  <div class="row q-gutter-xs verification-buttons">
                    <q-btn flat round size="sm" color="green" icon="check_circle"
                      @click.stop="verifyHotspot(hotspot, 'verified')">
                      <q-tooltip>{{ t('analysis.unified.hotspots.tooltips.verify') }}</q-tooltip>
                    </q-btn>
                    <q-btn flat round size="sm" color="amber" icon="help"
                      @click.stop="verifyHotspot(hotspot, 'unsure')">
                      <q-tooltip>{{ t('analysis.unified.hotspots.tooltips.unsure') }}</q-tooltip>
                    </q-btn>
                    <q-btn flat round size="sm" color="blue-grey" icon="cancel"
                      @click.stop="verifyHotspot(hotspot, 'rejected')">
                      <q-tooltip>{{ t('analysis.unified.hotspots.tooltips.reject') }}</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </div>

        <!-- Actions Footer - Fixed height -->
        <div class="analysis-footer-section">
          <q-card-section class="q-pa-sm">
            <div v-if="hotspots?.length" class="row q-col-gutter-sm">
              <q-btn flat color="primary" icon="analytics" :label="t('analysis.unified.stats.title')"
                @click="showStats = true" />
              <q-btn flat color="primary" icon="download" :label="t('analysis.unified.hotspots.export.title')"
                @click="exportHotspots('all')">
                <q-menu>
                  <q-list style="min-width: 100px">
                    <q-item clickable v-close-popup @click="exportHotspots('all')">
                      <q-item-section>{{ t('analysis.unified.hotspots.export.all') }}</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="exportHotspots('verified')">
                      <q-item-section>{{ t('analysis.unified.hotspots.export.verifiedOnly') }}</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-btn>
            </div>
            <div v-else class="text-caption text-center">
              {{ t('analysis.unified.hotspots.empty') }}
            </div>
          </q-card-section>
        </div>
      </q-card>
    </div>

    <!-- Right Panel - Dual Maps -->
    <div class="comparison-container">
      <div class="comparison-maps">
        <div class="map-container">
          <div ref="primaryMap" class="comparison-map"></div>
          <div class="map-label">{{ getPrimaryMapLabel }}</div>
          <CustomLayerSwitcher mapId="primary" />
          <div class="map-loading-overlay" :class="{ active: primaryMapLoading }">
            <q-spinner-dots color="primary" size="100px" />
            <div class="text-h6 q-mt-sm">{{ t('analysis.unified.loading') }}</div>
          </div>

          <!-- Add legend -->
          <div class="map-legend">
            <div class="legend-title">{{ t('analysis.unified.maps.legend.title') }}</div>
            <div class="legend-item">
              <div class="legend-line local-line"></div>
              <span>{{ t('analysis.unified.maps.legend.local') }}</span>
            </div>
            <div class="legend-item">
              <div class="legend-line gfw-line"></div>
              <span>{{ t('analysis.unified.maps.legend.gfw') }}</span>
            </div>
            <div class="legend-title mt-2">{{ t('analysis.unified.maps.legend.status.title') }}</div>
            <div class="legend-item">
              <div class="legend-line verified-line"></div>
              <span>{{ t('analysis.unified.maps.legend.status.verified') }}</span>
            </div>
            <div class="legend-item">
              <div class="legend-line unsure-line"></div>
              <span>{{ t('analysis.unified.maps.legend.status.unsure') }}</span>
            </div>
            <div class="legend-item">
              <div class="legend-line rejected-line"></div>
              <span>{{ t('analysis.unified.maps.legend.status.rejected') }}</span>
            </div>
          </div>
        </div>
        <div class="map-container">
          <div ref="secondaryMap" class="comparison-map"></div>
          <div class="map-label">{{ getSecondaryMapLabel }}</div>
          <CustomLayerSwitcher mapId="secondary" />
          <div class="map-loading-overlay" :class="{ active: secondaryMapLoading }">
            <q-spinner-dots color="primary" size="100px" />
            <div class="text-h6 q-mt-sm">{{ t('analysis.unified.loading') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Deforestation statistics modal -->
  <q-dialog v-model="showStats">
    <q-card class="stats-dialog">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ getStatsTitle }}</div>
        <div class="text-caption" v-if="getStatsSubtitle">
          {{ getStatsSubtitle }}
        </div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <!-- Overview Section -->
        <div class="text-h6 q-mb-md">{{ t('analysis.unified.stats.overview.title', { minArea: minAreaHa }) }}</div>
        <div class="row q-col-gutter-md">
          <!-- Local Alerts -->
          <div class="col-6">
            <q-card class="source-stats-card local-stats">
              <q-card-section>
                <div class="text-h6 q-mb-md">{{ t('analysis.unified.stats.overview.localAlerts') }}</div>
                <div class="text-caption q-mb-sm">{{ t('analysis.unified.stats.overview.showing', {
                  minArea: minAreaHa
                })
                  }}</div>
                <div class="row q-col-gutter-md">
                  <div class="col-4">
                    <div class="text-subtitle2">{{ t('analysis.unified.stats.overview.hotspots') }}</div>
                    <div class="text-h5">{{ sourceStats.local.count }}</div>
                  </div>
                  <div class="col-4">
                    <div class="text-subtitle2">{{ t('analysis.unified.stats.overview.totalArea') }}</div>
                    <div class="text-h5">{{ sourceStats.local.area.toFixed(1) }} ha</div>
                    <div class="text-caption">{{ t('analysis.unified.stats.overview.percentOfAoi', {
                      percent:
                        (sourceStats.local.area / projectStore.aoiAreaHa * 100).toFixed(1)
                    }) }}</div>
                  </div>
                  <div class="col-4">
                    <div class="text-subtitle2">{{ t('analysis.unified.stats.overview.annualRate') }}</div>
                    <div class="text-h5">{{ sourceStats.local.rate.toFixed(1) }} {{
                      t('analysis.unified.stats.overview.haPerYear') }}</div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- GFW Alerts -->
          <div class="col-6">
            <q-card class="source-stats-card gfw-stats">
              <q-card-section>
                <div class="text-h6 q-mb-md">{{ t('analysis.unified.stats.overview.gfwAlerts') }}</div>
                <div class="text-caption q-mb-sm">{{ t('analysis.unified.stats.overview.showing', {
                  minArea: minAreaHa
                })
                  }}</div>
                <div class="row q-col-gutter-md">
                  <div class="col-4">
                    <div class="text-subtitle2">{{ t('analysis.unified.stats.overview.hotspots') }}</div>
                    <div class="text-h5">{{ sourceStats.gfw.count }}</div>
                  </div>
                  <div class="col-4">
                    <div class="text-subtitle2">{{ t('analysis.unified.stats.overview.totalArea') }}</div>
                    <div class="text-h5">{{ sourceStats.gfw.area.toFixed(1) }} ha</div>
                    <div class="text-caption">{{ t('analysis.unified.stats.overview.percentOfAoi', {
                      percent:
                        (sourceStats.gfw.area / projectStore.aoiAreaHa * 100).toFixed(1)
                    }) }}</div>
                  </div>
                  <div class="col-4">
                    <div class="text-subtitle2">{{ t('analysis.unified.stats.overview.annualRate') }}</div>
                    <div class="text-h5">{{ sourceStats.gfw.rate.toFixed(1) }} {{
                      t('analysis.unified.stats.overview.haPerYear') }}</div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <!-- Status Breakdown Section -->
        <div class="text-h6 q-mt-lg q-mb-md">{{ t('analysis.unified.stats.breakdown.title', { minArea: minAreaHa }) }}
        </div>
        <div class="row q-col-gutter-md">
          <!-- Local Status Breakdown -->
          <div class="col-6">
            <q-card class="status-breakdown local-stats">
              <q-card-section>
                <div class="text-h6 q-mb-md">{{ t('analysis.unified.stats.overview.localAlerts') }}</div>
                <div class="row q-col-gutter-md">
                  <div v-for="status in localStatusBreakdown" :key="status.name" class="col-6">
                    <div :class="`text-${status.color}`">
                      <div class="text-subtitle2">{{
                        t(`analysis.unified.stats.breakdown.status.${status.name.toLowerCase()}`) }}</div>
                      <div class="text-h6">{{ t('analysis.unified.stats.breakdown.hotspotCount', {
                        count: status.count
                      })
                        }}</div>
                      <div class="text-caption">{{ t('analysis.unified.stats.breakdown.percentOfSource', {
                        percent:
                          status.percentage.toFixed(1), source: t('analysis.unified.stats.overview.localAlerts')
                      }) }}
                      </div>
                      <div class="text-subtitle2 q-mt-sm">{{ status.area.toFixed(1) }} ha</div>
                      <div class="text-caption">{{ t('analysis.unified.stats.overview.percentOfAoi', {
                        percent:
                          status.areaPercentageOfAOI.toFixed(1)
                      }) }}</div>
                      <div class="text-subtitle2 q-mt-sm">{{ status.rate.toFixed(1) }} {{
                        t('analysis.unified.stats.overview.haPerYear') }}</div>
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- GFW Status Breakdown -->
          <div class="col-6">
            <q-card class="status-breakdown gfw-stats">
              <q-card-section>
                <div class="text-h6 q-mb-md">{{ t('analysis.unified.stats.overview.gfwAlerts') }}</div>
                <div class="row q-col-gutter-md">
                  <div v-for="status in gfwStatusBreakdown" :key="status.name" class="col-6">
                    <div :class="`text-${status.color}`">
                      <div class="text-subtitle2">{{
                        t(`analysis.unified.stats.breakdown.status.${status.name.toLowerCase()}`) }}</div>
                      <div class="text-h6">{{ t('analysis.unified.stats.breakdown.hotspotCount', {
                        count: status.count
                      })
                        }}</div>
                      <div class="text-caption">{{ t('analysis.unified.stats.breakdown.percentOfSource', {
                        percent:
                          status.percentage.toFixed(1), source: t('analysis.unified.stats.overview.gfwAlerts')
                      }) }}</div>
                      <div class="text-subtitle2 q-mt-sm">{{ status.area.toFixed(1) }} ha</div>
                      <div class="text-caption">{{ t('analysis.unified.stats.overview.percentOfAoi', {
                        percent:
                          status.areaPercentageOfAOI.toFixed(1)
                      }) }}</div>
                      <div class="text-subtitle2 q-mt-sm">{{ status.rate.toFixed(1) }} {{
                        t('analysis.unified.stats.overview.haPerYear') }}</div>
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <!-- Add AOI info -->
        <div class="text-caption q-mt-md">
          <q-icon name="info" size="xs" class="q-mr-xs" />
          {{ t('analysis.unified.stats.aoiInfo', { area: projectStore.aoiAreaHa.toFixed(1) }) }}
        </div>

        <!-- Land Cover Percentages -->
        <div class="text-h6 q-mt-lg q-mb-md">{{ t('analysis.unified.stats.landCover.title') }}</div>
        <div class="row q-col-gutter-md">
          <!-- Before -->
          <div class="col-6">
            <q-card class="land-cover-stats shadow-2">
              <q-card-section>
                <div class="text-h6 q-mb-md">{{ formatDate(selectedDeforestationMap.summary_statistics.prediction1_date)
                  }}</div>
                <div class="row q-col-gutter-md">
                  <template v-for="type in ['Forest', 'Non-Forest', 'Water', 'Cloud', 'Shadow']" :key="type">
                    <div class="col-6">
                      <div class="text-subtitle2">{{ t(`analysis.unified.stats.landCover.types.${type.toLowerCase()}`)
                        }}</div>
                      <div class="text-h6">{{
                        selectedDeforestationMap.summary_statistics.percentages_time1?.[type]?.toFixed(1) || 'NaN' }}%
                      </div>
                      <div class="text-caption">{{
                        selectedDeforestationMap.summary_statistics.areas_time1_ha?.[type]?.toFixed(1) || 'NaN' }} ha
                      </div>
                    </div>
                  </template>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- After -->
          <div class="col-6">
            <q-card class="land-cover-stats shadow-2">
              <q-card-section>
                <div class="text-h6 q-mb-md">{{ formatDate(selectedDeforestationMap.summary_statistics.prediction2_date)
                  }}</div>
                <div class="row q-col-gutter-md">
                  <template v-for="type in ['Forest', 'Non-Forest', 'Water', 'Cloud', 'Shadow']" :key="type">
                    <div class="col-6">
                      <div class="text-subtitle2">{{ t(`analysis.unified.stats.landCover.types.${type.toLowerCase()}`)
                        }}</div>
                      <div class="text-h6">{{
                        selectedDeforestationMap.summary_statistics.percentages_time2?.[type]?.toFixed(1) || 'NaN' }}%
                      </div>
                      <div class="text-caption">{{
                        selectedDeforestationMap.summary_statistics.areas_time2_ha?.[type]?.toFixed(1) || 'NaN' }} ha
                      </div>
                    </div>
                  </template>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('common.close')" color="primary" v-close-popup />
        <q-btn flat :label="t('common.export')" color="primary" icon="download" @click="exportStats" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <analysis-welcome-modal />
</template>

<script>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue';
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
import debounce from 'lodash/debounce';
import { useI18n } from 'vue-i18n';
import AnalysisWelcomeModal from 'components/welcome/AnalysisWelcomeModal.vue';

export default {
  name: 'UnifiedAnalysis',
  components: {
    CustomLayerSwitcher,
    AnalysisWelcomeModal
  },

  setup() {
    const mapStore = useMapStore();
    const projectStore = useProjectStore();
    const $q = useQuasar();
    const router = useRouter();
    const { t } = useI18n();

    // State
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
    const showDateSelection = ref(false);
    const primaryMapLoading = ref(false);
    const secondaryMapLoading = ref(false);

    // Add to setup() after other state declarations
    const sourceOptions = [
      { label: t('analysis.unified.hotspots.filters.sources.all'), value: 'all' },
      { label: t('analysis.unified.hotspots.filters.sources.local'), value: 'local' },
      { label: t('analysis.unified.hotspots.filters.sources.gfw'), value: 'gfw' }
    ];
    // Computed
    const getPrimaryMapLabel = computed(() => {
      if (!selectedDeforestationMap.value) return 'Select Analysis';
      return formatDate(selectedDeforestationMap.value.summary_statistics.prediction1_date);
    });

    const getSecondaryMapLabel = computed(() => {
      if (!selectedDeforestationMap.value) return 'Select Analysis';
      return formatDate(selectedDeforestationMap.value.summary_statistics.prediction2_date);
    });

    // Initialize maps
    onMounted(() => {
      if (!projectStore.currentProject) {
        $q.notify({
          message: t('analysis.unified.notifications.projectRequired'),
          color: 'warning',
          icon: 'folder',
          actions: [
            {
              label: t('analysis.unified.notifications.selectProject'),
              color: 'white',
              handler: () => router.push('/')
            }
          ]
        });
        return;
      }

      console.log("Showing dual maps")
      console.log("Primary map", primaryMap.value)
      console.log("Secondary map", secondaryMap.value)
      mapStore.initDualMaps(primaryMap.value, secondaryMap.value);
      loadInitialData();

      // Setup keyboard shortcuts
      setupKeyboardShortcuts();
      
    });

      // Clean up on unmount
      onUnmounted(() => {
        console.log("Unmounting UnifiedAnalysis")
        // console.log("Hiding dual maps")
        // mapStore.hideDualMaps()
        if (mapStore.maps.primary) mapStore.maps.primary.setTarget(null);
        if (mapStore.maps.secondary) mapStore.maps.secondary.setTarget(null);
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

    const clearMapLayers = (targetMapId) => {
      // If no specific map ID is provided, clear both maps (maintaining backward compatibility)
      const mapIds = targetMapId ? [targetMapId] : ['primary', 'secondary'];

      mapIds.forEach(mapId => {
        const map = mapStore.maps[mapId];
        if (!map) return;

        // Get all layers except OSM
        const layersToRemove = map.getLayers().getArray()
          .filter(layer => layer.get('id') !== 'osm');

        // Remove each layer properly
        layersToRemove.forEach(layer => {
          map.removeLayer(layer);
          // Only try to clear vector sources
          const source = layer.getSource();
          if (source && typeof source.clear === 'function') {
            source.clear();
          }
        });
      });
    };

    const loadHotspots = async () => {
      if (!selectedDeforestationMap.value) return;

      try {
        console.log("Loading hotspots...", selectedSource.value);
        loading.value = true;
        const response = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          minAreaHa.value,
          selectedSource.value.value
        );
        hotspots.value = response.data.features;

        // Refresh the hotspots on both maps
        await displayHotspots();


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

      const hotspotsGeoJSON = {
        type: 'FeatureCollection',
        features: hotspots.value
      };

      const getHotspotStyle = (feature) => {
        // Identify if the feature is currently selected
        const isSelected = (
          selectedHotspot.value &&
          selectedHotspot.value.properties.id === feature.getProperties().id
        );

        // Get properties
        const source = feature.getProperties().source; // 'gfw' or 'local'
        const status = feature.getProperties().verification_status; // 'verified', 'rejected', 'unsure', etc.

        // Inner stroke color (based on source) 
        // (Purple for GFW, Blue for Local)
        const innerColor = (source === 'gfw') ? '#9C27B0' : '#1976D2';

        // Outer stroke color (based on status)
        // More intuitive color for 'rejected' is red (#F44336),
        // while green (#4CAF50) and amber (#FFC107) remain
        // for 'verified' and 'unsure', respectively.
        let outerColor;
        switch (status) {
          case 'verified':
            // Green 500
            outerColor = '#4CAF50';
            break;
          case 'rejected':
            outerColor = '#607D8B';
            break;
          case 'unsure':
            // Amber 500
            outerColor = '#FFC107';
            break;
          default:
            // No status => transparent or a subtle grey if desired
            outerColor = 'rgba(0,0,0,0)';
            break;
        }

        // Adjust widths if selected, to emphasize
        const outerStrokeWidth = isSelected ? 4 : 4;
        const innerStrokeWidth = isSelected ? 1.5 : 1.5;

        // Optionally apply dashed lines to highlight selected
        const dashPattern = isSelected ? [3, 3] : [];

        // Return an array of two styles (outer stroke first, inner stroke second)
        return [
          // Outer stroke for Source
          new Style({
            stroke: new Stroke({
              color: outerColor,
              width: outerStrokeWidth,
              lineDash: dashPattern
            })
          }),
          // Inner stroke for Status
          new Style({
            stroke: new Stroke({
              color: innerColor,
              width: innerStrokeWidth,
              lineDash: dashPattern
            })
          })
        ];
      };

      // Create and add layers to both maps
      ['primary', 'secondary'].forEach(mapId => {
        // Remove existing hotspot layer if it exists
        if (hotspotLayers.value[mapId]) {
          mapStore.maps[mapId].removeLayer(hotspotLayers.value[mapId]);
        }

        const layer = new VectorLayer({
          source: new VectorSource({
            features: new GeoJSON().readFeatures(hotspotsGeoJSON)
          }),
          style: getHotspotStyle,
          title: `Deforestation Alerts`,
          id: `alerts`,
          zIndex: 2
        });

        hotspotLayers.value[mapId] = layer;
        mapStore.maps[mapId].addLayer(layer);
      });
    };

    const selectHotspot = (hotspot) => {
      selectedHotspot.value = hotspot;

      // Refresh the layer styles
      if (hotspotLayers.value.primary) {
        hotspotLayers.value.primary.changed();
        hotspotLayers.value.secondary.changed();
      }

      // Zoom to hotspot extent
      const extent = new GeoJSON().readFeature(hotspot).getGeometry().getExtent();
      mapStore.maps.primary.getView().fit(extent, {
        padding: [150, 150, 150, 150],
        maxZoom: 17
      });
    };

    const verifyHotspot = async (hotspot, status) => {
      try {
        await api.verifyHotspot(hotspot.properties.id, status);

        // Update local state
        hotspot.properties.verification_status = status;

        // Force refresh of vector layers to update styles
        if (hotspotLayers.value.primary) {
          // Update the feature properties in both layers
          ['primary', 'secondary'].forEach(mapId => {
            const layer = hotspotLayers.value[mapId];
            const features = layer.getSource().getFeatures();
            const feature = features.find(f =>
              f.getProperties().id === hotspot.properties.id
            );
            if (feature) {
              feature.set('verification_status', status, true);
            }
            layer.changed(); // Force style refresh
          });
        }

        $q.notify({
          type: 'positive',
          message: t('analysis.unified.notifications.verificationUpdated')
        });
      } catch (error) {
        console.error('Error verifying hotspot:', error);
        $q.notify({
          type: 'negative',
          message: t('analysis.unified.notifications.verificationError')
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
      return predictions.value.map(p => {
        // Create a date object for the first day of the month
        const [year, month] = p.basemap_date.split('-');
        const dateObj = new Date(year, parseInt(month) - 1, 1);  // month is 0-based in JS

        return {
          label: date.formatDate(dateObj, 'MMMM YYYY'),
          value: p.basemap_date
        };
      });
    });

    const analyzeDeforestation = async () => {
      if (!startDate.value || !endDate.value) return;

      try {
        primaryMapLoading.value = true;
        secondaryMapLoading.value = true;

        const pred1 = predictions.value.find(p => p.basemap_date === startDate.value.value);
        const pred2 = predictions.value.find(p => p.basemap_date === endDate.value.value);

        if (!pred1 || !pred2) {
          throw new Error('Could not find predictions for the selected dates.');
        }

        const aoiShape = typeof projectStore.currentProject.aoi === 'string'
          ? JSON.parse(projectStore.currentProject.aoi)
          : projectStore.currentProject.aoi;

        // Run analysis and get results - this should create a new deforestation map
        const results = await api.getChangeAnalysis({
          prediction1_id: pred1.id,
          prediction2_id: pred2.id,
          aoi_shape: aoiShape
        });

        // Make sure we have a valid deforestation map from the results
        if (!results.data?.deforestation_prediction_id) {
          throw new Error('Change analysis did not return a valid deforestation map ID');
        }

        // Store the deforestation map
        selectedDeforestationMap.value = {
          id: results.data.deforestation_prediction_id,
          name: `Deforestation ${startDate.value.label} to ${endDate.value.label}`,
          summary_statistics: {
            prediction1_date: startDate.value.value,
            prediction2_date: endDate.value.value,
            ...results.data.summary_statistics
          }
        };

        // Load hotspots for this deforestation map
        const hotspotsResponse = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,  // Use the deforestation map ID
          minAreaHa.value,
          selectedSource.value.value
        );

        hotspots.value = hotspotsResponse.data.features;

        // Display the hotspots on the maps
        await displayHotspots();

        // Reload the existing analysis list
        await loadInitialData();

        $q.notify({
          type: 'positive',
          message: t('analysis.unified.notifications.analysisSaved')
        });
      } catch (error) {
        console.error('Error analyzing deforestation:', error);
        $q.notify({
          type: 'negative',
          message: t('analysis.unified.notifications.analysisError')
        });
      } finally {
        primaryMapLoading.value = false;
        secondaryMapLoading.value = false;
      }
    };


    // Replace updatePrimaryMap and updateSecondaryMap with this single function
    const updateMap = async (mapId, date) => {
      try {
        if (mapId === 'primary') {
          primaryMapLoading.value = true;
        } else {
          secondaryMapLoading.value = true;
        }

        if (!date) return;

        // Clear the map layers
        clearMapLayers(mapId);


        const prediction = predictions.value.find(p => p.basemap_date === date.value.value);
        if (prediction) {
          // Clear only prediction and basemap layers, preserving AOI layer
          const mapLayers = mapStore.maps[mapId].getLayers().getArray();
          mapLayers.forEach(layer => {
            const layerId = layer.get('id');
            // Only remove prediction and planet basemap layers
            if (layerId?.includes('landcover-') || layerId === 'planet-basemap') {
              mapStore.maps[mapId].removeLayer(layer);
            }
          });

          // Add Planet basemap first (so it's at the bottom)
          console.log(`Adding Planet basemap for ${mapId} date:`, date.value.value);
          const basemap = mapStore.createPlanetBasemap(date.value.value);
          basemap.setVisible(true);
          basemap.setZIndex(1); // Set lower z-index for basemap
          mapStore.addLayerToDualMaps(basemap, mapId);

          // Add land cover prediction on top
          console.log(`Adding land cover prediction for ${mapId}:`, prediction.name);
          await mapStore.displayPrediction(
            prediction.file,
            `landcover-${prediction.id}`,
            prediction.name,
            'landcover',
            mapId
          );

          // Ensure proper layer ordering
          const layers = mapStore.maps[mapId].getLayers().getArray();
          layers.forEach(layer => {
            const layerId = layer.get('id');
            if (layerId?.includes('landcover-')) {
              layer.setZIndex(3); // Prediction layer on top
            } else if (layerId === 'planet-basemap') {
              layer.setZIndex(1); // Basemap in middle
            } else if (layerId === 'area-of-interest') {
              layer.setZIndex(2); // AOI between basemap and prediction
            }
          });
        }
      } catch (error) {
        console.error(`Error updating ${mapId} map:`, error);
        throw error;
      } finally {
        if (mapId === 'primary') {
          primaryMapLoading.value = false;
        } else {
          secondaryMapLoading.value = false;
        }
      }
    };

    // Update the watchers to use the new function
    watch(startDate, async (newDate) => {
      if (newDate) {
        await updateMap('primary', startDate);
      }
    });

    watch(endDate, async (newDate) => {
      if (newDate) {
        await updateMap('secondary', endDate);
      }
    });

    const loadExistingAnalysis = async (map) => {
      try {
        loading.value = true;
        primaryMapLoading.value = true;
        secondaryMapLoading.value = true;
        selectedDeforestationMap.value = map;

        // Load hotspots for the selected analysis
        const hotspotsResponse = await api.getDeforestationHotspots(
          map.id,
          minAreaHa.value,
          selectedSource.value.value
        );

        hotspots.value = hotspotsResponse.data.features;

        // Clear existing layers
        clearMapLayers();

        // Add AOI layer first
        if (projectStore.currentProject?.aoi) {
          const aoiGeojson = typeof projectStore.currentProject.aoi === 'string'
            ? JSON.parse(projectStore.currentProject.aoi)
            : projectStore.currentProject.aoi;

          const { layer: primaryAOILayer } = mapStore.createAOILayer(aoiGeojson);
          const { layer: secondaryAOILayer } = mapStore.createAOILayer(aoiGeojson);

          mapStore.maps.primary.addLayer(primaryAOILayer);
          mapStore.maps.secondary.addLayer(secondaryAOILayer);
        }

        // Add basemaps (visible by default)
        const beforeBasemap = mapStore.createPlanetBasemap(map.summary_statistics.prediction1_date);
        const afterBasemap = mapStore.createPlanetBasemap(map.summary_statistics.prediction2_date);
        beforeBasemap.setOpacity(1.0);
        afterBasemap.setOpacity(1.0);
        mapStore.addLayerToDualMaps(beforeBasemap, 'primary');
        mapStore.addLayerToDualMaps(afterBasemap, 'secondary');

        // Find and add land cover predictions (not visible by default)
        const pred1 = predictions.value.find(p => p.basemap_date === map.summary_statistics.prediction1_date);
        const pred2 = predictions.value.find(p => p.basemap_date === map.summary_statistics.prediction2_date);

        if (pred1) {
          await mapStore.displayPrediction(
            pred1.file,
            `landcover-${pred1.id}`,
            pred1.name,
            'landcover',
            'primary'
          );
        }

        if (pred2) {
          await mapStore.displayPrediction(
            pred2.file,
            `landcover-${pred2.id}`,
            pred2.name,
            'landcover',
            'secondary'
          );
        }

        // Make prediction layers invisible by default
        mapStore.maps.primary.getLayers().forEach(layer => {
          if (layer.get('id')?.includes('landcover-')) {
            layer.setVisible(false);
          }
        });
        mapStore.maps.secondary.getLayers().forEach(layer => {
          if (layer.get('id')?.includes('landcover-')) {
            layer.setVisible(false);
          }
        });

        // Display hotspots on top
        await displayHotspots();

        // The layer switcher will automatically update when layers change
        // No need to call updateLayers explicitly

      } catch (error) {
        console.error('Error loading existing analysis:', error);
        $q.notify({
          type: 'negative',
          message: t('analysis.unified.notifications.analysisError')
        });
      } finally {
        loading.value = false;
        primaryMapLoading.value = false;
        secondaryMapLoading.value = false;
      }
    };

    const formatDateRange = (startDate, endDate) => {
      return `${date.formatDate(startDate, 'MMM YYYY')} - ${date.formatDate(endDate, 'MMM YYYY')}`;
    };

    const confirmDeleteAnalysis = (map) => {
      $q.dialog({
        title: t('analysis.unified.dialogs.delete.title'),
        message: t('analysis.unified.dialogs.delete.message'),
        ok: {
          color: 'negative',
          label: t('analysis.unified.dialogs.delete.confirm')
        },
        cancel: t('analysis.unified.dialogs.delete.cancel')
      }).onOk(() => {
        deleteAnalysis(map);
      });
    };

    const deleteAnalysis = async (map) => {
      try {
        await projectStore.deleteDeforestationMap(map.id);
        await loadInitialData();
        $q.notify({
          type: 'positive',
          message: t('analysis.unified.notifications.analysisDeleted')
        });
      } catch (error) {
        console.error('Error deleting analysis:', error);
        $q.notify({
          type: 'negative',
          message: t('analysis.unified.notifications.deleteError')
        });
      }
    };

    // Add to setup()
    const updateHotspotFilters = async () => {
      if (!selectedDeforestationMap.value) return;

      try {
        loading.value = true;

        // Load hotspots with new filters
        const hotspotsResponse = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          minAreaHa.value,
          selectedSource.value.value
        );

        hotspots.value = hotspotsResponse.data.features;

        // Update map display
        await displayHotspots();

      } catch (error) {
        console.error('Error updating hotspots:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to update hotspots'
        });
      } finally {
        loading.value = false;
      }
    };

    // Add to setup()
    const exportHotspots = async (type) => {
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
            min_area_threshold_ha: minAreaHa.value,
            source_breakdown: {
              local: hotspotsToExport.filter(h => h.properties.source === 'local').length,
              gfw: hotspotsToExport.filter(h => h.properties.source === 'gfw').length
            },
            export_type: type,
            export_timestamp: new Date().toISOString(),
            projection: 'EPSG:3857',
            projection_name: 'Web Mercator'
          },
          features: hotspotsToExport.map(h => ({
            type: 'Feature',
            geometry: h.geometry,
            properties: {
              id: h.properties.id,
              area_ha: h.properties.area_ha,
              verification_status: h.properties.verification_status || 'unverified',
              source: h.properties.source,  // Add source information
              confidence: h.properties.confidence || null,  // Add confidence for GFW alerts
              perimeter_m: h.properties.perimeter_m,
              compactness: h.properties.compactness,
              edge_density: h.properties.edge_density,
              centroid_lon: h.properties.centroid_lon,
              centroid_lat: h.properties.centroid_lat
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

        $q.notify({
          type: 'positive',
          message: t('analysis.unified.notifications.exportSuccess')
        });
      } catch (error) {
        console.error('Error exporting data:', error);
        $q.notify({
          type: 'negative',
          message: t('analysis.unified.notifications.exportError')
        });
      }
    };

    // Add debounced version for the min area input
    const debouncedUpdateFilters = debounce(updateHotspotFilters, 500);

    // Add to setup()
    const setupKeyboardShortcuts = () => {
      const handleKeyPress = (event) => {
        if (!hotspots.value?.length) return;

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

      window.addEventListener('keydown', handleKeyPress);
      return () => window.removeEventListener('keydown', handleKeyPress);
    };

    const scrollArea = ref(null);

    const navigateHotspots = (direction) => {
      if (!hotspots.value?.length) return;

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
        const element = scrollArea.value?.$el.querySelector(`.q-item:nth-child(${newIndex + 1})`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    };

    // Add these computed properties in setup()
    const getStatsTitle = computed(() => {
      if (!selectedDeforestationMap.value) return 'Analysis Statistics';
      return `Analysis Statistics: ${selectedDeforestationMap.value.name}`;
    });

    const getStatsSubtitle = computed(() => {
      if (!selectedDeforestationMap.value) return '';
      const stats = selectedDeforestationMap.value.summary_statistics;
      return `Analysis Period: ${formatDateRange(stats.prediction1_date, stats.prediction2_date)}`;
    });

    const deforestationStats = computed(() => {
      if (!selectedDeforestationMap.value?.summary_statistics) return null;
      return {
        deforested_area_ha: selectedDeforestationMap.value.summary_statistics.deforested_area_ha || 0,
        deforestation_rate: selectedDeforestationMap.value.summary_statistics.deforestation_rate || 0,
        total_forest_area_ha: selectedDeforestationMap.value.summary_statistics.total_forest_area_ha || 0,
        annual_rate_ha: selectedDeforestationMap.value.summary_statistics.annual_rate_ha || 0,
        annual_rate_percentage: selectedDeforestationMap.value.summary_statistics.annual_rate_percentage || 0
      };
    });

    // Add these methods in setup()
    const exportStats = () => {
      if (!selectedDeforestationMap.value) return;

      try {
        // Create CSV rows
        const rows = [
          // Header row
          ['Analysis Name', selectedDeforestationMap.value.name],
          ['Analysis Period', `${selectedDeforestationMap.value.summary_statistics.prediction1_date} to ${selectedDeforestationMap.value.summary_statistics.prediction2_date}`],
          ['Total AOI Area (ha)', projectStore.aoiAreaHa.toFixed(1)],
          ['Minimum Hotspot Size (ha)', minAreaHa.value],
          [''],  // Empty row for spacing

          // Hotspot Stats by Source
          ['Hotspot Statistics by Source (Hotspots ≥ ' + minAreaHa.value + ' ha)'],
          ['Source', 'Count', 'Area (ha)', 'Annual Rate (ha/year)', '% of AOI'],
          ['Local Alerts',
            sourceStats.value.local.count,
            sourceStats.value.local.area.toFixed(1),
            sourceStats.value.local.rate.toFixed(1),
            (sourceStats.value.local.area / projectStore.aoiAreaHa * 100).toFixed(1)
          ],
          ['GFW Alerts',
            sourceStats.value.gfw.count,
            sourceStats.value.gfw.area.toFixed(1),
            sourceStats.value.gfw.rate.toFixed(1),
            (sourceStats.value.gfw.area / projectStore.aoiAreaHa * 100).toFixed(1)
          ],
          [''],  // Empty row for spacing

          // Deforestation Stats
          ['Deforestation Statistics'],
          ['Total Deforested Area (ha)', deforestationStats.value.deforested_area_ha.toFixed(1)],
          ['Deforestation Rate (%)', deforestationStats.value.deforestation_rate.toFixed(1)],
          ['Annual Rate (ha/year)', deforestationStats.value.annual_rate_ha.toFixed(1)],
          ['Annual Rate (%/year)', deforestationStats.value.annual_rate_percentage.toFixed(1)],
          [''],  // Empty row for spacing

          // Hotspot Stats by Source
          ['Hotspot Statistics by Source (Hotspots ≥ ' + minAreaHa.value + ' ha)'],
          ['Source', 'Count', 'Area (ha)', 'Annual Rate (ha/year)', '% of AOI'],
          ['Local Alerts',
            sourceStats.value.local.count,
            sourceStats.value.local.area.toFixed(1),
            sourceStats.value.local.rate.toFixed(1),
            (sourceStats.value.local.area / projectStore.aoiAreaHa * 100).toFixed(1)
          ],
          ['GFW Alerts',
            sourceStats.value.gfw.count,
            sourceStats.value.gfw.area.toFixed(1),
            sourceStats.value.gfw.rate.toFixed(1),
            (sourceStats.value.gfw.area / projectStore.aoiAreaHa * 100).toFixed(1)
          ],
          [''],  // Empty row for spacing

          // Status Breakdown
          ['Status Breakdown'],
          ['Status', 'Count', 'Area (ha)', 'Annual Rate (ha/year)', '% of AOI'],
          ...['Verified', 'Unsure', 'Rejected', 'Unverified'].map(status => {
            const hotspotsWithStatus = hotspots.value.filter(h =>
              status === 'Unverified' ? !h.properties.verification_status : h.properties.verification_status === status.toLowerCase()
            );
            const area = hotspotsWithStatus.reduce((sum, h) => sum + h.properties.area_ha, 0);
            const yearsDiff = (new Date(selectedDeforestationMap.value.summary_statistics.prediction2_date) -
              new Date(selectedDeforestationMap.value.summary_statistics.prediction1_date)) /
              (1000 * 60 * 60 * 24 * 365.25);
            const rate = area / yearsDiff;
            return [
              status,
              hotspotsWithStatus.length,
              area.toFixed(1),
              rate.toFixed(1),
              (area / projectStore.aoiAreaHa * 100).toFixed(1)
            ];
          })
        ];

        // Convert rows to CSV string
        const csvContent = rows.map(row => row.join(',')).join('\n');

        // Create and trigger download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `deforestation_analysis_stats_${selectedDeforestationMap.value.id}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        $q.notify({
          type: 'positive',
          message: t('analysis.unified.notifications.exportSuccess')
        });
      } catch (error) {
        console.error('Error exporting statistics:', error);
        $q.notify({
          type: 'negative',
          message: t('analysis.unified.notifications.exportError')
        });
      }
    };

    // Add these computed properties in setup() after other computed properties
    const sourceStats = computed(() => {
      const stats = {
        local: { count: 0, area: 0, rate: 0 },
        gfw: { count: 0, area: 0, rate: 0 }
      }

      hotspots.value.forEach(h => {
        const source = h.properties.source;
        stats[source].count++;
        stats[source].area += h.properties.area_ha;
      });

      // Calculate rates for each source
      if (selectedDeforestationMap.value) {
        const beforeDate = new Date(selectedDeforestationMap.value.summary_statistics.prediction1_date);
        const afterDate = new Date(selectedDeforestationMap.value.summary_statistics.prediction2_date);
        const yearsDiff = (afterDate - beforeDate) / (1000 * 60 * 60 * 24 * 365.25);

        stats.local.rate = stats.local.area / yearsDiff;
        stats.gfw.rate = stats.gfw.area / yearsDiff;
      }

      return stats;
    });

    const localStatusBreakdown = computed(() => {
      return calculateStatusBreakdown(hotspots.value.filter(h => h.properties.source === 'local'));
    });

    const gfwStatusBreakdown = computed(() => {
      return calculateStatusBreakdown(hotspots.value.filter(h => h.properties.source === 'gfw'));
    });

    // Add helper function for status breakdown calculations
    const calculateStatusBreakdown = (sourceHotspots) => {
      const statuses = ['verified', 'unsure', 'rejected', 'unverified'];
      const colors = ['green', 'amber', 'blue-grey', 'purple'];
      const displayNames = ['Verified', 'Unsure', 'Rejected', 'Unverified'];

      const totalCount = sourceHotspots.length;
      const totalArea = sourceHotspots.reduce((sum, h) => sum + h.properties.area_ha, 0);

      return statuses.map((status, index) => {
        const hotspotsWithStatus = sourceHotspots.filter(h =>
          status === 'unverified'
            ? !h.properties.verification_status
            : h.properties.verification_status === status
        );

        const count = hotspotsWithStatus.length;
        const area = hotspotsWithStatus.reduce((sum, h) => sum + h.properties.area_ha, 0);

        // Calculate rate based on the time period
        let rate = 0;
        if (selectedDeforestationMap.value) {
          const beforeDate = new Date(selectedDeforestationMap.value.summary_statistics.prediction1_date);
          const afterDate = new Date(selectedDeforestationMap.value.summary_statistics.prediction2_date);
          const yearsDiff = (afterDate - beforeDate) / (1000 * 60 * 60 * 24 * 365.25);
          rate = area / yearsDiff;
        }

        return {
          name: displayNames[index],
          color: colors[index],
          count,
          percentage: totalCount ? (count / totalCount) * 100 : 0,
          area,
          areaPercentage: totalArea ? (area / totalArea) * 100 : 0,
          areaPercentageOfAOI: (area / projectStore.aoiAreaHa) * 100,
          rate
        };
      });
    };

    const formatDate = (dateStr) => {
      if (!dateStr) return '';

      // Add day to the partial date string
      const [year, month] = dateStr.split('-');
      const dateObj = new Date(year, parseInt(month) - 1, 1);  // month is 0-based in JS

      return date.formatDate(dateObj, 'MMMM YYYY');
    };

    return {
      // State
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
      showDateSelection,
      primaryMapLoading,
      secondaryMapLoading,
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
      sourceOptions,
      loadExistingAnalysis,
      formatDateRange,
      confirmDeleteAnalysis,
      deleteAnalysis,
      debouncedUpdateFilters,
      scrollArea,
      navigateHotspots,
      setupKeyboardShortcuts,
      getStatsTitle,
      getStatsSubtitle,
      deforestationStats,
      exportStats,
      projectStore,
      sourceStats,
      localStatusBreakdown,
      gfwStatusBreakdown,
      exportHotspots,
      formatDate,
      t,
    };
  }
};
</script>
<style lang="scss" scoped>
.analysis-controls-container {
  width: var(--app-sidebar-width);
  height: calc(100vh - var(--app-header-height));
  background: #fafafa;
}

.analysis-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  box-shadow: none;
  border-radius: 0;
  overflow: hidden;
}

/* Header section - Fixed height */
.analysis-header-section {
  flex: 0 0 auto;
  min-height: 220px;
}

/* Hotspots section - Flexible height */
.analysis-hotspots-section {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding-top: 0px;
}

/* Footer section - Fixed height */
.analysis-footer-section {
  flex: 0 0 auto;
  min-height: 60px;
  background: white;
  z-index: 1;
}

/* Adjust the hotspots scroll area to fill available space */
.hotspots-scroll-area {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

/* Make the card sections more compact */
.q-card-section {
  padding: 8px 16px;
}

/* Adjust input spacing */
.modern-input {
  margin-bottom: 4px;
}

.comparison-container {
  flex: 1;
  height: calc(100vh - var(--app-header-height));
  padding: 16px;
  background: #fafafa;
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
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
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

.selected-analysis {
  background: rgba(0, 0, 0, 0.05);
  border-left: 4px solid var(--q-primary);
}

.map-legend {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: white;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  font-size: 12px;
  z-index: 1000;

  .legend-title {
    font-weight: 600;
    margin-bottom: 5px;
    font-size: 0.8rem;
  }

  .mt-2 {
    margin-top: 8px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    margin: 4px 0;

    .legend-line {
      width: 20px;
      height: 2px;
      margin-right: 8px;
    }

    .local-line {
      background: #1976D2;
    }

    .gfw-line {
      background: #9C27B0;
    }

    .verified-line {
      background: #4CAF50;
    }

    .unsure-line {
      background: #FFC107;
    }

    .rejected-line {
      background: #607D8B;
    }
  }
}

.hotspot-item {
  border-left: 4px solid transparent;
  transition: all 0.2s ease;

  &.selected-hotspot {
    background: rgba(25, 118, 210, 0.1) !important;
    border-left-color: var(--q-primary);
    font-weight: 500;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  }

  &.local-alert {
    border-left-color: #1976D2;

    &.selected-hotspot {
      background: rgba(25, 118, 210, 0.1) !important;
    }
  }

  &.gfw-alert {
    border-left-color: #9C27B0;

    &.selected-hotspot {
      background: rgba(156, 39, 176, 0.1) !important;
    }
  }

  &.verified {
    background: rgba(76, 175, 80, 0.05);

    &.selected-hotspot {
      background: rgba(76, 175, 80, 0.15) !important;
    }
  }

  &.rejected {
    background: rgba(96, 125, 139, 0.05);

    &.selected-hotspot {
      background: rgba(96, 125, 139, 0.15) !important;
    }
  }

  &.unsure {
    background: rgba(255, 193, 7, 0.05);

    &.selected-hotspot {
      background: rgba(255, 193, 7, 0.15) !important;
    }
  }
}

.verification-buttons {
  gap: 2px !important;

  .q-btn {
    padding: 4px;
    margin: 0;
  }
}

.stats-dialog {
  width: 90vw;
  max-width: 1200px;
}

.land-cover-stats {
  height: 100%;
}

/* Add loading overlay styles */
.map-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: opacity 1.0s ease, visibility 1.0s ease;
  pointer-events: none;

  .text-caption {
    margin-top: 1rem;
    font-weight: 500;
  }

  &.active {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
  }
}
</style>