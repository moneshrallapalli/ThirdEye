import React, { useEffect, useRef, useState } from 'react';
import { Camera } from '../types';
import { cameraApi } from '../services/api';
import { utcToDate } from '../utils/time';

interface AskAIDrawerProps {
  camera: Camera | null;
  liveFrame?: string;
  onClose: () => void;
}

type Msg =
  | { role: 'user'; text: string; mode: 'live' | 'history'; ts: string }
  | {
      role: 'assistant';
      text: string;
      mode: 'live' | 'history';
      ts: string;
      eventsAnalysed?: number;
      timeRange?: { start: string; end: string };
      frames?: { event_id: number; timestamp: string; frame_url: string | null; scene_description: string }[];
      error?: boolean;
    };

const SESSIONS: Map<number, { live: Msg[]; history: Msg[] }> = new Map();

const AskAIDrawer: React.FC<AskAIDrawerProps> = ({ camera, liveFrame, onClose }) => {
  const [mode, setMode] = useState<'live' | 'history'>('live');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [, forceRefresh] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const session = camera ? SESSIONS.get(camera.id) ?? { live: [], history: [] } : { live: [], history: [] };
  const messages = mode === 'live' ? session.live : session.history;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, mode, loading]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!camera) return null;

  const pushMessage = (m: Msg) => {
    const existing = SESSIONS.get(camera.id) ?? { live: [], history: [] };
    if (m.mode === 'live') existing.live = [...existing.live, m];
    else existing.history = [...existing.history, m];
    SESSIONS.set(camera.id, existing);
    forceRefresh((n) => n + 1);
  };

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    const ts = new Date().toLocaleTimeString();
    pushMessage({ role: 'user', text: q, mode, ts });
    setInput('');
    setLoading(true);
    try {
      if (mode === 'live') {
        const result = await cameraApi.query(camera.id, q);
        pushMessage({ role: 'assistant', text: result.answer, mode: 'live', ts: new Date().toLocaleTimeString() });
      } else {
        const result = await cameraApi.history(camera.id, q);
        pushMessage({
          role: 'assistant',
          text: result.answer,
          mode: 'history',
          ts: new Date().toLocaleTimeString(),
          eventsAnalysed: result.events_analysed,
          timeRange: result.time_range,
          frames: result.relevant_frames,
        });
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail || 'Request failed';
      pushMessage({ role: 'assistant', text: detail, mode, ts: new Date().toLocaleTimeString(), error: true });
    } finally {
      setLoading(false);
    }
  };

  const clearSession = () => {
    const existing = SESSIONS.get(camera.id) ?? { live: [], history: [] };
    if (mode === 'live') existing.live = [];
    else existing.history = [];
    SESSIONS.set(camera.id, existing);
    forceRefresh((n) => n + 1);
  };

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      {/* Backdrop */}
      <div className="flex-1 bg-black/20" />
      {/* Drawer */}
      <aside
        className="w-full max-w-md flex flex-col shadow-2xl"
        style={{ background: 'var(--bg-page)', borderLeft: '1px solid var(--border)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 flex items-start justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3 min-w-0">
            {/* Thumb */}
            <div className="w-14 h-9 rounded overflow-hidden flex-shrink-0" style={{ background: 'var(--bg-surface-subtle)' }}>
              {camera.is_active && liveFrame ? (
                <img src={`data:image/jpeg;base64,${liveFrame}`} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-stone-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-stone-900 truncate">Ask {camera.name}</p>
              <p className="text-xs text-stone-500 truncate">
                {camera.location || 'No location'} ·{' '}
                <span className={camera.is_active ? 'text-green-600' : 'text-stone-400'}>
                  {camera.is_active ? 'Active' : 'Offline'}
                </span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-stone-400 hover:text-stone-900 rounded transition-colors flex-shrink-0 ml-2"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Mode tabs */}
        <div className="px-5 pt-3 flex items-center justify-between">
          <div className="inline-flex rounded-md p-0.5" style={{ background: 'var(--bg-surface-subtle)' }}>
            <button
              onClick={() => setMode('live')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mode === 'live' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-800'
              }`}
            >
              Live
            </button>
            <button
              onClick={() => setMode('history')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mode === 'history' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-800'
              }`}
            >
              History
            </button>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearSession}
              className="text-xs text-stone-400 hover:text-stone-700 transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {/* Conversation */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-xs">
                <div
                  className="inline-flex items-center justify-center w-10 h-10 rounded-full mb-3"
                  style={{ background: 'var(--bg-surface-subtle)' }}
                >
                  <svg className="w-5 h-5 text-stone-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d={
                        mode === 'live'
                          ? 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z'
                          : 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z'
                      }
                    />
                  </svg>
                </div>
                <p className="text-sm font-medium text-stone-900 mb-1">
                  {mode === 'live' ? 'Ask about the live feed' : 'Search past footage'}
                </p>
                <p className="text-xs text-stone-500 leading-relaxed">
                  {mode === 'live'
                    ? camera.is_active
                      ? 'Ask a question about what this camera sees right now.'
                      : 'Start the camera first to query the live feed.'
                    : 'Describe an event or object to find when it occurred in recorded footage.'}
                </p>
              </div>
            </div>
          ) : (
            messages.map((m, i) =>
              m.role === 'user' ? (
                <div key={i} className="flex justify-end">
                  <div
                    className="max-w-[85%] rounded-lg px-3 py-2 text-sm"
                    style={{ background: 'var(--btn-primary-bg)', color: 'var(--btn-primary-text)' }}
                  >
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex justify-start">
                  <div
                    className={`max-w-[92%] rounded-lg px-3 py-2.5 text-sm leading-relaxed whitespace-pre-line ${
                      m.error ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-white border border-stone-200 text-stone-800'
                    }`}
                  >
                    {m.text}
                    {m.mode === 'history' && m.eventsAnalysed !== undefined && m.eventsAnalysed > 0 && (
                      <p className="text-[10px] text-stone-400 mt-1.5">
                        Analysed {m.eventsAnalysed} events
                        {m.timeRange?.start && (
                          <>
                            {' · '}
                            {new Date(m.timeRange.start).toLocaleDateString()} → {new Date(m.timeRange.end).toLocaleDateString()}
                          </>
                        )}
                      </p>
                    )}
                    {m.frames && m.frames.filter((f) => f.frame_url).length > 0 && (
                      <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1">
                        {m.frames
                          .filter((f) => f.frame_url)
                          .map((f) => (
                            <div key={f.event_id} className="flex-shrink-0 w-24">
                              <img
                                src={`http://localhost:8000${f.frame_url}`}
                                alt={f.scene_description}
                                className="w-24 h-16 object-cover rounded border border-stone-200"
                              />
                              <p className="text-[9px] text-stone-400 mt-0.5 truncate">
                                {utcToDate(f.timestamp).toLocaleTimeString()}
                              </p>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
              ),
            )
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-stone-200 rounded-lg px-3 py-2.5 text-sm flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-stone-400 animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-stone-400 animate-pulse" style={{ animationDelay: '0.15s' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-stone-400 animate-pulse" style={{ animationDelay: '0.3s' }} />
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="px-5 py-4" style={{ borderTop: '1px solid var(--border)' }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                mode === 'live'
                  ? camera.is_active
                    ? 'Ask about the live feed...'
                    : 'Camera offline'
                  : 'Search past footage...'
              }
              disabled={loading || (mode === 'live' && !camera.is_active)}
              className="input flex-1 text-sm"
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || (mode === 'live' && !camera.is_active)}
              className="btn-primary disabled:opacity-40"
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              )}
            </button>
          </form>
        </div>
      </aside>
    </div>
  );
};

export default AskAIDrawer;
