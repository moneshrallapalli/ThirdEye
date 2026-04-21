import React, { useEffect, useState } from 'react';
import { Camera, CameraTask } from '../types';
import { taskApi } from '../services/api';

interface CameraTaskPanelProps {
  camera: Camera;
  onClose: () => void;
}

const taskTypeLabels: Record<string, string> = {
  fire_detection: 'Fire',
  safety_monitoring: 'Safety',
  intrusion_detection: 'Intrusion',
  property_monitoring: 'Property',
  package_detection: 'Package',
  vehicle_monitoring: 'Vehicle',
  activity_monitoring: 'Activity',
  motion_detection: 'Motion',
  access_monitoring: 'Access',
  state_monitoring: 'State',
  theft_detection: 'Theft',
  custom: 'Custom',
};

const taskTypeColor: Record<string, string> = {
  fire_detection: 'bg-red-50 text-red-700 border-red-200',
  safety_monitoring: 'bg-orange-50 text-orange-700 border-orange-200',
  intrusion_detection: 'bg-red-50 text-red-700 border-red-200',
  theft_detection: 'bg-red-50 text-red-700 border-red-200',
  property_monitoring: 'bg-green-50 text-green-700 border-green-200',
  package_detection: 'bg-stone-50 text-stone-600 border-stone-200',
  vehicle_monitoring: 'bg-stone-50 text-stone-600 border-stone-200',
  activity_monitoring: 'bg-stone-50 text-stone-600 border-stone-200',
  motion_detection: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  access_monitoring: 'bg-stone-50 text-stone-600 border-stone-200',
  state_monitoring: 'bg-stone-50 text-stone-600 border-stone-200',
  custom: 'bg-stone-50 text-stone-600 border-stone-200',
};

const CameraTaskPanel: React.FC<CameraTaskPanelProps> = ({ camera, onClose }) => {
  const [tasks, setTasks] = useState<CameraTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCommand, setNewCommand] = useState('');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');

  const loadTasks = async () => {
    try {
      const data = await taskApi.getForCamera(camera.id);
      setTasks(data);
    } catch {
      setError('Failed to load tasks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [camera.id]);

  const handleAdd = async () => {
    const cmd = newCommand.trim();
    if (!cmd) return;
    setAdding(true);
    setError('');
    try {
      await taskApi.create(camera.id, cmd);
      setNewCommand('');
      await loadTasks();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add task.');
    } finally {
      setAdding(false);
    }
  };

  const handleToggle = async (task: CameraTask) => {
    try {
      await taskApi.update(camera.id, task.id, { is_active: !task.is_active });
      await loadTasks();
    } catch {}
  };

  const handleDelete = async (taskId: number) => {
    try {
      await taskApi.delete(camera.id, taskId);
      await loadTasks();
    } catch {}
  };

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl border border-stone-200 shadow-xl w-full max-w-lg max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100 flex-shrink-0">
          <div>
            <h3 className="text-base font-semibold text-stone-900">{camera.name} — Tasks</h3>
            <p className="text-xs text-stone-400 mt-0.5">{camera.location || 'No location'}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-stone-400 hover:text-stone-600 rounded transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Task list */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-stone-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-stone-500 mb-1">No tasks assigned</p>
              <p className="text-xs text-stone-400">Add a task below to start monitoring.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => {
                const typeLabel = taskTypeLabels[task.task_type] || task.task_type;
                const typeColor = taskTypeColor[task.task_type] || taskTypeColor.custom;

                return (
                  <div
                    key={task.id}
                    className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                      task.is_active
                        ? 'bg-white border-stone-200'
                        : 'bg-stone-50 border-stone-100 opacity-60'
                    }`}
                  >
                    {/* Toggle */}
                    <button
                      onClick={() => handleToggle(task)}
                      className={`mt-0.5 flex-shrink-0 w-8 h-5 rounded-full transition-colors relative ${
                        task.is_active ? 'bg-stone-700' : 'bg-stone-300'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                          task.is_active ? 'left-3.5' : 'left-0.5'
                        }`}
                      />
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${task.is_active ? 'text-stone-800' : 'text-stone-500'}`}>
                        {task.command}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${typeColor}`}>
                          {typeLabel}
                        </span>
                        {task.is_default && (
                          <span className="text-[10px] text-stone-400">Default</span>
                        )}
                      </div>
                    </div>

                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(task.id)}
                      className="p-1 text-stone-300 hover:text-red-500 rounded transition-colors flex-shrink-0"
                      title="Remove task"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Add task form */}
        <div className="px-6 py-4 border-t border-stone-100 flex-shrink-0">
          {error && (
            <p className="text-xs text-red-600 mb-2">{error}</p>
          )}
          <form
            onSubmit={(e) => { e.preventDefault(); handleAdd(); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={newCommand}
              onChange={(e) => setNewCommand(e.target.value)}
              placeholder="e.g. Alert if fridge door is left open"
              className="input flex-1 text-sm"
              disabled={adding}
            />
            <button
              type="submit"
              disabled={adding || !newCommand.trim()}
              className="btn-primary disabled:opacity-50 flex-shrink-0"
            >
              {adding ? 'Adding...' : 'Add'}
            </button>
          </form>
          <p className="text-[10px] text-stone-400 mt-1.5">
            Describe what you want this camera to watch for. Tasks run 24/7 while the camera is active.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CameraTaskPanel;
