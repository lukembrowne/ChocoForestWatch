<template>
  <div class="drawing-controls">
    <q-card class="control-card">
      <!-- Drawing Mode Controls -->
      <q-card-section class="section-header">
        <div class="row items-center">
          <div class="text-subtitle1">{{ t('drawing.title') }}</div>
          <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
            <q-tooltip>{{ t('drawing.tooltips.controls') }}</q-tooltip>
          </q-btn>
        </div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <!-- Main Controls Row -->
        <div class="row q-col-gutter-sm">
          <div class="col-12">
            <div class="row q-col-gutter-sm items-center">
              <!-- Drawing Mode Buttons -->
              <div class="col">
                <q-btn-group spread>
                  <q-btn
                    :color="interactionMode === 'draw' ? 'primary' : 'white'"
                    :text-color="interactionMode === 'draw' ? 'white' : 'black'"
                    icon="create"
                    @click="setInteractionMode('draw')"
                    dense
                  >
                    <q-tooltip>{{ t('drawing.modes.draw') }}</q-tooltip>
                  </q-btn>
                  <q-btn
                    :color="interactionMode === 'pan' ? 'primary' : 'white'"
                    :text-color="interactionMode === 'pan' ? 'white' : 'black'"
                    icon="pan_tool"
                    @click="setInteractionMode('pan')"
                    dense
                  >
                    <q-tooltip>{{ t('drawing.modes.pan') }}</q-tooltip>
                  </q-btn>
                  <q-btn
                    :color="interactionMode === 'zoom_in' ? 'primary' : 'white'"
                    :text-color="interactionMode === 'zoom_in' ? 'white' : 'black'"
                    icon="zoom_in"
                    @click="setInteractionMode('zoom_in')"
                    dense
                  >
                    <q-tooltip>{{ t('drawing.modes.zoomIn') }}</q-tooltip>
                  </q-btn>
                  <q-btn
                    :color="interactionMode === 'zoom_out' ? 'primary' : 'white'"
                    :text-color="interactionMode === 'zoom_out' ? 'white' : 'black'"
                    icon="zoom_out"
                    @click="setInteractionMode('zoom_out')"
                    dense
                  >
                    <q-tooltip>{{ t('drawing.modes.zoomOut') }}</q-tooltip>
                  </q-btn>
                </q-btn-group>
              </div>

              <!-- Drawing Mode Toggle -->
              <div class="col-auto">
                <q-btn
                  :icon="drawingMode === 'square' ? 'crop_square' : 'gesture'"
                  :color="drawingMode === 'square' ? 'primary' : 'secondary'"
                  round
                  dense
                  @click="toggleDrawingMode"
                >
                  <q-tooltip>
                    {{ drawingMode === 'square' ? t('drawing.options.squareMode') : t('drawing.options.freehandMode') }}
                  </q-tooltip>
                </q-btn>
              </div>

              <!-- Polygon Size Button (only shown in square mode) -->
              <div class="col-auto" v-if="drawingMode === 'square'">
                <q-btn round dense color="grey-6" icon="straighten">
                  <q-tooltip>{{ t('drawing.options.polygonSize') }}</q-tooltip>
                  <q-menu anchor="bottom middle" self="top middle" class="polygon-size-menu">
                    <div class="q-pa-md">
                      <div class="text-subtitle2 q-mb-sm">{{ t('drawing.options.squareSize') }}</div>
                      <div class="row items-center q-gutter-sm">
                        <q-slider
                          v-model="polygonSize"
                          :min="10"
                          :max="500"
                          :step="10"
                          label
                          label-always
                          color="primary"
                          @update:model-value="updatePolygonSize"
                          class="col"
                        />
                        <div class="text-caption text-grey-8 q-ml-sm">
                          {{ polygonSize }}m × {{ polygonSize }}m
                        </div>
                      </div>
                    </div>
                  </q-menu>
                </q-btn>
              </div>
            </div>
          </div>

          <!-- Class Selection -->
          <div class="col-12 q-mt-md">
            <div class="row items-center q-mb-sm">
              <div class="text-subtitle1">{{ t('drawing.classes.title') }}</div>
              <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
                <q-tooltip>{{ t('drawing.tooltips.classes') }}</q-tooltip>
              </q-btn>
            </div>
            <div class="row q-col-gutter-sm">
              <div 
                v-for="(className, index) in projectClasses"
                :key="className"
                class="col-4"
              >
                <q-btn
                  :label="`${className} (${index + 1})`"
                  :color="selectedClass === className ? 'primary' : 'white'"
                  :text-color="selectedClass === className ? 'white' : 'black'"
                  @click="setClassLabel(className)"
                  class="full-width text-no-wrap"
                  dense
                  no-caps
                >
                  <q-tooltip>{{ t('drawing.tooltips.selectClass', { class: className, number: index + 1 }) }}</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>

          <!-- Polygon Management -->
          <div class="col-12 q-mt-md">
            <div class="row items-center q-mb-sm">
              <div class="text-subtitle1">{{ t('drawing.management.title') }}</div>
              <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
                <q-tooltip>{{ t('drawing.tooltips.management') }}</q-tooltip>
              </q-btn>
            </div>
            <div class="row q-col-gutter-sm">
              <div class="col-2">
                <q-btn class="full-width" icon="undo" @click="undoLastDraw" :disable="interactionMode !== 'draw'" dense>
                  <q-tooltip>{{ t('drawing.management.undo') }}</q-tooltip>
                </q-btn>
              </div>
              <div class="col-2">
                <q-btn class="full-width" icon="save" @click="saveTrainingPolygons" dense>
                  <q-tooltip>{{ t('drawing.management.save') }}</q-tooltip>
                </q-btn>
              </div>
              <div class="col-2">
                <q-btn class="full-width" icon="delete_sweep" @click="clearDrawnPolygons" dense>
                  <q-tooltip>{{ t('drawing.management.clear') }}</q-tooltip>
                </q-btn>
              </div>
              <div class="col-2">
                <q-btn class="full-width" icon="delete" @click="deleteSelectedFeature" dense>
                  <q-tooltip>{{ t('drawing.management.delete') }}</q-tooltip>
                </q-btn>
              </div>
              <div class="col-2">
                <q-btn class="full-width" icon="download" @click="downloadPolygons" dense>
                  <q-tooltip>{{ t('drawing.management.download') }}</q-tooltip>
                </q-btn>
              </div>
              <div class="col-2">
                <q-btn class="full-width" icon="upload_file" @click="triggerFileUpload" dense>
                  <q-tooltip>{{ t('drawing.management.load') }}</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <input type="file" ref="fileInput" style="display: none" accept=".geojson" @change="loadPolygons" />
  </div>
