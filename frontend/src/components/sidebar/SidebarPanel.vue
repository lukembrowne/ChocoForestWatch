<template>
  <q-card flat bordered class="sidebar-panel column full-height">
    <!-- Location search with suggestions -->
    <q-card-section class="q-pb-none">
      <q-select
        v-model="selectedLabel"
        :options="options"
        use-input
        input-debounce="300"
        dense outlined
        placeholder="Search location"
        prepend-icon="search"
        option-label="label"
        option-value="label"
        @filter="onFilter"
        @update:model-value="onSelect"
        emit-value
        map-options
      >
        <template v-slot:no-option>
          <q-item>
            <q-item-section class="text-grey">No results</q-item-section>
          </q-item>
        </template>
      </q-select>
    </q-card-section>


    <q-separator />

    <div class="q-pa-sm flex column">
      <LandCoverStats />
    </div>
  </q-card>
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
  overflow-y: auto;
}
</style> 