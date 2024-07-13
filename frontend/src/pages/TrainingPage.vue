<template>
  <q-page class="row">
    <q-drawer v-model="leftDrawerOpen" show-if-above :width="300" :breakpoint="400" bordered class="bg-grey-3">
      <q-scroll-area class="fit">
        <q-list>
          <q-item-label header>Instructions</q-item-label>
          <q-item>
            <q-item-section>
              <ol>
                <li>Choose a class from the dropdown below.</li>
                <li>Click the "Draw Polygon" button to start drawing.</li>
                <li>Click on the map to add points to your polygon.</li>
                <li>Double-click to finish drawing the polygon.</li>
                <li>Repeat for different classes as needed.</li>
              </ol>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section>
              <q-select v-model="currentClass" :options="classOptions" label="Class" />
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section>
              <q-btn label="Draw Polygon" color="primary" @click="startDrawing" class="full-width" />
            </q-item-section>
          </q-item>

          <q-item-label header>Load Saved Polygons</q-item-label>
          <q-item>
            <q-item-section>
              <q-select v-model="selectedSavedPolygons" :options="savedPolygonsOptions" label="Saved Polygons"
                @update:model-value="loadSavedPolygons" />
            </q-item-section>
          </q-item>

          <q-item-label header>Select Basemap Date</q-item-label>
          <q-item>
            <q-item-section>
              <q-select v-model="selectedBasemapDate" :options="basemapDateOptions" label="Basemap Date"
                @update:model-value="updateBasemap" />
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section>
              <q-btn label="Save Polygons" color="positive" @click="savePolygons" class="full-width q-mt-md" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <div class="col">
      <div class="map-container" style="height: calc(100vh - 50px);">
        <BaseMapComponent ref="baseMap" @map-ready="onMapReady" class="full-height full-width" />

        <div class="map-overlay bottom-right">
          <q-btn fab icon="menu" color="primary" @click="toggleLeftDrawer" class="q-mb-md" />
        </div>
      </div>
    </div>
  </q-page>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from 'src/stores/projectStore'
import BaseMapComponent from 'components/BaseMapComponent.vue'
import { Draw } from 'ol/interaction'
import VectorSource from 'ol/source/Vector'
import VectorLayer from 'ol/layer/Vector'
import { GeoJSON } from 'ol/format'
import apiService from 'src/services/api'
import { Style, Fill, Stroke } from 'ol/style';
import Feature from 'ol/Feature';


