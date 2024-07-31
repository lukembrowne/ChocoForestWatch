<template>
    <q-card class="aoi-floating-card">
        <q-card-section>
            <div class="text-h6">Define Area of Interest</div>
            <p>Please draw the Area of Interest (AOI) for your project on the map or upload a GeoJSON file.</p>
        </q-card-section>

        <q-card-actions align="center" class="q-gutter-md">
            <q-btn label="Draw AOI" color="primary" icon="create" @click="startDrawingAOI" :disable="isDrawing" />
            <q-btn label="Upload GeoJSON" color="secondary" icon="upload_file" @click="triggerFileUpload" />
            <q-btn label="Clear AOI" color="negative" icon="clear" @click="clearAOI" :disable="!aoiDrawn" />
            <q-btn label="Save AOI" color="positive" icon="save" @click="saveAOI" :disable="!aoiDrawn" />
        </q-card-actions>

        <input type="file" ref="fileInput" style="display: none" accept=".geojson,application/geo+json"
            @change="handleFileUpload" />
    </q-card>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useQuasar } from 'quasar'
import Draw, {
    createBox,
} from 'ol/interaction/Draw.js'; import { Vector as VectorLayer } from 'ol/layer'
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
        const fileInput = ref(null)

        let drawInteraction
        let vectorLayer
        let vectorSource

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
            vectorSource = new VectorSource()
            vectorLayer = new VectorLayer({
                source: vectorSource,
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

            // Clear existing features before starting a new draw
            vectorSource.clear()
            aoiDrawn.value = false

            drawInteraction = new Draw({
                source: vectorLayer.getSource(),
                type: 'Circle',
                geometryFunction: createBox()
            })

            drawInteraction.on('drawend', (event) => {
                isDrawing.value = false
                aoiDrawn.value = true
                vectorSource.clear()
                mapStore.map.removeInteraction(drawInteraction)

            })

            mapStore.map.addInteraction(drawInteraction)
        }

        const clearAOI = () => {
            vectorSource.clear()
            aoiDrawn.value = false
        }

        const saveAOI = async () => {
            if (!aoiDrawn.value) return

            const feature = vectorLayer.getSource().getFeatures()[0]
            const geojson = new GeoJSON().writeFeatureObject(feature)

            try {
                await mapStore.setProjectAOI(geojson)

                // Load project to make layer list
                await projectStore.loadProject(projectStore.currentProject.id)

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

        const triggerFileUpload = () => {
            fileInput.value.click()
        }

        const handleFileUpload = (event) => {
            const file = event.target.files[0]
            if (!file) return

            const reader = new FileReader()
            reader.onload = (e) => {
                try {
                    const geojson = JSON.parse(e.target.result)
                    const features = new GeoJSON().readFeatures(geojson, {
                        featureProjection: mapStore.map.getView().getProjection()
                    })

                    // Clear existing features and add only the first feature from the file
                    clearAOI()
                    if (features.length > 0) {
                        vectorSource.addFeature(features[0])
                        aoiDrawn.value = true

                        // Zoom to the extent of the uploaded feature
                        const extent = vectorSource.getExtent()
                        mapStore.map.getView().fit(extent, { padding: [50, 50, 50, 50] })

                        $q.notify({
                            color: 'positive',
                            message: 'GeoJSON file uploaded successfully',
                            icon: 'check'
                        })
                    } else {
                        throw new Error('No valid features found in the GeoJSON file')
                    }
                } catch (error) {
                    console.error('Error parsing GeoJSON:', error)
                    $q.notify({
                        color: 'negative',
                        message: 'Failed to parse GeoJSON file',
                        icon: 'error'
                    })
                }
            }
            reader.readAsText(file)
        }


        return {
            isDrawing,
            aoiDrawn,
            startDrawingAOI,
            clearAOI,
            saveAOI,
            triggerFileUpload,
            handleFileUpload,
            fileInput
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