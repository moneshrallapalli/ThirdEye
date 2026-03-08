import React, { useEffect, useRef } from 'react';
import { formatDistanceToNow } from 'date-fns';

interface NarrationEntry {
  id: string;
  timestamp: string;
  cameraId: number;
  description: string;
  significance: number;
  detections: number;
  context?: string;
}

interface SceneNarrationProps {
  narrations: NarrationEntry[];
}

const SceneNarration: React.FC<SceneNarrationProps> = ({ narrations }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narrations]);

  const significanceBadge = (score: number) => {
    if (score >= 80) return 'text-red-600 bg-red-50 border-red-200';
    if (score >= 50) return 'text-orange-600 bg-orange-50 border-orange-200';
    return 'text-blue-600 bg-blue-50 border-blue-200';
  };

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">Scene Analysis</h2>
        <span className="text-xs text-gray-400">{narrations.length} events</span>
      </div>

      <div ref={scrollRef} className="overflow-y-auto p-4 space-y-2" style={{ maxHeight: '320px' }}>
        {narrations.length === 0 ? (
          <div className="py-10 text-center">
            <svg className="w-8 h-8 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <p className="text-sm text-gray-400">Waiting for scene analysis...</p>
          </div>
        ) : (
          narrations.map((entry) => (
            <div key={entry.id} className="flex gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
              <div className="w-0.5 bg-blue-200 rounded-full flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-xs font-medium text-gray-700">Camera {entry.cameraId}</span>
                  <span className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                  </span>
                  <span className={`badge border ${significanceBadge(entry.significance)}`}>
                    {entry.significance}%
                  </span>
                </div>
                <p className="text-sm text-gray-700">{entry.description}</p>
                {entry.detections > 0 && (
                  <p className="text-xs text-gray-400 mt-1">
                    {entry.detections} object{entry.detections !== 1 ? 's' : ''} detected
                  </p>
                )}
                {entry.context && (
                  <details className="mt-1 text-xs">
                    <summary className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium">
                      View context
                    </summary>
                    <p className="mt-1 text-gray-500 pl-2 border-l border-gray-200">{entry.context}</p>
                  </details>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SceneNarration;
