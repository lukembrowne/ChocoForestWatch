<template>
  <div class="analysis-panel">
    <!-- Map Configuration Section -->
    <div class="benchmark-section">
      <div class="section-header-compact">
        <span class="section-title-compact">{{ t('analysis.panel.configureMap') }}</span>
      </div>
      
      <!-- Forest Cover Dataset Subsection -->
      <div class="subsection-compact">
        <div class="subsection-header-compact">
          <span class="subsection-title-compact">{{ t('analysis.panel.forestCoverDataset') }}</span>
          <q-icon name="info" size="xs" class="subsection-info-icon">
            <q-tooltip>
              {{ t('analysis.panel.forestCoverDatasetTooltip') }}
            </q-tooltip>
          </q-icon>
        </div>
        <div class="benchmark-selector-container">
          <CompactDatasetSelector />
        </div>
      </div>

      <!-- Satellite Basemap Subsection -->
      <div class="subsection-compact">
        <div class="subsection-header-compact">
          <span class="subsection-title-compact">{{ t('analysis.panel.satelliteBasemap') }}</span>
          <q-icon name="info" size="xs" class="subsection-info-icon">
            <q-tooltip>
              {{ t('analysis.panel.satelliteBasemapTooltip') }}
            </q-tooltip>
          </q-icon>
        </div>
        <div class="planet-control-container">
          <q-btn
            :class="{ 'planet-btn-active': isPlanetImageryActive }"
            class="planet-btn full-width"
            @click="togglePlanetImagery"
            size="sm"
            no-caps
            flat
            :data-umami-event="'toggle_planet_imagery'"
            :data-umami-event-action="isPlanetImageryActive ? 'remove' : 'add'"
            :data-umami-event-date="mapStore.selectedBasemapDate"
          >
            <div class="planet-btn-content">
              <q-icon name="satellite" size="sm" class="planet-icon" />
              <span class="planet-text">
                {{ isPlanetImageryActive ? t('analysis.panel.planetImagery.remove') : t('analysis.panel.planetImagery.add') }}
              </span>
            </div>
          </q-btn>
        </div>
      </div>
    </div>

    <!-- Area Selection Section -->
    <div class="area-selection-section">
      <div class="section-header-compact">
        <span class="section-title-compact">{{ t('analysis.panel.defineArea') }}</span>
      </div>

      <!-- Area Method Buttons -->
      <div class="method-buttons-row">
        <q-btn
          :class="{ 'method-btn-active': selectedMethod === 'regional' }"
          class="method-btn"
          @click="selectedMethod = 'regional'"
          size="sm"
          no-caps
          flat
        >
          <div class="method-btn-content">
            <span>{{ t('analysis.panel.methods.regional') }}</span>
            <q-icon name="info" size="xs" class="method-info-icon">
              <q-tooltip>
                {{ t('analysis.panel.methodTooltips.regional') }}
              </q-tooltip>
            </q-icon>
          </div>
        </q-btn>
        <q-btn
          :class="{ 'method-btn-active': selectedMethod === 'draw' }"
          class="method-btn"
          @click="selectedMethod = 'draw'"
          size="sm"
          no-caps
          flat
        >
          <div class="method-btn-content">
            <span>{{ t('analysis.panel.methods.draw') }}</span>
            <q-icon name="info" size="xs" class="method-info-icon">
              <q-tooltip>
                {{ t('analysis.panel.methodTooltips.draw') }}
              </q-tooltip>
            </q-icon>
          </div>
        </q-btn>
        <q-btn
          :class="{ 'method-btn-active': selectedMethod === 'upload' }"
          class="method-btn"
          @click="selectedMethod = 'upload'"
          size="sm"
          no-caps
          flat
        >
          <div class="method-btn-content">
            <span>{{ t('analysis.panel.methods.upload') }}</span>
            <q-icon name="info" size="xs" class="method-info-icon">
              <q-tooltip>
                {{ t('analysis.panel.methodTooltips.upload') }}
              </q-tooltip>
            </q-icon>
          </div>
        </q-btn>
      </div>

      <!-- Area Method Content -->
      <div class="method-content-compact">
        <!-- Regional Analysis -->
        <div v-if="selectedMethod === 'regional'" class="method-panel-compact">
          <q-btn 
            color="primary" 
            :label="t('analysis.panel.regional.calculate')"
            @click="loadRegionalStats"
            :loading="isLoading"
            :disable="!benchmark"
            class="full-width action-btn-compact"
            size="sm"
            :data-umami-event="'calculate_regional_stats'"
            :data-umami-event-benchmark="mapStore.selectedBenchmark"
          >
            <q-tooltip v-if="!benchmark">{{ t('analysis.panel.selectMapFirst') }}</q-tooltip>
          </q-btn>
        </div>

        <!-- Draw Area -->
        <div v-if="selectedMethod === 'draw'" class="method-panel-compact">
          <q-btn 
            v-if="!isDrawing"
            color="primary" 
            :label="t('analysis.panel.draw.start')"
            @click="startDraw"
            :disable="!benchmark"
            class="full-width action-btn-compact"
            size="sm"
            :data-umami-event="'start_aoi_drawing'"
          >
            <q-tooltip v-if="!benchmark">{{ t('analysis.panel.selectMapFirst') }}</q-tooltip>
          </q-btn>
          
          <q-btn 
            v-else
            color="negative" 
            :label="t('analysis.panel.draw.cancel')"
            @click="cancelDrawing"
            class="full-width action-btn-compact"
            outline
            size="sm"
            :data-umami-event="'cancel_aoi_drawing'"
          />
        </div>

        <!-- Upload Area -->
        <div v-if="selectedMethod === 'upload'" class="method-panel-compact">
          <!-- Show upload area only if no file is uploaded -->
          <div v-if="!uploadedFile" class="upload-area-compact" 
               :class="{ 'drag-over': isDragOver }" 
               @dragover.prevent="onDragOver" 
               @dragleave.prevent="onDragLeave" 
               @drop.prevent="onDrop"
               @click="triggerFileUpload"
               :data-umami-event="'trigger_upload_aoi'">
            <q-icon name="cloud_upload" size="md" class="upload-icon-compact" />
            <div class="upload-text-compact">{{ t('analysis.panel.upload.dragDrop') }}</div>
            <div class="supported-formats-compact">{{ t('analysis.panel.upload.supportedFormats') }}</div>
          </div>
          
          <input 
            type="file" 
            ref="fileInput" 
            style="display: none" 
            accept=".geojson,.json,application/geo+json,.zip"
            @change="handleFileUpload" 
          />
          
          <!-- Upload progress -->
          <div v-if="uploadProgress" class="upload-progress-compact">
            <q-linear-progress :value="uploadProgress.percent / 100" color="primary" class="q-mb-xs" />
            <div class="progress-text-compact">{{ uploadProgress.message }}</div>
          </div>
          
          <!-- Uploaded file info -->
          <div v-if="uploadedFile" class="uploaded-file-info-compact">
            <div class="file-info-header-compact">
              <q-icon name="check_circle" color="positive" size="sm" />
              <span class="file-name-compact">{{ uploadedFile.name }}</span>
              <q-btn flat round dense size="xs" icon="close" @click="clearUploadedFile" />
            </div>
            <q-btn 
              color="primary" 
              :label="t('analysis.panel.upload.calculateStats')" 
              @click="calculateForestStats" 
              :loading="isCalculatingStats"
              class="full-width action-btn-compact"
              :disable="!uploadedFile || !benchmark"
              size="sm"
              :data-umami-event="'calculate_forest_stats'"
              :data-umami-event-file="uploadedFile?.name"
              :data-umami-event-benchmark="mapStore.selectedBenchmark"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Results Section -->
    <div v-if="hasResults" class="results-section-compact">

      <div class="section-header-compact">
        <span class="section-title-compact">{{ t('analysis.panel.results.title') }}</span>
      </div>
      
      <!-- Area Info Compact -->
      <div class="area-info-compact">
        <span class="area-name-compact" :class="{ 'regional-stats': isRegionalStats }">
          {{ getAreaDisplayName() }}
        </span>
       
        <q-chip 
          v-if="isRegionalStats" 
          size="xs" 
          color="green" 
          text-color="white"
          class="regional-chip-compact"
        >
          {{ t('analysis.panel.results.regional') }}
        </q-chip>
      </div>

      <!-- Total Area Context -->
      <div class="total-area-context">
        <span class="total-area-text">{{ t('analysis.panel.results.totalArea') }}: {{ analysisResults.totalAreaHa.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</span>
      </div>

      <!-- Statistics Grid -->
      <div class="stats-grid-compact">
        <!-- Forest Cover Stats -->
        <div v-if="analysisResults.forestCover" class="stat-cell forest-cell">
          <div class="stat-icon-compact">
            <q-icon name="forest" size="20px" />
          </div>
          <div class="stat-content-compact">
            <div class="stat-value-compact">{{ (analysisResults.forestCover.pct_forest * 100).toFixed(1) }}%</div>
            <div class="stat-label-compact">{{ t('analysis.panel.results.forestCover') }}</div>
            <div class="stat-detail-compact">{{ analysisResults.forestCover.forest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</div>
          </div>
        </div>

        <!-- Non-Forest Stats -->
        <div v-if="analysisResults.forestCover" class="stat-cell nonforest-cell">
          <div class="stat-icon-compact">
            <q-icon name="landscape" size="20px" />
          </div>
          <div class="stat-content-compact">
            <div class="stat-value-compact">{{ (100 - analysisResults.forestCover.pct_forest * 100).toFixed(1) }}%</div>
            <div class="stat-label-compact">{{ t('analysis.panel.results.nonForest') }}</div>
            <div class="stat-detail-compact">{{ analysisResults.forestCover.nonforest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</div>
          </div>
        </div>

        <!-- Deforestation Alerts Stats -->
        <div v-if="analysisResults.deforestationAlerts" class="stat-cell alert-cell">
          <div class="stat-icon-compact">
            <q-icon name="warning" size="20px" />
          </div>
          <div class="stat-content-compact">
            <div class="stat-value-compact">{{ ((analysisResults.deforestationAlerts.forest_ha / analysisResults.totalAreaHa) * 100).toFixed(3) }}%</div>
            <div class="stat-label-compact">{{ t('analysis.panel.results.deforestationRate') }}</div>
            <div class="stat-detail-compact">{{ analysisResults.deforestationAlerts.forest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha {{ t('analysis.panel.results.alertsDetected') }}</div>
          </div>
        </div>

        <!-- Empty cell for spacing when only 3 stats -->
        <div class="stat-cell empty-cell"></div>
      </div>

      <!-- Missing Data Info (only for forest cover data) -->
      <div v-if="analysisResults.forestCover && analysisResults.forestCover.pct_missing > 0" class="missing-data-compact">
        <q-icon name="info_outline" size="xs" class="missing-icon" />
        <span class="missing-text">{{ (analysisResults.forestCover.pct_missing * 100).toFixed(1) }}% {{ t('analysis.panel.results.noData').toLowerCase() }}</span>
      </div>
    </div>

    <!-- Export / Save Section (only when logged in) -->
    <div class="export-section-compact" v-if="isLoggedIn">
      <div class="section-header-compact">
        <span class="section-title-compact">Export / Save</span>
      </div>

      <div class="export-card-compact">
        <div class="export-row">
          <div class="export-info">
            <div class="export-title">{{ t('analysis.panel.exportSave.titleImagery') }}</div>
            <div class="export-caption">
              {{ t('analysis.panel.exportSave.source', { date: mapStore.selectedBasemapDate || '—' }) }}
            </div>
            <div v-if="!canDownloadImagery" class="export-hint">
              {{ t('analysis.panel.exportSave.hint') }}
            </div>
          </div>
          <div class="export-controls">
            <q-btn
              color="primary"
              class="export-btn"
              no-caps
              size="sm"
              :disable="!canDownloadImagery || isFetchingAssets"
              @click="openAssetsDialog"
            >
              <q-icon name="download" class="q-mr-xs" />
              {{ t('analysis.panel.exportSave.downloadImagery') }}
            </q-btn>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Original Assets Dialog -->
    <q-dialog v-model="showAssetsDialog" maximized="false">
      <q-card class="q-pa-md" style="min-width: 520px; max-width: 720px;" @keyup.esc="showAssetsDialog = false" tabindex="0">
        <div class="row items-center q-mb-sm">
          <div class="col">
            <div class="text-h6">{{ t('analysis.panel.exportDialog.title') }}</div>
            <div class="text-caption text-grey-7">{{ t('analysis.panel.exportDialog.collection', { collection: currentCollectionId }) }}</div>
          </div>
          <div class="col-auto">
            <q-btn dense flat round icon="close" @click="showAssetsDialog = false" />
          </div>
        </div>
        <q-separator />
        <div class="q-my-sm">
          <div class="q-mb-md text-body2">
            <p>{{ t('analysis.panel.exportDialog.description') }}</p>
            <p>
              {{ t('analysis.panel.exportDialog.licenseNotice', { year: (mapStore.selectedBasemapDate || '').slice(0,4) || '20xx' }) }}
              <a :href="licenseUrl" target="_blank" rel="noopener">{{ t('analysis.panel.exportDialog.licenseLinkText') }}</a>.
            </p>
            <q-checkbox v-model="assetsTermsAccepted" color="primary" :label="t('analysis.panel.exportDialog.ack')" />
          </div>
          
          <q-banner v-if="isFetchingAssets" dense class="bg-grey-2">
            <q-spinner size="16px" class="q-mr-sm" /> {{ t('analysis.panel.exportDialog.fetching') }}
          </q-banner>
          <q-banner v-else-if="assetsList.length === 0" dense class="bg-yellow-1 text-grey-9">
            {{ t('analysis.panel.exportDialog.noAssets') }}
          </q-banner>
          <div v-else class="q-mt-sm">
            <q-list bordered separator>
              <q-item v-for="(a, idx) in assetsList" :key="a.filename">
                <q-item-section>
                  <div class="text-body2">{{ idx + 1 }}. {{ a.filename }}</div>
                  <div class="text-caption text-grey-7">{{ a.id }}</div>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    type="a"
                    :href="assetsTermsAccepted ? a.signed_url : null"
                    :disable="!assetsTermsAccepted"
                    target="_blank"
                    rel="noopener"
                    color="primary"
                    dense
                    no-caps
                    :data-umami-event="'download_imagery'"
                    :data-umami-event-filename="a.filename"
                    :data-umami-event-asset-id="a.id"
                    :data-umami-event-collection-id="currentCollectionId"
                    :data-umami-event-date="mapStore.selectedBasemapDate"
                    :data-umami-event-href="a.signed_url"
                  >
                    {{ t('analysis.panel.exportDialog.download') }}
                  </q-btn>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </div>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useAuthStore } from 'src/stores/authStore'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { GeoJSON } from 'ol/format'
import { transformExtent } from 'ol/proj'
import { getArea } from 'ol/sphere'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import { Style, Fill, Stroke } from 'ol/style'
import shp from 'shpjs'
import api from 'src/services/api'
import CompactDatasetSelector from '../sidebar/CompactDatasetSelector.vue'

const mapStore = useMapStore()
const authStore = useAuthStore()
const { t } = useI18n()
const $q = useQuasar()

// State
const selectedMethod = ref('regional')
const isLoading = computed(() => mapStore.isLoading)
const isDrawing = computed(() => mapStore.isDrawingSummaryAOI)
const isMapLoading = computed(() => mapStore.isLoading)

// Unified analysis results structure
const analysisResults = ref({
  forestCover: null,
  deforestationAlerts: null,
  totalAreaHa: 0,
  areaName: '',
  isRegional: false
})

// Get the current benchmark from store
const benchmark = computed(() => mapStore.selectedBenchmark)

// File upload state
const fileInput = ref(null)
const isDragOver = ref(false)
const uploadProgress = ref(null)
const uploadedFile = ref(null)
const isCalculatingStats = ref(false)
const uploadedGeometry = ref(null)

// Computed properties
const isRegionalStats = computed(() => analysisResults.value.isRegional)
const hasResults = computed(() => 
  analysisResults.value.forestCover || analysisResults.value.deforestationAlerts
)

// Export / Save state
const canDownloadImagery = computed(() => {
  // Depend on reactive refs so UI updates when AOI changes
  const hasAnyAOIRef = !!mapStore.aoiLayer || !!mapStore.summaryAOILayer || !!mapStore.aoi
  const hasDate = !!mapStore.selectedBasemapDate
  return hasAnyAOIRef && hasDate
})
const isFetchingAssets = ref(false)
const showAssetsDialog = ref(false)
const assetsList = ref([])
const currentCollectionId = ref('')
const assetsTermsAccepted = ref(false)
const licenseUrl = 'https://university.planet.com/nicfi-resources/1219786'
const isLoggedIn = computed(() => !!authStore.currentUser)

// Planet imagery state
const isPlanetImageryActive = computed(() => {
  if (!mapStore.map) return false
  const planetLayer = mapStore.map.getLayers().getArray().find(layer => 
    layer.get('id') === 'planet-basemap'
  )
  return !!planetLayer
})

// Get visible datasets for statistics calculation
const visibleDatasets = computed(() => {
  const visible = mapStore.layers
    .filter(layer => layer.visible)
    .map(layer => {
      // Map layer ID to dataset info from availableDatasets
      const dataset = mapStore.availableDatasets.find(d => {
        // Handle GFW alerts layers specifically
        if (layer.id.startsWith('gfw-alerts-') && d.type === 'alerts') {
          const layerYear = layer.id.split('-').pop()
          return d.year === layerYear
        }
        
        // Handle other datasets
        return layer.id.includes(d.value) || 
               layer.id === `benchmark-${d.value}`
      })
      
      return dataset
    })
    .filter(Boolean)
    
  return visible
})

const visibleDatasetsByType = computed(() => {
  const visible = visibleDatasets.value
  const byType = {
    forestCover: visible.filter(d => ['prediction', 'benchmark'].includes(d.type)),
    alerts: visible.filter(d => d.type === 'alerts'),
    imagery: visible.filter(d => d.type === 'basemap-imagery')
  }
  
  return byType
})

// Methods
const getAreaIcon = () => {
  if (isRegionalStats.value) return 'public'
  if (uploadedFile.value) return 'upload_file'
  return 'draw'
}

const getAreaDisplayName = () => {
  if (isRegionalStats.value) return t('analysis.panel.results.allWesternEcuador')
  if (analysisResults.value.areaName) return analysisResults.value.areaName
  return t('analysis.panel.results.customArea')
}

// Unified function to calculate area statistics for both forest cover and deforestation alerts
async function calculateAreaStatistics(geometry = null, areaName = null, isRegional = false) {
  console.log(`calculateAreaStatistics called:`, { geometry: !!geometry, areaName, isRegional })
  
  // Show loading notification
  const loadingNotification = $q.notify({
    type: 'ongoing',
    message: 'Calculating area statistics...',
    timeout: 0, // Don't auto-dismiss
    spinner: true,
    position: 'bottom'
  });
  
  try {
    mapStore.isLoading = true
    
    // Get datasets
    const forestDataset = visibleDatasetsByType.value.forestCover[0]
    const alertsDataset = visibleDatasetsByType.value.alerts[0]
    
    console.log('Available datasets:', { 
      forestDataset: forestDataset?.value, 
      alertsDataset: alertsDataset?.value 
    })
    
    // Build promises for both dataset types
    const promises = []
    
    if (forestDataset) {
      console.log(`Adding forest dataset promise (${isRegional ? 'regional' : 'AOI'})`)
      const promise = isRegional 
        ? api.getWesternEcuadorStats(forestDataset.value)
        : api.getAOISummary(geometry, forestDataset.value)
      promises.push(promise.then(response => ({ type: 'forestCover', data: response.data })))
    } else {
      console.log('No forest dataset available')
    }
    
    if (alertsDataset) {
      console.log(`Adding alerts dataset promise (${isRegional ? 'regional' : 'AOI'})`)
      const promise = isRegional 
        ? api.getWesternEcuadorStats(alertsDataset.value)
        : api.getAOISummary(geometry, alertsDataset.value)
      promises.push(promise.then(response => ({ type: 'alerts', data: response.data })))
    } else {
      console.log('No alerts dataset available')
    }
    
    console.log(`Executing ${promises.length} API calls in parallel`)
    
    // Execute all promises in parallel
    const results = await Promise.all(promises)
    
    console.log('API results:', results)
    
    // Process results and update unified structure
    const forestResult = results.find(r => r.type === 'forestCover')
    const alertsResult = results.find(r => r.type === 'alerts')
    
    const newResults = {
      forestCover: forestResult ? forestResult.data : null,
      deforestationAlerts: alertsResult ? alertsResult.data : null,
      totalAreaHa: forestResult ? (forestResult.data.total_analyzed_ha || (forestResult.data.forest_ha + forestResult.data.nonforest_ha)) : 0,
      areaName: areaName || (isRegional ? 'Western Ecuador' : 'Custom Area'),
      isRegional: isRegional
    }
    
    console.log('Setting analysisResults to:', newResults)
    analysisResults.value = newResults
    
    // Dismiss loading notification
    loadingNotification();
    
    // Only show success notification if we actually got results
    const hasActualResults = newResults.forestCover || newResults.deforestationAlerts
    if (hasActualResults) {
      $q.notify({
        type: 'positive',
        message: 'Area statistics calculated successfully',
        timeout: 2000,
        position: 'bottom'
      });
    }
    
  } catch (error) {
    console.error('Failed to calculate area statistics:', error)
    
    // Dismiss loading notification
    loadingNotification();
    
    // Show more detailed error message for connectivity issues
    const errorMessage = error.message?.includes('fetch') || error.message?.includes('Network') 
      ? 'Unable to connect to database. Please check your connection and try again.'
      : 'Failed to calculate area statistics. Please try again.';
      
    $q.notify({
      type: 'negative',
      message: errorMessage,
      timeout: 5000,
      position: 'bottom'
    })
  } finally {
    mapStore.isLoading = false
  }
}

// Auto-refresh stats when benchmark changes
watch(benchmark, async (newBenchmark, oldBenchmark) => {
  if (newBenchmark && newBenchmark !== oldBenchmark) {
    console.log('Benchmark changed from', oldBenchmark, 'to', newBenchmark)
    
    // Automatically load western Ecuador stats for the new benchmark
    if (!mapStore.summaryAOILayer && selectedMethod.value === 'regional') {
      console.log('Auto-loading regional stats due to benchmark change')
      await calculateAreaStatistics(null, 'Western Ecuador', true)
    }
    
    // Auto-refresh stats if user has drawn a rectangle
    if (mapStore.summaryAOILayer) {
      console.log('Refreshing AOI stats for new benchmark')
      await refreshAOIStats()
    }
  }
})


// Function to refresh AOI stats for current geometry
async function refreshAOIStats() {
  console.log('refreshAOIStats called')
  console.log('mapStore.summaryAOILayer:', mapStore.summaryAOILayer)
  
  if (!mapStore.summaryAOILayer) {
    console.log('No summaryAOILayer found')
    return
  }
  
  const features = mapStore.summaryAOILayer.getSource().getFeatures()
  console.log('Found features:', features.length)
  
  if (features.length === 0) {
    console.log('No features in summaryAOILayer')
    return
  }
  
  const geometry = features[0].getGeometry()
  console.log('Geometry:', geometry)
  
  const geoJSONGeom = new GeoJSON().writeGeometryObject(geometry, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  })
  
  console.log('Converted to GeoJSON:', geoJSONGeom)
  
  const geoJSONFeature = { type: 'Feature', geometry: geoJSONGeom }
  
  console.log('Calling calculateAreaStatistics with:', geoJSONFeature)
  await calculateAreaStatistics(geoJSONFeature, 'Custom Area', false)
}

// Watch for changes in layer visibility to auto-refresh stats
watch(visibleDatasetsByType, async (newValue, oldValue) => {
  console.log('visibleDatasetsByType changed:', { newValue, oldValue })
  
  // Auto-load regional stats when datasets first become available
  if (!hasResults.value && !mapStore.summaryAOILayer && benchmark.value && 
      (newValue.forestCover.length > 0 || newValue.alerts.length > 0) &&
      (oldValue.forestCover.length === 0 && oldValue.alerts.length === 0)) {
    console.log('✓ Datasets became available - auto-loading regional statistics')
    await calculateAreaStatistics(null, 'Western Ecuador', true)
    return
  }
  
  // Only refresh if we have existing results and the visible datasets changed
  if (hasResults.value && JSON.stringify(newValue) !== JSON.stringify(oldValue)) {
    console.log('Refreshing existing results due to dataset visibility change')
    if (!mapStore.summaryAOILayer && selectedMethod.value === 'regional') {
      await calculateAreaStatistics(null, 'Western Ecuador', true)
    } else if (mapStore.summaryAOILayer) {
      await refreshAOIStats()
    }
  }
}, { deep: true })

// Regional analysis methods
async function loadRegionalStats() {
  console.log('loadRegionalStats button clicked')
  try {
    window.umami?.track?.('calculate_regional_stats', {
      benchmark: mapStore.selectedBenchmark,
      area: 'Western Ecuador'
    })
  } catch (e) { /* no-op */ }
  await calculateAreaStatistics(null, 'Western Ecuador', true)
  selectedMethod.value = 'regional'
}

// Drawing methods
function startDraw() {
  console.log("Starting AOI drawing")
  try {
    window.umami?.track?.('start_aoi_drawing', {
      benchmark: mapStore.selectedBenchmark
    })
  } catch (e) { /* no-op */ }
  mapStore.startSummaryAOIDraw()
  selectedMethod.value = 'draw'
}

function cancelDrawing() {
  console.log("Canceling AOI drawing")
  try {
    window.umami?.track?.('cancel_aoi_drawing', {
      benchmark: mapStore.selectedBenchmark
    })
  } catch (e) { /* no-op */ }
  mapStore.clearSummaryAOI()
 // loadRegionalStats()
}

// Planet imagery methods
function togglePlanetImagery() {
  if (isPlanetImageryActive.value) {
    removePlanetImagery()
  } else {
    addPlanetImagery()
  }
}

function addPlanetImagery() {
  console.log("Adding Planet imagery")
  try {
    window.umami?.track?.('toggle_planet_imagery', {
      action: 'add',
      date: mapStore.selectedBasemapDate
    })
  } catch (e) { /* no-op */ }
  mapStore.addPlanetImageryLayer()
  $q.notify({
    type: 'positive',
    message: t('analysis.panel.planetImagery.add'),
    timeout: 2000,
    position: 'bottom'
  })
}

function removePlanetImagery() {
  console.log("Removing Planet imagery")
  if (!mapStore.map) return
  
  const layers = mapStore.map.getLayers().getArray()
  const planetLayer = layers.find(layer => layer.get('id') === 'planet-basemap')
  if (planetLayer) {
    mapStore.map.removeLayer(planetLayer)
    try {
      window.umami?.track?.('toggle_planet_imagery', {
        action: 'remove',
        date: mapStore.selectedBasemapDate
      })
    } catch (e) { /* no-op */ }
    $q.notify({
      type: 'info',
      message: t('analysis.panel.planetImagery.remove'),
      timeout: 2000,
      position: 'bottom'
    })
  }
}

function clearAndReset() {
  mapStore.clearSummaryAOI()
  clearUploadedFile()
  analysisResults.value = {
    forestCover: null,
    deforestationAlerts: null,
    totalAreaHa: 0,
    areaName: '',
    isRegional: false
  }
  selectedMethod.value = 'regional'
}

// File upload methods
const triggerFileUpload = () => {
  fileInput.value.click()
}

const onDragOver = (e) => {
  e.preventDefault()
  isDragOver.value = true
}

const onDragLeave = (e) => {
  e.preventDefault()
  isDragOver.value = false
}

const onDrop = (e) => {
  e.preventDefault()
  isDragOver.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    try {
      window.umami?.track?.('upload_aoi_file_selected', {
        name: file.name,
        size: file.size,
        type: file.type
      })
    } catch (e) { /* no-op */ }
    processFile(file)
  }
  event.target.value = ''
}

const processFile = async (file) => {
  uploadProgress.value = { percent: 0, message: t('analysis.panel.upload.reading') }
  
  try {
    let geojson
    
    if (file.name.toLowerCase().endsWith('.geojson') || file.name.toLowerCase().endsWith('.json')) {
      geojson = await handleGeoJSON(file)
    } else if (file.name.toLowerCase().endsWith('.zip')) {
      geojson = await handleShapefile(file)
    } else {
      throw new Error(t('analysis.panel.upload.unsupportedFormat'))
    }
    
    uploadProgress.value = { percent: 50, message: t('analysis.panel.upload.processing') }
    
    // Process and validate the geometry
    await processGeometry(geojson, file.name)
    
    uploadProgress.value = { percent: 100, message: t('analysis.panel.upload.complete') }
    
    // Clear progress after short delay
    setTimeout(() => {
      uploadProgress.value = null
    }, 1000)
    
  } catch (error) {
    console.error('File upload error:', error)
    try {
      window.umami?.track?.('upload_aoi_error', {
        name: file?.name,
        message: error?.message
      })
    } catch (e) { /* no-op */ }
    uploadProgress.value = null
    $q.notify({
      type: 'negative',
      message: error.message || t('analysis.panel.upload.error'),
      timeout: 4000
    })
  }
}

const handleGeoJSON = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const geojson = JSON.parse(e.target.result)
        resolve(geojson)
      } catch (error) {
        reject(new Error(t('analysis.panel.upload.invalidGeoJSON')))
      }
    }
    reader.onerror = () => reject(new Error(t('analysis.panel.upload.readError')))
    reader.readAsText(file)
  })
}

