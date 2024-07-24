<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 700px; max-width: 80vw;">
      <q-card-section>
        <div class="text-h6">Model Evaluation</div>
      </q-card-section>

      <q-card-section>
        <q-select v-model="selectedModel" :options="modelOptions" label="Select a model" option-label="name"
          option-value="id" emit-value map-options @update:model-value="loadModelMetrics" />
      </q-card-section>

      <q-card-section v-if="metrics">
        <div class="text-h6">Model Metrics</div>
        <div>Overall Accuracy: {{ (metrics.accuracy * 100).toFixed(2) }}%</div>

        <div v-for="(classMetrics, className) in metrics.class_metrics" :key="className">
          <div class="text-subtitle2 q-mt-sm">{{ className }}</div>
          <div>Precision: {{ (classMetrics.precision * 100).toFixed(2) }}%</div>
          <div>Recall: {{ (classMetrics.recall * 100).toFixed(2) }}%</div>
          <div>F1 Score: {{ (classMetrics.f1 * 100).toFixed(2) }}%</div>
        </div>

        <div class="q-mt-md text-h6">Confusion Matrix</div>
        <q-table v-if="confusionMatrixColumns.length > 0" :rows="confusionMatrixRows" :columns="confusionMatrixColumns"
          hide-bottom />
        <p v-else>Confusion matrix data is not available for this model.</p>

        <div class="q-mt-md text-h6">Interpretation</div>
        <p>The model's overall accuracy is {{ (metrics.accuracy * 100).toFixed(1) }}%. This means it correctly
          classifies all classes {{ (metrics.accuracy * 100).toFixed(1) }}% of the time.</p>
        <p>For each class:</p>
        <ul>
          <li v-for="(classMetrics, className) in metrics.class_metrics" :key="className">
            {{ className }}:
            <ul>
              <li>Precision of {{ (classMetrics.precision * 100).toFixed(1) }}% means that when the model predicts an
                area is {{ className }}, it's correct {{ (classMetrics.precision * 100).toFixed(1) }}% of the time.</li>
              <li>Recall of {{ (classMetrics.recall * 100).toFixed(1) }}% means that the model correctly identifies {{
                (classMetrics.recall * 100).toFixed(1) }}% of all actual {{ className }} areas.</li>
              <li>F1 Score of {{ (classMetrics.f1 * 100).toFixed(1) }}% is a balanced measure of precision and recall,
                where 100% would be perfect performance.</li>
            </ul>
          </li>
        </ul>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { useDialogPluginComponent } from 'quasar'
import { useModelEvaluationStore } from 'src/stores/modelEvaluationStore'

export default {
  name: 'ModelEvaluationDialog',
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const modelEvaluationStore = useModelEvaluationStore()

    const selectedModel = ref(null)
    const metrics = computed(() => modelEvaluationStore.metrics)

    const modelOptions = computed(() => modelEvaluationStore.models)

    const loadModelMetrics = async (modelId) => {
      await modelEvaluationStore.fetchModelMetrics(modelId)
    }

    const confusionMatrixColumns = computed(() => {
      if (!metrics.value || !metrics.value.class_names) {
        // If class_names are not available, try to derive them from class_metrics
        const classNames = Object.keys(metrics.value?.class_metrics || {});
        if (classNames.length === 0) return [];

        return [
          { name: 'predicted', label: 'Predicted', field: 'predicted', align: 'center' },
          ...classNames.map(className => ({
            name: `actual_${className}`,
            label: `Actual ${className}`,
            field: `actual_${className}`,
            align: 'center'
          }))
        ];
      }

      return [
        { name: 'predicted', label: 'Predicted', field: 'predicted', align: 'center' },
        ...metrics.value.class_names.map(className => ({
          name: `actual_${className}`,
          label: `Actual ${className}`,
          field: `actual_${className}`,
          align: 'center'
        }))
      ];
    });

    const confusionMatrixRows = computed(() => {
      if (!metrics.value || !metrics.value.confusion_matrix) return [];

      const classNames = metrics.value.class_names || Object.keys(metrics.value.class_metrics || {});
      if (classNames.length === 0) return [];

      return classNames.map((className, i) => {
        const row = { predicted: className };
        classNames.forEach((actualClass, j) => {
          row[`actual_${actualClass}`] = metrics.value.confusion_matrix[i][j];
        });
        return row;
      });
    });

    return {
      dialogRef,
      onDialogHide,
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      selectedModel,
      modelOptions,
      metrics,
      loadModelMetrics,
      confusionMatrixColumns,
      confusionMatrixRows
    }
  }
}
</script>