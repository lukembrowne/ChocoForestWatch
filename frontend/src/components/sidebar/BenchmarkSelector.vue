<template>
  <div>
    <q-card-section class="q-pt-none q-pb-xs flex flex-center">
      <q-btn 
        color="primary" 
        size="sm" 
        class="full-width add-dataset-btn" 
        @click="showDialog = true"
        icon="add_circle_outline"
      >
        {{ $t('layers.switcher.benchmarks.title') }}
      </q-btn>
    </q-card-section>

    <q-dialog v-model="showDialog" class="dataset-dialog">
      <q-card class="dataset-dialog-card">
        <q-card-section class="dialog-header">
          <div class="dialog-title">
            <q-icon name="layers" class="title-icon" />
            <span class="title-text">{{ $t('layers.switcher.benchmarks.title') }}</span>
          </div>
          <div class="dialog-subtitle">{{ $t('layers.switcher.benchmarks.description') }}</div>
        </q-card-section>
        
        <q-card-section class="dialog-content">
          <div class="datasets-grid">
            <div v-for="benchmark in benchmarkOptions" :key="benchmark.value" class="dataset-item">
              <q-card 
                class="dataset-card" 
                :class="{ 'selected': selectedBenchmark === benchmark.value, 'featured': benchmark.value.includes('nicfi-pred') }"
                @click="selectedBenchmark = benchmark.value"
              >
                <div class="card-header">
                  <div class="dataset-icon">
                    <q-icon :name="getDatasetIcon(benchmark.value)" />
                  </div>
                  <div class="featured-badge" v-if="benchmark.value.includes('nicfi-pred')">
                    <q-icon name="star" />
                    <span>{{ $t('layers.switcher.benchmarks.featured') }}</span>
                  </div>
                </div>
                
                <q-card-section class="card-content">
                  <div class="dataset-title">{{ $t(`layers.switcher.benchmarks.datasets.${getDatasetKey(benchmark.value)}.title`) }}</div>
                  <div class="dataset-description">{{ $t(`layers.switcher.benchmarks.datasets.${getDatasetKey(benchmark.value)}.description`) }}</div>
                  
                  <div class="dataset-meta">
                    <div class="meta-item">
                      <q-icon name="map" size="xs" />
                      <span>{{ getDatasetYear(benchmark.value) }}</span>
                    </div>
                    <div class="meta-item">
                      <q-icon name="straighten" size="xs" />
                      <span>{{ getDatasetResolution(benchmark.value) }}</span>
                    </div>
                  </div>
                </q-card-section>
                
                <q-card-actions class="card-actions">
                  <q-btn 
                    flat 
                    size="sm" 
                    :href="$t(`layers.switcher.benchmarks.datasets.${getDatasetKey(benchmark.value)}.url`)" 
                    target="_blank" 
                    class="learn-more-btn"
                    @click.stop
                  >
                    <q-icon name="open_in_new" size="xs" class="q-mr-xs" />
                    {{ $t('common.learnMore') }}
                  </q-btn>
                  <q-btn 
                    color="primary" 
                    :label="$t('layers.switcher.benchmarks.add')" 
                    @click.stop="addBenchmark(benchmark.value)"
                    class="add-btn"
                    icon="add"
                    size="sm"
                  />
                </q-card-actions>
              </q-card>
            </div>
          </div>
        </q-card-section>
        
        <q-card-actions class="dialog-actions">
          <q-btn flat :label="$t('common.cancel')" v-close-popup class="cancel-btn" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useMapStore } from 'src/stores/mapStore'

