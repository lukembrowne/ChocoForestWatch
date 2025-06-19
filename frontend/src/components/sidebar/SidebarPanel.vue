<template>
  <div class="sidebar-panel column full-height">

   
    <!-- Content Section -->
    <div class="content-section">
      <LandCoverStats />
    </div>

     <!-- File Upload Section -->
     <div class="upload-section">
      <div class="section-label">
        <q-icon name="upload_file" class="section-icon" />
        {{ t('sidebar.upload.title') }}
        <q-btn 
          flat 
          round 
          dense 
          size="xs" 
          icon="info" 
          class="info-btn"
        >
          <q-tooltip class="bg-dark text-white" max-width="280px">
            {{ t('sidebar.upload.tooltip') }}
          </q-tooltip>
        </q-btn>
      </div>
      
      <div class="upload-area" :class="{ 'drag-over': isDragOver }" 
           @dragover.prevent="onDragOver" 
           @dragleave.prevent="onDragLeave" 
           @drop.prevent="onDrop"
           @click="triggerFileUpload">
        <q-icon name="cloud_upload" size="32px" class="upload-icon" />
        <div class="upload-text">{{ t('sidebar.upload.dragDrop') }}</div>
        <div class="upload-subtext">{{ t('sidebar.upload.clickToSelect') }}</div>
        <div class="supported-formats">{{ t('sidebar.upload.supportedFormats') }}</div>
      </div>
      
      <input 
        type="file" 
        ref="fileInput" 
        style="display: none" 
        accept=".geojson,.json,application/geo+json,.zip"
        @change="handleFileUpload" 
      />
      
      <!-- Upload progress -->
      <div v-if="uploadProgress" class="upload-progress">
        <q-linear-progress :value="uploadProgress.percent / 100" color="primary" class="q-mb-xs" />
        <div class="progress-text">{{ uploadProgress.message }}</div>
      </div>
      
      <!-- Uploaded file info -->
      <div v-if="uploadedFile" class="uploaded-file-info">
        <div class="file-info-header">
          <q-icon name="check_circle" color="positive" />
          <span class="file-name">{{ uploadedFile.name }}</span>
          <q-btn flat round dense size="sm" icon="close" @click="clearUploadedFile" />
        </div>
        <div class="file-stats">
          <div class="stat-item">
            <span class="stat-label">{{ t('sidebar.upload.features') }}:</span>
            <span class="stat-value">{{ uploadedFile.featureCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('sidebar.upload.area') }}:</span>
            <span class="stat-value">{{ uploadedFile.totalArea.toLocaleString(undefined, { maximumFractionDigits: 1 }) }} ha</span>
          </div>
        </div>
        <q-btn 
          color="primary" 
          :label="t('sidebar.upload.calculateStats')" 
          @click="calculateForestStats" 
          :loading="isCalculatingStats"
          class="full-width q-mt-sm"
          :disable="!uploadedFile"
        />
      </div>
    </div>

     <!-- Search Section -->
     <div class="search-section">
      <div class="section-label">
        <q-icon name="search" class="section-icon" />
        {{ t('sidebar.search.title') }}
      </div>
      <q-select
        v-model="selectedLabel"
        :options="options"
        use-input
        input-debounce="300"
        outlined
        :placeholder="t('sidebar.search.placeholder')"
        option-label="label"
        option-value="label"
        @filter="onFilter"
        @update:model-value="onSelect"
        emit-value
        map-options
        class="search-input"
      >
        <template v-slot:prepend>
          <q-icon name="place" color="primary" />
        </template>
        <template v-slot:no-option>
          <q-item>
            <q-item-section class="text-grey-6">
              <div class="text-center">
                <q-icon name="search_off" size="md" class="q-mb-sm" />
                <div>{{ t('sidebar.search.noResults') }}</div>
                <div class="text-caption">{{ t('sidebar.search.tryDifferent') }}</div>
              </div>
            </q-item-section>
          </q-item>
        </template>
      </q-select>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useMapStore } from 'src/stores/mapStore'
import { useI18n } from 'vue-i18n'
import { GeoJSON } from 'ol/format'
import { getArea } from 'ol/sphere'
import { transformExtent } from 'ol/proj'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import { Style, Fill, Stroke } from 'ol/style'
import shp from 'shpjs'
import api from 'src/services/api'

import LandCoverStats from '../LandCoverStats.vue'

const mapStore   = useMapStore()
const { t } = useI18n()
const $q = useQuasar()

const options        = ref([])
const selectedLabel  = ref('')

// File upload state
const fileInput = ref(null)
const isDragOver = ref(false)
const uploadProgress = ref(null)
const uploadedFile = ref(null)
const isCalculatingStats = ref(false)
const uploadedGeometry = ref(null)

const onFilter = (val, update, abort) => {
  if (val === '') {
    options.value = []
    update()
    return
  }
  mapStore.searchLocation(val).then(res => {
    update(() => {
      options.value = res
    })
  })
}

const onSelect = (val) => {
  const result = options.value.find(o => o.label === val)
  if (result) {
    mapStore.zoomToSearchResult(result)
  }
}

// File upload functions
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
  // Reset input value to allow re-uploading same file
  event.target.value = ''
}

