// NavigationBar.vue
<template>
  <nav>
    <router-link to="/upload">Upload Data</router-link>
    <router-link to="/draw">Draw Polygons</router-link>
    <router-link to="/review">Review Polygons</router-link>
    <router-link to="/train">Train Model</router-link>
    <router-link to="/predict">Predict Land Use</router-link>
    <router-link to="/visualize">Visualize Results</router-link>
  </nav>
</template>

<script>
export default {
  name: 'NavigationBar'
}
</script>