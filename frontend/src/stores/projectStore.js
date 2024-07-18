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
    },
    setAOI(geometry) {
      this.aoi = geometry;
    },
    async fetchProjects() {
      try {
        const response = await api.getProjects();
        this.projects = response.data;
      } catch (error) {
        console.error('Failed to fetch projects:', error);
        throw error;
      }
    },
    async createProject(projectData) {
      try {
        const response = await api.createProject({
          name: projectData.name,
          description: projectData.description,
          // aoi: projectData.aoi.geometry 
        });
        this.currentProject = response.data;
        this.projects.push(response.data);
        this.selectedProjectId = response.data.id;
        return this.currentProject;
      } catch (error) {
        console.error('Failed to create project:', error);
        throw error;
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
    setCurrentProject(project) {
      this.currentProject = project
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