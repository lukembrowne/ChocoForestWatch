<!-- Enhanced AOI summary stats component -->
<template>
  <div class="land-cover-stats">

    <!-- Forest Cover Map Selection -->
    <div class="benchmark-section">
      <div class="workflow-step">
        <div class="step-number">1</div>
        <div class="step-content">
          <div class="input-label">
            <q-icon name="map" class="label-icon" />
            {{ t('sidebar.landCover.chooseMap') }}
            <q-btn 
              flat 
              round 
              dense 
              size="xs" 
              icon="info" 
              class="info-btn"
            >
              <q-tooltip class="bg-dark text-white" max-width="280px">
                {{ t('sidebar.landCover.chooseMapTooltip') }}
              </q-tooltip>
            </q-btn>
          </div>
          <q-select
            outlined
            v-model="benchmark"
            :options="benchmarkOptions"
            option-label="label"
            option-value="value"
            emit-value
            map-options
            :disable="isDrawing || isMapLoading"
            class="benchmark-select"
            :placeholder="t('sidebar.landCover.selectMapPlaceholder')"
          >
            <template v-slot:prepend>
              <q-icon name="layers" color="primary" />
            </template>
            <template v-slot:append v-if="isMapLoading">
              <q-spinner color="primary" size="sm" />
            </template>
          </q-select>
        </div>
      </div>
    </div>

    <!-- Analysis Section -->
    <div class="analysis-section">
      <div class="workflow-step" v-if="!stats">
        <div class="step-number">2</div>
        <div class="step-content">
          <div class="input-label">
            <q-icon name="crop_free" class="label-icon" />
            {{ t('sidebar.landCover.drawArea') }}
            <q-btn 
              flat 
              round 
              dense 
              size="xs" 
              icon="info" 
              class="info-btn"
            >
              <q-tooltip class="bg-dark text-white" max-width="280px">
                {{ t('sidebar.landCover.drawAreaTooltip') }}
              </q-tooltip>
            </q-btn>
          </div>
          <div class="no-analysis">
            <div class="no-analysis-content">
              <q-icon name="draw" size="32px" class="no-analysis-icon" />
              <div class="no-analysis-text">{{ t('sidebar.landCover.readyToAnalyze') }}</div>
              <div class="no-analysis-subtitle">{{ t('sidebar.landCover.clickThenDraw') }}</div>
              <q-btn 
                color="primary" 
                icon="draw" 
                :label="t('sidebar.landCover.startDrawing')" 
                @click="startDraw" 
                :loading="isLoading"
                class="draw-btn"
                size="md"
                rounded
                :disable="!benchmark"
              >
                <q-tooltip v-if="!benchmark">{{ t('sidebar.landCover.selectMapFirst') }}</q-tooltip>
              </q-btn>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="results-section">
        <!-- Results Header -->
        <div class="results-header">
          <div class="step-number completed">✓</div>
          <div class="results-title">
            <q-icon name="analytics" class="label-icon" />
            {{ t('sidebar.landCover.analysisResults') }}
          </div>
        </div>
        
        <!-- Area Info -->
        <div class="area-info" v-if="stats">
          <q-icon :name="stats.area_name === 'Western Ecuador' ? 'public' : 'place'" size="sm" />
          <span class="area-name" :class="{ 'regional-stats': stats.area_name === 'Western Ecuador' }">
            {{ stats.area_name === 'Western Ecuador' ? 'All of Western Ecuador' : (stats.area_name ? stats.area_name : t('sidebar.landCover.customArea')) }}
          </span>
          <q-chip 
            v-if="stats.area_name === 'Western Ecuador'" 
            size="sm" 
            color="green" 
            text-color="white"
            icon="analytics"
            class="regional-chip"
          >
            {{ t('sidebar.landCover.regional') }}
          </q-chip>
        </div>
        
        <!-- Action Buttons -->
        <div class="action-bar">
          <q-btn 
            v-if="!isDrawing"
            icon="crop_free" 
            color="primary" 
            :label="t('sidebar.landCover.analyzeNewArea')" 
            @click="clear"
            outline
            class="action-btn"
            size="sm"
          />
          <q-btn 
            v-if="isDrawing"
            icon="close" 
            color="negative" 
            :label="t('sidebar.landCover.cancelDrawing')" 
            @click="cancelDrawing"
            outline
            class="action-btn"
            size="sm"
          />
          <q-btn 
            v-if="!isDrawing && stats.area_name !== 'Western Ecuador'"
            icon="public" 
            color="green" 
            :label="t('sidebar.landCover.showRegionalStats')" 
            @click="loadRegionalStats"
            flat
            class="action-btn"
            size="sm"
          />
        </div>

        <!-- Statistics Cards -->
        <div class="stats-grid">
          <div class="stat-card forest-card">
            <div class="stat-icon">
              <q-icon name="park" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ (stats.pct_forest * 100).toFixed(1) }}%</div>
              <div class="stat-label">{{ t('sidebar.landCover.forestCover') }}</div>
              <div class="stat-detail">{{ stats.forest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</div>
            </div>
          </div>

          <div class="stat-card nonforest-card">
            <div class="stat-icon">
              <q-icon name="landscape" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ (100 - stats.pct_forest * 100).toFixed(1) }}%</div>
              <div class="stat-label">{{ t('sidebar.landCover.nonForest') }}</div>
              <div class="stat-detail">{{ stats.nonforest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</div>
            </div>
          </div>

          <div class="stat-card missing-card">
            <div class="stat-icon">
              <q-icon name="help_outline" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ (stats.pct_missing * 100).toFixed(1) }}%</div>
              <div class="stat-label">{{ t('sidebar.landCover.noData') }}</div>
              <div class="stat-detail">{{ stats.pct_missing > 0 ? t('sidebar.landCover.missingPixels') : t('sidebar.landCover.completeCoverage') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useI18n } from 'vue-i18n'

const mapStore = useMapStore()
const { t } = useI18n()

const stats         = computed(() => mapStore.summaryStats)
const isLoading     = computed(() => mapStore.isLoading)
const isDrawing     = computed(() => mapStore.isDrawingSummaryAOI)
const isMapLoading  = computed(() => mapStore.isLoading)

const benchmarkOptions = computed(() => mapStore.availableBenchmarks)
const benchmark        = computed({
  get: () => mapStore.selectedBenchmark,
  set: (val) => mapStore.selectedBenchmark = val,
})

// Auto-refresh stats and load forest cover map when benchmark changes
watch(benchmark, async (newBenchmark, oldBenchmark) => {
  // Auto-load the selected forest cover map onto the main map
  if (newBenchmark && newBenchmark !== oldBenchmark) {
    mapStore.addBenchmarkLayer(newBenchmark)
    
    // Automatically load western Ecuador stats for the new benchmark
    // unless the user has drawn their own custom area
    if (!mapStore.summaryAOILayer) {
      await mapStore.loadWesternEcuadorStats()
    }
  }
  
  // Auto-refresh stats if user has drawn a rectangle
  if (stats.value && mapStore.summaryAOILayer) {
    await mapStore.startSummaryAOIDraw(); // triggers new call
  }
})

function startDraw() {
  mapStore.startSummaryAOIDraw()
}

async function clear() {
  mapStore.clearSummaryAOI()
  // Start drawing a new area instead of auto-loading regional stats
  startDraw()
}

function cancelDrawing() {
  mapStore.clearSummaryAOI()
  // Load regional stats after canceling drawing
  loadRegionalStats()
}

async function loadRegionalStats() {
  await mapStore.loadWesternEcuadorStats()
}

// Automatically load western Ecuador stats when component mounts
onMounted(async () => {
  // Only load if no custom area has been drawn and we have a selected benchmark
  if (!mapStore.summaryAOILayer && !stats.value && benchmark.value) {
    await mapStore.loadWesternEcuadorStats()
  }
})

</script>


<style scoped>
.land-cover-stats {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.section-header {
  background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
  padding: 16px;
  border-bottom: 1px solid #e0e7e4;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #1b5e20;
  margin-bottom: 4px;
}

.section-icon {
  font-size: 20px;
  margin-right: 8px;
  color: #4caf50;
}

.section-subtitle {
  font-size: 13px;
  color: #2e7d32;
  opacity: 0.8;
}

.benchmark-section {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.input-label {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #424242;
  margin-bottom: 8px;
}

.label-icon {
  font-size: 16px;
  margin-right: 6px;
  color: #666;
}

.benchmark-select {
  border-radius: 8px;
}

.benchmark-select :deep(.q-field__control) {
  border-radius: 8px;
  transition: all 0.2s ease;
}

.benchmark-select :deep(.q-field--focused .q-field__control) {
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.15);
}

.workflow-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #4caf50;
  color: white;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 4px;
}

.step-number.completed {
  background: #66bb6a;
  font-size: 16px;
}

.step-content {
  flex: 1;
}

.help-btn, .info-btn {
  margin-left: 4px;
  opacity: 0.7;
}

.help-btn:hover, .info-btn:hover {
  opacity: 1;
}

.map-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 13px;
  color: #2e7d32;
  opacity: 0.9;
}

