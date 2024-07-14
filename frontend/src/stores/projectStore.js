import { defineStore } from 'pinia';
import api from 'src/services/api';

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null,
    projects: [],
    aoi: null,
    selectedProjectId: null
  }),
  actions: {
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
          aoi: projectData.aoi.geometry  // Send only the geometry part of the GeoJSON
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
    setSelectedProjectId(id) {
      this.selectedProjectId = id;
    }
  },
});