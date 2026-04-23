"""
API routes for SentinTinel Surveillance System
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from loguru import logger
import anthropic
import base64
import cv2
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, User, Camera, CameraTask, Event, Detection, Alert, ContextPattern, AlertSeverity
from camera_presets import get_preset_tasks, get_all_presets
from api.websocket import manager
from agents import VisionAgent, ContextAgent
from services import camera_service
from services.email_verification_service import send_verification_email, send_welcome_email
from config import settings
from auth import (
    UserCreate, UserLogin, Token, UserResponse, ResendVerificationRequest,
    create_access_token, verify_password, get_password_hash,
    create_verification_token, get_current_active_user
)

# Create routers
router = APIRouter()
ws_router = APIRouter()


def _resolve_tz(tz_name: Optional[str]):
    if tz_name and ZoneInfo:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return None
    return None


def _fmt_ts_local(utc_dt: datetime, tz) -> str:
    """Format a naive UTC datetime in the user's tz; fall back to labeled UTC."""
    if tz is not None:
        return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%Y-%m-%d %I:%M:%S %p %Z")
    return utc_dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _iso_utc(utc_dt: datetime) -> str:
    """Return ISO string with explicit Z so JS parses it as UTC."""
    return utc_dt.replace(tzinfo=None).isoformat() + "Z"

# Initialize local agents
vision_agent = VisionAgent()
context_agent = ContextAgent()

# Get shared command_agent from main (will be set after main.py initializes it)
def get_command_agent():
    """Get the shared command_agent instance"""
    import main
    return main.command_agent

command_agent = None  # Will be lazy-loaded when needed


# Authentication endpoints
@router.post("/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create verification token
    verification_token = create_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)

    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=False,  # Will be activated after email verification
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=verification_expires
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send verification email
    email_sent = await send_verification_email(new_user.email, verification_token)
    if not email_sent:
        logger.warning(f"Failed to send verification email to {new_user.email}")

    logger.info(f"New user registered: {new_user.email}")

    return new_user


@router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login and get access token
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()

    # Verify user exists and password is correct
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for verification link."
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    logger.info(f"User logged in: {user.email}")

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/auth/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify user email with token from email link
    """
    # Find user by verification token
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    # Check if token is expired
    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )

    # Verify user
    user.is_verified = True
    user.is_active = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    # Send welcome email
    await send_welcome_email(user.email, user.full_name)

    logger.info(f"User email verified: {user.email}")

    return {"message": "Email verified successfully! You can now login."}


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information
    """
    return current_user


