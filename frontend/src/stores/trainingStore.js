import { defineStore } from 'pinia'

export const useTrainingStore = defineStore('training', {
  state: () => ({
    drawnPolygons: [],
    pixelsExtracted: false,
    extractionError: null,
    selectedPolygon: null,
    selectedBasemapDate: null, 
  }),

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
    setSelectedBasemapDate(date) { 
      this.selectedBasemapDate = date;
    },
  }
})