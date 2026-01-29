"""
API routes for SentinTinel Surveillance System
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger
import base64
import cv2
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, Camera, Event, Detection, Alert, ContextPattern, AlertSeverity
from api.websocket import manager
from agents import VisionAgent, ContextAgent
from services import camera_service
from config import settings

# Create routers
router = APIRouter()
ws_router = APIRouter()

# Initialize local agents
vision_agent = VisionAgent()
context_agent = ContextAgent()

# Get shared command_agent from main (will be set after main.py initializes it)
def get_command_agent():
    """Get the shared command_agent instance"""
    import main
    return main.command_agent

command_agent = None  # Will be lazy-loaded when needed


# WebSocket endpoints
@ws_router.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    """
    WebSocket endpoint for live video feed and analysis
    """
    await manager.connect(websocket, "live_feed")

    try:
        while True:
            # Receive messages from client (e.g., camera selection)
            data = await websocket.receive_json()

            # Handle client requests
            if data.get("action") == "start_camera":
                camera_id = data.get("camera_id")
                # Client will receive updates via broadcast

            elif data.get("action") == "stop_camera":
                camera_id = data.get("camera_id")
                # Handle camera stop

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@ws_router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts
    """
    await manager.connect(websocket, "alerts")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@ws_router.websocket("/ws/analysis")
