// services/api.js
import axios from 'axios';

// const baseURL = process.env.NODE_ENV === 'production' 
//   ? 'http://backend:5000'
//   : 'http://localhost:5000'

  // Simple configuration that works both locally and on server
// const baseURL = window.location.hostname === 'localhost' 
// ? 'http://localhost:5000'  // Development
// : `http://${window.location.hostname}:5000`;  // Production (server IP)


const baseURL = 'http://localhost:5000/api'  // Development


export default {

  createProject(projectData) {
    return axios.post(`${baseURL}/projects`, projectData);
  },

  getProjects() {
    return axios.get(`${baseURL}/projects`);
  },

  getProject(id) {
    return axios.get(`${baseURL}/projects/${id}`);
  },

  updateProject(id, projectData) {
    return axios.put(`${baseURL}/projects/${id}`, projectData);
  },

  deleteProject(id) {
    return axios.delete(`${baseURL}/projects/${id}`);
  },

  
  updateProjectClasses(projectId, classes) {
    return axios.put(`${baseURL}/projects/${projectId}/classes`, { classes });
  },
  setProjectAOI(projectId, aoiGeojson, aoiExtent, basemapDates) {
    return axios.post(`${baseURL}/projects/${projectId}/aoi`, { aoi: aoiGeojson, aoi_extent: aoiExtent, basemap_dates: basemapDates })
  },

  getTrainingPolygons(projectId) {
    return axios.get(`${baseURL}/training_polygons/${projectId}`);
  },

  getSpecificTrainingPolygons(projectId, setID) {
    return axios.get(`${baseURL}/training_polygons/${projectId}/${setID}`);
  },
  
  saveTrainingPolygons(data) {
    return axios.post(`${baseURL}/training_polygons`, data);
  },

  updateTrainingPolygons(data) {
    return axios.put(`${baseURL}/training_polygons/${data.project_id}/${data.id}`, data);
  },
  
  deleteTrainingSet(projectId, setId) {
    return axios.delete(`${baseURL}/training_polygons/${projectId}/${setId}`);
  },

  updateTrainingSetExcluded(projectId, trainingSetId, excluded) {
    return axios.put(`${baseURL}/projects/${projectId}/training-sets/${trainingSetId}/excluded`, { excluded })
  },

  async getTrainedModels(projectId) {
    try {
      const response = await axios.get(`${baseURL}/trained_models/${projectId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching trained models:', error);
      throw error;
    }
  },

  getTrainingDataSummary(projectId) {
    return axios.get(`${baseURL}/training_data_summary/${projectId}`);
  },



  async trainModel(data) {
    console.log('Starting model training with data:', data);
    try {
      const response = await axios.post(`${baseURL}/train_model`, data);
      console.log('Model training response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error in model training:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Error response:', error.response.data);
        console.error('Error status:', error.response.status);
        console.error('Error headers:', error.response.headers);
      } else if (error.request) {
        // The request was made but no response was received
        console.error('Error request:', error.request);
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Error message:', error.message);
      }
      throw error; // Re-throw the error so it can be caught in the component
    }
  },


  async fetchModelMetrics(projectID) {
    try {
      const response = await axios.get(`${baseURL}/trained_models/${projectID}/metrics`);
      return response.data;
    } catch (error) {
      console.error('Error fetching model metrics:', error);
      throw error;
    }
  },

  async predictLandcover(data) {
    try {
      const response = await axios.post(`${baseURL}/predict_landcover`, data);
      return response.data;
    } catch (error) {
      console.error('Error predicting landcover:', error);
      throw error;
    }
  },


  async getPredictions(projectId) {
    try {
      const response = await axios.get(`${baseURL}/predictions/${projectId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching predictions:', error);
      throw error;
    }
  },

  async getPrediction(predictionId) {
    const response = await axios.get(`${baseURL}/prediction/${predictionId}`);
    return response.data;
  },

  async getSummaryStatistics(predictionId) {
    try {
      const response = await axios.get(`${baseURL}/analysis/summary/${predictionId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting summary statistics:', error);
      throw error;
    }
  },

  async getDeforestationAnalysis(projectId) {
    try {
      const response = await axios.get(`${baseURL}/analysis/deforestation/${projectId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting deforestation analysis:', error);
      throw error;
    }
  },

  async getChangeAnalysis(data) {
    try {
      const response = await axios.post(`${baseURL}/analysis/change/`, data);
      return response.data;
    } catch (error) {
      console.error('Error getting change analysis:', error);
      throw error;
    }
  },

  async renamePrediction(predictionId, newName) {
    try {
      const response = await axios.put(`${baseURL}/predictions/${predictionId}/rename`, { new_name: newName });
      return response.data;
    } catch (error) {
      console.error('Error renaming prediction:', error);
      throw error;
    }
  },

  async deletePrediction(predictionId) {
    try {
      const response = await axios.delete(`${baseURL}/predictions/${predictionId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting prediction:', error);
      throw error;
    }
  },

  async getDeforestationHotspots(predictionId, minAreaHa, source = 'all') {
    try {
      const response = await axios.get(
        `${baseURL}/analysis/deforestation_hotspots/${predictionId}`, 
        { 
          params: { 
            min_area_ha: minAreaHa,
            source: source 
          } 
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error detecting deforestation hotspots:', error);
      throw error;
    }
  },

  async verifyHotspot(hotspotId, status) {
    const response = await axios.put(`${baseURL}/hotspots/${hotspotId}/verify`, {
        status: status
    });
    return response.data;
  },

};