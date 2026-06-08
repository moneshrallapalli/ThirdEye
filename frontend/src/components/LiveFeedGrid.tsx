import React, { useEffect, useRef, useState } from 'react';
import { Camera } from '../types';
import { taskApi } from '../services/api';
import { utcToDate } from '../utils/time';

interface LiveFeedGridProps {
  cameras: Camera[];
  liveFeedData: Map<number, { frame: string; timestamp: string }>;
  view: 'grid' | 'list';
  onCameraStart: (cameraId: number) => void;
  onCameraStop: (cameraId: number) => void;
  onCameraAdd: (
    name: string,
    location: string,
    streamUrl: string,
    tasks?: { command: string; task_type: string; priority?: number }[],
  ) => Promise<void>;
  onCameraDelete: (cameraId: number) => Promise<void>;
  onOpenAskAI: (cameraId: number) => void;
  onManageTasks?: (cameraId: number) => void;
  onRequestAdd: () => void;
  showAddModal: boolean;
  onCloseAddModal: () => void;
}

const PRESET_LOCATIONS = [
  'Kitchen', 'Garden', 'Entrance', 'Front Door', 'Back Door',
  'Parking', 'Garage', 'Living Room', 'Bedroom', 'Office',
  'Warehouse', 'Pool', 'Baby Room', 'Nursery', 'Driveway',
  'Backyard', 'Shop', 'Store',
];

