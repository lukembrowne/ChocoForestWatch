<template>
  <div class="map-legend">
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

const { t } = useI18n()
</script>

<style scoped>
.map-legend {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 140px;
  border: 1px solid rgba(0, 0, 0, 0.1);
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
    top: 12px;
    right: 12px;
    padding: 10px;
    min-width: 120px;
  }
  
  .legend-title {
    font-size: 11px;
  }
  
  .legend-label {
    font-size: 11px;
  }
  
  .legend-color {
    width: 14px;
    height: 14px;
  }
}
</style>