const handleShapefile = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const geojson = await shp(arrayBuffer)
    return geojson
  } catch (error) {
    throw new Error(t('analysis.panel.upload.invalidShapefile'))
  }
}

const processGeometry = async (geojson, fileName) => {
  // Ensure we have a FeatureCollection
  if (geojson.type === 'Feature') {
    geojson = {
      type: 'FeatureCollection',
      features: [geojson]
    }
  }
  
  if (!geojson.features || geojson.features.length === 0) {
    throw new Error(t('analysis.panel.upload.noFeatures'))
  }
  
  // Read features with OpenLayers
  const format = new GeoJSON()
  const features = format.readFeatures(geojson, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857'
  })
  
  if (features.length === 0) {
    throw new Error(t('analysis.panel.upload.noValidFeatures'))
  }
  
  // Calculate total area and feature count
  let totalArea = 0
  features.forEach(feature => {
    const geometry = feature.getGeometry()
    if (geometry) {
      totalArea += getArea(geometry) / 10000 // Convert to hectares
    }
  })
  
  // Store the processed geometry for later use
  uploadedGeometry.value = geojson
  
  // Update uploaded file info
  uploadedFile.value = {
    name: fileName,
    featureCount: features.length,
    totalArea: totalArea,
    features: features
  }
  
  // Display features on map
  displayUploadedFeatures(features)

  // Also set AOI layer in mapStore for export/download workflows
  try {
    const firstFeature = features[0]
    if (firstFeature) {
      const aoiFeature3857 = new GeoJSON().writeFeatureObject(firstFeature, {
        dataProjection: 'EPSG:3857',
        featureProjection: 'EPSG:3857'
      })
      mapStore.displayAOI(aoiFeature3857)
      if (features.length > 1) {
        $q.notify({
          type: 'info',
          message: 'Multiple features detected; using the first feature as AOI for export.',
          timeout: 3000
        })
      }
    }
  } catch (e) {
    console.warn('Failed to set AOI layer from uploaded features', e)
  }
  
  // Zoom to extent
  if (features.length > 0) {
    let extent = features[0].getGeometry().getExtent().slice()
    
    features.forEach(feature => {
      const featureExtent = feature.getGeometry().getExtent()
      extent[0] = Math.min(extent[0], featureExtent[0])
      extent[1] = Math.min(extent[1], featureExtent[1])
      extent[2] = Math.max(extent[2], featureExtent[2])
      extent[3] = Math.max(extent[3], featureExtent[3])
    })
    
    mapStore.map.getView().fit(extent, { padding: [50, 50, 50, 50] })
  }
  
  $q.notify({
    type: 'positive',
    message: t('analysis.panel.upload.success', { count: features.length }),
    timeout: 3000
  })
  
  selectedMethod.value = 'upload'
}

