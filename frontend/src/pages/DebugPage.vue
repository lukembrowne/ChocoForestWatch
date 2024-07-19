<template>
    <q-page padding>
      <h2 class="text-h4 q-mb-md">Store Debug Information</h2>
  
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-6" v-for="(store, storeName) in stores" :key="storeName">
          <q-card>
            <q-card-section>
              <div class="text-h6">{{ storeName }}</div>
              <q-separator class="q-my-md" />
              <pre class="store-content">{{ JSON.stringify(store.$state, null, 2) }}</pre>
            </q-card-section>
          </q-card>
        </div>
      </div>
    </q-page>
  </template>
  
  <script>
  import { defineComponent, reactive } from 'vue';
  import { useTrainingStore } from '../stores/trainingStore';
  import { usePredictionStore } from '../stores/predictionStore';
  import { useAnalysisStore } from '../stores/analysisStore';
  import { useProjectStore } from '../stores/projectStore';
  import { useMapStore } from '../stores/mapStore';

  export default defineComponent({
    name: 'DebugPage',
    setup() {
      const mapStore = useMapStore();
      const trainingStore = useTrainingStore();
      const predictionStore = usePredictionStore();
      const analysisStore = useAnalysisStore();
      const projectStore = useProjectStore();
  
      const stores = reactive({
        // MapStore: mapStore,
        ProjectStore: projectStore,
        TrainingStore: trainingStore,
        PredictionStore: predictionStore,
        AnalysisStore: analysisStore,
      });
  
      return {
        stores,
      };
    },
  });
  </script>
  
  <style scoped>
  .store-content {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: monospace;
    font-size: 0.9em;
  }
  </style>