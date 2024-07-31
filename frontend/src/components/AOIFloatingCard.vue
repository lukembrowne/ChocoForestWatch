<template>
    <q-card class="aoi-floating-card">
        <q-card-section>
            <div class="text-h6">Define Area of Interest</div>
            <p>Please draw the Area of Interest (AOI) for your project on the map.</p>
        </q-card-section>

        <q-card-actions align="center" class="q-gutter-md">
            <q-btn label="Draw AOI" color="primary" icon="create" @click="startDrawingAOI" :disable="isDrawing" />
            <q-btn label="Clear AOI" color="negative" icon="clear" @click="clearAOI" :disable="!aoiDrawn" />
            <q-btn label="Save AOI" color="positive" icon="save" @click="saveAOI" :disable="!aoiDrawn" />
        </q-card-actions>
    </q-card>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useQuasar } from 'quasar'
import Draw, {
  createBox,
} from 'ol/interaction/Draw.js';import { Vector as VectorLayer } from 'ol/layer'
import { Vector as VectorSource } from 'ol/source'
import GeoJSON from 'ol/format/GeoJSON'

export default {
    name: 'AOIFloatingCard',
    setup() {
        const projectStore = useProjectStore()
        const mapStore = useMapStore()
        const $q = useQuasar()

        const isDrawing = ref(false)
        const aoiDrawn = ref(false)

        let drawInteraction
        let vectorLayer

        onMounted(() => {
            initializeVectorLayer()
        })

        onUnmounted(() => {
            if (drawInteraction && mapStore.map) {
                mapStore.map.removeInteraction(drawInteraction)
            }
            if (vectorLayer && mapStore.map) {
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
        }

        const saveAOI = async () => {
            if (!aoiDrawn.value) return

            const feature = vectorLayer.getSource().getFeatures()[0]
            const geojson = new GeoJSON().writeFeatureObject(feature)

            try {
                await mapStore.setProjectAOI(geojson)
                projectStore.currentProject.aoi = geojson

                $q.notify({
                    color: 'positive',
                    message: 'AOI saved successfully',
                    icon: 'check'
                })
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
            saveAOI
        }
    }
}
</script>

<style lang="scss">
.aoi-floating-card {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 400px;
    max-width: 90%;
    z-index: 1000;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    background-color: white;
}
</style>