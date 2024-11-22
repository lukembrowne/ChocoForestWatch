<template>
    <div class="custom-layer-switcher">
      <p class="text-subtitle2 q-mb-sm">Map Layers</p>
      <q-separator class="q-mb-sm" />
      <Sortable
        :list="sortableLayers"
        item-key="id"
        @end="onDragEnd"
        :options="{ handle: '.drag-handle' }"
      >
        <template #item="{ element }">
          <div class="layer-item q-mb-xs">
            <div class="row items-center no-wrap">
                <q-icon name="drag_indicator" class="drag-handle cursor-move q-mr-sm" />
                <q-checkbox v-model="element.visible" :label="element.title"
                    @update:model-value="toggleLayerVisibility(element.id)" dense class="col" />
                <q-btn flat round dense icon="tune" size="sm" @click="element.showOpacity = !element.showOpacity" />
                <q-btn
                  v-if="element.id.includes('prediction') || element.id.includes('deforestation')"
                  flat
                  round
                  dense
                  icon="delete"
                  color="negative"
                  size="sm"
                  @click="removeLayer(element.id)"
                >
                  <q-tooltip>Remove layer</q-tooltip>
                </q-btn>
            </div>
            <q-slide-transition>
                <div v-show="element.showOpacity" class="opacity-slider q-mt-xs">
                    <q-slider
                        v-model="element.opacity"
                        :min="0"
                        :max="1"
                        :step="0.1"
                        label
                        label-always
                        color="primary"
                        @update:model-value="updateLayerOpacity(element.id, $event)"
                        dense
                    />
                </div>
            </q-slide-transition>
          </div>
        </template>
      </Sortable>
    </div>
  </template>
  
  <script>
  import { ref, computed } from 'vue';
  import { useMapStore } from 'src/stores/mapStore';
  import { Sortable } from 'sortablejs-vue3';

  export default {
    name: 'CustomLayerSwitcher',
    components: {
      Sortable,
    },
    setup() {
      const mapStore = useMapStore();

      // const sortableLayers = computed(() => {
      //   let sortedLayers = [...mapStore.layers].sort((a, b) => b.zIndex - a.zIndex);
      //   console.log("sortableLayers within CustomLayerSwitcher.vue", sortedLayers)
      //   return sortedLayers;
      // });

      const sortableLayers = computed(() => {
        return mapStore.layers;
      });

      const onDragEnd = (event) => {
        console.log("drag end event", event)
        console.log("Layers before reorder", mapStore.layers)
        mapStore.reorderLayers(event.oldIndex, event.newIndex);
        console.log("Layers after reorder", mapStore.layers)
      };

      const toggleLayerVisibility = (layerId) => {
        mapStore.toggleLayerVisibility(layerId);
      };

      const updateLayerOpacity = (layerId, opacity) => {
        mapStore.updateLayerOpacity(layerId, opacity);
      };

      const removeLayer = (layerId) => {
        mapStore.removeLayer(layerId);
      };

      return {
        sortableLayers,
        onDragEnd,
        toggleLayerVisibility,
        updateLayerOpacity,
        removeLayer,
      };
    }
  };
  </script>
  
  <style lang="scss" scoped>
.custom-layer-switcher {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: rgba(255, 255, 255, 0.95);
  padding: 8px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-width: 300px;
  max-height: 80vh;
  overflow-y: auto;

  .text-subtitle2 {
    font-size: 0.775rem;
    margin-bottom: 4px;
  }

  .layer-item {
    font-size: 0.7125rem;
    
    .q-checkbox {
      font-size: 0.7125rem;
    }
    
    .opacity-slider {
      padding-left: 24px;
    }
  }

  .q-btn {
    padding: 4px;
    
    .q-icon {
      font-size: 0.8rem;
    }
  }
}

.layer-list {
  max-height: 60vh;
}

.layer-item {
  border-bottom: 1px solid #e0e0e0;
  padding: 4px 0;

  &:last-child {
    border-bottom: none;
  }
}

.opacity-slider {
  padding: 4px 0;
}

.drag-handle {
  cursor: move;
  font-size: 1.2rem;
}
  </style>