<template>
  <q-card class="polygon-list-card">
    <q-card-section class="q-pa-sm">
      <div class="text-h6">Drawn Polygons</div>
        <div class="summary q-gutter-xs">
          <div v-for="(summary, className) in classSummary" :key="className">
            {{ className }}: {{ summary.count }} features, {{ summary.area.toFixed(1) }} ha
          </div>
      </div>
    </q-card-section>
    <q-separator />
    <q-card-section class="polygon-list q-pa-none">
      <q-list dense>
        <q-item v-for="(polygon, index) in drawnPolygons" :key="index" class="q-py-xs">
          <q-item-section avatar>
            <q-icon name="lens" :style="{ color: getClassColor(polygon.properties.classLabel) }" size="xs" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ polygon.properties.classLabel }}</q-item-label>
            <q-item-label caption>{{ (calculateArea(polygon) / 10000).toFixed(1) }} ha</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn flat round dense color="negative" icon="delete" size="sm" @click="deletePolygon(index)" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card-section>
  </q-card>
</template>

<script>
import { computed } from 'vue'
import { useMapStore } from 'src/stores/mapStore'
import { useProjectStore } from 'src/stores/projectStore'
import { getArea } from 'ol/sphere'
import { GeoJSON } from 'ol/format'

export default {
  name: 'PolygonListCard',
  setup() {
    const mapStore = useMapStore()
    const projectStore = useProjectStore()

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

    const getClassColor = (className) => {
      const classObj = projectStore.currentProject?.classes.find(cls => cls.name === className)
      return classObj ? classObj.color : '#000000'
    }

    return {
      drawnPolygons,
      calculateArea,
      classSummary,
      deletePolygon,
      getClassColor
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
}

.summary {
  display: flex;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.polygon-list {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}
</style>