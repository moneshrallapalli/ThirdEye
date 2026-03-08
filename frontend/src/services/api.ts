/**
 * API service for backend communication
 */
import axios from 'axios';
import { Camera, Event, Alert, SummaryStats } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const cameraApi = {
  getAll: async (): Promise<Camera[]> => {
    const response = await api.get('/cameras');
    return response.data;
  },

  create: async (name: string, location: string, streamUrl: string): Promise<Camera> => {
    const response = await api.post('/cameras', { name, location, stream_url: streamUrl });
    return response.data;
  },

  start: async (cameraId: number): Promise<void> => {
    await api.post(`/cameras/${cameraId}/start`);
  },

  stop: async (cameraId: number): Promise<void> => {
    await api.post(`/cameras/${cameraId}/stop`);
  },

  delete: async (cameraId: number): Promise<void> => {
    await api.delete(`/cameras/${cameraId}`);
  },
};

export const eventApi = {
  getAll: async (params?: {
    camera_id?: number;
    start_date?: string;
    end_date?: string;
    severity?: string;
    limit?: number;
  }): Promise<Event[]> => {
    const response = await api.get('/events', { params });
    return response.data;
  },
};

export const alertApi = {
  getAll: async (params?: {
    is_read?: boolean;
    severity?: string;
    limit?: number;
  }): Promise<Alert[]> => {
    const response = await api.get('/alerts', { params });
    return response.data;
  },

  acknowledge: async (alertId: number): Promise<Alert> => {
    const response = await api.post(`/alerts/${alertId}/acknowledge`);
    return response.data;
  },
};

export const statsApi = {
  getSummary: async (hours: number = 24): Promise<SummaryStats> => {
    const response = await api.get('/stats/summary', { params: { hours } });
    return response.data;
  },
};

export default api;
