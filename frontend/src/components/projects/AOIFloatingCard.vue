<template>
  <div class="aoi-container">
    <q-card class="aoi-card">
      <q-card-section>
        <div class="text-h6">Define Area of Interest</div>
        <p class="text-body2">Please draw the Area of Interest (AOI) for your project on the map or upload a GeoJSON file or .zipped Shapefile.</p>
        
        <div class="text-subtitle2 q-mt-md">Current AOI Size</div>
        <div class="text-body1">{{ aoiSizeHa.toFixed(2) }} ha</div>
        <q-badge v-if="aoiSizeHa > maxAoiSizeHa" color="negative" class="q-mt-sm">
          Warning: AOI size exceeds the maximum allowed ({{ maxAoiSizeHa }} ha)
        </q-badge>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <div class="text-subtitle2 q-mb-sm">Actions</div>
        <div class="column q-gutter-y-sm">
          <q-btn 
            label="Draw AOI" 
            color="primary" 
            icon="create" 
            @click="startDrawingAOI"
            class="full-width" 
          />
          <q-btn 
            label="Upload AOI file" 
            color="secondary" 
            icon="upload_file"
            @click="triggerFileUpload"
            class="full-width" 
          >
            <q-tooltip>Upload .geojson or zipped shapefile</q-tooltip>
          </q-btn>
          <q-btn 
            label="Clear AOI" 
            color="negative" 
            icon="clear" 
            @click="clearAOI"
            class="full-width" 
          />
          <q-btn 
            label="Save AOI" 
            color="positive" 
            icon="save" 
            @click="saveAOI" 
            :disable="!aoiDrawn"
            class="full-width" 
          />
        </div>
      </q-card-section>

      <input 
        type="file" 
        ref="fileInput" 
        style="display: none" 
        accept=".geojson,application/geo+json,.zip"
        @change="handleFileUpload" 
      />
    </q-card>
  </div>
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
    emits: ['aoi-saved', 'clearAOI'],
    
    setup(props, { emit }) { 
        const projectStore = useProjectStore()
        const mapStore = useMapStore()
        const $q = useQuasar()

        const isDrawing = ref(false)
        const aoiDrawn = ref(false)
        const fileInput = ref(null)
        const aoiSizeHa = ref(0)
        const maxAoiSizeHa = ref(10000)
        const vectorSource = ref(null)
        const vectorLayer = ref(null)
        let drawInteraction = null

        onMounted(() => {
            initializeVectorLayer()
        })

        onUnmounted(() => {
            if (drawInteraction && mapStore.map) {
                mapStore.map.removeInteraction(drawInteraction)
            }
            if (vectorLayer.value && mapStore.map) {
                mapStore.map.removeLayer(vectorLayer.value)
            }
        })

        const initializeVectorLayer = () => {
            console.log("Initializing vector layer in AOIFloatingCard")

            if (vectorSource.value) {
                vectorSource.value.clear()
                return
            }

            vectorSource.value = new VectorSource()
            vectorLayer.value = new VectorLayer({
                source: vectorSource.value,
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
            mapStore.map.addLayer(vectorLayer.value)
        }

        const startDrawingAOI = () => {
            isDrawing.value = true

            // Clear existing features before starting a new draw
            if (vectorSource.value) {
                vectorSource.value.clear()
            }
            aoiDrawn.value = false

            drawInteraction = new Draw({
                source: vectorLayer.value.getSource(),
                type: 'Circle',
                geometryFunction: createBox()
            })

            drawInteraction.on('drawend', (event) => {
                const feature = event.feature;
                const area = getArea(feature.getGeometry()) / 10000;
                console.log("Area of AOI: ", area)
                aoiSizeHa.value = area
                if (area > maxAoiSizeHa.value) {
                    vectorSource.value.clear()
                    aoiDrawn.value = false;
                    $q.notify({
                        color: 'negative',
                        message: `Drawn AOI is too large. Maximum allowed area is ${maxAoiSizeHa.value} ha`,
                        icon: 'error'
                    });
                } else {
                    isDrawing.value = false;
                    aoiDrawn.value = true;
                }

                mapStore.map.removeInteraction(drawInteraction);
            });

            mapStore.map.addInteraction(drawInteraction)
        }

        const clearAOI = () => {
            vectorSource.value.clear()
            aoiDrawn.value = false
            emit('clearAOI')
        }

        const saveAOI = async () => {
            if (!aoiDrawn.value) {
                console.log("No AOI drawn, returning early")
                return
            }

            const feature = vectorLayer.value.getSource().getFeatures()[0]
            if (!feature) {
                console.log("No feature found in vector source")
                return
            }

            const geojson = new GeoJSON().writeFeatureObject(feature)

            try {
                console.log("About to save AOI to project...")
                // Don't await this - it seems to interfere with event emission
                mapStore.setProjectAOI(geojson)
                console.log("AOI saved to project successfully")

                // Emit event immediately
                const eventData = {
                    success: true,
                    area: aoiSizeHa.value,
                    timestamp: Date.now()
                }
                console.log('Emitting aoi-saved event with data:', eventData)
                emit('aoi-saved', eventData)

                $q.notify({
                    color: 'positive',
                    message: 'AOI saved successfully',
                    icon: 'check'
                })

            } catch (error) {
                console.error('Error in saveAOI:', error)
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
                vectorSource.value.addFeature(features[0]);

                // Add area to aoiSizeHa
                aoiSizeHa.value = getArea(features[0].getGeometry()) / 10000;

                const extent = vectorSource.value.getExtent();
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

<style lang="scss" scoped>
.aoi-container {
  height: calc(100vh - var(--app-header-height));
  overflow-y: auto;
}

.aoi-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 0;
  box-shadow: none;

  .q-card__section {
    padding: 16px;
  }

  p {
    margin: 8px 0;
  }
}

// Make buttons more compact but still readable
.q-btn {
  height: 36px;
  font-size: 0.875rem;
}
</style>