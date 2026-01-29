/**
 * Real-time scene narration panel
 */
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
    // Auto-scroll to bottom when new narrations arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narrations]);

  const getSignificanceColor = (score: number): string => {
    if (score >= 80) return 'text-red-400';
    if (score >= 50) return 'text-orange-400';
    return 'text-blue-400';
  };

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            Live Scene Analysis
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">{narrations.length} events</span>
        </div>
      </div>
      <div className="card-body p-0">
        <div ref={scrollRef} className="max-h-96 overflow-y-auto p-4 space-y-3">
          {narrations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <p>Waiting for scene analysis...</p>
            </div>
          ) : (
            narrations.map((entry) => (
              <div
                key={entry.id}
                className="border-l-2 border-primary-600 pl-3 py-2 bg-dark-800/50 rounded-r animate-fade-in"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-primary-400">
                    Camera {entry.cameraId}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                  </span>
                  <span className={`text-xs font-semibold ${getSignificanceColor(entry.significance)}`}>
                    {entry.significance}%
                  </span>
                </div>
                <p className="text-sm text-gray-200 mb-1">{entry.description}</p>
                {entry.detections > 0 && (
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                    <span>{entry.detections} object{entry.detections !== 1 ? 's' : ''} detected</span>
                  </div>
                )}
                {entry.context && (
                  <details className="mt-2 text-xs">
                    <summary className="cursor-pointer text-cyan-400 hover:text-cyan-300">
                      View context
                    </summary>
                    <p className="mt-1 text-gray-400 pl-3 border-l border-dark-600">
                      {entry.context}
                    </p>
                  </details>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default SceneNarration;
