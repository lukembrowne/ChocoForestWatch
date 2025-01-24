<template>
  <div class="custom-layer-switcher">
    <div class="row items-center justify-between q-mb-sm">
      <p class="text-subtitle1 q-mb-none">{{ t('layers.switcher.title') }}</p>
      <q-btn flat round dense :icon="isExpanded ? 'expand_less' : 'expand_more'" size="sm" @click="isExpanded = !isExpanded">
        <q-tooltip>{{ isExpanded ? t('layers.switcher.tooltips.collapse') : t('layers.switcher.tooltips.expand') }}</q-tooltip>
      </q-btn>
    </div>
    <q-slide-transition>
      <div v-show="isExpanded">
        <Sortable :list="mapLayers" item-key="id" @end="onDragEnd" :options="{ handle: '.drag-handle' }">
          <template #item="{ element }">
            <div class="layer-item q-mb-xs">
              <div class="row items-center no-wrap">
                <q-icon name="drag_indicator" class="drag-handle cursor-move q-mr-sm" />
                <q-checkbox v-model="element.visible" :label="element.title"
                  @update:model-value="toggleLayerVisibility(element.id)" dense class="col" />
                <!-- <q-btn flat round dense icon="tune" size="sm" @click="element.showOpacity = !element.showOpacity">
                  <q-tooltip>{{ t('layers.switcher.tooltips.toggleOpacity') }}</q-tooltip>
                </q-btn> -->
                <q-btn v-if="element.id.includes('landcover') || element.id.includes('deforestation')" flat round dense
                  icon="delete" color="negative" size="sm" @click="removeLayer(element.id)">
                  <q-tooltip>{{ t('layers.switcher.tooltips.remove') }}</q-tooltip>
                </q-btn>
              </div>
              <!-- <q-slide-transition>
                <div v-show="element.showOpacity" class="opacity-slider q-mt-xs">
                  <q-slider v-model="element.opacity" :min="0" :max="1" :step="0.1" label label-always color="primary"
                    @update:model-value="updateLayerOpacity(element.id, $event)" dense />
                </div>
              </q-slide-transition> -->
            </div>
          </template>
        </Sortable>
      </div>
    </q-slide-transition>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { Sortable } from 'sortablejs-vue3';
import { useI18n } from 'vue-i18n';

export default {
  name: 'CustomLayerSwitcher',
  components: {
    Sortable,
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

    return {
      mapLayers,
      onDragEnd,
      toggleLayerVisibility,
      updateLayerOpacity,
      removeLayer,
      t,
      isExpanded,
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
  width: 250px;
  max-height: 80vh;
  overflow-y: auto;

  .text-subtitle1 {
    margin: 0;
  }
}

.layer-item {

  .q-checkbox {
    font-size: .85rem;
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

.layer-list {
  max-height: 60vh;
}

.layer-item {
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 4px;
  padding-top: 4px;

  &:last-child {
    border-bottom: none;
  }

  &:first-child {
    border-top: 1px solid #e0e0e0;
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