<template>
  <div class="custom-layer-switcher">
    <!-- Header Section -->
    <div class="switcher-header">
      <div class="header-top">
        <div class="header-title">
          <q-icon name="layers" class="title-icon" />
          <span class="title-text">{{ t('layers.switcher.title') }}</span>
        </div>
        <q-btn 
          flat 
          round 
          dense 
          :icon="isExpanded ? 'expand_less' : 'expand_more'" 
          size="sm" 
          class="expand-btn"
          @click="isExpanded = !isExpanded"
        >
          <q-tooltip>{{ isExpanded ? t('layers.switcher.tooltips.collapse') : t('layers.switcher.tooltips.expand') }}</q-tooltip>
        </q-btn>
      </div>
      
      <!-- Add Dataset Section -->
      <div class="add-dataset-section" v-show="isExpanded">
        <BenchmarkSelector />
      </div>
    </div>
    <!-- Layers List Section -->
    <q-slide-transition>
      <div v-show="isExpanded" class="layers-container">
        <div class="layers-header">
          <span class="layers-count">{{ mapLayers.length }} {{ t('layers.switcher.layersCount') }}</span>
        </div>
        
        <div class="layers-list">
          <Sortable :list="mapLayers" item-key="id" @end="onDragEnd" :options="{ handle: '.drag-handle' }">
            <template #item="{ element }">
              <div class="layer-item" :class="{ 'layer-visible': element.visible }">
                <div class="layer-main">
                  <q-icon name="drag_indicator" class="drag-handle" />
                  
                  <div class="layer-content">
                    <div class="layer-info">
                      <q-checkbox 
                        v-model="element.visible" 
                        :label="element.title"
                        @update:model-value="toggleLayerVisibility(element.id)" 
                        dense 
                        class="layer-checkbox"
                      />
                    </div>
                    
                    <div class="layer-actions">
                      <q-btn 
                        flat 
                        round 
                        dense 
                        icon="tune" 
                        size="sm" 
                        class="opacity-btn"
                        @click="element.showOpacity = !element.showOpacity"
                        :color="element.showOpacity ? 'primary' : 'grey-6'"
                      >
                        <q-tooltip>{{ t('layers.switcher.tooltips.toggleOpacity') }}</q-tooltip>
                      </q-btn>
                      
                      <q-btn 
                        v-if="element.id.includes('landcover') || element.id.includes('deforestation') || element.id.includes('benchmark')" 
                        flat 
                        round 
                        dense
                        icon="delete" 
                        color="negative" 
                        size="sm" 
                        class="delete-btn"
                        @click="removeLayer(element.id)"
                      >
                        <q-tooltip>{{ t('layers.switcher.tooltips.remove') }}</q-tooltip>
                      </q-btn>
                    </div>
                  </div>
                </div>
                
                <q-slide-transition>
                  <div v-show="element.showOpacity" class="opacity-controls">
                    <div class="opacity-label">
                      <span>{{ t('layers.switcher.opacity') }}</span>
                      <span class="opacity-value">{{ Math.round(element.opacity * 100) }}%</span>
                    </div>
                    <q-slider 
                      v-model="element.opacity" 
                      :min="0" 
                      :max="1" 
                      :step="0.05" 
                      color="primary"
                      track-color="grey-3"
                      @update:model-value="updateLayerOpacity(element.id, $event)" 
                      dense 
                      class="opacity-slider"
                    />
                  </div>
                </q-slide-transition>
              </div>
            </template>
          </Sortable>
        </div>
      </div>
    </q-slide-transition>

 
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { Sortable } from 'sortablejs-vue3';
import { useI18n } from 'vue-i18n';
import BenchmarkSelector from './sidebar/BenchmarkSelector.vue'



