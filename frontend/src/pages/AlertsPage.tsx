import React, { useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { Alert, AlertSeverity } from '../types';
import { formatDistanceToNow } from 'date-fns';

type Filter = 'all' | 'critical' | 'warning' | 'info';

const severityBar: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  WARNING: 'bg-orange-400',
  INFO: 'bg-blue-400',
  SYSTEM: 'bg-gray-400',
};

const severityBadge: Record<string, string> = {
  CRITICAL: 'badge badge-critical',
  WARNING: 'badge badge-warning',
  INFO: 'badge badge-info',
  SYSTEM: 'badge badge-system',
};

const AlertRow: React.FC<{ alert: Alert; onDismiss: (id: number | string) => void }> = ({ alert, onDismiss }) => {
  const [showEvidence, setShowEvidence] = useState(false);
  const hasEvidence = !!(alert.frame_url || alert.frame_base64);

  return (
    <div className={`flex gap-3 px-5 py-4 hover:bg-gray-50 transition-colors ${alert.is_read ? 'opacity-60' : ''}`}>
      <div className={`w-0.5 flex-shrink-0 self-stretch rounded-full ${severityBar[alert.severity] ?? 'bg-gray-300'}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={severityBadge[alert.severity] ?? 'badge badge-system'}>
              {alert.severity}
            </span>
            {alert.camera_id !== undefined && (
              <span className="text-xs text-gray-400">Camera {alert.camera_id}</span>
            )}
            {alert.significance !== undefined && (
              <span className="text-xs text-gray-400">{alert.significance}% confidence</span>
            )}
          </div>
          <span className="text-xs text-gray-400 flex-shrink-0">
            {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
          </span>
        </div>

        <p className="text-sm font-medium text-gray-800 mb-1">{alert.title}</p>
        <p className="text-xs text-gray-500 whitespace-pre-line mb-2">{alert.message}</p>

        {alert.detected_objects && alert.detected_objects.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {alert.detected_objects.map((obj, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                {obj}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-3">
          {hasEvidence && (
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              {showEvidence ? 'Hide evidence' : 'View evidence'}
            </button>
          )}
          <button
            onClick={() => onDismiss(alert.id)}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Dismiss
          </button>
        </div>

        {showEvidence && hasEvidence && (
          <div className="mt-2 rounded-md overflow-hidden border border-gray-200">
            <img
              src={
                alert.frame_base64
                  ? `data:image/jpeg;base64,${alert.frame_base64}`
                  : `http://localhost:8000${alert.frame_url}`
              }
              alt="Evidence"
              className="w-full max-h-64 object-contain bg-gray-50"
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

const AlertsPage: React.FC = () => {
  const { alerts, handleAcknowledgeAlert, handleClearAllAlerts } = useSurveillance();
  const [filter, setFilter] = useState<Filter>('all');

  const filtered = filter === 'all'
    ? alerts
    : alerts.filter((a) => a.severity.toLowerCase() === filter);

  const counts = {
    all: alerts.length,
    critical: alerts.filter((a) => a.severity === AlertSeverity.CRITICAL).length,
    warning: alerts.filter((a) => a.severity === AlertSeverity.WARNING).length,
    info: alerts.filter((a) => a.severity === AlertSeverity.INFO).length,
  };

  const filterTabs: { id: Filter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'critical', label: 'Critical' },
    { id: 'warning', label: 'Warning' },
    { id: 'info', label: 'Info' },
  ];

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Alerts</h1>
          <p className="text-sm text-gray-500 mt-0.5">{alerts.length} notification{alerts.length !== 1 ? 's' : ''}</p>
        </div>
        {alerts.length > 0 && (
          <button onClick={handleClearAllAlerts} className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
            Clear all
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1">
        {filterTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors ${
              filter === tab.id
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
          >
            {tab.label}
            {counts[tab.id] > 0 && (
              <span className={`ml-1.5 text-xs ${filter === tab.id ? 'text-gray-300' : 'text-gray-400'}`}>
                {counts[tab.id]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 text-center">
            <div className="inline-flex items-center justify-center w-10 h-10 bg-gray-100 rounded-full mb-3">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500">No {filter === 'all' ? '' : filter} alerts</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filtered.map((alert) => (
              <AlertRow key={alert.id} alert={alert} onDismiss={handleAcknowledgeAlert} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertsPage;
