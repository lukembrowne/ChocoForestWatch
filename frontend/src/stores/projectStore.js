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
    isLoading: false,
    currentTrainingSet: null  

  }),
  getters: {
    projectClasses: (state) => state.currentProject?.classes || []
  },
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
        mapStore.updateTrainingLayerStyle();
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
    updateProjectClasses(classes) {
      if (this.currentProject) {
        this.currentProject.classes = classes;
        // Here you might want to add an API call to update the classes on the backend
        // api.updateProjectClasses(this.currentProject.id, classes)
      }
    },
    async updateProject(projectId, updatedData) {
      try {
        const response = await api.updateProject(projectId, updatedData);
        const updatedProject = response.data;
        
        // Update the project in the projects array
        const index = this.projects.findIndex(p => p.id === projectId);
        if (index !== -1) {
          this.projects[index] = updatedProject;
        }
        
        // If it's the current project, update that too
        if (this.currentProject && this.currentProject.id === projectId) {
          this.currentProject = updatedProject;
        }
        
        return updatedProject;
      } catch (error) {
        console.error('Error updating project:', error);
        throw error;
      }
    },

    async deleteProject(projectId) {
      try {
        await api.deleteProject(projectId);
        
        // Remove the project from the projects array
        this.projects = this.projects.filter(p => p.id !== projectId);
        
        // If it's the current project, clear it
        if (this.currentProject && this.currentProject.id === projectId) {
          this.currentProject = null;
        }
      } catch (error) {
        console.error('Error deleting project:', error);
        throw error;
      }
    },

    setCurrentTrainingSet(trainingSet) {
      this.currentTrainingSet = trainingSet;
    },

    clearCurrentTrainingSet() {
      this.currentTrainingSet = null;
    }
  }
});