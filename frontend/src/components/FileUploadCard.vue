<template>
  <q-card class="q-mb-md">
    <q-card-section>
      <div class="text-h6">Upload {{ dataType }}</div>
      <q-input v-model="description" :label="`${dataType} Description`" class="q-mt-md" />
      <q-btn :label="`Upload ${dataType}`" color="primary" @click="triggerFileInput" class="q-mt-md" />
      <input type="file" ref="fileInput" @change="handleFileUpload" style="display: none;"
        :accept="acceptedFileTypes" />
      <q-linear-progress v-if="uploading" :value="uploadProgress / 100" buffer-color="grey-5" color="primary"
        class="q-mt-md"></q-linear-progress>
    </q-card-section>
  </q-card>
</template>

<script>
import { ref } from 'vue';
import apiService from '../services/api';

export default {
  name: 'FileUploadCard',
  props: {
    dataType: {
      type: String,
      required: true
    },
    acceptedFileTypes: {
      type: String,
      default: ''
    }
  },
  emits: ['file-uploaded'],
  setup(props, { emit }) {
    const description = ref('');
    const uploading = ref(false);
    const uploadProgress = ref(0);
    const fileInput = ref(null);

    const triggerFileInput = () => {
      fileInput.value.click();
    };

    const handleFileUpload = async (event) => {
      const file = event.target.files[0];
      if (!file) return;

      uploading.value = true;
      uploadProgress.value = 0;

      const formData = new FormData();
      formData.append('file', file);
      formData.append('description', description.value);

      try {

        let response;
        if (props.dataType.toLowerCase() === 'raster') {
          response = await apiService.uploadRaster(formData);
        } else if (props.dataType.toLowerCase() === 'vector') {
          response = await apiService.uploadVector(formData);
        } else {
          throw new Error('Invalid data type');
        }

        console.log(`${props.dataType} uploaded successfully:`, response.data);
        emit('file-uploaded', response.data);
        description.value = '';
      } catch (error) {
        console.error(`Error uploading ${props.dataType.toLowerCase()}:`, error);
        // TODO: Show error message to user
      } finally {
        uploading.value = false;
      }
    };

    return {
      description,
      uploading,
      uploadProgress,
      fileInput,
      triggerFileInput,
      handleFileUpload
    };
  }
};
</script>