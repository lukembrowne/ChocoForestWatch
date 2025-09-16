import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import authService from '../services/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const isInitialized = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!user.value)
  const currentUser = computed(() => user.value)

  // Actions
  const initializeAuth = () => {
    if (!isInitialized.value) {
      const storedUser = authService.getCurrentUser()
      user.value = storedUser
      isInitialized.value = true
    }
  }

  const setUser = (userData) => {
    user.value = userData
  }

  const clearUser = () => {
    user.value = null
  }

  const login = async (username, password, remember = false) => {
    try {
      const response = await authService.login(username, password, remember)
      user.value = response // Store the full response which contains user and token
      return response
    } catch (error) {
      throw error
    }
  }

  const register = async (username, email, password, preferredLanguage) => {
    try {
      const response = await authService.register(username, email, password, preferredLanguage)
      return response
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    authService.logout()
    user.value = null
  }

  return {
    // State
    user,
    isInitialized,
    
    // Getters
    isAuthenticated,
    currentUser,
    
    // Actions
    initializeAuth,
    setUser,
    clearUser,
    login,
    register,
    logout
  }
})
