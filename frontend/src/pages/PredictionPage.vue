<template>
  <q-page padding>
    <h2 class="text-h4 q-mb-md">Land Cover Prediction</h2>
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <data-table title="Available Models" :rows="modelOptions" :columns="modelColumns" @row-selected="handleModelSelection" />
      </div>
      <div class="col-12 col-md-6">
        <data-table title="Available Rasters" :rows="rasterOptions" :columns="rasterColumns" @row-selected="handleRasterSelection" />
      </div>
    </div>
    <div v-if="selectedRaster && selectedModel" class="q-mt-md">
      <q-btn label="Predict Landcover" @click="predictLandcover" color="primary" />
    </div>
    <div ref="mapContainer" class="map-container q-mt-md"></div>
  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue';
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';
import { fromUrl } from 'geotiff';
import OSM from 'ol/source/OSM';
import apiService from '../services/api';
import DataTable from '../components/DataTable.vue';


export default {
  components: {
    DataTable
  },
  setup() {
    const mapContainer = ref(null);
    const map = ref(null);
    const rasterLayer = ref(null);
    const predictionLayer = ref(null);
    const selectedModel = ref(null);
    const selectedRaster = ref(null);
    const modelOptions = ref([]);
    const rasterOptions = ref([]);
    const mapInitialized = ref(false);
    const error = ref(null);
    const predictionFile = ref(null);


    onMounted(() => {
      initMap();
      fetchModelOptions();
      fetchRasterOptions();
    });

    const initMap = () => {
      map.value = new Map({
        target: mapContainer.value,
        layers: [
          new TileLayer({
            source: new OSM()
          })
        ],
        view: new View({
          center: [0, 0],
          zoom: 2
        })
      });
      mapInitialized.value = true;
    };

    const fetchModelOptions = async () => {

      try {
        const modelResponse = await apiService.fetchModels()
        modelOptions.value = modelResponse.data;

      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    const fetchRasterOptions = async () => {

      try {
        const rasterResponse = await apiService.fetchRasters()
        rasterOptions.value = rasterResponse.data;
        console.log(rasterOptions.value);

      } catch (error) {
        console.error('Error fetching data:', error);
      }


    };

    const predictLandcover = async () => {
      if (!selectedModel.value || !selectedRaster.value) return;

      const response = await apiService.predictLandcover({
          model_id: selectedModel.value.id,
          raster_id: selectedRaster.value.id
        },);

      const result = response.data;
      if (result.prediction_file) {
        predictionFile.value = result.prediction_file;
        displayPrediction();
      }
    };

    const displayPrediction = async () => {
      console.log('Displaying prediction:', predictionFile.value);
      try {
        const url = `http://127.0.0.1:5000/${predictionFile.value}`;
        const tiff = await fromUrl(url);
        const image = await tiff.getImage();
        const width = image.getWidth();
        const height = image.getHeight();
        const bbox = image.getBoundingBox();

        const rasterData = await image.readRasters();

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d');

        const imageData = context.createImageData(width, height);
        const data = imageData.data;

        for (let i = 0; i < width * height; i++) {
          const value = rasterData[0][i];
          const color = value === 0 ? [255, 255, 0, 255] : [0, 128, 0, 255]; // Yellow for non-forest, green for forest
          data[i * 4] = color[0];
          data[i * 4 + 1] = color[1];
          data[i * 4 + 2] = color[2];
          data[i * 4 + 3] = color[3];
        }
        context.putImageData(imageData, 0, 0);

        const imageUrl = canvas.toDataURL();
        const extent = bbox;

        if (predictionLayer.value) {
          map.value.removeLayer(predictionLayer.value);
        }

        predictionLayer.value = new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            imageExtent: extent,
          }),
          zIndex: 1,
          opacity: 0.7
        });

        map.value.addLayer(predictionLayer.value);
        map.value.getView().fit(extent, { duration: 1000 });
      } catch (error) {
        console.error('Error displaying prediction:', error);
        error.value = 'Failed to display prediction: ' + error.message;
      }
    };

    const handleRasterSelection = (updatedRow) => {
      const index = rasterOptions.value.findIndex(row => row.id === updatedRow.id);
      if (index !== -1) {
        rasterOptions.value[index] = updatedRow;
      }
      // Do something with the selected row
      console.log('Updated row:', updatedRow);
      selectedRaster.value = updatedRow;
    };

    const handleModelSelection = (updatedRow) => {
      const index = modelOptions.value.findIndex(row => row.id === updatedRow.id);
      if (index !== -1) {
        modelOptions.value[index] = updatedRow;
      }
      // Do something with the selected row
      console.log('Updated row:', updatedRow);
      selectedModel.value = updatedRow;
    };

    return {
      mapContainer,
      selectedModel,
      selectedRaster,
      modelOptions,
      rasterOptions,
      predictLandcover, rasterColumns: [
        { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
        { name: 'filename', required: true, label: 'Filename', align: 'left', field: 'filename', sortable: true },
        { name: 'description', required: true, label: 'Description', align: 'left', field: 'description', sortable: true },
        { name: 'actions', label: 'Select', field: 'actions', align: 'left' }
      ],
      modelColumns: [
        { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
        { name: 'name', required: true, label: 'Name', align: 'left', field: 'name', sortable: true },
        { name: 'file_path', required: true, label: 'File Path', align: 'left', field: 'file_path', sortable: true },
        { name: 'pixel_dataset_id', required: true, label: 'pixel_dataset_id', align: 'left', field: 'pixel_dataset_id', sortable: true },
        { name: 'accuracy', required: true, label: 'Accuracy', align: 'left', field: 'accuracy', sortable: true },
        { name: 'created_at', required: true, label: 'Created At', align: 'left', field: 'created_at', sortable: true},
        { name: 'actions', label: 'Select', field: 'actions', align: 'left' }
      ],
      handleRasterSelection,
      handleModelSelection,
      error,
      displayPrediction,
      predictionFile
    };
  }
};
</script>


<style scoped>
.map-container {
  width: 100%;
  height: 500px;
}
</style>
