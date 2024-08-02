// services/api.js
import axios from 'axios';

const API_URL = 'http://127.0.0.1:5000/api';
// const API_URL = 'http://localhost:5000/api';


export default {

  createProject(projectData) {
    return axios.post(`${API_URL}/projects`, projectData);
  },

  getProjects() {
    return axios.get(`${API_URL}/projects`);
  },

  getProject(id) {
    return axios.get(`${API_URL}/projects/${id}`);
  },

  updateProject(id, projectData) {
    return axios.put(`${API_URL}/projects/${id}`, projectData);
  },

  deleteProject(id) {
    return axios.delete(`${API_URL}/projects/${id}`);
  },

  
  updateProjectClasses(projectId, classes) {
    return axios.put(`${API_URL}/projects/${projectId}/classes`, { classes });
  },
  setProjectAOI(projectId, aoiGeojson) {
    return axios.post(`${API_URL}/projects/${projectId}/aoi`, { aoi: aoiGeojson })
  },

  getTrainingPolygons(projectId) {
    return axios.get(`${API_URL}/training_polygons/${projectId}`);
  },

  getSpecificTrainingPolygons(projectId, setID) {
    return axios.get(`${API_URL}/training_polygons/${projectId}/${setID}`);
  },
  
  saveTrainingPolygons(data) {
    return axios.post(`${API_URL}/training_polygons`, data);
  },

  updateTrainingPolygons(data) {
    return axios.put(`${API_URL}/training_polygons/${data.project_id}/${data.id}`, data);
  },
  
  deleteTrainingSet(projectId, setId) {
    return axios.delete(`${API_URL}/training_polygons/${projectId}/${setId}`);
  },

  fetchRasters() {
    return axios.get(`${API_URL}/list_rasters`);
  },
  fetchVectors() {
    return axios.get(`${API_URL}/list_vectors`);
  },
  fetchModels() {
    return axios.get(`${API_URL}/list_models`);
  },

  async getTrainedModels(projectId) {
    try {
      const response = await axios.get(`${API_URL}/trained_models/${projectId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching trained models:', error);
      throw error;
    }
  },
  async predictLandcover(data) {
    try {
      const response = await axios.post(`${API_URL}/predict_landcover`, data);
      return response.data;
    } catch (error) {
      console.error('Error predicting landcover:', error);
      throw error;
    }
  },

  async trainModel(data) {
    console.log('Starting model training with data:', data);
    try {
      const response = await axios.post(`${API_URL}/train_model`, data);
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

  async renameModel(modelId, newName) {
    try {
      const response = await axios.put(`${API_URL}/trained_models/${modelId}/rename`, { new_name: newName });
      return response.data;
    } catch (error) {
      console.error('Error renaming model:', error);
      throw error;
    }
  },

  async deleteModel(modelId) {
    try {
      const response = await axios.delete(`${API_URL}/trained_models/${modelId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting model:', error);
      throw error;
    }
  },

  async fetchModelMetrics(modelId) {
    try {
      const response = await axios.get(`${API_URL}/trained_models/${modelId}/metrics`);
      return response.data;
    } catch (error) {
      console.error('Error fetching model metrics:', error);
      throw error;
    }
  },



  async getPredictions(projectId) {
    const response = await axios.get(`${API_URL}/predictions/${projectId}`);
    return response.data;
  },

  async getPrediction(predictionId) {
    const response = await axios.get(`${API_URL}/prediction/${predictionId}`);
    return response.data;
  },

  async getSummaryStatistics(predictionId) {
    try {
      const response = await axios.get(`${API_URL}/analysis/summary/${predictionId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting summary statistics:', error);
      throw error;
    }
  },

  async getChangeAnalysis(predictionId1, predictionId2) {
    try {
      const response = await axios.get(`${API_URL}/analysis/change/${predictionId1}/${predictionId2}`);
      return response.data;
    } catch (error) {
      console.error('Error getting change analysis:', error);
      throw error;
    }
  },

  async renamePrediction(predictionId, newName) {
    try {
      const response = await axios.put(`${API_URL}/predictions/${predictionId}/rename`, { new_name: newName });
      return response.data;
    } catch (error) {
      console.error('Error renaming prediction:', error);
      throw error;
    }
  },

  async deletePrediction(predictionId) {
    try {
      const response = await axios.delete(`${API_URL}/predictions/${predictionId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting prediction:', error);
      throw error;
    }
  },

};