<template>
  <q-page class="q-pa-md flex flex-center">
    <div style="width: 100%; height: 600px;">
      <BaseMapComponent ref="baseMap" @map-ready="onMapReady" class="full-width full-height" />

      <div class="absolute-top-right q-ma-md">
        <q-btn color="primary" label="Draw Area of Interest" @click="startDrawing" :disable="isDrawing" />
        <q-btn color="secondary" label="Fetch Quads" @click="fetchQuadsForDrawnArea" class="q-ml-sm"
          :disable="!areaOfInterest" />
      </div>

      <q-dialog v-model="showQuadList">
        <q-card style="width: 300px; max-width: 80vw;">
          <q-card-section>
            <div class="text-h6">Available Quads</div>
          </q-card-section>

          <q-card-section class="q-pa-none">
            <q-list separator>
              <q-item v-for="quad in availableQuads" :key="quad.id" clickable v-ripple @click="showQuadDetails(quad)">
                <q-item-section>{{ quad.name }}</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>

          <q-card-section v-if="availableQuads.length === 0">
            No quads available for the selected area.
          </q-card-section>
        </q-card>
      </q-dialog>
      <q-input v-model="mosaicName" label="Mosaic Name" class="q-mt-md" />

    </div>

    <q-inner-loading :showing="isLoading">
      <q-spinner-gears size="50px" color="primary" />
    </q-inner-loading>
  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import BaseMapComponent from '../components/BaseMapComponent.vue';
import planetApi from '../services/planetApi';
import { Draw } from 'ol/interaction';
import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';
import { transformExtent } from 'ol/proj';

export default {
  name: 'SatelliteImageBrowser',
  components: {
    BaseMapComponent
  },
  setup() {
    const $q = useQuasar();
    const baseMap = ref(null);
    const availableQuads = ref([]);
    const showQuadList = ref(false);
    const isLoading = ref(false);
    const isDrawing = ref(false);
    const areaOfInterest = ref(null);
    const drawInteraction = ref(null);
    const vectorLayer = ref(null);

    const onMapReady = (map) => {
      const source = new VectorSource();
      vectorLayer.value = new VectorLayer({
        source: source,
        style: {
          'fill-color': 'rgba(255, 255, 255, 0.2)',
          'stroke-color': '#ffcc33',
          'stroke-width': 2
        }
      });
      map.addLayer(vectorLayer.value);
    };

    const startDrawing = () => {
      if (!baseMap.value || !baseMap.value.map) return;

      isDrawing.value = true;
      const source = vectorLayer.value.getSource();
      source.clear();  // Clear previous drawings

      drawInteraction.value = new Draw({
        source: source,
        type: 'Polygon'
      });

      drawInteraction.value.on('drawend', (event) => {
        const feature = event.feature;
        const extent = feature.getGeometry().getExtent();
        areaOfInterest.value = transformExtent(extent, 'EPSG:3857', 'EPSG:4326');
        isDrawing.value = false;
        baseMap.value.map.removeInteraction(drawInteraction.value);
      });

      baseMap.value.map.addInteraction(drawInteraction.value);
    };

    const mosaicName = ref('planet_medres_normalized_analytic_2022-08_mosaic');

    const fetchQuadsForDrawnArea = async () => {
      if (!areaOfInterest.value) {
        $q.notify({
          color: 'warning',
          message: 'Please draw an area of interest first.',
          icon: 'warning'
        });
        return;
      }

      isLoading.value = true;
      try {
        const quads = await planetApi.getAvailableQuads(areaOfInterest.value, mosaicName.value);
        availableQuads.value = quads;
        showQuadList.value = true;
      } catch (error) {
        console.error('Error fetching available quads:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch quads. Please try again.',
          icon: 'error'
        });
      } finally {
        isLoading.value = false;
      }
    };

    const showQuadDetails = (quad) => {
      $q.dialog({
        title: 'Quad Details',
        message: `Name: ${quad.name}<br>ID: ${quad.id}<br>Date: ${quad.date}`,
        html: true
      });
    };

    onMounted(() => {
      // Any initialization logic
    });

    return {
      baseMap,
      availableQuads,
      showQuadList,
      isLoading,
      isDrawing,
      areaOfInterest,
      onMapReady,
      startDrawing,
      fetchQuadsForDrawnArea,
      showQuadDetails,
      mosaicName
    };
  }
}
</script>

<style scoped>
.full-width {
  width: 100%;
}

.full-height {
  height: 100vh;
}

.relative-position {
  position: relative;
}
</style>