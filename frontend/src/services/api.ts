/**
 * API service for backend communication
 */
import axios from 'axios';
import { Camera, CameraTask, Event, Alert, SummaryStats } from '../types';

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

  create: async (
    name: string,
    location: string,
    streamUrl: string,
    tasks?: { command: string; task_type: string; priority?: number }[]
  ): Promise<Camera> => {
    const response = await api.post('/cameras', {
      name,
      location,
      stream_url: streamUrl,
      tasks: tasks ?? [],
    });
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

  query: async (cameraId: number, question: string): Promise<{
    camera_id: number;
    question: string;
    answer: string;
    scene_description: string;
    detections: any[];
    significance: number;
    query_match: boolean;
    query_confidence: number;
    frame: string;
    timestamp: string;
  }> => {
    const response = await api.post(`/cameras/${cameraId}/query`, { question });
    return response.data;
  },

  history: async (
    cameraId: number,
    question: string,
    startTime?: string,
    endTime?: string,
  ): Promise<{
    camera_id: number;
    question: string;
    answer: string;
    events_analysed: number;
    time_range: { start: string; end: string };
    relevant_frames: {
      event_id: number;
      timestamp: string;
      scene_description: string;
      significance: number;
      frame_url: string | null;
    }[];
  }> => {
    const body: Record<string, any> = { question };
    if (startTime) body.start_time = startTime;
    if (endTime) body.end_time = endTime;
    const response = await api.post(`/cameras/${cameraId}/history`, body);
    return response.data;
  },
};

export const taskApi = {
  getForCamera: async (cameraId: number): Promise<CameraTask[]> => {
    const response = await api.get(`/cameras/${cameraId}/tasks`);
    return response.data;
  },

  create: async (cameraId: number, command: string, priority?: number): Promise<CameraTask> => {
    const response = await api.post(`/cameras/${cameraId}/tasks`, {
      command,
      task_type: 'custom',
      priority: priority ?? 1,
    });
    return response.data;
  },

  update: async (cameraId: number, taskId: number, data: Partial<CameraTask>): Promise<CameraTask> => {
    const response = await api.put(`/cameras/${cameraId}/tasks/${taskId}`, data);
    return response.data;
  },

  delete: async (cameraId: number, taskId: number): Promise<void> => {
    await api.delete(`/cameras/${cameraId}/tasks/${taskId}`);
  },

  getPresets: async (): Promise<Record<string, { command: string; task_type: string }[]>> => {
    const response = await api.get('/camera-presets');
    return response.data;
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

  acknowledgeAll: async (): Promise<{ acknowledged: number }> => {
    const response = await api.post('/alerts/acknowledge-all');
    return response.data;
  },

  delete: async (alertId: number): Promise<void> => {
    await api.delete(`/alerts/${alertId}`);
  },

  deleteAll: async (): Promise<{ deleted: number }> => {
    const response = await api.delete('/alerts');
    return response.data;
  },
};

export interface SceneSearchMatch {
  event_id: number;
  camera_id: number;
  camera_name: string;
  camera_location: string | null;
  timestamp: string;
  scene_description: string;
  significance: number;
  is_anomaly: boolean;
  semantic_similarity: number | null;
  frame_url: string | null;
  source: 'semantic' | 'text';
}

export interface SceneSearchResult {
  query: string;
  answer: string;
  total_matches: number;
  time_range: { start: string; end: string };
  matches: SceneSearchMatch[];
}

export const searchApi = {
  scenes: async (
    query: string,
    startTime?: string,
    endTime?: string,
    cameraIds?: number[],
    limit?: number,
  ): Promise<SceneSearchResult> => {
    const body: Record<string, any> = { query };
    if (startTime) body.start_time = startTime;
    if (endTime) body.end_time = endTime;
    if (cameraIds?.length) body.camera_ids = cameraIds;
    if (limit) body.limit = limit;
    const response = await api.post('/search/scenes', body);
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
