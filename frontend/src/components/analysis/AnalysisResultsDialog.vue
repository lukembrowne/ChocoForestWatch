<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
      <q-card class="analysis-results-dialog" style="width: 700px; max-width: 80vw;">
        <q-card-section>
          <div class="text-h6">Analysis Results</div>
        </q-card-section>
  
        <q-card-section v-if="results.summary">
          <h6>Summary Statistics</h6>
          <div v-for="(value, key) in results.summary" :key="key" class="q-mb-sm">
            <strong>{{ formatLabel(key) }}:</strong> {{ formatValue(value) }}
          </div>
        </q-card-section>
  
        <q-card-section v-if="results.class_statistics">
          <h6>Class Statistics</h6>
          <q-table
            :rows="classStatisticsRows"
            :columns="classStatisticsColumns"
            row-key="class"
            dense
            flat
            :pagination="{ rowsPerPage: 0 }"
          />
        </q-card-section>
  
        <q-card-section v-if="results.change_statistics">
          <h6>Change Statistics</h6>
          <div v-for="(value, key) in results.change_statistics" :key="key" class="q-mb-sm">
            <strong>{{ formatLabel(key) }}:</strong> {{ formatValue(value) }}
          </div>
        </q-card-section>
  
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </template>
  
  <script>
  import { computed } from 'vue';
  import { useDialogPluginComponent } from 'quasar';
  
  export default {
    name: 'AnalysisResultsDialog',
    props: {
      results: {
        type: Object,
        required: true
      }
    },
    emits: [
      ...useDialogPluginComponent.emits
    ],
    setup(props) {
      const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent();
  
      const classStatisticsColumns = [
        { name: 'class', align: 'left', label: 'Class', field: 'class' },
        { name: 'area', align: 'right', label: 'Area (km²)', field: 'area' },
        { name: 'percentage', align: 'right', label: 'Percentage', field: 'percentage' }
      ];
  
      const classStatisticsRows = computed(() => {
        if (!props.results.class_statistics) return [];
        return Object.entries(props.results.class_statistics).map(([className, stats]) => ({
          class: className,
          area: stats.area_km2.toFixed(2),
          percentage: `${stats.percentage.toFixed(2)}%`
        }));
      });
  
      const formatLabel = (key) => {
        return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
      };
  
      const formatValue = (value) => {
        if (typeof value === 'number') {
          return value.toFixed(2);
        }
        return value;
      };
  
      return {
        dialogRef,
        onDialogHide,
        onDialogOK,
        onDialogCancel,
        classStatisticsColumns,
        classStatisticsRows,
        formatLabel,
        formatValue
      };
    }
  };
  </script>