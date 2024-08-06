<template>
  <div class="training-component">

    <TrainingSetManager />

    <q-separator spaced />

    <!-- Basemap date selection -->
    <div class="basemap-selection q-mb-md">
    </div>

    <q-separator spaced />

  </div>
</template>

<script>
import TrainingSetManager from 'components/TrainingSetManager.vue'



export default {
  name: 'TrainingComponent',
  components: {
    TrainingSetManager
  },
  setup() {


    return {
    }
  }
}
</script>