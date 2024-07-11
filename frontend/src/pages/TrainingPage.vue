<template>
  <q-page padding>
    <h2 class="text-h4 q-mb-md">Model Training</h2>

    <!-- Horizontal Stepper -->
    <q-stepper v-model="step" ref="stepper" color="primary" animated flat>
      <q-step :name="1" title="Select Training Data" icon="folder_open" :done="step > 1">
        <h4>Select Raster</h4>
        <q-table :rows="rasters" :columns="rasterColumns" row-key="id" :pagination="{ rowsPerPage: 5 }"
          :filter="rasterFilter" @row-click="onRasterRowClick">
          <template v-slot:top-right>
            <q-input dense debounce="300" v-model="rasterFilter" placeholder="Search">
              <template v-slot:append>
                <q-icon name="search" />
              </template>
            </q-input>
          </template>
        </q-table>
        <q-file v-model="newRasterFile" label="Upload new raster" accept=".tif,.tiff" class="q-mt-md" />
        <q-btn label="Upload Raster" color="primary" class="q-mt-sm" @click="uploadRaster" :disable="!newRasterFile" />

        <h4 class="q-mt-lg">Select or Upload Training Polygons</h4>
        <q-table :rows="vectors" :columns="vectorColumns" row-key="id" :pagination="{ rowsPerPage: 5 }"
          :filter="vectorFilter" @row-click="onVectorRowClick">
          <template v-slot:top-right>
            <q-input dense debounce="300" v-model="vectorFilter" placeholder="Search">
              <template v-slot:append>
                <q-icon name="search" />
              </template>
            </q-input>
          </template>
        </q-table>
        <q-file v-model="newVectorFile" label="Upload new vector" accept=".geojson" class="q-mt-md" />
        <q-btn label="Upload Vector" color="primary" class="q-mt-sm" @click="uploadVector" :disable="!newVectorFile" />
      </q-step>

      <q-step :name="2" title="Draw Polygons & Extract Pixels" icon="edit" :done="step > 2">
        <div style="width: 100%; height: 400px;">
          <BaseMapComponent ref="baseMap" @map-ready="onMapReady" />
        </div>
        <div class="toolbar q-mt-md">
          <q-btn :label="drawing ? 'Stop Drawing' : 'Start Drawing'" :color="drawing ? 'negative' : 'primary'"
            @click="toggleDrawing" class="q-mr-sm" />
          <q-select v-model="classLabel" :options="classOptions" label="Class Label" class="q-ml-md"
            style="width: 150px;" />
          <q-btn label="Extract Pixels" color="secondary" @click="extractPixels" :loading="extractingPixels"
            :disable="!canExtractPixels" class="q-ml-sm" />
          <q-btn label="Delete Selected Polygon" color="negative" @click="deleteSelectedPolygon"
            :disable="!selectedPolygon" class="q-ml-sm" />
          <q-btn label="Save Drawn Polygons" color="secondary" class="q-ml-sm" @click="saveDrawnPolygons"
            :disable="polygons?.length === 0" />
        </div>
      </q-step>

      <q-step :name="3" title="Train Model" icon="school">
        <ModelTraining :pixel-dataset-id="pixelDatasetId" @model-trained="onModelTrained" />
      </q-step>
    </q-stepper>

    <!-- Navigation Buttons -->
    <div class="q-mt-md">
      <q-btn v-if="step > 1" flat color="primary" @click="step--" label="Back" class="q-mr-sm" />
      <q-btn v-if="step < 3" color="primary" @click="step++" label="Continue" :disable="!canProceedToNextStep" />
      <q-btn v-else color="positive" @click="finishTraining" label="Finish" :disable="!modelTrained" />
    </div>
  </q-page>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useQuasar } from 'quasar';
import ModelTraining from 'components/ModelTraining.vue';
import { useTrainingStore } from '../stores/trainingStore';
import { storeToRefs } from 'pinia';
import apiService from '../services/api';
import GeoJSON from 'ol/format/GeoJSON';
import { useDrawing } from '../composables/useDrawing';
import BaseMapComponent from '../components/BaseMapComponent.vue';


