<template>
    <div class="drawing-controls q-pa-sm">
      <div class="text-subtitle1 q-mb-sm">Drawing Controls</div>
      <div class="row q-gutter-xs">
        <q-btn-toggle
          v-model="interactionMode"
          :options="[
            { label: 'Draw', value: 'draw', icon: 'create' },
            { label: 'Pan', value: 'pan', icon: 'pan_tool' },
            { label: 'Zoom in', value: 'zoom_in', icon: 'zoom_in' },
            { label: 'Zoom out', value: 'zoom_out', icon: 'zoom_out' }
          ]"
          @update:model-value="setInteractionMode"
          dense
          size="sm"
        />
      </div>
      <div class="row q-gutter-xs q-mt-sm">
        <q-btn dense label="Undo" size="sm" icon="undo" @click="undoLastDraw" :disable="interactionMode !== 'draw'" />
        <q-btn dense label="Save" size="sm" icon="save" @click="saveTrainingPolygons" />
        <q-btn dense label="Clear" size="sm" icon="delete_sweep" @click="clearDrawnPolygons" />
        <q-btn
          dense
          :label="isCurrentDateExcluded ? 'Include Date' : 'Exclude Date'"
          size="sm"
          :icon="isCurrentDateExcluded ? 'add_circle' : 'block'"
          @click="toggleExcludeCurrentDate"
        />
      </div>

      <div class="text-caption q-mt-sm">Polygon Size (m)</div>
      <q-slider
        v-model="polygonSize"
        :min="10"
        :max="500"
        :step="10"
        label
        label-always
        color="primary"
        @update:model-value="updatePolygonSize"
        dense
      />

      <div class="text-caption q-mt-sm">Select Class</div>
      <div class="row q-gutter-xs">
        <q-btn
          v-for="className in projectClasses"
          :key="className"
          :label="className"
          :color="selectedClass === className ? 'primary' : 'grey-4'"
          :text-color="selectedClass === className ? 'white' : 'black'"
          @click="setClassLabel(className)"
          dense
          size="sm"
        />
      </div>
    </div>
  </template>

<script>
import { computed, onMounted, watch } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import { useQuasar } from 'quasar'



export default {
    name: 'DrawingControlsCard',
    setup() {
        const mapStore = useMapStore()
        const projectStore = useProjectStore()
        const $q = useQuasar()
        const drawnPolygons = computed(() => mapStore.drawnPolygons)
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)

        onMounted(async () => {
            window.addEventListener('keydown', handleKeyDown);

            if (projectClasses.value.length > 0 && !selectedClass.value) {
                selectedClass.value = projectClasses.value[0].name
            }
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
            } else if ((event.key === 'Delete' || event.key === 'Backspace') && mapStore.selectedPolygon !== null) {
                mapStore.deletePolygon(mapStore.selectedPolygon);
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
            }
        };

        watch(drawnPolygons, () => {
            // console.log("Drawn polygons changed - watcher in drawingcontrolscard")
            drawnPolygons.value = mapStore.drawnPolygons
        }, { immediate: true });

        watch(() => projectClasses.value, (newClasses) => {
            if (newClasses.length > 0 && !selectedClass.value) {
                selectedClass.value = newClasses[0].value
            }
        }, { immediate: true })

        const saveTrainingPolygons = async () => {
            try {
                await mapStore.saveCurrentTrainingPolygons(selectedBasemapDate.value);
                // Show success notification
                $q.notify({
                    type: 'positive',
                    message: 'Training polygons saved successfully'
                });
            } catch (error) {
                // Show error notification
                $q.notify({
                    type: 'negative',
                    message: 'Error saving training polygons'
                });
            }
        };

        const clearDrawnPolygons = () => {
            mapStore.clearDrawnPolygons(true)
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
                        ? 'Date has been included'
                        : 'Date has been excluded'
                });
            } catch (error) {
                $q.notify({
                    type: 'negative',
                    message: 'Error toggling date exclusion status'
                });
            }
        };

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
        }
    }
}
</script>

<style scoped>
.drawing-controls {
  background-color: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
