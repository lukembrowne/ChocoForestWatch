<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 700px; max-width: 80vw;">
      <q-card-section>
        <div class="text-h6">Model Evaluation</div>
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
        <q-table :rows="confusionMatrixRows" :columns="confusionMatrixColumns" hide-bottom
          :hide-header="confusionMatrixColumns.length === 0">
          <template v-slot:body="props">
            <q-tr :props="props">
              <q-td key="predicted" :props="props">
                {{ props.row.predicted }}
              </q-td>
              <q-td v-for="column in confusionMatrixColumns.slice(1)" :key="column.name" :props="props">
                {{ props.row[column.name] }}
                <q-badge v-if="isClassInTraining(column.label) && isClassInTraining(props.row.predicted)"
                  color="primary" floating>
                  {{ ((props.row[column.name] / getClassTotal(props.row.predicted)) * 100).toFixed(1) }}%
                </q-badge>
              </q-td>
            </q-tr>
          </template>
        </q-table>

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
import { ref, computed, onMounted } from 'vue'
import { useDialogPluginComponent } from 'quasar'
import api from 'src/services/api'
import { useProjectStore } from 'src/stores/projectStore'
import { useQuasar } from 'quasar'


export default {
  name: 'ModelEvaluationDialog',
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const projectStore = useProjectStore()
    const selectedModel = ref(null)
    const modelOptions = ref([])
    const metrics = ref(null)
    const loading = ref(false)
    const $q = useQuasar()


    onMounted(async () => {
      console.log("Fetching models")

      try {
        // Make the function async
        const response = await api.fetchModelMetrics(projectStore.currentProject.id)
        metrics.value = response
        console.log("Fetched model metrics:", metrics.value)
      } catch (error) {
        console.error("Error fetching model metrics:", error)
      }
    })


    const confusionMatrixColumns = computed(() => {
      if (!metrics.value || !metrics.value.class_names) return [];

      return [
        { name: 'predicted', label: 'Predicted', field: 'predicted', align: 'center' },
        ...metrics.value.class_names.map(className => ({
          name: `actual_${className}`,
          label: className,
          field: `actual_${className}`,
          align: 'center'
        }))
      ];
    });

    const confusionMatrixRows = computed(() => {
      if (!metrics.value || !metrics.value.confusion_matrix) return [];

      const classNames = metrics.value.class_names;
      if (!classNames || classNames.length === 0) return [];

      return classNames.map((className, i) => {
        const row = { predicted: className };
        classNames.forEach((actualClass, j) => {
          row[`actual_${actualClass}`] = metrics.value.confusion_matrix[i][j];
        });
        return row;
      });
    });

    const isClassInTraining = (className) => {
      return metrics.value?.classes_in_training?.includes(className) || false;
    };

    const getClassTotal = (className) => {
      const index = metrics.value.class_names.indexOf(className);
      return metrics.value.confusion_matrix[index].reduce((a, b) => a + b, 0);
    };



    return {
      dialogRef,
      onDialogHide,
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      selectedModel,
      modelOptions,
      metrics,
      confusionMatrixColumns,
      confusionMatrixRows,
      loading,
      isClassInTraining,
      getClassTotal
    }
  }
}
</script>