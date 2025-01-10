<template>
    <div class="training-and-polygon-manager">
        <div class="content-wrapper">
            <!-- DrawingControlsCard here -->
            <drawing-controls-card />

            <q-separator class="q-my-md" />

            <q-card class="polygon-list-card">
               


                <q-card-section class="section-header">
                    <div class="row items-center">
                        <div class="text-subtitle1">{{ t('training.summary.title') }}</div>
                        <q-btn
                          flat
                          round
                          dense
                          icon="help"
                          size="sm"
                          class="q-ml-sm"
                        >
                          <q-tooltip>{{ t('training.tooltips.summarySection') }}</q-tooltip>
                        </q-btn>
                    </div>
                </q-card-section>

                <div class="summary-grid">
                    <q-item v-for="(summary, className) in classSummary" 
                        :key="className" 
                        class="summary-item"
                        dense
                    >
                        <q-item-section>
                            <q-item-label class="text-weight-medium">{{ className }}</q-item-label>
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

                <q-separator class="q-my-md" />

                <q-card-section class="section-header">
                    <div class="row items-center">
                        <div class="text-subtitle1">{{ t('training.model.title') }}</div>
                        <q-btn
                          flat
                          round
                          dense
                          icon="help"
                          size="sm"
                          class="q-ml-sm"
                        >
                          <q-tooltip>{{ t('training.tooltips.modelSection') }}</q-tooltip>
                        </q-btn>
                    </div>
                </q-card-section>

                <q-card-section class="q-pa-md">
                    <q-card-actions align="center" class="q-gutter-sm">
                        <q-btn 
                            :label="t('training.model.fit')" 
                            color="primary" 
                            @click="openModelTrainingDialog"
                        />
                        <q-btn 
                            :label="t('training.model.evaluate')" 
                            color="primary" 
                            @click="openModelEvaluationDialog"
                        />
                    </q-card-actions>
                </q-card-section>
            </q-card>

            <training-welcome-modal />
        </div>
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
import TrainingWelcomeModal from 'components/welcome/TrainingWelcomeModal.vue'


export default {
    name: 'TrainingAndPolygonManager',
    components: {
        DrawingControlsCard,
        TrainingWelcomeModal
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
    background: #fafafa;
}

.content-wrapper {
    height: 100%;
}

.manager-card {
    background-color: rgba(255, 255, 255, 1.0);
    display: flex;
    flex-direction: column;
}

.polygon-list-card {
    border-radius: 0px;
    background: white;
    box-shadow: none;
}

.summary-grid {
    display: grid;
    gap: 8px;
    padding: 0 16px;
}

.summary-item {
    background-color: #f8fafc;
    border-radius: 8px;
    padding: 8px;
    width: 100%;
    font-size: 0.8rem;

    &:hover {
        background-color: #f1f8f1;
    }

    :deep(.q-item__label) {
        font-size: 0.8rem;
    }

    :deep(.q-item__label--caption) {
        font-size: 0.75rem;
    }
}

:deep(.q-chip) {
    font-size: 0.75rem;
    padding: 0 8px;
}

.q-separator {
    margin: 16px 0;
}
</style>