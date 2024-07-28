Updated LoadTrainingSetDialog.vue

<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 900px; max-width: 90vw;">
      <q-card-section>
        <div class="text-h6">Load Training Set</div>
      </q-card-section>

      <q-card-section>
        <q-table :rows="trainingSets" :columns="columns" row-key="id" @row-click="onRowClick">
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat round icon="edit" @click.stop="openRenameDialog(props.row)" />
              <q-btn flat round icon="delete" @click.stop="confirmDelete(props.row)" />
              <q-btn flat round icon="save" @click.stop="saveToFile(props.row)" />
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Cancel" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <!-- Rename Dialog -->
  <q-dialog v-model="renameDialog">
    <q-card>
      <q-card-section>
        <div class="text-h6">Rename Training Set</div>
      </q-card-section>
      <q-card-section>
        <q-input v-model="newName" label="New Name" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="Cancel" v-close-popup />
        <q-btn flat label="Rename" @click="renameTrainingSet" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useDialogPluginComponent, useQuasar } from 'quasar';
import api from 'src/services/api';
import { useProjectStore } from 'src/stores/projectStore'


export default {
  name: 'LoadTrainingSetDialog',
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent();
    const trainingSets = ref([]);
    const projectStore = useProjectStore()
    const $q = useQuasar();

    const renameDialog = ref(false);
    const newName = ref('');
    const trainingSetToRename = ref(null);

    const columns = [
      { name: 'actions', align: 'center', label: 'Actions' },
      { name: 'name', required: true, label: 'Name', align: 'left', field: 'name' },
      { name: 'basemap_date', align: 'center', label: 'Basemap Date', field: 'basemap_date' },
      { name: 'feature_count', align: 'center', label: 'Features', field: 'feature_count' },
      { name: 'created_at', align: 'center', label: 'Created', field: 'created_at' }
    ];

    onMounted(async () => {
      const response = await api.getTrainingPolygons(projectStore.currentProject.id);
      trainingSets.value = response.data;
    });

    const onRowClick = (evt, row) => {
      onDialogOK(row);
    };

    const openRenameDialog = (row) => {
      trainingSetToRename.value = row;
      newName.value = row.name;
      renameDialog.value = true;
    };
    const renameTrainingSet = async () => {
      try {
        await api.updateTrainingPolygons({
          project_id: projectStore.currentProject.id,
          id: trainingSetToRename.value.id,
          name: newName.value
        });
        const index = trainingSets.value.findIndex(set => set.id === trainingSetToRename.value.id);
        if (index !== -1) {
          trainingSets.value[index].name = newName.value;
        }
        $q.notify({
          color: 'positive',
          message: 'Training set renamed successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error renaming training set:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to rename training set',
          icon: 'error'
        });
      }
    };

    const confirmDelete = (row) => {
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to delete the training set "${row.name}"?`,
        cancel: true,
        persistent: true
      }).onOk(async () => {
        try {
          await api.deleteTrainingSet(projectStore.currentProject.id, row.id);
          trainingSets.value = trainingSets.value.filter(set => set.id !== row.id);
          $q.notify({
            color: 'positive',
            message: 'Training set deleted successfully',
            icon: 'check'
          });
        } catch (error) {
          console.error('Error deleting training set:', error);
          $q.notify({
            color: 'negative',
            message: 'Failed to delete training set',
            icon: 'error'
          });
        }
      });
    };

    const saveToFile = async (row) => {
      try {
        const response = await api.getSpecificTrainingPolygons(projectStore.currentProject.id, row.id);
        const geoJsonData = response.data;
        const blob = new Blob([JSON.stringify(geoJsonData)], { type: 'application/json' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${row.name}.geojson`;
        link.click();
        URL.revokeObjectURL(link.href);
        $q.notify({
          color: 'positive',
          message: 'Training set saved to file successfully',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error saving training set to file:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to save training set to file',
          icon: 'error'
        });
      }
    };

    return {
      dialogRef,
      onDialogHide,
      onDialogOK,
      onDialogCancel,
      trainingSets,
      columns,
      onRowClick,
      renameDialog,
      newName,
      openRenameDialog,
      renameTrainingSet,
      confirmDelete,
      saveToFile
    };
  },
};
</script>