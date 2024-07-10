import { defineStore } from 'pinia'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    predictionResults: [],
    selectedPrediction: null,
    analysisResults: null,
  }),
  actions: {
    setSelectedPrediction(prediction) {
      this.selectedPrediction = prediction
    },
    async runAnalysis(params) {
      // Implement analysis logic here
      // Update this.analysisResults with the analysis results
    },
  },
})