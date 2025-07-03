<template>
  <div>
    <!-- Current Dataset Card or Add Button -->
    <div v-if="currentDatasetName" class="current-dataset-card" @click="showDialog = true">
      <div class="current-dataset-header">
        <div class="current-dataset-icon">
          <q-icon :name="getDatasetIcon(currentBenchmark)" />
        </div>
        <div class="current-dataset-info">
          <div class="current-dataset-title">{{ currentDatasetName }}</div>
          <div class="current-dataset-meta">
            <span class="current-dataset-year">{{ getDatasetYear(currentBenchmark) }}</span>
            <span class="current-dataset-resolution">{{ getDatasetResolution(currentBenchmark) }}</span>
            <span v-if="getDatasetVersion(currentBenchmark)" class="current-dataset-version">v{{ getDatasetVersion(currentBenchmark) }}</span>
          </div>
        </div>
       
      </div>
      <div class="current-dataset-actions">
        <q-btn 
          flat 
          size="sm" 
          :href="t(`layers.switcher.benchmarks.datasets.${getDatasetKey(currentBenchmark)}.url`)" 
          target="_blank" 
          class="current-dataset-learn-more"
          @click.stop
        >
          <q-icon name="open_in_new" size="xs" class="q-mr-xs" />
          {{ t('common.learnMore') }}
        </q-btn>
        <q-btn 
          outline
          color="primary"
          size="sm" 
          class="change-dataset-explicit-btn"
          @click.stop="showDialog = true"
          icon="swap_horiz"
          no-caps
        >
          {{ t('analysis.panel.changeDataset') }}
        </q-btn>
      </div>
    </div>
    
    <!-- Add Dataset Button (when no dataset selected) -->
    <q-btn 
      v-else
      color="primary" 
      size="sm" 
      class="full-width add-dataset-btn" 
      @click="showDialog = true"
      icon="add"
      no-caps
    >
      {{ t('analysis.panel.chooseDataset') }}
    </q-btn>

    <q-dialog v-model="showDialog" class="compact-dataset-dialog">
      <q-card class="compact-dataset-dialog-card">
        <q-card-section class="dialog-header">
          <div class="dialog-title">
            <q-icon name="layers" class="title-icon" />
            <span class="title-text">{{ t('layers.switcher.benchmarks.title') }}</span>
          </div>
          <div class="dialog-subtitle">{{ t('layers.switcher.benchmarks.description') }}</div>
        </q-card-section>
        
        <q-card-section class="dialog-content">
          <q-table
            :rows="tableRows"
            :columns="columns"
            row-key="id"
            flat
            class="dataset-table"
            :pagination="{ rowsPerPage: 0 }"
            hide-pagination
            separator="cell"
            :table-header-style="{ fontSize: '13px' }"
          >
            <!-- Row styling -->
            <template v-slot:body="props">
              <q-tr 
                :props="props"
                :class="{ 
                  'table-row-current': props.row.isCurrent,
                  'table-row-featured': props.row.isFeatured && !props.row.isCurrent,
                  'table-row-selected': selectedBenchmark === props.row.value
                }"
                @click="selectRow(props.row.value)"
              >
                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                  <div v-if="col.name === 'dataset'" class="table-dataset-info">
                    <div class="table-dataset-name">
                      <q-icon :name="getDatasetIcon(props.row.value)" class="dataset-inline-icon" />
                      <span>{{ props.row.name }}</span>
                      <div v-if="props.row.isCurrent" class="current-badge-inline">
                        <q-icon name="check_circle" />
                        <span>{{ t('analysis.panel.currentDataset') }}</span>
                      </div>
                      <div v-else-if="props.row.isFeatured" class="featured-badge-inline">
                        <q-icon name="star" />
                        <span>{{ t('layers.switcher.benchmarks.featured') }}</span>
                      </div>
                    </div>
                    <div class="table-dataset-description">
                      {{ props.row.description }}
                      <a
                        :href="props.row.learnMoreUrl"
                        target="_blank"
                        class="inline-learn-more-link"
                      >
                        {{ t('common.learnMore') }}
                      </a>
                    </div>
                  </div>
                  <div v-else-if="col.name === 'year'" class="table-year-badge">{{ props.row.year }}</div>
                  <div v-else-if="col.name === 'resolution'" class="table-resolution-badge">{{ props.row.resolution }}</div>
                  <div v-else-if="col.name === 'actions'" class="table-actions">
                    <q-btn
                      color="primary"
                      size="sm"
                      @click.stop="addBenchmark(props.row.value)"
                      class="table-add-btn"
                      no-caps
                    >
                      <q-icon name="add" size="xs" class="btn-icon" />
                      <span class="btn-text">{{ t('layers.switcher.benchmarks.add') }}</span>
                    </q-btn>
                  </div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
        
        <q-card-actions class="dialog-actions">
          <q-btn flat :label="t('common.cancel')" v-close-popup class="cancel-btn" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useI18n } from 'vue-i18n'

