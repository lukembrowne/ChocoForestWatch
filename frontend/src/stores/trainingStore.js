import { defineStore } from 'pinia'
import apiService from '../services/api'


export const useTrainingStore = defineStore('training', {
  state: () => ({
    selectedRaster: null,
    selectedVector: null,
    drawnPolygons: [],
    pixelsExtracted: false,
    extractionError: null,
    selectedPolygon: null,
  }),

  getters: {
    canExtractPixels: (state) =>
      state.selectedRaster && (state.selectedVector || state.drawnPolygons.length > 0)
  },

  actions: {

    setDrawnPolygons(polygons) {
      this.drawnPolygons = polygons
    },

    addPolygon(polygon) {
      this.drawnPolygons.push(polygon);
    },
    removePolygon(id) {
      this.drawnPolygons = this.drawnPolygons.filter(p => p.id !== id);
    },
    updatePolygon(index, updatedPolygon) {
      this.drawnPolygons[index] = updatedPolygon;
    },
    setSelectedPolygon(polygon) {
      this.selectedPolygon = polygon;
    },
    clearPolygons() {
      this.drawnPolygons = []
    },
  }
})