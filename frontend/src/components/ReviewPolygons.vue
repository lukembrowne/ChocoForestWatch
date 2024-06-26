<template>
    <div>
      <h2>Review Polygons</h2>
      <ul>
        <li v-for="polygon in polygons" :key="polygon.id">
          {{ polygon.classLabel }}
          <button @click="editPolygon(polygon)">Edit</button>
          <button @click="deletePolygon(polygon)">Delete</button>
        </li>
      </ul>
    </div>
  </template>
  
  <script>
  export default {
    data() {
      return {
        polygons: []
      }
    },
    methods: {
    //   editPolygon(polygon) {
    //     // Edit polygon logic
    //   },
    //   deletePolygon(polygon) {
    //     // Delete polygon logic
    //   }
    }
  }
  </script>