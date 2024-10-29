<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 900px; max-width: 90vw;">
      <!-- Header -->
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">Model Evaluation</div>
        <div class="text-caption" v-if="metrics">
          Created: {{ formatDate(metrics.created_at) }}
          <template v-if="metrics.updated_at">
            | Updated: {{ formatDate(metrics.updated_at) }}
          </template>
        </div>
      </q-card-section>

      <q-card-section v-if="!metrics" class="text-center q-pa-lg">
        <q-icon name="warning" size="48px" color="warning" />
        <div class="text-h6 q-mt-md">No Model Metrics Available</div>
        <div class="text-subtitle2">Please train a model first.</div>
      </q-card-section>

      <template v-if="metrics">
        <!-- Model Parameters Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">Model Parameters</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <q-list bordered separator>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Split Method</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.split_method || 'feature' }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Train/Test Split</q-item-label>
                    <q-item-label>{{ ((metrics.model_parameters?.train_test_split || 0.2) * 100).toFixed(0) }}%</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Number of Estimators</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.n_estimators || 100 }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Max Depth</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.max_depth || 3 }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
            <div class="col-12 col-md-6">
              <q-list bordered separator>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Learning Rate</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.learning_rate || 0.1 }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Min Child Weight</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.min_child_weight || 1 }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Sieve Filter Size</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.sieve_size || 0 }} pixels</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>Subsample</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.subsample || 0.8 }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </div>
        </q-card-section>

        <!-- Performance Metrics Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">Performance Metrics</div>
          <div class="row q-col-gutter-md">
            <div class="col-12">
              <q-card class="bg-primary text-white">
                <q-card-section>
                  <div class="text-h4 text-center">{{ (metrics.accuracy * 100).toFixed(1) }}%</div>
                  <div class="text-subtitle2 text-center">Overall Accuracy</div>
                </q-card-section>
              </q-card>
            </div>
            
            <div class="col-12">
              <q-table
                flat
                bordered
                :rows="classMetricsRows"
                :columns="classMetricsColumns"
                hide-bottom
              >
                <template v-slot:body="props">
                  <q-tr :props="props">
                    <q-td key="class" :props="props">
                      <q-chip :color="getClassColor(props.row.class)" text-color="black" square>
                        {{ props.row.class }}
                      </q-chip>
                    </q-td>
                    <q-td key="precision" :props="props">{{ props.row.precision }}%</q-td>
                    <q-td key="recall" :props="props">{{ props.row.recall }}%</q-td>
                    <q-td key="f1" :props="props">{{ props.row.f1 }}%</q-td>
                  </q-tr>
                </template>
              </q-table>
            </div>
          </div>
        </q-card-section>

        <!-- Confusion Matrix Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">Confusion Matrix</div>
          <q-table
            flat
            bordered
            :rows="confusionMatrixRows"
            :columns="confusionMatrixColumns"
            hide-bottom
            :hide-header="confusionMatrixColumns.length === 0"
          >
            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td key="predicted" :props="props">
                  <q-chip :color="getClassColor(props.row.predicted)" text-color="black" square>
                    {{ props.row.predicted }}
                  </q-chip>
                </q-td>
                <q-td
                  v-for="column in confusionMatrixColumns.slice(1)"
                  :key="column.name"
                  :props="props"
                  :class="{'bg-green-1': isHighlightCell(props.row.predicted, column.label, props.row[column.name])}"
                >
                  {{ props.row[column.name] }}
                  <q-badge
                    v-if="isClassInTraining(column.label) && isClassInTraining(props.row.predicted)"
                    :color="getCellColor(props.row[column.name], getClassTotal(props.row.predicted))"
                    floating
                  >
                    {{ ((props.row[column.name] / getClassTotal(props.row.predicted)) * 100).toFixed(1) }}%
                  </q-badge>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>

        <!-- Interpretation Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">Interpretation</div>
          <p>The model achieves an overall accuracy of {{ (metrics.accuracy * 100).toFixed(1) }}%, meaning it correctly
            classifies this percentage of all test samples.</p>
          <p>Key findings per class:</p>
          <ul>
            <li v-for="(classMetrics, className) in metrics.class_metrics" :key="className">
              <strong>{{ className }}</strong>:
              <ul>
                <li>Precision: {{ (classMetrics.precision * 100).toFixed(1) }}% of areas predicted as {{ className }} are correct</li>
                <li>Recall: {{ (classMetrics.recall * 100).toFixed(1) }}% of actual {{ className }} areas are correctly identified</li>
                <li>F1 Score: {{ (classMetrics.f1 * 100).toFixed(1) }}% balanced accuracy measure</li>
              </ul>
            </li>
          </ul>
        </q-card-section>
      </template>

      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useDialogPluginComponent, date } from 'quasar'
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

    const formatDate = (dateString) => {
      return date.formatDate(dateString, 'MMMM D, YYYY HH:mm:ss')
    };

    const classMetricsColumns = computed(() => [
      { name: 'class', label: 'Class', field: 'class', align: 'left' },
      { name: 'precision', label: 'Precision', field: 'precision', align: 'center' },
      { name: 'recall', label: 'Recall', field: 'recall', align: 'center' },
      { name: 'f1', label: 'F1 Score', field: 'f1', align: 'center' }
    ]);

    const classMetricsRows = computed(() => {
      if (!metrics.value?.class_metrics) return [];
      return Object.entries(metrics.value.class_metrics).map(([className, metrics]) => ({
        class: className,
        precision: (metrics.precision * 100).toFixed(1),
        recall: (metrics.recall * 100).toFixed(1),
        f1: (metrics.f1 * 100).toFixed(1)
      }));
    });

    const getClassColor = (className) => {
      const classObj = projectStore.currentProject?.classes.find(cls => cls.name === className);
      return classObj ? classObj.color : '#CCCCCC';
    };

    const getCellColor = (value, total) => {
      const percentage = (value / total) * 100;
      if (percentage >= 80) return 'positive';
      if (percentage >= 50) return 'warning';
      return 'negative';
    };

    const isHighlightCell = (predicted, actual, value) => {
      return predicted === actual && value > 0;
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
      getClassTotal,
      formatDate,
      classMetricsColumns,
      classMetricsRows,
      getClassColor,
      getCellColor,
      isHighlightCell
    }
  }
}
</script>