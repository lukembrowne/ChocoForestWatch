<template>
  <q-list dense class="layer-controls">
    <!-- Add benchmark button -->
    <q-item dense class="q-px-none q-mb-xs">
      <q-item-section avatar>
        <q-btn flat round dense icon="add" size="sm" @click="showBenchmarkDialog = true" />
      </q-item-section>
      <q-item-section>{{ $t('layers.switcher.benchmarks.title') }}</q-item-section>
    </q-item>

    <Sortable :list="mapLayers" item-key="id" @end="onDragEnd" :options="{ handle: '.drag-handle' }">
      <template #item="{ element }">
        <q-item dense class="q-px-none layer-row">
          <q-item-section avatar class="drag-handle cursor-move q-pr-xs">
            <q-icon name="drag_indicator" size="16px" />
          </q-item-section>
          <q-item-section class="q-pl-none">
            <q-checkbox v-model="element.visible" @update:model-value="toggleLayerVisibility(element.id)" :label="element.title" dense />
          </q-item-section>
          <q-item-section avatar>
            <q-btn flat round dense icon="tune" size="sm" @click="element.showOpacity = !element.showOpacity" />
          </q-item-section>
          <q-item-section avatar class="q-pl-xs" v-if="canRemove(element.id)">
            <q-btn flat round dense icon="delete" size="sm" color="negative" @click="removeLayer(element.id)" />
          </q-item-section>
        </q-item>
        <q-slide-transition>
          <div v-show="element.showOpacity" class="q-mx-md q-mb-sm">
            <q-slider v-model="element.opacity" :min="0" :max="1" :step="0.1" @update:model-value="updateOpacity(element)" dense />
          </div>
        </q-slide-transition>
      </template>
    </Sortable>

    <!-- Benchmark dialog -->
    <q-dialog v-model="showBenchmarkDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="text-h6">{{ $t('layers.switcher.benchmarks.title') }}</q-card-section>
        <q-card-section>
          <q-list bordered separator>
            <q-item v-for="b in benchmarkOptions" :key="b.value" clickable @click="addBenchmark(b.value)">
              <q-item-section>{{ b.label }}</q-item-section>
              <q-item-section side><q-icon name="add" /></q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-actions align="right"><q-btn flat :label="$t('common.close')" v-close-popup /></q-card-actions>
      </q-card>
    </q-dialog>
  </q-list>
</template>

<script>
import { computed, reactive } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { Sortable } from 'sortablejs-vue3'

export default {
  name: 'LayerControls',
  components: { Sortable },
  props: {
    mapId: {
      type: String,
      default: 'training'
    }
  },
  setup (props) {
    const mapStore = useMapStore()

    const mapLayers = computed(() => {
      const map = props.mapId === 'training' ? mapStore.map : mapStore.maps[props.mapId]
      if (!map) return []
      return map.getLayers().getArray().map(l => ({
        id: l.get('id'),
        title: l.get('title'),
        visible: l.getVisible(),
        opacity: l.getOpacity(),
        showOpacity: false
      }))
    })

    const updateOpacity = (layerObj) => {
      mapStore.updateLayerOpacity(layerObj.id, layerObj.opacity, props.mapId)
    }

    const toggleLayerVisibility = (id) => {
      mapStore.toggleLayerVisibility(id, props.mapId)
    }

    const removeLayer = (id) => {
      mapStore.removeLayer(id, props.mapId)
    }

    const onDragEnd = (evt) => {
      mapStore.reorderLayers(evt.oldIndex, evt.newIndex, props.mapId)
    }

    const canRemove = id => id.includes('landcover') || id.includes('deforestation') || id.includes('benchmark')

    // Benchmark dataset support
    const showBenchmarkDialog = reactive({ value: false })
    const benchmarkOptions = [
      { label: 'Hansen Tree Cover 2022', value: 'benchmarks-hansen-tree-cover-2022' },
      { label: 'MapBiomas 2022', value: 'benchmarks-mapbiomes-2022' },
      { label: 'ESA WorldCover 2020', value: 'benchmarks-esa-landcover-2020' },
      { label: 'JRC Forest Cover 2020', value: 'benchmarks-jrc-forestcover-2020' }
    ]

    const addBenchmark = (val) => {
      mapStore.addBenchmarkLayer(val, props.mapId)
      showBenchmarkDialog.value = false
    }

    return { mapLayers, toggleLayerVisibility, removeLayer, onDragEnd, canRemove, updateOpacity, showBenchmarkDialog, benchmarkOptions, addBenchmark }
  }
}
</script>

<style scoped>
.layer-row {
  min-height: 20px;
  padding-top: 0;
  padding-bottom: 0;
}
.layer-controls {
  max-height: 300px;
  overflow-y: auto;
}
/* highlight row while dragging */
.sortable-chosen {
  background: #f0f0f0;
}

.layer-row .q-item__section--avatar {
  padding-right: 4px;
  padding-left: 0;
}

.layer-row .q-item__section--main {
  padding-left: 0;
}

.layer-row .q-checkbox {
  font-size: 0.75rem;
}

.layer-row .q-btn {
  margin: 0;
}
</style> 