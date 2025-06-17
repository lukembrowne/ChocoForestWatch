<template>
  <div class="sidebar-panel column full-height">

   
    <!-- Content Section -->
    <div class="content-section">
      <LandCoverStats />
    </div>

     <!-- Search Section -->
     <div class="search-section">
      <div class="section-label">
        <q-icon name="search" class="section-icon" />
        Location Search
      </div>
      <q-select
        v-model="selectedLabel"
        :options="options"
        use-input
        input-debounce="300"
        outlined
        placeholder="Search for any location..."
        option-label="label"
        option-value="label"
        @filter="onFilter"
        @update:model-value="onSelect"
        emit-value
        map-options
        class="search-input"
      >
        <template v-slot:prepend>
          <q-icon name="place" color="primary" />
        </template>
        <template v-slot:no-option>
          <q-item>
            <q-item-section class="text-grey-6">
              <div class="text-center">
                <q-icon name="search_off" size="md" class="q-mb-sm" />
                <div>No locations found</div>
                <div class="text-caption">Try a different search term</div>
              </div>
            </q-item-section>
          </q-item>
        </template>
      </q-select>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useMapStore } from 'src/stores/mapStore'

import LandCoverStats from '../LandCoverStats.vue'

const mapStore   = useMapStore()

const options        = ref([])
const selectedLabel  = ref('')

const onFilter = (val, update, abort) => {
  if (val === '') {
    options.value = []
    update()
    return
  }
  mapStore.searchLocation(val).then(res => {
    update(() => {
      options.value = res
    })
  })
}

const onSelect = (val) => {
  const result = options.value.find(o => o.label === val)
  if (result) {
    mapStore.zoomToSearchResult(result)
  }
}
</script>

<style scoped>
.sidebar-panel {
  background: linear-gradient(180deg, #f8fffe 0%, #ffffff 100%);
  overflow-y: auto;
  border-right: 1px solid #e0e7e4;
}


.search-section {
  padding: 20px 16px;
  background: white;
  border-bottom: 1px solid #e8f5e8;
}

.section-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #2e7d32;
  margin-bottom: 12px;
  font-size: 14px;
}

.section-icon {
  font-size: 18px;
  margin-right: 6px;
}

.search-input {
  border-radius: 8px;
}

.search-input :deep(.q-field__control) {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s ease;
}

.search-input :deep(.q-field__control):hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.search-input :deep(.q-field--focused .q-field__control) {
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.15);
}

.content-section {
  flex: 1;
  padding: 16px;
  background: white;
  overflow-y: auto;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .sidebar-header {
    padding: 16px 12px 12px;
  }
  
  .header-text {
    font-size: 16px;
  }
  
  .search-section {
    padding: 16px 12px;
  }
  
  .content-section {
    padding: 12px;
  }
}
</style> 