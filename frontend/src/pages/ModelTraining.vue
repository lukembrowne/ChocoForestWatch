<template>
  <q-page>
    <div class="q-pa-md">
      <q-card>
        <q-card-section>
          <div class="text-h6">Model Training</div>
          <q-btn label="Upload Raster" color="primary" @click="openFileDialog" class="q-mt-md" />
          <input type="file" ref="rasterFileInput" @change="handleRasterUpload" style="display: none;" />
          <q-linear-progress v-if="uploading" :value="uploadProgress / 100" buffer-color="grey-5" color="primary" class="q-mt-md"></q-linear-progress>
        </q-card-section>
      </q-card>
      <q-card>
        <q-card-section>
          <div class="text-h6">Available Rasters</div>
          <q-table :rows="rasters" :columns="columns" row-key="name" class="q-mt-md">
            <template v-slot:body-cell-actions="props">
              <q-td>
                <q-btn dense flat label="Select" color="primary" @click="selectRaster(props.row.name)" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
      <map-component :raster-url="rasterUrl" class="q-mt-md" />
    </div>
  </q-page>
</template>

<script>
import MapComponent from 'components/MapComponent.vue';

export default {
  name: 'ModelTrainingPage',
  components: {
    MapComponent
  },
  data() {
    return {
      rasterUrl: '',
      uploading: false,
      uploadProgress: 0,
      rasters: [],
      columns: [
        { name: 'name', required: true, label: 'Name', align: 'left', field: 'name' },
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
        formData.append('raster', file);

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
          this.fetchRasters(); // Refresh the raster list
        } catch (error) {
          console.error('Error uploading raster:', error);
          this.uploading = false;
        }
      }
    },
    async fetchRasters() {
      try {
        const response = await fetch('http://127.0.0.1:5000/list_rasters');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        this.rasters = await response.json();
      } catch (error) {
        console.error('Error fetching rasters:', error);
      }
    },
    selectRaster(rasterName) {
      this.rasterUrl = `http://127.0.0.1:5000/uploads/${rasterName}`;
    }
  },
  mounted() {
    this.fetchRasters();
  }
};
</script>