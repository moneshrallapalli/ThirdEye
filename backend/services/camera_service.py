"""
Camera Service - Manages camera connections and frame capture
"""
import cv2
import asyncio
import numpy as np
from typing import Optional, AsyncGenerator, Dict, Any
from datetime import datetime
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

    async def initialize_camera(
        self,
        camera_id: int,
        source: Any,
        fps: int = None,
        resolution: tuple = None
    ) -> bool:
        """
        Initialize a camera connection

        Args:
            camera_id: Camera ID
            source: Video source (URL, file path, or device index)
            fps: Target FPS (defaults to config)
            resolution: Target resolution (width, height)

        Returns:
            Success status
        """
        try:
            # Convert numeric strings to int so cv2 treats them as device
            # indices (e.g. "0" → 0) rather than file paths.
            if isinstance(source, str) and source.strip().lstrip('-').isdigit():
                source = int(source)

            # On macOS use AVFoundation backend for webcam indices to avoid
            # permission and access issues with the default backend.
            if isinstance(source, int):
                cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)
            else:
                cap = cv2.VideoCapture(source)

            if not cap.isOpened():
                return False

            # Set resolution if specified
            if resolution:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.VIDEO_RESOLUTION_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.VIDEO_RESOLUTION_HEIGHT)

            # Store camera
            self.active_cameras[camera_id] = cap
            self.camera_configs[camera_id] = {
                "source": source,
                "fps": fps or settings.CAMERA_FPS,
                "resolution": resolution or (settings.VIDEO_RESOLUTION_WIDTH, settings.VIDEO_RESOLUTION_HEIGHT),
                "initialized_at": datetime.utcnow()
            }

            return True

        except Exception as e:
            print(f"Error initializing camera {camera_id}: {e}")
            return False

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
