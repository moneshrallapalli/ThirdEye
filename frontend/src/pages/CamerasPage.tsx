import React, { useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import LiveFeedGrid from '../components/LiveFeedGrid';

interface CamerasPageProps {
  onNavigateToTasks?: () => void;
}

const CamerasPage: React.FC<CamerasPageProps> = ({ onNavigateToTasks }) => {
  const { cameras, liveFeedData, handleCameraStart, handleCameraStop, handleCameraAdd, handleCameraDelete } = useSurveillance();
  const [cols, setCols] = useState<1 | 2 | 3>(2);

  const activeCameras = cameras.filter((c) => c.is_active).length;

  return (
    <div className="p-6 space-y-5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Live Cameras</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            {cameras.length} camera{cameras.length !== 1 ? 's' : ''}{activeCameras > 0 ? ` · ${activeCameras} active` : ''}
          </p>
        </div>

        {/* Grid size toggle */}
        {cameras.length > 0 && (
          <div className="flex items-center gap-1 bg-stone-100 rounded-md p-0.5">
            {([1, 2, 3] as const).map((n) => (
              <button
                key={n}
                onClick={() => setCols(n)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  cols === n ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'
                }`}
              >
                {n} col{n > 1 ? 's' : ''}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Camera grid */}
      <LiveFeedGrid
        cameras={cameras}
        liveFeedData={liveFeedData}
        cols={cols}
        onCameraStart={handleCameraStart}
        onCameraStop={handleCameraStop}
        onCameraAdd={handleCameraAdd}
        onCameraDelete={handleCameraDelete}
        onSelectCamera={onNavigateToTasks ? () => onNavigateToTasks() : undefined}
      />
    </div>
  );
};

export default CamerasPage;