export default {
  name: 'BenchmarkSelector',
  setup () {
    const mapStore = useMapStore()
    const showDialog = ref(false)
    const selectedBenchmark = ref(null)
    const benchmarkOptions = [
      { label: 'Choco Forest Watch 2022', value: 'nicfi-pred-northern_choco_test_2025_06_09-composite-2022' },
      { label: 'Hansen Global Forest Change', value: 'benchmarks-hansen-tree-cover-2022' },
      { label: 'MapBiomas Ecuador', value: 'benchmarks-mapbiomes-2022' },
      { label: 'ESA WorldCover', value: 'benchmarks-esa-landcover-2020' },
      { label: 'JRC Forest Cover', value: 'benchmarks-jrc-forestcover-2020' },
      { label: 'ALOS PALSAR Forest Map', value: 'benchmarks-palsar-2020' },
      { label: 'WRI Tropical Tree Cover', value: 'benchmarks-wri-treecover-2020' },
      { label: 'GFW Deforestation Alerts 2022', value: 'gfw-alerts-2022' },
    ]

    const addBenchmark = (val) => {
      if (val === 'gfw-alerts-2022') {
        mapStore.addGFWAlertsLayer('training')
      } else {
        mapStore.addBenchmarkLayer(val, 'training')
      }
      showDialog.value = false
    }

    const getDatasetKey = (value) => {
      if (value === 'gfw-alerts-2022') {
        return 'gfw-alerts'
      }
      if (value === 'nicfi-pred-northern_choco_test_2025_06_09-composite-2022') {
        return 'cfw-composite'
      }
      // For other benchmark datasets, extract the second part after splitting by '-'
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
      getDatasetKey,
      getDatasetIcon,
      getDatasetYear,
      getDatasetResolution
    }
  }
}
</script>

<style scoped>
/* Button Styles */
.add-dataset-btn {
  border-radius: 8px;
  font-weight: 500;
  text-transform: none;
  transition: all 0.2s ease;
}

.add-dataset-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
}

/* Dialog Styles */
.dataset-dialog :deep(.q-dialog__inner) {
  padding: 16px;
}

.dataset-dialog-card {
  min-width: 1200px;
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
  padding: 24px;
  flex-shrink: 0;
}

.dialog-title {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.title-icon {
  font-size: 28px;
  color: #4caf50;
  margin-right: 12px;
}

.title-text {
  font-size: 24px;
  font-weight: 600;
  color: #1b5e20;
}

.dialog-subtitle {
  font-size: 14px;
  color: #2e7d32;
  opacity: 0.9;
  margin-left: 40px;
}

.dialog-content {
  padding: 24px;
  background: #fafafa;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

/* Grid Layout */
.datasets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 20px;
}

/* Dataset Cards */
.dataset-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  cursor: pointer;
  border: 2px solid transparent;
  overflow: hidden;
  position: relative;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.dataset-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border-color: #e0e7e4;
}

.dataset-card.selected {
  border-color: #4caf50;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.3);
}

.dataset-card.featured {
  background: linear-gradient(135deg, #fff9e6 0%, #ffffff 100%);
  border-color: #ffc107;
}

.dataset-card.featured.selected {
  border-color: #4caf50;
  background: linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%);
}

/* Card Header */
.card-header {
  position: relative;
  padding: 16px 16px 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.dataset-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.featured-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background: linear-gradient(135deg, #ffc107 0%, #ffca28 100%);
  color: #744e03;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(255, 193, 7, 0.3);
}

.featured-badge .q-icon {
  font-size: 12px;
}

/* Card Content */
.card-content {
  padding: 16px !important;
}

.dataset-title {
  font-size: 16px;
  font-weight: 600;
  color: #1b5e20;
  margin-bottom: 8px;
  line-height: 1.3;
}

.dataset-description {
  font-size: 13px;
  color: #424242;
  line-height: 1.4;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Meta Information */
.dataset-meta {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 6px;
}

.meta-item .q-icon {
  opacity: 0.7;
}

/* Card Actions */
.card-actions {
  padding: 8px 16px 16px !important;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.learn-more-btn {
  color: #666;
  font-size: 12px;
  text-transform: none;
}

.learn-more-btn:hover {
  color: #1976d2;
}

.add-btn {
  border-radius: 8px;
  font-weight: 500;
  text-transform: none;
  min-width: 80px;
}

/* Dialog Actions */
.dialog-actions {
  padding: 16px 24px;
  background: #f9f9f9;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.cancel-btn {
  color: #666;
  text-transform: none;
}

/* Responsive Design */
@media (max-width: 1280px) {
  .dataset-dialog-card {
    min-width: 1000px;
  }
  
  .datasets-grid {
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .dataset-dialog-card {
    min-width: auto;
    width: 95vw;
    margin: 8px;
  }
  
  .datasets-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .dialog-header {
    padding: 20px 16px;
  }
  
  .dialog-content {
    padding: 16px;
  }
  
  .title-text {
    font-size: 20px;
  }
}
</style> 