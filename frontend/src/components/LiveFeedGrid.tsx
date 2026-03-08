/**
 * Live camera feed grid — real cameras only, full CRUD management
 */
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
    if (!window.confirm('Delete this camera? This cannot be undone.')) return;
    setDeletingId(cameraId);
    try {
      await onCameraDelete(cameraId);
    } finally {
      setDeletingId(null);
    }
  };

  const activeCameraCount = cameras.filter(c => c.is_active).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
            <span className="text-2xl">📹</span>
            Live Camera Feeds
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            {cameras.length} camera{cameras.length !== 1 ? 's' : ''} registered
            {activeCameraCount > 0 && ` · ${activeCameraCount} active`}
          </p>
        </div>
        <button
          onClick={() => { setShowAddModal(true); setAddError(''); }}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors text-sm font-medium shadow-lg shadow-cyan-500/20"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Camera
        </button>
      </div>

      {/* Empty state */}
      {cameras.length === 0 && (
        <div className="text-center py-16 border-2 border-dashed border-dark-700 rounded-xl">
          <div className="text-5xl mb-4">📷</div>
          <p className="text-gray-400 font-medium mb-2">No cameras registered yet</p>
          <p className="text-gray-600 text-sm mb-6">Add a camera to start AI-powered monitoring</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors text-sm font-medium"
          >
            Add your first camera
          </button>
        </div>
      )}

      {/* Camera grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cameras.map((camera) => {
          const feedData = liveFeedData.get(camera.id);
          const isDeleting = deletingId === camera.id;

          return (
            <div key={camera.id} className="card group hover:border-cyan-500/30 transition-all duration-300">
              {/* Card header */}
              <div className="card-header flex items-center justify-between bg-gradient-to-r from-dark-800 to-dark-900">
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-100 flex items-center gap-2 truncate">
                    <span className="text-lg flex-shrink-0">📹</span>
                    <span className="truncate">{camera.name}</span>
                  </h3>
                  <p className="text-xs text-gray-400 truncate">{camera.location || 'No location set'}</p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                  {camera.is_active ? (
                    <>
                      <span className="flex items-center gap-1 text-xs text-green-400 font-semibold">
                        <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50"></span>
                        AI ACTIVE
                      </span>
                      <button
                        onClick={() => onCameraStop(camera.id)}
                        className="text-xs px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                      >
                        Stop
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => onCameraStart(camera.id)}
                      className="text-xs px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                    >
                      Start AI
                    </button>
                  )}

                  {/* Delete button */}
                  <button
                    onClick={() => handleDelete(camera.id)}
                    disabled={isDeleting}
                    className="text-xs p-1.5 bg-dark-700 hover:bg-red-600/20 text-gray-500 hover:text-red-400 rounded-lg transition-colors border border-dark-600 hover:border-red-500/40"
                    title="Delete camera"
                  >
                    {isDeleting ? (
                      <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Feed area */}
              <div className="card-body p-0">
                <div className="relative aspect-video bg-dark-900 overflow-hidden">
                  {camera.is_active && feedData?.frame ? (
                    <>
                      <img
                        src={`data:image/jpeg;base64,${feedData.frame}`}
                        alt={`Feed from ${camera.name}`}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute top-3 right-3 bg-gradient-to-r from-green-500 to-green-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg flex items-center gap-1">
                        <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                        AI LIVE
                      </div>
                      <div className="absolute bottom-3 left-3 bg-dark-900/90 backdrop-blur-sm px-3 py-1.5 rounded-lg text-xs text-gray-300 border border-dark-700">
                        🕐 {new Date(feedData.timestamp).toLocaleTimeString()}
                      </div>
                    </>
                  ) : camera.is_active ? (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <div className="animate-pulse mb-2">
                          <svg className="w-12 h-12 mx-auto text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <p className="text-gray-300 text-sm">Initializing AI surveillance...</p>
                        <p className="text-xs text-gray-600 mt-1">Frames will appear shortly</p>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <div className="bg-dark-800 rounded-full p-4 inline-block mb-3 border-2 border-dark-700">
                          <svg className="w-10 h-10 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <p className="text-gray-300 font-medium">Camera Ready</p>
                        <p className="text-xs text-gray-600 mt-1">
                          {camera.stream_url ? 'Click "Start AI" to begin monitoring' : 'No video source configured'}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Camera info bar */}
                <div className="px-3 py-2 bg-dark-800/50 border-t border-dark-700 flex items-center justify-between text-xs text-gray-500">
                  <span className="truncate">
                    Source: <span className="text-gray-400">{camera.stream_url || 'Not set'}</span>
                  </span>
                  <span className="ml-2 flex-shrink-0">ID: {camera.id}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700 rounded-xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-dark-700">
              <h3 className="text-lg font-bold text-gray-100">Add New Camera</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-500 hover:text-gray-300 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Camera Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.name}
                  onChange={(e) => setAddForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Kitchen Camera"
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Location</label>
                <input
                  type="text"
                  value={addForm.location}
                  onChange={(e) => setAddForm(f => ({ ...f, location: e.target.value }))}
                  placeholder="e.g. Kitchen, Garden, Front Door"
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Video Source <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.streamUrl}
                  onChange={(e) => setAddForm(f => ({ ...f, streamUrl: e.target.value }))}
                  placeholder="0 (webcam), /path/to/video.mp4, or rtsp://..."
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500 text-sm"
                />
                <p className="text-xs text-gray-600 mt-1">
                  Use <code className="text-cyan-500">0</code> for webcam, a file path for video, or RTSP URL for IP cameras
                </p>
              </div>

              {addError && (
                <p className="text-sm text-red-400 bg-red-400/10 px-3 py-2 rounded-lg border border-red-400/20">
                  {addError}
                </p>
              )}
            </div>

            <div className="flex gap-3 px-6 pb-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2 bg-dark-800 hover:bg-dark-700 text-gray-400 rounded-lg transition-colors text-sm border border-dark-600"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="flex-1 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2"
              >
                {adding ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Adding...
                  </>
                ) : 'Add Camera'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveFeedGrid;
