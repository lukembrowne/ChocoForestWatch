<template>
  <q-page>
    <div class="q-pa-md">
      <q-card>
        <q-card-section>
          <div class="text-h6">Model Training</div>
          <q-input v-model="description" label="Description" class="q-mt-md" />
          <q-btn label="Upload Raster" color="primary" @click="openFileDialog" class="q-mt-md" />
          <input type="file" ref="rasterFileInput" @change="handleRasterUpload" style="display: none;" />
          <q-linear-progress v-if="uploading" :value="uploadProgress / 100" buffer-color="grey-5" color="primary"
            class="q-mt-md"></q-linear-progress>
        </q-card-section>
      </q-card>
      <q-card>
        <q-card-section>
          <div class="text-h6">Available Rasters</div>
          <q-table :rows="rasters" :columns="columns" row-key="id" class="q-mt-md">
            <template v-slot:body-cell-actions="props">
              <q-td>
                <q-btn dense flat label="Select" color="primary" @click="selectRaster(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
      <map-component :selectedRaster="selectedRaster" class="q-mt-md" />
    </div>
    <div>Selected Raster in ModelTraining: {{ selectedRaster ? selectedRaster.filename : 'None' }}</div>

  </q-page>
</template>

<script>
import axios from 'axios';
import MapComponent from 'components/MapComponent.vue';

export default {
  name: 'ModelTrainingPage',
  components: {
    MapComponent
  },
  data() {
    return {
      selectedRaster: null,
      uploading: false,
      uploadProgress: 0,
      description: '',
      rasters: [],
      columns: [
        { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
        { name: 'filename', required: true, label: 'Filename', align: 'left', field: 'filename', sortable: true },
        { name: 'description', required: true, label: 'Description', align: 'left', field: 'description', sortable: true },
        { name: 'actions', label: 'Actions', align: 'right' }
    ]
    };
  },
  methods: {
    openFileDialog() {
      this.$refs.rasterFileInput.click();
    },
    async handleRasterUpload(event) {
      const file = event.target.files[0];
      if (file) {
        this.uploading = true;
        this.uploadProgress = 0;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('description', this.description);

        try {
          const response = await fetch('http://127.0.0.1:5000/upload_raster', {
            method: 'POST',
            body: formData,
            onprogress: (e) => {
              if (e.lengthComputable) {
                this.uploadProgress = (e.loaded / e.total) * 100;
              }
            }
          });
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();
          this.rasterUrl = data.url;
          this.uploading = false;
          this.fetchRasters();
        } catch (error) {
          console.error('Error uploading raster:', error);
          this.uploading = false;
        }
      }
    },
    async fetchRasters() {
      try {
        const response = await axios.get('http://127.0.0.1:5000/api/rasters');
        this.rasters = response.data;
        console.log('Fetched rasters:', this.rasters);
      } catch (error) {
        console.error('Error fetching rasters:', error);
      }
    },
    selectRaster(raster) {
      console.log('Selecting raster:', raster);
      this.selectedRaster = null; // First, set to null
      this.$nextTick(() => {
        this.selectedRaster = { ...raster }; // Then set the new value
        console.log('Selected raster updated:', this.selectedRaster);
      });
    }
  },
  mounted() {
    this.fetchRasters();
  }
};
</script>