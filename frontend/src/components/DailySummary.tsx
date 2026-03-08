import React from 'react';
import { SummaryStats } from '../types';

interface DailySummaryProps {
  stats: SummaryStats | null;
}

const DailySummary: React.FC<DailySummaryProps> = ({ stats }) => {
  const totalEvents = stats?.total_events ?? 0;
  const criticalAlerts = stats?.critical_alerts ?? 0;
  const warningAlerts = stats?.warning_alerts ?? 0;
  const infoAlerts = stats?.info_alerts ?? 0;
  const avgResponseTime = stats?.avg_response_time_seconds ?? 0;
  const activeCameras = stats?.active_cameras ?? 0;

  const formatTime = (s: number) => {
    if (s === 0) return '—';
    if (s < 60) return `${Math.round(s)}s`;
    return `${Math.round(s / 60)}m`;
  };

  const items = [
    { label: 'Events', value: totalEvents, valueColor: 'text-gray-900' },
    { label: 'Critical', value: criticalAlerts, valueColor: criticalAlerts > 0 ? 'text-red-600' : 'text-gray-900' },
    { label: 'Warnings', value: warningAlerts, valueColor: warningAlerts > 0 ? 'text-orange-600' : 'text-gray-900' },
    { label: 'Info', value: infoAlerts, valueColor: 'text-gray-900' },
    { label: 'Avg Response', value: formatTime(avgResponseTime), valueColor: 'text-gray-900' },
    { label: 'Cameras', value: activeCameras, valueColor: activeCameras > 0 ? 'text-green-600' : 'text-gray-900' },
  ];

  return (
    <div className="card h-full">
      <div className="card-header flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Today</h2>
          <p className="text-xs text-gray-400 mt-0.5">Last 24 hours</p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
          <span className="text-xs text-gray-400">Live</span>
        </div>
      </div>

      <div className="card-body">
        <div className="grid grid-cols-2 gap-3">
          {items.map((item) => (
            <div key={item.label} className="bg-gray-50 rounded-lg px-3 py-3 border border-gray-100">
              <p className="text-xs text-gray-500 mb-1">{item.label}</p>
              <p className={`text-2xl font-semibold ${item.valueColor}`}>{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DailySummary;
