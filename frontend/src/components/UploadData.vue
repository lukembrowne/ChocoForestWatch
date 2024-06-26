<template>
    <div>
      <h2>Upload Data</h2>
      <input type="file" @change="handleRasterUpload" ref="rasterFileInput" />
      <input type="file" @change="handlePolygonsUpload" ref="polygonsFileInput" />
    </div>
  </template>
  
  <script>
  export default {
    methods: {
    //   handleRasterUpload(event) {
    //     // Handle raster upload
    //   },
    //   handlePolygonsUpload(event) {
    //     // Handle polygons upload
    //   }
    }
  }
  </script>