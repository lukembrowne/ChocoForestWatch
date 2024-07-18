<template>
    <div>
      <h2>Predictions</h2>
      <q-list>
        <q-item v-for="prediction in predictions" :key="prediction.id" clickable @click="selectPrediction(prediction)">
          <q-item-section>
            <q-item-label>Prediction {{ prediction.id }}</q-item-label>
            <q-item-label caption>Date: {{ prediction.basemap_date }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </div>
  </template>
  
  <script>
  import { ref, onMounted, computed } from 'vue';
  import apiService from '../services/api';
  import { useProjectStore } from 'src/stores/projectStore'
  
  export default {
    emits: ['predictionSelected'],
    setup(props, { emit }) {
      const predictions = ref([]);
      
      const projectStore = useProjectStore()
      const currentProject = computed(() => projectStore.currentProject)

  
      const fetchPredictions = async () => {
        predictions.value = await apiService.getPredictions(currentProject.value.id);
        console.log('Fetched Predictions', predictions.value);
      };
  
      const selectPrediction = (prediction) => {
        console.log('Selected prediction', prediction);
        emit('predictionSelected', prediction);
      };
  
      onMounted(fetchPredictions);
  
      return { predictions, selectPrediction };
    }
  }
  </script>