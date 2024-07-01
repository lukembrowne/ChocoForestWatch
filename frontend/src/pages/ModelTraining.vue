<template>
  <q-page>
    <div class="q-pa-md">
      <file-upload-card 
        data-type="Raster"
        accepted-file-types=".tif,.tiff"
        @file-uploaded="handleRasterUploaded"
      />
      <file-upload-card 
        data-type="Vector"
        accepted-file-types=".geojson"
        @file-uploaded="handleVectorUploaded"
      />
      
      <data-table
        title="Available Rasters"
        :rows="rasters"
        :columns="rasterColumns"
        @row-selected="selectRaster"
      />
      
      <data-table
        title="Available Vectors"
        :rows="vectors"
        :columns="vectorColumns"
        @row-selected="selectVector"
      />

      <map-component 
        :selected-raster="selectedRaster" 
        :selected-vector="selectedVector" 
        class="q-mt-md" 
      />
    </div>
  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue';
import FileUploadCard from '../components/FileUploadCard.vue';
import DataTable from '../components/DataTable.vue';
import MapComponent from '../components/MapComponent.vue';
import apiService from '../services/api';

export default {
  name: 'ModelTrainingPage',
  components: {
    FileUploadCard,
    DataTable,
    MapComponent
  },
  setup() {
    const rasters = ref([]);
    const vectors = ref([]);
    const selectedRaster = ref(null);
    const selectedVector = ref(null);

    const fetchData = async () => {
      try {
        const [rasterResponse, vectorResponse] = await Promise.all([
          apiService.fetchRasters(),
          apiService.fetchVectors()
        ]);
        rasters.value = rasterResponse.data;
        vectors.value = vectorResponse.data;
      } catch (error) {
        console.error('Error fetching data:', error);
        // TODO: Show error message to user
      }
    };

    onMounted(fetchData);

    const handleRasterUploaded = () => {
      fetchData();
      // TODO: Show success message to user
    };

    const handleVectorUploaded = () => {
      fetchData();
      // TODO: Show success message to user
    };

    const selectRaster = (raster) => {
      selectedRaster.value = raster;
    };

    const selectVector = (vector) => {
      selectedVector.value = vector;
    };

    return {
      rasters,
      vectors,
      selectedRaster,
      selectedVector,
      handleRasterUploaded,
      handleVectorUploaded,
      selectRaster,
      selectVector,
      rasterColumns: [
        { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
        { name: 'filename', required: true, label: 'Filename', align: 'left', field: 'filename', sortable: true },
        { name: 'description', required: true, label: 'Description', align: 'left', field: 'description', sortable: true },
        { name: 'actions', label: 'Actions', align: 'right' }
      ],
      vectorColumns: [
        { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
        { name: 'filename', required: true, label: 'Filename', align: 'left', field: 'filename', sortable: true },
        { name: 'description', required: true, label: 'Description', align: 'left', field: 'description', sortable: true },
        { name: 'actions', label: 'Actions', align: 'right' }
      ]
    };
  }
};
</script>