<template>
  <div 
    v-if="mapStore.gfwAlertVisible && mapStore.gfwAlertInfo"
    class="gfw-alert-popup"
    :style="popupStyle"
  >
    <div class="popup-content">
      <div class="popup-header">
        <div class="popup-title">
          <q-icon name="warning" color="red" size="18px" class="q-mr-sm" />
          <span class="text-weight-medium">{{ $t('alerts.gfw.title') }}</span>
        </div>
        <q-btn
          icon="close"
          flat
          dense
          size="sm"
          @click="mapStore.hideGFWAlertPopup"
          class="popup-close"
        />
      </div>
      
      <div class="popup-body">
        <div class="alert-info">
          <div v-if="mapStore.gfwAlertInfo.date" class="info-item">
            <strong>{{ $t('alerts.gfw.date') }}:</strong>
            {{ formatDate(mapStore.gfwAlertInfo.date) }}
          </div>
          
          <div v-if="mapStore.gfwAlertInfo.confidence" class="info-item">
            <strong>{{ $t('alerts.gfw.confidence') }}:</strong>
            <span 
              :class="getConfidenceClass(mapStore.gfwAlertInfo.confidence)"
              class="confidence-badge"
            >
              {{ getConfidenceLabel(mapStore.gfwAlertInfo.confidence) }}
            </span>
          </div>
          
        </div>
      </div>
      
      <!-- Pointer arrow -->
      <div class="popup-arrow"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useI18n } from 'vue-i18n'

const mapStore = useMapStore()
const { t } = useI18n()

// Convert map coordinate to screen pixel position
const popupStyle = computed(() => {
  if (!mapStore.gfwAlertInfo?.coordinate || !mapStore.map) {
    return { display: 'none' }
  }
  
  try {
    const map = mapStore.map
    const pixel = map.getPixelFromCoordinate(mapStore.gfwAlertInfo.coordinate)
    
    if (!pixel) {
      return { display: 'none' }
    }
    
    // Get map container position
    const mapElement = map.getTargetElement()
    const mapRect = mapElement.getBoundingClientRect()
    
    // Calculate absolute position relative to viewport
    const left = mapRect.left + pixel[0]
    const top = mapRect.top + pixel[1] - 20 // Offset above the click point
    
    return {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
      transform: 'translate(-50%, -100%)', // Center horizontally, position above point
      zIndex: 1000
    }
  } catch (error) {
    console.error('Error calculating popup position:', error)
    return { display: 'none' }
  }
})

const formatDate = (date) => {
  return new Date(date).toLocaleDateString()
}

const getConfidenceLabel = (confidence) => {
  const labels = {
    2: t('alerts.gfw.confidenceLevels.low'),
    3: t('alerts.gfw.confidenceLevels.medium'),
    4: t('alerts.gfw.confidenceLevels.high')
  }
  return labels[confidence] || confidence
}

const getConfidenceClass = (confidence) => {
  const classes = {
    2: 'confidence-low',
    3: 'confidence-medium',
    4: 'confidence-high'
  }
  return classes[confidence] || ''
}
</script>

<style scoped>
.gfw-alert-popup {
  position: fixed;
  z-index: 1000;
  pointer-events: auto;
}

.popup-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 1px solid #e0e0e0;
  min-width: 280px;
  max-width: 350px;
  position: relative;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}

.popup-title {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #333;
}

.popup-close {
  opacity: 0.7;
}

.popup-close:hover {
  opacity: 1;
}

.popup-body {
  padding: 16px;
}

.alert-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  line-height: 1.4;
}

.info-item strong {
  color: #555;
  min-width: 80px;
}

.confidence-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.confidence-low {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.confidence-medium {
  background: #ffeaa7;
  color: #b8860b;
  border: 1px solid #fdcb6e;
}

.confidence-high {
  background: #fdcb6e;
  color: #d63031;
  border: 1px solid #fd79a8;
}

.popup-arrow {
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid white;
}

.popup-arrow::before {
  content: '';
  position: absolute;
  top: -9px;
  left: -9px;
  width: 0;
  height: 0;
  border-left: 9px solid transparent;
  border-right: 9px solid transparent;
  border-top: 9px solid #e0e0e0;
}
</style>