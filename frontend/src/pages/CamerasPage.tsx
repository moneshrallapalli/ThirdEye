import React, { useMemo, useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import LiveFeedGrid from '../components/LiveFeedGrid';
import AskAIDrawer from '../components/AskAIDrawer';

interface CamerasPageProps {
  onNavigateToTasks?: () => void;
}

type View = 'grid' | 'list';
type StatusFilter = 'all' | 'active' | 'offline';

const CamerasPage: React.FC<CamerasPageProps> = ({ onNavigateToTasks }) => {
  const {
    cameras,
    liveFeedData,
    handleCameraStart,
    handleCameraStop,
    handleCameraAdd,
    handleCameraDelete,
  } = useSurveillance();

  const [view, setView] = useState<View>('grid');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [askCameraId, setAskCameraId] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const activeCount = cameras.filter((c) => c.is_active).length;
  const offlineCount = cameras.length - activeCount;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return cameras.filter((c) => {
      if (statusFilter === 'active' && !c.is_active) return false;
      if (statusFilter === 'offline' && c.is_active) return false;
      if (!q) return true;
      return (
        c.name.toLowerCase().includes(q) ||
        (c.location || '').toLowerCase().includes(q) ||
        (c.stream_url || '').toLowerCase().includes(q)
      );
    });
  }, [cameras, search, statusFilter]);

  const askCamera = askCameraId !== null ? cameras.find((c) => c.id === askCameraId) ?? null : null;
  const askLiveFrame = askCamera ? liveFeedData.get(askCamera.id)?.frame : undefined;

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Cameras</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            {cameras.length} registered
            {activeCount > 0 && (
              <>
                {' · '}
                <span className="text-green-700">{activeCount} active</span>
              </>
            )}
            {offlineCount > 0 && (
              <>
                {' · '}
                <span>{offlineCount} offline</span>
              </>
            )}
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-1.5 px-3 py-2 bg-stone-900 hover:bg-stone-800 text-white text-sm font-medium rounded-md transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add camera
        </button>
      </div>

      {/* Toolbar: search + filters + view toggle */}
      {cameras.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
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
              placeholder="Search cameras, locations…"
              className="input pl-9 py-1.5"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-stone-400 hover:text-stone-700 rounded"
                aria-label="Clear search"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Status filter chips */}
          <div className="flex items-center gap-1 bg-white border border-stone-200 rounded-md p-0.5">
            {([
              { id: 'all' as StatusFilter, label: 'All', count: cameras.length },
              { id: 'active' as StatusFilter, label: 'Active', count: activeCount },
              { id: 'offline' as StatusFilter, label: 'Offline', count: offlineCount },
            ]).map((f) => (
              <button
                key={f.id}
                onClick={() => setStatusFilter(f.id)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  statusFilter === f.id
                    ? 'bg-stone-900 text-white'
                    : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50'
                }`}
              >
                {f.label}
                <span className={`ml-1 text-[10px] ${statusFilter === f.id ? 'text-stone-300' : 'text-stone-400'}`}>
                  {f.count}
                </span>
              </button>
            ))}
          </div>

          {/* View toggle (Grid/List) */}
          <div className="flex items-center ml-auto bg-white border border-stone-200 rounded-md p-0.5">
            <button
              onClick={() => setView('grid')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                view === 'grid' ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'
              }`}
              title="Grid view"
              aria-pressed={view === 'grid'}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
              </svg>
              Grid
            </button>
            <button
              onClick={() => setView('list')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                view === 'list' ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'
              }`}
              title="List view"
              aria-pressed={view === 'list'}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
              List
            </button>
          </div>
        </div>
      )}

      {/* Empty search result */}
      {cameras.length > 0 && filtered.length === 0 && (
        <div className="bg-white border border-stone-200 rounded-lg py-16 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-stone-100 rounded-full mb-3">
            <svg className="w-5 h-5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-stone-900 mb-1">No matches</p>
          <p className="text-sm text-stone-400">
            {search ? `No cameras match "${search}"` : 'No cameras match this filter'}
          </p>
          <button
            onClick={() => {
              setSearch('');
              setStatusFilter('all');
            }}
            className="mt-3 text-xs text-stone-700 hover:text-stone-900 font-medium"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Camera display */}
      {(cameras.length === 0 || filtered.length > 0) && (
        <LiveFeedGrid
          cameras={filtered.length > 0 ? filtered : cameras}
          liveFeedData={liveFeedData}
          view={view}
          onCameraStart={handleCameraStart}
          onCameraStop={handleCameraStop}
          onCameraAdd={handleCameraAdd}
          onCameraDelete={handleCameraDelete}
          onOpenAskAI={(cameraId) => setAskCameraId(cameraId)}
          onManageTasks={onNavigateToTasks ? () => onNavigateToTasks() : undefined}
          onRequestAdd={() => setShowAddModal(true)}
          showAddModal={showAddModal}
          onCloseAddModal={() => setShowAddModal(false)}
        />
      )}

      {/* Ask AI Drawer */}
      {askCamera && (
        <AskAIDrawer
          camera={askCamera}
          liveFrame={askLiveFrame}
          onClose={() => setAskCameraId(null)}
        />
      )}
    </div>
  );
};

export default CamerasPage;
