<template>
  <q-page class="flex">
    <div class="full-width">
      <div id="map" style="width: 100%; height: 400px;"></div>
    </div>

    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-fab icon="add" direction="up" color="primary">
        <q-fab-action color="primary" icon="save" label="Save" @click="saveCurrentStep" />
        <q-fab-action color="primary" icon="play_arrow" label="Run" @click="runCurrentStep" />
      </q-fab>
    </q-page-sticky>
  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useProjectStore } from 'src/stores/projectStore'
import { useQuasar } from 'quasar'

export default {
  name: 'MainPage',
  components: {
  },
  setup() {
    const baseMap = ref(null)
    const projectStore = useProjectStore()
    const $q = useQuasar()

    onMounted(() => {
      console.log('Initializing map...')
      projectStore.initMap('map')
    })

    const onMapReady = (map) => {
      // Initialize map with current project data if available
      if (projectStore.currentProject) {
        // Load project data onto the map
      }
    }

    const saveCurrentStep = () => {
      // Implement saving logic for the current workflow step
      $q.notify({
        color: 'positive',
        message: 'Progress saved successfully',
        icon: 'save'
      })
    }

    const runCurrentStep = () => {
      // Implement running logic for the current workflow step
      $q.notify({
        color: 'info',
        message: 'Running current step...',
        icon: 'play_arrow'
      })
    }

    return {
      baseMap,
      onMapReady,
      saveCurrentStep,
      runCurrentStep
    }
  }
}
</script>

<style lang="scss" scoped>
.full-height {
  height: calc(100vh - 50px); // Adjust based on your header/footer height
}
</style>