@router.post("/auth/resend-verification")
async def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Resend verification email
    """
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a verification link has been sent."}

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )

    # Generate new token
    verification_token = create_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)

    user.verification_token = verification_token
    user.verification_token_expires = verification_expires
    db.commit()

    # Send verification email
    await send_verification_email(user.email, verification_token)

    return {"message": "Verification email sent. Please check your inbox."}


# WebSocket endpoints
@ws_router.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket, token: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    WebSocket endpoint for live video feed and analysis
    """
    # Validate JWT token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Verify user exists and is active
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active or not user.is_verified:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

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
async def websocket_alerts(websocket: WebSocket, token: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time alerts
    """
    # Validate JWT token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active or not user.is_verified:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, "alerts")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@ws_router.websocket("/ws/analysis")
async def websocket_analysis(websocket: WebSocket, token: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    WebSocket endpoint for scene analysis/narration
    """
    # Validate JWT token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active or not user.is_verified:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, "analysis")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@ws_router.websocket("/ws/system")
async def websocket_system(websocket: WebSocket, token: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    WebSocket endpoint for system messages and commands
    """
    # Validate JWT token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active or not user.is_verified:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

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
    camera_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new camera with user-selected tasks.
    """
    camera = Camera(
        name=camera_data.get("name", "Camera"),
        location=camera_data.get("location", ""),
        stream_url=camera_data.get("stream_url", ""),
        is_active=False
    )
    db.add(camera)
    db.flush()

    # Create tasks the user explicitly selected during setup
    for task_data in camera_data.get("tasks", []):
        command = task_data.get("command", "").strip()
        if not command:
            continue
        task = CameraTask(
            camera_id=camera.id,
            command=command,
            task_type=task_data.get("task_type", "custom"),
            priority=task_data.get("priority", 1),
            is_default=task_data.get("is_default", False),
            is_active=True,
        )
        db.add(task)

    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/cameras/{camera_id}")
async def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a camera and stop its worker if running
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Stop worker and hardware capture if running
    import main as main_module
    main_module.stop_camera_worker(camera_id)
    await camera_service.stop_camera(camera_id)

    db.delete(camera)
    db.commit()
    return {"status": "deleted", "camera_id": camera_id}


@router.post("/cameras/{camera_id}/start")
async def start_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
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
        raw_url = camera.stream_url or str(camera_id)
        # Convert numeric strings (e.g. "0") to int so cv2.VideoCapture treats
        # them as device indices, not file paths.
        try:
            stream_url = int(raw_url)
        except (ValueError, TypeError):
            stream_url = raw_url

    except HTTPException:
        raise
    except Exception as e:
        # If database is not available, try to start camera directly
        from loguru import logger
        logger.warning(f"Database not available, starting camera {camera_id} directly: {e}")

    # Initialize camera hardware capture
    try:
        success = await camera_service.initialize_camera(
            camera_id,
            stream_url,
            fps=fps
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if success:
        if camera is not None:
            try:
                camera.is_active = True
                db.commit()
            except Exception:
                pass

        # Start the independent per-camera worker task
        import main as main_module
        main_module.start_camera_worker(camera_id)

        return {"status": "started", "camera_id": camera_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to start camera")


@router.post("/cameras/{camera_id}/stop")
async def stop_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
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

    # Stop the per-camera worker task first
    import main as main_module
    main_module.stop_camera_worker(camera_id)

    # Stop hardware capture
    await camera_service.stop_camera(camera_id)

    if camera is not None:
        try:
            camera.is_active = False
            db.commit()
        except Exception:
            pass

    return {"status": "stopped", "camera_id": camera_id}


# ─────────────────────────────────────────────
# Live Prompting – ask a question about a camera's current frame
# ─────────────────────────────────────────────

@router.post("/cameras/{camera_id}/query")
async def query_camera_live(
    camera_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Ask a real-time question about a camera's current frame.
    Body: { "question": "Is there anyone on the porch?" }
    """
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not camera.is_active:
        raise HTTPException(status_code=400, detail="Camera is not active")

    frame = await camera_service.capture_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=503, detail="Could not capture frame from camera")

    analysis = await vision_agent.analyze_frame(
        frame=frame,
        camera_id=camera_id,
        user_query=question,
    )

    # Encode the analysed frame so the frontend can show it alongside the answer
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    frame_b64 = base64.b64encode(buf).decode('utf-8')

    return {
        "camera_id": camera_id,
        "question": question,
        "answer": analysis.get("query_details") or analysis.get("scene_description", ""),
        "scene_description": analysis.get("scene_description", ""),
        "detections": analysis.get("detections", []),
        "significance": analysis.get("significance", 0),
        "query_match": analysis.get("query_match", False),
        "query_confidence": analysis.get("query_confidence", 0),
        "frame": frame_b64,
        "timestamp": analysis.get("timestamp", ""),
    }


# ─────────────────────────────────────────────
# Historical Query – ask questions about past footage
# ─────────────────────────────────────────────

@router.post("/cameras/{camera_id}/history")
async def query_camera_history(
    camera_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Ask a question about a camera's past recordings.

    Body: {
      "question": "Was there anyone at the door between 2pm and 4pm?",
      "start_time": "2026-03-08T14:00:00",   // optional, defaults to 24h ago
      "end_time":   "2026-03-08T16:00:00",    // optional, defaults to now
      "limit":      200                        // max events to consider
    }
    """
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Parse time range
    now = datetime.utcnow()
    try:
        start_time = datetime.fromisoformat(body["start_time"]) if body.get("start_time") else now - timedelta(hours=24)
    except (ValueError, TypeError):
        start_time = now - timedelta(hours=24)
    try:
        end_time = datetime.fromisoformat(body["end_time"]) if body.get("end_time") else now
    except (ValueError, TypeError):
        end_time = now

    limit = min(int(body.get("limit", 200)), 500)
    user_tz = _resolve_tz(body.get("tz"))
    tz_label = str(user_tz) if user_tz else "UTC"

    # ── Fetch events with detections ────────────────────────────────────
    from database import Event, Detection

    events = (
        db.query(Event)
        .filter(
            Event.camera_id == camera_id,
            Event.timestamp >= start_time,
            Event.timestamp <= end_time,
        )
        .order_by(Event.timestamp.asc())
        .limit(limit)
        .all()
    )

    if not events:
        return {
            "camera_id": camera_id,
            "question": question,
            "answer": f"No recorded events found for this camera between {_fmt_ts_local(start_time, user_tz)} and {_fmt_ts_local(end_time, user_tz)}.",
            "events_analysed": 0,
            "time_range": {"start": _iso_utc(start_time), "end": _iso_utc(end_time)},
            "relevant_frames": [],
        }

    # ── Build a text timeline for Claude ────────────────────────────────
    # Each entry is prefixed with a stable numeric id (id=<event_id>) so
    # Claude can tell us exactly which events it used when forming the
    # answer. We'll parse those ids back out to attach the matching frames
    # as evidence (previously we picked frames by global significance,
    # which produced thumbnails that did not correspond to the cited times
    # in the answer).
    timeline_entries = []
    events_by_id: dict[int, Event] = {}

    event_frames_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "event_frames")

    for ev in events:
        ts = _fmt_ts_local(ev.timestamp, user_tz)
        desc = ev.scene_description or ev.description or ""
        activity = ""
        detected = []
        if ev.event_metadata and isinstance(ev.event_metadata, dict):
            activity = ev.event_metadata.get("activity", "")
            for d in ev.event_metadata.get("detections", []):
                label = d.get("label", d.get("object_label", ""))
                if label:
                    detected.append(label)

        entry = f"[id={ev.id}][{ts}] {desc}"
        if activity:
            entry += f" | Activity: {activity}"
        if detected:
            entry += f" | Detected: {', '.join(detected)}"
        if ev.significance_score and ev.significance_score >= 50:
            entry += f" | Significance: {ev.significance_score}/100"
        timeline_entries.append(entry)
        events_by_id[ev.id] = ev

    timeline_text = "\n".join(timeline_entries)

    # ── Ask Claude to answer the question from the timeline ─────────────
    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

    system_prompt = (
        "You are an AI surveillance analyst. You are given a chronological timeline of scene "
        "observations from a security camera. Each entry starts with an event id in the form "
        "'[id=NNN]' followed by a timestamp.\n\n"
        f"All timestamps in the timeline are in {tz_label}. When you reference times in your "
        f"answer, use that same timezone and format (12-hour with AM/PM).\n\n"
        "Answer the user's question based ONLY on this timeline data. Be specific about times, "
        "people, objects, and activities. If something was not observed, say so clearly. Keep the "
        "answer concise and factual.\n\n"
        "IMPORTANT — at the VERY END of your response, on its own line, include a single tag "
        "listing the event ids that directly support your answer (most relevant first, max 6), "
        "like this:\n"
        "<cited_event_ids>42,44,49</cited_event_ids>\n"
        "If no events support the answer, emit <cited_event_ids></cited_event_ids>. Never include "
        "ids that are not in the timeline. Do not mention this tag in the prose above it."
    )

    import asyncio
    answer = None
    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Camera: {camera.name} ({camera.location or 'unknown location'})\n"
                        f"Time range: {_fmt_ts_local(start_time, user_tz)} to {_fmt_ts_local(end_time, user_tz)}\n"
                        f"Total observations: {len(events)}\n\n"
                        f"--- TIMELINE ---\n{timeline_text}\n--- END ---\n\n"
                        f"Question: {question}"
                    ),
                }
            ],
        )
        answer = response.content[0].text
    except Exception as exc:
        logger.warning(f"Claude history synthesis failed: {exc}")
        # Fallback: return the raw timeline entries so the user still gets data
        answer = (
            f"AI synthesis unavailable. Found {len(events)} event(s) in the requested time range.\n\n"
            + "\n".join(timeline_entries[:20])
        )

    # ── Parse the <cited_event_ids>...</cited_event_ids> tag ────────────
    import re as _re
    cited_ids: list[int] = []
    if answer:
        m = _re.search(r"<cited_event_ids>\s*([0-9,\s]*)\s*</cited_event_ids>", answer)
        if m:
            raw = m.group(1)
            for tok in raw.split(","):
                tok = tok.strip()
                if tok.isdigit():
                    eid = int(tok)
                    if eid in events_by_id and eid not in cited_ids:
                        cited_ids.append(eid)
            # Strip the machine-readable tag from the user-visible answer
            answer = _re.sub(
                r"\s*<cited_event_ids>[\s0-9,]*</cited_event_ids>\s*$",
                "",
                answer,
            ).rstrip()

    # ── Build the evidence frame list ───────────────────────────────────
    # Priority order:
    #   1. Events Claude explicitly cited (kept in Claude's ranking order,
    #      which already has most-relevant first)
    #   2. If we have fewer than 2 cited events (or parsing failed), fall
    #      back to keyword-overlap ranking against the question — this
    #      keeps evidence aligned with what the user ACTUALLY asked rather
    #      than with global scene significance.
    evidence_events: list[Event] = [events_by_id[i] for i in cited_ids]

    if len(evidence_events) < 2:
        q_stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "did", "do", "does",
            "you", "your", "i", "see", "seen", "saw", "any", "of", "in", "on",
            "at", "to", "for", "and", "or", "with", "by", "as", "be", "been",
            "have", "has", "had", "what", "when", "who", "where", "why", "how",
            "today", "yesterday", "show", "me", "tell", "about", "my",
        }
        q_tokens = {
            t for t in _re.findall(r"[a-zA-Z]{3,}", question.lower())
            if t not in q_stopwords
        }

        def _overlap_score(ev: Event) -> tuple[int, int]:
            haystack_parts = [
                (ev.scene_description or ""),
                (ev.description or ""),
            ]
            if ev.event_metadata and isinstance(ev.event_metadata, dict):
                haystack_parts.append(str(ev.event_metadata.get("activity", "")))
                for d in ev.event_metadata.get("detections", []):
                    label = d.get("label", d.get("object_label", ""))
                    if label:
                        haystack_parts.append(str(label))
            haystack = " ".join(haystack_parts).lower()
            hay_tokens = set(_re.findall(r"[a-zA-Z]{3,}", haystack))
            overlap = len(q_tokens & hay_tokens) if q_tokens else 0
            # Break ties with significance so at equal relevance we still
            # prefer the more significant moment.
            return (overlap, ev.significance_score or 0)

        ranked = sorted(events, key=_overlap_score, reverse=True)
        seen_ids = {ev.id for ev in evidence_events}
        for ev in ranked:
            if len(evidence_events) >= 5:
                break
            # Only use the fallback-ranked event if it actually matches
            # SOMETHING in the question — otherwise we'd be back to
            # unrelated thumbnails. If nothing matches the question at all
            # (overlap 0 across the board), surface the highest-significance
            # moment so the user still gets visual context.
            overlap = _overlap_score(ev)[0]
            if ev.id in seen_ids:
                continue
            if overlap > 0 or not evidence_events:
                evidence_events.append(ev)
                seen_ids.add(ev.id)

        # If we still have nothing (no question-token matches at all and
        # no citations), fall back to the old behaviour: top significance.
        if not evidence_events:
            evidence_events = sorted(
                events, key=lambda e: e.significance_score or 0, reverse=True
            )[:3]

    # Stable chronological display order for the UI (oldest → newest) so
    # the thumbnails read like a mini-timeline of the cited moments.
    evidence_events.sort(key=lambda e: e.timestamp)

    relevant_frames = []
    for ev in evidence_events:
        ts_prefix = ev.timestamp.strftime("%Y%m%d_%H%M%S")
        frame_url = None
        try:
            for f in os.listdir(event_frames_dir):
                if f.startswith(f"camera{camera_id}_{ts_prefix}"):
                    frame_url = f"/event_frames/{f}"
                    break
        except OSError:
            pass

        relevant_frames.append({
            "event_id": ev.id,
            "timestamp": _iso_utc(ev.timestamp),
            "scene_description": ev.scene_description or "",
            "significance": ev.significance_score or 0,
            "frame_url": frame_url,
        })

    return {
        "camera_id": camera_id,
        "question": question,
        "answer": answer,
        "events_analysed": len(events),
        "time_range": {"start": _iso_utc(start_time), "end": _iso_utc(end_time)},
        "relevant_frames": relevant_frames,
    }