async def websocket_analysis(websocket: WebSocket):
    """
    WebSocket endpoint for scene analysis/narration
    """
    await manager.connect(websocket, "analysis")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@ws_router.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    """
    WebSocket endpoint for system messages and commands
    """
    await manager.connect(websocket, "system")

    try:
        while True:
            data = await websocket.receive_json()

            # Handle system commands
            if data.get("command"):
                await handle_system_command(data["command"], data.get("params", {}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# REST API endpoints
@router.get("/cameras")
async def get_cameras(db: Session = Depends(get_db)):
    """
    Get all cameras
    """
    try:
        cameras = db.query(Camera).all()
        return cameras
    except Exception as e:
        # If database is not available, return empty list or active cameras from service
        from loguru import logger
        logger.warning(f"Database not available for /cameras endpoint: {e}")
        # Return minimal camera info from camera service if any are active
        active_cameras = []
        for cam_id in camera_service.active_cameras.keys():
            active_cameras.append({
                "id": cam_id,
                "name": f"Camera {cam_id}",
                "location": "Unknown",
                "stream_url": str(cam_id),
                "is_active": True,
                "fps": 2
            })
        return active_cameras


@router.post("/cameras")
async def create_camera(
    name: str,
    location: str,
    stream_url: str,
    db: Session = Depends(get_db)
):
    """
    Create a new camera
    """
    camera = Camera(
        name=name,
        location=location,
        stream_url=stream_url,
        is_active=True
    )

    db.add(camera)
    db.commit()
    db.refresh(camera)

    return camera


@router.post("/cameras/{camera_id}/start")
async def start_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Start a camera feed
    """
    camera = None
    fps = 2
    stream_url = camera_id

    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()

        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        fps = camera.fps
        stream_url = camera.stream_url or camera_id

    except HTTPException:
        raise
    except Exception as e:
        # If database is not available, try to start camera directly
        from loguru import logger
        logger.warning(f"Database not available, starting camera {camera_id} directly: {e}")

    # Initialize camera (works with or without database)
    success = await camera_service.initialize_camera(
        camera_id,
        stream_url,
        fps=fps
    )

    if success:
        # Update database if available
        if camera is not None:
            try:
                camera.is_active = True
                db.commit()
            except:
                pass  # DB update failed, but camera started
        return {"status": "started", "camera_id": camera_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to start camera")


@router.post("/cameras/{camera_id}/stop")
async def stop_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Stop a camera feed
    """
    camera = None

    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()

        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
    except HTTPException:
        raise
    except Exception as e:
        # If database is not available, proceed with stopping
        from loguru import logger
        logger.warning(f"Database not available, stopping camera {camera_id} directly: {e}")

    # Stop camera (works with or without database)
    await camera_service.stop_camera(camera_id)

    # Update database if available
    if camera is not None:
        try:
            camera.is_active = False
            db.commit()
        except:
            pass  # DB update failed, but camera stopped

    return {"status": "stopped", "camera_id": camera_id}


@router.get("/events")
async def get_events(
    camera_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    severity: Optional[AlertSeverity] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get events with filtering
    """
    query = db.query(Event)

    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    if start_date:
        query = query.filter(Event.timestamp >= start_date)
    if end_date:
        query = query.filter(Event.timestamp <= end_date)
    if severity:
        query = query.filter(Event.severity == severity)

    events = query.order_by(Event.timestamp.desc()).limit(limit).all()
    return events


@router.get("/alerts")
async def get_alerts(
    is_read: Optional[bool] = None,
    severity: Optional[AlertSeverity] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get alerts with filtering
    """
    try:
        query = db.query(Alert)

        if is_read is not None:
            query = query.filter(Alert.is_read == is_read)
        if severity:
            query = query.filter(Alert.severity == severity)

        alerts = query.order_by(Alert.timestamp.desc()).limit(limit).all()
        return alerts
    except Exception as e:
        from loguru import logger
        logger.warning(f"Database not available for alerts: {e}")
        return []  # Return empty list if database not available


@router.get("/alerts/recent-events")
async def get_recent_events_with_images(
    min_significance: int = 60,
    hours: int = 24,
    limit: int = 20
):
    """
    Get recent significant events with supporting images from event_frames folder
    Returns events with significance >= min_significance
    """
    from pathlib import Path
    import os
    from datetime import timedelta
    
    try:
        # Get event frames directory
        event_frames_dir = Path(__file__).parent.parent / "event_frames"
        
        if not event_frames_dir.exists():
            return {"events": [], "message": "No event frames directory"}
        
        # Get all frame files sorted by modification time (newest first)
        frame_files = sorted(
            event_frames_dir.glob("camera*.jpg"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Filter frames from last N hours
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_frames = [
            f for f in frame_files
            if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff_time
        ][:limit]
        
        # Build event summaries
        events = []
        for frame_file in recent_frames:
            frame_name = frame_file.name
            frame_url = f"/event_frames/{frame_name}"
            
            # Extract timestamp from filename (camera0_20251116_073346_551497.jpg)
            try:
                parts = frame_name.replace('.jpg', '').split('_')
                if len(parts) >= 4:
                    date_str = parts[1]  # 20251116
                    time_str = parts[2]  # 073346
                    
                    # Parse timestamp
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])
                    
                    event_time = datetime(year, month, day, hour, minute, second)
                    timestamp = event_time.isoformat()
                else:
                    timestamp = datetime.fromtimestamp(frame_file.stat().st_mtime).isoformat()
            except:
                timestamp = datetime.fromtimestamp(frame_file.stat().st_mtime).isoformat()
            
            # Check if significance is in filename
            significance = 65  # Default for events that triggered save
            if '_sig' in frame_name:
                try:
                    sig_part = frame_name.split('_sig')[1].replace('.jpg', '')
                    significance = int(sig_part)
                except:
                    pass
            
            # Only include if meets significance threshold
            if significance >= min_significance:
                event = {
                    "id": frame_name.replace('.jpg', ''),
                    "timestamp": timestamp,
                    "camera_id": 0,
                    "frame_url": frame_url,
                    "frame_path": str(frame_file),
                    "significance": significance,
                    "severity": "CRITICAL" if significance >= 80 else "WARNING" if significance >= 70 else "INFO",
                    "title": f"Event Detected - Significance {significance}%",
                    "summary": f"Significant event captured at {timestamp}",
                    "file_size": frame_file.stat().st_size,
                    "is_read": False
                }
                events.append(event)
        
        return {
            "events": events,
            "count": len(events),
            "min_significance": min_significance,
            "hours": hours,
            "message": f"Found {len(events)} significant events (>={min_significance}% confidence)"
        }
        
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting recent events: {e}")
        return {"events": [], "error": str(e)}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Acknowledge an alert
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    alert.acknowledged_at = datetime.utcnow()

    if alert.event:
        response_time = (alert.acknowledged_at - alert.event.timestamp).total_seconds()
        alert.response_time_seconds = int(response_time)

    db.commit()

    return alert


@router.get("/stats/summary")
async def get_summary_stats(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics
    """
    try:
        since = datetime.utcnow() - timedelta(hours=hours)

        total_events = db.query(Event).filter(Event.timestamp >= since).count()
        critical_alerts = db.query(Alert).filter(
            Alert.timestamp >= since,
            Alert.severity == AlertSeverity.CRITICAL
        ).count()
        warning_alerts = db.query(Alert).filter(
            Alert.timestamp >= since,
            Alert.severity == AlertSeverity.WARNING
        ).count()

        # Average response time
        acknowledged_alerts = db.query(Alert).filter(
            Alert.timestamp >= since,
            Alert.acknowledged_at.isnot(None)
        ).all()

        avg_response_time = 0
        if acknowledged_alerts:
            total_response = sum(a.response_time_seconds for a in acknowledged_alerts if a.response_time_seconds)
            avg_response_time = total_response / len(acknowledged_alerts) if acknowledged_alerts else 0

        # Get ChromaDB stats
        chroma_stats = context_agent.get_statistics()

        return {
            "period_hours": hours,
            "total_events": total_events,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "info_alerts": total_events - critical_alerts - warning_alerts,
            "avg_response_time_seconds": int(avg_response_time),
            "active_cameras": camera_service.get_active_camera_count(),
            "context_stats": chroma_stats
        }
    except Exception as e:
        # If database is not available, return minimal stats
        from loguru import logger
        logger.warning(f"Database not available for stats, returning minimal data: {e}")
        return {
            "period_hours": hours,
            "total_events": 0,
            "critical_alerts": 0,
            "warning_alerts": 0,
            "info_alerts": 0,
            "avg_response_time_seconds": 0,
            "active_cameras": camera_service.get_active_camera_count(),
            "context_stats": context_agent.get_statistics()
        }


@router.get("/patterns")
async def get_patterns(
    camera_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get identified patterns
    """
    query = db.query(ContextPattern).filter(ContextPattern.is_active == True)

    patterns_db = query.order_by(ContextPattern.frequency.desc()).limit(20).all()

    # Also get patterns from context agent
    patterns_chroma = await context_agent.identify_patterns(camera_id=camera_id)

    return {
        "database_patterns": patterns_db,
        "detected_patterns": patterns_chroma
    }


@router.get("/system/health")
async def health_check():
    """
    System health check
    """
    connection_stats = manager.get_connection_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "websocket_connections": connection_stats,
        "active_cameras": camera_service.get_active_camera_count(),
        "version": "1.0.0"
    }


@router.post("/system/command")
async def process_command_endpoint(command: dict):
    """
    Process a natural language command
    
    Request body:
    {
        "command": "watch for people entering the building",
        "params": {}
    }
    """
    try:
        command_text = command.get("command", "")
        params = command.get("params", {})
        
        if not command_text:
            raise HTTPException(status_code=400, detail="Command text is required")
        
        logger.info(f"[COMMAND API] Received command: {command_text}")
        
        # Process the command
        await process_user_command(command_text, params)
        
        return {
            "status": "processing",
            "command": command_text,
            "message": "Command received and being processed"
        }
    except Exception as e:
        logger.error(f"[COMMAND API] Error processing command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/send-alert")
async def send_test_alert():
    """
    Send a test alert with supporting image for demonstration
    """
    from pathlib import Path
    import base64
    
    try:
        # Get the most recent frame
        event_frames_dir = Path(__file__).parent.parent / "event_frames"
        frame_files = sorted(
            event_frames_dir.glob("camera*.jpg"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not frame_files:
            raise HTTPException(status_code=404, detail="No frames available")
        
        latest_frame = frame_files[0]
        frame_url = f"/event_frames/{latest_frame.name}"
        
        # Read and encode frame
        with open(latest_frame, 'rb') as f:
            frame_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Create test alert
        alert_data = {
            "id": f"test_alert_{int(datetime.utcnow().timestamp())}",
            "severity": "WARNING",
            "title": "🎯 Test Alert - Object Detection Demo",
            "message": """**Event Detected** (Confidence: 75%)

**Scene:** Test detection event - system is monitoring successfully

**Activity:** Continuous monitoring active

**Objects Detected:** Testing alert system with supporting images

**Time:** """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + """
**Camera:** 0
**Context:** This is a test alert to demonstrate the image display feature""",
            "camera_id": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "significance": 75,
            "frame_url": frame_url,
            "frame_path": str(latest_frame),
            "frame_base64": frame_base64,
            "detected_objects": ["test object", "camera", "surveillance"],
            "is_read": False
        }
        
        # Send via WebSocket
        await manager.send_alert(alert_data)
        logger.info(f"[TEST] Test alert sent with image: {frame_url}")
        
        return {
            "status": "success",
            "message": "Test alert sent with supporting image",
            "alert": alert_data
        }
        
    except Exception as e:
        logger.error(f"[TEST] Error sending test alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def handle_system_command(command: str, params: dict):
    """
    Handle system commands from WebSocket
    """
    if command == "get_stats":
        stats = manager.get_connection_stats()
        await manager.send_system_message("stats_response", stats)

    elif command == "test_alert":
        await manager.send_alert({
            "severity": "INFO",
            "title": "Test Alert",
            "message": "This is a test alert",
            "camera_id": params.get("camera_id", 1)
        })

    else:
        # Process as natural language command with Gemini
        await process_user_command(command, params)


async def process_user_command(command: str, params: dict):
    """
    Process natural language user command with Gemini

    Args:
        command: User's natural language command
        params: Additional parameters
    """
    try:
        # Get current context
        active_camera_ids = list(camera_service.active_cameras.keys())
        context = {
            "active_cameras": active_camera_ids,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Process command with CommandAgent (use shared instance from main)
        import main
        result = await main.command_agent.process_command(command, context)

        # Send confirmation to user
        await manager.send_system_message("command_processed", {
            "original_command": command,
            "task_id": result.get('task_id'),
            "task_type": result.get('task_type'),
            "confirmation": result.get('confirmation'),
            "understood_intent": result.get('understood_intent'),
            "parameters": result.get('parameters')
        })

        # Execute task based on type
        task_type = result.get('task_type')

        if task_type in ['object_detection', 'activity_detection', 'state_change_detection', 'surveillance', 'scene_analysis', 'anomaly_detection', 'tracking']:
            # Start monitoring task
            await start_monitoring_task(result)

        elif task_type == 'alert':
            # Create immediate alert
            await manager.send_alert({
                "severity": "INFO",
                "title": "Command Alert",
                "message": result.get('confirmation'),
                "camera_id": params.get("camera_id", 1)
            })

    except Exception as e:
        await manager.send_system_message("command_error", {
            "error": str(e),
            "message": f"Failed to process command: {str(e)}"
        })


async def start_monitoring_task(task_command: dict):
    """
    Start a monitoring task based on parsed command

    Args:
        task_command: Parsed command from CommandAgent
    """
    task_id = task_command.get('task_id')
    camera_ids = task_command.get('parameters', {}).get('camera_ids', ['all'])

    # Auto-start camera 0 (webcam) if no cameras are active
    if camera_service.get_active_camera_count() == 0:
        logger.info("[CAMERA] No cameras active, auto-starting camera 0 (webcam)")
        try:
            # Initialize camera 0 (default webcam) with lower resolution for speed
            success = await camera_service.initialize_camera(
                camera_id=0,
                source=0,  # Default webcam
                fps=1,  # Lower FPS for faster processing
                resolution=(640, 480)  # Lower resolution for faster processing
            )
            if success:
                logger.info("[CAMERA] ✓ Camera 0 started successfully")
                await manager.send_system_message("camera_started", {
                    "camera_id": 0,
                    "status": "success",
                    "message": "Camera 0 auto-started for monitoring"
                })
            else:
                logger.error("[CAMERA] ✗ Failed to start camera 0 - Check permissions!")
                await manager.send_system_message("camera_error", {
                    "camera_id": 0,
                    "status": "failed",
                    "message": "⚠️ Failed to start camera. Please check:\n1. Camera permissions in System Settings\n2. No other app is using the camera\n3. Try using a video file instead: upload a video for testing",
                    "permission_help": {
                        "macos": "Go to System Settings → Privacy & Security → Camera → Enable for Terminal/Python",
                        "alternative": "You can test with a video file: use /api/video/query-scene endpoint"
                    }
                })
                # Don't return - continue with no active cameras for now
        except Exception as e:
            logger.error(f"[CAMERA] Exception starting camera 0: {e}")
            await manager.send_system_message("camera_error", {
                "camera_id": 0,
                "status": "error",
                "message": f"Camera error: {str(e)}. You can test with video files instead.",
                "error_details": str(e)
            })
            # Don't return - continue with no active cameras

    # Determine which cameras to monitor
    if camera_ids == ['all'] or 'all' in camera_ids:
        target_cameras = list(camera_service.active_cameras.keys())
    else:
        target_cameras = [int(cid) for cid in camera_ids if isinstance(cid, (int, str))]

    # Send status update
    await manager.send_system_message("task_started", {
        "task_id": task_id,
        "task_type": task_command.get('task_type'),
        "target": task_command.get('target'),
        "cameras": target_cameras,
        "message": f"Started monitoring on {len(target_cameras)} camera(s) for: {task_command.get('target')}"
    })


@router.post("/test/camera/init")
async def test_init_camera(camera_id: int = 0, source: int = 0):
    """
    Test endpoint to initialize a camera without database
    Useful for testing with webcam
    """
    try:
        success = await camera_service.initialize_camera(
            camera_id=camera_id,
            source=source,
            fps=2,
            resolution=(1280, 720)
        )

        if success:
            # Get camera info
            info = await camera_service.get_camera_info(camera_id)
            return {
                "status": "success",
                "message": f"Camera {camera_id} initialized successfully",
                "camera_info": info,
                "active_cameras": camera_service.get_active_camera_count()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize camera")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/camera/stop")
async def test_stop_camera(camera_id: int = 0):
    """
    Test endpoint to stop a camera without database
    """
    try:
        success = await camera_service.stop_camera(camera_id)

        if success:
            return {
                "status": "success",
                "message": f"Camera {camera_id} stopped successfully",
                "active_cameras": camera_service.get_active_camera_count()
            }
        else:
            raise HTTPException(status_code=404, detail="Camera not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/camera/status")
async def test_camera_status():
    """
    Test endpoint to check camera status without database
    """
    try:
        active_count = camera_service.get_active_camera_count()
        active_cameras = list(camera_service.active_cameras.keys())

        camera_infos = []
        for cam_id in active_cameras:
            info = await camera_service.get_camera_info(cam_id)
            if info:
                camera_infos.append(info)

        return {
            "status": "success",
            "active_count": active_count,
            "active_camera_ids": active_cameras,
            "cameras": camera_infos
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Video Timestamp Analysis Endpoints
from pydantic import BaseModel

class VideoSceneQueryRequest(BaseModel):
    """Request model for video scene query"""
    video_file_path: str
    scene_query: str
    camera_id: Optional[int] = None
    fps: Optional[int] = None


class VideoTimelineRequest(BaseModel):
    """Request model for video timeline analysis"""
    video_file_path: str
    camera_id: Optional[int] = None
    fps: Optional[int] = 1


@router.post("/video/query-scene")
async def query_scene_in_video(request: VideoSceneQueryRequest):
    """
    Query for specific scenes in a video and get timestamps when they occur

    This endpoint allows you to ask questions like:
    - "when does a person wearing red appear?"
    - "when does someone enter through the door?"
    - "when is there a vehicle in the frame?"

    The API will return timestamps (MM:SS format) for when the queried scene occurs.

    Example request:
    ```json
    {
        "video_file_path": "/path/to/video.mp4",
        "scene_query": "when does a person wearing red clothing appear?",
        "camera_id": 1,
        "fps": 2
    }
    ```

    Example response:
    ```json
    {
        "found": true,
        "timestamps": ["00:15", "01:23", "02:45"],
        "descriptions": [
            {
                "timestamp": "00:15",
                "description": "Person in red shirt enters from left",
                "confidence": 0.95,
                "key_details": ["red shirt", "entering", "carrying bag"]
            }
        ],
        "summary": "Person in red clothing appears 3 times in the video"
    }
    ```
    """
    try:
        result = await vision_agent.query_scene_in_video(
            video_file_path=request.video_file_path,
            scene_query=request.scene_query,
            camera_id=request.camera_id,
            fps=request.fps
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/timeline")
async def analyze_video_timeline(request: VideoTimelineRequest):
    """
    Analyze a complete video file and get a timeline of events with timestamps

    This endpoint provides a comprehensive timeline of all significant events
    in a surveillance video, including timestamps for each event.

    Example request:
    ```json
    {
        "video_file_path": "/path/to/surveillance.mp4",
        "camera_id": 1,
        "fps": 2
    }
    ```

    Example response:
    ```json
    {
        "events": [
            {
                "timestamp": "00:00",
                "event_type": "person_detected",
                "description": "Person enters frame from left",
                "significance": 60,
                "detections": ["person"]
            },
            {
                "timestamp": "00:45",
                "event_type": "vehicle_detected",
                "description": "Car parks in view",
                "significance": 75,
                "detections": ["vehicle", "person"]
            }
        ],
        "summary": "Video shows normal activity with 3 people and 2 vehicles",
        "total_duration": "05:30",
        "key_moments": ["00:45", "02:15", "04:30"]
    }
    ```
    """
    try:
        result = await vision_agent.analyze_video_with_timestamps(
            video_file_path=request.video_file_path,
            camera_id=request.camera_id,
            fps=request.fps
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/capabilities")
async def video_analysis_capabilities():
    """
    Get information about video analysis capabilities

    Returns documentation about how to use video timestamp features
    """
    return {
        "video_timestamp_support": True,
        "capabilities": {
            "scene_query": {
                "description": "Query for specific scenes and get timestamps",
                "endpoint": "/api/video/query-scene",
                "method": "POST",
                "example_queries": [
                    "when does a person wearing red appear?",
                    "when does someone enter through the door?",
                    "when is there a vehicle in the frame?",
                    "when does suspicious activity occur?"
                ]
            },
            "timeline_analysis": {
                "description": "Get complete timeline of events with timestamps",
                "endpoint": "/api/video/timeline",
                "method": "POST",
                "features": [
                    "Event detection with timestamps",
                    "Significance scoring",
                    "Key moment identification",
                    "Event categorization"
                ]
            }
        },
        "timestamp_format": "MM:SS",
        "supported_fps": "1-30 FPS (default: 1 FPS for efficiency)",
        "video_formats": ["mp4", "avi", "mov", "mkv"],
        "notes": [
            "Higher FPS provides more detail but costs more tokens",
            "Default 1 FPS works well for static scenes",
            "Use 2-5 FPS for dynamic scenes",
            "Timestamps are only returned when specifically queried for scenes",
            "File API automatically processes video at specified FPS"
        ],
        "usage_tips": [
            "Be specific in scene queries for better accuracy",
            "Use timeline analysis to get overview before specific queries",
            "Adjust FPS based on scene dynamics",
            "Consider token costs when using higher FPS"
        ]
    }


# ============================================================================
# Event Frames Endpoints
# ============================================================================

@router.get("/frames/list")
async def list_event_frames(
    camera_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List saved event frames

    Args:
        camera_id: Filter by camera ID (optional)
        limit: Maximum number of frames to return
        offset: Offset for pagination

    Returns:
        List of frame metadata with URLs
    """
    from pathlib import Path
    import re
    from datetime import datetime as dt

    event_frames_dir = Path(__file__).parent.parent / "event_frames"

    if not event_frames_dir.exists():
        return {
            "frames": [],
            "total": 0,
            "camera_id": camera_id,
            "limit": limit,
            "offset": offset
        }

    # Get all frame files
    all_frames = []
    for frame_file in event_frames_dir.glob("*.jpg"):
        # Parse filename: camera{id}_{timestamp}_sig{significance}.jpg or camera{id}_{timestamp}_task{id}.jpg
        filename = frame_file.name

        # Extract camera_id from filename
        match = re.match(r'camera(\d+)_(\d{8}_\d{6}_\d+)_(sig(\d+)|task([\w]+))\.jpg', filename)
        if match:
            file_camera_id = int(match.group(1))
            timestamp_str = match.group(2)

            # Filter by camera_id if specified
            if camera_id is not None and file_camera_id != camera_id:
                continue

            # Parse timestamp
            try:
                timestamp = dt.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
            except:
                timestamp = dt.fromtimestamp(frame_file.stat().st_mtime)

            # Get significance or task info
            significance = None
            task_id = None
            if match.group(4):  # sig group
                significance = int(match.group(4))
            elif match.group(5):  # task group
                task_id = match.group(5)

            all_frames.append({
                "filename": filename,
                "camera_id": file_camera_id,
                "timestamp": timestamp.isoformat(),
                "significance": significance,
                "task_id": task_id,
                "url": f"/event_frames/{filename}",
                "size": frame_file.stat().st_size
            })

    # Sort by timestamp (newest first)
    all_frames.sort(key=lambda x: x['timestamp'], reverse=True)

    # Apply pagination
    paginated_frames = all_frames[offset:offset + limit]

    return {
        "frames": paginated_frames,
        "total": len(all_frames),
        "camera_id": camera_id,
        "limit": limit,
        "offset": offset
    }


@router.get("/frames/recent")
async def get_recent_event_frames(
    camera_id: Optional[int] = None,
    hours: int = Query(1, ge=1, le=168)  # Max 1 week
):
    """
    Get event frames from recent hours

    Args:
        camera_id: Filter by camera ID (optional)
        hours: Number of hours to look back

    Returns:
        Recent frames with metadata
    """
    from pathlib import Path
    from datetime import datetime as dt, timedelta
    import re

    event_frames_dir = Path(__file__).parent.parent / "event_frames"

    if not event_frames_dir.exists():
        return {
            "frames": [],
            "hours": hours,
            "camera_id": camera_id
        }

    cutoff_time = dt.utcnow() - timedelta(hours=hours)
    recent_frames = []

    for frame_file in event_frames_dir.glob("*.jpg"):
        # Check file modification time
        file_mtime = dt.fromtimestamp(frame_file.stat().st_mtime)

        if file_mtime < cutoff_time:
            continue

        # Parse filename
        filename = frame_file.name
        match = re.match(r'camera(\d+)_(\d{8}_\d{6}_\d+)_(sig(\d+)|task([\w]+))\.jpg', filename)

        if match:
            file_camera_id = int(match.group(1))

            # Filter by camera_id if specified
            if camera_id is not None and file_camera_id != camera_id:
                continue

            timestamp_str = match.group(2)
            try:
                timestamp = dt.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
            except:
                timestamp = file_mtime

            significance = None
            task_id = None
            if match.group(4):
                significance = int(match.group(4))
            elif match.group(5):
                task_id = match.group(5)

            recent_frames.append({
                "filename": filename,
                "camera_id": file_camera_id,
                "timestamp": timestamp.isoformat(),
                "significance": significance,
                "task_id": task_id,
                "url": f"/event_frames/{filename}",
                "size": frame_file.stat().st_size
            })

    # Sort by timestamp (newest first)
    recent_frames.sort(key=lambda x: x['timestamp'], reverse=True)

    return {
        "frames": recent_frames,
        "total": len(recent_frames),
        "hours": hours,
        "camera_id": camera_id,
        "cutoff_time": cutoff_time.isoformat()
    }


@router.delete("/frames/{filename}")
async def delete_event_frame(filename: str):
    """
    Delete a specific event frame

    Args:
        filename: Frame filename to delete

    Returns:
        Success status
    """
    from pathlib import Path

    event_frames_dir = Path(__file__).parent.parent / "event_frames"
    frame_path = event_frames_dir / filename

    if not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")

    # Security check: ensure filename is just a filename, not a path
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        frame_path.unlink()
        return {
            "success": True,
            "filename": filename,
            "message": "Frame deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete frame: {str(e)}")


@router.delete("/frames/cleanup")
async def cleanup_old_frames(
    days: int = Query(7, ge=1, le=365)
):
    """
    Delete event frames older than specified days

    Args:
        days: Delete frames older than this many days

    Returns:
        Cleanup statistics
    """
    from pathlib import Path
    from datetime import datetime as dt, timedelta

    event_frames_dir = Path(__file__).parent.parent / "event_frames"

    if not event_frames_dir.exists():
        return {
            "deleted": 0,
            "days": days
        }

    cutoff_time = dt.utcnow() - timedelta(days=days)
    deleted_count = 0
    deleted_size = 0

    for frame_file in event_frames_dir.glob("*.jpg"):
        file_mtime = dt.fromtimestamp(frame_file.stat().st_mtime)

        if file_mtime < cutoff_time:
            try:
                file_size = frame_file.stat().st_size
                frame_file.unlink()
                deleted_count += 1
                deleted_size += file_size
            except Exception as e:
                logger.warning(f"Failed to delete {frame_file.name}: {e}")

    return {
        "deleted": deleted_count,
        "deleted_size_bytes": deleted_size,
        "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
        "days": days,
        "cutoff_time": cutoff_time.isoformat()
    }
