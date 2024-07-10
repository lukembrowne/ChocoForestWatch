<template>
    <div class="training-store-debug">
      <q-card>
        <q-card-section>
          <pre>{{ storeState }}</pre>
        </q-card-section>
      </q-card>
    </div>
  </template>
  
  <script>
  import { computed } from 'vue';
  import { useTrainingStore } from '../stores/trainingStore';
  
  export default {
    name: 'TrainingStoreDebug',
    setup() {
      const trainingStore = useTrainingStore();
  
      const storeState = computed(() => JSON.stringify(trainingStore.$state, null, 2));
  
      return {
        storeState
      };
    }
  };
  </script>
  
  <style scoped>
  .training-store-debug pre {
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  </style>