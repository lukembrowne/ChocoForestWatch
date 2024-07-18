<template>
  <div class="row">
    <div class="col-3">
      <PredictionList @predictionSelected="loadPrediction" />
    </div>
    <div class="col relative-position" style="height: calc(100vh - 50px);">
      <BaseMapComponent ref="baseMap" @map-ready="onMapReady" @basemap-error="handleBasemapError"
        :basemapDate="selectedBasemapDate" class="absolute-full" />
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import BaseMapComponent from 'components/BaseMapComponent.vue';
import PredictionList from 'components/PredictionList.vue';
import { useProjectStore } from 'src/stores/projectStore'
import { GeoJSON } from 'ol/format'
import VectorSource from 'ol/source/Vector'
import VectorLayer from 'ol/layer/Vector'
import { Style, Fill, Stroke } from 'ol/style';
import Feature from 'ol/Feature';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';
import { fromUrl } from 'geotiff';


export default {
  components: { BaseMapComponent, PredictionList },
  props: ['projectId'],
  setup(props) {
    const baseMap = ref(null);
    const currentPrediction = ref(null);
    const projectStore = useProjectStore()
    const currentProject = computed(() => projectStore.currentProject)
    const aoiLayer = ref(null);
    const predictionLayer = ref(null);




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


      // Set view to project AOI and display it
      if (projectStore.currentProject.aoi) {
        try {

          // Saved as GEOJSON so need to convert to geometry
          // const geojsonFormat = new GeoJSON();
          // const geometry = geojsonFormat.readGeometry(projectStore.currentProject.aoi);

          // Assuming projectStore.currentProject.aoi contains the GeoJSON string
          const geojsonString = projectStore.currentProject.aoi;

          // Initialize the GeoJSON format with the correct projections
          const geojsonFormat = new GeoJSON();

          // Read the geometry from the GeoJSON string, specifying the projections
          const geometry = geojsonFormat.readGeometry(geojsonString, {
            dataProjection: 'EPSG:4326',    // The projection of the GeoJSON data
            featureProjection: 'EPSG:3857'  // The projection to convert the data to
          });
          const extent = geometry.getExtent();
          const aoiFeature = new Feature({
            geometry: geometry,
          });
          aoiLayer.value.getSource().addFeature(aoiFeature);
          map.getView().fit(extent, { padding: [50, 50, 50, 50] });
        } catch (error) {
          console.error('Error getting AOI extent:', error);
        }
      }
    };

    // const loadPrediction = async (prediction) => {
    //   currentPrediction.value = prediction;
    //   if (baseMap.value) {
    //     console.log(baseMap.value)
    //     baseMap.value.clearLayers();
    //     baseMap.value.addPredictionLayer(prediction.file_path);      }
    // };

    const loadPrediction = async (prediction) => {
      console.log('Displaying prediction:', prediction.file_path);

     if (baseMap.value) {
        baseMap.value.clearLayers();
     }

      try {
        const url = `http://127.0.0.1:5000/${prediction.file_path}`;
        const tiff = await fromUrl(url);
        const image = await tiff.getImage();
        const width = image.getWidth();
        const height = image.getHeight();
        const bbox = image.getBoundingBox();

        const rasterData = await image.readRasters();

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d');

        const imageData = context.createImageData(width, height);
        const data = imageData.data;

        for (let i = 0; i < width * height; i++) {
          const value = rasterData[0][i];
          const color = value === 1 ? [255, 255, 0, 255] : [0, 128, 0, 255]; // Yellow for non-forest, green for forest
          data[i * 4] = color[0];
          data[i * 4 + 1] = color[1];
          data[i * 4 + 2] = color[2];
          data[i * 4 + 3] = color[3];
        }
        context.putImageData(imageData, 0, 0);

        const imageUrl = canvas.toDataURL();
        const extent = bbox;

        if (predictionLayer.value) {
          baseMap.value.removeLayer(predictionLayer.value);
        }

        predictionLayer.value = new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            imageExtent: extent,
          }),
          zIndex: 1,
          opacity: 0.7
        });

        baseMap.value.addLayer(predictionLayer.value);
      } catch (error) {
        console.error('Error displaying prediction:', error);
        error.value = 'Failed to display prediction: ' + error.message;
      }
    };

    return { baseMap, onMapReady, loadPrediction };
  }
}
</script>