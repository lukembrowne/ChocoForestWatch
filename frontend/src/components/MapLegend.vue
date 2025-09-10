<template>
  <div class="map-legend" :class="{ 'with-slider': showBasemapSlider }">
    <div class="legend-header">
      <q-icon name="info" size="14px" class="q-mr-xs" />
      <span class="legend-title">{{ t('legend.title') }}</span>
    </div>
    <div class="legend-items">
      <div class="legend-item">
        <div class="legend-color forest"></div>
        <span class="legend-label">{{ t('legend.forest') }}</span>
      </div>
      <div class="legend-item">
        <div class="legend-color non-forest"></div>
        <span class="legend-label">{{ t('legend.nonForest') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'

const { t } = useI18n()
const mapStore = useMapStore()

// Check if basemap slider should be visible (same logic as BasemapDateSlider)
const showBasemapSlider = computed(() => {
  // Check if there's a planet-basemap layer on the map
  if (!mapStore.map) return false;
  const planetLayer = mapStore.map.getLayers().getArray().find(layer => 
    layer.get('id') === 'planet-basemap'
  );
  return !!planetLayer;
})
</script>

<style scoped>
.map-legend {
  position: absolute;
  bottom: 25px;
  right: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 140px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: bottom 0.3s ease-in-out;
}

.map-legend.with-slider {
  bottom: 150px;
}

.legend-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: #1a1a1a;
}

.legend-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  border: 1px solid rgba(0, 0, 0, 0.2);
  flex-shrink: 0;
}

.legend-color.forest {
  background-color: rgb(34, 102, 51);
}

.legend-color.non-forest {
  background-color: rgb(205, 170, 125);
}

.legend-label {
  font-size: 12px;
  color: #2c2c2c;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .map-legend {
    bottom: 16px;
    right: 16px;
    padding: 8px;
    min-width: 110px;
    max-width: 140px;
  }
  
  .map-legend.with-slider {
    bottom: 150px;
  }
  
  .legend-header {
    margin-bottom: 6px;
  }
  
  .legend-title {
    font-size: 10px;
  }
  
  .legend-items {
    gap: 4px;
  }
  
  .legend-label {
    font-size: 10px;
  }
  
  .legend-color {
    width: 12px;
    height: 12px;
  }
}

@media (max-width: 480px) {
  .map-legend {
    bottom: 16px;
    right: 16px;
    padding: 6px;
    min-width: 100px;
    max-width: 120px;
  }
  
  .legend-header {
    margin-bottom: 4px;
  }
  
  .legend-title {
    font-size: 9px;
  }
  
  .legend-items {
    gap: 3px;
  }
  
  .legend-item {
    gap: 6px;
  }
  
  .legend-label {
    font-size: 9px;
  }
  
  .legend-color {
    width: 10px;
    height: 10px;
  }
}
</style>