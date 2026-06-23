import React from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { formatDistanceToNow } from 'date-fns';
import { AlertSeverity } from '../types';
import { utcToDate } from '../utils/time';

interface OverviewPageProps {
  onNavigate: (page: string) => void;
}

const severityBar: Record<string, string> = {
  CRITICAL: 'bg-red-400',
  WARNING: 'bg-orange-400',
  INFO: 'bg-stone-400',
  SYSTEM: 'bg-stone-400',
};

const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const { cameras, alerts, stats, liveFeedData, handleCameraStart } = useSurveillance();

  const activeCameras = cameras.filter((c) => c.is_active).length;
  const criticalCount = alerts.filter((a) => a.severity === AlertSeverity.CRITICAL && !a.is_read).length;
  const recentAlerts = alerts.slice(0, 8);

  const totalAlerts = (stats?.critical_alerts ?? 0) + (stats?.warning_alerts ?? 0) + (stats?.info_alerts ?? 0);

  const statTiles = [
    {
      label: 'Total alerts',
      value: stats ? totalAlerts : '—',
      sub: 'Last 24 hours',
      highlight: false,
      onClick: () => onNavigate('alerts'),
    },
    {
      label: 'Critical alerts',
      value: stats?.critical_alerts ?? '—',
      sub: criticalCount > 0 ? `${criticalCount} unread` : 'All clear',
      highlight: (stats?.critical_alerts ?? 0) > 0,
      onClick: () => onNavigate('alerts:critical'),
    },
    {
      label: 'Cameras active',
      value: `${activeCameras} / ${cameras.length}`,
      sub: cameras.length === 0 ? 'No cameras added' : `${cameras.length} total`,
      highlight: false,
      onClick: () => onNavigate('cameras'),
    },
    {
      label: 'Avg response',
      value: stats ? (stats.avg_response_time_seconds === 0 ? '—' : `${Math.round(stats.avg_response_time_seconds)}s`) : '—',
      sub: 'Time to acknowledge',
      highlight: false,
      onClick: undefined,
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Page title */}
      <div>
        <h1 className="font-display text-xl font-semibold text-stone-900">Overview</h1>
        <p className="text-sm text-stone-500 mt-0.5">System health at a glance</p>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statTiles.map((tile) => {
          const base = `bg-white rounded-lg border p-4 text-left w-full transition-colors ${
            tile.highlight ? 'border-red-200 bg-red-50' : 'border-stone-200'
          } ${tile.onClick ? 'cursor-pointer hover:border-stone-300 hover:bg-stone-50' : ''}`;
          const inner = (
            <>
              <p className="text-xs text-stone-500 mb-1">{tile.label}</p>
              <p className={`text-2xl font-semibold mb-0.5 ${tile.highlight ? 'text-red-600' : 'text-stone-900'}`}>
                {tile.value}
              </p>
              <p className="text-xs text-stone-400">{tile.sub}</p>
            </>
          );
          return tile.onClick ? (
            <button key={tile.label} className={base} onClick={tile.onClick}>{inner}</button>
          ) : (
            <div key={tile.label} className={base}>{inner}</div>
          );
        })}
      </div>

      {/* Camera thumbnails + Alert feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Camera thumbnails — 2/3 width */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-stone-700">Camera feeds</h2>
            <button
              onClick={() => onNavigate('cameras')}
              className="text-xs text-stone-700 hover:text-stone-900 font-medium"
            >
              Manage cameras
            </button>
          </div>

          {cameras.length === 0 ? (
            <div className="bg-white border border-stone-200 rounded-lg p-10 text-center">
              <div className="inline-flex items-center justify-center w-10 h-10 bg-stone-100 rounded-full mb-3">
                <svg className="w-5 h-5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-sm text-stone-500 mb-3">No cameras registered yet.</p>
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
                    className="bg-white border border-stone-200 rounded-lg overflow-hidden cursor-pointer hover:border-stone-300 transition-colors"
                    onClick={() => onNavigate('cameras')}
                  >
                    <div className="relative aspect-video bg-stone-100">
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
                          <svg className="w-8 h-8 text-stone-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="px-3 py-2 flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-stone-800 truncate">{camera.name}</p>
                        <p className="text-[10px] text-stone-400 truncate">{camera.location || 'No location'}</p>
                      </div>
                      {!camera.is_active && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCameraStart(camera.id); }}
                          className="text-[10px] px-2 py-0.5 bg-stone-900 text-white rounded ml-2 flex-shrink-0 hover:bg-stone-800 transition-colors"
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
            <h2 className="text-sm font-semibold text-stone-700">Recent alerts</h2>
            <button
              onClick={() => onNavigate('alerts')}
              className="text-xs text-stone-700 hover:text-stone-900 font-medium"
            >
              View all
            </button>
          </div>

          <div className="bg-white border border-stone-200 rounded-lg overflow-hidden">
            {recentAlerts.length === 0 ? (
              <div className="py-10 text-center">
                <svg className="w-7 h-7 mx-auto text-stone-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs text-stone-400">No alerts</p>
              </div>
            ) : (
              <div className="divide-y divide-stone-100">
                {recentAlerts.map((alert) => (
                  <button
                    key={alert.id}
                    className="w-full flex items-start gap-2.5 px-3 py-2.5 hover:bg-stone-50 transition-colors text-left"
                    onClick={() => onNavigate(`alerts:${alert.severity.toLowerCase()}`)}
                  >
                    <div className={`w-0.5 self-stretch rounded-full flex-shrink-0 mt-0.5 ${severityBar[alert.severity] ?? 'bg-stone-300'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-stone-800 truncate">{alert.title}</p>
                      <p className="text-[10px] text-stone-400 mt-0.5">
                        {formatDistanceToNow(utcToDate(alert.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {alerts.length > 8 && (
              <div className="px-3 py-2 bg-stone-50 border-t border-stone-100">
                <button onClick={() => onNavigate('alerts')} className="text-xs text-stone-700 hover:text-stone-900 font-medium w-full text-center">
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
