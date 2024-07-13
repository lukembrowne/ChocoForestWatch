import { defineStore } from 'pinia';
import api from 'src/services/api';

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null,
    projects: [],
    aoi: null,
  }),
  actions: {
    setAOI(geometry) {
        this.aoi = geometry;
      },
    async createProject(projectData) {
      try {
        const response = await api.createProject(projectData);
        this.currentProject = response.data;
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
        return this.currentProject;
      } catch (error) {
        console.error('Failed to load project:', error);
        throw error;
      }
    },
    async updateProject(id, projectData) {
      try {
        const response = await api.updateProject(id, projectData);
        this.currentProject = response.data;
        return this.currentProject;
      } catch (error) {
        console.error('Failed to update project:', error);
        throw error;
      }
    },
    async fetchProjects() {
      try {
        const response = await api.getProjects();
        this.projects = response.data;
        return this.projects;
      } catch (error) {
        console.error('Failed to fetch projects:', error);
        throw error;
      }
    },
  },
});