const LiveFeedGrid: React.FC<LiveFeedGridProps> = ({
  cameras,
  liveFeedData,
  view,
  onCameraStart,
  onCameraStop,
  onCameraAdd,
  onCameraDelete,
  onOpenAskAI,
  onManageTasks,
  onRequestAdd,
  showAddModal,
  onCloseAddModal,
}) => {
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
        }),
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
      onCloseAddModal();
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

  // Empty state
  if (cameras.length === 0) {
    return (
      <>
        <div className="bg-white border border-stone-200 rounded-lg py-20 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-stone-100 rounded-full mb-4">
            <svg className="w-6 h-6 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-stone-900 mb-1">No cameras registered</p>
          <p className="text-sm text-stone-400 mb-4">Add a camera to start monitoring.</p>
          <button onClick={onRequestAdd} className="btn-primary">
            Add your first camera
          </button>
        </div>
        {showAddModal && (
          <AddCameraModal
            addForm={addForm}
            setAddForm={setAddForm}
            adding={adding}
            addError={addError}
            matchedPreset={matchedPreset}
            selectedPresets={selectedPresets}
            setSelectedPresets={setSelectedPresets}
            customTasks={customTasks}
            setCustomTasks={setCustomTasks}
            customTaskInput={customTaskInput}
            setCustomTaskInput={setCustomTaskInput}
            onClose={onCloseAddModal}
            onSubmit={handleAdd}
          />
        )}
      </>
    );
  }

  // Grid view
  if (view === 'grid') {
    return (
      <>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {cameras.map((camera) => {
            const feedData = liveFeedData.get(camera.id);
            const isDeleting = deletingId === camera.id;
            const activeTaskCount = taskCounts[camera.id] ?? 0;

            return (
              <div
                key={camera.id}
                className="bg-white border border-stone-200 rounded-lg overflow-hidden flex flex-col group hover:border-stone-300 transition-colors"
              >
                {/* Feed area (header is now overlay) */}
                <div className="relative aspect-video bg-stone-100">
                  {camera.is_active && feedData?.frame ? (
                    <img
                      src={`data:image/jpeg;base64,${feedData.frame}`}
                      alt={`Feed from ${camera.name}`}
                      className="w-full h-full object-cover"
                    />
                  ) : camera.is_active ? (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <div className="w-7 h-7 border-2 border-stone-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                        <p className="text-xs text-stone-500">Initializing…</p>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <svg className="w-10 h-10 text-stone-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}

                  {/* Status pill top-left */}
                  <div className="absolute top-2 left-2">
                    {camera.is_active ? (
                      <span className="inline-flex items-center gap-1 bg-white/95 text-green-700 text-[10px] px-1.5 py-0.5 rounded-full border border-green-200 font-medium">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                        Live
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 bg-white/95 text-stone-500 text-[10px] px-1.5 py-0.5 rounded-full border border-stone-200 font-medium">
                        <span className="w-1.5 h-1.5 bg-stone-300 rounded-full" />
                        Offline
                      </span>
                    )}
                  </div>

                  {/* Task pill top-right */}
                  {activeTaskCount > 0 && (
                    <button
                      onClick={() => onManageTasks?.(camera.id)}
                      className="absolute top-2 right-2 inline-flex items-center gap-1 bg-white/95 text-stone-700 hover:text-stone-900 text-[10px] px-1.5 py-0.5 rounded-full border border-stone-200 font-medium transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      {activeTaskCount}
                    </button>
                  )}

                  {/* Timestamp bottom-right */}
                  {camera.is_active && feedData?.timestamp && (
                    <div className="absolute bottom-2 right-2 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
                      {utcToDate(feedData.timestamp).toLocaleTimeString()}
                    </div>
                  )}
                </div>

                {/* Info row */}
                <div className="px-4 py-3 flex items-center justify-between gap-3 flex-1">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-stone-900 truncate">{camera.name}</h3>
                    <p className="text-xs text-stone-500 truncate">{camera.location || 'No location'}</p>
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0">
                    {camera.is_active ? (
                      <button
                        onClick={() => onCameraStop(camera.id)}
                        className="text-xs px-2.5 py-1.5 bg-white border border-stone-200 hover:bg-stone-50 text-stone-700 rounded-md transition-colors font-medium"
                        title="Stop camera"
                      >
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => onCameraStart(camera.id)}
                        className="text-xs px-2.5 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded-md transition-colors font-medium"
                        title="Start AI monitoring"
                      >
                        Start
                      </button>
                    )}

                    <button
                      onClick={() => onOpenAskAI(camera.id)}
                      className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded-md transition-colors"
                      title="Ask AI about this camera"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                    </button>

                    <CameraOverflowMenu
                      cameraId={camera.id}
                      isDeleting={isDeleting}
                      onManageTasks={onManageTasks ? () => onManageTasks(camera.id) : undefined}
                      onDelete={() => handleDelete(camera.id)}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {showAddModal && (
          <AddCameraModal
            addForm={addForm}
            setAddForm={setAddForm}
            adding={adding}
            addError={addError}
            matchedPreset={matchedPreset}
            selectedPresets={selectedPresets}
            setSelectedPresets={setSelectedPresets}
            customTasks={customTasks}
            setCustomTasks={setCustomTasks}
            customTaskInput={customTaskInput}
            setCustomTaskInput={setCustomTaskInput}
            onClose={onCloseAddModal}
            onSubmit={handleAdd}
          />
        )}
      </>
    );
  }

  // List view
  return (
    <>
      <div className="bg-white border border-stone-200 rounded-lg">
        <div className="hidden md:grid px-4 py-2.5 gap-4 border-b border-stone-100 bg-stone-50 rounded-t-lg text-[11px] font-medium text-stone-500 uppercase tracking-wide" style={{ gridTemplateColumns: '120px 1fr 120px 80px 200px' }}>
          <div>Feed</div>
          <div>Camera</div>
          <div>Status</div>
          <div className="text-center">Tasks</div>
          <div className="text-right">Actions</div>
        </div>
        <div className="divide-y divide-stone-100">
          {cameras.map((camera) => {
            const feedData = liveFeedData.get(camera.id);
            const isDeleting = deletingId === camera.id;
            const activeTaskCount = taskCounts[camera.id] ?? 0;

            return (
              <div
                key={camera.id}
                className="px-4 py-3 grid gap-4 items-center hover:bg-stone-50 transition-colors"
                style={{ gridTemplateColumns: '120px 1fr 120px 80px 200px' }}
              >
                {/* Thumbnail */}
                <div className="w-[108px] h-[60px] rounded overflow-hidden bg-stone-100 flex-shrink-0 relative">
                  {camera.is_active && feedData?.frame ? (
                    <img
                      src={`data:image/jpeg;base64,${feedData.frame}`}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-stone-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Camera info */}
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-stone-900 truncate">{camera.name}</p>
                  <p className="text-xs text-stone-500 truncate">{camera.location || 'No location'}</p>
                  <p className="text-[10px] text-stone-400 truncate mt-0.5 md:hidden">
                    Source: {camera.stream_url || 'Not set'}
                  </p>
                </div>

                {/* Status */}
                <div>
                  {camera.is_active ? (
                    <span className="inline-flex items-center gap-1.5 text-xs text-green-700 font-medium">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                      Live
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-xs text-stone-400 font-medium">
                      <span className="w-1.5 h-1.5 bg-stone-300 rounded-full" />
                      Offline
                    </span>
                  )}
                </div>

                {/* Tasks */}
                <div className="text-center">
                  {activeTaskCount > 0 ? (
                    <button
                      onClick={() => onManageTasks?.(camera.id)}
                      className="text-xs font-medium text-stone-700 hover:text-stone-900 px-2 py-0.5 rounded-full bg-stone-100 hover:bg-stone-200 transition-colors"
                    >
                      {activeTaskCount}
                    </button>
                  ) : (
                    <span className="text-xs text-stone-300">—</span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-1 flex-shrink-0">
                  {camera.is_active ? (
                    <button
                      onClick={() => onCameraStop(camera.id)}
                      className="text-xs px-2.5 py-1.5 bg-white border border-stone-200 hover:bg-stone-100 text-stone-700 rounded-md transition-colors font-medium"
                    >
                      Stop
                    </button>
                  ) : (
                    <button
                      onClick={() => onCameraStart(camera.id)}
                      className="text-xs px-2.5 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded-md transition-colors font-medium"
                    >
                      Start
                    </button>
                  )}
                  <button
                    onClick={() => onOpenAskAI(camera.id)}
                    className="text-xs px-2.5 py-1.5 text-stone-700 hover:text-stone-900 hover:bg-stone-100 rounded-md transition-colors font-medium flex items-center gap-1"
                    title="Ask AI"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    Ask
                  </button>
                  <CameraOverflowMenu
                    cameraId={camera.id}
                    isDeleting={isDeleting}
                    onManageTasks={onManageTasks ? () => onManageTasks(camera.id) : undefined}
                    onDelete={() => handleDelete(camera.id)}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {showAddModal && (
        <AddCameraModal
          addForm={addForm}
          setAddForm={setAddForm}
          adding={adding}
          addError={addError}
          matchedPreset={matchedPreset}
          selectedPresets={selectedPresets}
          setSelectedPresets={setSelectedPresets}
          customTasks={customTasks}
          setCustomTasks={setCustomTasks}
          customTaskInput={customTaskInput}
          setCustomTaskInput={setCustomTaskInput}
          onClose={onCloseAddModal}
          onSubmit={handleAdd}
        />
      )}
    </>
  );
};

/* -------------- Overflow menu -------------- */

interface OverflowMenuProps {
  cameraId: number;
  isDeleting: boolean;
  onManageTasks?: () => void;
  onDelete: () => void;
}

const CameraOverflowMenu: React.FC<OverflowMenuProps> = ({ cameraId, isDeleting, onManageTasks, onDelete }) => {
  const [open, setOpen] = useState(false);
  const [flipUp, setFlipUp] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = () => setOpen(false);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, [open]);

  const handleToggle = () => {
    if (!open && btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      setFlipUp(spaceBelow < 120);
    }
    setOpen((o) => !o);
  };

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        ref={btnRef}
        onClick={handleToggle}
        disabled={isDeleting}
        className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded-md transition-colors"
        title="More"
        aria-label={`More actions for camera ${cameraId}`}
      >
        {isDeleting ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01" />
          </svg>
        )}
      </button>
      {open && (
        <div
          className={`absolute right-0 w-44 bg-white border border-stone-200 rounded-md shadow-lg z-50 overflow-hidden ${
            flipUp ? 'bottom-full mb-1' : 'top-full mt-1'
          }`}
          onClick={() => setOpen(false)}
        >
          {onManageTasks && (
            <button
              onClick={onManageTasks}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-stone-700 hover:bg-stone-50 text-left"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              Manage tasks
            </button>
          )}
          <button
            onClick={onDelete}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-600 hover:bg-red-50 text-left"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete camera
          </button>
        </div>
      )}
    </div>
  );
};

/* -------------- Add camera modal -------------- */

interface AddCameraModalProps {
  addForm: { name: string; location: string; streamUrl: string };
  setAddForm: React.Dispatch<React.SetStateAction<{ name: string; location: string; streamUrl: string }>>;
  adding: boolean;
  addError: string;
  matchedPreset: { command: string; task_type: string }[];
  selectedPresets: Set<number>;
  setSelectedPresets: React.Dispatch<React.SetStateAction<Set<number>>>;
  customTasks: string[];
  setCustomTasks: React.Dispatch<React.SetStateAction<string[]>>;
  customTaskInput: string;
  setCustomTaskInput: React.Dispatch<React.SetStateAction<string>>;
  onClose: () => void;
  onSubmit: () => void;
}

const AddCameraModal: React.FC<AddCameraModalProps> = ({
  addForm,
  setAddForm,
  adding,
  addError,
  matchedPreset,
  selectedPresets,
  setSelectedPresets,
  customTasks,
  setCustomTasks,
  customTaskInput,
  setCustomTaskInput,
  onClose,
  onSubmit,
}) => (
  <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
    <div className="bg-white rounded-xl border border-stone-200 shadow-xl w-full max-w-md max-h-[90vh] flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100 flex-shrink-0">
        <h3 className="text-base font-semibold text-stone-900">Add camera</h3>
        <button
          onClick={onClose}
          className="p-1 text-stone-400 hover:text-stone-900 rounded transition-colors"
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

        {matchedPreset.length > 0 && (
          <div className="bg-stone-50 border border-stone-200 rounded-md p-3">
            <p className="text-xs font-medium text-stone-700 mb-2">Suggested rules for this location</p>
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
        <button onClick={onClose} className="flex-1 btn-secondary">Cancel</button>
        <button
          onClick={onSubmit}
          disabled={adding}
          className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {adding ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Adding…
            </>
          ) : (
            'Add camera'
          )}
        </button>
      </div>
    </div>
  </div>
);

export default LiveFeedGrid;
