<template>
    <div class="project-wizard">
      <div class="step-indicator">
        <q-stepper
          v-model="step"
          vertical
          color="primary"
          animated
        >
          <q-step
            :name="1"
            title="Project Setup"
            icon="add_circle"
            :done="step > 1"
          >
            Upload raster and vector data, provide project details
          </q-step>
  
          <q-step
            :name="2"
            title="Data Preparation"
            icon="map"
            :done="step > 2"
          >
            Select areas and extract pixel data
          </q-step>
  
          <q-step
            :name="3"
            title="Model Training"
            icon="school"
            :done="step > 3"
          >
            Set model parameters and train the XGBoost model
          </q-step>
  
          <q-step
            :name="4"
            title="Prediction"
            icon="insights"
          >
            Apply trained model to new data and visualize results
          </q-step>
        </q-stepper>
      </div>
  
      <div class="step-content">
        <router-view></router-view>
      </div>
    </div>
  </template>
  
  <script>
  import { defineComponent, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  
  export default defineComponent({
    name: 'ProjectWizard',
    setup() {
      const step = ref(1);
      const route = useRoute();
  
      const stepMap = {
        '/project-setup': 1,
        '/data-preparation': 2,
        '/model-training': 3,
        '/prediction': 4
      };
  
      watch(() => route.path, (newPath) => {
        step.value = stepMap[newPath] || 1;
      }, { immediate: true });
  
      return {
        step
      };
    }
  });
  </script>
  
  <style scoped>
  .project-wizard {
    display: flex;
    height: 100%;
  }
  
  .step-indicator {
    width: 300px;
    padding: 20px;
  }
  
  .step-content {
    flex-grow: 1;
    padding: 20px;
  }
  </style>