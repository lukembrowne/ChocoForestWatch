<!-- New component for displaying AOI summary stats -->
<template>
  <q-card class="q-pa-md">
    <q-card-section>
      <div class="text-h6">Forest-cover summary</div>
    </q-card-section>

    <q-card-section class="q-gutter-sm">
      <q-select
        dense
        outlined
        v-model="benchmark"
        :options="benchmarkOptions"
        option-label="label"
        option-value="value"
        emit-value
        map-options
        label="Benchmark"
        :disable="isDrawing || isLoading"
      />
    </q-card-section>

    <q-separator inset />

    <q-card-section class="q-gutter-md">
      <div v-if="!stats">
        <q-btn color="primary" label="Draw area" @click="startDraw" :loading="isLoading"/>
      </div>

      <div v-else>
        <div class="row items-center q-gutter-sm">
          <q-btn dense icon="refresh" color="green-5" label="Draw new area" @click="clear"/>
        </div>

        <q-markup-table dense flat class="q-mt-sm">
          <tbody>
            <tr>
              <td>Forest (%)</td>
              <td class="text-right">{{ (stats.pct_forest * 100).toFixed(1) }}</td>
            </tr>
            <tr>
              <td>Non-forest (%)</td>
              <td class="text-right">{{ (100 - stats.pct_forest * 100).toFixed(1) }}</td>
            </tr>
            <tr>
              <td>Missing (%)</td>
              <td class="text-right">{{ (stats.pct_missing * 100).toFixed(1) }}</td>
            </tr>
            <tr>
              <td>Forest (ha)</td>
              <td class="text-right">{{ stats.forest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }}</td>
            </tr>
            <tr>
              <td>Non-forest (ha)</td>
              <td class="text-right">{{ stats.nonforest_ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) }}</td>
            </tr>
          </tbody>
        </q-markup-table>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useMapStore } from 'src/stores/mapStore'

const mapStore = useMapStore()

const stats         = computed(() => mapStore.summaryStats)
const isLoading     = computed(() => mapStore.isLoading)
const isDrawing     = computed(() => mapStore.isDrawingSummaryAOI)

const benchmarkOptions = computed(() => mapStore.availableBenchmarks)
const benchmark        = computed({
  get: () => mapStore.selectedBenchmark,
  set: (val) => mapStore.selectedBenchmark = val,
})

// Auto-refresh stats if user changes benchmark and rectangle exists
watch(benchmark, async () => {
  if (stats.value && mapStore.summaryAOILayer) {
    await mapStore.startSummaryAOIDraw(); // triggers new call
  }
})

function startDraw() {
  mapStore.startSummaryAOIDraw()
}

function clear() {
  mapStore.clearSummaryAOI()
}
</script>

<style scoped></style> 