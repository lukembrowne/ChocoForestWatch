<template>
    <div>
      <h2>Draw Polygons</h2>
      <MapComponent />
      <button @click="startDrawing('forest')">Draw Forest Polygon</button>
      <button @click="startDrawing('non-forest')">Draw Non-Forest Polygon</button>
    </div>
  </template>
  
  <script>
  import MapComponent from './MapComponent.vue'
  
  export default {
    components: {
      MapComponent
    },
    methods: {
      startDrawing(classLabel) {
        this.$refs.mapComponent.startDrawing(classLabel)
      }
    }
  }
  </script>