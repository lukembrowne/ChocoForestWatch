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


export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null,
    projects: [],
    aoi: null,
    selectedProjectId: null,
    map: null,
    mapInitialized: false

  }),
  actions: {
    initMap(target) {
      this.map = new Map({
        target: target,
        layers: [
          new TileLayer({
            source: new OSM()
          })
        ],
        view: new View({
          center: fromLonLat([-79.81822466589962, 0.460628082970743]),
          zoom: 12
        })
      })
      console.log('Map initialized...')
      this.mapInitialized = true
    },
    setAOI(geometry) {
      this.aoi = geometry;
    },
    setMap(map) {
      this.map = map
    },
    async fetchProjects() {
      try {
        const response = await api.getProjects()
        this.projects = response.data
        return this.projects
      } catch (error) {
        console.error('Error fetching projects:', error)
        throw error
      }
    },
    async createProject(projectData) {
      try {
        const response = await api.createProject(projectData)
        this.projects.push(response.data)
        return response.data
      } catch (error) {
        console.error('Error creating project:', error)
        throw error
      }
    },
    async setCurrentProject(project) {
      this.currentProject = project
    },

    async setProjectAOI(aoiGeojson) {
      if (!this.currentProject) {
        throw new Error('No project selected')
      }
      try {
        const response = await api.setProjectAOI(this.currentProject.id, aoiGeojson)
        this.currentProject.aoi = response.data.aoi
        return response.data
      } catch (error) {
        console.error('Error setting project AOI:', error)
        throw error
      }
    },
    async loadProject(projectId) {
      try {
        const response = await api.getProject(projectId)
        this.currentProject = response.data
        if (this.currentProject.aoi && this.mapInitialized) {
          this.displayAOI(this.currentProject.aoi)
        }
        return this.currentProject
      } catch (error) {
        console.error('Error loading project:', error)
        throw error
      }
    },
    clearCurrentProject() {
      this.currentProject = null;
      this.selectedProjectId = null;
    },
    setSelectedProjectId(id) {
      this.selectedProjectId = id;
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
    }
  },
  getters: {
    getMap: (state) => state.map,
    // ... other getters
  }
});