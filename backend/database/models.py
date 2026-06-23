"""
Database models for SentinTinel Surveillance System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum


Base = declarative_base()


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    SYSTEM = "SYSTEM"


class DetectionStatus(str, enum.Enum):
    """Detection processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base):
    """User accounts for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=False)  # False until email verified
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class Camera(Base):
    """Camera configuration and metadata"""
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    stream_url = Column(String(512))
    is_active = Column(Boolean, default=True)
    fps = Column(Integer, default=2)
    resolution_width = Column(Integer, default=1280)
    resolution_height = Column(Integer, default=720)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="camera", cascade="all, delete-orphan")
    tasks = relationship("CameraTask", back_populates="camera", cascade="all, delete-orphan")


class Event(Base):
    """Surveillance events and incidents"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(100))
    description = Column(Text)
    scene_description = Column(Text)  # Gemini's scene analysis
    significance_score = Column(Integer, default=0)  # 0-100
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.INFO)
    event_metadata = Column(JSON)  # Additional event data
    embedding_id = Column(String(255), index=True)  # ChromaDB reference
    context_summary = Column(Text)  # Historical context from ChromaDB
    is_anomaly = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    camera = relationship("Camera", back_populates="events")
    detections = relationship("Detection", back_populates="event", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="event", cascade="all, delete-orphan")


class Detection(Base):
    """Object and person detections from Gemini"""
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    object_type = Column(String(100))  # person, vehicle, package, etc.
    object_label = Column(String(255))
    confidence_score = Column(Float)
    bounding_box = Column(JSON)  # {x, y, width, height}
    attributes = Column(JSON)  # color, size, characteristics
    tracking_id = Column(String(100), index=True)  # For object tracking over time
    status = Column(SQLEnum(DetectionStatus), default=DetectionStatus.PENDING)

    # Relationships
    event = relationship("Event", back_populates="detections")
    camera = relationship("Camera", back_populates="detections")


class Alert(Base):
    """Alert notifications generated from events"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    response_time_seconds = Column(Integer, nullable=True)
    alert_metadata = Column(JSON)

    # Relationships
    event = relationship("Event", back_populates="alerts")


class ContextPattern(Base):
    """Learned patterns and routines from historical data"""
    __tablename__ = "context_patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String(100))  # daily_routine, regular_visitor, unusual_time, etc.
    pattern_name = Column(String(255))
    description = Column(Text)
    confidence_score = Column(Float)
    frequency = Column(Integer, default=1)  # How often this pattern occurs
    time_range_start = Column(DateTime, nullable=True)
    time_range_end = Column(DateTime, nullable=True)
    pattern_metadata = Column(JSON)
    embedding_ids = Column(JSON)  # Related ChromaDB embeddings
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class CameraTask(Base):
    """Persistent monitoring tasks assigned to cameras"""
    __tablename__ = "camera_tasks"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    command = Column(Text, nullable=False)  # Detection target sent to vision/reasoning agents
    task_type = Column(String(100))  # fire_detection, intrusion_detection, custom, etc.
    is_default = Column(Boolean, default=False)  # True = auto-assigned from location preset
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # Higher = more important

    # Provenance. "manual" = set up from Cameras page; "ai_command" = issued
    # from the Intelligence → AI Command panel (broadcast across live cameras).
    source = Column(String(50), default="manual", nullable=False, index=True)
    # When `source == "ai_command"` we keep the user's original natural-language
    # instruction here so the UI can show what they typed even after the parser
    # has normalised it into a short detection target.
    original_command = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    camera = relationship("Camera", back_populates="tasks")


class SystemLog(Base):
    """System activity and performance logs"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    log_level = Column(String(20))  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component = Column(String(100))  # vision_agent, context_agent, api, etc.
    message = Column(Text)
    log_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
