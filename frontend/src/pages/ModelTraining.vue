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
      uploadProgress: 0
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
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();
          this.rasterUrl = data.url;
          this.uploading = false;
        } catch (error) {
          console.error('Error uploading raster:', error);
          this.uploading = false;
        }
      }
    }
  }
};
</script>