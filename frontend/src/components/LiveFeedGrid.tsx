/**
 * Live camera feed grid component with 4 cameras
 * Camera 0: Real active surveillance
 * Cameras 1-3: Dummy video playback
 */
import React, { useRef, useState, useEffect } from 'react';
import { Camera } from '../types';

interface LiveFeedGridProps {
  cameras: Camera[];
  liveFeedData: Map<number, { frame: string; timestamp: string }>;
  onCameraStart: (cameraId: number) => void;
  onCameraStop: (cameraId: number) => void;
}

const LiveFeedGrid: React.FC<LiveFeedGridProps> = ({
  cameras,
  liveFeedData,
  onCameraStart,
  onCameraStop
}) => {
  const videoRefs = useRef<{ [key: number]: HTMLVideoElement | null }>({});
  const [playingVideos, setPlayingVideos] = useState<Set<number>>(new Set());
  const [hasInteracted, setHasInteracted] = useState(false);

  // Dummy camera configuration
  const dummyCameras = [
    { id: 1, name: 'Camera 1 - Entrance', location: 'Front Door', videoPath: '/dummy_camera.mov' },
    { id: 2, name: 'Shoemaker', location: 'Workshop Area', videoPath: '/shoemaker.mov' },
    { id: 3, name: 'Parking', location: 'Parking Lot', videoPath: '/parking_video.mp4' }
  ];

  // Find camera 0 or create a default one
  const realCamera = cameras.find(cam => cam.id === 0) || {
    id: 0,
    name: 'Camera 0 - AI Surveillance',
    location: 'Monitor Zone',
    is_active: false,
    stream_url: ''
  };

  const allCameras = [realCamera, ...dummyCameras];

  // Start all videos on first user interaction (due to browser autoplay policy)
  useEffect(() => {
    const startAllVideos = () => {
      if (hasInteracted) return;

      setHasInteracted(true);
      dummyCameras.forEach((camera) => {
        const video = videoRefs.current[camera.id];
        if (video) {
          video.play()
            .then(() => {
              console.log(`Camera ${camera.id} started playing`);
            })
            .catch(err => {
              console.error(`Error playing camera ${camera.id}:`, err);
            });
        }
      });
    };

    // Listen for any user interaction
    const events = ['click', 'touchstart', 'keydown'];
    events.forEach(event => {
      document.addEventListener(event, startAllVideos, { once: true });
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, startAllVideos);
      });
    };
  }, [hasInteracted]);

  const handleDummyCameraClick = (cameraId: number) => {
    const video = videoRefs.current[cameraId];
    if (!video) return;

    if (playingVideos.has(cameraId)) {
      video.pause();
      setPlayingVideos(prev => {
        const newSet = new Set(prev);
        newSet.delete(cameraId);
        return newSet;
      });
    } else {
      video.play().catch(err => console.error('Error playing video:', err));
      setPlayingVideos(prev => new Set(prev).add(cameraId));
    }
  };

  const renderCameraCard = (camera: any, index: number) => {
    const isRealCamera = camera.id === 0;
    const isDummyCamera = camera.id >= 1 && camera.id <= 3;
    const feedData = liveFeedData.get(camera.id);
    const isPlaying = playingVideos.has(camera.id);

    return (
      <div key={camera.id} className="card group hover:border-cyan-500/30 transition-all duration-300">
        <div className="card-header flex items-center justify-between bg-gradient-to-r from-dark-800 to-dark-900">
          <div>
            <h3 className="font-semibold text-gray-100 flex items-center gap-2">
              <span className="text-lg">📹</span>
              {camera.name}
            </h3>
            <p className="text-xs text-gray-400">{camera.location}</p>
          </div>
          <div className="flex items-center gap-2">
            {isRealCamera && camera.is_active ? (
              <>
                <span className="flex items-center gap-1 text-xs text-green-400 font-semibold">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50"></span>
                  AI ACTIVE
                </span>
                <button
                  onClick={() => onCameraStop(camera.id)}
                  className="text-xs px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors shadow-lg hover:shadow-red-500/50"
                >
                  Stop
                </button>
              </>
            ) : isRealCamera && !camera.is_active ? (
              <button
                onClick={() => onCameraStart(camera.id)}
                className="text-xs px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors shadow-lg hover:shadow-green-500/50"
              >
                Start AI
              </button>
            ) : isDummyCamera ? (
              <span className="flex items-center gap-1 text-xs text-cyan-400 font-semibold">
                {isPlaying ? (
                  <>
                    <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/50"></span>
                    PLAYING
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 bg-gray-500 rounded-full"></span>
                    READY
                  </>
                )}
              </span>
            ) : null}
          </div>
        </div>

        <div className="card-body p-0">
          <div className="relative aspect-video bg-dark-900 overflow-hidden">
            {isRealCamera && feedData?.frame ? (
              <>
                <img
                  src={`data:image/jpeg;base64,${feedData.frame}`}
                  alt={`Feed from ${camera.name}`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    console.error(`Failed to load image for camera ${camera.id}`);
                  }}
                />
                <div className="absolute top-3 right-3 bg-gradient-to-r from-green-500 to-green-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                  AI LIVE
                </div>
              </>
            ) : isDummyCamera ? (
              <div
                className="relative w-full h-full cursor-pointer group/video"
                onClick={() => handleDummyCameraClick(camera.id)}
              >
                <video
                  ref={(el) => {
                    if (el) {
                      videoRefs.current[camera.id] = el;
                      // Set muted via JavaScript to ensure autoplay works
                      el.muted = true;
                      el.defaultMuted = true;
                    }
                  }}
                  src={camera.videoPath}
                  className="w-full h-full object-cover"
                  autoPlay
                  loop
                  muted
                  playsInline
                  onPlay={() => setPlayingVideos(prev => new Set(prev).add(camera.id))}
                  onPause={() => setPlayingVideos(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(camera.id);
                    return newSet;
                  })}
                />
                {/* Play/Pause overlay */}
                <div className="absolute inset-0 bg-black/30 opacity-0 group-hover/video:opacity-100 transition-opacity flex items-center justify-center">
                  <div className="bg-black/50 backdrop-blur-sm rounded-full p-4">
                    {isPlaying ? (
                      <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                      </svg>
                    ) : (
                      <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    )}
                  </div>
                </div>
                <div className="absolute top-3 right-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                  {isPlaying ? 'RECORDING' : 'PAUSED'}
                </div>
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-500">
                {isRealCamera && camera.is_active ? (
                  <div className="text-center">
                    <div className="animate-pulse mb-2">
                      <svg className="w-12 h-12 mx-auto text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <p className="mb-1 text-gray-300">Initializing AI surveillance...</p>
                    <p className="text-xs text-gray-600">Frames will appear shortly</p>
                  </div>
                ) : isRealCamera ? (
                  <div className="text-center">
                    <div className="bg-dark-800 rounded-full p-4 inline-block mb-3 border-2 border-dark-700">
                      <svg className="w-10 h-10 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <p className="text-gray-300 font-medium">AI Camera Ready</p>
                    <p className="text-xs text-gray-600 mt-1">Click "Start AI" to begin monitoring</p>
                  </div>
                ) : null}
              </div>
            )}

            {feedData?.timestamp && isRealCamera && (
              <div className="absolute bottom-3 left-3 bg-dark-900/90 backdrop-blur-sm px-3 py-1.5 rounded-lg text-xs text-gray-300 border border-dark-700">
                🕐 {new Date(feedData.timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
            <span className="text-2xl">📹</span>
            Live Camera Feeds
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Monitor all camera feeds in real-time
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-2 bg-dark-800 rounded-lg border border-dark-700">
            <span className="text-xs text-gray-400">Active:</span>
            <span className="ml-2 text-sm font-semibold text-cyan-400">{realCamera.is_active ? 1 : 0} / 4</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {allCameras.map((camera, index) => renderCameraCard(camera, index))}
      </div>
    </div>
  );
};

export default LiveFeedGrid;
