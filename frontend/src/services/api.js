// API service for frontend
import axios from 'axios';

export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Build an absolute URL out of a server-returned path (which the backend
// returns as a leading-slash path like "/api/v1/encode/download/abc").
export const buildAbsoluteUrl = (path) => {
  if (!path) return path;
  if (/^https?:\/\//.test(path)) return path;       // already absolute
  return `${API_URL}${path.startsWith('/') ? '' : '/'}${path}`;
};

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Encode image endpoint
export const encodeImage = async (file, ownerName, ownerEmail, location = '', description = '') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('owner_name', ownerName);
  formData.append('owner_email', ownerEmail);
  if (location) formData.append('location', location);
  if (description) formData.append('description', description);

  return api.post('/api/v1/encode/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

// Decode image endpoint
export const decodeImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  return api.post('/api/v1/decode/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

// Get tracking info
export const getTrackingInfo = async (trackingId) => {
  return api.get(`/api/v1/tracking/${trackingId}`);
};

// Test robustness
export const testRobustness = async (file, trackingId = null) => {
  const formData = new FormData();
  formData.append('file', file);
  if (trackingId) formData.append('tracking_id', trackingId);

  return api.get('/api/v1/encode/test-robustness', {
    params: { trackingId },
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

// Health check
export const healthCheck = async () => {
  return api.get('/health');
};

export default api;
