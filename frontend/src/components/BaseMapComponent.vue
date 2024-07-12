<template>
    <div ref="mapContainer" class="map"></div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import 'ol/ol.css';
import { Map, View } from 'ol';
import TileLayer from 'ol/layer/Tile';
import XYZ from 'ol/source/XYZ';
import { fromLonLat } from 'ol/proj';
import ImageLayer from 'ol/layer/Image';
import ImageStatic from 'ol/source/ImageStatic';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import { fromUrl } from 'geotiff';
import apiService from '../services/api';

export default {
    name: 'BaseMapComponent',
    props: {
        center: {
            type: Array,
            default: () => [-79.81822466589962, 0.460628082970743]
        },
        zoom: {
            type: Number,
            default: 12
        }
    },
    emits: ['map-ready'],
    setup(props, { emit, expose }) {
        const mapContainer = ref(null);
        const map = ref(null);
        const rasterLayer = ref(null);
        const vectorLayer = ref(null);

        const apiKey = process.env.VUE_APP_PLANET_API_KEY;
        if (!apiKey) {
            console.error('API key is not defined. Please check your .env file.');
            return;
        }

        const initMap = () => {
            map.value = new Map({
                target: mapContainer.value,
                // layers: [
                //     new TileLayer({
                //         source: new XYZ({
                //             url: 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png'
                //         }),
                //         zIndex: 0
                //     })
                // ],

                layers: [
                    new TileLayer({
                        source: new XYZ({
                            url: `https://tiles{0-3}.planet.com/basemaps/v1/planet-tiles/planet_medres_normalized_analytic_2022-08_mosaic/gmap/{z}/{x}/{y}.png?api_key=${apiKey}`,
                        }),
                        zIndex: 0
                    })
                ],
                view: new View({
                    center: fromLonLat(props.center),
                    zoom: props.zoom
                })
            });
            emit('map-ready', map.value);
        };

        const loadRaster = async (id) => {
            try {
                const response = await apiService.fetchRasterById(id);
                const url = `http://127.0.0.1:5000/${response.filepath}`;
                const tiff = await fromUrl(url);
                const image = await tiff.getImage();
                const bbox = image.getBoundingBox();
                const [width, height] = [image.getWidth(), image.getHeight()];

                const rasterData = await image.readRasters();
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                const imageData = ctx.createImageData(width, height);
                const data = imageData.data;

                for (let i = 0; i < width * height; i++) {
                    data[i * 4] = rasterData[0][i];
                    data[i * 4 + 1] = rasterData[1][i];
                    data[i * 4 + 2] = rasterData[2][i];
                    data[i * 4 + 3] = 255;
                }
                ctx.putImageData(imageData, 0, 0);

                if (rasterLayer.value) {
                    map.value.removeLayer(rasterLayer.value);
                }

                rasterLayer.value = new ImageLayer({
                    source: new ImageStatic({
                        url: canvas.toDataURL(),
                        imageExtent: bbox,
                    }),
                    zIndex: 0
                });

                map.value.addLayer(rasterLayer.value);
                map.value.getView().fit(bbox, { duration: 1000 });
            } catch (error) {
                console.error('Error loading raster:', error);
            }
        };

        const loadVector = async (id) => {
            try {
                const response = await apiService.fetchVectorById(id);
                const vectorSource = new VectorSource({
                    features: new GeoJSON().readFeatures(response.geojson, {
                        featureProjection: 'EPSG:3857'
                    })
                });

                if (vectorLayer.value) {
                    map.value.removeLayer(vectorLayer.value);
                }

                vectorLayer.value = new VectorLayer({
                    source: vectorSource,
                    zIndex: 1
                });

                map.value.addLayer(vectorLayer.value);
                const extent = vectorSource.getExtent();
                map.value.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 1000 });
            } catch (error) {
                console.error('Error loading vector:', error);
            }
        };

        onMounted(() => {
            initMap();
        });

        onBeforeUnmount(() => {
            if (map.value) {
                map.value.setTarget(null);
                map.value = null;
            }
        });

        watch(() => props.center, (newCenter) => {
            if (map.value) {
                map.value.getView().setCenter(fromLonLat(newCenter));
            }
        });

        watch(() => props.zoom, (newZoom) => {
            if (map.value) {
                map.value.getView().setZoom(newZoom);
            }
        });

        const addLayer = (layer) => {
            if (map.value) {
                map.value.addLayer(layer);
            }
        };

        const removeLayer = (layer) => {
            if (map.value) {
                map.value.removeLayer(layer);
            }
        };

        expose({ map, addLayer, removeLayer, loadRaster, loadVector });

        return { mapContainer };
    }
};
</script>

<style scoped>
.map {
    width: 100%;
    height: 100%;
}
</style>