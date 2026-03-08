import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Camera, Alert, SummaryStats } from '../types';
import { cameraApi, alertApi, statsApi } from '../services/api';
import wsService from '../services/websocket';
import LiveFeedGrid from './LiveFeedGrid';
import AlertPanel from './AlertPanel';
import SceneNarration from './SceneNarration';
import SummaryStatsComponent from './SummaryStats';
import SystemCommand from './SystemCommand';
import DailySummary from './DailySummary';

interface NarrationEntry {
  id: string;
  timestamp: string;
  cameraId: number;
  description: string;
  significance: number;
  detections: number;
  context?: string;
}

const tabs = [
  { id: 'dashboard', label: 'Overview' },
  { id: 'live', label: 'Live Cameras' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'summary', label: 'Analytics' },
];

function Dashboard() {
  const { user, logout } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [liveFeedData, setLiveFeedData] = useState<Map<number, { frame: string; timestamp: string }>>(new Map());
  const [narrations, setNarrations] = useState<NarrationEntry[]>([]);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    loadCameras();
    loadAlerts();
    loadStats();
    const statsInterval = setInterval(loadStats, 30000);
    return () => clearInterval(statsInterval);
  }, []);

  useEffect(() => {
    wsService.connectLiveFeed((update) => {
      setLiveFeedData((prev) => {
        const newMap = new Map(prev);
        newMap.set(update.camera_id, { frame: update.frame, timestamp: update.timestamp });
        return newMap;
      });
    });

    wsService.connectAlerts((alert) => {
      setAlerts((prev) => [alert, ...prev].slice(0, 50));
      if (alert.severity === 'CRITICAL') playAlertSound();
    });

    wsService.connectAnalysis((update) => {
      const narration: NarrationEntry = {
        id: `${update.analysis.camera_id}-${Date.now()}`,
        timestamp: update.timestamp,
        cameraId: update.analysis.camera_id,
        description: update.analysis.scene_description,
        significance: update.analysis.significance,
        detections: update.analysis.detections,
        context: update.analysis.context,
      };
      setNarrations((prev) => [...prev, narration].slice(-100));
    });

    wsService.connectSystem((message) => {
      console.log('System message:', message);
    });

    return () => wsService.disconnectAll();
  }, []);

  const loadCameras = async () => {
    try { setCameras(await cameraApi.getAll()); } catch {}
  };

  const loadAlerts = async () => {
    try { setAlerts(await alertApi.getAll({ limit: 50 })); } catch {}
  };

  const loadStats = async () => {
    try { setStats(await statsApi.getSummary(24)); } catch {}
  };

  const handleCameraStart = async (cameraId: number) => {
    try { await cameraApi.start(cameraId); await loadCameras(); } catch {}
  };

  const handleCameraStop = async (cameraId: number) => {
    try {
      await cameraApi.stop(cameraId);
      setLiveFeedData((prev) => { const m = new Map(prev); m.delete(cameraId); return m; });
      await loadCameras();
    } catch {}
  };

  const handleCameraAdd = async (name: string, location: string, streamUrl: string) => {
    await cameraApi.create(name, location, streamUrl);
    await loadCameras();
  };

  const handleCameraDelete = async (cameraId: number) => {
    await cameraApi.delete(cameraId);
    setLiveFeedData((prev) => { const m = new Map(prev); m.delete(cameraId); return m; });
    await loadCameras();
  };

  const handleAcknowledgeAlert = async (alertId: number | string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    if (typeof alertId === 'number') {
      try { await alertApi.acknowledge(alertId); } catch {}
    }
  };

  const handleClearAllAlerts = () => setAlerts([]);

  const handleSystemCommand = (command: string) => {
    wsService.send('/ws/system', { command, params: {} });
  };

  const playAlertSound = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 800;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.5);
    } catch {}
  };

  const unreadAlerts = alerts.filter((a) => !a.is_read).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <span className="text-base font-semibold text-gray-900">ThirdEye</span>
            </div>

            {/* Nav tabs */}
            <nav className="flex items-center gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    activeTab === tab.id
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {tab.label}
                  {tab.id === 'alerts' && unreadAlerts > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold bg-red-500 text-white rounded-full">
                      {unreadAlerts > 9 ? '9+' : unreadAlerts}
                    </span>
                  )}
                </button>
              ))}
            </nav>

            {/* User + status */}
            <div className="flex items-center gap-3">
              {stats && stats.active_cameras > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                  {stats.active_cameras} active
                </div>
              )}
              {user && (
                <span className="text-sm text-gray-500 hidden sm:block">{user.email}</span>
              )}
              <button
                onClick={logout}
                className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {activeTab === 'dashboard' && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <LiveFeedGrid
                  cameras={cameras}
                  liveFeedData={liveFeedData}
                  onCameraStart={handleCameraStart}
                  onCameraStop={handleCameraStop}
                  onCameraAdd={handleCameraAdd}
                  onCameraDelete={handleCameraDelete}
                />
              </div>
              <div>
                <AlertPanel
                  alerts={alerts}
                  onAcknowledge={handleAcknowledgeAlert}
                  onClearAll={handleClearAllAlerts}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <SystemCommand onCommand={handleSystemCommand} />
              </div>
              <div>
                <DailySummary stats={stats} />
              </div>
            </div>

            <SceneNarration narrations={narrations} />
          </>
        )}

        {activeTab === 'live' && (
          <LiveFeedGrid
            cameras={cameras}
            liveFeedData={liveFeedData}
            onCameraStart={handleCameraStart}
            onCameraStop={handleCameraStop}
            onCameraAdd={handleCameraAdd}
            onCameraDelete={handleCameraDelete}
          />
        )}

        {activeTab === 'alerts' && (
          <div className="max-w-3xl mx-auto">
            <AlertPanel alerts={alerts} onAcknowledge={handleAcknowledgeAlert} onClearAll={handleClearAllAlerts} />
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SummaryStatsComponent stats={stats} />
            <SceneNarration narrations={narrations} />
          </div>
        )}
      </main>
    </div>
  );
}

export default Dashboard;