export default {
  name: 'TrainingPage',
  components: {
    BaseMapComponent,
    ModelTraining,
  },
  setup() {
    const $q = useQuasar();
    const trainingStore = useTrainingStore();
    const { selectedRaster, selectedVector, drawnPolygons, selectedPolygon } = storeToRefs(trainingStore);

    const step = ref(1);
    const baseMap = ref(null);
    const rasters = ref([]);
    const vectors = ref([]);
    const newRasterFile = ref(null);
    const newVectorFile = ref(null);
    const extractingPixels = ref(false);
    const pixelsExtracted = ref(false);
    const pixelDatasetId = ref(null);
    const modelTrained = ref(false);
    const mapComponent = ref(null);
    const rasterFilter = ref('');
    const vectorFilter = ref('');
    const classLabel = ref('forest');
    const classOptions = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non-forest' },
    ];


    const rasterColumns = [
      { name: 'id', field: 'id', label: 'ID', sortable: true },
      { name: 'filename', field: 'filename', label: 'Filename', sortable: true },
      { name: 'description', field: 'description', label: 'Description', sortable: true },
      { name: 'date', field: 'date', label: 'Date', sortable: true },
    ];

    const vectorColumns = [
      { name: 'id', field: 'id', label: 'ID', sortable: true },
      { name: 'filename', field: 'filename', label: 'Filename', sortable: true },
      { name: 'description', field: 'description', label: 'Description', sortable: true },
      { name: 'created_at', field: 'created_at', label: 'created_at', sortable: true }
    ];

    const canExtractPixels = computed(() =>
      selectedRaster.value && (selectedVector.value || drawnPolygons.value.length > 0)
    );

    const canProceedToNextStep = computed(() => {
      switch (step.value) {
        case 1: return selectedRaster.value !== null;
        case 2: return pixelsExtracted.value;
        default: return true;
      }
    });

    const onMapReady = (map) => {
      loadRasterAndVector();
    };

    const {
      drawing,
      polygons,
      startDrawing,
      stopDrawing,
      getDrawnPolygonsGeoJSON,
      setClassLabel
    } = useDrawing(baseMap);

    const toggleDrawing = () => {
      if (drawing.value) {
        stopDrawing();
      } else {
        startDrawing();
      }
    };

    const deleteSelectedPolygon = () => {
      if (selectedPolygon.value) {
        deletePolygon(selectedPolygon.value);
      }
    };

    const loadRasterAndVector = async () => {
      if (baseMap.value && selectedRaster.value) {
        await baseMap.value.loadRaster(selectedRaster.value.id);
      }
      if (baseMap.value && selectedVector.value) {
        await baseMap.value.loadVector(selectedVector.value.id);
      }
    };


    onMounted(async () => {

      window.addEventListener('keydown', handleKeyDown);

      try {
        const [rasterResponse, vectorResponse] = await Promise.all([
          apiService.fetchRasters(),
          apiService.fetchVectors()
        ]);
        rasters.value = await Promise.all(rasterResponse.data.map(async (raster) => {
          const date = null;
          return { ...raster, date };
        }));
        vectors.value = vectorResponse.data;
      } catch (error) {
        console.error('Error fetching data:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to load rasters and vectors',
          icon: 'error'
        });
      }
    });

    const extractDateFromRaster = async (rasterId) => {
      try {
        const response = await apiService.extractRasterDate(rasterId);
        return response.data.date;
      } catch (error) {
        console.error('Error extracting date from raster:', error);
        return 'Unknown';
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === '1') {
        classLabel.value = 'forest';
      } else if (event.key === '2') {
        classLabel.value = 'non-forest';
      } else if (event.key === 'Delete' && selectedPolygon.value) {
        deletePolygon(selectedPolygon.value);
      } else if (event.key === ' ' && !event.repeat) {
        event.preventDefault();
        toggleDrawing();
      }
    };

    const uploadRaster = async () => {
      if (!newRasterFile.value) return;

      try {
        const formData = new FormData();
        formData.append('file', newRasterFile.value);
        formData.append('description', 'Uploaded raster');

        const response = await apiService.uploadRaster(formData);
        const date = null;
        const newRaster = { ...response.data, date };
        rasters.value.push(newRaster);
        trainingStore.setSelectedRaster(newRaster);
        newRasterFile.value = null;

        $q.notify({
          type: 'positive',
          message: 'Raster uploaded successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error uploading raster:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to upload raster',
          icon: 'error'
        });
      }
    };

    const uploadVector = async () => {
      if (!newVectorFile.value) return;

      try {
        const formData = new FormData();
        formData.append('file', newVectorFile.value);
        formData.append('description', 'Uploaded vector');

        const response = await apiService.uploadVector(formData);
        vectors.value.push(response.data);
        trainingStore.setSelectedVector(response.data);
        newVectorFile.value = null;

        $q.notify({
          type: 'positive',
          message: 'Vector uploaded successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error uploading vector:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to upload vector',
          icon: 'error'
        });
      }
    };

    const onRasterRowClick = (evt, row) => {
      trainingStore.setSelectedRaster(row);
    };

    const onVectorRowClick = (evt, row) => {
      trainingStore.setSelectedVector(row);
    };

    const onPolygonsDrawn = (polygons) => {
      trainingStore.setDrawnPolygons(polygons);
    };

    const saveDrawnPolygons = async () => {
      try {
        const geoJSONFormat = new GeoJSON();
        const features = drawnPolygons.value.map(polygon => {
          const feature = geoJSONFormat.writeFeatureObject(polygon, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          return {
            type: 'Feature',
            geometry: feature.geometry,
            properties: {
              classLabel: polygon.get('classLabel')
            }
          };
        });

        const response = await apiService.saveDrawnPolygons({
          description: 'Drawn training polygons',
          polygons: features
        });

        vectors.value.push(response.data);
        trainingStore.setSelectedVector(response.data);

        $q.notify({
          type: 'positive',
          message: 'Polygons saved successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error saving drawn polygons:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to save drawn polygons',
          icon: 'error'
        });
      }
    };

    const extractPixels = async () => {
      extractingPixels.value = true;
      try {
        const polygonsToUse = selectedVector.value
          ? selectedVector.value.geojson.features
          : drawnPolygons.value;

        const response = await apiService.extractPixels({
          rasterId: selectedRaster.value.id,
          polygons: polygonsToUse
        });

        pixelsExtracted.value = true;
        pixelDatasetId.value = response.data.pixel_dataset_id;
        $q.notify({
          type: 'positive',
          message: 'Pixels extracted successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error extracting pixels:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to extract pixels',
          icon: 'error'
        });
      } finally {
        extractingPixels.value = false;
      }
    };

    const onModelTrained = (modelInfo) => {
      modelTrained.value = true;
      $q.notify({
        type: 'positive',
        message: 'Model trained successfully',
        icon: 'check'
      });
    };

    const finishTraining = () => {
      $q.notify({
        type: 'positive',
        message: 'Training process completed',
        icon: 'check'
      });
      // Navigate to another page or reset the wizard
    };


    watch(classLabel, (newLabel) => {
      setClassLabel(newLabel);
    });

    watch([selectedRaster, selectedVector], () => {
      if (baseMap.value) {
        loadRasterAndVector();
      }
    });

    return {
      step,
      rasters,
      vectors,
      selectedRaster,
      selectedVector,
      drawnPolygons,
      newRasterFile,
      newVectorFile,
      extractingPixels,
      pixelsExtracted,
      pixelDatasetId,
      modelTrained,
      mapComponent,
      rasterFilter,
      vectorFilter,
      rasterColumns,
      vectorColumns,
      canExtractPixels,
      canProceedToNextStep,
      uploadRaster,
      uploadVector,
      onRasterRowClick,
      onVectorRowClick,
      onPolygonsDrawn,
      saveDrawnPolygons,
      extractPixels,
      onModelTrained,
      finishTraining,
      baseMap,
      polygons,
      classLabel,
      onMapReady,
      drawing,
      toggleDrawing,
      classOptions,
      loadRasterAndVector,
      selectedPolygon,
      deleteSelectedPolygon,
      setClassLabel,
    };
  }
};
</script>

<style scoped>
.map-card {
  height: 600px;
  display: flex;
  flex-direction: column;
}

.map-card .q-card__section:first-child {
  flex-grow: 1;
  overflow: hidden;
}
</style>