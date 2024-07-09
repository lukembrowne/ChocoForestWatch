// services/api.js
import axios from 'axios';

const API_URL = 'http://127.0.0.1:5000/api';

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

  uploadRaster(formData) {
    return axios.post(`${API_URL}/upload_raster`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  uploadVector(formData) {
    return axios.post(`${API_URL}/upload_vector`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  async fetchRasterById(id) {
    try {
      const response = await axios.get(`${API_URL}/rasters/${id}`);
      return response.data;  // This line is crucial
    } catch (error) {
      console.error('Error fetching raster:', error);
      throw error;
    }
  },

  async fetchVectorById(id) {
    try {
      const response = await axios.get(`${API_URL}/vectors/${id}`);
      return response.data;  // This line is crucial
    } catch (error) {
      console.error('Error fetching vector:', error);
      throw error;
    }
  },
  fetchRasters() {
    // const response = await axios.get(`${API_URL}/list_rasters`);
    // const rasters = response.data; // Extract data array from response
    // console.log('Rasters from fetchRasters:', rasters);
    // return rasters;
    return axios.get(`${API_URL}/list_rasters`);
  },
  fetchVectors() {
    return axios.get(`${API_URL}/list_vectors`);
  },
  fetchModels() {
    return axios.get(`${API_URL}/list_models`);
  },
  predictLandcover(JSON) {
    return axios.post(`${API_URL}/predict_landcover`, JSON, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
  },

  extractPixels(JSON) {
    return axios.post(`${API_URL}/extract_pixels`, JSON, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
  },
};