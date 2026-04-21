import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Camera, Alert, SummaryStats } from '../types';
import { cameraApi, alertApi, statsApi } from '../services/api';
import wsService from '../services/websocket';

export interface NarrationEntry {
  id: string;
  timestamp: string;
  cameraId: number;
  description: string;
  significance: number;
  detections: number;
  context?: string;
}

interface SurveillanceContextType {
  cameras: Camera[];
  alerts: Alert[];
  stats: SummaryStats | null;
  liveFeedData: Map<number, { frame: string; timestamp: string }>;
  narrations: NarrationEntry[];
  unreadAlerts: number;
  loadCameras: () => Promise<void>;
  handleCameraStart: (id: number) => Promise<void>;
  handleCameraStop: (id: number) => Promise<void>;
  handleCameraAdd: (name: string, location: string, streamUrl: string, tasks?: { command: string; task_type: string; priority?: number }[]) => Promise<void>;
  handleCameraDelete: (id: number) => Promise<void>;
  handleAcknowledgeAlert: (id: number | string) => Promise<void>;
  handleClearAllAlerts: () => void;
  handleSystemCommand: (command: string) => void;
}

const SurveillanceContext = createContext<SurveillanceContextType | undefined>(undefined);

export const useSurveillance = () => {
  const ctx = useContext(SurveillanceContext);
  if (!ctx) throw new Error('useSurveillance must be used within SurveillanceProvider');
  return ctx;
};

export const SurveillanceProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [liveFeedData, setLiveFeedData] = useState<Map<number, { frame: string; timestamp: string }>>(new Map());
  const [narrations, setNarrations] = useState<NarrationEntry[]>([]);

  useEffect(() => {
    loadCameras();
    loadAlerts();
    loadStats();
    const interval = setInterval(loadStats, 30000);

    wsService.connectLiveFeed((update) => {
      setLiveFeedData((prev) => {
        const m = new Map(prev);
        m.set(update.camera_id, { frame: update.frame, timestamp: update.timestamp });
        return m;
      });
    });

    wsService.connectAlerts((alert) => {
      setAlerts((prev) => [alert, ...prev].slice(0, 50));
      if (alert.severity === 'CRITICAL') playAlertSound();
    });

    wsService.connectAnalysis((update) => {
      setNarrations((prev) =>
        [...prev, {
          id: `${update.analysis.camera_id}-${Date.now()}`,
          timestamp: update.timestamp,
          cameraId: update.analysis.camera_id,
          description: update.analysis.scene_description,
          significance: update.analysis.significance,
          detections: update.analysis.detections,
          context: update.analysis.context,
        }].slice(-100)
      );
    });

    wsService.connectSystem((msg) => console.log('System:', msg));

    return () => {
      clearInterval(interval);
      wsService.disconnectAll();
    };
  }, []);

  const loadCameras = async () => {
    try { setCameras(await cameraApi.getAll()); } catch {}
  };

  const loadAlerts = async () => {
    try { setAlerts(await alertApi.getAll({ limit: 100 })); } catch {}
  };

  const loadStats = async () => {
    try { setStats(await statsApi.getSummary(24)); } catch {}
  };

  const handleCameraStart = async (id: number) => {
    try {
      await cameraApi.start(id);
      await loadCameras();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to start camera';
      alert(msg);
      throw e;
    }
  };

  const handleCameraStop = async (id: number) => {
    try {
      await cameraApi.stop(id);
      setLiveFeedData((prev) => { const m = new Map(prev); m.delete(id); return m; });
      await loadCameras();
    } catch {}
  };

  const handleCameraAdd = async (name: string, location: string, streamUrl: string, tasks?: { command: string; task_type: string; priority?: number }[]) => {
    await cameraApi.create(name, location, streamUrl, tasks);
    await loadCameras();
  };

  const handleCameraDelete = async (id: number) => {
    await cameraApi.delete(id);
    setLiveFeedData((prev) => { const m = new Map(prev); m.delete(id); return m; });
    await loadCameras();
  };

  const handleAcknowledgeAlert = async (id: number | string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    if (typeof id === 'number') { try { await alertApi.delete(id); } catch {} }
  };

  const handleClearAllAlerts = async () => {
    setAlerts([]);
    try { await alertApi.deleteAll(); } catch {}
  };

  const handleSystemCommand = (command: string) => {
    wsService.send('/ws/system', { command, params: {} });
  };

  const playAlertSound = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = 800; osc.type = 'sine';
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
      osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.5);
    } catch {}
  };

  return (
    <SurveillanceContext.Provider value={{
      cameras, alerts, stats, liveFeedData, narrations,
      unreadAlerts: alerts.filter((a) => !a.is_read).length,
      loadCameras, handleCameraStart, handleCameraStop,
      handleCameraAdd, handleCameraDelete,
      handleAcknowledgeAlert, handleClearAllAlerts, handleSystemCommand,
    }}>
      {children}
    </SurveillanceContext.Provider>
  );
};
