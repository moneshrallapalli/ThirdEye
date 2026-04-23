import React, { useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { Alert, AlertSeverity } from '../types';
import { formatDistanceToNow, format } from 'date-fns';
import { utcToDate } from '../utils/time';

type Filter = 'all' | 'critical' | 'warning' | 'info';

const severityBar: Record<string, string> = {
  CRITICAL: 'bg-red-400',
  WARNING: 'bg-orange-400',
  INFO: 'bg-stone-400',
  SYSTEM: 'bg-stone-400',
};

const severityBadge: Record<string, string> = {
  CRITICAL: 'badge badge-critical',
  WARNING: 'badge badge-warning',
  INFO: 'badge badge-info',
  SYSTEM: 'badge badge-system',
};

const evidenceSrc = (alert: Alert): string | null => {
  if (alert.frame_base64) return `data:image/jpeg;base64,${alert.frame_base64}`;
  if (alert.frame_url) return `http://localhost:8000${alert.frame_url}`;
  return null;
};

const ReasonBlock: React.FC<{ label: string; value?: string | null }> = ({ label, value }) => {
  if (!value) return null;
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-stone-400 font-medium mb-1">{label}</p>
      <p className="text-sm text-stone-700 whitespace-pre-line leading-relaxed">{value}</p>
    </div>
  );
};

