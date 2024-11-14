// services/api.js
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// API functions
export default {
    // Project endpoints
    getProjects() {
        return api.get('/projects/');
    },
    
    createProject(data) {
        return api.post('/projects/', data);
    },
    
    getProject(id) {
        return api.get(`/projects/${id}/`);
    },
    
    updateProject(id, data) {
        return api.put(`/projects/${id}/`, data);
    },
    
    setProjectAOI(id, aoiGeojson, aoiExtentLatLon, availableDates) {
        const data = {
            aoi: aoiGeojson.geometry,
            aoi_extent_lat_lon: aoiExtentLatLon,
            basemap_dates: availableDates
        };
        return api.put(`/projects/${id}/`, data);
    },
    
    deleteProject(id) {
        return api.delete(`/projects/${id}/`);
    },

    // Training set endpoints
    getTrainingPolygons(projectId) {
        return api.get('/training-sets/', { params: { project_id: projectId } });
    },
    
    saveTrainingPolygons(data) {
        return api.post('/training-sets/', data);
    },
    
    updateTrainingPolygons(id, data) {
        return api.put(`/training-sets/${id}/`, data);
    },
    
    setTrainingSetExcluded(id, excluded) {
        return api.put(`/training-sets/${id}/excluded/`, { excluded });
    },

    // Model endpoints
    getModels(projectId) {
        return api.get('/trained-models/', { params: { project_id: projectId } });
    },
    
    trainModel(data) {
        return api.post('/trained-models/train/', data);
    },
    
    deleteModel(id) {
        return api.delete(`/trained-models/${id}/`);
    },

    // Prediction endpoints
    getPredictions(projectId) {
        return api.get('/predictions/', { params: { project_id: projectId } });
    },
    
    generatePrediction(data) {
        return api.post('/predictions/generate/', data);
    },
    
    deletePrediction(id) {
        return api.delete(`/predictions/${id}/`);
    },

    // Hotspot endpoints
    getHotspots(predictionId) {
        return api.get('/hotspots/', { params: { prediction_id: predictionId } });
    },
    
    verifyHotspot(id, status) {
        return api.put(`/hotspots/${id}/verify/`, { status });
    },

    // Analysis endpoints
    analyzeChange(data) {
        return api.post('/analysis/change/', data);
    },

    getDeforestationHotspots(predictionId, params) {
        return api.get(`/analysis/deforestation_hotspots/${predictionId}/`, { params });
    },

    getSummaryStatistics(predictionId) {
        return api.get(`/analysis/summary/${predictionId}/`);
    }
};

// WebSocket connection function
export const connectWebSocket = (projectId, onMessage) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/progress/${projectId}/`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
    };

    return ws;
};