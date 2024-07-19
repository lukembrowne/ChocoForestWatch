import { defineStore } from 'pinia';
import api from 'src/services/api';
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'
import { Map, View } from 'ol'


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
          center: [0, 0],
          zoom: 2
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
    async loadProjectAOI(projectId) {
      try {
        const response = await api.getProjectAOI(projectId)
        this.currentProject.aoi = response.data.aoi
        this.currentProject.aoiName = response.data.aoiName
      } catch (error) {
        console.error('Error loading project AOI:', error)
        throw error
      }
    },
    async setProjectAOI(aoiData) {
      try {
        const response = await api.setProjectAOI(this.currentProject.id, aoiData)
        this.currentProject.aoi = response.data.aoi
        this.currentProject.aoiName = response.data.aoiName
      } catch (error) {
        console.error('Error setting project AOI:', error)
        throw error
      }
    },
    async loadProject(id) {
      try {
        const response = await api.getProject(id);
        this.currentProject = response.data;
        this.selectedProjectId = id;
        return this.currentProject;
      } catch (error) {
        console.error('Failed to load project:', error);
        throw error;
      }
    },
    clearCurrentProject() {
      this.currentProject = null;
      this.selectedProjectId = null;
    },
    setSelectedProjectId(id) {
      this.selectedProjectId = id;
    }
  },
  getters: {
    getMap: (state) => state.map,
    // ... other getters
  }
});