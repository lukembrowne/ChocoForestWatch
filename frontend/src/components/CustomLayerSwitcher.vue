<template>
  <div class="custom-layer-switcher">
    <div class="row items-center justify-between q-mb-sm">
      <p class="text-subtitle1 q-mb-none">{{ t('layers.switcher.title') }}</p>
      <div class="row items-center no-wrap">
        <!-- Add benchmark button -->
        <q-btn flat round dense icon="add" size="sm" class="q-mr-xs" @click="showBenchmarkDialog = true">
          <q-tooltip>{{ t('layers.switcher.tooltips.addBenchmark') }}</q-tooltip>
        </q-btn>
        <!-- Expand / collapse -->
        <q-btn flat round dense :icon="isExpanded ? 'expand_less' : 'expand_more'" size="sm" @click="isExpanded = !isExpanded">
          <q-tooltip>{{ isExpanded ? t('layers.switcher.tooltips.collapse') : t('layers.switcher.tooltips.expand') }}</q-tooltip>
        </q-btn>
      </div>
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
                <q-btn v-if="element.id.includes('landcover') || element.id.includes('deforestation') || element.id.includes('benchmark')" flat round dense
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

    <!-- Dialog for selecting benchmark dataset -->
    <q-dialog v-model="showBenchmarkDialog">
      <q-card style="min-width: 600px">
        <q-card-section class="text-h6">{{ t('layers.switcher.benchmarks.title') }}</q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-md">
            <div v-for="benchmark in benchmarkOptions" :key="benchmark.value" class="col-12 col-md-6">
              <q-card 
                class="benchmark-card cursor-pointer" 
                :class="{ 'selected': selectedBenchmark === benchmark.value }"
                @click="selectedBenchmark = benchmark.value"
              >
                <q-card-section>
                  <div class="text-h6">{{ t(`layers.switcher.benchmarks.datasets.${benchmark.value.split('-')[1]}.title`) }}</div>
                  <div class="text-caption q-mt-sm">{{ t(`layers.switcher.benchmarks.datasets.${benchmark.value.split('-')[1]}.description`) }}</div>
                  <div class="text-caption q-mt-sm">
                    <a :href="t(`layers.switcher.benchmarks.datasets.${benchmark.value.split('-')[1]}.url`)"
                       target="_blank"
                       class="text-primary"
                       @click.stop>
                      {{ t('common.learnMore') }}
                    </a>
                  </div>
                </q-card-section>
                <q-card-actions align="right">
                  <q-btn flat color="primary" :label="t('layers.switcher.benchmarks.add')" @click.stop="addBenchmark(benchmark.value)" />
                </q-card-actions>
              </q-card>
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
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

    // Benchmark dialog state
    const showBenchmarkDialog = ref(false);
    const selectedBenchmark = ref(null);
    const benchmarkOptions = [
      { 
        label: 'Hansen Tree Cover 2022', 
        value: 'benchmarks-hansen-tree-cover-2022',
        description: 'Global forest cover data from University of Maryland, showing tree cover density at 30m resolution.'
      },
      { 
        label: 'MapBiomas 2022', 
        value: 'benchmarks-mapbiomes-2022',
        description: 'Brazilian land use and land cover data, providing detailed classification of natural and anthropic areas.'
      },
      { 
        label: 'ESA WorldCover 2020', 
        value: 'benchmarks-esa-landcover-2020',
        description: 'Global land cover map at 10m resolution from the European Space Agency, covering 11 land cover classes.'
      },
      { 
        label: 'JRC Forest Cover 2020', 
        value: 'benchmarks-jrc-forestcover-2020',
        description: 'Global forest cover map from the Joint Research Centre, showing forest presence at 10m resolution.'
      },
      { 
        label: 'PALSAR Forest/Non-Forest 2020', 
        value: 'benchmarks-palsar-2020',
        description: 'Forest/non-forest classification based on L-band SAR data from the PALSAR-2 sensor.'
      },
      { 
        label: 'WRI Tree Cover 2020', 
        value: 'benchmarks-wri-treecover-2020',
        description: 'Global tree cover data from World Resources Institute, showing percentage of tree cover at 30m resolution.'
      },
    ];

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
      showBenchmarkDialog.value = false;
    };

    return {
      mapLayers,
      onDragEnd,
      toggleLayerVisibility,
      updateLayerOpacity,
      removeLayer,
      t,
      isExpanded,
      showBenchmarkDialog,
      benchmarkOptions,
      selectedBenchmark,
      addBenchmark,
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

.benchmark-card {
  transition: all 0.3s ease;
  border: 2px solid transparent;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  &.selected {
    border-color: var(--q-primary);
  }

  .text-h6 {
    font-size: 1rem;
    font-weight: 500;
  }

  .text-caption {
    color: rgba(0, 0, 0, 0.6);
  }
}
</style>