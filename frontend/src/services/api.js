// services/api.js
import axios from 'axios';

const API_URL = 'http://127.0.0.1:5000/api';

export default {
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
  fetchRasters() {
    return axios.get(`${API_URL}/list_rasters`);
  },
  fetchVectors() {
    return axios.get(`${API_URL}/list_vectors`);
  },
};