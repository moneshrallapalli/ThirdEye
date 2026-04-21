import React, { useEffect, useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { Camera, CameraTask } from '../types';
import { taskApi } from '../services/api';

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

interface CameraTaskGroup {
  camera: Camera;
  tasks: CameraTask[];
  loading: boolean;
}

const TasksPage: React.FC = () => {
  const { cameras } = useSurveillance();
  const [groups, setGroups] = useState<CameraTaskGroup[]>([]);
  const [addingFor, setAddingFor] = useState<number | null>(null);
  const [newCommand, setNewCommand] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadAllTasks = async () => {
    const result: CameraTaskGroup[] = cameras.map((c) => ({
      camera: c,
      tasks: [],
      loading: true,
    }));
    setGroups(result);

    const loaded = await Promise.all(
      cameras.map(async (cam) => {
        try {
          const tasks = await taskApi.getForCamera(cam.id);
          return { camera: cam, tasks, loading: false };
        } catch {
          return { camera: cam, tasks: [], loading: false };
        }
      })
    );
    setGroups(loaded);
  };

  useEffect(() => {
    loadAllTasks();
  }, [cameras]);

  const handleToggle = async (cameraId: number, task: CameraTask) => {
    try {
      await taskApi.update(cameraId, task.id, { is_active: !task.is_active });
      await loadAllTasks();
    } catch {}
  };

  const handleDelete = async (cameraId: number, taskId: number) => {
    try {
      await taskApi.delete(cameraId, taskId);
      await loadAllTasks();
    } catch {}
  };

  const handleAdd = async (cameraId: number) => {
    const cmd = newCommand.trim();
    if (!cmd) return;
    setSubmitting(true);
    try {
      await taskApi.create(cameraId, cmd);
      setNewCommand('');
      setAddingFor(null);
      await loadAllTasks();
    } catch {}
    setSubmitting(false);
  };

  const totalTasks = groups.reduce((sum, g) => sum + g.tasks.length, 0);
  const activeTasks = groups.reduce(
    (sum, g) => sum + g.tasks.filter((t) => t.is_active).length,
    0
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Monitoring Tasks</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            {totalTasks} task{totalTasks !== 1 ? 's' : ''} across {cameras.length} camera{cameras.length !== 1 ? 's' : ''}
            {activeTasks > 0 ? ` · ${activeTasks} active` : ''}
          </p>
        </div>
      </div>

      {/* Empty state */}
      {cameras.length === 0 && (
        <div className="bg-white border border-stone-200 rounded-lg py-16 text-center">
          <svg className="w-10 h-10 mx-auto text-stone-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-sm font-medium text-stone-900 mb-1">No cameras registered</p>
          <p className="text-sm text-stone-400">Add a camera first, then assign monitoring tasks to it.</p>
        </div>
      )}

      {/* Camera task groups */}
      <div className="space-y-4">
        {groups.map(({ camera, tasks, loading }) => (
          <div key={camera.id} className="bg-white border border-stone-200 rounded-lg overflow-hidden">
            {/* Camera header */}
            <div className="px-5 py-4 border-b border-stone-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${camera.is_active ? 'bg-green-500' : 'bg-stone-300'}`}
                  />
                  <h2 className="text-sm font-semibold text-stone-900">{camera.name}</h2>
                </div>
                {camera.location && (
                  <span className="text-xs text-stone-400">{camera.location}</span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-stone-400">
                  {tasks.filter((t) => t.is_active).length} of {tasks.length} active
                </span>
                <button
                  onClick={() => {
                    setAddingFor(addingFor === camera.id ? null : camera.id);
                    setNewCommand('');
                  }}
                  className="flex items-center gap-1 text-xs px-2.5 py-1.5 text-white rounded-md transition-colors"
                  style={{ background: '#1A1714' }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = '#2C2724')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = '#1A1714')}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add task
                </button>
              </div>
            </div>

            {/* Add task input */}
            {addingFor === camera.id && (
              <div className="px-5 py-3 bg-stone-50 border-b border-stone-100">
                <form
                  onSubmit={(e) => { e.preventDefault(); handleAdd(camera.id); }}
                  className="flex gap-2"
                >
                  <input
                    type="text"
                    value={newCommand}
                    onChange={(e) => setNewCommand(e.target.value)}
                    placeholder="Describe what this camera should watch for..."
                    className="input flex-1 text-sm"
                    autoFocus
                    disabled={submitting}
                  />
                  <button
                    type="submit"
                    disabled={submitting || !newCommand.trim()}
                    className="btn-primary disabled:opacity-50 flex-shrink-0"
                  >
                    {submitting ? 'Adding...' : 'Add'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAddingFor(null); setNewCommand(''); }}
                    className="px-3 py-2 text-sm text-stone-500 hover:text-stone-700 transition-colors"
                  >
                    Cancel
                  </button>
                </form>
              </div>
            )}

            {/* Task list */}
            {loading ? (
              <div className="px-5 py-6 flex justify-center">
                <div className="w-5 h-5 border-2 border-stone-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : tasks.length === 0 ? (
              <div className="px-5 py-6 text-center">
                <p className="text-sm text-stone-400">No tasks assigned to this camera.</p>
              </div>
            ) : (
              <div className="divide-y divide-stone-100">
                {tasks.map((task) => {
                  const typeLabel = taskTypeLabels[task.task_type] || task.task_type;
                  const typeColor = taskTypeColor[task.task_type] || taskTypeColor.custom;

                  return (
                    <div
                      key={task.id}
                      className={`px-5 py-3 flex items-center gap-4 transition-colors ${
                        task.is_active ? '' : 'opacity-50'
                      }`}
                    >
                      {/* Toggle */}
                      <button
                        onClick={() => handleToggle(camera.id, task)}
                        className={`flex-shrink-0 w-9 h-5 rounded-full transition-colors relative ${
                          task.is_active ? 'bg-stone-700' : 'bg-stone-300'
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                            task.is_active ? 'left-4' : 'left-0.5'
                          }`}
                        />
                      </button>

                      {/* Command text */}
                      <p className="flex-1 text-sm text-stone-800 min-w-0">{task.command}</p>

                      {/* Badges */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${typeColor}`}>
                          {typeLabel}
                        </span>
                        {task.is_default && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded border border-stone-200 text-stone-400 font-medium">
                            Preset
                          </span>
                        )}
                      </div>

                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(camera.id, task.id)}
                        className="p-1 text-stone-300 hover:text-red-500 rounded transition-colors flex-shrink-0"
                        title="Remove task"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TasksPage;