export default {
  name: 'CompactDatasetSelector',
  setup () {
    const mapStore = useMapStore()
    const { t } = useI18n()
    const showDialog = ref(false)
    const selectedBenchmark = ref(null)
    
    // Use benchmarks from mapStore with version information
    const benchmarkOptions = computed(() => [
      ...mapStore.availableDatasets
    ])
    
    // Create table rows from dataset options
    const tableRows = computed(() => {
      return benchmarkOptions.value.map((dataset, index) => ({
        id: index,
        value: dataset.value,
        name: t(`layers.switcher.benchmarks.datasets.${getDatasetKey(dataset.value)}.title`),
        description: t(`layers.switcher.benchmarks.datasets.${getDatasetKey(dataset.value)}.description`),
        year: dataset.year,
        resolution: dataset.resolution,
        version: dataset.version,
        type: dataset.type,
        isCurrent: currentBenchmark.value === dataset.value,
        isFeatured: dataset.value.includes('nicfi-pred'),
        icon: getDatasetIcon(dataset.value),
        learnMoreUrl: t(`layers.switcher.benchmarks.datasets.${getDatasetKey(dataset.value)}.url`)
      }))
    })

    // Table columns configuration
    const columns = [
      {
        name: 'dataset',
        label: t('analysis.panel.table.dataset'),
        field: 'name',
        align: 'left',
        style: 'min-width: 300px;'
      },
      {
        name: 'year',
        label: t('analysis.panel.table.year'),
        field: 'year',
        align: 'center',
        style: 'width: 80px',
        sortable: true
      },
      {
        name: 'resolution',
        label: t('analysis.panel.table.resolution'),
        field: 'resolution',
        align: 'center',
        style: 'width: 100px',
        sortable: true
      },
      {
        name: 'actions',
        label: t('analysis.panel.table.actions'),
        field: 'actions',
        align: 'center',
        style: 'width: 100px'
      }
    ]
    
    // Get currently selected benchmark from store
    const currentBenchmark = computed(() => mapStore.selectedBenchmark)
    
    // Get the display name for current benchmark
    const currentDatasetName = computed(() => {
      if (!currentBenchmark.value) return null
      const dataset = benchmarkOptions.value.find(option => option.value === currentBenchmark.value)
      if (!dataset) return null
      return t(`layers.switcher.benchmarks.datasets.${getDatasetKey(currentBenchmark.value)}.title`)
    })

    const addBenchmark = (val) => {
      try {
        // Handle GFW alerts datasets
        if (val.startsWith('datasets-gfw-integrated-alerts-')) {
          const year = val.split('-').pop(); // Extract year from collection ID
          mapStore.addGFWAlertsLayer(val, year, 'primary')
        } else {
          mapStore.addBenchmarkLayer(val, 'primary')
        }
        // Update the selected benchmark in the store
        mapStore.selectedBenchmark = val
        showDialog.value = false
      } catch (error) {
        console.error('Error adding benchmark:', error)
      }
    }

    const selectRow = (rowValue) => {
      selectedBenchmark.value = rowValue
    }

    const getDatasetKey = (value) => {
      if (value.startsWith('datasets-gfw-integrated-alerts-')) {
        return 'alerts'
      }
      if (value === 'northern_choco_test_2025_06_20_2022_merged_composite') {
        return 'cfw-composite'
      }
      return value.split('-')[1]
    }

    const getDatasetIcon = (value) => {
      if (value.includes('nicfi-pred')) return 'forest'
      if (value.includes('hansen')) return 'satellite_alt'
      if (value.includes('mapbiomes')) return 'terrain'
      if (value.includes('esa')) return 'public'
      if (value.includes('jrc')) return 'park'
      if (value.includes('palsar')) return 'radar'
      if (value.includes('wri')) return 'eco'
      if (value.includes('gfw')) return 'warning'
      return 'layers'
    }

    const getDatasetYear = (value) => {
      const dataset = benchmarkOptions.value.find(b => b.value === value)
      return dataset ? dataset.year : 'Various'
    }

    const getDatasetResolution = (value) => {
      const dataset = benchmarkOptions.value.find(b => b.value === value)
      return dataset ? dataset.resolution : 'Various'
    }
    
    const getDatasetVersion = (value) => {
      const dataset = benchmarkOptions.value.find(b => b.value === value)
      return dataset ? dataset.version : null
    }
    
    const getDatasetType = (value) => {
      const dataset = benchmarkOptions.value.find(b => b.value === value)
      return dataset ? dataset.type : 'dataset'
    }

    return {
      showDialog,
      benchmarkOptions,
      addBenchmark,
      selectedBenchmark,
      currentBenchmark,
      currentDatasetName,
      getDatasetKey,
      getDatasetIcon,
      getDatasetYear,
      getDatasetResolution,
      getDatasetVersion,
      getDatasetType,
      tableRows,
      columns,
      selectRow,
      t
    }
  }
}
</script>