const displayUploadedFeatures = (features) => {
  // Remove any existing uploaded features layer
  clearUploadedFeatures()
  
  // Create vector source with the already projected features
  const vectorSource = new VectorSource({
    features: features
  })
  
  // Create style for uploaded features
  const style = new Style({
    fill: new Fill({
      color: 'rgba(33, 150, 243, 0.0)'  // Transparent fill
    }),
    stroke: new Stroke({
      color: '#2196F3',
      width: 2
    })
  })
  
  // Create vector layer
  const vectorLayer = new VectorLayer({
    source: vectorSource,
    style: style,
    title: 'Uploaded Features',
    id: 'uploaded-features',
    zIndex: 10
  })
  
  // Add layer directly to map
  mapStore.map.addLayer(vectorLayer)
  
  console.log('Added uploaded features layer with', features.length, 'features')
}

const clearUploadedFeatures = () => {
  // Remove uploaded features layer if it exists
  if (mapStore.map) {
    const layers = mapStore.map.getLayers().getArray()
    const uploadedLayer = layers.find(layer => layer.get('id') === 'uploaded-features')
    if (uploadedLayer) {
      mapStore.map.removeLayer(uploadedLayer)
      console.log('Removed uploaded features layer')
    }
  }
}

const clearUploadedFile = () => {
  uploadedFile.value = null
  uploadedGeometry.value = null
  clearUploadedFeatures()
}

