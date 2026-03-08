import React from 'react';
import { SummaryStats as Stats } from '../types';

interface SummaryStatsProps {
  stats: Stats | null;
}

const SummaryStats: React.FC<SummaryStatsProps> = ({ stats }) => {
  if (!stats) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="text-base font-semibold text-gray-900">Statistics</h2>
        </div>
        <div className="card-body">
          <p className="text-sm text-gray-400 text-center py-6">Loading...</p>
        </div>
      </div>
    );
  }

  const items = [
    { label: 'Total Events', value: stats.total_events, color: 'text-gray-900' },
    { label: 'Critical Alerts', value: stats.critical_alerts, color: 'text-red-600' },
    { label: 'Warning Alerts', value: stats.warning_alerts, color: 'text-orange-600' },
    { label: 'Info Alerts', value: stats.info_alerts, color: 'text-blue-600' },
    { label: 'Avg Response', value: `${stats.avg_response_time_seconds}s`, color: 'text-gray-900' },
    { label: 'Active Cameras', value: stats.active_cameras, color: 'text-gray-900' },
  ];

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">Statistics</h2>
        <span className="text-xs text-gray-400">Last {stats.period_hours}h</span>
      </div>
      <div className="card-body">
        <div className="grid grid-cols-2 gap-3">
          {items.map((item) => (
            <div key={item.label} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
              <p className="text-xs text-gray-500 mb-1">{item.label}</p>
              <p className={`text-xl font-semibold ${item.color}`}>{item.value}</p>
            </div>
          ))}
        </div>

        {stats.context_stats && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-700 mb-2">Context database</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500 text-xs">Stored scenes</span>
                <span className="text-gray-900 text-xs font-medium">{stats.context_stats.total_scenes}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 text-xs">Patterns</span>
                <span className="text-gray-900 text-xs font-medium">{stats.context_stats.total_patterns}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SummaryStats;
