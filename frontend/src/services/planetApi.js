import axios from 'axios';

const API_URL = 'http://127.0.0.1:5000/api'; // Update this to match your Flask app's URL

const planetApi = axios.create({
  baseURL: API_URL
});


export default {
  getAvailableQuads: async (areaOfInterest, mosaicName = 'planet_medres_normalized_analytic_2022-08_mosaic') => {
    try {
      const response = await planetApi.post('/planet/quads', {
        bbox: areaOfInterest,
        mosaic_name: mosaicName
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching quads from Planet API:', error);
      throw error;
    }
  }
};