<style scoped>
/* Current Dataset Card Styles */
.current-dataset-card {
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
  border: 2px solid #22c55e;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.15);
}

.current-dataset-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.25);
  border-color: #16a34a;
}

.current-dataset-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.current-dataset-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(34, 197, 94, 0.3);
}

.current-dataset-info {
  flex: 1;
  min-width: 0;
}

.current-dataset-title {
  font-size: 14px;
  font-weight: 600;
  color: #1b5e20;
  line-height: 1.2;
  margin-bottom: 4px;
}

.current-dataset-meta {
  display: flex;
  gap: 8px;
}

.current-dataset-year,
.current-dataset-resolution {
  font-size: 11px;
  color: #16a34a;
  background: rgba(34, 197, 94, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.change-dataset-btn {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.1);
  flex-shrink: 0;
}

.change-dataset-btn:hover {
  background: rgba(34, 197, 94, 0.2);
  color: #15803d;
}

.current-dataset-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.current-dataset-learn-more {
  color: #16a34a;
  font-size: 11px;
  text-transform: none;
  font-weight: 500;
  flex-shrink: 0;
}

.current-dataset-learn-more:hover {
  color: #15803d;
  background: rgba(34, 197, 94, 0.1);
}

.change-dataset-explicit-btn {
  font-size: 12px;
  font-weight: 500;
  text-transform: none;
  border-radius: 6px;
  min-height: 28px;
  padding: 4px 12px;
  flex-shrink: 0;
}

.change-dataset-explicit-btn:hover {
  background: rgba(25, 118, 210, 0.1);
}

/* Add Dataset Button (when no dataset selected) */
.add-dataset-btn {
  border-radius: 6px;
  font-weight: 500;
  text-transform: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: white;
  border: none;
  font-size: 13px;
  min-height: 36px;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.25);
}

.add-dataset-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);
}

/* Dialog Styles */
.compact-dataset-dialog :deep(.q-dialog__inner) {
  padding: 16px;
}

