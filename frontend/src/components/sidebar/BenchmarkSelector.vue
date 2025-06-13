<template>
  <div>
    <q-card-section class="q-pt-none q-pb-xs">
      <q-btn color="primary" outline size="sm" class="full-width" icon="add" @click="showDialog = true">
        {{ $t('layers.switcher.benchmarks.title') }}
      </q-btn>
    </q-card-section>

    <q-dialog v-model="showDialog">
      <q-card style="min-width: 1000px">
        <q-card-section class="text-h6">{{ $t('layers.switcher.benchmarks.title') }}</q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-md">
            <div v-for="benchmark in benchmarkOptions" :key="benchmark.value" class="col-12 col-md-6">
              <q-card 
                class="benchmark-card cursor-pointer" 
                :class="{ 'selected': selectedBenchmark === benchmark.value }"
                @click="selectedBenchmark = benchmark.value"
              >
                <q-card-section>
                  <div class="text-h6">{{ $t(`layers.switcher.benchmarks.datasets.${benchmark.value.split('-')[1]}.title`) }}</div>
                  <div class="text-caption q-mt-sm">{{ $t(`layers.switcher.benchmarks.datasets.${benchmark.value.split('-')[1]}.description`) }}</div>
                  <div class="text-caption q-mt-sm">
                    <a :href="$t(`layers.switcher.benchmarks.datasets.${benchmark.value.split('-')[1]}.url`)" target="_blank" class="text-primary" @click.stop>
                      {{ $t('common.learnMore') }}
                    </a>
                  </div>
                </q-card-section>
                <q-card-actions align="right">
                  <q-btn flat color="primary" :label="$t('layers.switcher.benchmarks.add')" @click.stop="addBenchmark(benchmark.value)" />
                </q-card-actions>
              </q-card>
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat :label="$t('common.cancel')" v-close-popup />
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
      { label: 'Hansen Tree Cover 2022', value: 'benchmarks-hansen-tree-cover-2022' },
      { label: 'MapBiomas 2022', value: 'benchmarks-mapbiomes-2022' },
      { label: 'ESA WorldCover 2020', value: 'benchmarks-esa-landcover-2020' },
      { label: 'JRC Forest Cover 2020', value: 'benchmarks-jrc-forestcover-2020' },
      { label: 'PALSAR Forest/Non-Forest 2020', value: 'benchmarks-palsar-2020' },
      { label: 'WRI Tree Cover 2020', value: 'benchmarks-wri-treecover-2020' },
    ]

    const addBenchmark = (val) => {
      mapStore.addBenchmarkLayer(val, 'training')
      showDialog.value = false
    }

    return {
      showDialog,
      benchmarkOptions,
      addBenchmark,
      selectedBenchmark
    }
  }
}
</script>

<style scoped>
/* Add any specific styles for the benchmark selector here if needed */
</style> 