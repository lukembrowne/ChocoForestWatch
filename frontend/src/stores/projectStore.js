import { defineStore } from 'pinia';
import api from 'src/services/api';
import 'ol/ol.css';
import { useMapStore } from './mapStore';  // Import the mapStore



export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null,
    projects: [],
    selectedProjectId: null,
    map: null,
    mapInitialized: false,
    isLoading: false

  }),
  actions: {
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
      console.log("Current Project: ", project)
      this.currentProject = project
    },
    async loadProject(projectId) {

      console.log('Loading project:', projectId)

      try {
        const response = await api.getProject(projectId)
        this.currentProject = response.data

        const mapStore = useMapStore();  // Access the mapStore
        if (this.currentProject['aoi'] && mapStore.mapInitialized) {
          console.log("Displaying AOI from within projectSTore")
          mapStore.displayAOI(this.currentProject.aoi)
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

  },
  });