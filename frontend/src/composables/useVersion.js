import { ref, onMounted } from 'vue'
import api from '../services/api'

export function useVersion() {
  const version = ref('')
  const environment = ref('')
  const loading = ref(false)
  const error = ref(null)

  const fetchVersion = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await api.getVersion()
      version.value = response.data.version
      environment.value = response.data.environment
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch version info:', err)
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    fetchVersion()
  })

  return {
    version,
    environment,
    loading,
    error,
    fetchVersion
  }
}