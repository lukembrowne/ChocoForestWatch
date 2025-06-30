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
          </div>
        </div>
        <q-btn 
          flat 
          round 
          dense 
          size="sm" 
          icon="edit" 
          class="change-dataset-btn"
          @click.stop="showDialog = true"
        >
          <q-tooltip>{{ t('analysis.panel.clickToChange') }}</q-tooltip>
        </q-btn>
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
          <div class="compact-datasets-grid">
            <div v-for="benchmark in benchmarkOptions" :key="benchmark.value" class="compact-dataset-item">
              <q-card 
                class="compact-dataset-card" 
                :class="{ 
                  'selected': selectedBenchmark === benchmark.value, 
                  'current': currentBenchmark === benchmark.value,
                  'featured': benchmark.value.includes('nicfi-pred') 
                }"
                @click="selectedBenchmark = benchmark.value"
              >
                <div class="compact-card-header">
                  <div class="compact-dataset-icon">
                    <q-icon :name="getDatasetIcon(benchmark.value)" />
                  </div>
                  <div class="current-badge" v-if="currentBenchmark === benchmark.value">
                    <q-icon name="check_circle" />
                    <span>{{ t('analysis.panel.currentDataset') }}</span>
                  </div>
                  <div class="featured-badge" v-else-if="benchmark.value.includes('nicfi-pred')">
                    <q-icon name="star" />
                    <span>{{ t('layers.switcher.benchmarks.featured') }}</span>
                  </div>
                </div>
                
                <q-card-section class="compact-card-content">
                  <div class="compact-dataset-title">{{ t(`layers.switcher.benchmarks.datasets.${getDatasetKey(benchmark.value)}.title`) }}</div>
                  <div class="compact-dataset-description">{{ t(`layers.switcher.benchmarks.datasets.${getDatasetKey(benchmark.value)}.description`) }}</div>
                  
                  <div class="compact-dataset-meta">
                    <div class="compact-meta-item">
                      <q-icon name="map" size="xs" />
                      <span>{{ getDatasetYear(benchmark.value) }}</span>
                    </div>
                    <div class="compact-meta-item">
                      <q-icon name="straighten" size="xs" />
                      <span>{{ getDatasetResolution(benchmark.value) }}</span>
                    </div>
                  </div>
                </q-card-section>
                
                <q-card-actions class="compact-card-actions">
                  <q-btn 
                    flat 
                    size="xs" 
                    :href="t(`layers.switcher.benchmarks.datasets.${getDatasetKey(benchmark.value)}.url`)" 
                    target="_blank" 
                    class="compact-learn-more-btn"
                    @click.stop
                  >
                    <q-icon name="open_in_new" size="xs" class="q-mr-xs" />
                    {{ t('common.learnMore') }}
                  </q-btn>
                  <q-btn 
                    color="primary" 
                    :label="t('layers.switcher.benchmarks.add')" 
                    @click.stop="addBenchmark(benchmark.value)"
                    class="compact-add-btn"
                    icon="add"
                    size="s"
                  />
                </q-card-actions>
              </q-card>
            </div>
          </div>
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
    
    const benchmarkOptions = [
      { label: 'Choco Forest Watch 2022', value: 'northern_choco_test_2025_06_20_2022_merged_composite' },
      { label: 'Hansen Global Forest Change', value: 'benchmarks-hansen-tree-cover-2022' },
      { label: 'MapBiomas Ecuador', value: 'benchmarks-mapbiomes-2022' },
      { label: 'ESA WorldCover', value: 'benchmarks-esa-landcover-2020' },
      { label: 'JRC Forest Cover', value: 'benchmarks-jrc-forestcover-2020' },
      { label: 'ALOS PALSAR Forest Map', value: 'benchmarks-palsar-2020' },
      { label: 'WRI Tropical Tree Cover', value: 'benchmarks-wri-treecover-2020' },
      { label: 'GFW Deforestation Alerts 2022', value: 'gfw-alerts-2022' },
    ]
    
    // Get currently selected benchmark from store
    const currentBenchmark = computed(() => mapStore.selectedBenchmark)
    
    // Get the display name for current benchmark
    const currentDatasetName = computed(() => {
      if (!currentBenchmark.value) return null
      const dataset = benchmarkOptions.find(option => option.value === currentBenchmark.value)
      if (!dataset) return null
      return t(`layers.switcher.benchmarks.datasets.${getDatasetKey(currentBenchmark.value)}.title`)
    })

    const addBenchmark = (val) => {
      if (val === 'gfw-alerts-2022') {
        mapStore.addGFWAlertsLayer('primary')
      } else {
        mapStore.addBenchmarkLayer(val, 'primary')
      }
      // Update the selected benchmark in the store
      mapStore.selectedBenchmark = val
      showDialog.value = false
    }

    const getDatasetKey = (value) => {
      if (value === 'gfw-alerts-2022') {
        return 'gfw-alerts'
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
      if (value.includes('2022')) return '2022'
      if (value.includes('2020')) return '2020'
      return 'Various'
    }

    const getDatasetResolution = (value) => {
      if (value.includes('hansen')) return '30m'
      if (value.includes('mapbiomes')) return '30m'
      if (value.includes('esa')) return '10m'
      if (value.includes('jrc')) return '10m'
      if (value.includes('palsar')) return '25m'
      if (value.includes('wri')) return '10m'
      if (value.includes('nicfi-pred')) return '4.7m'
      return 'Various'
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
  min-width: 1000px;
  max-width: 95vw;
  max-height: 90vh;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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

/* Compact Grid Layout */
.compact-datasets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

/* Compact Dataset Cards */
.compact-dataset-card {
  border-radius: 10px;
  transition: all 0.3s ease;
  cursor: pointer;
  border: 2px solid transparent;
  overflow: hidden;
  position: relative;
  background: white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  height: 240px;
  display: flex;
  flex-direction: column;
}

.compact-dataset-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
  border-color: #e0e7e4;
}

.compact-dataset-card.selected {
  border-color: #4caf50;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.25);
}

.compact-dataset-card.current {
  border-color: #22c55e;
  box-shadow: 0 4px 16px rgba(34, 197, 94, 0.3);
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
}

.compact-dataset-card.featured {
  background: linear-gradient(135deg, #fff9e6 0%, #ffffff 100%);
  border-color: #ffc107;
}

.compact-dataset-card.featured.selected {
  border-color: #4caf50;
  background: linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%);
}

.compact-dataset-card.featured.current {
  border-color: #22c55e;
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
}

/* Compact Card Header */
.compact-card-header {
  position: relative;
  padding: 16px 16px 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-shrink: 0;
}

.compact-dataset-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  box-shadow: 0 2px 6px rgba(76, 175, 80, 0.25);
}

