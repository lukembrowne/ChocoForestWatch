<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 900px; max-width: 90vw;">
      <!-- Header -->
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ t('training.evaluation.title') }}</div>
        <div class="text-caption" v-if="metrics">
          {{ t('training.evaluation.created') }}: {{ formatDate(metrics.created_at) }}
          <template v-if="metrics.updated_at">
            | {{ t('training.evaluation.updated') }}: {{ formatDate(metrics.updated_at) }}
          </template>
        </div>
      </q-card-section>

      <q-card-section v-if="!metrics" class="text-center q-pa-lg">
        <q-icon name="warning" size="48px" color="warning" />
        <div class="text-h6 q-mt-md">{{ t('training.evaluation.noMetrics.title') }}</div>
        <div class="text-subtitle2">{{ t('training.evaluation.noMetrics.subtitle') }}</div>
      </q-card-section>

      <template v-if="metrics">
       

        <!-- Performance Metrics Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">{{ t('training.evaluation.metrics.title') }}</div>
          <div class="row q-col-gutter-md">
            <div class="col-12">
              <q-card class="bg-primary text-white">
                <q-card-section>
                  <div class="text-h4 text-center">{{ (metrics.accuracy * 100).toFixed(1) }}%</div>
                  <div class="text-subtitle2 text-center">{{ t('training.evaluation.metrics.overallAccuracy') }}</div>
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

        <!-- Interpretation Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">{{ t('training.evaluation.interpretation.title') }}</div>
          <p>{{ t('training.evaluation.interpretation.accuracy', { accuracy: (metrics.accuracy * 100).toFixed(1) }) }}</p>
          <p>{{ t('training.evaluation.interpretation.keyFindings') }}</p>
          <ul>
            <li v-for="(classMetrics, className) in metrics.class_metrics" :key="className">
              <strong>{{ className }}</strong>:
              <ul>
                <li>{{ t('training.evaluation.interpretation.classMetrics.precision', { 
                  value: (classMetrics.precision * 100).toFixed(1),
                  class: className 
                }) }}</li>
                <li>{{ t('training.evaluation.interpretation.classMetrics.recall', {
                  value: (classMetrics.recall * 100).toFixed(1),
                  class: className
                }) }}</li>
                <li>{{ t('training.evaluation.interpretation.classMetrics.f1', {
                  value: (classMetrics.f1 * 100).toFixed(1)
                }) }}</li>
              </ul>
            </li>
          </ul>
        </q-card-section>

        <!-- Confusion Matrix Section -->
        <q-card-section>
          <div class="text-h6 q-mb-md">{{ t('training.evaluation.confusionMatrix.title') }}</div>
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

        

         <!-- Model Parameters Section -->
         <q-card-section>
          <div class="text-h6 q-mb-md">{{ t('training.evaluation.parameters.title') }}</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <q-list bordered separator>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.splitMethod') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.split_method || 'feature' }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.trainTestSplit') }}</q-item-label>
                    <q-item-label>{{ ((metrics.model_parameters?.train_test_split || 0.2) * 100).toFixed(0) }}%</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.estimators') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.n_estimators || 100 }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.maxDepth') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.max_depth || 3 }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
            <div class="col-12 col-md-6">
              <q-list bordered separator>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.learningRate') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.learning_rate || 0.1 }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.minChildWeight') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.min_child_weight || 1 }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.sieveSize') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.sieve_size || 0 }} {{ t('training.evaluation.parameters.pixels') }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>{{ t('training.evaluation.parameters.subsample') }}</q-item-label>
                    <q-item-label>{{ metrics.model_parameters?.subsample || 0.8 }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </div>
        </q-card-section>


      </template>

      <q-card-actions align="right">
        <q-btn flat :label="t('training.evaluation.close')" color="primary" v-close-popup />
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
import { useI18n } from 'vue-i18n'

export default {
  name: 'ModelEvaluationDialog',
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const projectStore = useProjectStore()
    const { t } = useI18n()
    const selectedModel = ref(null)
    const modelOptions = ref([])
    const metrics = ref(null)
    const loading = ref(false)
    const $q = useQuasar()

    onMounted(async () => {
      console.log("Fetching models")

      try {
        const response = await api.getModelMetrics(projectStore.currentProject.id);
        metrics.value = response.data;
        console.log("Fetched model metrics:", metrics.value);
      } catch (error) {
        console.error("Error fetching model metrics:", error);
      }
    })

    const confusionMatrixColumns = computed(() => {
      if (!metrics.value || !metrics.value.class_names) return [];

      return [
        { name: 'predicted', label: t('training.evaluation.confusionMatrix.predicted'), field: 'predicted', align: 'center' },
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
      { name: 'class', label: t('training.evaluation.metrics.class'), field: 'class', align: 'left' },
      { name: 'precision', label: t('training.evaluation.metrics.precision'), field: 'precision', align: 'center' },
      { name: 'recall', label: t('training.evaluation.metrics.recall'), field: 'recall', align: 'center' },
      { name: 'f1', label: t('training.evaluation.metrics.f1Score'), field: 'f1', align: 'center' }
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
      isHighlightCell,
      t
    }
  }
}
</script>