const calculateForestStats = async () => {
  if (!uploadedGeometry.value) return
 
 
  try {
    // Convert FeatureCollection to a single Feature for the API
    let geometryToSend = uploadedGeometry.value
    
    if (geometryToSend.type === 'FeatureCollection') {
      if (geometryToSend.features.length === 1) {
        geometryToSend = geometryToSend.features[0]
      } else {
        geometryToSend = geometryToSend.features[0]
        
        $q.notify({
          type: 'warning',
          message: t('analysis.panel.upload.multipleFeatures'),
          timeout: 4000
        })
      }
    }
    
    // Ensure we have a proper Feature object with geometry property
    if (!geometryToSend.geometry) {
      throw new Error('Invalid geometry format')
    }
    
    // Use the unified calculation function
    await calculateAreaStatistics(geometryToSend, uploadedFile.value.name, false)
    
  } catch (error) {
    console.error('Error calculating forest stats:', error)
    
    // Show more detailed error message for connectivity issues
    const errorMessage = error.message?.includes('fetch') || error.message?.includes('Network') 
      ? 'Unable to connect to database. Please check your connection and try again.'
      : error.message || t('analysis.panel.upload.statsError');
      
    $q.notify({
      type: 'negative',
      message: errorMessage,
      timeout: 5000,
      position: 'bottom'
    })
  } finally {
    isCalculatingStats.value = false
  }
}

