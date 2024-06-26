<template>
    <q-page>
      <div class="q-pa-md">
        <q-card>
          <q-card-section>
            <div class="text-h6">Upload Data</div>
            <div class="q-mt-md">
              <q-uploader
                label="Upload Raster File"
                accept=".tif"
                @added="handleRasterFileAdded"
                ref="rasterUploader"
              />
            </div>
            <div class="q-mt-md">
              <q-uploader
                label="Upload GeoJSON File"
                accept=".geojson"
                @added="handleGeoJSONFileAdded"
                ref="geojsonUploader"
              />
            </div>
          </q-card-section>
  
          <q-card-actions align="right">
            <q-btn label="Submit" color="primary" @click="handleSubmit" />
          </q-card-actions>
        </q-card>
      </div>
    </q-page>
  </template>
  
  <script>
  export default {
    name: 'UploadData',
    data() {
      return {
        rasterFile: null,
        geojsonFile: null,
      }
    },
    methods: {
      handleRasterFileAdded(files) {
        this.rasterFile = files[0];
      },
      handleGeoJSONFileAdded(files) {
        this.geojsonFile = files[0];
      },
      handleSubmit() {
        if (!this.rasterFile || !this.geojsonFile) {
          this.$q.notify({
            type: 'negative',
            message: 'Please upload both raster and GeoJSON files.',
          });
          return;
        }
  
        const formData = new FormData();
        formData.append('raster', this.rasterFile);
        formData.append('geojson', this.geojsonFile);
  
        fetch('http://localhost:5000/upload', {
          method: 'POST',
          body: formData,
        })
          .then(response => response.json())
          .then(data => {
            this.$q.notify({
              type: 'positive',
              message: 'Files uploaded successfully!',
            });
          })
          .catch(error => {
            console.error('Error uploading files:', error);
            this.$q.notify({
              type: 'negative',
              message: 'Failed to upload files.',
            });
          });
      },
    },
  }
  </script>
  
  <style scoped>
  .q-uploader {
    max-width: 100%;
  }
  </style>