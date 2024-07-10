import { defineStore } from 'pinia'

export const usePredictionStore = defineStore('prediction', {
  state: () => ({
    models: [],
    selectedModel: null,
    rasters: [],
    selectedRaster: null,
    predictionResult: null,
  }),
  actions: {
    setSelectedModel(model) {
      this.selectedModel = model
    },
    setSelectedRaster(raster) {
      this.selectedRaster = raster
    },
    async predictLandcover() {
      // Implement land cover prediction logic here
      // Update this.predictionResult with the prediction
    },
  },
})