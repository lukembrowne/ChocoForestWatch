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
                        <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
                            <q-tooltip>{{ t('training.tooltips.summarySection') }}</q-tooltip>
                        </q-btn>
                    </div>
                </q-card-section>

                <div class="summary-grid">
                    <q-item v-for="(summary, className) in classSummary" :key="className" class="summary-item" dense>
                        <q-item-section>
                            <q-item-label class="text-weight-medium">{{ className }}</q-item-label>
                            <q-item-label caption>
                                {{ summary.count }} {{ summary.count === 1 ? t('training.summary.features') :
                                    t('training.summary.features_plural') }}
                            </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                            <q-chip color="primary" text-color="white">
                                {{ summary.area.toFixed(2) }} {{ t('training.summary.hectares') }}
                            </q-chip>
                        </q-item-section>
                    </q-item>
                </div>

                <q-separator class="q-my-md" />

                <q-card-section class="section-header">
                    <div class="row items-center">
                        <div class="text-subtitle1">{{ t('training.model.title') }}</div>
                        <q-btn flat round dense icon="help" size="sm" class="q-ml-sm">
                            <q-tooltip>{{ t('training.tooltips.modelSection') }}</q-tooltip>
                        </q-btn>
                    </div>
                </q-card-section>

                <q-card-section class="q-pa-md">
                    <q-card-actions align="center" class="q-gutter-sm">
                        <q-btn :label="t('training.model.fit')" color="primary" @click="openModelTrainingDialog" />
                        <q-btn :label="t('training.model.evaluate')" color="primary"
                            @click="openModelEvaluationDialog" />
                        <q-btn :label="t('training.model.loadprediction')" color="primary" @click="loadPredictionToMap"
                            :disable="!basemapDateHasPrediction">
                            <q-tooltip>{{ t('training.tooltips.loadPrediction') }}</q-tooltip>
                        </q-btn>
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
import api from 'src/services/api';



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
        const prediction = ref(null)
        const predictions = ref([])
        const basemapDateHasPrediction = ref(false)


        onMounted(() => {
            if (mapStore.map) {
                mapStore.map.on('click', handleFeatureClick);
            }
            console.log("Showing single map")
            mapStore.initMap('map')
            mapStore.showSingleMap('map')
            loadPredictionsFromDatabase().then(() => {
                checkPredictionForDate(selectedBasemapDate.value);
            })
        });

        onUnmounted(() => {
            if (mapStore.map) {
                mapStore.map.un('click', handleFeatureClick);
            }

            console.log("Unmounting TrainingAndPolygonManager")
            console.log("Hiding single map")
            mapStore.hideSingleMap()
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

                // Load predictions from database after model training is complete
                loadPredictionsFromDatabase().then(() => {
                    checkPredictionForDate(selectedBasemapDate.value);
                })
                // Handle the response from model training
                console.log('Model training completed:', response)
                $q.notify({
                    color: 'positive',
                    message: t('training.model.notifications.initiated'),
                    icon: 'check'
                })
            })
        }

        const loadPredictionsFromDatabase = async () => {
            try {
                const response = await api.getPredictions(projectStore.currentProject.id);
                console.log("Predictions fetched:", response.data);
                predictions.value = response.data
                    .filter(p => p.type === "land_cover")
                    .sort((a, b) => new Date(a.basemap_date) - new Date(b.basemap_date));
            } catch (error) {
                console.error('Error loading initial data:', error);
                $q.notify({
                    color: 'negative',
                    message: 'Failed to load analysis data',
                    icon: 'error'
                });
            }
        };

        const loadPredictionToMap = () => {

            // Check to see if layer is already added to map

            console.log("Layers in map", mapStore.map.getLayers().getArray())
            const layer = mapStore.map.getLayers().getArray().find(l => l.get('id') === `landcover-${prediction.value.id}`);
            if (layer) {
                console.log("Layer already added to map")
                $q.notify({
                    color: 'warning',
                    message: 'Land cover prediction already loaded',
                    icon: 'warning'
                });
                return
            }



            console.log(`Adding land cover prediction for `, prediction.value);

            // Prediction is not null
            if (prediction.value) {

                mapStore.displayPrediction(
                    prediction.value.file,
                    `landcover-${prediction.value.id}`,
                    prediction.value.name,
                    'landcover',
                    null,
                    true
                );
            }
        }

        const checkPredictionForDate = (date) => {
            if (!date) {
                basemapDateHasPrediction.value = false;
                prediction.value = null;
                return;
            }

            prediction.value = predictions.value.find(p => p.basemap_date === date);
            console.log("Found prediction for basemap date", prediction.value);
            basemapDateHasPrediction.value = !!prediction.value;

            // If prediction exists but layer isn't on map, remove any existing prediction layers
            if (prediction.value) {
                const layers = mapStore.map.getLayers().getArray();
                const predictionLayers = layers.filter(l => l.get('id')?.startsWith('landcover-'));
                predictionLayers.forEach(layer => {
                    if (layer.get('id') !== `landcover-${prediction.value.id}`) {
                        mapStore.map.removeLayer(layer);
                    }
                });
            }
        };

        // Watch for basemap date changes
        watch(selectedBasemapDate, (newBasemapDate) => {
            console.log("selectedBasemapDate changed to:", newBasemapDate);
            loadPredictionsFromDatabase().then(() => {
                checkPredictionForDate(newBasemapDate);
            })
        });

        return {
            selectedBasemapDate,
            drawnPolygons,
            calculateArea,
            classSummary,
            getClassColor,
            openModelTrainingDialog,
            openModelEvaluationDialog,
            t,
            loadPredictionsFromDatabase,
            basemapDateHasPrediction,
            loadPredictionToMap,
            checkPredictionForDate
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
    font-size: 0.85rem;

    &:hover {
        background-color: #f1f8f1;
    }

    :deep(.q-item__label) {
        font-size: 0.85rem;
    }

    :deep(.q-item__label--caption) {
        font-size: 0.85rem;
    }
}

:deep(.q-chip) {
    font-size: 0.85rem;
    padding: 0 10px;
}
</style>