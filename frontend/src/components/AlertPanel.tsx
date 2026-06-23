import React from 'react';
import { Alert, AlertSeverity } from '../types';
import { formatDistanceToNow } from 'date-fns';
import { utcToDate } from '../utils/time';

interface AlertPanelProps {
  alerts: Alert[];
  onAcknowledge: (alertId: number | string) => void;
  onClearAll?: () => void;
}

const severityConfig: Record<string, { bar: string; badge: string; label: string }> = {
  CRITICAL: { bar: 'bg-red-500', badge: 'badge-critical', label: 'Critical' },
  WARNING:  { bar: 'bg-orange-400', badge: 'badge-warning', label: 'Warning' },
  INFO:     { bar: 'bg-stone-400', badge: 'badge-info', label: 'Info' },
  SYSTEM:   { bar: 'bg-stone-400', badge: 'badge-system', label: 'System' },
};

const AlertPanel: React.FC<AlertPanelProps> = ({ alerts, onAcknowledge, onClearAll }) => {
  return (
    <div className="card flex flex-col h-full">
      <div className="card-header flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-stone-900">Alerts</h2>
          <p className="text-xs text-stone-400 mt-0.5">{alerts.length} notification{alerts.length !== 1 ? 's' : ''}</p>
        </div>
        {onClearAll && alerts.length > 0 && (
          <button
            onClick={onClearAll}
            className="text-xs text-stone-400 hover:text-stone-600 transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="overflow-y-auto" style={{ maxHeight: '480px' }}>
        {alerts.length === 0 ? (
          <div className="py-12 text-center">
            <div className="inline-flex items-center justify-center w-10 h-10 bg-stone-100 rounded-full mb-3">
              <svg className="w-5 h-5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-stone-500">No alerts</p>
          </div>
        ) : (
          <div className="divide-y divide-stone-100">
            {alerts.map((alert) => {
              const cfg = severityConfig[alert.severity] ?? severityConfig.SYSTEM;
              return (
                <div
                  key={alert.id}
                  className={`flex gap-3 px-4 py-3 hover:bg-stone-50 transition-colors ${alert.is_read ? 'opacity-60' : ''}`}
                >
                  {/* Severity bar */}
                  <div className={`w-0.5 flex-shrink-0 rounded-full ${cfg.bar}`} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`badge ${cfg.badge}`}>{cfg.label}</span>
                      {alert.camera_id !== undefined && (
                        <span className="text-xs text-stone-400">Camera {alert.camera_id}</span>
                      )}
                      {alert.significance !== undefined && (
                        <span className="text-xs text-stone-400">{alert.significance}%</span>
                      )}
                    </div>

                    <p className="text-sm font-medium text-stone-800 mb-0.5">{alert.title}</p>
                    <p className="text-xs text-stone-500 whitespace-pre-line mb-2">{alert.message}</p>

                    {alert.detected_objects && alert.detected_objects.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {alert.detected_objects.map((obj, idx) => (
                          <span key={idx} className="text-xs px-1.5 py-0.5 bg-stone-100 text-stone-600 rounded">
                            {obj}
                          </span>
                        ))}
                      </div>
                    )}

                    {(alert.frame_url || alert.frame_base64) && (
                      <div className="mb-2 rounded-md overflow-hidden border border-stone-200">
                        <img
                          src={
                            alert.frame_base64
                              ? `data:image/jpeg;base64,${alert.frame_base64}`
                              : `http://localhost:8000${alert.frame_url}`
                          }
                          alt="Event frame"
                          className="w-full h-auto max-h-48 object-contain bg-stone-50"
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                        <div className="px-2 py-1 text-xs text-stone-400 text-center bg-stone-50 border-t border-stone-100">
                          Supporting evidence
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-stone-400">
                        {formatDistanceToNow(utcToDate(alert.timestamp), { addSuffix: true })}
                      </span>
                      <button
                        onClick={() => onAcknowledge(alert.id)}
                        className="text-xs text-stone-600 hover:text-stone-800 font-medium transition-colors"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertPanel;
