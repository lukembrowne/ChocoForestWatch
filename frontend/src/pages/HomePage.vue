<template>
  <q-page class="fullscreen-map">
    <div class="map-container">
      <BaseMapComponent ref="baseMap" @map-ready="onMapReady" class="full-height full-width" />
      
      <div class="map-overlay bottom-right">
        <q-btn fab icon="edit" color="primary" @click="startDrawingAOI" />
        <q-btn fab icon="check" color="positive" class="q-ml-sm" @click="createProject" :disable="!aoiDrawn" />
      </div>
    </div>
  </q-page>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useProjectStore } from 'stores/projectStore';
import BaseMapComponent from 'components/BaseMapComponent.vue';
import Draw, {
  createBox,
} from 'ol/interaction/Draw.js';import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';
import GeoJSON from 'ol/format/GeoJSON';


export default {
  name: 'HomePage',
  components: {
    BaseMapComponent
  },
  setup() {
    const router = useRouter();
    const projectStore = useProjectStore();
    const baseMap = ref(null);
    const aoiDrawn = ref(false);
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

    const startDrawingAOI = () => {
      if (!baseMap.value || !baseMap.value.map) return;

      const source = vectorLayer.value.getSource();
      source.clear();  // Clear previous drawings

      drawInteraction.value = new Draw({
        source: source,
        type: 'Circle',
        geometryFunction: createBox()
      });

      drawInteraction.value.on('drawend', (event) => {
        const feature = event.feature;
        const geometry = feature.getGeometry();
        projectStore.setAOI(geometry);
        aoiDrawn.value = true;
        baseMap.value.map.removeInteraction(drawInteraction.value);
      });

      baseMap.value.map.addInteraction(drawInteraction.value);
    };

    const createProject = async () => {
      if (!aoiDrawn.value) return;

      try {
        const feature = vectorLayer.value.getSource().getFeatures()[0];
        const geojson = new GeoJSON().writeFeatureObject(feature);
        
        const project = await projectStore.createProject({
          name: 'New Forest Monitoring Project',
          description: 'Created from homepage',
          aoi: geojson.geometry
        });

      } catch (error) {
        console.error('Failed to create project:', error);
        // Handle error (show notification, etc.)
      }
    };

    return {
      baseMap,
      aoiDrawn,
      onMapReady,
      startDrawingAOI,
      createProject
    };
  }
};
</script>

<style lang="scss" scoped>
.fullscreen-map {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  z-index: 1;
  padding: 10px;
}

.top-left {
  top: 10px;
  left: 10px;
}

.bottom-right {
  bottom: 10px;
  right: 10px;
}
</style>