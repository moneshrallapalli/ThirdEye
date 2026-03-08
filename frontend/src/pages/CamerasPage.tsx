import React, { useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import LiveFeedGrid from '../components/LiveFeedGrid';

const CamerasPage: React.FC = () => {
  const { cameras, liveFeedData, handleCameraStart, handleCameraStop, handleCameraAdd, handleCameraDelete } = useSurveillance();
  const [cols, setCols] = useState<1 | 2 | 3>(2);

  const activeCameras = cameras.filter((c) => c.is_active).length;

  return (
    <div className="p-6 space-y-5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Live Cameras</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {cameras.length} camera{cameras.length !== 1 ? 's' : ''}{activeCameras > 0 ? ` · ${activeCameras} active` : ''}
          </p>
        </div>

        {/* Grid size toggle */}
        {cameras.length > 0 && (
          <div className="flex items-center gap-1 bg-gray-100 rounded-md p-0.5">
            {([1, 2, 3] as const).map((n) => (
              <button
                key={n}
                onClick={() => setCols(n)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  cols === n ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
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
      />
    </div>
  );
};

export default CamerasPage;