.map-info.loading {
  color: #1976d2;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.results-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.results-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #1b5e20;
}

.results-title .label-icon {
  margin-right: 8px;
  color: #4caf50;
}

.analysis-section {
  padding: 16px;
}

.no-analysis {
  text-align: center;
  padding: 24px 16px;
}

.no-analysis-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.no-analysis-icon {
  color: #9e9e9e;
  opacity: 0.7;
}

.no-analysis-text {
  font-size: 16px;
  font-weight: 500;
  color: #424242;
}

.no-analysis-subtitle {
  font-size: 13px;
  color: #757575;
  margin-bottom: 8px;
}

.draw-btn {
  margin-top: 8px;
  padding: 8px 24px;
  text-transform: none;
  font-weight: 500;
}

.results-section {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.area-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #666;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 3px solid #e0e0e0;
}

.area-name {
  font-weight: 500;
  flex: 1;
}

.area-name.regional-stats {
  color: #2e7d32;
  font-weight: 600;
  font-size: 14px;
}

.area-info:has(.regional-stats) {
  background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
  border-left-color: #4caf50;
}

.regional-chip {
  margin-left: auto;
}

.action-bar {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  text-transform: none;
  font-weight: 500;
  border-radius: 20px;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.forest-card {
  background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
  border: 1px solid #c8e6c9;
}

.nonforest-card {
  background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%);
  border: 1px solid #ffccbc;
}

.missing-card {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1f5fe 100%);
  border: 1px solid #e1bee7;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  margin-right: 16px;
  font-size: 24px;
}

.forest-card .stat-icon {
  background: rgba(76, 175, 80, 0.15);
  color: #2e7d32;
}

.nonforest-card .stat-icon {
  background: rgba(255, 152, 0, 0.15);
  color: #ef6c00;
}

.missing-card .stat-icon {
  background: rgba(156, 39, 176, 0.15);
  color: #7b1fa2;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #212121;
  line-height: 1;
  margin-bottom: 2px;
}

.stat-label {
  font-size: 14px;
  font-weight: 600;
  color: #424242;
  margin-bottom: 2px;
}

.stat-detail {
  font-size: 12px;
  color: #757575;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .section-header {
    padding: 12px;
  }
  
  .section-title {
    font-size: 15px;
  }
  
  .benchmark-section,
  .analysis-section {
    padding: 12px;
  }
  
  .no-analysis {
    padding: 20px 12px;
  }
  
  .stat-card {
    padding: 12px;
  }
  
  .stat-icon {
    width: 40px;
    height: 40px;
    margin-right: 12px;
    font-size: 20px;
  }
  
  .stat-value {
    font-size: 20px;
  }
}
</style> 