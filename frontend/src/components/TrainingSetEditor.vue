<template>
  <div class="training-component">

    <TrainingSetManager />

    <q-separator spaced />

    <!-- Basemap date selection -->
    <div class="basemap-selection q-mb-md">
      <BasemapDateSelector />
    </div>

    <q-separator spaced />

  </div>
</template>

<script>
import BasemapDateSelector from 'components/BasemapDateSelector.vue'
import TrainingSetManager from 'components/TrainingSetManager.vue'



export default {
  name: 'TrainingComponent',
  components: {
    BasemapDateSelector,
    TrainingSetManager
  },
  setup() {


    return {
    }
  }
}
</script>