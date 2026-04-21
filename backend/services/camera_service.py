"""
Camera Service - Manages camera connections and frame capture
"""
import cv2
import asyncio
import numpy as np
from typing import Optional, AsyncGenerator, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class CameraService:
    """
    Manages camera connections and video streaming
    """

    def __init__(self):
        self.active_cameras: Dict[int, cv2.VideoCapture] = {}
        self.camera_configs: Dict[int, Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _open_capture(self, source: Any) -> cv2.VideoCapture:
        """Blocking call — runs in thread pool."""
        if isinstance(source, int):
            cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)
        else:
            # For RTSP/network streams, set a transport preference and
            # shorter timeout via environment so OpenCV doesn't hang.
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        return cap

    async def initialize_camera(
        self,
        camera_id: int,
        source: Any,
        fps: int = None,
        resolution: tuple = None
    ) -> bool:
        """
        Initialize a camera connection.

        Runs the blocking cv2.VideoCapture in a thread to avoid stalling
        the event loop, with a 15-second timeout for network streams.
        """
        try:
            # Convert numeric strings to int for device indices.
            if isinstance(source, str) and source.strip().lstrip('-').isdigit():
                source = int(source)

            loop = asyncio.get_event_loop()
            timeout = 15 if isinstance(source, str) else 10

            try:
                cap = await asyncio.wait_for(
                    loop.run_in_executor(self._executor, self._open_capture, source),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.error(f"[CAM-{camera_id}] Timed out connecting to {source} after {timeout}s")
                raise RuntimeError(f"Connection timed out after {timeout}s")

            if not cap.isOpened():
                # Try reading one frame to surface the real error
                # (OpenCV often logs the reason to stderr)
                cap.release()
                logger.error(f"[CAM-{camera_id}] Failed to open source: {source}")
                raise RuntimeError(f"Could not open video source: {source}")

            # Verify we can actually read a frame.
            # On macOS the sensor often needs a few warm-up reads before it
            # returns valid data, so retry up to 10 times with a short delay.
            ret = False
            for attempt in range(10):
                ret, _ = cap.read()
                if ret:
                    break
                await asyncio.sleep(0.3)
            if not ret:
                cap.release()
                logger.error(f"[CAM-{camera_id}] Source opened but cannot read frames: {source}")
                raise RuntimeError(f"Source opened but cannot read frames (check credentials or stream status)")

            # Set resolution
            if resolution:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.VIDEO_RESOLUTION_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.VIDEO_RESOLUTION_HEIGHT)

            self.active_cameras[camera_id] = cap
            self.camera_configs[camera_id] = {
                "source": source,
                "fps": fps or settings.CAMERA_FPS,
                "resolution": resolution or (settings.VIDEO_RESOLUTION_WIDTH, settings.VIDEO_RESOLUTION_HEIGHT),
                "initialized_at": datetime.utcnow()
            }

            logger.info(f"[CAM-{camera_id}] Initialized: {source}")
            return True

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[CAM-{camera_id}] Error initializing: {e}")
            raise RuntimeError(f"Camera initialization failed: {e}")

    async def capture_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera

        Args:
            camera_id: Camera ID

        Returns:
            Frame as numpy array or None
        """
        if camera_id not in self.active_cameras:
            return None

        cap = self.active_cameras[camera_id]

        try:
            ret, frame = cap.read()
            if ret:
                return frame
            return None
        except Exception as e:
            print(f"Error capturing frame from camera {camera_id}: {e}")
            return None

    async def stream_frames(
        self,
        camera_id: int,
        fps: int = None
    ) -> AsyncGenerator[np.ndarray, None]:
        """
        Stream frames from camera at specified FPS

        Args:
            camera_id: Camera ID
            fps: Frames per second (defaults to camera config)

        Yields:
            Video frames
        """
        if camera_id not in self.active_cameras:
            return

        target_fps = fps or self.camera_configs[camera_id].get('fps', settings.CAMERA_FPS)
        frame_interval = 1.0 / target_fps

        while camera_id in self.active_cameras:
            frame = await self.capture_frame(camera_id)

            if frame is not None:
                yield frame

            await asyncio.sleep(frame_interval)

    async def get_camera_info(self, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        Get camera information

        Args:
            camera_id: Camera ID

        Returns:
            Camera info dictionary
        """
        if camera_id not in self.active_cameras:
            return None

        cap = self.active_cameras[camera_id]
        config = self.camera_configs[camera_id]

        return {
            "camera_id": camera_id,
            "is_active": cap.isOpened(),
            "fps": config['fps'],
            "resolution": {
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            },
            "source": config['source'],
            "initialized_at": config['initialized_at'].isoformat()
        }

    async def stop_camera(self, camera_id: int) -> bool:
        """
        Stop and release camera

        Args:
            camera_id: Camera ID

        Returns:
            Success status
        """
        if camera_id not in self.active_cameras:
            return False

        try:
            self.active_cameras[camera_id].release()
            del self.active_cameras[camera_id]
            del self.camera_configs[camera_id]
            return True
        except Exception as e:
            print(f"Error stopping camera {camera_id}: {e}")
            return False

    async def stop_all_cameras(self):
        """
        Stop all active cameras
        """
        camera_ids = list(self.active_cameras.keys())
        for camera_id in camera_ids:
            await self.stop_camera(camera_id)

    def get_active_camera_count(self) -> int:
        """
        Get number of active cameras

        Returns:
            Number of active cameras
        """
        return len(self.active_cameras)

    async def test_camera_source(self, source: Any) -> bool:
        """
        Test if a camera source is accessible

        Args:
            source: Video source

        Returns:
            True if accessible
        """
        try:
            cap = cv2.VideoCapture(source)
            is_open = cap.isOpened()
            cap.release()
            return is_open
        except:
            return False


# Global camera service instance
camera_service = CameraService()
