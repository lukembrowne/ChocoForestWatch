import { defineStore } from 'pinia'
import apiService from '../services/api'


export const useTrainingStore = defineStore('training', {
  state: () => ({
    selectedRaster: null,
    selectedVector: null,
    drawnPolygons: [],
    pixelsExtracted: false,
    extractionError: null
  }),

  getters: {
    canExtractPixels: (state) =>
      state.selectedRaster && (state.selectedVector || state.drawnPolygons.length > 0)
  },

  actions: {
    setSelectedRaster(raster) {
      this.selectedRaster = raster
    },

    setSelectedVector(vector) {
      this.selectedVector = vector
    },

    setDrawnPolygons(polygons) {
      this.drawnPolygons = polygons
    },

    async extractPixels(polygonsToUse) {
      if (!this.canExtractPixels) {
        throw new Error('Cannot extract pixels: No raster or polygons selected');
      }

      this.extractionError = null;
      this.pixelsExtracted = false;

      try {
        const response = await apiService.extractPixels({
          rasterId: this.selectedRaster.id,
          polygons: polygonsToUse
        });

        console.log('Pixel extraction response:', response);
        this.pixelsExtracted = true;
        return response;
      } catch (error) {
        console.error('Error extracting pixels:', error);
        this.extractionError = error.message || 'An error occurred during pixel extraction';
        throw error;
      }
    }
  }
})