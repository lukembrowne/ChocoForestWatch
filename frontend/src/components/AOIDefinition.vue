<template>
  <div>
    <h6>Define Area of Interest</h6>
    <p v-if="!aoiDrawn">Please draw your Area of Interest on the map.</p>
    <q-btn label="Draw AOI" color="primary" @click="startDrawingAOI" :disable="isDrawing" />
    <q-btn label="Clear AOI" color="negative" @click="clearAOI" :disable="!aoiDrawn" class="q-ml-sm" />
    
    <q-input v-if="aoiDrawn" v-model="aoiName" label="AOI Name" class="q-mt-md" />
    
    <q-btn v-if="aoiDrawn" label="Save AOI" color="positive" @click="saveAOI" :disable="!aoiName" class="q-mt-md" />
    
    <q-banner v-if="aoiDrawn && !aoiName" class="bg-yellow-1 text-grey-9 q-mt-md">
      Please provide a name for your Area of Interest before saving.
    </q-banner>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
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
    const $q = useQuasar()
    
    const isDrawing = ref(false)
    const aoiDrawn = ref(false)
    const aoiName = ref('')
    
    let drawInteraction
    let vectorLayer

    onMounted(() => {
      if (projectStore.mapInitialized) {
        initializeVectorLayer()
        if (projectStore.currentProject?.aoi) {
          loadExistingAOI()
        }
      }
    })

  onUnmounted(() => {
      if (drawInteraction && projectStore.map) {
        projectStore.map.removeInteraction(drawInteraction)
      }
      if (vectorLayer && projectStore.map) {
        projectStore.map.removeLayer(vectorLayer)
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
      projectStore.map.addLayer(vectorLayer)
    }

    watch(() => projectStore.mapInitialized, (initialized) => {
      if (initialized) {
        initializeVectorLayer()
        if (projectStore.currentProject?.aoi) {
          loadExistingAOI()
        }
      }
    })

    const loadExistingAOI = () => {
      const format = new GeoJSON()
      const feature = format.readFeature(projectStore.currentProject.aoi, {
        featureProjection: 'EPSG:3857'
      })
      vectorLayer.getSource().addFeature(feature)
      aoiDrawn.value = true
      aoiName.value = projectStore.currentProject.aoiName || ''
    }

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
        projectStore.map.removeInteraction(drawInteraction)
      })

      projectStore.map.addInteraction(drawInteraction)
    }

    const clearAOI = () => {
      vectorLayer.getSource().clear()
      aoiDrawn.value = false
      aoiName.value = ''
    }

    const saveAOI = async () => {
      if (!aoiDrawn.value || !aoiName.value) return

      const feature = vectorLayer.getSource().getFeatures()[0]
      const geojson = new GeoJSON().writeFeatureObject(feature)

      try {
        await projectStore.setProjectAOI({
          name: aoiName.value,
          geometry: geojson
        })

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
      aoiName,
      startDrawingAOI,
      clearAOI,
      saveAOI,
      mapInitialized: projectStore.mapInitialized
    }
  }
}
</script>