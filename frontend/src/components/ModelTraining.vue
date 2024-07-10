<template>
  <div class="model-training">
    <h2>XGBoost Model Training</h2>
    
    <q-table
      title="Pixel Datasets"
      :rows="pixelDatasets"
      :columns="columns"
      row-key="id"
      :selected-rows-label="getSelectedString"
      selection="single"
      v-model:selected="selected"
    />

    <q-form v-if="selected.length > 0" @submit="trainModel" class="q-gutter-md q-mt-md">
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
import { ref, onMounted } from 'vue';
import axios from 'axios';

export default {
  name: 'ModelTraining',
  setup() {
    const pixelDatasets = ref([]);
    const selected = ref([]);
    const n_estimators = ref(100);
    const max_depth = ref(3);
    const learning_rate = ref(0.1);
    const n_folds = ref(5);
    const results = ref(null);

    const columns = [
      { name: 'id', field: 'id', label: 'ID', sortable: true },
      { name: 'raster_filename', field: 'raster_filename', label: 'Raster Filename', sortable: true },
      { name: 'num_pixels', field: 'num_pixels', label: 'Number of Pixels', sortable: true },
      { name: 'class_distribution', field: 'class_distribution', label: 'Class Distribution' }
    ];

    const fetchPixelDatasets = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:5000/api/list_pixel_datasets');
        pixelDatasets.value = response.data;
      } catch (error) {
        console.error('Error fetching pixel datasets:', error);
      }
    };

    const trainModel = async () => {
      if (selected.value.length === 0) return;

      try {
        const response = await axios.post('http://127.0.0.1:5000/api/train_model', {
          pixel_dataset_id: selected.value[0].id,
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

    const getSelectedString = () => {
      return selected.value.length === 0 ? '' : `${selected.value.length} record${selected.value.length > 1 ? 's' : ''} selected of ${pixelDatasets.value.length}`;
    };

    onMounted(fetchPixelDatasets);

    return {
      pixelDatasets,
      selected,
      columns,
      n_estimators,
      max_depth,
      learning_rate,
      n_folds,
      results,
      trainModel,
      getSelectedString
    };
  }
}
</script>