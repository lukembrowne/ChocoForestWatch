<template>
    <div class="training-and-polygon-manager">
       
        <!-- DrawingControlsCard here -->
        <drawing-controls-card />

        <q-separator />



        <q-card class="polygon-list-card">
            <q-card-section class="q-pa-sm">
                <div class="text-h6">Training Data Summary</div>
                <div class="summary q-gutter-xs">
                    <div v-for="(summary, className) in classSummary" :key="className">
                        {{ className }}: {{ summary.count }} features, {{ summary.area.toFixed(2) }} ha
                    </div>
                </div>
            </q-card-section>
            <q-separator />
        </q-card>



    </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'
import { useQuasar } from 'quasar'
import DrawingControlsCard from './DrawingControlsCard.vue'


export default {
    name: 'TrainingAndPolygonManager',
    components: {
        DrawingControlsCard
    },
    setup() {
        const mapStore = useMapStore()
        const $q = useQuasar()
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)
        const drawnPolygons = computed(() => mapStore.drawnPolygons)


        // Polygon list functions
        const calculateArea = (polygon) => {
            const feature = new GeoJSON().readFeature(polygon)
            return getArea(feature.getGeometry())
        }

        const classSummary = computed(() => {
            const summary = {}
            drawnPolygons.value.forEach(polygon => {
                const classLabel = polygon.properties.classLabel
                let area = calculateArea(polygon) // Convert to hectares
                area = area / 10000 // Convert to hectares
                if (!summary[classLabel]) {
                    summary[classLabel] = { count: 0, area: 0 }
                }
                summary[classLabel].count++
                summary[classLabel].area += area
            })
            return summary
        })

        const deletePolygon = (index) => {
            mapStore.deletePolygon(index)
        }

        const getClassColor = (className) => {
            const classObj = projectStore.currentProject?.classes.find(cls => cls.name === className)
            return classObj ? classObj.color : '#000000'
        }

        const hasUnsavedChanges = computed(() => mapStore.hasUnsavedChanges);

        return {
            selectedBasemapDate,
            drawnPolygons,
            calculateArea,
            classSummary,
            deletePolygon,
            getClassColor,
        }
    }
}
</script>

<style lang="scss" scoped>
.training-and-polygon-manager {
    position: absolute;
    top: 50px; // Adjust this value to account for the header height
    left: 0;
    bottom: 0;
    width: 350px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
}

.manager-card {
    background-color: rgba(255, 255, 255, 1.0);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
}

.full-height {
    height: 100%;
}

.polygon-list-section {
    flex-grow: 1;
    overflow-y: auto;
}

.polygon-list-card {
    background-color: rgba(255, 255, 255, 1.0);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    overflow-y: auto;
}

.summary {
    display: flex;
    flex-wrap: wrap;
    margin-bottom: 8px;
}


</style>