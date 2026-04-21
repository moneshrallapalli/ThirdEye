import React from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';

const AnalyticsPage: React.FC = () => {
  const { stats } = useSurveillance();

  const formatTime = (s: number) => {
    if (!s || s === 0) return '—';
    if (s < 60) return `${Math.round(s)}s`;
    return `${Math.round(s / 60)}m`;
  };

  const tiles = [
    { label: 'Total events', value: stats?.total_events ?? '—', color: 'text-stone-900', highlight: false },
    { label: 'Critical alerts', value: stats?.critical_alerts ?? '—', color: (stats?.critical_alerts ?? 0) > 0 ? 'text-red-600' : 'text-stone-900', highlight: (stats?.critical_alerts ?? 0) > 0 },
    { label: 'Warning alerts', value: stats?.warning_alerts ?? '—', color: (stats?.warning_alerts ?? 0) > 0 ? 'text-orange-600' : 'text-stone-900', highlight: false },
    { label: 'Info alerts', value: stats?.info_alerts ?? '—', color: 'text-stone-900', highlight: false },
    { label: 'Avg response time', value: stats ? formatTime(stats.avg_response_time_seconds) : '—', color: 'text-stone-900', highlight: false },
    { label: 'Active cameras', value: stats?.active_cameras ?? '—', color: (stats?.active_cameras ?? 0) > 0 ? 'text-green-600' : 'text-stone-900', highlight: false },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Analytics</h1>
          <p className="text-sm text-stone-500 mt-0.5">Last 24 hours</p>
        </div>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {tiles.map((tile) => (
          <div
            key={tile.label}
            className={`bg-white rounded-lg border p-5 ${tile.highlight ? 'border-red-200' : 'border-stone-200'}`}
          >
            <p className="text-xs text-stone-500 mb-2">{tile.label}</p>
            <p className={`text-3xl font-semibold ${tile.color}`}>{tile.value}</p>
          </div>
        ))}
      </div>

      {/* Breakdown */}
      {stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Alert breakdown */}
          <div className="bg-white border border-stone-200 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-stone-900 mb-4">Alert breakdown</h2>
            <div className="space-y-3">
              {[
                { label: 'Critical', value: stats.critical_alerts, total: stats.total_events, color: 'bg-red-500' },
                { label: 'Warning', value: stats.warning_alerts, total: stats.total_events, color: 'bg-orange-400' },
                { label: 'Info', value: stats.info_alerts, total: stats.total_events, color: 'bg-stone-400' },
              ].map((row) => {
                const pct = stats.total_events > 0 ? Math.round((row.value / stats.total_events) * 100) : 0;
                return (
                  <div key={row.label}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-stone-600">{row.label}</span>
                      <span className="text-stone-900 font-medium">{row.value} <span className="text-stone-400">({pct}%)</span></span>
                    </div>
                    <div className="w-full bg-stone-100 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${row.color}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Context database */}
          {stats.context_stats && (
            <div className="bg-white border border-stone-200 rounded-lg p-5">
              <h2 className="text-sm font-semibold text-stone-900 mb-4">Context database</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-stone-100">
                  <div>
                    <p className="text-sm font-medium text-stone-800">Stored scenes</p>
                    <p className="text-xs text-stone-400 mt-0.5">Scene descriptions saved to memory</p>
                  </div>
                  <span className="text-2xl font-semibold text-stone-900">{stats.context_stats.total_scenes}</span>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-stone-800">Recognized patterns</p>
                    <p className="text-xs text-stone-400 mt-0.5">Behavioral patterns identified</p>
                  </div>
                  <span className="text-2xl font-semibold text-stone-900">{stats.context_stats.total_patterns}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {!stats && (
        <div className="bg-white border border-stone-200 rounded-lg p-10 text-center">
          <div className="inline-block w-6 h-6 border-2 border-stone-600 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-sm text-stone-400">Loading analytics...</p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;
