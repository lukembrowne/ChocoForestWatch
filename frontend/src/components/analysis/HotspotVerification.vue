<template>
  <div class="row no-wrap" style="height: 100vh;">
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
    <div class="comparison-container">
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
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
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
import OSM from 'ol/source/OSM'
import { fromLonLat, toLonLat } from 'ol/proj';



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
      console.log('Initializing maps');
      console.log('beforeMap element:', beforeMap.value);
      console.log('afterMap element:', afterMap.value);

      const createMap = (target) => {
        console.log('Creating map for target:', target);
        return new Map({
          target: target,
          layers: [
            new TileLayer({
              source: new OSM(),
              name: 'baseMap'
            })
          ],
          view: new View({
            center: fromLonLat([-79.81822466589962, 0.460628082970743]),
            zoom: 12
          })
        });
      };

      nextTick(() => {
        beforeMapInstance.value = createMap(beforeMap.value);
        afterMapInstance.value = createMap(afterMap.value);

        // Force a redraw
        beforeMapInstance.value.updateSize();
        afterMapInstance.value.updateSize();

        // Sync map movements
        const beforeView = beforeMapInstance.value.getView();
        const afterView = afterMapInstance.value.getView();

        // Sync center changes
        beforeView.on('change:center', () => {
          afterView.setCenter(beforeView.getCenter());
        });
        afterView.on('change:center', () => {
          beforeView.setCenter(afterView.getCenter());
        });

        // Sync zoom changes
        beforeView.on('change:resolution', () => {
          afterView.setResolution(beforeView.getResolution());
        });
        afterView.on('change:resolution', () => {
          beforeView.setResolution(afterView.getResolution());
        });

        // Sync rotation changes
        beforeView.on('change:rotation', () => {
          afterView.setRotation(beforeView.getRotation());
        });
        afterView.on('change:rotation', () => {
          beforeView.setRotation(afterView.getRotation());
        });
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
        // Load hotspots
        const response = await api.getDeforestationHotspots(
          selectedDeforestationMap.value.id,
          50.0 // minimum area in hectares
        );
        hotspots.value = response.features;

        // Update the before/after maps with appropriate imagery and all hotspots
        updateComparisonMaps(selectedDeforestationMap.value);
        displayAllHotspots();
      } catch (error) {
        console.error('Error loading hotspots:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load hotspots',
          icon: 'error'
        });
      }
    };

    const updateComparisonMaps = async (deforestationMap) => {
      if (!beforeMapInstance.value || !afterMapInstance.value) return;

      // Clear existing layers
      beforeMapInstance.value.getLayers().forEach(layer => {
        beforeMapInstance.value.removeLayer(layer);
      });
      
      afterMapInstance.value.getLayers().forEach(layer => {
        afterMapInstance.value.removeLayer(layer);
      });

      // Add Planet basemap layers
      const beforeLayer = mapStore.createPlanetBasemap(deforestationMap.summary_statistics.prediction1_date);
      const afterLayer = mapStore.createPlanetBasemap(deforestationMap.summary_statistics.prediction2_date);

      if (beforeLayer && afterLayer) {
        beforeMapInstance.value.addLayer(beforeLayer);
        afterMapInstance.value.addLayer(afterLayer);

        // Add AOI layers if project has AOI
        if (projectStore.currentProject?.aoi) {
          const { layer: beforeAOILayer, source: beforeAOISource } = mapStore.createAOILayer(
            projectStore.currentProject.aoi
          );
          const { layer: afterAOILayer } = mapStore.createAOILayer(
            projectStore.currentProject.aoi
          );

          beforeMapInstance.value.addLayer(beforeAOILayer);
          afterMapInstance.value.addLayer(afterAOILayer);

          // Fit to AOI extent
          const extent = beforeAOISource.getExtent();
          beforeMapInstance.value.getView().fit(extent, { padding: [50, 50, 50, 50] });
        }

        // Update labels
        const beforeLabel = document.querySelector('.map-container:first-child .map-label');
        const afterLabel = document.querySelector('.map-container:last-child .map-label');
        
        if (beforeLabel && afterLabel) {
          beforeLabel.textContent = `Before (${deforestationMap.summary_statistics.prediction1_date})`;
          afterLabel.textContent = `After (${deforestationMap.summary_statistics.prediction2_date})`;
        }
      } else {
        console.error('Failed to create Planet basemap layers');
        $q.notify({
          color: 'negative',
          message: 'Failed to load Planet imagery',
          icon: 'error'
        });
      }
    };

    const displayAllHotspots = () => {
      // Remove existing hotspot layers if they exist
      if (hotspotLayers.value.before) {
        beforeMapInstance.value.removeLayer(hotspotLayers.value.before);
        afterMapInstance.value.removeLayer(hotspotLayers.value.after);
      }

      // Create GeoJSON FeatureCollection
      const hotspotsGeoJSON = {
        type: 'FeatureCollection',
        features: hotspots.value
      };

      // Create styles
      const normalStyle = new Style({
        fill: new Fill({
          color: 'rgba(255, 68, 68, 0.2)'
        }),
        stroke: new Stroke({
          color: '#FF4444',
          width: 2
        })
      });

      const selectedStyle = new Style({
        fill: new Fill({
          color: 'rgba(255, 255, 0, 0.3)'
        }),
        stroke: new Stroke({
          color: '#FFFF00',
          width: 3
        })
      });

      // Create vector sources
      const beforeSource = new VectorSource({
        features: new GeoJSON().readFeatures(hotspotsGeoJSON)
      });

      const afterSource = new VectorSource({
        features: new GeoJSON().readFeatures(hotspotsGeoJSON)
      });

      // Add debug logging
      console.log('Selected hotspot:', selectedHotspot.value);

      // Create vector layers
      hotspotLayers.value = {
        before: new VectorLayer({
          source: beforeSource,
          style: (feature) => {
            const featureId = feature.get('id'); // Get ID from properties
            const isSelected = selectedHotspot.value && 
                              selectedHotspot.value.properties.id === featureId;
            return isSelected ? selectedStyle : normalStyle;
          },
          title: 'hotspots-before',
          id: 'hotspots-before',
          zIndex: 2
        }),
        after: new VectorLayer({
          source: afterSource,
          style: (feature) => {
            const featureId = feature.get('id'); // Get ID from properties
            const isSelected = selectedHotspot.value && 
                              selectedHotspot.value.properties.id === featureId;
            return isSelected ? selectedStyle : normalStyle;
          },
          title: 'hotspots-after',
          id: 'hotspots-after',
          zIndex: 2
        })
      };

      // Add layers to maps
      beforeMapInstance.value.addLayer(hotspotLayers.value.before);
      afterMapInstance.value.addLayer(hotspotLayers.value.after);

      console.log('Added hotspot layers:', hotspotLayers.value);
      console.log('Number of features:', beforeSource.getFeatures().length);
    };

    const selectHotspot = (hotspot) => {
      console.log('Selecting hotspot:', hotspot);
      selectedHotspot.value = hotspot;

      // Refresh the layer styles to highlight the selected hotspot
      if (hotspotLayers.value.before) {
        hotspotLayers.value.before.changed();
        hotspotLayers.value.after.changed();
      }

      // Re-enable the fit to extent code
      const extent = new GeoJSON().readFeature(hotspot).getGeometry().getExtent();
      beforeMapInstance.value.getView().fit(extent, { 
        padding: [50, 50, 50, 50],
        duration: 1000
      });
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
      console.log('Component mounted');
      await loadDeforestationMaps();
      setTimeout(() => {
        initializeMaps();
      }, 100);
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
  width: 100%;
}

.map-container {
  flex: 1;
  position: relative;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  min-height: 500px;
}

.comparison-map {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.map-label {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  z-index: 1;
}
</style> 