.compact-dataset-dialog-card {
  min-width: 900px;
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.dialog-header {
  background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
  border-bottom: 1px solid #e0e7e4;
  padding: 20px;
  flex-shrink: 0;
}

.dialog-title {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.title-icon {
  font-size: 24px;
  color: #4caf50;
  margin-right: 10px;
}

.title-text {
  font-size: 20px;
  font-weight: 600;
  color: #1b5e20;
}

.dialog-subtitle {
  font-size: 13px;
  color: #2e7d32;
  opacity: 0.9;
  margin-left: 34px;
}

.dialog-content {
  padding: 20px;
  background: #fafafa;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

/* Table Styles */
.dataset-table {
  border-radius: 8px;
  overflow: hidden;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.dataset-table :deep(.q-table__top) {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-bottom: 1px solid #dee2e6;
}

.dataset-table :deep(.q-table__bottom) {
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
}

.dataset-table :deep(thead th) {
  background: #ffffff;
  color: #1a202c;
  font-weight: 700;
  font-size: 14px;
  text-transform: none;
  letter-spacing: 0;
  padding: 18px 16px;
  border-bottom: 3px solid #e2e8f0;
  border-top: 1px solid #e2e8f0;
  position: relative;
}


.dataset-table :deep(tbody tr) {
  transition: all 0.2s ease;
  cursor: pointer;
}

.dataset-table :deep(tbody tr:hover) {
  background: #f8f9fa;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.dataset-table :deep(tbody td) {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  vertical-align: top;
}

/* Table Row States */
.table-row-current {
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%) !important;
  border-left: 4px solid #22c55e !important;
}

.table-row-current:hover {
  background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%) !important;
  box-shadow: 0 2px 12px rgba(34, 197, 94, 0.15) !important;
}

.table-row-featured {
  background: linear-gradient(135deg, #fff9e6 0%, #ffffff 100%) !important;
  border-left: 4px solid #ffc107 !important;
}

.table-row-featured:hover {
  background: linear-gradient(135deg, #fff8e1 0%, #fff9e6 100%) !important;
  box-shadow: 0 2px 12px rgba(255, 193, 7, 0.15) !important;
}

.table-row-selected {
  background: linear-gradient(135deg, #e8f5e8 0%, #f0fdf4 100%) !important;
  border-left: 4px solid #4caf50 !important;
}

/* Table Component Styles */

.table-dataset-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.table-dataset-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a202c;
  line-height: 1.3;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dataset-inline-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.25);
}

.current-badge-inline,
.featured-badge-inline {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-left: auto;
}

.current-badge-inline {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(16, 185, 129, 0.3);
}

.featured-badge-inline {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(245, 158, 11, 0.3);
}

.current-badge-inline .q-icon,
.featured-badge-inline .q-icon {
  font-size: 10px;
}

.table-dataset-description {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
  word-wrap: break-word;
  overflow-wrap: break-word;
  hyphens: auto;
  white-space: normal;
}

.inline-learn-more-link {
  color: #1976d2;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
  transition: all 0.2s ease;
}

.inline-learn-more-link:hover {
  color: #1565c0;
  text-decoration: underline;
}

/* Table Badge Styles */
.table-year-badge,
.table-resolution-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  min-width: 40px;
  justify-content: center;
  white-space: nowrap;
}

.table-year-badge {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  color: #1565c0;
  border: 1px solid #90caf9;
}

.table-resolution-badge {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  color: #7b1fa2;
  border: 1px solid #ce93d8;
}



/* Table Actions */
.table-actions {
  display: flex;
  align-items: center;
  justify-content: center;
}

.table-add-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 8px;
  font-weight: 600;
  text-transform: none;
  min-width: 70px;
  min-height: 32px;
  font-size: 11px;
  padding: 6px 12px;
  color: white;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.table-add-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.table-add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
}

.table-add-btn:hover::before {
  left: 100%;
}

.table-add-btn:active {
  transform: translateY(0);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}

.table-add-btn .btn-icon {
  margin-right: 4px;
}

.table-add-btn .btn-text {
  line-height: 1;
}

/* Dialog Actions */
.dialog-actions {
  padding: 12px 20px;
  background: #f9f9f9;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.cancel-btn {
  color: #666;
  text-transform: none;
}

/* Responsive Design */
@media (max-width: 1200px) {
  .compact-dataset-dialog-card {
    min-width: 700px;
  }
  
  .dataset-table :deep(thead th) {
    padding: 12px 8px;
    font-size: 12px;
  }
  
  .dataset-table :deep(tbody td) {
    padding: 12px 8px;
  }
  
  .table-dataset-name {
    font-size: 13px;
  }
  
  .table-dataset-description {
    font-size: 11px;
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }
  
  .dataset-inline-icon {
    width: 18px;
    height: 18px;
    font-size: 11px;
  }
  
  .table-year-badge,
  .table-resolution-badge {
    font-size: 10px;
    padding: 3px 6px;
    min-width: 35px;
  }
  
  
  .table-add-btn {
    font-size: 10px;
    min-width: 60px;
    min-height: 28px;
    padding: 4px 8px;
  }
}

@media (max-width: 768px) {
  .compact-dataset-dialog-card {
    min-width: auto;
    width: 95vw;
    margin: 8px;
  }
  
  .dialog-header {
    padding: 12px;
  }
  
  .dialog-content {
    padding: 12px;
  }
  
  .title-text {
    font-size: 16px;
  }
  
  .dataset-table :deep(thead th) {
    padding: 8px 4px;
    font-size: 11px;
  }
  
  .dataset-table :deep(tbody td) {
    padding: 8px 4px;
  }
  
  .dataset-inline-icon {
    width: 16px;
    height: 16px;
    font-size: 10px;
  }
  
  .table-dataset-name {
    font-size: 12px;
    gap: 6px;
  }
  
  .table-dataset-description {
    font-size: 10px;
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }
  
  .table-year-badge,
  .table-resolution-badge {
    font-size: 9px;
    padding: 2px 4px;
    min-width: 30px;
  }
  
  .current-badge-inline,
  .featured-badge-inline {
    font-size: 8px;
    padding: 1px 4px;
  }
  
  
  .table-add-btn {
    font-size: 9px;
    min-height: 24px;
    padding: 3px 6px;
    min-width: 50px;
  }
}
</style>