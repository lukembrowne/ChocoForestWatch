<template>
  <div class="aoi-container">
    <q-card class="aoi-card">
      <q-card-section>
        <div class="section-header q-mb-md">
          <div class="text-subtitle1">{{ t('projects.aoi.title')}}</div>
        </div>
        <div class="text-h6">{{  }}</div>
        
        <!-- Main description -->
        <div class="text-body2 description-text">
          {{ t('projects.aoi.description') }}
        </div>
        
        <!-- Additional explanation -->
        <div class="text-body2 description-text q-mt-md">
          {{ t('projects.aoi.explanation') }}
        </div>
        
        <!-- Size limits warning -->
        <div class="text-body2 description-text q-mt-md warning-text">
          {{ t('projects.aoi.limits') }}
        </div>
        
        <!-- Current size section -->
        <div class="section-header q-mt-lg">
          <div class="text-subtitle1">{{ t('projects.aoi.currentSize') }}</div>
          <div class="text-h6 size-value">{{ aoiSizeHa.toFixed(2) }} {{ t('projects.aoi.hectares') }}</div>
        </div>
        
        <q-badge v-if="aoiSizeHa > maxAoiSizeHa" color="negative" class="q-mt-sm">
          {{ t('projects.aoi.sizeWarning', { max: maxAoiSizeHa }) }}
        </q-badge>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <div class="section-header q-mb-md">
          <div class="text-subtitle1">{{ t('projects.aoi.actions') }}</div>
        </div>
        
        <div class="column q-gutter-y-sm">
          <q-btn 
            :label="t('projects.aoi.buttons.draw')"
            color="primary" 
            icon="create" 
            @click="startDrawingAOI"
          >
            <q-tooltip>{{ t('projects.aoi.tooltips.draw') }}</q-tooltip>
          </q-btn>
          <q-btn 
            :label="t('projects.aoi.buttons.upload')"
            color="secondary" 
            icon="upload_file"
            @click="triggerFileUpload"
          >
            <q-tooltip>{{ t('projects.aoi.tooltips.upload_aoi') }}</q-tooltip>
          </q-btn>
          <q-btn 
            :label="t('projects.aoi.buttons.clear')"
            color="negative" 
            icon="clear" 
            @click="clearAOI"
          >
            <q-tooltip>{{ t('projects.aoi.tooltips.clear') }}</q-tooltip>
          </q-btn>
          <q-btn 
            :label="t('projects.aoi.buttons.save')"
            color="positive" 
            icon="save" 
            @click="saveAOI" 
            :disable="!aoiDrawn"
          >
            <q-tooltip>{{ t('projects.aoi.tooltips.save') }}</q-tooltip>
          </q-btn>
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
import { useI18n } from 'vue-i18n'
import Draw, {
    createBox,
} from 'ol/interaction/Draw.js'; import { Vector as VectorLayer } from 'ol/layer'
import { Vector as VectorSource } from 'ol/source'
import GeoJSON from 'ol/format/GeoJSON'
import { Style, Fill, Stroke } from 'ol/style'
import shp from 'shpjs';
import { getArea } from 'ol/sphere'
import { transformExtent } from 'ol/proj'