.current-badge {
  display: flex;
  align-items: center;
  gap: 3px;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
  padding: 3px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(34, 197, 94, 0.3);
}

.current-badge .q-icon {
  font-size: 10px;
}

.featured-badge {
  display: flex;
  align-items: center;
  gap: 3px;
  background: linear-gradient(135deg, #ffc107 0%, #ffca28 100%);
  color: #744e03;
  padding: 3px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(255, 193, 7, 0.25);
}

.featured-badge .q-icon {
  font-size: 10px;
}

/* Compact Card Content */
.compact-card-content {
  padding: 12px 16px !important;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.compact-dataset-title {
  font-size: 15px;
  font-weight: 600;
  color: #1b5e20;
  margin-bottom: 8px;
  line-height: 1.3;
}

.compact-dataset-description {
  font-size: 12px;
  color: #424242;
  line-height: 1.4;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

/* Compact Meta Information */
.compact-dataset-meta {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.compact-meta-item {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  color: #666;
  background: #f5f5f5;
  padding: 3px 6px;
  border-radius: 4px;
}

.compact-meta-item .q-icon {
  opacity: 0.7;
}

/* Compact Card Actions */
.compact-card-actions {
  padding: 8px 16px 12px !important;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.compact-learn-more-btn {
  color: #666;
  font-size: 12px;
  text-transform: none;
  min-height: 28px;
  padding: 4px 8px;
}

.compact-learn-more-btn:hover {
  color: #1976d2;
}

.compact-add-btn {
  border-radius: 6px;
  font-weight: 500;
  text-transform: none;
  min-width: 70px;
  min-height: 28px;
  font-size: 12px;
  padding: 4px 12px;
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
    min-width: 800px;
  }
  
  .compact-datasets-grid {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 10px;
  }
}

@media (max-width: 768px) {
  .compact-dataset-dialog-card {
    min-width: auto;
    width: 95vw;
    margin: 8px;
  }
  
  .compact-datasets-grid {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 8px;
  }
  
  .dialog-header {
    padding: 16px;
  }
  
  .dialog-content {
    padding: 16px;
  }
  
  .title-text {
    font-size: 18px;
  }
  
  .compact-dataset-card {
    height: 180px;
  }
}
</style>