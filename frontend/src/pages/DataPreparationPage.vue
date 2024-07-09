<template>

<div class="selected-info"></div>
  <div>Selected Raster: {{ selectedRaster ? selectedRaster.filename : 'None' }}</div>
  <div>Selected Vector: {{ selectedVector ? selectedVector.filename : 'None' }}</div>

  <div class="data-prepar</div>ation q-pa-md">
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-8">
        <MapComponent
          :rasterId="selectedRaster ? selectedRaster.id : null"
          :vectorId="selectedVector ? selectedVector.id : null"
          @polygons-drawn="onPolygonsDrawn"
        />
      </div>
      <div class="col-12 col-md-4">
        <q-select
          v-model="selectedRaster"
          :options="rasters"
          option-label="filename"
          label="Select Raster"
          class="q-mb-md"
          @update:model-value="updateMap"
        />
        <q-select
          v-model="selectedVector"
          :options="vectors"
          option-label="filename"
          label="Select Vector"
          class="q-mb-md"
          @update:model-value="updateMap"
        />
        <q-btn
          label="Extract Pixels"
          color="primary"
          @click="extractPixels"
          :disable="!canExtractPixels"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';
import MapComponent from 'components/MapComponent.vue';
import apiService from 'src/services/api';

export default {
  name: 'DataPreparationPage',
  components: {
    MapComponent
  },
  setup() {
    const $q = useQuasar();
    const router = useRouter();

    const rasters = ref([]);
    const vectors = ref([]);
    const selectedRaster = ref(null);
    const selectedVector = ref(null);
    const drawnPolygons = ref([]);

    const canExtractPixels = computed(() => 
      selectedRaster.value && (selectedVector.value || drawnPolygons.value.length > 0)
    );

    onMounted(async () => {
      try {
        const [rasterResponse, vectorResponse] = await Promise.all([
          apiService.fetchRasters(),
          apiService.fetchVectors()
        ]);
        rasters.value = rasterResponse.data;
        vectors.value = vectorResponse.data;
      } catch (error) {
        console.error('Error fetching data:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to load rasters and vectors',
          icon: 'error'
        });
      }
    });

    const onPolygonsDrawn = (polygons) => {
      drawnPolygons.value = polygons;
    };

    const updateMap = () => {
      // This function is called when a raster or vector is selected
      // The MapComponent will react to the changes in rasterId and vectorId props
    };

    const extractPixels = async () => {
      try {
        const polygonsToUse = selectedVector.value 
          ? selectedVector.value.geojson.features 
          : drawnPolygons.value;

        await apiService.extractPixels({
          rasterId: selectedRaster.value.id,
          polygons: polygonsToUse
        });

        $q.notify({
          type: 'positive',
          message: 'Pixels extracted successfully',
          icon: 'check'
        });

        // Navigate to the next step
        router.push('/model-training');
      } catch (error) {
        console.error('Error extracting pixels:', error);
        $q.notify({
          type: 'negative',
          message: 'Failed to extract pixels',
          icon: 'error'
        });
      }
    };

    // Watch for changes in selectedRaster and selectedVector
    watch([selectedRaster, selectedVector], updateMap);

    return {
      rasters,
      vectors,
      selectedRaster,
      selectedVector,
      canExtractPixels,
      onPolygonsDrawn,
      extractPixels,
      updateMap
    };
  }
};
</script>