export default {
    name: 'AOIFloatingCard',
    emits: ['aoi-saved', 'clearAOI'],
    
    setup(props, { emit }) { 
        const projectStore = useProjectStore()
        const mapStore = useMapStore()
        const $q = useQuasar()
        const { t } = useI18n()

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
            console.log("AOIFloatingCard unmounting...")
            if (drawInteraction) {
                console.log("Removing draw interaction on unmount:", drawInteraction)
                mapStore.map.removeInteraction(drawInteraction)
                const remainingInteractions = mapStore.map.getInteractions().getArray();
                console.log("Remaining interactions after unmount cleanup:", remainingInteractions)
            }
            if (vectorLayer.value) {
                console.log("Removing vector layer on unmount:", vectorLayer.value)
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
                const geometry = feature.getGeometry();
                
                // Check if the drawn AOI is within Ecuador
                if (!isWithinEcuador(geometry)) {
                    vectorSource.value.clear()
                    aoiDrawn.value = false
                    $q.notify({
                        color: 'negative',
                        message: t('projects.aoi.notifications.outsideEcuador'),
                        icon: 'error'
                    })
                    return
                }

                // Calculate area and continue with existing checks
                const area = getArea(geometry) / 10000;
                console.log("Area of AOI: ", area)
                aoiSizeHa.value = area
                
                if (area > maxAoiSizeHa.value) {
                    vectorSource.value.clear()
                    aoiDrawn.value = false
                    $q.notify({
                        color: 'negative',
                        message: t('projects.aoi.notifications.tooLarge', { max: maxAoiSizeHa.value }),
                        icon: 'error'
                    })
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
                // Remove drawing interaction if it exists
                if (drawInteraction) {
                    mapStore.map.getInteractions().remove(drawInteraction);
                    // Verify it was removed
                    const remainingInteractions = mapStore.map.getInteractions().getArray();
                    
                    // Double check and force remove if still present
                    const stillExists = remainingInteractions.includes(drawInteraction);
                    if (stillExists) {
                        console.log("Draw interaction still exists, forcing removal...")
                        remainingInteractions.forEach((interaction, index) => {
                            if (interaction instanceof Draw) {
                                mapStore.map.getInteractions().removeAt(index);
                            }
                        });
                    }
                    
                    drawInteraction = null
                }

                // Remove the vector layer
                if (vectorLayer.value) {
                    mapStore.map.removeLayer(vectorLayer.value)
                    vectorLayer.value = null
                }

                mapStore.setProjectAOI(geojson)
                console.log("AOI saved to project successfully")

                const eventData = {
                    success: true,
                    area: aoiSizeHa.value,
                    timestamp: Date.now()
                }
                console.log('Emitting aoi-saved event with data:', eventData)
                emit('aoi-saved', eventData)

                $q.notify({
                    color: 'positive',
                    message: t('projects.aoi.notifications.saved'),
                    icon: 'check'
                })

                emit('aoi-saved', { success: true, area: aoiSizeHa.value, timestamp: Date.now() })
            } catch (error) {
                console.error('Error in saveAOI:', error)
                $q.notify({
                    color: 'negative',
                    message: t('projects.aoi.notifications.saveFailed'),
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
                    message: t('projects.aoi.notifications.unsupportedFile'),
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
                        message: t('projects.aoi.notifications.uploadFailed', { fileType: 'GeoJSON' }),
                        icon: 'error'
                    });
                }
            };
            reader.readAsText(file);
        };

        const handleShapefile = async (file) => {
            try {
                if (file.type === "application/zip" || file.name.endsWith('.zip')) {
                    const arrayBuffer = await file.arrayBuffer();
                    const geojson = await shp(arrayBuffer);
                    processGeoJSON(geojson);
                }
            } catch (error) {
                console.error('Error parsing Shapefile:', error);
                $q.notify({
                    color: 'negative',
                    message: t('projects.aoi.notifications.uploadFailed', { fileType: 'Shapefile' }),
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
                const feature = features[0]
                
                // Check if the uploaded AOI is within Ecuador
                if (!isWithinEcuador(feature.getGeometry())) {
                    $q.notify({
                        color: 'negative',
                        message: t('projects.aoi.notifications.outsideEcuador'),
                        icon: 'error'
                    })
                    return
                }

                // Continue with existing functionality
                vectorSource.value.addFeature(feature)
                aoiSizeHa.value = getArea(feature.getGeometry()) / 10000

                const extent = vectorSource.value.getExtent()
                mapStore.map.getView().fit(extent, { padding: [50, 50, 50, 50] })

                if (aoiSizeHa.value > maxAoiSizeHa.value) {
                    aoiDrawn.value = false;
                    $q.notify({
                        color: 'negative',
                        message: t('projects.aoi.notifications.tooLarge', { max: maxAoiSizeHa.value }),
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

        // Define Ecuador's bounding box in WGS84 (EPSG:4326)
        const ecuadorBounds = {
            minLon: -81.5,
            maxLon: -75.0,
            minLat: -5.0,
            maxLat: 1.5
        }

        const isWithinEcuador = (geometry) => {
            // Get the extent of the drawn feature in map projection (usually EPSG:3857)
            const extent = geometry.getExtent()
            
            // Transform the extent to WGS84 (EPSG:4326) for comparison
            const wgs84Extent = transformExtent(extent, 'EPSG:3857', 'EPSG:4326')
            
            // Check if the extent is within Ecuador's bounds
            return (
                wgs84Extent[0] >= ecuadorBounds.minLon &&
                wgs84Extent[2] <= ecuadorBounds.maxLon &&
                wgs84Extent[1] >= ecuadorBounds.minLat &&
                wgs84Extent[3] <= ecuadorBounds.maxLat
            )
        }

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
            maxAoiSizeHa,
            t
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


.description-text {
  line-height: 1.5;
  color: #000000;
  margin-top: 8px;
}

.warning-text {
  color: #f57c00;
  font-weight: 500;
}

</style>