const AlertRow: React.FC<{ alert: Alert; onDismiss: (id: number | string) => void }> = ({ alert, onDismiss }) => {
  const [expanded, setExpanded] = useState(false);
  const evidence = evidenceSrc(alert);

  const confidence = alert.query_confidence ?? alert.significance;
  const ts = utcToDate(alert.timestamp);

  return (
    <div className={`${alert.is_read ? 'opacity-70' : ''}`}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left flex gap-3 px-5 py-4 hover:bg-stone-50 transition-colors"
      >
        <div className={`w-0.5 flex-shrink-0 self-stretch rounded-full ${severityBar[alert.severity] ?? 'bg-stone-300'}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={severityBadge[alert.severity] ?? 'badge badge-system'}>
                {alert.severity}
              </span>
              {alert.camera_id !== undefined && alert.camera_id !== null && (
                <span className="text-xs text-stone-400">Camera {alert.camera_id}</span>
              )}
              {confidence !== undefined && confidence !== null && (
                <span className="text-xs text-stone-400">{confidence}% confidence</span>
              )}
              {alert.user_query && (
                <span className="text-[11px] px-1.5 py-0.5 bg-stone-900 text-stone-50 rounded">
                  trigger: {alert.user_query}
                </span>
              )}
            </div>
            <span className="text-xs text-stone-400 flex-shrink-0">
              {formatDistanceToNow(ts, { addSuffix: true })}
            </span>
          </div>

          <p className="text-sm font-medium text-stone-800 mb-1">{alert.title}</p>
          <p className="text-xs text-stone-500 whitespace-pre-line">{alert.message}</p>

          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="text-stone-500 font-medium">
              {expanded ? 'Hide reasoning' : 'Show reasoning & proof'}
            </span>
            <span className="text-stone-300">•</span>
            <span
              role="button"
              onClick={(e) => { e.stopPropagation(); onDismiss(alert.id); }}
              className="text-stone-400 hover:text-stone-600 transition-colors cursor-pointer"
            >
              Dismiss
            </span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 pt-1 bg-stone-50/60 border-t border-stone-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Left: reasoning */}
            <div className="space-y-4">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-stone-400 font-medium mb-1">
                  Why this was alerted
                </p>
                <p className="text-xs text-stone-500">
                  The model raised this because your active monitoring trigger
                  {alert.user_query ? ` "${alert.user_query}"` : ''} matched the live scene
                  {confidence !== undefined && confidence !== null ? ` with ${confidence}% confidence` : ''}.
                  Details below are produced directly from the frame shown as proof.
                </p>
              </div>

              <ReasonBlock label="Your trigger" value={alert.user_query} />
              <ReasonBlock label="Match evidence" value={alert.query_details} />
              <ReasonBlock label="Model reasoning" value={alert.claude_reasoning} />
              <ReasonBlock label="Scene" value={alert.scene_description} />
              <ReasonBlock label="Activity" value={alert.activity} />

              {!alert.query_details && !alert.claude_reasoning && !alert.scene_description && alert.reasoning && (
                <ReasonBlock label="Reasoning" value={alert.reasoning} />
              )}

              {alert.detected_objects && alert.detected_objects.length > 0 && (
                <div>
                  <p className="text-[11px] uppercase tracking-wider text-stone-400 font-medium mb-1">
                    Detected objects
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {alert.detected_objects.map((obj, i) => (
                      <span key={i} className="text-[11px] px-1.5 py-0.5 bg-white border border-stone-200 text-stone-600 rounded">
                        {obj}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2 text-[11px] text-stone-400">
                Recorded {format(ts, 'PP p')}
              </div>
            </div>

            {/* Right: supporting evidence frame */}
            <div>
              <p className="text-[11px] uppercase tracking-wider text-stone-400 font-medium mb-1">
                Supporting evidence (frame at trigger time)
              </p>
              {evidence ? (
                <div className="rounded-md overflow-hidden border border-stone-200 bg-white">
                  <img
                    src={evidence}
                    alt="Evidence frame"
                    className="w-full max-h-80 object-contain bg-stone-50"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <div className="px-2 py-1 text-[11px] text-stone-400 text-center bg-stone-50 border-t border-stone-100">
                    Frame analysed by the model
                  </div>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-stone-200 px-4 py-8 text-center text-xs text-stone-400">
                  No frame was captured for this alert.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const AlertsPage: React.FC<{ initialFilter?: string }> = ({ initialFilter }) => {
  const { alerts, handleAcknowledgeAlert, handleClearAllAlerts } = useSurveillance();
  const [filter, setFilter] = useState<Filter>((initialFilter as Filter) ?? 'all');

  // Only show alerts that were actually produced by a user trigger.
  // The backend now only persists those, but WS may still deliver legacy
  // entries; this keeps the page strictly user-initiated.
  const userTriggered = alerts.filter(
    (a) => !!(a.user_query || a.alert_type === 'trigger_match')
  );

  const filtered = filter === 'all'
    ? userTriggered
    : userTriggered.filter((a) => a.severity.toLowerCase() === filter);

  const counts = {
    all: userTriggered.length,
    critical: userTriggered.filter((a) => a.severity === AlertSeverity.CRITICAL).length,
    warning: userTriggered.filter((a) => a.severity === AlertSeverity.WARNING).length,
    info: userTriggered.filter((a) => a.severity === AlertSeverity.INFO).length,
  };

  const filterTabs: { id: Filter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'critical', label: 'Critical' },
    { id: 'warning', label: 'Warning' },
    { id: 'info', label: 'Info' },
  ];

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Alerts</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            {userTriggered.length} trigger match{userTriggered.length !== 1 ? 'es' : ''} from your monitoring tasks
          </p>
        </div>
        {userTriggered.length > 0 && (
          <button onClick={handleClearAllAlerts} className="text-sm text-stone-400 hover:text-stone-600 transition-colors">
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
                ? 'bg-stone-900 text-white'
                : 'text-stone-500 hover:text-stone-700 hover:bg-stone-100'
            }`}
          >
            {tab.label}
            <span className={`ml-1.5 text-xs ${filter === tab.id ? 'text-stone-300' : 'text-stone-400'}`}>
              {counts[tab.id]}
            </span>
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="bg-white border border-stone-200 rounded-lg overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 text-center">
            <div className="inline-flex items-center justify-center w-10 h-10 bg-stone-100 rounded-full mb-3">
              <svg className="w-5 h-5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-stone-500">
              No {filter === 'all' ? '' : filter} alerts. Set up a monitoring task on a camera and alerts will appear here when it fires.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-stone-100">
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