const processFile = async (file) => {
  uploadProgress.value = { percent: 0, message: t('sidebar.upload.reading') }
  
  try {
    let geojson
    
    if (file.name.toLowerCase().endsWith('.geojson') || file.name.toLowerCase().endsWith('.json')) {
      geojson = await handleGeoJSON(file)
    } else if (file.name.toLowerCase().endsWith('.zip')) {
      geojson = await handleShapefile(file)
    } else {
      throw new Error(t('sidebar.upload.unsupportedFormat'))
    }
    
    uploadProgress.value = { percent: 50, message: t('sidebar.upload.processing') }
    
    // Process and validate the geometry
    await processGeometry(geojson, file.name)
    
    uploadProgress.value = { percent: 100, message: t('sidebar.upload.complete') }
    
    // Clear progress after short delay
    setTimeout(() => {
      uploadProgress.value = null
    }, 1000)
    
  } catch (error) {
    console.error('File upload error:', error)
    uploadProgress.value = null
    $q.notify({
      type: 'negative',
      message: error.message || t('sidebar.upload.error'),
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
        reject(new Error(t('sidebar.upload.invalidGeoJSON')))
      }
    }
    reader.onerror = () => reject(new Error(t('sidebar.upload.readError')))
    reader.readAsText(file)
  })
}

const handleShapefile = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const geojson = await shp(arrayBuffer)
    return geojson
  } catch (error) {
    throw new Error(t('sidebar.upload.invalidShapefile'))
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
    throw new Error(t('sidebar.upload.noFeatures'))
  }
  
  // Read features with OpenLayers
  const format = new GeoJSON()
  const features = format.readFeatures(geojson, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857'
  })
  
  if (features.length === 0) {
    throw new Error(t('sidebar.upload.noValidFeatures'))
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
    // Calculate the combined extent of all features
    let extent = features[0].getGeometry().getExtent().slice() // Copy first extent
    
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
    message: t('sidebar.upload.success', { count: features.length }),
    timeout: 3000
  })
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
      color: 'rgba(33, 150, 243, 0.2)' // Blue with transparency
    }),
    stroke: new Stroke({
      color: '#2196F3', // Blue stroke
      width: 3
    })
  })
  
  // Create vector layer
  const vectorLayer = new VectorLayer({
    source: vectorSource,
    style: style,
    title: 'Uploaded Features',
    id: 'uploaded-features',
    zIndex: 10 // High z-index to appear above other layers
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
        // Single feature - send as Feature
        geometryToSend = geometryToSend.features[0]
      } else {
        // Multiple features - union them into a single feature
        // For now, we'll send the first feature and calculate stats for each separately
        // TODO: Implement proper geometry union if needed
        geometryToSend = geometryToSend.features[0]
        
        $q.notify({
          type: 'warning',
          message: t('sidebar.upload.multipleFeatures'),
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
    
    // Update the summary stats in the mapStore so LandCoverStats component shows them
    mapStore.summaryStats = statsWithName
    
    $q.notify({
      type: 'positive',
      message: t('sidebar.upload.statsCalculated'),
      timeout: 3000
    })
    
  } catch (error) {
    console.error('Error calculating forest stats:', error)
    $q.notify({
      type: 'negative',
      message: error.message || t('sidebar.upload.statsError'),
      timeout: 4000
    })
  } finally {
    isCalculatingStats.value = false
  }
}
</script>

<style scoped>
.sidebar-panel {
  background: linear-gradient(180deg, #f8fffe 0%, #ffffff 100%);
  overflow-y: auto;
  border-right: 1px solid #e0e7e4;
}


.upload-section {
  padding: 20px 16px;
  background: white;
  border-bottom: 1px solid #e8f5e8;
}

.upload-area {
  border: 2px dashed #e0e7e4;
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafcfa;
  margin-bottom: 16px;
}

.upload-area:hover {
  border-color: #4caf50;
  background: #f1f8e9;
  transform: translateY(-2px);
}

.upload-area.drag-over {
  border-color: #4caf50;
  background: #e8f5e8;
  border-style: solid;
}

.upload-icon {
  color: #81c784;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: #2e7d32;
  margin-bottom: 4px;
}

.upload-subtext {
  font-size: 12px;
  color: #66bb6a;
  margin-bottom: 8px;
}

.supported-formats {
  font-size: 11px;
  color: #9e9e9e;
  font-style: italic;
}

.upload-progress {
  margin-bottom: 16px;
}

.progress-text {
  font-size: 12px;
  color: #666;
  text-align: center;
  margin-top: 4px;
}

.uploaded-file-info {
  background: #f1f8e9;
  border: 1px solid #c8e6c9;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.file-info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-name {
  flex: 1;
  font-weight: 500;
  color: #2e7d32;
  font-size: 13px;
  word-break: break-word;
  line-height: 1.2;
}

.file-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-label {
  color: #666;
}

.stat-value {
  color: #2e7d32;
  font-weight: 500;
}

.info-btn {
  margin-left: 4px;
  opacity: 0.7;
}

.info-btn:hover {
  opacity: 1;
}

.search-section {
  padding: 20px 16px;
  background: white;
  border-bottom: 1px solid #e8f5e8;
}

.section-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #2e7d32;
  margin-bottom: 12px;
  font-size: 14px;
}

.section-icon {
  font-size: 18px;
  margin-right: 6px;
}

.search-input {
  border-radius: 8px;
}

.search-input :deep(.q-field__control) {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s ease;
}

.search-input :deep(.q-field__control):hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.search-input :deep(.q-field--focused .q-field__control) {
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.15);
}

.content-section {
  flex: 1;
  padding: 16px;
  background: white;
  overflow-y: auto;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .sidebar-header {
    padding: 16px 12px 12px;
  }
  
  .header-text {
    font-size: 16px;
  }
  
  .search-section {
    padding: 16px 12px;
  }
  
  .content-section {
    padding: 12px;
  }
}
</style> 