/**
 * Alert notifications panel
 */
import React from 'react';
import { Alert, AlertSeverity } from '../types';
import { formatDistanceToNow } from 'date-fns';

interface AlertPanelProps {
  alerts: Alert[];
  onAcknowledge: (alertId: number | string) => void;
  onClearAll?: () => void;
}

const AlertPanel: React.FC<AlertPanelProps> = ({ alerts, onAcknowledge, onClearAll }) => {
  const getSeverityStyles = (severity: AlertSeverity): string => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return 'border-l-4 border-red-500 bg-red-500/10';
      case AlertSeverity.WARNING:
        return 'border-l-4 border-orange-500 bg-orange-500/10';
      case AlertSeverity.INFO:
        return 'border-l-4 border-blue-500 bg-blue-500/10';
      case AlertSeverity.SYSTEM:
        return 'border-l-4 border-cyan-500 bg-cyan-500/10';
      default:
        return 'border-l-4 border-gray-500 bg-gray-500/10';
    }
  };

  const getSeverityIcon = (severity: AlertSeverity): string => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return '🚨';
      case AlertSeverity.WARNING:
        return '⚠️';
      case AlertSeverity.INFO:
        return 'ℹ️';
      case AlertSeverity.SYSTEM:
        return '🔧';
      default:
        return '•';
    }
  };

  const getSeverityColor = (severity: AlertSeverity): string => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return 'text-red-400';
      case AlertSeverity.WARNING:
        return 'text-orange-400';
      case AlertSeverity.INFO:
        return 'text-blue-400';
      case AlertSeverity.SYSTEM:
        return 'text-cyan-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-lg font-semibold">Alerts & Notifications</h2>
        {onClearAll && alerts.length > 0 && (
          <button
            onClick={onClearAll}
            className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
          >
            Clear All ({alerts.length})
          </button>
        )}
      </div>
      <div className="card-body p-0">
        <div className="max-h-96 overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>No alerts at this time</p>
            </div>
          ) : (
            <div className="divide-y divide-dark-700">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 transition-all duration-200 hover:bg-dark-700/50 ${getSeverityStyles(alert.severity)} ${
                    alert.is_read ? 'opacity-60' : ''
                  }`}
                >
                  <div className="flex flex-col gap-3">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl flex-shrink-0">
                        {getSeverityIcon(alert.severity)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`badge badge-${alert.severity.toLowerCase()}`}>
                            {alert.severity}
                          </span>
                          {alert.camera_id !== undefined && (
                            <span className="text-xs text-gray-400">
                              Camera {alert.camera_id}
                            </span>
                          )}
                          {alert.significance !== undefined && (
                            <span className="text-xs px-2 py-0.5 bg-blue-600/30 text-blue-300 rounded">
                              {alert.significance}% confidence
                            </span>
                          )}
                        </div>
                        <h3 className="font-semibold text-gray-100 mb-1">
                          {alert.title}
                        </h3>
                        <div className="text-sm text-gray-300 mb-2 whitespace-pre-line">
                          {alert.message}
                        </div>
                        
                        {/* Display detected objects as tags */}
                        {alert.detected_objects && alert.detected_objects.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-2">
                            {alert.detected_objects.map((obj, idx) => (
                              <span
                                key={idx}
                                className="text-xs px-2 py-0.5 bg-green-600/20 text-green-300 rounded-full border border-green-600/30"
                              >
                                {obj}
                              </span>
                            ))}
                          </div>
                        )}
                        
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-400">
                            {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                          </span>
                        <button
                          onClick={() => onAcknowledge(alert.id)}
                          className="text-xs px-2 py-1 bg-primary-600 hover:bg-primary-700 text-white rounded transition-colors"
                        >
                          Acknowledge
                        </button>
                        </div>
                      </div>
                    </div>
                    
                    {/* Supporting Image */}
                    {(alert.frame_url || alert.frame_base64) && (
                      <div className="ml-11 mt-2">
                        <div className="rounded-lg overflow-hidden border border-dark-600 bg-dark-900">
                          <img
                            src={
                              alert.frame_base64
                                ? `data:image/jpeg;base64,${alert.frame_base64}`
                                : `http://localhost:8000${alert.frame_url}`
                            }
                            alt="Event Frame"
                            className="w-full h-auto max-h-64 object-contain"
                            onError={(e) => {
                              console.error('Image load error:', e);
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                          <div className="px-2 py-1 bg-dark-800 text-xs text-gray-400 text-center">
                            📷 Supporting Evidence
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlertPanel;