# ─────────────────────────────────────────────
# Cross-Camera Scene Search
# ─────────────────────────────────────────────

@router.post("/search/scenes")
async def search_scenes(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search for a described scene across ALL cameras and return exact timestamps.

    Body: {
      "query": "person wearing red near the entrance",
      "start_time": "2026-03-20T00:00:00",  // optional, defaults to 7 days ago
      "end_time":   "2026-03-27T23:59:59",  // optional, defaults to now
      "camera_ids": [1, 2],                 // optional, defaults to all cameras
      "limit": 50
    }
    """
    from sqlalchemy import or_

    query_text = (body.get("query") or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="query is required")

    now = datetime.utcnow()
    try:
        start_time = datetime.fromisoformat(body["start_time"]) if body.get("start_time") else now - timedelta(days=7)
    except (ValueError, TypeError):
        start_time = now - timedelta(days=7)
    try:
        end_time = datetime.fromisoformat(body["end_time"]) if body.get("end_time") else now
    except (ValueError, TypeError):
        end_time = now

    camera_ids_filter = body.get("camera_ids") or None
    limit = min(int(body.get("limit", 50)), 200)
    user_tz = _resolve_tz(body.get("tz"))
    tz_label = str(user_tz) if user_tz else "UTC"

    # ── 1. ChromaDB semantic search (all cameras) ────────────────────────
    chroma_event_ids: set = set()
    chroma_scores: dict = {}  # event_id -> similarity (0–1, higher = better)

    try:
        collection_count = context_agent.scene_collection.count()
        if collection_count > 0:
            similar = await context_agent.find_similar_events(
                scene_description=query_text,
                n_results=min(50, collection_count),
                camera_id=None,  # None = search all cameras
            )
            for match in similar:
                meta = match.get("metadata", {})
                eid = meta.get("event_id")
                if eid is not None:
                    eid = int(eid)
                    chroma_event_ids.add(eid)
                    dist = match.get("distance") or 1.0
                    chroma_scores[eid] = round(max(0.0, 1.0 - float(dist)), 3)
    except Exception as exc:
        logger.warning(f"ChromaDB search error (falling back to DB-only): {exc}")

    # ── 2. DB text search across all cameras ────────────────────────────
    base_q = db.query(Event).filter(
        Event.timestamp >= start_time,
        Event.timestamp <= end_time,
    )
    if camera_ids_filter:
        base_q = base_q.filter(Event.camera_id.in_(camera_ids_filter))

    search_term = f"%{query_text}%"
    text_events = (
        base_q.filter(
            or_(
                Event.scene_description.ilike(search_term),
                Event.description.ilike(search_term),
            )
        )
        .order_by(Event.timestamp.desc())
        .limit(limit)
        .all()
    )

    # ── 3. Fetch DB rows for ChromaDB hits (filtered by time/camera) ─────
    chroma_db_events = []
    if chroma_event_ids:
        chroma_q = db.query(Event).filter(
            Event.id.in_(chroma_event_ids),
            Event.timestamp >= start_time,
            Event.timestamp <= end_time,
        )
        if camera_ids_filter:
            chroma_q = chroma_q.filter(Event.camera_id.in_(camera_ids_filter))
        chroma_db_events = chroma_q.all()

    # ── 4. Merge & deduplicate ───────────────────────────────────────────
    events_map = {ev.id: ev for ev in chroma_db_events}
    for ev in text_events:
        events_map[ev.id] = ev

    if not events_map:
        return {
            "query": query_text,
            "answer": f"No matching scenes found for '{query_text}' between {_fmt_ts_local(start_time, user_tz)} and {_fmt_ts_local(end_time, user_tz)}.",
            "total_matches": 0,
            "time_range": {"start": _iso_utc(start_time), "end": _iso_utc(end_time)},
            "matches": [],
        }

    all_events = sorted(events_map.values(), key=lambda e: e.timestamp)

    # ── 5. Load camera metadata ─────────────────────────────────────────
    cam_ids = {e.camera_id for e in all_events}
    cameras_map = {c.id: c for c in db.query(Camera).filter(Camera.id.in_(cam_ids)).all()}

    # ── 6. Build timeline text for Claude ────────────────────────────────
    timeline_lines = []
    for ev in all_events:
        cam = cameras_map.get(ev.camera_id)
        cam_label = (
            f"{cam.name} — {cam.location}" if cam and cam.location
            else (cam.name if cam else f"Camera {ev.camera_id}")
        )
        ts = _fmt_ts_local(ev.timestamp, user_tz)
        desc = ev.scene_description or ev.description or "(no description)"
        sim = chroma_scores.get(ev.id)
        sim_tag = f" [similarity {sim:.0%}]" if sim is not None else ""
        sig_tag = f" | significance {ev.significance_score}/100" if ev.significance_score and ev.significance_score >= 50 else ""
        timeline_lines.append(f"[{ts}] {cam_label}: {desc}{sim_tag}{sig_tag}")

    # Cap the timeline at 150 lines to stay within prompt limits
    timeline_text = "\n".join(timeline_lines[:150])

    # ── 7. Ask Claude to synthesise the answer ───────────────────────────
    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    system_prompt = (
        "You are an AI surveillance analyst for a multi-camera security system. "
        "You are given a chronological timeline of scene observations from multiple cameras. "
        "Each line contains a timestamp, the camera name, a scene description, and optionally "
        "a semantic similarity score showing how closely the observation matches the user's query.\n\n"
        f"All timestamps in the timeline are in {tz_label}. When you reference times in your "
        f"answer, use that same timezone and format (12-hour with AM/PM).\n\n"
        "Your job: answer the user's query by identifying EXACTLY when and on which camera "
        "the described scene occurred. If there are multiple occurrences list all of them with "
        "precise timestamps. If nothing matches, say so clearly. Be concise and factual."
    )

    import asyncio
    cam_names = ", ".join(c.name for c in cameras_map.values()) if cameras_map else "all cameras"
    answer = None
    try:
        llm_response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    f"Query: {query_text}\n"
                    f"Time range searched: {_fmt_ts_local(start_time, user_tz)} → {_fmt_ts_local(end_time, user_tz)}\n"
                    f"Cameras searched: {cam_names}\n"
                    f"Total observations in timeline: {len(timeline_lines)}\n\n"
                    f"--- TIMELINE ---\n{timeline_text}\n--- END ---\n\n"
                    "When did this happen, and on which camera?"
                ),
            }],
        )
        answer = llm_response.content[0].text
    except Exception as exc:
        logger.warning(f"Claude synthesis failed: {exc}")
        # Build a plain-text summary from the timeline as fallback
        if timeline_lines:
            answer = (
                f"Found {len(all_events)} event(s) matching '{query_text}'. "
                f"AI synthesis unavailable — see matching events below for exact timestamps and cameras."
            )
        else:
            answer = f"No matching scenes found for '{query_text}'."

    # ── 8. Build structured matches list ────────────────────────────────
    event_frames_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "event_frames")
    matches = []
    for ev in all_events[:limit]:
        cam = cameras_map.get(ev.camera_id)
        frame_url = None
        try:
            ts_prefix = ev.timestamp.strftime("%Y%m%d_%H%M%S")
            for fname in os.listdir(event_frames_dir):
                if fname.startswith(f"camera{ev.camera_id}_{ts_prefix}"):
                    frame_url = f"/event_frames/{fname}"
                    break
        except Exception:
            pass

        matches.append({
            "event_id": ev.id,
            "camera_id": ev.camera_id,
            "camera_name": cam.name if cam else f"Camera {ev.camera_id}",
            "camera_location": cam.location if cam else None,
            "timestamp": _iso_utc(ev.timestamp),
            "scene_description": ev.scene_description or ev.description or "",
            "significance": ev.significance_score or 0,
            "is_anomaly": bool(ev.is_anomaly),
            "semantic_similarity": chroma_scores.get(ev.id),
            "frame_url": frame_url,
            "source": "semantic" if ev.id in chroma_event_ids else "text",
        })

    # Best semantic matches first, then chronological
    matches.sort(key=lambda m: (-(m["semantic_similarity"] or 0), m["timestamp"]))

    return {
        "query": query_text,
        "answer": answer,
        "total_matches": len(matches),
        "time_range": {"start": _iso_utc(start_time), "end": _iso_utc(end_time)},
        "matches": matches,
    }


# ─────────────────────────────────────────────
# Camera Task endpoints
# ─────────────────────────────────────────────

@router.get("/camera-presets")
async def list_presets():
    """Return all available location presets."""
    return get_all_presets()


@router.get("/cameras/{camera_id}/tasks")
async def get_camera_tasks(
    camera_id: int,
    db: Session = Depends(get_db),
):
    """Get all tasks for a camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    tasks = (
        db.query(CameraTask)
        .filter(CameraTask.camera_id == camera_id)
        .order_by(CameraTask.priority.desc(), CameraTask.created_at)
        .all()
    )
    return [
        {
            "id": t.id,
            "camera_id": t.camera_id,
            "command": t.command,
            "task_type": t.task_type,
            "is_default": t.is_default,
            "is_active": t.is_active,
            "priority": t.priority,
            "source": getattr(t, "source", "manual") or "manual",
            "original_command": getattr(t, "original_command", None),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


@router.post("/cameras/{camera_id}/tasks")
async def add_camera_task(
    camera_id: int,
    task_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a new monitoring task to a camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    command = task_data.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Task command is required")

    task = CameraTask(
        camera_id=camera_id,
        command=command,
        task_type=task_data.get("task_type", "custom"),
        is_default=False,
        is_active=True,
        priority=task_data.get("priority", 1),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "camera_id": task.camera_id,
        "command": task.command,
        "task_type": task.task_type,
        "is_default": task.is_default,
        "is_active": task.is_active,
        "priority": task.priority,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.put("/cameras/{camera_id}/tasks/{task_id}")
async def update_camera_task(
    camera_id: int,
    task_id: int,
    task_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Toggle a task active/inactive or update its command."""
    task = (
        db.query(CameraTask)
        .filter(CameraTask.id == task_id, CameraTask.camera_id == camera_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if "is_active" in task_data:
        task.is_active = task_data["is_active"]
    if "command" in task_data:
        task.command = task_data["command"]
    if "priority" in task_data:
        task.priority = task_data["priority"]

    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "camera_id": task.camera_id,
        "command": task.command,
        "task_type": task.task_type,
        "is_default": task.is_default,
        "is_active": task.is_active,
        "priority": task.priority,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.delete("/cameras/{camera_id}/tasks/{task_id}")
async def delete_camera_task(
    camera_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a task from a camera."""
    task = (
        db.query(CameraTask)
        .filter(CameraTask.id == task_id, CameraTask.camera_id == camera_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"status": "deleted", "task_id": task_id}


# ─────────────────────────────────────────────────────────────────────────────
# AI Commands (Intelligence page)
#
# An "AI Command" is a natural-language instruction the user types on the
# Intelligence page (e.g. "alert me if you see any water bottle"). Under the
# hood it fans out into one `CameraTask` row per live camera, all sharing the
# same `original_command` text and `source="ai_command"`. These endpoints
# expose the command-level view (group-by original_command) plus cancellation.
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/ai-commands")
async def list_ai_commands(db: Session = Depends(get_db)):
    """Return every active AI Command, grouped across cameras.

    Shape:
      {
        "active": [ { "original_command", "detection_target", "task_type",
                      "created_at", "cameras": [{camera_id, camera_name,
                      camera_location, task_id}] } ],
        "pending": [ { "original_command", "command", "task_type",
                       "queued_at" } ]
      }
    """
    import main as main_module

    rows = (
        db.query(CameraTask, Camera)
        .join(Camera, CameraTask.camera_id == Camera.id)
        .filter(
            CameraTask.source == "ai_command",
            CameraTask.is_active == True,  # noqa: E712
        )
        .order_by(CameraTask.created_at.desc())
        .all()
    )

    groups: dict[str, dict] = {}
    for task, cam in rows:
        key = task.original_command or task.command
        if key not in groups:
            groups[key] = {
                "original_command": task.original_command or task.command,
                "detection_target": task.command,
                "task_type": task.task_type,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "cameras": [],
            }
        groups[key]["cameras"].append({
            "camera_id": cam.id,
            "camera_name": cam.name,
            "camera_location": cam.location,
            "task_id": task.id,
        })

    return {
        "active": list(groups.values()),
        "pending": list(main_module.pending_ai_commands),
    }


@router.delete("/ai-commands")
async def cancel_ai_command(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Disarm every camera running this AI Command and clear it from the
    pending queue if queued.

    Body: `{ "original_command": "..." }`
    """
    import main as main_module

    original = (payload or {}).get("original_command", "").strip()
    if not original:
        raise HTTPException(status_code=400, detail="original_command is required")

    deleted = (
        db.query(CameraTask)
        .filter(
            CameraTask.source == "ai_command",
            CameraTask.original_command == original,
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    before = len(main_module.pending_ai_commands)
    main_module.pending_ai_commands[:] = [
        p for p in main_module.pending_ai_commands
        if p.get("original_command") != original
    ]
    pending_removed = before - len(main_module.pending_ai_commands)

    await manager.send_system_message("ai_command_changed", {
        "reason": "cancelled",
        "original_command": original,
        "deleted_rows": deleted,
        "pending_removed": pending_removed,
    })

    return {
        "status": "cancelled",
        "original_command": original,
        "deleted_rows": deleted,
        "pending_removed": pending_removed,
    }


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
    Get alerts with filtering. Each alert is flattened with its stored
    `alert_metadata` so the UI can show why the model raised it and the
    supporting evidence frame.
    """
    try:
        query = db.query(Alert)

        if is_read is not None:
            query = query.filter(Alert.is_read == is_read)
        if severity:
            query = query.filter(Alert.severity == severity)

        alerts = query.order_by(Alert.timestamp.desc()).limit(limit).all()

        result = []
        for a in alerts:
            meta = a.alert_metadata or {}
            camera_id = meta.get("camera_id")
            if camera_id is None and a.event is not None:
                camera_id = a.event.camera_id
            result.append({
                "id": a.id,
                "event_id": a.event_id,
                "severity": a.severity.value if hasattr(a.severity, "value") else a.severity,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "is_read": a.is_read,
                "is_dismissed": a.is_dismissed,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "response_time_seconds": a.response_time_seconds,
                "camera_id": camera_id,
                "significance": meta.get("significance") or meta.get("query_confidence"),
                "frame_url": meta.get("frame_url"),
                "detected_objects": meta.get("detected_objects", []),
                "detections": meta.get("detections", []),
                "user_query": meta.get("user_query"),
                "query_confidence": meta.get("query_confidence"),
                "query_details": meta.get("query_details"),
                "claude_reasoning": meta.get("claude_reasoning"),
                "scene_description": meta.get("scene_description"),
                "activity": meta.get("activity"),
                "reasoning": meta.get("reasoning"),
                # IMPORTANT: do NOT default this to "trigger_match" — legacy
                # alerts (pre-metadata) would then impersonate user-triggered
                # ones and slip past the Alerts page filter, inflating counts.
                # Only surface the value if it's actually present in metadata.
                "alert_type": meta.get("alert_type"),
            })
        return result
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


@router.post("/alerts/acknowledge-all")
async def acknowledge_all_alerts(db: Session = Depends(get_db)):
    """
    Mark all unread alerts as acknowledged
    """
    now = datetime.utcnow()
    unread = db.query(Alert).filter(Alert.is_read == False).all()
    for alert in unread:
        alert.is_read = True
        alert.acknowledged_at = now
    db.commit()
    return {"acknowledged": len(unread)}


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


@router.delete("/alerts")
async def delete_all_alerts(db: Session = Depends(get_db)):
    """
    Permanently delete all alerts (used by Clear All on the frontend)
    """
    count = db.query(Alert).delete()
    db.commit()
    return {"deleted": count}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Permanently delete a single alert (used by Dismiss on the frontend)
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"deleted": alert_id}


@router.post("/email/test-alert")
async def send_test_alert_email(
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Send a realistic sample alert email so the operator can verify the
    layout, logo, and timezone without having to trigger a real event.

    Body (all fields optional):
        {
          "recipient": "override@example.com",  # defaults to current user
          "variant": "critical" | "warning" | "summary"
        }
    """
    from services.email_service import email_service
    from services.brand_assets import render_test_frame_png

    if not email_service.enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "Email service not configured — set GMAIL_USER and "
                "GMAIL_APP_PASSWORD in your environment."
            ),
        )

    body = payload or {}
    recipient = (body.get("recipient") or current_user.email or "").strip()
    variant = (body.get("variant") or "critical").lower()

    # Generate a deterministic placeholder "camera frame" so the Evidence
    # section renders exactly like a real alert.
    try:
        frame_png = render_test_frame_png()
        frame_b64 = base64.b64encode(frame_png).decode("utf-8")
    except Exception as exc:
        logger.warning(f"Test frame render failed: {exc}")
        frame_b64 = None

    now_iso = datetime.utcnow().isoformat()

    base_payload = {
        "timestamp": now_iso,
        "camera_id": 0,
        "camera_name": "Outdoor (test)",
        "frame_base64": frame_b64,
        "detected_objects": ["person", "delivery bag", "doormat"],
        "scene_description": (
            "A person in a rain jacket is standing at the front door with a "
            "small cardboard package held under their left arm. The porch "
            "light is on. No one else is visible in the frame."
        ),
        "activity": "Person approaching the front door with a package",
    }

    if variant == "summary":
        alert_payload = {
            **base_payload,
            "severity": "INFO",
            "title": "Nothing unusual in the last 2 minutes",
            "message": (
                "This is a test summary email.\n\n"
                "ThirdEye would normally use this layout for a routine "
                "digest when no alert rules matched during the window."
            ),
            "significance": 45,
        }
        ok = await email_service.send_summary_email(alert_payload, recipient=recipient)
    else:
        severity = "CRITICAL" if variant == "critical" else "WARNING"
        confidence = 92 if severity == "CRITICAL" else 71
        alert_payload = {
            **base_payload,
            "severity": severity,
            "title": "Trigger matched: Person At Front Door",
            "message": (
                f"Camera Outdoor (test) matched your monitoring trigger with "
                f"{confidence}% confidence.\n\n"
                f"This is a test email sent by the developer — it is not a "
                f"real event."
            ),
            "user_query": "Notify me if someone enters my home",
            "query_confidence": confidence,
            "query_details": (
                "Rule matched: a person carrying a package is visible at the "
                "front door, which qualifies as someone entering the home."
            ),
            "claude_reasoning": (
                "The subject is walking deliberately toward the door while "
                "holding a package. Lighting, posture, and direction of travel "
                "are consistent with an entry event rather than a passer-by."
            ),
        }
        ok = await email_service.send_critical_alert(alert_payload, recipient=recipient)

    if not ok:
        raise HTTPException(status_code=502, detail="SMTP send failed — see backend logs.")

    return {
        "status": "sent",
        "recipient": recipient,
        "variant": variant,
        "subject_hint": f"[ThirdEye • {alert_payload['severity'].title()}] {alert_payload.get('title')}",
    }


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
        info_alerts = db.query(Alert).filter(
            Alert.timestamp >= since,
            Alert.severity == AlertSeverity.INFO
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
            "info_alerts": info_alerts,
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


MONITORING_TASK_TYPES = {
    "object_detection",
    "activity_detection",
    "state_change_detection",
    "surveillance",
    "scene_analysis",
    "anomaly_detection",
    "tracking",
}


def _derive_detection_target(parsed: dict, fallback: str) -> str:
    """Collapse a parsed command into the short text the vision agent uses.

    Priority mirrors what `_analysis_loop` already does for in-memory tasks:
    `expected_change` → `target` → `objects_to_detect` → `activities_to_detect`
    → `understood_intent` → original user command.
    """
    params = parsed.get("parameters") or {}
    candidates = [
        parsed.get("expected_change"),
        parsed.get("target"),
        ", ".join(params.get("objects_to_detect", []) or []),
        ", ".join(params.get("activities_to_detect", []) or []),
        parsed.get("understood_intent"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return fallback.strip()


async def process_user_command(command: str, params: dict):
    """Parse a natural-language command from the Intelligence page and arm it
    across every active camera.

    Behaviour:
    - Parse the command ONCE with any available CommandAgent (per-camera if
      present, otherwise the global fallback).
    - For monitoring-style task types, persist the parsed target as a
      `CameraTask` row (`source="ai_command"`) for every currently active
      camera. DB persistence means it survives backend restarts and is
      picked up by the same high-sensitivity path the Cameras page uses.
    - If no cameras are active, enqueue the command so the very next camera
      that comes online attaches it automatically.
    - Emit a single `command_processed` message that tells the UI *how many
      cameras were armed* and surface any per-camera failures.
    """
    import main as main_module

    original_command = command
    active_camera_ids: list[int] = list(camera_service.active_cameras.keys())
    context = {
        "active_cameras": active_camera_ids,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # ── 1. Pick a parser. Prefer an existing per-camera agent; else global. ──
    target_camera_id = params.get("camera_id")
    parse_agent = None
    if target_camera_id and target_camera_id in main_module.camera_command_agents:
        parse_agent = main_module.camera_command_agents[target_camera_id]
    elif main_module.camera_command_agents:
        parse_agent = next(iter(main_module.camera_command_agents.values()))
    else:
        parse_agent = main_module.command_agent

    # ── 2. Parse once. ──────────────────────────────────────────────────────
    try:
        parsed = await parse_agent.process_command(command, context)
    except Exception as e:
        logger.exception("[AI-CMD] Parser failed")
        await manager.send_system_message("command_error", {
            "error": str(e),
            "message": f"Failed to interpret command: {e}",
        })
        return

    if parsed.get("task_type") == "error":
        await manager.send_system_message("command_error", {
            "error": parsed.get("error", "unknown"),
            "message": parsed.get("confirmation", "Failed to process command"),
        })
        return

    task_type = parsed.get("task_type", "surveillance")
    detection_target = _derive_detection_target(parsed, original_command)

    # ── 3. Non-monitoring task types: short-circuit to alert-only path. ────
    if task_type == "alert":
        await manager.send_alert({
            "severity": "INFO",
            "title": "Command Alert",
            "message": parsed.get("confirmation", original_command),
            "camera_id": params.get("camera_id", 1),
        })
        await manager.send_system_message("command_processed", {
            "original_command": original_command,
            "task_id": parsed.get("task_id"),
            "task_type": task_type,
            "confirmation": parsed.get("confirmation"),
            "understood_intent": parsed.get("understood_intent"),
            "armed_cameras": [],
            "pending": False,
        })
        return

    if task_type not in MONITORING_TASK_TYPES:
        # Nothing persistent to do — just echo the parsed interpretation.
        await manager.send_system_message("command_processed", {
            "original_command": original_command,
            "task_id": parsed.get("task_id"),
            "task_type": task_type,
            "confirmation": parsed.get("confirmation"),
            "understood_intent": parsed.get("understood_intent"),
            "armed_cameras": [],
            "pending": False,
        })
        return

    # ── 4. Fan out to every live camera concurrently. ──────────────────────
    target_cameras: list[int] = (
        [target_camera_id]
        if target_camera_id and target_camera_id in camera_service.active_cameras
        else active_camera_ids
    )

    if not target_cameras:
        # Queue until a camera comes online. `start_camera_worker` flushes this.
        main_module.pending_ai_commands.append({
            "original_command": original_command,
            "command": detection_target,
            "task_type": task_type,
            "priority": 2,
            "queued_at": datetime.utcnow().isoformat(),
        })
        logger.info(
            f"[AI-CMD] Queued (no active cameras): '{original_command}' → '{detection_target}'"
        )
        await manager.send_system_message("command_processed", {
            "original_command": original_command,
            "task_id": parsed.get("task_id"),
            "task_type": task_type,
            "confirmation": parsed.get("confirmation"),
            "understood_intent": parsed.get("understood_intent"),
            "detection_target": detection_target,
            "armed_cameras": [],
            "pending": True,
            "queued_message": (
                "No cameras are running. Command queued — it will arm the next "
                "camera that comes online."
            ),
        })
        return

    async def _persist_one(cam_id: int) -> dict:
        """Persist one CameraTask row for one camera. Runs in a thread."""
        def _sync():
            from database import SessionLocal
            db = SessionLocal()
            try:
                existing = (
                    db.query(CameraTask)
                    .filter(
                        CameraTask.camera_id == cam_id,
                        CameraTask.source == "ai_command",
                        CameraTask.original_command == original_command,
                        CameraTask.is_active == True,  # noqa: E712
                    )
                    .first()
                )
                if existing:
                    return {"camera_id": cam_id, "status": "already_armed", "task_id": existing.id}

                task_row = CameraTask(
                    camera_id=cam_id,
                    command=detection_target,
                    task_type=task_type,
                    is_default=False,
                    is_active=True,
                    priority=2,
                    source="ai_command",
                    original_command=original_command,
                )
                db.add(task_row)
                db.commit()
                db.refresh(task_row)
                return {"camera_id": cam_id, "status": "armed", "task_id": task_row.id}
            except Exception as exc:
                db.rollback()
                return {"camera_id": cam_id, "status": "error", "error": str(exc)}
            finally:
                db.close()

        import asyncio as _asyncio
        return await _asyncio.to_thread(_sync)

    import asyncio as _asyncio
    results = await _asyncio.gather(
        *[_persist_one(cid) for cid in target_cameras],
        return_exceptions=False,
    )

    armed = [r for r in results if r.get("status") in ("armed", "already_armed")]
    failed = [r for r in results if r.get("status") == "error"]

    logger.info(
        f"[AI-CMD] '{original_command}' → target='{detection_target}' "
        f"armed={len(armed)}/{len(target_cameras)} failed={len(failed)}"
    )

    await manager.send_system_message("command_processed", {
        "original_command": original_command,
        "task_id": parsed.get("task_id"),
        "task_type": task_type,
        "confirmation": parsed.get("confirmation"),
        "understood_intent": parsed.get("understood_intent"),
        "detection_target": detection_target,
        "armed_cameras": [r["camera_id"] for r in armed],
        "failed_cameras": [{"camera_id": r["camera_id"], "error": r.get("error")} for r in failed],
        "pending": False,
    })

    # Tell the UI the armed-commands panel needs to re-fetch.
    await manager.send_system_message("ai_command_changed", {
        "reason": "armed",
        "original_command": original_command,
        "armed_cameras": [r["camera_id"] for r in armed],
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
