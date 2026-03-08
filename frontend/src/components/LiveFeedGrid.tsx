import React, { useState } from 'react';
import { Camera } from '../types';

interface LiveFeedGridProps {
  cameras: Camera[];
  liveFeedData: Map<number, { frame: string; timestamp: string }>;
  onCameraStart: (cameraId: number) => void;
  onCameraStop: (cameraId: number) => void;
  onCameraAdd: (name: string, location: string, streamUrl: string) => Promise<void>;
  onCameraDelete: (cameraId: number) => Promise<void>;
}

const LiveFeedGrid: React.FC<LiveFeedGridProps> = ({
  cameras,
  liveFeedData,
  onCameraStart,
  onCameraStop,
  onCameraAdd,
  onCameraDelete,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({ name: '', location: '', streamUrl: '' });
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleAdd = async () => {
    if (!addForm.name.trim() || !addForm.streamUrl.trim()) {
      setAddError('Camera name and video source are required.');
      return;
    }
    setAdding(true);
    setAddError('');
    try {
      await onCameraAdd(addForm.name.trim(), addForm.location.trim(), addForm.streamUrl.trim());
      setAddForm({ name: '', location: '', streamUrl: '' });
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

  const activeCameraCount = cameras.filter((c) => c.is_active).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Live Cameras</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {cameras.length} registered{activeCameraCount > 0 && ` · ${activeCameraCount} active`}
          </p>
        </div>
        <button
          onClick={() => { setShowAddModal(true); setAddError(''); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add camera
        </button>
      </div>

      {/* Empty state */}
      {cameras.length === 0 && (
        <div className="card">
          <div className="card-body py-16 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-900 mb-1">No cameras registered</p>
            <p className="text-sm text-gray-500 mb-4">Add a camera to begin AI-powered monitoring.</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-primary"
            >
              Add your first camera
            </button>
          </div>
        </div>
      )}

      {/* Camera grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cameras.map((camera) => {
          const feedData = liveFeedData.get(camera.id);
          const isDeleting = deletingId === camera.id;

          return (
            <div key={camera.id} className="card overflow-hidden">
              {/* Card header */}
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-gray-900 truncate">{camera.name}</h3>
                  <p className="text-xs text-gray-400 truncate">{camera.location || 'No location'}</p>
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
                        className="text-xs px-2.5 py-1 bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 rounded-md transition-colors"
                      >
                        Stop
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => onCameraStart(camera.id)}
                      className="text-xs px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                    >
                      Start AI
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(camera.id)}
                    disabled={isDeleting}
                    className="p-1 text-gray-400 hover:text-red-500 rounded-md transition-colors"
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
              <div className="relative aspect-video bg-gray-100">
                {camera.is_active && feedData?.frame ? (
                  <>
                    <img
                      src={`data:image/jpeg;base64,${feedData.frame}`}
                      alt={`Feed from ${camera.name}`}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 right-2 flex items-center gap-1 bg-white/90 text-green-700 text-xs px-2 py-0.5 rounded-full border border-green-200">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                      Live
                    </div>
                    <div className="absolute bottom-2 left-2 bg-white/90 text-gray-600 text-xs px-2 py-0.5 rounded border border-gray-200">
                      {new Date(feedData.timestamp).toLocaleTimeString()}
                    </div>
                  </>
                ) : camera.is_active ? (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-sm text-gray-500">Initializing...</p>
                    </div>
                  </div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-center">
                      <svg className="w-10 h-10 text-gray-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      <p className="text-sm text-gray-400">
                        {camera.stream_url ? 'Click Start AI to begin' : 'No source configured'}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                <span className="truncate">Source: {camera.stream_url || 'Not set'}</span>
                <span className="ml-2 flex-shrink-0">ID {camera.id}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold text-gray-900">Add camera</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-md transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                <input
                  type="text"
                  value={addForm.location}
                  onChange={(e) => setAddForm((f) => ({ ...f, location: e.target.value }))}
                  placeholder="e.g. Entrance, Kitchen"
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Video source <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.streamUrl}
                  onChange={(e) => setAddForm((f) => ({ ...f, streamUrl: e.target.value }))}
                  placeholder="0 for webcam, /path/to/video.mp4, or rtsp://..."
                  className="input"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Use <code className="font-mono bg-gray-100 px-1 rounded">0</code> for your system webcam
                </p>
              </div>

              {addError && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md border border-red-200">
                  {addError}
                </p>
              )}
            </div>

            <div className="flex gap-2 px-6 pb-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="flex-1 btn-primary flex items-center justify-center gap-2"
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
