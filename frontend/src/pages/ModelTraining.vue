<template>
  <q-page>
    <div class="q-pa-md">
      <!-- Raster Upload Card -->
      <q-card class="q-mb-md">
        <q-card-section>
          <div class="text-h6">Upload Raster</div>
          <q-input v-model="rasterDescription" label="Raster Description" class="q-mt-md" />
          <q-btn label="Upload Raster" color="primary" @click="openFileDialog('raster')" class="q-mt-md" />
          <input type="file" ref="rasterFileInput" @change="handleRasterUpload" style="display: none;" />
          <q-linear-progress v-if="uploadingRaster" :value="rasterUploadProgress / 100" buffer-color="grey-5" color="primary"
            class="q-mt-md"></q-linear-progress>
        </q-card-section>
      </q-card>

      <!-- Vector Upload Card -->
      <q-card class="q-mb-md">
        <q-card-section>
          <div class="text-h6">Upload Vector</div>
          <q-input v-model="vectorDescription" label="Vector Description" class="q-mt-md" />
          <q-btn label="Upload Vector" color="primary" @click="openFileDialog('vector')" class="q-mt-md" />
          <input type="file" ref="vectorFileInput" @change="handleVectorUpload" style="display: none;" accept=".geojson" />
          <q-linear-progress v-if="uploadingVector" :value="vectorUploadProgress / 100" buffer-color="grey-5" color="primary"
            class="q-mt-md"></q-linear-progress>
        </q-card-section>
      </q-card>

      <q-card class="q-mt-md">
        <q-card-section>
          <div class="text-h6">Available Rasters</div>
          <q-table :rows="rasters" :columns="rasterColumns" row-key="id" class="q-mt-md">
            <template v-slot:body-cell-actions="props">
              <q-td>
                <q-btn dense flat label="Select" color="primary" @click="selectRaster(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <q-card class="q-mt-md">
        <q-card-section>
          <div class="text-h6">Available Vectors</div>
          <q-table :rows="vectors" :columns="vectorColumns" row-key="id" class="q-mt-md">
            <template v-slot:body-cell-actions="props">
              <q-td>
                <q-btn dense flat label="Select" color="primary" @click="selectVector(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <map-component :selected-raster="selectedRaster" :selected-vector="selectedVector" class="q-mt-md" />
    </div>

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
      selectedVector: null,
      uploading: false,
      uploadProgress: 0,
      rasterDescription: '',
      vectorDescription: '',
      rasters: [],
      vectors: [],
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
  },
  methods: {
    openFileDialog(type) {
    if (type === 'raster') {
      this.$refs.rasterFileInput.click();
    } else if (type === 'vector') {
      this.$refs.vectorFileInput.click();
    }
  },
    async handleRasterUpload(event) {
      const file = event.target.files[0];
      if (file) {
        this.uploading = true;
        this.uploadProgress = 0;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('description', this.rasterDescription);

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
    async handleVectorUpload(event) {
      const file = event.target.files[0];
      if (file) {
        this.uploading = true;
        this.uploadProgress = 0;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('description', this.vectorDescription);

        try {
          const response = await axios.post('http://127.0.0.1:5000/upload_vector', formData, {
            onUploadProgress: (progressEvent) => {
              this.uploadProgress = (progressEvent.loaded / progressEvent.total) * 100;
            }
          });
          console.log(response.data);
          this.fetchVectors();
        } catch (error) {
          console.error('Error uploading vector:', error);
        } finally {
          this.uploading = false;
        }
      }
    },
    async fetchRasters() {
      try {
        const response = await axios.get('http://127.0.0.1:5000/api/list_rasters');
        this.rasters = response.data;
        console.log('Fetched rasters:', this.rasters);
      } catch (error) {
        console.error('Error fetching rasters:', error);
      }
    },
    async fetchVectors() {
      try {
        const response = await axios.get('http://127.0.0.1:5000/api/list_vectors');
        this.vectors = response.data;
      } catch (error) {
        console.error('Error fetching vectors:', error);
      }
    },
    selectRaster(raster) {
      console.log('Selecting raster:', raster);
      this.selectedRaster = null; // First, set to null
      this.$nextTick(() => {
        this.selectedRaster = { ...raster }; // Then set the new value
        console.log('Selected raster updated:', this.selectedRaster);
      });
    },
    selectVector(vector) {
      this.selectedVector = vector;
    }
  },
  mounted() {
    this.fetchRasters();
    this.fetchVectors();
  }
};
</script>