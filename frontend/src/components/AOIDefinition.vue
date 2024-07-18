<template>
  <div>
    <h6>Define Area of Interest</h6>
    <q-btn label="Draw AOI" color="primary" @click="startDrawingAOI" :disable="isDrawing" />
    <q-btn label="Clear AOI" color="negative" @click="clearAOI" :disable="!aoiDrawn" class="q-ml-sm" />
    
    <q-input v-model="aoiName" label="AOI Name" class="q-mt-md" />
    
    <q-btn label="Save AOI" color="positive" @click="saveAOI" :disable="!aoiDrawn" class="q-mt-md" />
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { useProjectStore } from 'stores/projectStore'
import { useQuasar } from 'quasar'
import { Draw } from 'ol/interaction'
import { Vector as VectorLayer } from 'ol/layer'
import { Vector as VectorSource } from 'ol/source'
import GeoJSON from 'ol/format/GeoJSON'

export default {
  name: 'AOIDefinitionComponent',
  emits: ['step-completed'],
  setup(props, { emit }) {
    const projectStore = useProjectStore()
    const $q = useQuasar()
    
    const isDrawing = ref(false)
    const aoiDrawn = ref(false)
    const aoiName = ref('')
    
    let drawInteraction
    let vectorLayer

    onMounted(() => {
      initializeVectorLayer()
    })

    onUnmounted(() => {
      if (drawInteraction) {
        projectStore.getMap.removeInteraction(drawInteraction)
      }
      if (vectorLayer) {
        projectStore.getMap.removeLayer(vectorLayer)
      }
    })

    const initializeVectorLayer = () => {
      vectorLayer = new VectorLayer({
        source: new VectorSource(),
        style: {
          'fill-color': 'rgba(255, 255, 255, 0.2)',
          'stroke-color': '#ffcc33',
          'stroke-width': 2
        }
      })
      projectStore.getMap.addLayer(vectorLayer)
    }

    const startDrawingAOI = () => {
      isDrawing.value = true
      drawInteraction = new Draw({
        source: vectorLayer.getSource(),
        type: 'Polygon'
      })
      
      drawInteraction.on('drawend', (event) => {
        isDrawing.value = false
        aoiDrawn.value = true
        projectStore.getMap.removeInteraction(drawInteraction)
      })

      projectStore.getMap.addInteraction(drawInteraction)
    }

    const clearAOI = () => {
      vectorLayer.getSource().clear()
      aoiDrawn.value = false
      aoiName.value = ''
    }

    const saveAOI = () => {
      if (!aoiDrawn.value) return

      const feature = vectorLayer.getSource().getFeatures()[0]
      const geojson = new GeoJSON().writeFeatureObject(feature)

      projectStore.setProjectAOI({
        name: aoiName.value,
        geometry: geojson
      })

      $q.notify({
        color: 'positive',
        message: 'AOI saved successfully',
        icon: 'check'
      })

      emit('step-completed')
    }

    return {
      isDrawing,
      aoiDrawn,
      aoiName,
      startDrawingAOI,
      clearAOI,
      saveAOI
    }
  }
}
</script>