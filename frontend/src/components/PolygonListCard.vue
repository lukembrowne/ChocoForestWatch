<template>
    <q-card class="polygon-list-card">
      <q-card-section>
        <div class="text-h6">Drawn Polygons</div>
        <div class="summary">
          <div v-for="(summary, className) in classSummary" :key="className">
            {{ className }}: {{ summary.count }} features, {{ summary.area.toFixed(2) }} ha
          </div>
        </div>
      </q-card-section>
      <q-card-section class="polygon-list">
        <q-list>
          <q-item v-for="(polygon, index) in drawnPolygons" :key="index">
            <q-item-section>
              {{ polygon.properties.classLabel }} - {{ (calculateArea(polygon) / 10000).toFixed(2) }} ha
            </q-item-section>
            <q-item-section side>
              <q-btn flat round color="negative" icon="delete" @click="deletePolygon(index)" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </template>
  
  <script>
  import { computed } from 'vue'
  import { useMapStore } from 'src/stores/mapStore'
  import { getArea } from 'ol/sphere'
  import { GeoJSON } from 'ol/format'
  
  export default {
    name: 'PolygonListCard',
    setup() {
      const mapStore = useMapStore()
  
      const drawnPolygons = computed(() => mapStore.drawnPolygons)
  
      const calculateArea = (polygon) => {
        const feature = new GeoJSON().readFeature(polygon)
        return getArea(feature.getGeometry())
      }
  
      const classSummary = computed(() => {
        const summary = {}
        drawnPolygons.value.forEach(polygon => {
          const classLabel = polygon.properties.classLabel
          const area = calculateArea(polygon) / 10000 // Convert to hectares
          if (!summary[classLabel]) {
            summary[classLabel] = { count: 0, area: 0 }
          }
          summary[classLabel].count++
          summary[classLabel].area += area
        })
        return summary
      })
  
      const deletePolygon = (index) => {
        mapStore.deletePolygon(index)
      }
  
      return {
        drawnPolygons,
        calculateArea,
        classSummary,
        deletePolygon
      }
    }
  }
  </script>
  
  <style scoped>
  .polygon-list-card {
    position: absolute;
    top: 20px;
    right: 20px;
    width: 300px;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
    z-index: 1000;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    background-color: white;
  }

  .summary {
    margin-bottom: 10px;
  }
  
  .polygon-list {
    max-height: calc(100vh - 200px);
    overflow-y: auto;
  }
  </style>