<template>
    <q-card class="aoi-floating-card">
        <q-card-section>
            <div class="text-h6">Define Area of Interest</div>
            <p>Please draw the Area of Interest (AOI) for your project on the map or upload a GeoJSON file or .zipped Shapefile.</p>
            <p>Current AOI Size: {{ aoiSizeHa.toFixed(2) }} ha</p>
            <p v-if="aoiSizeHa > maxAoiSizeHa">Warning: AOI size exceeds the maximum allowed ({{ maxAoiSizeHa }} ha)</p>
        </q-card-section>

        <q-card-actions align="center" class="q-gutter-md">
            <q-btn label="Draw AOI" color="primary" icon="create" @click="startDrawingAOI" />
            <q-btn label="Upload AOI file (.geojson, zipped shapefile)" color="secondary" icon="upload_file"
                @click="triggerFileUpload" />
            <q-btn label="Clear AOI" color="negative" icon="clear" @click="clearAOI"/>
            <q-btn label="Save AOI" color="positive" icon="save" @click="saveAOI" :disable="!aoiDrawn" />
        </q-card-actions>

        <input type="file" ref="fileInput" style="display: none" accept=".geojson,application/geo+json,.zip"
            @change="handleFileUpload" />
    </q-card>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import { useQuasar } from 'quasar'
import Draw, {
    createBox,
} from 'ol/interaction/Draw.js'; import { Vector as VectorLayer } from 'ol/layer'
import { Vector as VectorSource } from 'ol/source'
import GeoJSON from 'ol/format/GeoJSON'
import { Style, Fill, Stroke } from 'ol/style'
import shp from 'shpjs';
import { getArea } from 'ol/sphere'



export default {
    name: 'AOIFloatingCard',
    setup() {
        const projectStore = useProjectStore()
        const mapStore = useMapStore()
        const $q = useQuasar()

        const isDrawing = ref(false)
        const aoiDrawn = ref(false)
        const fileInput = ref(null)
        const aoiSizeHa = ref(0)
        const maxAoiSizeHa = ref(10000) // Maximum AOI size in ha


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
                title: "Area of Interest",
                visible: true,
                id: 'area-of-interest',
                zIndex: 100,
                style: new Style({
                    fill: new Fill({
                        color: 'rgba(255, 255, 255, 0)'
                    }),
                    stroke: new Stroke({
                        color: '#000000',
                        width: 2
                    })
                }),
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
                const feature = event.feature;
                const area = getArea(feature.getGeometry()) / 10000; // Convert to ha
                console.log("Area of AOI: ", area)
                aoiSizeHa.value = area
                if (area > maxAoiSizeHa.value) {
                    vectorSource.clear()
                    aoiDrawn.value = false;
                    $q.notify({
                        color: 'negative',
                        message: `Drawn AOI is too large. Maximum allowed area is ${maxAoiSizeHa.value} ha`,
                        icon: 'error'
                    });

                } else {
                    console.log("Drawing finished")
                    console.log("Feature: ", feature)
                    isDrawing.value = false;
                    aoiDrawn.value = true;
                    vectorSource.clear()
                }

                mapStore.map.removeInteraction(drawInteraction);
            });

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
                    message: 'AOI saved successfully and imagery download initiated in the background',
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
            const file = event.target.files[0];
            if (!file) return;

            if (file.name.endsWith('.geojson')) {
                handleGeoJSON(file);
            } else if (file.name.endsWith('.zip')) {
                handleShapefile(file);
            } else {
                $q.notify({
                    color: 'negative',
                    message: 'Unsupported file type. Please upload a GeoJSON or a Zipped Shapefile.',
                    icon: 'error'
                });
            }
        };

        const handleGeoJSON = (file) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const geojson = JSON.parse(e.target.result);
                    processGeoJSON(geojson);
                } catch (error) {
                    console.error('Error parsing GeoJSON:', error);
                    $q.notify({
                        color: 'negative',
                        message: 'Failed to parse GeoJSON file',
                        icon: 'error'
                    });
                }
            };
            reader.readAsText(file);
        };

        const handleShapefile = async (file) => {
            try {
                // Check if it's a zip file
                if (file.type === "application/zip" || file.name.endsWith('.zip')) {
                    const arrayBuffer = await file.arrayBuffer();
                    const geojson = await shp(arrayBuffer);
                    processGeoJSON(geojson);
                }
            } catch (error) {
                console.error('Error parsing Shapefile:', error);
                $q.notify({
                    color: 'negative',
                    message: 'Failed to parse Shapefile: ' + error.message,
                    icon: 'error'
                });
            }
        };

        const processGeoJSON = (geojson) => {
            const features = new GeoJSON().readFeatures(geojson, {
                featureProjection: mapStore.map.getView().getProjection()
            });

            clearAOI();
            if (features.length > 0) {
                vectorSource.addFeature(features[0]);

                // Add area to aoiSizeHa
                aoiSizeHa.value = getArea(features[0].getGeometry()) / 10000;

                const extent = vectorSource.getExtent();
                mapStore.map.getView().fit(extent, { padding: [50, 50, 50, 50] });

                if (aoiSizeHa.value > maxAoiSizeHa.value) {
                    aoiDrawn.value = false;
                    $q.notify({
                        color: 'negative',
                        message: `Uploaded AOI is too large. Maximum allowed area is ${maxAoiSizeHa.value} ha`,
                        icon: 'error'
                    });

                } else {
                    aoiDrawn.value = true;
                    $q.notify({
                        color: 'positive',
                        message: 'File uploaded successfully',
                        icon: 'check'
                    });
                }
            } else {
                throw new Error('No valid features found in the file');
            }
        };


        return {
            isDrawing,
            aoiDrawn,
            startDrawingAOI,
            clearAOI,
            saveAOI,
            triggerFileUpload,
            handleFileUpload,
            fileInput,
            aoiSizeHa,
            maxAoiSizeHa
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