import { defineStore } from 'pinia';
import api from 'src/services/api';
import 'ol/ol.css';
import { useMapStore } from './mapStore';  // Import the mapStore
import { ref, computed } from 'vue';
import { getBasemapDateOptions } from 'src/utils/dateUtils';




export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null,
    projects: [],
    selectedProjectId: null,
    map: null,
    mapInitialized: false,
    isLoading: false,
    currentTrainingSet: null,
    trainingDates: [],  // New state for training dates
    excludedTrainingDates: ref([]),
    trainingPolygonSets: [],
  }),
  getters: {
    projectClasses: (state) => state.currentProject?.classes || [],
    aoiAreaHa: (state) => state.currentProject?.aoi_area_ha || 0,
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
        
        console.log("Creating project:", projectData)

        // Get basemap dates to initialize training polygon sets in database
        const basemapDates = getBasemapDateOptions().map(option => option.value);


        const response = await api.createProject({
          ...projectData,
          basemap_dates:basemapDates
        })
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
          console.log("Displaying AOI within loadProject")
          mapStore.displayAOI(this.currentProject.aoi)
        }

        // Fetch training dates when a project is loaded
        this.fetchTrainingDates();

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
    },

    async fetchTrainingDates() {
      if (this.currentProject) {
        try {
          const trainingPolygons = await api.getTrainingPolygons(this.currentProject.id);
          // Filter out dates with no featuresd
          this.trainingPolygonSets = trainingPolygons.data
          this.trainingDates = trainingPolygons.data.filter(set => set.feature_count > 0).map(set => set.basemap_date);

          // Set excluded dates
          this.excludedTrainingDates = this.trainingPolygonSets.filter(set => set.excluded).map(set => set.basemap_date);

        } catch (error) {
          console.error('Error fetching training polygon dates:', error);
        }
      }
    },

    hasTrainingData(date) {
      // console.log("Checking if training data exists for date within ProjectStore:", date);
      // console.log("Training dates:", this.trainingDates);
      const exists = this.trainingDates.includes(date);
      // console.log("Training data exists:", exists);
      return exists ;
    },

    async toggleExcludedDate(date) {
      try {
        const index = this.excludedTrainingDates.indexOf(date)
        const shouldExclude = index === -1

        if (shouldExclude) {
          this.excludedTrainingDates.push(date)
        } else {
          this.excludedTrainingDates.splice(index, 1)
        }

        // Find the training set with the matching date
        const trainingSet = this.trainingPolygonSets.find(set => set.basemap_date === date)
        
        if (trainingSet) {
          // Update the excluded status
          const response = await api.setTrainingSetExcluded(trainingSet.id, shouldExclude)
          if (response.status === 200) {
            // Update the local state
            trainingSet.excluded = shouldExclude
          } else {
            throw new Error('Failed to update training set excluded status')
          }
        } else {

          throw new Error('No training set found for date to update')
        }
      } catch (error) {
        console.error('Error updating excluded status:', error)
        // Revert the local change if the API call fails
        const index = this.excludedTrainingDates.indexOf(date)
        if (index === -1) {
          this.excludedTrainingDates.pop()
        } else {
          this.excludedTrainingDates.splice(index, 0, date)
        }
        throw error
      }
    },

    isDateExcluded(date) {
      return this.excludedTrainingDates.includes(date)
    },

    includedTrainingDates() {
      return this.trainingDates.filter(date => !this.isDateExcluded(date))
    },

  }
});