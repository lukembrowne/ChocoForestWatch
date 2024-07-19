<template>
  <div>
    <h6>Define Area of Interest</h6>
    <p v-if="!aoiDrawn">Please draw your Area of Interest on the map.</p>
    <q-btn label="Draw AOI" color="primary" @click="startDrawingAOI" :disable="isDrawing" />
    <q-btn label="Clear AOI" color="negative" @click="clearAOI" :disable="!aoiDrawn" class="q-ml-sm" />

    <q-btn v-if="aoiDrawn" label="Save AOI" color="positive" @click="saveAOI" class="q-mt-md" />
  </div>
</template>


<script>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useQuasar } from 'quasar'
import Draw, {
  createBox,
} from 'ol/interaction/Draw.js';
import { Vector as VectorLayer } from 'ol/layer'
import { Vector as VectorSource } from 'ol/source'
import GeoJSON from 'ol/format/GeoJSON'


export default {
  name: 'AOIDefinitionComponent',
  emits: ['step-completed'],
  setup(props, { emit }) {
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const $q = useQuasar()

    const isDrawing = ref(false)
    const aoiDrawn = ref(false)

    let drawInteraction
    let vectorLayer

    onMounted(() => {
      if (mapStore.mapInitialized) {
        initializeVectorLayer()
        if (projectStore.currentProject && mapStore.aoi) {
          console.log("Displaying AOI from AOIDefinition")
          mapStore.displayAOI(mapStore.aoi)
          aoiDrawn.value = true
        }
      }
    })

    onUnmounted(() => {
      if (drawInteraction && projectStore.map) {
        mapStore.map.removeInteraction(drawInteraction)
      }
      if (vectorLayer && projectStore.map) {
        mapStore.map.removeLayer(vectorLayer)
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
      mapStore.map.addLayer(vectorLayer)
    }

    watch(() => mapStore.mapInitialized, (initialized) => {
      if (initialized) {
        initializeVectorLayer()
      }
    })


    const startDrawingAOI = () => {
      isDrawing.value = true
      drawInteraction = new Draw({
        source: vectorLayer.getSource(),
        type: 'Circle',
        geometryFunction: createBox()
      })

      drawInteraction.on('drawend', (event) => {
        isDrawing.value = false
        aoiDrawn.value = true
        mapStore.map.removeInteraction(drawInteraction)
      })

      mapStore.map.addInteraction(drawInteraction)
    }

    const clearAOI = () => {
      vectorLayer.getSource().clear()
      aoiDrawn.value = false
      aoiName.value = ''
    }

    const saveAOI = async () => {
      if (!aoiDrawn.value) return

      const feature = vectorLayer.getSource().getFeatures()[0]
      const geojson = new GeoJSON().writeFeatureObject(feature)

      try {
        await mapStore.setProjectAOI(geojson)

        $q.notify({
          color: 'positive',
          message: 'AOI saved successfully',
          icon: 'check'
        })

        emit('step-completed')
      } catch (error) {
        console.error('Error saving AOI:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to save AOI',
          icon: 'error'
        })
      }
    }

    return {
      isDrawing,
      aoiDrawn,
      startDrawingAOI,
      clearAOI,
      saveAOI,
      mapInitialized: mapStore.mapInitialized
    }
  }
}
</script>