export default {
  name: 'TrainingPage',
  components: {
    BaseMapComponent
  },
  setup() {
    const route = useRoute()
    const projectStore = useProjectStore()
    const baseMap = ref(null)
    const project = ref({})
    const trainingPolygons = ref([])
    const currentClass = ref(null)
    const leftDrawerOpen = ref(true)
    const selectedSavedPolygons = ref(null)
    const selectedBasemapDate = ref(null)

    // Define vector layers
    const aoiLayer = ref(null);
    const trainingLayer = ref(null);

    const classOptions = [
      { label: 'Forest', value: 'forest' },
      { label: 'Non-Forest', value: 'non_forest' },
      { label: 'Water', value: 'water' },
      { label: 'Urban', value: 'urban' }
    ]

    const savedPolygonsOptions = ref([])

    const basemapDateOptions = computed(() => {
      const options = []
      for (let year = 2022; year <= 2024; year++) {
        for (let month = 1; month <= 12; month++) {
          if (year === 2024 && month > 1) break
          const date = new Date(year, month - 1)
          options.push({
            label: date.toLocaleString('default', { month: 'long', year: 'numeric' }),
            value: `${year}-${month.toString().padStart(2, '0')}`
          })
        }
      }
      return options
    })

    onMounted(async () => {
      const projectId = route.params.projectId
      project.value = await projectStore.loadProject(projectId)
      await fetchSavedPolygons()
    })

    const onMapReady = (map) => {
      /// Initialize vector layer for AOI
      const aoiSource = new VectorSource();
      aoiLayer.value = new VectorLayer({
        source: aoiSource,
        style: new Style({
          fill: new Fill({
            color: 'rgba(0, 0, 0, 0.1)',
          }),
          stroke: new Stroke({
            color: 'black',
            width: 2,
          }),
        }),
      });
      map.addLayer(aoiLayer.value);

      // Initialize vector layer for training polygons
      const trainingSource = new VectorSource();
      trainingLayer.value = new VectorLayer({
        source: trainingSource,
        style: new Style({
          fill: new Fill({
            color: 'rgba(255, 255, 255, 0.2)',
          }),
          stroke: new Stroke({
            color: '#ffcc33',
            width: 2,
          }),
        }),
      });
      map.addLayer(trainingLayer.value);

      // Set view to project AOI and display it
      if (projectStore.aoi) {
        try {
          // Convert geometry to feature
          const aoiFeature = new Feature({
            geometry: projectStore.aoi
          });
          aoiLayer.value.getSource().addFeature(aoiFeature);

          const extent = projectStore.aoi.getExtent();
          map.getView().fit(extent, { padding: [50, 50, 50, 50] });
        } catch (error) {
          console.error('Error getting AOI extent:', error);
        }
      }
    }

    const startDrawing = () => {
      if (!baseMap.value || !baseMap.value.map) return

      const draw = new Draw({
        source: baseMap.value.map.getLayers().getArray().find(layer => layer instanceof VectorLayer).getSource(),
        type: 'Polygon'
      })

      draw.on('drawend', (event) => {
        const feature = event.feature
        trainingPolygons.value.push({
          id: Date.now(),
          feature: feature,
          class: currentClass.value
        })
        baseMap.value.map.removeInteraction(draw)
      })

      baseMap.value.map.addInteraction(draw)
    }

    const savePolygons = async () => {
      try {
        const polygonsToSave = trainingPolygons.value.map(p => ({
          geometry: new GeoJSON().writeGeometryObject(p.feature.getGeometry()),
          class: p.class
        }))
        await apiService.saveTrainingPolygons(project.value.id, polygonsToSave)
        // Show success message
      } catch (error) {
        console.error('Error saving polygons:', error)
        // Show error message
      }
    }

    const fetchSavedPolygons = async () => {
      try {
        const response = await apiService.getSavedPolygonSets(project.value.id)
        savedPolygonsOptions.value = response.data.map(set => ({
          label: set.name,
          value: set.id
        }))
      } catch (error) {
        console.error('Error fetching saved polygon sets:', error)
      }
    }

    const loadSavedPolygons = async () => {
      if (!selectedSavedPolygons.value) return
      try {
        const response = await apiService.getPolygonSet(selectedSavedPolygons.value)
        // Clear existing polygons
        const vectorSource = baseMap.value.map.getLayers().getArray().find(layer => layer instanceof VectorLayer).getSource()
        vectorSource.clear()
        // Add loaded polygons to the map
        response.data.polygons.forEach(polygon => {
          const feature = new GeoJSON().readFeature(polygon.geometry)
          feature.set('class', polygon.class)
          vectorSource.addFeature(feature)
        })
        // Update trainingPolygons ref
        trainingPolygons.value = response.data.polygons.map(p => ({
          id: p.id,
          feature: new GeoJSON().readFeature(p.geometry),
          class: p.class
        }))
      } catch (error) {
        console.error('Error loading saved polygons:', error)
      }
    }

    const updateBasemap = () => {
      if (!selectedBasemapDate.value || !baseMap.value) return
      // Implementation to update the basemap based on the selected date
      // This will depend on how you're handling the Planet basemaps
    }

    const toggleLeftDrawer = () => {
      leftDrawerOpen.value = !leftDrawerOpen.value
    }

    return {
      baseMap,
      project,
      trainingPolygons,
      currentClass,
      classOptions,
      leftDrawerOpen,
      selectedSavedPolygons,
      savedPolygonsOptions,
      selectedBasemapDate,
      basemapDateOptions,
      onMapReady,
      startDrawing,
      savePolygons,
      loadSavedPolygons,
      updateBasemap,
      toggleLeftDrawer
    }
  }
}
</script>

<style scoped>
.map-overlay {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 1;
}
</style>