import { defineStore } from 'pinia'
import api from 'src/services/api'

export const useModelEvaluationStore = defineStore('modelEvaluation', {
  state: () => ({
    models: [],
    metrics: null,
  }),
  actions: {
    async fetchModels() {
      try {
        const response = await api.fetchModels()
        this.models = response.data
      } catch (error) {
        console.error('Error fetching models:', error)
        throw error
      }
    },
    async fetchModelMetrics(modelId) {
      try {
        const response = await api.fetchModelMetrics(modelId)
        this.metrics = response.data
        console.log("Fetched model metrics:", this.metrics)
      } catch (error) {
        console.error('Error fetching model metrics:', error)
        throw error
      }
    },
  },
})