import React, { useEffect, useState } from 'react';
import { Camera, CameraTask } from '../types';
import { taskApi, cameraApi } from '../services/api';
import { utcToDate } from '../utils/time';

interface LiveFeedGridProps {
  cameras: Camera[];
  liveFeedData: Map<number, { frame: string; timestamp: string }>;
  cols?: 1 | 2 | 3;
  onCameraStart: (cameraId: number) => void;
  onCameraStop: (cameraId: number) => void;
  onCameraAdd: (name: string, location: string, streamUrl: string, tasks?: { command: string; task_type: string; priority?: number }[]) => Promise<void>;
  onCameraDelete: (cameraId: number) => Promise<void>;
  onSelectCamera?: (cameraId: number) => void;
}

const colsClass: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
};

const PRESET_LOCATIONS = [
  'Kitchen', 'Garden', 'Entrance', 'Front Door', 'Back Door',
  'Parking', 'Garage', 'Living Room', 'Bedroom', 'Office',
  'Warehouse', 'Pool', 'Baby Room', 'Nursery', 'Driveway',
  'Backyard', 'Shop', 'Store',
];

const LiveFeedGrid: React.FC<LiveFeedGridProps> = ({
  cameras,
  liveFeedData,
  cols = 2,
  onCameraStart,
  onCameraStop,
  onCameraAdd,
  onCameraDelete,
  onSelectCamera,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({ name: '', location: '', streamUrl: '' });
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [presets, setPresets] = useState<Record<string, { command: string; task_type: string }[]>>({});
  const [matchedPreset, setMatchedPreset] = useState<{ command: string; task_type: string }[]>([]);
  const [selectedPresets, setSelectedPresets] = useState<Set<number>>(new Set());
  const [customTasks, setCustomTasks] = useState<string[]>([]);
  const [customTaskInput, setCustomTaskInput] = useState('');
  const [taskCounts, setTaskCounts] = useState<Record<number, number>>({});
  const [promptInputs, setPromptInputs] = useState<Record<number, string>>({});
  const [promptLoading, setPromptLoading] = useState<Record<number, boolean>>({});
  const [promptAnswers, setPromptAnswers] = useState<Record<number, { question: string; answer: string; timestamp: string } | null>>({});
  const [promptMode, setPromptMode] = useState<Record<number, 'live' | 'history'>>({});
  const [historyInputs, setHistoryInputs] = useState<Record<number, string>>({});
  const [historyLoading, setHistoryLoading] = useState<Record<number, boolean>>({});
  const [historyResults, setHistoryResults] = useState<Record<number, {
    question: string;
    answer: string;
    events_analysed: number;
    time_range: { start: string; end: string };
    relevant_frames: { event_id: number; timestamp: string; scene_description: string; significance: number; frame_url: string | null }[];
  } | null>>({});

  // Load presets on mount
  useEffect(() => {
    taskApi.getPresets().then(setPresets).catch(() => {});
  }, []);

  // Load task counts for all cameras
  useEffect(() => {
    const loadCounts = async () => {
      const counts: Record<number, number> = {};
      await Promise.all(
        cameras.map(async (cam) => {
          try {
            const tasks = await taskApi.getForCamera(cam.id);
            counts[cam.id] = tasks.filter((t) => t.is_active).length;
          } catch {
            counts[cam.id] = 0;
          }
        })
      );
      setTaskCounts(counts);
    };
    if (cameras.length > 0) loadCounts();
  }, [cameras]);

  // Match location to presets as user types
  useEffect(() => {
    const loc = addForm.location.trim().toLowerCase();
    if (!loc || Object.keys(presets).length === 0) {
      setMatchedPreset([]);
      setSelectedPresets(new Set());
      return;
    }
    const exact = presets[loc];
    if (exact) { setMatchedPreset(exact); setSelectedPresets(new Set()); return; }
    for (const [key, tasks] of Object.entries(presets)) {
      if (key.includes(loc) || loc.includes(key)) {
        setMatchedPreset(tasks);
        setSelectedPresets(new Set());
        return;
      }
    }
    setMatchedPreset([]);
    setSelectedPresets(new Set());
  }, [addForm.location, presets]);

  const handleAdd = async () => {
    if (!addForm.name.trim() || !addForm.streamUrl.trim()) {
      setAddError('Camera name and video source are required.');
      return;
    }
    setAdding(true);
    setAddError('');
    try {
      // Collect selected preset tasks + custom tasks
      const tasks: { command: string; task_type: string; priority?: number }[] = [];
      matchedPreset.forEach((preset, i) => {
        if (selectedPresets.has(i)) {
          tasks.push({ command: preset.command, task_type: preset.task_type, priority: 2 });
        }
      });
      customTasks.forEach((cmd) => {
        tasks.push({ command: cmd, task_type: 'custom', priority: 1 });
      });

      await onCameraAdd(addForm.name.trim(), addForm.location.trim(), addForm.streamUrl.trim(), tasks);
      setAddForm({ name: '', location: '', streamUrl: '' });
      setSelectedPresets(new Set());
      setCustomTasks([]);
      setCustomTaskInput('');
      setShowAddModal(false);
    } catch (e: any) {
      setAddError(e?.response?.data?.detail || 'Failed to add camera.');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (cameraId: number) => {
    if (!window.confirm('Delete this camera? This action cannot be undone.')) return;
    setDeletingId(cameraId);
    try {
      await onCameraDelete(cameraId);
    } finally {
      setDeletingId(null);
    }
  };

  const handlePrompt = async (cameraId: number) => {
    const question = (promptInputs[cameraId] || '').trim();
    if (!question) return;
    setPromptLoading((p) => ({ ...p, [cameraId]: true }));
    try {
      const result = await cameraApi.query(cameraId, question);
      setPromptAnswers((p) => ({
        ...p,
        [cameraId]: { question, answer: result.answer, timestamp: new Date().toLocaleTimeString() },
      }));
      setPromptInputs((p) => ({ ...p, [cameraId]: '' }));
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to get answer';
      setPromptAnswers((p) => ({
        ...p,
        [cameraId]: { question, answer: `Error: ${msg}`, timestamp: new Date().toLocaleTimeString() },
      }));
    } finally {
      setPromptLoading((p) => ({ ...p, [cameraId]: false }));
    }
  };

  const handleHistory = async (cameraId: number) => {
    const question = (historyInputs[cameraId] || '').trim();
    if (!question) return;
    setHistoryLoading((p) => ({ ...p, [cameraId]: true }));
    try {
      const result = await cameraApi.history(cameraId, question);
      setHistoryResults((p) => ({ ...p, [cameraId]: result }));
      setHistoryInputs((p) => ({ ...p, [cameraId]: '' }));
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to query history';
      setHistoryResults((p) => ({
        ...p,
        [cameraId]: {
          question,
          answer: `Error: ${msg}`,
          events_analysed: 0,
          time_range: { start: '', end: '' },
          relevant_frames: [],
        },
      }));
    } finally {
      setHistoryLoading((p) => ({ ...p, [cameraId]: false }));
    }
  };

  return (
    <div className="space-y-4">
      {/* Add camera button row */}
      <div className="flex justify-end">
        <button
          onClick={() => { setShowAddModal(true); setAddError(''); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-stone-900 hover:bg-stone-800 text-white text-sm font-medium rounded-md transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add camera
        </button>
      </div>

      {/* Empty state */}
      {cameras.length === 0 && (
        <div className="bg-white border border-stone-200 rounded-lg py-20 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-stone-100 rounded-full mb-4">
            <svg className="w-6 h-6 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-stone-900 mb-1">No cameras registered</p>
          <p className="text-sm text-stone-400 mb-4">Add a camera to start monitoring.</p>
          <button onClick={() => setShowAddModal(true)} className="btn-primary">
            Add your first camera
          </button>
        </div>
      )}

      {/* Camera grid */}
      {cameras.length > 0 && (
        <div className={`grid ${colsClass[cols]} gap-4`}>
          {cameras.map((camera) => {
            const feedData = liveFeedData.get(camera.id);
            const isDeleting = deletingId === camera.id;
            const activeTaskCount = taskCounts[camera.id] ?? 0;

            return (
              <div key={camera.id} className="bg-white border border-stone-200 rounded-lg overflow-hidden">
                {/* Card header */}
                <div className="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
                  <div className="min-w-0">
                    <h3 className="text-sm font-medium text-stone-900 truncate">{camera.name}</h3>
                    <p className="text-xs text-stone-400 truncate">{camera.location || 'No location'}</p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                    {camera.is_active ? (
                      <>
                        <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                          <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                          Active
                        </span>
                        <button
                          onClick={() => onCameraStop(camera.id)}
                          className="text-xs px-2.5 py-1 bg-white border border-stone-200 hover:bg-stone-50 text-stone-600 rounded-md transition-colors"
                        >
                          Stop
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => onCameraStart(camera.id)}
                        className="text-xs px-2.5 py-1 bg-stone-900 hover:bg-stone-800 text-white rounded-md transition-colors"
                      >
                        Start AI
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(camera.id)}
                      disabled={isDeleting}
                      className="p-1 text-stone-400 hover:text-red-500 rounded transition-colors"
                      title="Delete camera"
                    >
                      {isDeleting ? (
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Feed area */}
                <div className="relative aspect-video bg-stone-100">
                  {camera.is_active && feedData?.frame ? (
                    <>
                      <img
                        src={`data:image/jpeg;base64,${feedData.frame}`}
                        alt={`Feed from ${camera.name}`}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute top-2 right-2 flex items-center gap-1 bg-white/90 text-green-700 text-[10px] px-2 py-0.5 rounded-full border border-green-200">
                        <span className="w-1 h-1 bg-green-500 rounded-full" />
                        Live
                      </div>
                      <div className="absolute bottom-2 left-2 bg-white/90 text-stone-600 text-[10px] px-2 py-0.5 rounded border border-stone-200">
                        {utcToDate(feedData.timestamp).toLocaleTimeString()}
                      </div>
                    </>
                  ) : camera.is_active ? (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <div className="w-7 h-7 border-2 border-stone-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                        <p className="text-xs text-stone-500">Initializing...</p>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <svg className="w-9 h-9 text-stone-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <p className="text-xs text-stone-400">
                          {camera.stream_url ? 'Click Start AI to begin' : 'No source configured'}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer with task count */}
                <div className="px-4 py-2 bg-stone-50 border-t border-stone-100 flex items-center justify-between text-[10px] text-stone-400">
                  <span className="truncate">Source: {camera.stream_url || 'Not set'}</span>
                  <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                    {activeTaskCount > 0 && (
                      <button
                        onClick={() => onSelectCamera?.(camera.id)}
                        className="flex items-center gap-1 text-stone-700 hover:text-stone-900 font-medium"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        {activeTaskCount} task{activeTaskCount !== 1 ? 's' : ''}
                      </button>
                    )}
                    <span>ID {camera.id}</span>
                  </div>
                </div>

                {/* Ask AI — Live & History */}
                <div className="border-t border-stone-100">
                  {/* Tab toggle */}
                  <div className="flex border-b border-stone-100">
                    <button
                      onClick={() => setPromptMode((p) => ({ ...p, [camera.id]: 'live' }))}
                      className={`flex-1 px-3 py-1.5 text-[11px] font-medium transition-colors ${
                        (promptMode[camera.id] || 'live') === 'live'
                          ? 'text-stone-900 border-b-2 border-stone-800'
                          : 'text-stone-400 hover:text-stone-600'
                      }`}
                    >
                      Ask Live
                    </button>
                    <button
                      onClick={() => setPromptMode((p) => ({ ...p, [camera.id]: 'history' }))}
                      className={`flex-1 px-3 py-1.5 text-[11px] font-medium transition-colors ${
                        promptMode[camera.id] === 'history'
                          ? 'text-stone-900 border-b-2 border-stone-800'
                          : 'text-stone-400 hover:text-stone-600'
                      }`}
                    >
                      Ask History
                    </button>
                  </div>

                  {/* Live prompt */}
                  {(promptMode[camera.id] || 'live') === 'live' && (
                    <div className="px-4 py-3 space-y-2">
                      <form
                        onSubmit={(e) => { e.preventDefault(); handlePrompt(camera.id); }}
                        className="flex gap-2"
                      >
                        <input
                          type="text"
                          value={promptInputs[camera.id] || ''}
                          onChange={(e) => setPromptInputs((p) => ({ ...p, [camera.id]: e.target.value }))}
                          placeholder={camera.is_active ? 'Ask about the current feed...' : 'Camera must be active'}
                          disabled={promptLoading[camera.id] || !camera.is_active}
                          className="input flex-1 text-xs py-1.5"
                        />
                        <button
                          type="submit"
                          disabled={promptLoading[camera.id] || !camera.is_active || !(promptInputs[camera.id] || '').trim()}
                          className="px-3 py-1.5 bg-stone-900 hover:bg-stone-800 disabled:opacity-40 text-white text-xs font-medium rounded-md transition-colors flex items-center gap-1.5"
                        >
                          {promptLoading[camera.id] ? (
                            <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                            </svg>
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                          )}
                          Ask
                        </button>
                      </form>

                      {promptAnswers[camera.id] && (
                        <div className="bg-stone-50 border border-stone-200 rounded-md p-2.5 text-xs relative">
                          <button
                            onClick={() => setPromptAnswers((p) => ({ ...p, [camera.id]: null }))}
                            className="absolute top-1.5 right-1.5 text-stone-400 hover:text-stone-600"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                          <p className="text-stone-500 mb-1 font-medium pr-4">
                            Q: {promptAnswers[camera.id]!.question}
                          </p>
                          <p className="text-stone-700 leading-relaxed">
                            {promptAnswers[camera.id]!.answer}
                          </p>
                          <p className="text-stone-400 mt-1 text-[10px]">
                            {promptAnswers[camera.id]!.timestamp}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* History prompt */}
                  {promptMode[camera.id] === 'history' && (
                    <div className="px-4 py-3 space-y-2">
                      <form
                        onSubmit={(e) => { e.preventDefault(); handleHistory(camera.id); }}
                        className="flex gap-2"
                      >
                        <input
                          type="text"
                          value={historyInputs[camera.id] || ''}
                          onChange={(e) => setHistoryInputs((p) => ({ ...p, [camera.id]: e.target.value }))}
                          placeholder="Ask about past recordings..."
                          disabled={historyLoading[camera.id]}
                          className="input flex-1 text-xs py-1.5"
                        />
                        <button
                          type="submit"
                          disabled={historyLoading[camera.id] || !(historyInputs[camera.id] || '').trim()}
                          className="px-3 py-1.5 bg-stone-900 hover:bg-stone-800 disabled:opacity-40 text-white text-xs font-medium rounded-md transition-colors flex items-center gap-1.5"
                        >
                          {historyLoading[camera.id] ? (
                            <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                            </svg>
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          )}
                          Search
                        </button>
                      </form>

                      {historyResults[camera.id] && (
                        <div className="bg-stone-50 border border-stone-200 rounded-md p-2.5 text-xs relative space-y-2">
                          <button
                            onClick={() => setHistoryResults((p) => ({ ...p, [camera.id]: null }))}
                            className="absolute top-1.5 right-1.5 text-stone-400 hover:text-stone-600"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                          <p className="text-stone-500 font-medium pr-4">
                            Q: {historyResults[camera.id]!.question}
                          </p>
                          <p className="text-stone-700 leading-relaxed whitespace-pre-line">
                            {historyResults[camera.id]!.answer}
                          </p>
                          {historyResults[camera.id]!.events_analysed > 0 && (
                            <p className="text-stone-400 text-[10px]">
                              Analysed {historyResults[camera.id]!.events_analysed} events
                              {historyResults[camera.id]!.time_range.start && (
                                <> from {new Date(historyResults[camera.id]!.time_range.start).toLocaleString()} to {new Date(historyResults[camera.id]!.time_range.end).toLocaleString()}</>
                              )}
                            </p>
                          )}
                          {/* Relevant frame thumbnails */}
                          {historyResults[camera.id]!.relevant_frames.filter((f) => f.frame_url).length > 0 && (
                            <div className="space-y-1">
                              <p className="text-stone-500 font-medium text-[10px]">Key frames:</p>
                              <div className="flex gap-1.5 overflow-x-auto pb-1">
                                {historyResults[camera.id]!.relevant_frames
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
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-stone-200 shadow-xl w-full max-w-md max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100 flex-shrink-0">
              <h3 className="text-base font-semibold text-stone-900">Add camera</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 text-stone-400 hover:text-stone-600 rounded transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-6 py-4 space-y-4 overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  Camera name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.name}
                  onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Front Door"
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Location</label>
                <input
                  type="text"
                  value={addForm.location}
                  onChange={(e) => setAddForm((f) => ({ ...f, location: e.target.value }))}
                  placeholder="e.g. Entrance, Kitchen"
                  className="input"
                  list="location-presets"
                />
                <datalist id="location-presets">
                  {PRESET_LOCATIONS.map((loc) => (
                    <option key={loc} value={loc} />
                  ))}
                </datalist>
                <p className="text-xs text-stone-400 mt-1">
                  Recognized locations auto-assign monitoring rules
                </p>
              </div>

              {/* Suggested rules from presets */}
              {matchedPreset.length > 0 && (
                <div className="bg-stone-50 border border-stone-200 rounded-md p-3">
                  <p className="text-xs font-medium text-stone-700 mb-2">
                    Suggested rules for this location
                  </p>
                  <div className="space-y-2">
                    {matchedPreset.map((task, i) => (
                      <label key={i} className="flex items-start gap-2.5 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={selectedPresets.has(i)}
                          onChange={() => {
                            setSelectedPresets((prev) => {
                              const next = new Set(prev);
                              if (next.has(i)) next.delete(i); else next.add(i);
                              return next;
                            });
                          }}
                          className="mt-0.5 rounded border-stone-300 text-stone-700 focus:ring-stone-400"
                        />
                        <span className="text-xs text-stone-600 group-hover:text-stone-800">{task.command}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Custom tasks */}
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Monitoring rules</label>
                {customTasks.length > 0 && (
                  <div className="space-y-1.5 mb-2">
                    {customTasks.map((task, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs bg-stone-50 border border-stone-200 rounded-md px-3 py-2">
                        <span className="flex-1 text-stone-700">{task}</span>
                        <button
                          type="button"
                          onClick={() => setCustomTasks((prev) => prev.filter((_, j) => j !== i))}
                          className="text-stone-400 hover:text-red-500 flex-shrink-0"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customTaskInput}
                    onChange={(e) => setCustomTaskInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && customTaskInput.trim()) {
                        e.preventDefault();
                        setCustomTasks((prev) => [...prev, customTaskInput.trim()]);
                        setCustomTaskInput('');
                      }
                    }}
                    placeholder="e.g. Alert if fridge door is left open"
                    className="input flex-1 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (customTaskInput.trim()) {
                        setCustomTasks((prev) => [...prev, customTaskInput.trim()]);
                        setCustomTaskInput('');
                      }
                    }}
                    disabled={!customTaskInput.trim()}
                    className="px-3 py-2 text-sm font-medium text-stone-600 bg-stone-100 hover:bg-stone-200 rounded-md transition-colors disabled:opacity-40"
                  >
                    Add
                  </button>
                </div>
                <p className="text-xs text-stone-400 mt-1">
                  Describe what this camera should watch for. You can add more later.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  Video source <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.streamUrl}
                  onChange={(e) => setAddForm((f) => ({ ...f, streamUrl: e.target.value }))}
                  placeholder="0 for webcam, /path/to/video.mp4, or rtsp://..."
                  className="input"
                />
                <p className="text-xs text-stone-400 mt-1">
                  Use <code className="font-mono bg-stone-100 px-1 rounded">0</code> for your system webcam
                </p>
              </div>

              {addError && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md border border-red-200">
                  {addError}
                </p>
              )}
            </div>

            <div className="flex gap-2 px-6 py-4 border-t border-stone-100 flex-shrink-0">
              <button onClick={() => setShowAddModal(false)} className="flex-1 btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {adding ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Adding...
                  </>
                ) : 'Add camera'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveFeedGrid;
