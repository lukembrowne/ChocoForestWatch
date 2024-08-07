<template>
    <q-card class="drawing-controls-card">
        <q-card-section>
            <div class="text-h6">Drawing Controls</div>
            <div class="row q-gutter-sm">
                <q-btn-toggle v-model="interactionMode" :options="[
                    { label: 'Draw (d)', value: 'draw', icon: 'create' },
                    { label: 'Pan (m)', value: 'pan', icon: 'pan_tool' },
                    { label: 'Zoom in (z)', value: 'zoom_in', icon: 'zoom_in' },
                    { label: 'Zoom out (x)', value: 'zoom_out', icon: 'zoom_out' }
                ]" @update:model-value="setInteractionMode" />
                <q-btn label="Undo (Ctrl/Cmd+Z)" color="secondary" icon="undo" @click="undoLastDraw"
                    :disable="interactionMode !== 'draw'" />
            </div>
        </q-card-section>
        <q-card-section>
            <div class="text-subtitle2">Select Class</div>
            <q-radio v-model="selectedClass" :val="className" :label="className" v-for="className in projectClasses"
                :key="className" @update:model-value="setClassLabel" />
        </q-card-section>


    </q-card>
</template>

<script>
import { computed, onMounted, watch } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'


export default {
    name: 'DrawingControlsCard',
    setup() {
        const mapStore = useMapStore()
        const projectStore = useProjectStore()

        const drawnPolygons = computed(() => mapStore.drawnPolygons)
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)

        onMounted(async () => {
            window.addEventListener('keydown', handleKeyDown);

            if (projectClasses.value.length > 0 && !selectedClass.value) {
                selectedClass.value = projectClasses.value[0].name
            }
        })


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
            console.log("Drawn polygons changed - watcher in drawingcontrolscard")
            drawnPolygons.value = mapStore.drawnPolygons
        }, { immediate: true });

        watch(() => projectClasses.value, (newClasses) => {
            if (newClasses.length > 0 && !selectedClass.value) {
                selectedClass.value = newClasses[0].value
            }
        }, { immediate: true })

        return {
            interactionMode,
            selectedClass,
            projectClasses,
            setInteractionMode,
            setClassLabel,
            undoLastDraw,
            drawnPolygons,
            handleKeyDown,
            selectedBasemapDate
        }
    }
}
</script>

<style scoped>
.drawing-controls-card {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 800px;
    max-width: 90%;
    z-index: 1000;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    background-color: white;
}
</style>