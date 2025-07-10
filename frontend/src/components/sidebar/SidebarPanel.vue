<template>
  <div class="sidebar-panel column full-height">
    <!-- Content Section -->
    <div class="content-section">
      <AnalysisPanel />
    </div>

     <!-- Search Section - Commented out for now -->
     <!--
     <div class="search-section">
      <div 
        class="section-header" 
        @click="toggleSearchSection"
        @keydown.enter="toggleSearchSection"
        @keydown.space="toggleSearchSection"
        tabindex="0"
        role="button"
        :aria-expanded="searchSectionExpanded"
        :aria-label="t('sidebar.search.title') + ' - ' + (searchSectionExpanded ? t('sidebar.collapse') : t('sidebar.expand'))"
      >
        <div class="section-label">
          <q-icon name="search" class="section-icon" />
          {{ t('sidebar.search.title') }}
        </div>
        <q-btn 
          flat 
          round 
          dense 
          size="sm" 
          :icon="searchSectionExpanded ? 'expand_less' : 'expand_more'" 
          class="expand-btn"
          tabindex="-1"
          :aria-hidden="true"
        >
          <q-tooltip>{{ searchSectionExpanded ? t('sidebar.collapse') : t('sidebar.expand') }}</q-tooltip>
        </q-btn>
      </div>
      
      <q-slide-transition>
        <div v-show="searchSectionExpanded" class="section-content">
          <q-select
            v-model="selectedLabel"
            :options="options"
            use-input
            input-debounce="300"
            outlined
            :placeholder="t('sidebar.search.placeholder')"
            option-label="label"
            option-value="label"
            @filter="onFilter"
            @update:model-value="onSelect"
            emit-value
            map-options
            class="search-input"
            :loading="isSearching"
          >
            <template v-slot:prepend>
              <q-icon name="place" color="primary" />
            </template>
            <template v-slot:append v-if="isSearching">
              <q-spinner color="primary" size="sm" />
            </template>
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey-6">
                  <div class="text-center">
                    <q-icon name="search_off" size="md" class="q-mb-sm" />
                    <div>{{ t('sidebar.search.noResults') }}</div>
                    <div class="text-caption">{{ t('sidebar.search.tryDifferent') }}</div>
                  </div>
                </q-item-section>
              </q-item>
            </template>
          </q-select>
          
          <div v-if="searchFeedback" class="search-feedback" :class="`feedback-${searchFeedback.color}`">
            <q-icon :name="searchFeedback.icon" size="sm" />
            <span class="feedback-message">{{ searchFeedback.message }}</span>
          </div>
        </div>
        </q-slide-transition>
      </div>
    -->

  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useI18n } from 'vue-i18n'

import AnalysisPanel from '../analysis/AnalysisPanel.vue'

const mapStore = useMapStore()
const { t } = useI18n()

// Search functionality - commented out for now
/*
const options = ref([])
const selectedLabel = ref('')

// Search state
const isSearching = ref(false)
const searchFeedback = ref(null)

// Section expansion state - initialize based on local storage or defaults
const searchSectionExpanded = ref(
  localStorage.getItem('sidebar-search-expanded') === 'true'
)

// Watch for expansion state changes and save to localStorage
watch(searchSectionExpanded, (newValue) => {
  localStorage.setItem('sidebar-search-expanded', newValue.toString())
})

// Search section toggle
const toggleSearchSection = () => {
  searchSectionExpanded.value = !searchSectionExpanded.value
}
*/

// Search functions - commented out for now
/*
const onFilter = async (val, update, abort) => {
  if (val === '') {
    options.value = []
    update()
    return
  }

  isSearching.value = true
  searchFeedback.value = null

  try {
    const res = await mapStore.searchLocation(val)
    update(() => {
      options.value = res
      if (res.length === 0) {
        searchFeedback.value = {
          icon: 'search_off',
          color: 'warning',
          message: t('sidebar.search.noResultsFor', { query: val })
        }
      } else {
        searchFeedback.value = {
          icon: 'check_circle',
          color: 'positive',
          message: t('sidebar.search.foundResults', { count: res.length })
        }
      }
    })
  } catch (error) {
    searchFeedback.value = {
      icon: 'error',
      color: 'negative',
      message: t('sidebar.search.error')
    }
    abort()
  } finally {
    isSearching.value = false
    // Clear feedback after a delay
    setTimeout(() => {
      searchFeedback.value = null
    }, 3000)
  }
}

const onSelect = (val) => {
  const result = options.value.find(o => o.label === val)
  if (result) {
    mapStore.zoomToSearchResult(result)
    searchFeedback.value = {
      icon: 'my_location',
      color: 'positive',
      message: t('sidebar.search.navigatedTo', { location: val })
    }
    
    // Clear feedback after navigation
    setTimeout(() => {
      searchFeedback.value = null
    }, 2000)
  }
}
*/
</script>

<style scoped>
.sidebar-panel {
  background: linear-gradient(180deg, #f8fffe 0%, #ffffff 100%);
  overflow-y: auto;
  border-right: 1px solid #e0e7e4;
  position: relative;
  scroll-behavior: smooth;
  /* Optimize for mobile scrolling */
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.content-section {
  flex: 1;
  padding: 16px;
  background: white;
  overflow-y: auto;
}

.search-section {
  padding: 20px 16px;
  background: white;
  border-top: 1px solid #e8f5e8;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 8px 0;
  border-radius: 8px;
  transition: background-color 0.2s ease;
  outline: none;
}

.section-header:hover {
  background: rgba(76, 175, 80, 0.05);
}

.section-header:focus {
  background: rgba(76, 175, 80, 0.1);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.section-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #2e7d32;
  font-size: 13px;
}

.section-icon {
  font-size: 18px;
  margin-right: 6px;
}

.expand-btn {
  transition: transform 0.2s ease;
}

.section-content {
  padding-top: 16px;
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

.search-feedback {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  animation: slideIn 0.3s ease;
}

.feedback-positive {
  background: rgba(76, 175, 80, 0.1);
  color: #2e7d32;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.feedback-warning {
  background: rgba(255, 193, 7, 0.1);
  color: #f57c00;
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.feedback-negative {
  background: rgba(244, 67, 54, 0.1);
  color: #c62828;
  border: 1px solid rgba(244, 67, 54, 0.3);
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .search-section {
    padding: 16px 12px;
  }
  
  .content-section {
    padding: 12px;
  }
}
</style>