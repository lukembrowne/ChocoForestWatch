<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
      <q-card class="q-dialog-plugin" style="width: 700px; max-width: 80vw;">
        <q-card-section>
          <div class="text-h6">Load Training Set</div>
        </q-card-section>
  
        <q-card-section>
          <q-table
            :rows="trainingSets"
            :columns="columns"
            row-key="id"
            @row-click="onRowClick"
          />
        </q-card-section>
  
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </template>
  
  <script>
  import { ref, onMounted } from 'vue';
  import { useDialogPluginComponent } from 'quasar';
  import api from 'src/services/api';
  import { useProjectStore } from 'src/stores/projectStore'

  
  export default {
    name: 'LoadTrainingSetDialog',
    emits: [...useDialogPluginComponent.emits],
  
    setup() {
      const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent();
      const trainingSets = ref([]);
      const projectStore = useProjectStore()

  
      const columns = [
        { name: 'name', required: true, label: 'Name', align: 'left', field: 'name' },
        { name: 'basemap_date', align: 'center', label: 'Basemap Date', field: 'basemap_date' },
        { name: 'feature_count', align: 'center', label: 'Features', field: 'feature_count' },
        { name: 'created_at', align: 'center', label: 'Created', field: 'created_at' },
      ];
  
      onMounted(async () => {
        const response = await api.getTrainingPolygonSets( projectStore.currentProject.id);
        trainingSets.value = response.data;
      });
  
      const onRowClick = (evt, row) => {
        onDialogOK(row);
      };
  
      return {
        dialogRef,
        onDialogHide,
        onDialogOK,
        onDialogCancel,
        trainingSets,
        columns,
        onRowClick,
      };
    },
  };
  </script>