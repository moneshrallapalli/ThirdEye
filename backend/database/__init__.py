"""
Database package initialization
"""
from .models import (
    Base,
    User,
    Camera,
    CameraTask,
    Event,
    Detection,
    Alert,
    ContextPattern,
    SystemLog,
    AlertSeverity,
    DetectionStatus
)
from .database import get_db, init_db, engine, SessionLocal

__all__ = [
    "Base",
    "User",
    "Camera",
    "CameraTask",
    "Event",
    "Detection",
    "Alert",
    "ContextPattern",
    "SystemLog",
    "AlertSeverity",
    "DetectionStatus",
    "get_db",
    "init_db",
    "engine",
    "SessionLocal"
]