// Set up callback for when AOI stats are calculated
window.aoiStatsCallback = async () => {
  await refreshAOIStats()
}

// Export handlers
function getActiveAOIBbox4326() {
  const gj = mapStore.getActiveAOIGeometry4326()
  if (!gj) return null
  const format = new GeoJSON()
  const feat = format.readFeature(gj, { dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857' })
  const extent3857 = feat.getGeometry().getExtent()
  const extent4326 = transformExtent(extent3857, 'EPSG:3857', 'EPSG:4326')
  return [extent4326[0], extent4326[1], extent4326[2], extent4326[3]]
}

async function openAssetsDialog() {
  if (!canDownloadImagery.value) return
  const bbox = getActiveAOIBbox4326()
  if (!bbox) {
    $q.notify({ type: 'warning', message: 'No AOI found.', timeout: 2500 })
    return
  }
  try {
    assetsTermsAccepted.value = false
    isFetchingAssets.value = true
    currentCollectionId.value = `nicfi-${mapStore.selectedBasemapDate}`
    const resp = await api.getSignedAssets(currentCollectionId.value, bbox)
    assetsList.value = resp.data.assets || []
    showAssetsDialog.value = true
  } catch (e) {
    console.error('Failed to fetch signed assets:', e)
    $q.notify({ type: 'negative', message: 'Failed to fetch signed asset links', timeout: 4000 })
  } finally {
    isFetchingAssets.value = false
  }
}

// Automatically load western Ecuador stats when component mounts (if datasets are already available)
onMounted(async () => {
  // console.log('AnalysisPanel onMounted - checking conditions for auto-load')
  // console.log('- mapStore.summaryAOILayer:', mapStore.summaryAOILayer)
  // console.log('- benchmark.value:', benchmark.value)
  // console.log('- hasResults.value:', hasResults.value)
  // console.log('- visibleDatasetsByType.value:', JSON.stringify(visibleDatasetsByType.value))
  
  // Only load if no custom area has been drawn, we have a selected benchmark, and datasets are available
  if (!mapStore.summaryAOILayer && benchmark.value && 
      (visibleDatasetsByType.value.forestCover.length > 0 || visibleDatasetsByType.value.alerts.length > 0)) {
    // console.log('✓ Conditions met - auto-loading regional statistics on mount')
    await calculateAreaStatistics(null, 'Western Ecuador', true)
  } else {
    // console.log('✗ Conditions not met for auto-loading on mount (will retry when datasets load)')
    // if (mapStore.summaryAOILayer) // console.log('  - Reason: Custom AOI layer exists')
    // if (!benchmark.value) // console.log('  - Reason: No benchmark selected')
    // if (visibleDatasetsByType.value.forestCover.length === 0 && visibleDatasetsByType.value.alerts.length === 0) {
    //   console.log('  - Reason: No datasets available yet (watcher will handle when they load)')
    // }
  }
})
</script>

<style scoped>
.analysis-panel {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

/* Compact Section Headers */
.section-header-compact {
  padding: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.section-title-compact {
  font-size: 14px !important;
  font-weight: 600;
  color: #2e7d32;
}

/* Benchmark Section Compact */
.benchmark-section {
  margin-bottom: 8px;
}

.benchmark-selector-container {
  margin: 8px 0;
}

/* Area Selection Compact */
.area-selection-section {
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.method-buttons-row {
  display: flex;
  gap: 4px;
  margin: 8px 2px;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 4px;
}

.method-btn {
  flex: 1;
  font-size: 12px !important;
  font-weight: 500;
  border-radius: 4px;
  transition: all 0.2s ease;
  min-width: 0;
}

.method-btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: px;
  white-space: nowrap;
  overflow: hidden;
  width: 100%;
}

.method-btn-content span {
  flex-shrink: 0;
}

.method-btn-active {
  background: white !important;
  color: #2e7d32 !important;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.method-info-icon {
  opacity: 0.6;
  cursor: help;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
  margin: 0 4px;
}

.method-info-icon:hover {
  opacity: 1;
}

.method-content-compact {
  background: white;
  margin: 0 12px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.method-panel-compact {
  padding: 8px !important;
}

.action-btn-compact {
  text-transform: none;
  font-weight: 500;
  border-radius: 6px;
  height: 32px;
  font-size: 13px !important;
}

/* Export / Save Section */
.export-section-compact {
  border-top: 1px solid #f0f0f0;
  margin-top: 8px;
}

.export-card-compact {
  background: white;
  margin: 8px 12px 12px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  padding: 8px;
}

.export-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.export-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.export-title {
  font-weight: 600;
  font-size: 13px;
  color: #2e7d32;
}

.export-caption {
  font-size: 12px;
  color: #666;
}

.export-hint {
  font-size: 11px;
  color: #9e9e9e;
}

.export-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-format-select {
  min-width: 140px;
}

.export-btn {
  text-transform: none;
}

/* Upload Compact Styles */
.upload-area-compact {
  border: 2px dashed #e0e7e4;
  border-radius: 6px;
  padding: 12px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fafcfa;
  margin-bottom: 8px;
}

.upload-area-compact:hover {
  border-color: #4caf50;
  background: #f1f8e9;
}

.upload-area-compact.drag-over {
  border-color: #4caf50;
  background: #e8f5e8;
  border-style: solid;
}

.upload-icon-compact {
  color: #81c784;
  margin-bottom: 4px;
}

.upload-text-compact {
  font-size: 13px;
  font-weight: 500;
  color: #2e7d32;
  margin-bottom: 2px;
}

.supported-formats-compact {
  font-size: 11px;
  color: #9e9e9e;
  font-style: italic;
}

.upload-progress-compact {
  margin-bottom: 8px;
}

.progress-text-compact {
  font-size: 11px;
  color: #666;
  text-align: center;
  margin-top: 2px;
}

.uploaded-file-info-compact {
  background: #f1f8e9;
  border: 1px solid #c8e6c9;
  border-radius: 6px;
  padding: 8px;
  margin-top: 8px;
}

.file-info-header-compact {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
}

.file-name-compact {
  flex: 1;
  font-weight: 500;
  color: #2e7d32;
  font-size: 11px;
  word-break: break-word;
  line-height: 1.2;
}

/* Results Compact Styles */
.results-section-compact {
  animation: fadeIn 0.3s ease-in;
  background: #f8f9fa;
  border-radius: 8px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}


.area-info-compact {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #666;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #e0e0e0;
}

.area-name-compact {
  font-weight: 500;
  flex: 1;
}

.area-name-compact.regional-stats {
  color: #2e7d32;
  font-weight: 600;
}

.area-info-compact:has(.regional-stats) {
  background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
  border-left-color: #4caf50;
}

.regional-chip-compact {
  margin-left: auto;
}

.total-area-context {
  text-align: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(117, 117, 117, 0.1);
  border-radius: 6px;
  border: 1px solid rgba(117, 117, 117, 0.2);
}

.total-area-text {
  font-size: 12px;
  font-weight: 500;
  color: #424242;
}

.stats-grid-compact {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}

.stat-cell {
  padding: 12px 8px;
  border-radius: 6px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-height: 70px;
}

.stat-cell:hover:not(.empty-cell) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.empty-cell {
  background: transparent;
  border: none;
  min-height: 0;
}

.forest-cell {
  background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
  border: 1px solid #c8e6c9;
}

.nonforest-cell {
  background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%);
  border: 1px solid #ffccbc;
}

.alert-cell {
  background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
  border: 1px solid #f8bbd9;
}

.stat-icon-compact {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.8);
}

.forest-cell .stat-icon-compact {
  color: #2e7d32;
}

.nonforest-cell .stat-icon-compact {
  color: #f57c00;
}

.alert-cell .stat-icon-compact {
  color: #d32f2f;
}

.stat-content-compact {
  flex: 1;
  text-align: left;
}

.stat-value-compact {
  font-size: 16px !important;
  font-weight: 700;
  color: #212121;
  line-height: 1.2;
  margin-bottom: 2px;
}

.stat-label-compact {
  font-size: 12px !important;
  font-weight: 600;
  color: #424242;
  margin-bottom: 2px;
}

.stat-detail-compact {
  font-size: 12px !important;
  color: #757575;
  font-weight: 500;
  line-height: 1.2;
}

.missing-data-compact {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  background: rgba(156, 39, 176, 0.1);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid rgba(156, 39, 176, 0.2);
}

.missing-icon {
  color: #7b1fa2;
}

.missing-text {
  flex: 1;
}

/* Subsection Styles */
.subsection-compact {
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.subsection-compact:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.subsection-header-compact {
  padding: 6px 8px;
  background: #f8f9fa;
  display: flex;
  align-items: center;
  gap: 6px;
}

.subsection-title-compact {
  font-size: 12px !important;
  font-weight: 600;
  color: #424242;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex: 1;
}

.subsection-info-icon {
  opacity: 0.6;
  cursor: help;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
  color: #424242;
}

.subsection-info-icon:hover {
  opacity: 1;
}

/* Planet Control Styles */
.planet-control-container {
  margin: 8px 0;
}

.planet-btn {
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  transition: all 0.3s ease;
  font-weight: 500;
  text-transform: none;
  height: 38px;
  padding: 6px 12px;
}

.planet-btn:hover {
  border-color: #2196f3;
  background: #f3f8ff;
  transform: translateY(-1px);
}

.planet-btn-active {
  background: linear-gradient(135deg, #e8f4fd 0%, #f3f8ff 100%);
  border-color: #2196f3;
  color: #1976d2;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
}

.planet-btn-active:hover {
  background: linear-gradient(135deg, #e1f0fc 0%, #edf4ff 100%);
  border-color: #1976d2;
}

.planet-btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
}

.planet-icon {
  color: #2196f3;
  transition: all 0.3s ease;
}

.planet-btn-active .planet-icon {
  color: #1976d2;
}

.planet-text {
  font-size: 13px;
  font-weight: 500;
  color: #424242;
  transition: all 0.3s ease;
}

.planet-btn-active .planet-text {
  color: #1976d2;
  font-weight: 600;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .benchmark-select, .method-content-compact, .method-buttons-row {
    margin: 0 8px;
  }
  
  .results-section-compact {
    margin: 8px 8px;
    padding: 6px;
  }
  
  .stats-grid-compact {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  
  .stat-cell {
    padding: 10px 6px;
    min-height: 60px;
  }
  
  .stat-value-compact {
    font-size: 14px;
  }
  
  .stat-label-compact {
    font-size: 10px;
  }
  
  .stat-detail-compact {
    font-size: 9px;
  }
  
  .stat-icon-compact {
    width: 28px;
    height: 28px;
  }
  
  .total-area-text {
    font-size: 12px !important;
  }

  .planet-btn {
    height: 34px;
  }
  
  .planet-text {
    font-size: 12px;
  }
  
  .subsection-title-compact {
    font-size: 11px !important;
  }
}
</style>
