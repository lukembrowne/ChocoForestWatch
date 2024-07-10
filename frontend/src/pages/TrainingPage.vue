<template>
  <q-page padding>
    <h2 class="text-h4 q-mb-md">Training Data Preparation</h2>

    <div class="row q-col-gutter-md">
      <!-- Raster Table -->
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Available Rasters</div>
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
          </q-card-section>
        </q-card>
      </div>

      <!-- Vector Table -->
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Available Vectors</div>
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
          </q-card-section>
        </q-card>
      </div>

      <!-- Upload Cards -->
      <div class="col-12 col-md-6 q-mt-md">
        <FileUploadCard data-type="Raster" accepted-file-types=".tif,.tiff" @file-uploaded="handleRasterUploaded" />
      </div>
      <div class="col-12 col-md-6 q-mt-md">
        <FileUploadCard data-type="Vector" accepted-file-types=".geojson" @file-uploaded="handleVectorUploaded" />
      </div>
    </div>

    <div class="q-mt-md">
      <MapComponent :rasterId="selectedRaster ? selectedRaster.id : null"
        :vectorId="selectedVector ? selectedVector.id : null" @polygons-drawn="onPolygonsDrawn" />
    </div>

    <q-btn label="Extract Pixels" color="primary" @click="extractPixels" :disable="!canExtractPixels" class="q-mt-md" />

   <!-- Model Training Section -->
   <div class="q-mt-lg">
      <h3 class="text-h5">Model Training</h3>
      <ModelTraining :pixel-dataset-id="pixelDatasetId" @model-trained="onModelTrained" />
    </div>

    <!-- Debug Section -->
    <div class="q-mt-lg">
      <h3 class="text-h5">Debug: Training Store State</h3>
      <TrainingStoreDebug />
    </div>
  </q-page>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';
import MapComponent from '../components/MapComponent.vue';
import FileUploadCard from '../components/FileUploadCard.vue';
import TrainingStoreDebug from '../components/TrainingStoreDebug.vue';
import apiService from '../services/api';
import { useTrainingStore } from '../stores/trainingStore';
import { storeToRefs } from 'pinia';
import GeoJSON from 'ol/format/GeoJSON';
import ModelTraining from '../components/ModelTraining.vue';



export default {
  name: 'TrainingPage',
  components: {
    MapComponent,
    FileUploadCard,
    TrainingStoreDebug,
    ModelTraining,
  },
  setup() {
    const $q = useQuasar();
    const router = useRouter();
    const trainingStore = useTrainingStore();
    const { pixelsExtracted } = storeToRefs(trainingStore);

    const rasters = ref([]);
    const vectors = ref([]);
    const selectedRaster = ref(null);
    const selectedVector = ref(null);
    const rasterFilter = ref('');
    const vectorFilter = ref('');
    const drawnPolygons = ref([]);
    const pixelDatasetId = ref(null);


    const rasterColumns = [
      { name: 'id', field: 'id', label: 'ID', sortable: true },
      { name: 'filename', field: 'filename', label: 'Filename', sortable: true },
      { name: 'description', field: 'description', label: 'Description', sortable: true }
    ];

    const vectorColumns = [
      { name: 'id', field: 'id', label: 'ID', sortable: true },
      { name: 'filename', field: 'filename', label: 'Filename', sortable: true },
      { name: 'description', field: 'description', label: 'Description', sortable: true }
    ];

    const fetchRasters = async () => {
      try {
        const response = await apiService.fetchRasters();
        rasters.value = response.data;
      } catch (error) {
        console.error('Error fetching rasters:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to fetch rasters',
          icon: 'error'
        });
      }
    };

    const fetchVectors = async () => {
      try {
        const response = await apiService.fetchVectors();
        vectors.value = response.data;
      } catch (error) {
        console.error('Error fetching vectors:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to fetch vectors',
          icon: 'error'
        });
      }
    };

    const onRasterRowClick = (evt, row) => {
      selectedRaster.value = row;
      trainingStore.setSelectedRaster(row);
    };

    const onVectorRowClick = (evt, row) => {
      selectedVector.value = row;
      trainingStore.setSelectedVector(row);
    };

    const onPolygonsDrawn = (polygons) => {
      drawnPolygons.value = polygons;
      trainingStore.setDrawnPolygons(polygons);
    };

    const canExtractPixels = computed(() =>
      selectedRaster.value && (selectedVector.value || drawnPolygons.value.length > 0)
    );

    const convertPolygonsToGeoJSON = (polygons) => {
      const geoJSONFormat = new GeoJSON();
      return polygons.map(polygon => {
        const geojson = geoJSONFormat.writeFeatureObject(polygon, {
          dataProjection: 'EPSG:3857',
          featureProjection: 'EPSG:3857'
        });
        return {
          type: 'Feature',
          geometry: geojson.geometry,
          properties: {
            classLabel: polygon.get('classLabel')
          }
        };
      });
    };

    const extractPixels = async () => {
      try {
        let polygonsToUse;
        if (selectedVector.value) {
          polygonsToUse = selectedVector.value.geojson.features;
        } else if (drawnPolygons.value.length > 0) {
          polygonsToUse = convertPolygonsToGeoJSON(drawnPolygons.value);
        } else {
          throw new Error('No polygons selected or drawn');
        }

        await trainingStore.extractPixels(polygonsToUse);
        $q.notify({
          type: 'positive',
          message: 'Pixels extracted successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error in extractPixels:', error);
        $q.notify({
          type: 'negative',
          message: error.message || 'Failed to extract pixels',
          icon: 'error'
        });
      }
    }

      const onModelTrained = (modelInfo) => {
      // Handle the trained model info, e.g., save it to the store or navigate to a results page
      console.log('Model trained:', modelInfo);
      $q.notify({
        type: 'positive',
        message: 'Model trained successfully',
        icon: 'check'
      });
    }

    const handleRasterUploaded = async (raster) => {
      await fetchRasters();
      $q.notify({
        type: 'positive',
        message: 'Raster uploaded successfully',
        icon: 'check'
      });
    };

    const handleVectorUploaded = async (vector) => {
      await fetchVectors();
      $q.notify({
        type: 'positive',
        message: 'Vector uploaded successfully',
        icon: 'check'
      });
    };

    onMounted(() => {
      fetchRasters();
      fetchVectors();
    });

    return {
      rasters,
      vectors,
      selectedRaster,
      selectedVector,
      rasterColumns,
      vectorColumns,
      rasterFilter,
      vectorFilter,
      onRasterRowClick,
      onVectorRowClick,
      onPolygonsDrawn,
      canExtractPixels,
      extractPixels,
      pixelsExtracted,
      handleRasterUploaded,
      handleVectorUploaded,
      onModelTrained
    };
  }
};
</script>