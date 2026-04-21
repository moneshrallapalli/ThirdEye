import React, { useEffect, useMemo, useState } from 'react';
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

type StatusFilter = 'all' | 'active' | 'inactive';

const TasksPage: React.FC = () => {
  const { cameras } = useSurveillance();
  const [groups, setGroups] = useState<CameraTaskGroup[]>([]);
  const [addingFor, setAddingFor] = useState<number | null>(null);
  const [newCommand, setNewCommand] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

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
      }),
    );
    setGroups(loaded);
  };

  useEffect(() => {
    loadAllTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    0,
  );

  const filteredGroups = useMemo(() => {
    const q = search.trim().toLowerCase();
    return groups
      .map((g) => {
        let tasks = g.tasks;
        if (filter === 'active') tasks = tasks.filter((t) => t.is_active);
        else if (filter === 'inactive') tasks = tasks.filter((t) => !t.is_active);
        if (q) tasks = tasks.filter((t) => t.command.toLowerCase().includes(q));
        return { ...g, tasks };
      })
      .filter((g) => {
        if (!q) return true;
        const match = g.camera.name.toLowerCase().includes(q) || (g.camera.location || '').toLowerCase().includes(q);
        return g.tasks.length > 0 || match;
      });
  }, [groups, filter, search]);

  const toggleCollapse = (cameraId: number) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(cameraId)) next.delete(cameraId);
      else next.add(cameraId);
      return next;
    });
  };

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Monitoring Tasks</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            {totalTasks} task{totalTasks !== 1 ? 's' : ''} across {cameras.length} camera{cameras.length !== 1 ? 's' : ''}
            {activeTasks > 0 ? ` · ${activeTasks} active` : ''}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      {cameras.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400 pointer-events-none"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tasks or cameras…"
              className="input pl-9 py-1.5"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-stone-400 hover:text-stone-700 rounded"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 bg-white border border-stone-200 rounded-md p-0.5">
            {([
              { id: 'all' as StatusFilter, label: 'All', count: totalTasks },
              { id: 'active' as StatusFilter, label: 'Active', count: activeTasks },
              { id: 'inactive' as StatusFilter, label: 'Inactive', count: totalTasks - activeTasks },
            ]).map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  filter === f.id
                    ? 'bg-stone-900 text-white'
                    : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50'
                }`}
              >
                {f.label}
                <span className={`ml-1 text-[10px] ${filter === f.id ? 'text-stone-300' : 'text-stone-400'}`}>
                  {f.count}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

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
      <div className="space-y-3">
        {filteredGroups.map(({ camera, tasks, loading }) => {
          const isCollapsed = collapsed.has(camera.id);
          const taskCount = tasks.length;
          const activeCount = tasks.filter((t) => t.is_active).length;

          return (
            <div key={camera.id} className="bg-white border border-stone-200 rounded-lg overflow-hidden">
              {/* Camera header — clickable to collapse */}
              <div className="px-5 py-3.5 border-b border-stone-100 flex items-center justify-between gap-3">
                <button
                  onClick={() => toggleCollapse(camera.id)}
                  className="flex items-center gap-3 min-w-0 flex-1 text-left"
                >
                  <svg
                    className={`w-4 h-4 text-stone-400 flex-shrink-0 transition-transform ${
                      isCollapsed ? '' : 'rotate-90'
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <span
                    className={`w-2 h-2 rounded-full flex-shrink-0 ${camera.is_active ? 'bg-green-500' : 'bg-stone-300'}`}
                  />
                  <h2 className="text-sm font-semibold text-stone-900 truncate">{camera.name}</h2>
                  {camera.location && (
                    <span className="text-xs text-stone-400 truncate">{camera.location}</span>
                  )}
                  <span className="text-xs text-stone-400 ml-auto flex-shrink-0">
                    {activeCount}/{taskCount} active
                  </span>
                </button>
                <button
                  onClick={() => {
                    setAddingFor(addingFor === camera.id ? null : camera.id);
                    setNewCommand('');
                    if (isCollapsed) toggleCollapse(camera.id);
                  }}
                  className="flex-shrink-0 flex items-center gap-1 text-xs px-2.5 py-1.5 text-white rounded-md transition-colors"
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

              {/* Collapsible body */}
              {!isCollapsed && (
                <>
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
                          {submitting ? 'Adding…' : 'Add'}
                        </button>
                        <button
                          type="button"
                          onClick={() => { setAddingFor(null); setNewCommand(''); }}
                          className="px-3 py-2 text-sm text-stone-500 hover:text-stone-900 transition-colors"
                        >
                          Cancel
                        </button>
                      </form>
                    </div>
                  )}

                  {loading ? (
                    <div className="px-5 py-6 flex justify-center">
                      <div className="w-5 h-5 border-2 border-stone-600 border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : tasks.length === 0 ? (
                    <div className="px-5 py-8 text-center">
                      <p className="text-sm text-stone-400">
                        {filter === 'all' ? 'No tasks assigned to this camera.' : `No ${filter} tasks.`}
                      </p>
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
                            <button
                              onClick={() => handleToggle(camera.id, task)}
                              className={`flex-shrink-0 w-9 h-5 rounded-full transition-colors relative ${
                                task.is_active ? 'bg-stone-700' : 'bg-stone-300'
                              }`}
                              aria-label={task.is_active ? 'Disable task' : 'Enable task'}
                            >
                              <span
                                className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                                  task.is_active ? 'left-4' : 'left-0.5'
                                }`}
                              />
                            </button>

                            <p className="flex-1 text-sm text-stone-900 min-w-0">{task.command}</p>

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
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TasksPage;
