<template>
  <div class="model-training">
    <h2>XGBoost Model Training</h2>
    <q-form @submit="trainModel" class="q-gutter-md">
      <q-input v-model.number="n_estimators" type="number" label="Number of Trees" />
      <q-input v-model.number="max_depth" type="number" label="Max Depth" />
      <q-input v-model.number="learning_rate" type="number" label="Learning Rate" step="0.01" />
      <q-input v-model.number="n_folds" type="number" label="Number of Cross-validation Folds" />
      <q-btn label="Train Model" type="submit" color="primary"/>
    </q-form>
    <div v-if="results" class="q-mt-md">
      <h3>Training Results</h3>
      <p>Accuracy: {{ results.accuracy }}</p>
      <p>Cross-validation Scores: {{ results.cv_scores.join(', ') }}</p>
      <pre>{{ results.classification_report }}</pre>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import axios from 'axios';

export default {
  setup() {
    const n_estimators = ref(100);
    const max_depth = ref(3);
    const learning_rate = ref(0.1);
    const n_folds = ref(5);
    const results = ref(null);

    const trainModel = async () => {
      try {
        const response = await axios.post('http://127.0.0.1:5000/api/train_model', {
          raster_id: 1,
          n_estimators: n_estimators.value,
          max_depth: max_depth.value,
          learning_rate: learning_rate.value,
          n_folds: n_folds.value
        });
        results.value = response.data;
      } catch (error) {
        console.error('Error training model:', error);
      }
    };

    return {
      n_estimators,
      max_depth,
      learning_rate,
      n_folds,
      results,
      trainModel
    };
  }
}
</script>