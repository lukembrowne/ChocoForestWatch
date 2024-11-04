<template>
  <div class="row no-wrap">
    <!-- Left Panel - Hotspots List -->
    <div class="hotspot-list-container">
      <q-card class="hotspot-list-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">Deforestation Hotspots</div>
          
          <!-- Deforestation Map Selection -->
          <q-select
            v-model="selectedDeforestationMap"
            :options="deforestationMaps"
            label="Select Deforestation Map"
            option-label="name"
            class="q-mb-md"
            @update:model-value="loadHotspots"
          />

          <!-- Hotspots List -->
          <q-scroll-area v-if="hotspots.length" style="height: calc(100vh - 250px)">
            <q-list separator>
              <q-item
                v-for="(hotspot, index) in hotspots"
                :key="index"
                :class="{ 'bg-grey-2': selectedHotspot === hotspot }"
                clickable
                v-ripple
                @click="selectHotspot(hotspot)"
              >
                <q-item-section>
                  <q-item-label>Hotspot #{{ index + 1 }}</q-item-label>
                  <q-item-label caption>
                    Area: {{ hotspot.properties.area_ha.toFixed(2) }} ha
                  </q-item-label>
                  <q-item-label caption>
                    Status: {{ hotspot.properties.verification_status || 'Unverified' }}
                  </q-item-label>
                </q-item-section>
                
                <!-- Verification Actions -->
                <q-item-section side>
                  <div class="row q-gutter-xs">
                    <q-btn
                      flat
                      round
                      size="sm"
                      color="positive"
                      icon="check_circle"
                      @click.stop="verifyHotspot(hotspot, 'verified')"
                    >
                      <q-tooltip>Verify Deforestation</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      round
                      size="sm"
                      color="warning"
                      icon="help"
                      @click.stop="verifyHotspot(hotspot, 'unsure')"
                    >
                      <q-tooltip>Mark as Unsure</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      round
                      size="sm"
                      color="negative"
                      icon="cancel"
                      @click.stop="verifyHotspot(hotspot, 'rejected')"
                    >
                      <q-tooltip>Reject Alert</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card-section>
      </q-card>
    </div>

    <!-- Right Panel - Side by Side Comparison -->
    <div class="comparison-container" v-if="selectedHotspot">
      <div class="comparison-maps">
        <div class="map-container">
          <div ref="beforeMap" class="comparison-map"></div>
          <div class="map-label">Before</div>
        </div>
        <div class="map-container">
          <div ref="afterMap" class="comparison-map"></div>
          <div class="map-label">After</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { useProjectStore } from 'src/stores/projectStore';
import { useQuasar } from 'quasar';
import api from 'src/services/api';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { GeoJSON } from 'ol/format';
import { Style, Fill, Stroke } from 'ol/style';

