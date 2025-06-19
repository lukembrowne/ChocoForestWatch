// services/api.js
import axios from 'axios';
import authService from './auth';

const API_URL = import.meta.env.VITE_API_URL;

// Set default project id to 6. This is the public map project.
const DEFAULT_PROJECT_ID = import.meta.env.VITE_DEFAULT_PUBLIC_PROJECT_ID;

// Add some debugging
console.log('API_URL:', API_URL);
console.log('Environment variables:', import.meta.env);

// Create axios instance with base configuration
const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Add request interceptor to add auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = authService.getToken();
        if (token) {
            config.headers['Authorization'] = `Token ${token}`;
        }
        return config;
    }
);

// Add response interceptor to handle auth errors
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            const hadToken = !!authService.getToken();
            // Only force login redirect if user previously had a token (was logged in)
            if (hadToken) {
              authService.logout();
              window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

// API functions
const api = {

    // Project endpoints
    getProjects() {
        return apiClient.get('/projects/');
    },
    
    createProject(projectData) {

        return apiClient.post('/projects/', projectData); // Has to end in trailing slash
    },
    
    getProject(id) {
        return apiClient.get(`/projects/${id}/`);
    },
    
    updateProject(id, data) {
        return apiClient.put(`/projects/${id}/`, data);
    },
    
    setProjectAOI(id, aoiGeojson, aoiExtentLatLon, availableDates) {
        const data = {
            aoi: aoiGeojson.geometry,
            aoi_extent_lat_lon: aoiExtentLatLon,
            basemap_dates: availableDates
        };
        return apiClient.put(`/projects/${id}/`, data);
    },
    
    deleteProject(id) {
        return apiClient.delete(`/projects/${id}/`);
    },

    // Training set endpoints
    getTrainingPolygons(projectId) {
        return apiClient.get('/training-sets/', { params: { project_id: projectId } });
    },
    
    getSpecificTrainingPolygons(projectId, setId) {
        return apiClient.get('/training-sets/', { 
            params: { 
                project_id: projectId,
                id: setId 
            }
        });
    },
    
    saveTrainingPolygons(data) {
        return apiClient.post('/training-sets/', data);
    },
    
    updateTrainingPolygons(id, data) {
        return apiClient.put(`/training-sets/${id}/`, data);
    },
    
    setTrainingSetExcluded(id, excluded) {
        return apiClient.put(`/training-sets/${id}/excluded/`, { excluded });
    },


    getTrainingDataSummary(projectId) {
        return apiClient.get(`/training-sets/summary/`, { params: { project_id: projectId } });
    },

    // Model endpoints
    getTrainedModels(projectId) {
        return apiClient.get('/trained-models/', { params: { project_id: projectId } });
    },
    
    trainModel(data) {
        return apiClient.post('/trained-models/train/', data);
    },
    
    deleteModel(id) {
        return apiClient.delete(`/trained-models/${id}/`);
    },

    getModelTrainingProgress(taskId) {
        return apiClient.get(`/trained-models/training_progress/${taskId}/`);
    },

    // Prediction endpoints
    getPredictions(projectId) {
        return apiClient.get('/predictions/', { params: { project_id: projectId } });
    },
    
    generatePrediction(data) {
        return apiClient.post('/predictions/generate/', data);
    },
    
    deletePrediction(id) {
        return apiClient.delete(`/predictions/${id}/`);
    },


    verifyHotspot(id, status) {
        return apiClient.put(`/hotspots/${id}/verify/`, { status });
    },

    // Analysis endpoints
    analyzeChange(data) {
        return apiClient.post('/analysis/change/', data);
    },

    getDeforestationHotspots(predictionId, minAreaHa, source) {
        return apiClient.get(`/analysis/deforestation_hotspots/${predictionId}/`, { 
            params: { 
                min_area_ha: minAreaHa,
                source: source
            } 
        });
    },

    getSummaryStatistics(predictionId) {
        return apiClient.get(`/predictions/${predictionId}/summary/`);
    },

    // Model metrics endpoint
    getModelMetrics(projectId) {
        return apiClient.get(`/trained_models/${projectId}/metrics/`);
    },

    cancelModelTraining(taskId) {
        return apiClient.post(`/trained-models/training_progress/${taskId}/cancel/`);
    },

    // Change analysis endpoint
    getChangeAnalysis(data) {
        return apiClient.post('/analysis/change/', data);
    },

    // User settings endpoints
    getUserSettings() {
        return apiClient.get('/user/settings/');
    },

    updateUserSettings(settings) {
        return apiClient.patch('/user/settings/', settings);
    },

    // Feedback endpoint
    submitFeedback(data) {
        return apiClient.post('/feedback/', data);
    },

    getSystemStatistics() {
        return apiClient.get('/api/statistics/system/');
    },

    // Random points endpoints
    getRandomPoints(collectionId, count = 1) {
        return apiClient.get(`/random_points_collection/${collectionId}/`, {
            params: { count }
        });
    },

    // AOI summary statistics
    getAOISummary(aoiGeoJSON, collectionId) {
        return apiClient.post('/aoi_summary/', { aoi: aoiGeoJSON, collection_id: collectionId });
    },

    // GFW deforestation alerts
    getGFWAlerts2022() {
        return apiClient.get('/gfw/alerts/2022/');
    },

    // Western Ecuador cached statistics
    getWesternEcuadorStats(collectionId) {
        return apiClient.get('/western_ecuador_stats/', {
            params: { collection_id: collectionId }
        });
    },
};

// Initialize function for boot
function initializeApi(app) {
    app.config.globalProperties.$axios = axios;
    app.config.globalProperties.$api = api;
}

export { initializeApi };
export default api;

// Named exports
export { DEFAULT_PROJECT_ID }

