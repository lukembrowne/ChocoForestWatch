<template>
    <div class="training-and-polygon-manager">
        <q-card class="manager-card">
            <q-card-section>
                <div class="text-h6">Training Set Manager</div>
                <div class="text-subtitle1">Current Date: {{ selectedBasemapDate }}</div>

                <q-btn-group spread>
                    <q-btn label="Previous Date" icon="chevron_left" @click="moveToPreviousDate"
                        :disable="isFirstDate" />
                    <q-btn label="Next Date" icon="chevron_right" @click="moveToNextDate" :disable="isLastDate" />
                </q-btn-group>

                <q-btn label="Save and Move to Next Period" @click="saveAndMoveNext" color="primary"
                    class="q-mt-md full-width" />
            </q-card-section>

            <q-separator />
        </q-card>


        <q-card v-if="drawnPolygons.length > 0" class="polygon-list-card">
            <q-card-section class="q-pa-sm">
                <div class="text-h6">Training Polygons</div>
                <div class="summary q-gutter-xs">
                    <div v-for="(summary, className) in classSummary" :key="className">
                        {{ className }}: {{ summary.count }} features, {{ summary.area.toFixed(1) }} ha
                    </div>
                </div>
            </q-card-section>
            <q-separator />
            <p>Polygon list</p>
            <q-card-section class="polygon-list q-pa-none">
                <q-list dense>
                    <q-item v-for="(polygon, index) in drawnPolygons" :key="index" class="q-py-xs">
                        <q-item-section avatar>
                            <q-icon name="lens" :style="{ color: getClassColor(polygon.properties.classLabel) }"
                                size="xs" />
                        </q-item-section>
                        <q-item-section>
                            <q-item-label>{{ polygon.properties.classLabel }}</q-item-label>
                            <q-item-label caption>{{ (calculateArea(polygon) / 10000).toFixed(1) }} ha</q-item-label>
                        </q-item-section>
                        <q-item-section side>
                            <q-btn flat round dense color="negative" icon="delete" size="sm"
                                @click="deletePolygon(index)" />
                        </q-item-section>
                    </q-item>
                </q-list>
            </q-card-section>
        </q-card>



    </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'
import { useQuasar } from 'quasar'

export default {
    name: 'TrainingAndPolygonManager',
    setup() {
        const mapStore = useMapStore()
        const projectStore = useProjectStore()
        const $q = useQuasar()
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)
        const drawnPolygons = computed(() => mapStore.drawnPolygons)
        const isFirstDate = computed(() => {
            return mapStore.availableDates.indexOf(selectedBasemapDate.value) === 0
        })
        const isLastDate = computed(() => {
            return mapStore.availableDates.indexOf(selectedBasemapDate.value) === mapStore.availableDates.length - 1
        })

        const moveToPreviousDate = async () => {
            await mapStore.moveToPreviousDate()
        }

        const moveToNextDate = async () => {
            await mapStore.moveToNextDate()
        }

        const saveAndMoveNext = async () => {
            try {
                await mapStore.saveCurrentTrainingPolygons()
                await mapStore.moveToNextDate()
                $q.notify({
                    color: 'positive',
                    message: 'Training polygons saved and moved to next date',
                    icon: 'check'
                })
            } catch (error) {
                $q.notify({
                    color: 'negative',
                    message: 'Failed to save training polygons',
                    icon: 'error'
                })
            }
        }


        // Polygon list functions
        const calculateArea = (polygon) => {
            const feature = new GeoJSON().readFeature(polygon)
            return getArea(feature.getGeometry())
        }

        const classSummary = computed(() => {
            const summary = {}
            drawnPolygons.value.forEach(polygon => {
                const classLabel = polygon.properties.classLabel
                const area = calculateArea(polygon) / 10000 // Convert to hectares
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




        return {
            selectedBasemapDate,
            isFirstDate,
            isLastDate,
            moveToPreviousDate,
            moveToNextDate,
            saveAndMoveNext,
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

.polygon-list {
    max-height: calc(100vh - 200px);
    overflow-y: auto;
}
</style>