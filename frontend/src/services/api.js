// services/api.js
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// WebSocket connection function
export const connectWebSocket = (projectId, onMessage) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/progress/${projectId}/`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
    };

    return ws;
};

// API endpoints
export const endpoints = {
    // Project endpoints
    projects: {
        list: () => api.get('/projects/'),
        create: (data) => api.post('/projects/', data),
        get: (id) => api.get(`/projects/${id}/`),
        update: (id, data) => api.put(`/projects/${id}/`, data),
        delete: (id) => api.delete(`/projects/${id}/`),
    },

    // Training set endpoints
    trainingSets: {
        list: (projectId) => api.get('/training-sets/', { params: { project_id: projectId } }),
        create: (data) => api.post('/training-sets/', data),
        update: (id, data) => api.put(`/training-sets/${id}/`, data),
        setExcluded: (id, excluded) => api.put(`/training-sets/${id}/excluded/`, { excluded }),
    },

    // Model endpoints
    models: {
        list: (projectId) => api.get('/trained-models/', { params: { project_id: projectId } }),
        train: (data) => api.post('/trained-models/train/', data),
        delete: (id) => api.delete(`/trained-models/${id}/`),
    },

    // Prediction endpoints
    predictions: {
        list: (projectId) => api.get('/predictions/', { params: { project_id: projectId } }),
        generate: (data) => api.post('/predictions/generate/', data),
        delete: (id) => api.delete(`/predictions/${id}/`),
    },

    // Hotspot endpoints
    hotspots: {
        list: (predictionId) => api.get(`/hotspots/`, { params: { prediction_id: predictionId } }),
        verify: (id, status) => api.put(`/hotspots/${id}/verify/`, { status }),
    },
};

export default api;