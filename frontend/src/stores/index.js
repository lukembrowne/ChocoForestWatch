import { createPinia } from 'pinia'
import { useTrainingStore } from './trainingStore'
import { usePredictionStore } from './predictionStore'
import { useAnalysisStore } from './analysisStore'

export default function (/* { store, ssrContext } */) {
  const pinia = createPinia()

  return pinia
}

// Optionally, you can still export your store hooks if needed elsewhere
export { useTrainingStore, usePredictionStore, useAnalysisStore }