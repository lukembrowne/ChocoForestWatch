<template>
  <div class="analysis-panel">
    <!-- Map Selection Section -->
    <div class="benchmark-section">
      <div class="section-header-compact">
        <span class="section-title-compact">{{ t('analysis.panel.chooseMap') }}</span>
      </div>
      
      <q-select
        outlined
        v-model="benchmark"
        :options="benchmarkOptions"
        option-label="label"
        option-value="value"
        emit-value
        map-options
        :disable="isMapLoading"
        class="benchmark-select"
        :placeholder="t('analysis.panel.selectMapPlaceholder')"
        dense
      >
        <template v-slot:prepend>
          <q-icon name="layers" color="primary" size="sm" />
        </template>
        <template v-slot:append v-if="isMapLoading">
          <q-spinner color="primary" size="sm" />
        </template>
      </q-select>
    </div>

    <!-- Area Selection Section -->
    <div class="area-selection-section">
      <div class="section-header-compact">
        <span class="section-title-compact">{{ t('analysis.panel.defineArea') }}</span>
      </div>

      <!-- Area Method Tabs -->
      <q-tabs
        v-model="selectedMethod"
        class="method-tabs-compact"
        indicator-color="primary"
        active-color="primary"
        align="justify"
        dense
        no-caps
      >
        <q-tab name="regional" :label="t('analysis.panel.methods.regional')" />
        <q-tab name="draw" :label="t('analysis.panel.methods.draw')" />
        <q-tab name="upload" :label="t('analysis.panel.methods.upload')" />
      </q-tabs>

      <!-- Area Method Content -->
      <q-tab-panels v-model="selectedMethod" animated class="method-panels-compact">
        <!-- Regional Analysis -->
        <q-tab-panel name="regional" class="method-panel-compact">
          <q-btn 
            color="primary" 
            :label="t('analysis.panel.regional.calculate')"
            @click="loadRegionalStats"
            :loading="isLoading"
            :disable="!benchmark"
            class="full-width action-btn-compact"
            size="sm"
          >
            <q-tooltip v-if="!benchmark">{{ t('analysis.panel.selectMapFirst') }}</q-tooltip>
          </q-btn>
        </q-tab-panel>

        <!-- Draw Area -->
        <q-tab-panel name="draw" class="method-panel-compact">
          <q-btn 
            v-if="!isDrawing"
            color="primary" 
            :label="t('analysis.panel.draw.start')"
            @click="startDraw"
            :disable="!benchmark"
            class="full-width action-btn-compact"
            size="sm"
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
          />
        </q-tab-panel>

        <!-- Upload Area -->
        <q-tab-panel name="upload" class="method-panel-compact">
          <div class="upload-area-compact" 
               :class="{ 'drag-over': isDragOver }" 
               @dragover.prevent="onDragOver" 
               @dragleave.prevent="onDragLeave" 
               @drop.prevent="onDrop"
               @click="triggerFileUpload">
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
            />
          </div>
        </q-tab-panel>
      </q-tab-panels>
    </div>

    <!-- Results Section -->
    <div v-if="stats" class="results-section-compact">
      <div class="results-header-compact">
        <span class="results-title-compact">{{ t('analysis.panel.results.title') }}</span>
        <q-btn 
          flat
          round
          dense
          size="xs"
          icon="refresh" 
          color="primary" 
          @click="clearAndReset"
          class="refresh-btn"
        >
          <q-tooltip>{{ t('analysis.panel.results.analyzeNew') }}</q-tooltip>
        </q-btn>
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

      <!-- Statistics Grid -->
      <div class="stats-grid">
        <div class="stat-card forest-card">
          <div class="stat-icon">
            <q-icon name="forest" size="24px" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ (stats.pct_forest * 100).toFixed(1) }}%</div>
            <div class="stat-label">{{ t('analysis.panel.results.forestCover') }}</div>
            <div class="stat-detail">{{ stats.forest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</div>
          </div>
        </div>

        <div class="stat-card nonforest-card">
          <div class="stat-icon">
            <q-icon name="landscape" size="24px" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ (100 - stats.pct_forest * 100).toFixed(1) }}%</div>
            <div class="stat-label">{{ t('analysis.panel.results.nonForest') }}</div>
            <div class="stat-detail">{{ stats.nonforest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</div>
          </div>
        </div>
      </div>

      <!-- Missing Data Info -->
      <div v-if="stats.pct_missing > 0" class="missing-data-compact">
        <q-icon name="info_outline" size="xs" class="missing-icon" />
        <span class="missing-text">{{ (stats.pct_missing * 100).toFixed(1) }}% {{ t('analysis.panel.results.noData').toLowerCase() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { GeoJSON } from 'ol/format'
import { getArea } from 'ol/sphere'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import { Style, Fill, Stroke } from 'ol/style'
import shp from 'shpjs'
import api from 'src/services/api'

const mapStore = useMapStore()
const { t } = useI18n()
const $q = useQuasar()

// State
const selectedMethod = ref('regional')
const stats = computed(() => mapStore.summaryStats)
const isLoading = computed(() => mapStore.isLoading)
const isDrawing = computed(() => mapStore.isDrawingSummaryAOI)
const isMapLoading = computed(() => mapStore.isLoading)

// Benchmark selection
const benchmarkOptions = computed(() => mapStore.availableBenchmarks)
const benchmark = computed({
  get: () => mapStore.selectedBenchmark,
  set: (val) => mapStore.selectedBenchmark = val,
})

// File upload state
const fileInput = ref(null)
const isDragOver = ref(false)
const uploadProgress = ref(null)
const uploadedFile = ref(null)
const isCalculatingStats = ref(false)
const uploadedGeometry = ref(null)

// Computed properties
const isRegionalStats = computed(() => stats.value?.area_name === 'Western Ecuador')

// Methods
const getAreaIcon = () => {
  if (isRegionalStats.value) return 'public'
  if (uploadedFile.value) return 'upload_file'
  return 'draw'
}

const getAreaDisplayName = () => {
  if (isRegionalStats.value) return t('analysis.panel.results.allWesternEcuador')
  if (stats.value?.area_name) return stats.value.area_name
  return t('analysis.panel.results.customArea')
}

// Auto-refresh stats and load forest cover map when benchmark changes
watch(benchmark, async (newBenchmark, oldBenchmark) => {
  if (newBenchmark && newBenchmark !== oldBenchmark) {
    mapStore.addBenchmarkLayer(newBenchmark)
    
    // Automatically load western Ecuador stats for the new benchmark
    if (!mapStore.summaryAOILayer && selectedMethod.value === 'regional') {
      await mapStore.loadWesternEcuadorStats()
    }
  }
  
  // Auto-refresh stats if user has drawn a rectangle
  if (stats.value && mapStore.summaryAOILayer) {
    await mapStore.startSummaryAOIDraw()
  }
})

// Regional analysis methods
async function loadRegionalStats() {
  await mapStore.loadWesternEcuadorStats()
  selectedMethod.value = 'regional'
}

// Drawing methods
function startDraw() {
  mapStore.startSummaryAOIDraw()
  selectedMethod.value = 'draw'
}

function cancelDrawing() {
  mapStore.clearSummaryAOI()
  loadRegionalStats()
}

function clearAndReset() {
  mapStore.clearSummaryAOI()
  clearUploadedFile()
  selectedMethod.value = 'regional'
  loadRegionalStats()
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
      color: 'rgba(33, 150, 243, 0.2)'
    }),
    stroke: new Stroke({
      color: '#2196F3',
      width: 3
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
  
  isCalculatingStats.value = true
  
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
    
    // Use the same API endpoint as the drawing tool
    const response = await api.getAOISummary(
      geometryToSend, 
      mapStore.selectedBenchmark
    )
    
    // Add the file name to the response for display
    const statsWithName = {
      ...response.data,
      area_name: uploadedFile.value.name
    }
    
    // Update the summary stats in the mapStore so results show
    mapStore.summaryStats = statsWithName
    
    $q.notify({
      type: 'positive',
      message: t('analysis.panel.upload.statsCalculated'),
      timeout: 3000
    })
    
  } catch (error) {
    console.error('Error calculating forest stats:', error)
    $q.notify({
      type: 'negative',
      message: error.message || t('analysis.panel.upload.statsError'),
      timeout: 4000
    })
  } finally {
    isCalculatingStats.value = false
  }
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
.analysis-panel {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

/* Compact Section Headers */
.section-header-compact {
  padding: 8px 12px 4px;
  border-bottom: 1px solid #f0f0f0;
}

.section-title-compact {
  font-size: 13px;
  font-weight: 600;
  color: #2e7d32;
}

/* Benchmark Section Compact */
.benchmark-section {
  margin-bottom: 8px;
}

.benchmark-select {
  margin: 8px 12px 0;
  border-radius: 6px;
}

.benchmark-select :deep(.q-field__control) {
  border-radius: 6px;
  transition: all 0.2s ease;
  font-size: 13px;
}

.benchmark-select :deep(.q-field--focused .q-field__control) {
  box-shadow: 0 1px 4px rgba(76, 175, 80, 0.15);
}

/* Area Selection Compact */
.area-selection-section {
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.method-tabs-compact {
  background: #f8f9fa;
  margin: 0 12px;
  border-radius: 6px 6px 0 0;
  min-height: 32px;
}

.method-tabs-compact :deep(.q-tab) {
  font-size: 13px;
  font-weight: 500;
  min-height: 36px;
  padding: 6px 12px;
}

.method-panels-compact {
  background: white;
  margin: 0 12px;
  border-radius: 0 0 6px 6px;
  border: 1px solid #e0e0e0;
  border-top: none;
}

.method-panel-compact {
  padding: 8px !important;
}

.action-btn-compact {
  text-transform: none;
  font-weight: 500;
  border-radius: 6px;
  height: 32px;
  font-size: 13px;
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
  margin: 12px;
  padding: 16px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.results-header-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.results-title-compact {
  font-size: 14px;
  font-weight: 600;
  color: #2e7d32;
}

.refresh-btn {
  opacity: 0.7;
}

.refresh-btn:hover {
  opacity: 1;
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

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.stat-card {
  flex: 1;
  padding: 16px 12px;
  border-radius: 8px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  align-items: center;
  gap: 12px;
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

.stat-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
}

.forest-card .stat-icon {
  color: #2e7d32;
}

.nonforest-card .stat-icon {
  color: #f57c00;
}

.stat-content {
  flex: 1;
  text-align: left;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #212121;
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  font-weight: 600;
  color: #424242;
  margin-bottom: 2px;
}

.stat-detail {
  font-size: 11px;
  color: #757575;
  font-weight: 500;
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

/* Responsive adjustments */
@media (max-width: 600px) {
  .benchmark-select, .method-panels-compact {
    margin: 0 8px;
  }
  
  .results-section-compact {
    margin: 8px 8px;
    padding: 6px;
  }
  
  .stat-value {
    font-size: 16px;
  }
  
  .stat-label {
    font-size: 12px;
  }
  
  .stat-detail {
    font-size: 10px;
  }
  
  .stat-card {
    padding: 12px 8px;
  }
}
</style>