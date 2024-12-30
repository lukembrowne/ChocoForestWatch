<template>
    <div class="training-and-polygon-manager">

        <!-- DrawingControlsCard here -->
        <drawing-controls-card />

        <q-separator />



        <q-card class="polygon-list-card">
            <q-card-section class="q-pa-sm">
                <div class="text-subtitle1 q-mb-sm">{{ t('training.summary.title') }}</div>
                <div class="summary-grid">
                    <q-item v-for="(summary, className) in classSummary" :key="className" class="summary-item">
                        <q-item-section>
                            <q-item-label>{{ className }}</q-item-label>
                            <q-item-label caption>
                                {{ summary.count }} {{ summary.count === 1 ? t('training.summary.features') : t('training.summary.features_plural') }}
                            </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                            <q-chip color="primary" text-color="white" size="sm">
                                {{ summary.area.toFixed(2) }} {{ t('training.summary.hectares') }}
                            </q-chip>
                        </q-item-section>
                    </q-item>
                </div>
            </q-card-section>
            <q-separator />

            <q-card>
                <q-card-section class="q-pa-sm">

                    <div class="text-subtitle1 q-mb-sm">{{ t('training.model.title') }}</div>
                    <q-card-actions align="center">
                        <q-btn :label="t('training.model.fit')" color="primary" @click="openModelTrainingDialog" />
                        <q-btn :label="t('training.model.evaluate')" color="primary" @click="openModelEvaluationDialog" />

                    </q-card-actions>
                </q-card-section>
            </q-card>
        </q-card>



    </div>
</template>

<script>
import { ref, computed, watch, reactive, onMounted, onUnmounted } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import { useI18n } from 'vue-i18n'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'
import { useQuasar } from 'quasar'
import DrawingControlsCard from './DrawingControlsCard.vue'
import ModelTrainingDialog from 'components/models/ModelTrainingDialog.vue'
import ModelEvaluationDialog from 'components/models/ModelEvaluationDialog.vue'


export default {
    name: 'TrainingAndPolygonManager',
    components: {
        DrawingControlsCard
    },
    setup() {
        const mapStore = useMapStore()
        const projectStore = useProjectStore()
        const $q = useQuasar()
        const { t } = useI18n()
        const selectedBasemapDate = computed(() => mapStore.selectedBasemapDate)
        const drawnPolygons = computed(() => mapStore.drawnPolygons)


        onMounted(() => {
            if (mapStore.map) {
                mapStore.map.on('click', handleFeatureClick);
            }
        });

        onUnmounted(() => {
            if (mapStore.map) {
                mapStore.map.un('click', handleFeatureClick);
            }
        });

        const openModelEvaluationDialog = async () => {
            $q.dialog({
                component: ModelEvaluationDialog
            })
        }

        const calculateArea = (polygon) => {

            const feature = new GeoJSON().readFeature(polygon)
            const geometry = feature.getGeometry()

            // Transform the geometry to EPSG:3857 (Web Mercator) for accurate area calculation
            const areaInSquareMeters = getArea(geometry)
            const areaInHectares = areaInSquareMeters / 10000 // Convert to hectares

            return areaInHectares
        }

        const classSummary = computed(() => {
            const summary = reactive({})
            drawnPolygons.value.forEach(polygon => {
                const classLabel = polygon.properties.classLabel
                const area = calculateArea(polygon)
                if (!summary[classLabel]) {
                    summary[classLabel] = { count: 0, area: 0 }
                }
                summary[classLabel].count++
                summary[classLabel].area += area
            })
            return summary
        })


        const handleFeatureClick = (event) => {

            // Only allow feature selection if not in drawing mode
            if (!mapStore.isDrawing) {

                const feature = mapStore.map.forEachFeatureAtPixel(
                    event.pixel,
                    (feature) => feature,
                    {
                        layerFilter: (layer) => {
                            // Exclude the AOI layer from selection
                            return layer.get('id') !== 'area-of-interest';
                        }
                    }
                );
                console.log("selecdted", feature)
                mapStore.setSelectedFeature(feature);
            };
        }

        const getClassColor = (className) => {
            const classObj = projectStore.currentProject?.classes.find(cls => cls.name === className)
            return classObj ? classObj.color : '#000000'
        }

        const hasUnsavedChanges = computed(() => mapStore.hasUnsavedChanges);

        const openModelTrainingDialog = () => {
            $q.dialog({
                component: ModelTrainingDialog
            }).onOk((response) => {
                // Handle the response from model training
                console.log('Model training completed:', response)
                $q.notify({
                    color: 'positive',
                    message: t('training.model.notifications.initiated'),
                    icon: 'check'
                })
            })
        }

        return {
            selectedBasemapDate,
            drawnPolygons,
            calculateArea,
            classSummary,
            getClassColor,
            openModelTrainingDialog,
            openModelEvaluationDialog,
            t
        }
    }
}
</script>

<style lang="scss" scoped>
.training-and-polygon-manager {
    height: calc(100vh - var(--app-header-height));
    overflow-y: auto;
}

.manager-card {
    background-color: rgba(255, 255, 255, 1.0);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
}

.polygon-list-card {
    border-radius: 0px;
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

.summary-grid {
    display: grid;
    gap: 8px;
    width: 60%;
}

.summary-item {
    background-color: rgba(0, 0, 0, 0.03);
    width: 100%;
}
</style>