export default {
  name: 'HotspotVerification',

  setup() {
    const $q = useQuasar();
    const mapStore = useMapStore();
    const projectStore = useProjectStore();

    // Refs for map elements
    const beforeMap = ref(null);
    const afterMap = ref(null);
    const beforeMapInstance = ref(null);
    const afterMapInstance = ref(null);

    // State
    const deforestationMaps = ref([]);
    const selectedDeforestationMap = ref(null);
    const hotspots = ref([]);
    const selectedHotspot = ref(null);
    const hotspotLayers = ref({ before: null, after: null });

    // Initialize the comparison maps
    const initializeMaps = () => {
      const createMap = (target) => new Map({
        target,
        layers: [
          // We'll use the same base layer as the main map
          // You might want to adjust this based on your needs
          new TileLayer({
            source: mapStore.baseLayer.getSource()
          })
        ],
        view: new View({
          center: [0, 0],
          zoom: 12
        })
      });

      beforeMapInstance.value = createMap(beforeMap.value);
      afterMapInstance.value = createMap(afterMap.value);

      // Sync map movements
      beforeMapInstance.value.getView().on('change:center', (event) => {
        afterMapInstance.value.getView().setCenter(event.target.getCenter());
      });
      beforeMapInstance.value.getView().on('change:resolution', (event) => {
        afterMapInstance.value.getView().setResolution(event.target.getResolution());
      });

      afterMapInstance.value.getView().on('change:center', (event) => {
        beforeMapInstance.value.getView().setCenter(event.target.getCenter());
      });
      afterMapInstance.value.getView().on('change:resolution', (event) => {
        beforeMapInstance.value.getView().setResolution(event.target.getResolution());
      });
    };

    // Load deforestation maps and hotspots
    const loadDeforestationMaps = async () => {
      try {
        const response = await api.getPredictions(projectStore.currentProject.id);
        deforestationMaps.value = response.filter(p => p.type === "deforestation");
        deforestationMaps.value.sort((a, b) => new Date(b.end_date) - new Date(a.end_date));
      } catch (error) {
        console.error('Error loading deforestation maps:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load deforestation maps',
          icon: 'error'
        });
      }
    };

    const loadHotspots = async () => {
      if (!selectedDeforestationMap.value) return;

      try {
        const response = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          1.0 // minimum area in hectares
        );
        hotspots.value = response.features;
      } catch (error) {
        console.error('Error loading hotspots:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load hotspots',
          icon: 'error'
        });
      }
    };

    const selectHotspot = (hotspot) => {
      selectedHotspot.value = hotspot;

      // Clear existing hotspot layers
      if (hotspotLayers.value.before) {
        beforeMapInstance.value.removeLayer(hotspotLayers.value.before);
        afterMapInstance.value.removeLayer(hotspotLayers.value.after);
      }

      // Create new vector layers for the hotspot
      const vectorSource = new VectorSource({
        features: new GeoJSON().readFeatures(hotspot, {
          featureProjection: beforeMapInstance.value.getView().getProjection()
        })
      });

      const style = new Style({
        fill: new Fill({
          color: 'rgba(255, 0, 0, 0.2)'
        }),
        stroke: new Stroke({
          color: '#FF0000',
          width: 2
        })
      });

      // Add hotspot overlay to both maps
      hotspotLayers.value = {
        before: new VectorLayer({ source: vectorSource.clone(), style }),
        after: new VectorLayer({ source: vectorSource.clone(), style })
      };

      beforeMapInstance.value.addLayer(hotspotLayers.value.before);
      afterMapInstance.value.addLayer(hotspotLayers.value.after);

      // Fit maps to hotspot extent
      const extent = vectorSource.getExtent();
      beforeMapInstance.value.getView().fit(extent, { padding: [50, 50, 50, 50] });
    };

    const verifyHotspot = async (hotspot, status) => {
      try {
        await api.verifyHotspot(hotspot.id, status);
        // Update local state
        hotspot.properties.verification_status = status;
        $q.notify({
          color: 'positive',
          message: 'Hotspot verification updated',
          icon: 'check'
        });
      } catch (error) {
        console.error('Error verifying hotspot:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to update hotspot verification',
          icon: 'error'
        });
      }
    };

    onMounted(async () => {
      await loadDeforestationMaps();
      initializeMaps();
    });

    onUnmounted(() => {
      if (beforeMapInstance.value) beforeMapInstance.value.setTarget(null);
      if (afterMapInstance.value) afterMapInstance.value.setTarget(null);
    });

    return {
      beforeMap,
      afterMap,
      deforestationMaps,
      selectedDeforestationMap,
      hotspots,
      selectedHotspot,
      loadHotspots,
      selectHotspot,
      verifyHotspot
    };
  }
};
</script>

<style lang="scss" scoped>
.hotspot-list-container {
  width: 400px;
  height: calc(100vh - 50px);
  overflow-y: auto;
  z-index: 1;
}

.hotspot-list-card {
  height: 100%;
}

.comparison-container {
  flex: 1;
  height: calc(100vh - 50px);
  padding: 16px;
}

.comparison-maps {
  display: flex;
  gap: 16px;
  height: 100%;
}

.map-container {
  flex: 1;
  position: relative;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.comparison-map {
  width: 100%;
  height: 100%;
}

.map-label {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
}
</style> 