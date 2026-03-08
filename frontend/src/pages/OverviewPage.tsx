import React from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { formatDistanceToNow } from 'date-fns';
import { AlertSeverity } from '../types';

interface OverviewPageProps {
  onNavigate: (page: string) => void;
}

const severityBar: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  WARNING: 'bg-orange-400',
  INFO: 'bg-blue-400',
  SYSTEM: 'bg-gray-400',
};

const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const { cameras, alerts, stats, liveFeedData, handleCameraStart } = useSurveillance();

  const activeCameras = cameras.filter((c) => c.is_active).length;
  const criticalCount = alerts.filter((a) => a.severity === AlertSeverity.CRITICAL && !a.is_read).length;
  const recentAlerts = alerts.slice(0, 8);

  const statTiles = [
    {
      label: 'Events today',
      value: stats?.total_events ?? '—',
      sub: 'Last 24 hours',
      highlight: false,
    },
    {
      label: 'Critical alerts',
      value: stats?.critical_alerts ?? '—',
      sub: criticalCount > 0 ? `${criticalCount} unread` : 'All clear',
      highlight: (stats?.critical_alerts ?? 0) > 0,
    },
    {
      label: 'Cameras active',
      value: `${activeCameras} / ${cameras.length}`,
      sub: cameras.length === 0 ? 'No cameras added' : `${cameras.length} total`,
      highlight: false,
    },
    {
      label: 'Avg response',
      value: stats ? (stats.avg_response_time_seconds === 0 ? '—' : `${Math.round(stats.avg_response_time_seconds)}s`) : '—',
      sub: 'AI processing time',
      highlight: false,
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Overview</h1>
        <p className="text-sm text-gray-500 mt-0.5">System health at a glance</p>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statTiles.map((tile) => (
          <div
            key={tile.label}
            className={`bg-white rounded-lg border p-4 ${
              tile.highlight ? 'border-red-200 bg-red-50' : 'border-gray-200'
            }`}
          >
            <p className="text-xs text-gray-500 mb-1">{tile.label}</p>
            <p className={`text-2xl font-semibold mb-0.5 ${tile.highlight ? 'text-red-600' : 'text-gray-900'}`}>
              {tile.value}
            </p>
            <p className="text-xs text-gray-400">{tile.sub}</p>
          </div>
        ))}
      </div>

      {/* Camera thumbnails + Alert feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Camera thumbnails — 2/3 width */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Camera feeds</h2>
            <button
              onClick={() => onNavigate('cameras')}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              Manage cameras
            </button>
          </div>

          {cameras.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-lg p-10 text-center">
              <div className="inline-flex items-center justify-center w-10 h-10 bg-gray-100 rounded-full mb-3">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500 mb-3">No cameras registered yet.</p>
              <button onClick={() => onNavigate('cameras')} className="btn-primary text-xs">
                Add your first camera
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {cameras.map((camera) => {
                const feed = liveFeedData.get(camera.id);
                return (
                  <div
                    key={camera.id}
                    className="bg-white border border-gray-200 rounded-lg overflow-hidden cursor-pointer hover:border-blue-300 transition-colors"
                    onClick={() => onNavigate('cameras')}
                  >
                    <div className="relative aspect-video bg-gray-100">
                      {camera.is_active && feed?.frame ? (
                        <>
                          <img
                            src={`data:image/jpeg;base64,${feed.frame}`}
                            alt={camera.name}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute top-1.5 right-1.5 flex items-center gap-1 bg-white/90 text-green-700 text-[10px] px-1.5 py-0.5 rounded-full border border-green-200">
                            <span className="w-1 h-1 bg-green-500 rounded-full" />
                            Live
                          </div>
                        </>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="px-3 py-2 flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{camera.name}</p>
                        <p className="text-[10px] text-gray-400 truncate">{camera.location || 'No location'}</p>
                      </div>
                      {!camera.is_active && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCameraStart(camera.id); }}
                          className="text-[10px] px-2 py-0.5 bg-blue-600 text-white rounded ml-2 flex-shrink-0 hover:bg-blue-700 transition-colors"
                        >
                          Start
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent alerts — 1/3 width */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Recent alerts</h2>
            <button
              onClick={() => onNavigate('alerts')}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              View all
            </button>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            {recentAlerts.length === 0 ? (
              <div className="py-10 text-center">
                <svg className="w-7 h-7 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs text-gray-400">No alerts</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {recentAlerts.map((alert) => (
                  <div key={alert.id} className="flex items-start gap-2.5 px-3 py-2.5">
                    <div className={`w-0.5 self-stretch rounded-full flex-shrink-0 mt-0.5 ${severityBar[alert.severity] ?? 'bg-gray-300'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-800 truncate">{alert.title}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {alerts.length > 8 && (
              <div className="px-3 py-2 bg-gray-50 border-t border-gray-100">
                <button onClick={() => onNavigate('alerts')} className="text-xs text-blue-600 hover:text-blue-700 font-medium w-full text-center">
                  +{alerts.length - 8} more alerts
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;