export default {
  name: 'CustomLayerSwitcher',
  components: {
    Sortable,
    BenchmarkSelector,
  },
  props: {
    mapId: {
      type: String,
      required: true,
      validator: value => ['primary', 'secondary', 'training'].includes(value)
    }
  },
  setup(props) {
    const mapStore = useMapStore();
    const { t } = useI18n();
    const isExpanded = ref(true);

    const mapLayers = computed(() => {
      if (props.mapId === 'training') {
        // console.log("mapLayers in training", mapStore.layers)
        if (mapStore.map) {
          // console.log("Mapstores dirctly from mapStore", mapStore.map.getLayers().getArray())
          return mapStore.map.getLayers().getArray()
            .map(layer => ({
              id: layer.get('id'),
              title: layer.get('title'),
              zIndex: layer.getZIndex(),
              visible: layer.getVisible(),
              opacity: layer.getOpacity(),
              showOpacity: false,
              layer: layer
            }))
            .sort((a, b) => b.zIndex - a.zIndex);
        }
        return [];
      } else {

        const map = mapStore.maps[props.mapId];
        if (!map) return [];

        // console.log("mapLayers", map.getLayers().getArray())

        return map.getLayers().getArray()
          .map(layer => ({
            id: layer.get('id'),
            title: layer.get('title'),
            zIndex: layer.getZIndex(),
            visible: layer.getVisible(),
            opacity: layer.getOpacity(),
            showOpacity: false,
            layer: layer
          }))
          .sort((a, b) => b.zIndex - a.zIndex);
      }
    });

    const onDragEnd = (event) => {
      mapStore.reorderLayers(event.oldIndex, event.newIndex, props.mapId);
    };

    const toggleLayerVisibility = (layerId) => {
      mapStore.toggleLayerVisibility(layerId, props.mapId);
    };

    const updateLayerOpacity = (layerId, opacity) => {
      mapStore.updateLayerOpacity(layerId, opacity, props.mapId);
    };

    const removeLayer = (layerId) => {
      mapStore.removeLayer(layerId, props.mapId);
    };

    const addBenchmark = (benchmarkValue) => {
      if (!benchmarkValue) return;
      mapStore.addBenchmarkLayer(benchmarkValue, props.mapId);
    };

    return {
      mapLayers,
      onDragEnd,
      toggleLayerVisibility,
      updateLayerOpacity,
      removeLayer,
      t,
      isExpanded
    };
  }
};
</script>

<style lang="scss" scoped>
.custom-layer-switcher {
  position: absolute;
  top: 10px;
  right: 10px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95));
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  z-index: 1000;
  width: 280px;
  max-height: 85vh;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15), 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

// Header Section
.switcher-header {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  padding: 16px;
  border-radius: 12px 12px 0 0;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 20px;
  color: #4ade80;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  letter-spacing: -0.025em;
}

.expand-btn {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 8px;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.95);
    border-color: #22c55e;
    transform: scale(1.05);
  }

  .q-icon {
    color: #64748b;
    font-size: 18px;
  }
}

.add-dataset-section {
  margin-top: 8px;
  animation: fadeInUp 0.3s ease-out;
}

// Layers Section
.layers-container {
  padding: 0;
  max-height: calc(85vh - 120px);
  overflow-y: auto;
  
  &::-webkit-scrollbar {
    width: 4px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.3);
    border-radius: 2px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.5);
  }
}

.layers-header {
  padding: 12px 16px 8px;
  background: rgba(248, 250, 252, 0.5);
  border-bottom: 1px solid rgba(226, 232, 240, 0.3);
}

.layers-count {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.layers-list {
  padding: 8px 12px 12px;
}

// Layer Items
.layer-item {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(226, 232, 240, 0.4);
  border-radius: 8px;
  margin-bottom: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;

  &:hover {
    background: rgba(255, 255, 255, 0.9);
    border-color: rgba(34, 197, 94, 0.3);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  &.layer-visible {
    border-color: rgba(34, 197, 94, 0.4);
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.05), rgba(255, 255, 255, 0.8));
  }

  &:last-child {
    margin-bottom: 0;
  }
}

.layer-main {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.drag-handle {
  cursor: grab;
  color: #94a3b8;
  font-size: 16px;
  transition: color 0.2s ease;
  padding: 2px;

  &:hover {
    color: #64748b;
  }

  &:active {
    cursor: grabbing;
    color: #22c55e;
  }
}

.layer-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 0;
}

.layer-info {
  flex: 1;
  min-width: 0;
}

.layer-checkbox {
  .q-checkbox__label {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    line-height: 1.3;
  }

  .q-checkbox__inner {
    transform: scale(0.9);
  }
}

.layer-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.opacity-btn, .delete-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  transition: all 0.2s ease;

  .q-icon {
    font-size: 14px;
  }

  &:hover {
    transform: scale(1.1);
  }
}

.opacity-btn {
  &:hover {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
}

.delete-btn {
  &:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
}

// Opacity Controls
.opacity-controls {
  padding: 8px 16px 12px;
  background: rgba(248, 250, 252, 0.8);
  border-top: 1px solid rgba(226, 232, 240, 0.3);
  animation: fadeInDown 0.2s ease-out;
}

.opacity-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.opacity-value {
  color: #22c55e;
  font-weight: 600;
}

.opacity-slider {
  .q-slider__track {
    height: 3px;
  }

  .q-slider__thumb {
    width: 14px;
    height: 14px;
    box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
  }
}

// Animations
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// Responsive Design
@media (max-width: 768px) {
  .custom-layer-switcher {
    width: 260px;
    right: 8px;
    top: 8px;
  }
  
  .title-text {
    font-size: 14px;
  }
  
  .layer-checkbox .q-checkbox__label {
    font-size: 12px;
  }
}
</style>