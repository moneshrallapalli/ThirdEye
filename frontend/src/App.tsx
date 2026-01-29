/**
 * Main Application Component
 */
import React, { useState, useEffect } from 'react';
import { Camera, Alert, SummaryStats } from './types';
import { cameraApi, alertApi, statsApi } from './services/api';
import wsService from './services/websocket';
import LiveFeedGrid from './components/LiveFeedGrid';
import AlertPanel from './components/AlertPanel';
import SceneNarration from './components/SceneNarration';
import SummaryStatsComponent from './components/SummaryStats';
import SystemCommand from './components/SystemCommand';
import DailySummary from './components/DailySummary';

interface NarrationEntry {
  id: string;
  timestamp: string;
  cameraId: number;
  description: string;
  significance: number;
  detections: number;
  context?: string;
}

function App() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [liveFeedData, setLiveFeedData] = useState<Map<number, { frame: string; timestamp: string }>>(new Map());
  const [narrations, setNarrations] = useState<NarrationEntry[]>([]);
  const [activeTab, setActiveTab] = useState('dashboard');

  // Load initial data
  useEffect(() => {
    loadCameras();
    loadAlerts();
    loadStats();

    // Refresh stats every 30 seconds
    const statsInterval = setInterval(loadStats, 30000);

    return () => clearInterval(statsInterval);
  }, []);

  // Setup WebSocket connections
  useEffect(() => {
    // Connect to live feed
    wsService.connectLiveFeed((update) => {
      console.log('Live feed update received:', {
        camera_id: update.camera_id,
        timestamp: update.timestamp,
        hasFrame: !!update.frame,
        frameLength: update.frame?.length
      });
      
      setLiveFeedData((prev) => {
        const newMap = new Map(prev);
        newMap.set(update.camera_id, {
          frame: update.frame,
          timestamp: update.timestamp
        });
        console.log('Updated liveFeedData for camera:', update.camera_id);
        return newMap;
      });
    });

    // Connect to alerts
    wsService.connectAlerts((alert) => {
      setAlerts((prev) => [alert, ...prev].slice(0, 50)); // Keep last 50 alerts

      // Play alert sound for critical alerts
      if (alert.severity === 'CRITICAL') {
        playAlertSound();
      }
    });

    // Connect to analysis
    wsService.connectAnalysis((update) => {
      const narration: NarrationEntry = {
        id: `${update.analysis.camera_id}-${Date.now()}`,
        timestamp: update.timestamp,
        cameraId: update.analysis.camera_id,
        description: update.analysis.scene_description,
        significance: update.analysis.significance,
        detections: update.analysis.detections,
        context: update.analysis.context
      };

      setNarrations((prev) => [...prev, narration].slice(-100)); // Keep last 100 narrations
    });

    // Connect to system
    wsService.connectSystem((message) => {
      console.log('System message:', message);
    });

    return () => {
      wsService.disconnectAll();
    };
  }, []);

  const loadCameras = async () => {
    try {
      const data = await cameraApi.getAll();
      setCameras(data);
    } catch (error) {
      console.error('Error loading cameras:', error);
    }
  };

  const loadAlerts = async () => {
    try {
      const data = await alertApi.getAll({ limit: 50 });
      setAlerts(data);
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  };

  const loadStats = async () => {
    try {
      const data = await statsApi.getSummary(24);
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleCameraStart = async (cameraId: number) => {
    try {
      await cameraApi.start(cameraId);
      await loadCameras();
    } catch (error) {
      console.error('Error starting camera:', error);
    }
  };

  const handleCameraStop = async (cameraId: number) => {
    try {
      await cameraApi.stop(cameraId);
      setLiveFeedData((prev) => {
        const newMap = new Map(prev);
        newMap.delete(cameraId);
        return newMap;
      });
      await loadCameras();
    } catch (error) {
      console.error('Error stopping camera:', error);
    }
  };

  const handleAcknowledgeAlert = async (alertId: number | string) => {
    try {
      console.log('Acknowledging alert:', alertId);
      
      // Remove the alert from the list immediately (clear it)
      setAlerts((prev) => {
        const filtered = prev.filter((alert) => alert.id !== alertId);
        console.log('Alerts after filter:', filtered.length);
        return filtered;
      });
      
      // If it's a numeric ID, also acknowledge in backend
      if (typeof alertId === 'number') {
        await alertApi.acknowledge(alertId);
      }
      
      console.log('Alert acknowledged and cleared:', alertId);
    } catch (error) {
      console.error('Error acknowledging alert:', error);
      // Even if backend fails, keep it removed from UI
    }
  };

  const handleClearAllAlerts = () => {
    console.log('Clearing all alerts');
    setAlerts([]);
  };

  const handleSystemCommand = (command: string) => {
    wsService.send('/ws/system', { command, params: {} });
  };

  const playAlertSound = () => {
    // Simple beep sound (in production, use a proper alert sound)
    const context = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = context.createOscillator();
    const gainNode = context.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(context.destination);

    oscillator.frequency.value = 800;
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.3, context.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.5);

    oscillator.start(context.currentTime);
    oscillator.stop(context.currentTime + 0.5);
  };

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'live', label: 'Live Cameras', icon: '📹' },
    { id: 'alerts', label: 'Alerts', icon: '🚨' },
    { id: 'summary', label: 'Summary', icon: '📈' }
  ];

  return (
    <div className="min-h-screen bg-dark-950">
      {/* Header */}
      <header className="bg-gradient-to-r from-dark-900 via-dark-900 to-dark-950 border-b border-dark-800 shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* ThirdEye Logo and Branding */}
            <div className="flex items-center gap-4">
              <div className="relative group">
                {/* Eye icon with gradient */}
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/50">
                  <div className="w-full h-full rounded-full bg-dark-900 flex items-center justify-center">
                    <svg className="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </div>
                </div>
                {/* Pulse effect */}
                <div className="absolute inset-0 rounded-full bg-cyan-400/20 animate-ping"></div>
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-cyan-500 bg-clip-text text-transparent">
                  THIRDEYE
                </h1>
                <p className="text-xs text-gray-400 tracking-wide">AI-Powered Intelligent Monitoring System</p>
              </div>
            </div>

            {/* Status and Actions */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                {stats && (
                  <>
                    <div className="flex items-center gap-2 px-4 py-2 bg-dark-800/50 rounded-lg border border-dark-700">
                      <span className={`w-2.5 h-2.5 rounded-full ${stats.active_cameras > 0 ? 'bg-green-400 animate-pulse shadow-lg shadow-green-400/50' : 'bg-gray-600'}`}></span>
                      <span className="text-sm text-gray-300 font-medium">
                        {stats.active_cameras} Camera{stats.active_cameras !== 1 ? 's' : ''}
                      </span>
                    </div>
                    {stats.critical_alerts > 0 && (
                      <div className="flex items-center gap-2 px-4 py-2 bg-red-500/10 rounded-lg border border-red-500/20 animate-pulse">
                        <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <span className="text-sm text-red-400 font-semibold">{stats.critical_alerts} Critical</span>
                      </div>
                    )}
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button className="p-2.5 hover:bg-dark-800 rounded-lg transition-all hover:scale-110 group">
                  <svg className="w-5 h-5 text-gray-400 group-hover:text-cyan-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                </button>
                <button className="p-2.5 hover:bg-dark-800 rounded-lg transition-all hover:scale-110 group">
                  <svg className="w-5 h-5 text-gray-400 group-hover:text-cyan-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex gap-2 mt-6 border-b border-dark-800">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-6 py-3 font-medium transition-all duration-200 relative group
                  ${activeTab === tab.id
                    ? 'text-cyan-400'
                    : 'text-gray-400 hover:text-gray-300'
                  }
                `}
              >
                <span className="mr-2 text-lg">{tab.icon}</span>
                <span>{tab.label}</span>
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 shadow-lg shadow-cyan-500/50"></div>
                )}
                {activeTab !== tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                )}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {activeTab === 'dashboard' && (
          <>
            {/* Row 1: Live Camera Feeds + Alerts Panel */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Live Camera Feed - 2/3 width */}
              <div className="lg:col-span-2">
                <LiveFeedGrid
                  cameras={cameras}
                  liveFeedData={liveFeedData}
                  onCameraStart={handleCameraStart}
                  onCameraStop={handleCameraStop}
                />
              </div>

              {/* Alerts and Notifications - 1/3 width */}
              <div>
                <AlertPanel
                  alerts={alerts}
                  onAcknowledge={handleAcknowledgeAlert}
                  onClearAll={handleClearAllAlerts}
                />
              </div>
            </div>

            {/* Row 2: AI Command Center + Daily Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* AI Command Center - 2/3 width */}
              <div className="lg:col-span-2">
                <SystemCommand onCommand={handleSystemCommand} />
              </div>

              {/* Daily Summary - 1/3 width */}
              <div>
                <DailySummary stats={stats} />
              </div>
            </div>

            {/* Row 3: Live Scene Analysis - Full Width */}
            <div className="w-full">
              <SceneNarration narrations={narrations} />
            </div>
          </>
        )}

        {activeTab === 'live' && (
          <LiveFeedGrid
            cameras={cameras}
            liveFeedData={liveFeedData}
            onCameraStart={handleCameraStart}
            onCameraStop={handleCameraStop}
          />
        )}

        {activeTab === 'alerts' && (
          <div className="max-w-3xl mx-auto">
            <AlertPanel alerts={alerts} onAcknowledge={handleAcknowledgeAlert} />
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

export default App;
