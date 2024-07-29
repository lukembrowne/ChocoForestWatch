<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 700px; max-width: 80vw;">
      <q-card-section>
        <div class="text-h6">Model Evaluation</div>
      </q-card-section>

      <q-card-section>
        <q-table :rows="modelOptions" :columns="columns" row-key="id" :loading="loading" v-model:selected="selectedRows"
          @row-click="onRowClick">
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat round icon="edit" @click.stop="openRenameDialog(props.row)" />
              <q-btn flat round icon="delete" @click.stop="confirmDelete(props.row)" />
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-dialog v-model="renameDialog">
        <q-card>
          <q-card-section>
            <div class="text-h6">Rename Model</div>
          </q-card-section>
          <q-card-section>
            <q-input v-model="newModelName" label="New Name" />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Cancel" v-close-popup />
            <q-btn flat label="Rename" @click="renameModel" v-close-popup />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <q-card-section v-if="selectedModel">
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
    const renameDialog = ref(false)
    const newModelName = ref('')
    const modelToRename = ref(null)
    const $q = useQuasar()
    const selectedRows = ref([])



    const columns = [
      { name: 'name', required: true, label: 'Name', align: 'left', field: row => row.name, sortable: true },
      { name: 'actions', align: 'center', label: 'Actions' },
      { name: 'description', align: 'left', label: 'Description', field: 'description', sortable: true },
      { name: 'created_at', align: 'left', label: 'Created At', field: 'created_at', sortable: true },
      { name: 'accuracy', align: 'left', label: 'Accuracy', field: 'accuracy', sortable: true },
      { name: 'training_periods', align: 'left', label: 'Training Periods', field: 'training_periods' },
      { name: 'num_training_samples', align: 'left', label: 'Training Samples', field: 'num_training_samples', sortable: true }
    ]


    onMounted(() => {
      console.log("Fetching models")
      fetchModels()
    })


    const openRenameDialog = (model) => {
      modelToRename.value = model
      newModelName.value = model.name
      renameDialog.value = true
    }

    const renameModel = async () => {
      try {
        await api.renameModel(modelToRename.value.id, newModelName.value)
        $q.notify({
          color: 'positive',
          message: 'Model renamed successfully',
          icon: 'check'
        })
        fetchModels()
      } catch (error) {
        console.error('Error renaming model:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to rename model',
          icon: 'error'
        })
      }
    }

    const confirmDelete = (model) => {
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to delete the model "${model.name}"?`,
        cancel: true,
        persistent: true
      }).onOk(async () => {
        try {
          console.log("Deleting model:", model.id)
          await api.deleteModel(model.id)
          $q.notify({
            color: 'positive',
            message: 'Model deleted successfully',
            icon: 'check'
          })
          fetchModels()
          if (selectedModel.value && selectedModel.value.id === model.id) {
            selectedModel.value = null
          }
        } catch (error) {
          console.error('Error deleting model:', error)
          $q.notify({
            color: 'negative',
            message: 'Failed to delete model',
            icon: 'error'
          })
        }
      })
    }


    const fetchModels = async () => {
      try {
        const response = await api.getTrainedModels(projectStore.currentProject.id)
        modelOptions.value = response
      } catch (error) {
        console.error('Error fetching models:', error)
        throw error
      }
    }

    const onRowClick = async (evt, row) => {
      loading.value = true
      try {
        const response = await api.fetchModelMetrics(row.id)
        selectedModel.value = { ...row, ...response.data }
        metrics.value = response
        console.log("Fetched model metrics:", metrics.value)
      } catch (error) {
        console.error('Error fetching model metrics:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch model metrics',
          icon: 'error'
        })
      }
      loading.value = false
    }

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
      renameDialog,
      newModelName,
      openRenameDialog,
      renameModel,
      confirmDelete,
      loading,
      columns,
      onRowClick,
      selectedRows,
      isClassInTraining,
      getClassTotal
    }
  }
}
</script>