</template>

<script>
import { computed, onMounted, onUnmounted, watch, ref } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'

export default {
    name: 'DrawingControlsCard',
    setup() {
        const mapStore = useMapStore()
        const projectStore = useProjectStore()
        const { t } = useI18n()
        const $q = useQuasar()
        const drawnPolygons = computed(() => mapStore.drawnPolygons)
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)

        const fileInput = ref(null)

        onMounted(async () => {
            window.addEventListener('keydown', handleKeyDown);

            if (projectClasses.value.length > 0 && !selectedClass.value) {
                selectedClass.value = projectClasses.value[0].name
            }
        })

        onUnmounted(() => {
            window.removeEventListener('keydown', handleKeyDown);
            mapStore.setInteractionMode('pan');
        })

        const polygonSize = computed({
            get: () => mapStore.polygonSize,
            set: (value) => mapStore.setPolygonSize(value)
        })

        const updatePolygonSize = (value) => {
            mapStore.setPolygonSize(value)
        }


        const interactionMode = computed({
            get: () => mapStore.interactionMode,
            set: (value) => mapStore.setInteractionMode(value)
        })

        const selectedClass = computed({
            get: () => mapStore.selectedClass,
            set: (value) => mapStore.setClassLabel(value)
        })

        const projectClasses = computed(() => {
            return projectStore.currentProject?.classes?.map(cls => cls.name) || []
        })

        const setInteractionMode = (mode) => {
            mapStore.setInteractionMode(mode)
        }

        const setClassLabel = (label) => {
            mapStore.setClassLabel(label)
        }

        const undoLastDraw = () => {
            mapStore.undoLastDraw()
        }

        const handleKeyDown = (event) => {

            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return; // Ignore keyboard events when typing in input fields
            }

            const numKey = parseInt(event.key);

            if (numKey && numKey > 0 && numKey <= projectStore.projectClasses.length) {
                selectedClass.value = projectStore.projectClasses[numKey - 1]['name'];
                mapStore.setClassLabel(selectedClass.value);
                mapStore.setInteractionMode('draw');
            } else if ((event.key === 'Delete' || event.key === 'Backspace')) {
                mapStore.deleteSelectedFeature();
            } else if (event.key === 'm') {
                mapStore.setInteractionMode('pan');
            } else if ((event.ctrlKey || event.metaKey) && event.key === 'z') {
                event.preventDefault(); // Prevent the default undo behavior if necessary
                mapStore.undoLastDraw();
            } else if ((event.ctrlKey || event.metaKey) && event.key === 's') {
                event.preventDefault(); // Prevent the default undo behavior if necessary
                saveTrainingPolygons();
            } else if (event.key === 'z') {
                mapStore.setInteractionMode('zoom_in');
            } else if (event.key === 'x') {
                mapStore.setInteractionMode('zoom_out');
            } else if (event.key === 'd') {
                mapStore.setInteractionMode('draw');
            } else if (event.key == 'Escape') {
                mapStore.setInteractionMode('pan');
                mapStore.stopDrawing();
            } else if (event.key === 'f') {
                toggleDrawingMode();
            }
        };

        watch(drawnPolygons, () => {
            drawnPolygons.value = mapStore.drawnPolygons
        }, { immediate: true });

        watch(() => projectClasses.value, (newClasses) => {
            if (newClasses.length > 0 && !selectedClass.value) {
                selectedClass.value = newClasses[0]
            }
        }, { immediate: true })

        const saveTrainingPolygons = async () => {
            try {
                await mapStore.saveCurrentTrainingPolygons(selectedBasemapDate.value);
                // Show success notification
                $q.notify({
                    type: 'positive',
                    message: t('drawing.notifications.dateIncluded')
                });
            } catch (error) {
                // Show error notification
                $q.notify({
                    type: 'negative',
                    message: t('drawing.notifications.saveError')
                });
            }
        };

        const clearDrawnPolygons = () => {
                $q.dialog({
                    title: t('drawing.dialogs.clear.title'),
                    message: t('drawing.dialogs.clear.message'),
                    cancel: true,
                    persistent: true
                }).onOk(() => {
                    mapStore.clearDrawnPolygons(true)
                });
        }

        const isCurrentDateExcluded = computed(() => {
            return projectStore.isDateExcluded(mapStore.selectedBasemapDate);
        });

        const toggleExcludeCurrentDate = async () => {
            try {
                await projectStore.toggleExcludedDate(mapStore.selectedBasemapDate);
                $q.notify({
                    type: 'positive',
                    message: isCurrentDateExcluded.value
                        ? t('drawing.notifications.dateIncluded')
                        : t('drawing.notifications.dateExcluded')
                });
            } catch (error) {
                $q.notify({
                    type: 'negative',
                    message: t('drawing.notifications.dateToggleError')
                });
            }
        };

        const deleteSelectedFeature = () => {
            if (mapStore.selectedFeature) {
                $q.dialog({
                    title: t('drawing.dialogs.delete.title'),
                    message: t('drawing.dialogs.delete.message'),
                    cancel: true,
                    persistent: true
                }).onOk(() => {
                    mapStore.deleteSelectedFeature();
                });
            } else {
                $q.notify({
                    type: 'negative',
                    message: t('drawing.notifications.noFeatureSelected')
                });
            }
        };

        const downloadPolygons = () => {
            const polygons = mapStore.drawnPolygons.map(polygon => ({
                ...polygon,
                properties: {
                    ...polygon.properties,
                    basemapDate: mapStore.selectedBasemapDate
                }
            }));
            const geojson = {
                type: "FeatureCollection",
                features: polygons
            };
            const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: "application/geo+json" });
            const url = URL.createObjectURL(blob);

            // Retrieve and sanitize the project name
            const projectNameRaw = projectStore.currentProject?.name || 'unknown_project';
            const projectName = projectNameRaw.replace(/[<>:"\/\\|?*\x00-\x1F]/g, '_').replace(/\s+/g, '_');

            const link = document.createElement('a');
            link.href = url;
            link.download = `training_polygons_${projectName}_${mapStore.selectedBasemapDate}.geojson`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        };

        const triggerFileUpload = () => {
            fileInput.value.click()
        };

        const loadPolygons = (event) => {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const geojson = JSON.parse(e.target.result);
                    if (geojson.type !== 'FeatureCollection') {
                        throw new Error('Invalid GeoJSON format');
                    }
                    geojson.features.forEach(feature => {
                        if (feature.geometry && feature.properties) {
                            mapStore.addPolygon({
                                ...feature,
                                properties: {
                                    ...feature.properties,
                                    basemapDate: feature.properties.basemapDate || mapStore.selectedBasemapDate
                                }
                            });
                        }
                    });
                    $q.notify({
                        type: 'positive',
                        message: t('drawing.notifications.polygonsLoaded')
                    });
                } catch (error) {
                    console.error('Error loading GeoJSON:', error);
                    $q.notify({
                        type: 'negative',
                        message: t('drawing.notifications.loadError')
                    });
                }
            };
            reader.readAsText(file);
            // Reset the file input
            event.target.value = null;
        };

        const drawingMode = computed(() => mapStore.drawingMode)

        const toggleDrawingMode = () => {
            mapStore.toggleDrawingMode()
        }

        return {
            interactionMode,
            selectedClass,
            projectClasses,
            setInteractionMode,
            setClassLabel,
            undoLastDraw,
            drawnPolygons,
            handleKeyDown,
            selectedBasemapDate,
            polygonSize,
            updatePolygonSize,
            saveTrainingPolygons,
            clearDrawnPolygons,
            isCurrentDateExcluded,
            toggleExcludeCurrentDate,
            deleteSelectedFeature,
            downloadPolygons,
            triggerFileUpload,
            loadPolygons,
            fileInput,
            drawingMode,
            toggleDrawingMode,
            t
        }
    }
}
</script>

<style lang="scss" scoped>
.drawing-controls {
  width: 100%;
}

.control-card {
  background: white;
  box-shadow: none;
  border-radius: 0;
}


.q-btn {
  min-height: 32px;
  
  &.full-width {
    padding: 4px 8px;
    font-size: 0.8rem;
  }
}

/* Add smooth transitions */
.q-btn {
  transition: all 0.3s ease;
}

.text-subtitle2 {
  font-size: 0.9rem;
  color: #2c3e50;
}

.polygon-size-menu {
  min-width: 300px;
  
  :deep(.q-slider__pin) {
    top: -20px;
  }
  
  :deep(.q-slider__pin-value-marker) {
    min-width: 24px;
    height: 24px;
    font-size: 12px;
    padding: 2px;
  }
}

</style>
