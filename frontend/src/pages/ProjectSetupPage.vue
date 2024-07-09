<template>
    <q-page padding>
      <h2 class="text-h4 q-mb-md">Project Setup</h2>
      <q-form @submit="onSubmit" class="q-gutter-md">
        <q-input
          filled
          v-model="projectName"
          label="Project Name"
          lazy-rules
          :rules="[ val => val && val.length > 0 || 'Please enter a project name']"
        />
  
        <q-input
          filled
          v-model="projectDescription"
          type="textarea"
          label="Project Description"
        />
  
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-file
              filled
              v-model="rasterFile"
              label="Upload Raster File"
              accept=".tif,.tiff"
              @update:model-value="onRasterFileChange"
            >
              <template v-slot:prepend>
                <q-icon name="attach_file" />
              </template>
            </q-file>
          </div>
          <div class="col-12 col-md-6">
            <q-file
              filled
              v-model="vectorFile"
              label="Upload Vector File"
              accept=".geojson"
              @update:model-value="onVectorFileChange"
            >
              <template v-slot:prepend>
                <q-icon name="attach_file" />
              </template>
            </q-file>
          </div>
        </div>
  
        <div>
          <q-btn label="Submit" type="submit" color="primary"/>
        </div>
      </q-form>
    </q-page>
  </template>
  
 
<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import apiService from 'src/services/api';

export default {
  name: 'ProjectSetupPage',
  setup() {
    const $q = useQuasar();
    const router = useRouter();

    const projectName = ref('');
    const projectDescription = ref('');
    const rasterFile = ref(null);
    const vectorFile = ref(null);

    const onRasterFileChange = (file) => {
      if (file) {
        console.log('Raster file selected:', file.name);
      }
    };

    const onVectorFileChange = (file) => {
      if (file) {
        console.log('Vector file selected:', file.name);
      }
    };

    const onSubmit = async () => {
      try {
        // Upload raster file
        if (rasterFile.value) {
          const formData = new FormData();
          formData.append('file', rasterFile.value);
          formData.append('description', projectDescription.value);
          await apiService.uploadRaster(formData);
        }

        // Upload vector file
        if (vectorFile.value) {
          const formData = new FormData();
          formData.append('file', vectorFile.value);
          formData.append('description', projectDescription.value);
          await apiService.uploadVector(formData);
        }

        $q.notify({
          type: 'positive',
          message: 'Project setup completed successfully',
          icon: 'check'
        });

        // Navigate to the next step
        router.push('/data-preparation');
      } catch (error) {
        console.error('Error during project setup:', error);
        $q.notify({
          type: 'negative',
          message: 'An error occurred during project setup',
          icon: 'error'
        });
      }
    };

    return {
      projectName,
      projectDescription,
      rasterFile,
      vectorFile,
      onRasterFileChange,
      onVectorFileChange,
      onSubmit
    };
  }
};
</script>