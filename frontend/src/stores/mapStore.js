import { defineStore } from 'pinia';
import api from 'src/services/api';
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'
import { Map, View } from 'ol'
import { fromLonLat } from 'ol/proj';
import 'ol/ol.css';
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import { Style, Fill, Stroke } from 'ol/style'
import XYZ from 'ol/source/XYZ';
import { useProjectStore } from './projectStore';

export const useMapStore = defineStore('map', {
    state: () => ({
      aoi: null,
      map: null,
      mapInitialized: false,
      isLoading: false
    }),
    actions: {
      initMap(target) {
        this.map = new Map({
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
        })
        console.log('Map initialized in MapStore...')
        this.mapInitialized = true
      },
      setAOI(geometry) {
        this.aoi = geometry;
      },
      async setProjectAOI(aoiGeojson) {
        const projectStore = useProjectStore()
        if (!projectStore.currentProject) {
          throw new Error('No project selected')
        }
        try {
          const response = await api.setProjectAOI(projectStore.currentProject.id, aoiGeojson)
          projectStore.currentProject.aoi = response.data.aoi
          return response.data
        } catch (error) {
          console.error('Error setting project AOI:', error)
          throw error
        }
      },

      displayAOI(aoiGeojson) {
  
        if (!this.map) return
  
        // Remove existing AOI layer if it exists
        if (this.aoiLayer) {
          this.map.removeLayer(this.aoiLayer)
        }
  
        // Create new AOI layer
        const format = new GeoJSON()
        const feature = format.readFeature(aoiGeojson)
        const vectorSource = new VectorSource({
          features: [feature]
        })
        this.aoiLayer = new VectorLayer({
          source: vectorSource,
          style: new Style({
            fill: new Fill({
              color: 'rgba(255, 255, 255, 0.2)'
            }),
            stroke: new Stroke({
              color: '#000000',
              width: 2
            })
          })
        })
  
        // Add new AOI layer to map
        this.map.addLayer(this.aoiLayer)
  
        // Zoom to AOI
        this.map.getView().fit(vectorSource.getExtent(), { padding: [50, 50, 50, 50] })
      },
  
      clearAOI() {
        if (this.aoiLayer) {
          this.map.removeLayer(this.aoiLayer)
          this.aoiLayer = null
        }
      },
  
      setLoading(){
        this.isLoading = true
      },
      clearLoading(){
        this.isLoading = false
      },
  
      updateBasemap(date) {
  
        const apiKey = process.env.VUE_APP_PLANET_API_KEY;
        if (!apiKey) {
          console.error('API key is not defined. Please check your .env file.');
          return;
        }
  
        // const formattedDate = date.replace(/^(\d{4})-(\d{1,2})$/, (_, year, month) => `${year}-${month.padStart(2, '0')}`);
        console.log("Updating basemap for date: ", date);
        const newSource = new XYZ({
          url: `https://tiles{0-3}.planet.com/basemaps/v1/planet-tiles/planet_medres_normalized_analytic_${date}_mosaic/gmap/{z}/{x}/{y}.png?api_key=${apiKey}`,
        });
  
        newSource.on('tileloaderror', () => {
          console.error('basemap-error', `Failed to load basemap for date: ${date}`);
          this.clearLoading()
        });
        // Find the base layer and set the new source
        this.map.getLayers().forEach(layer => {
          if (layer.get('name') === 'baseMap') {
            console.log("Setting source for updated basemap...");
            layer.setSource(newSource);
          }
        });
        },
  
  
    },
      getters: {
        getMap: (state) => state.map,
        // ... other getters
      }
    });