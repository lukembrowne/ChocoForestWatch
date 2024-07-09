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
  fetchRasterById(id) {
    return axios.get(`${API_URL}/rasters/${id}`);
  },

  fetchVectorById(id) {
    return axios.get(`${API_URL}/vectors/${id}`);
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