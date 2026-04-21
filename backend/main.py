"""
Main FastAPI application for ThirdEye Intelligent Monitoring System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import uvicorn
from loguru import logger
from typing import Dict
from pathlib import Path
from datetime import datetime, timedelta
import base64
import cv2
import os

from config import settings
from database import init_db
from api import router, ws_router
from services import camera_service
from services.email_service import email_service


# ─────────────────────────────────────────────
# Per-camera worker management
# ─────────────────────────────────────────────
camera_workers: Dict[int, asyncio.Task] = {}       # camera_id → asyncio.Task
camera_command_agents: Dict[int, object] = {}      # camera_id → CommandAgent instance

# Shared global command_agent kept for backward-compat with routes that import it
from agents import CommandAgent
command_agent = CommandAgent()


def start_camera_worker(camera_id: int):
    """Spawn an independent asyncio worker task for a camera."""
    if camera_id in camera_workers and not camera_workers[camera_id].done():
        logger.info(f"[CAM-{camera_id}] Worker already running")
        return

    from agents import CommandAgent
    camera_command_agents[camera_id] = CommandAgent()
    task = asyncio.create_task(_camera_worker(camera_id))
    camera_workers[camera_id] = task
    logger.info(f"[CAM-{camera_id}] Worker task started")


def stop_camera_worker(camera_id: int):
    """Cancel the worker task for a camera."""
    task = camera_workers.pop(camera_id, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"[CAM-{camera_id}] Worker task cancelled")
    camera_command_agents.pop(camera_id, None)


async def _camera_worker(camera_id: int):
    """
    Fully independent surveillance worker for ONE camera.
    Runs two concurrent loops:
      1. _frame_streamer — captures & sends frames to UI at full FPS (fast)
      2. _analysis_loop  — grabs latest frame, calls Claude AI, processes results (slow)
    """
    from agents import VisionAgent, ContextAgent
    from agents.reasoning_agent import ReasoningAgent
    from api import manager
    from database import SessionLocal, CameraTask, Event, Detection, Alert, AlertSeverity

    vision_agent = VisionAgent()
    context_agent = ContextAgent()
    cmd_agent = camera_command_agents.get(camera_id, command_agent)

    try:
        reasoning_agent = ReasoningAgent()
        logger.info(f"[CAM-{camera_id}] Reasoning Agent initialized")
    except Exception as e:
        logger.warning(f"[CAM-{camera_id}] Reasoning Agent unavailable: {e}")
        reasoning_agent = None

    event_frames_dir = Path(__file__).parent / "event_frames"
    event_frames_dir.mkdir(exist_ok=True)

    # Shared state between streamer and analyser
    latest_frame = {"frame": None, "base64": None}
    ANALYSIS_INTERVAL_SECONDS = 120
    minute_start_time = datetime.utcnow()
    critical_events = []
    baseline_states: Dict[str, dict] = {}

    logger.info(f"[CAM-{camera_id}] Surveillance worker started")

    # ── Fast frame streamer ──────────────────────────────────────────────
    async def _frame_streamer():
        """Capture frames and push to WebSocket at camera FPS."""
        while True:
            try:
                frame = await camera_service.capture_frame(camera_id)
                if frame is None:
                    await asyncio.sleep(1.0 / settings.CAMERA_FPS)
                    continue

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Update shared state for the analysis loop
                latest_frame["frame"] = frame
                latest_frame["base64"] = frame_b64

                await manager.send_live_feed_update(camera_id, frame_b64, {})
                await asyncio.sleep(1.0 / settings.CAMERA_FPS)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[CAM-{camera_id}] Frame streamer error: {e}")
                await asyncio.sleep(0.5)

    # ── Slow analysis loop ───────────────────────────────────────────────
    async def _analysis_loop():
        nonlocal minute_start_time, critical_events

        # Analysis interval — how often to call Claude (seconds)
        ANALYSIS_EVERY = 5
        consecutive_errors = 0

        while True:
            try:
                current_time = datetime.utcnow()
                elapsed_seconds = (current_time - minute_start_time).total_seconds()

                frame = latest_frame["frame"]
                frame_base64 = latest_frame["base64"]
                if frame is None:
                    await asyncio.sleep(1)
                    continue

                # ── Resolve active tasks ──────────────────────────────────
                user_query = None
                target_object = None
                requires_baseline = False
                task_id = None
                expected_change = None
                query_type = None

                db_task_queries = []
                try:
                    task_db = SessionLocal()
                    db_tasks = (
                        task_db.query(CameraTask)
                        .filter(CameraTask.camera_id == camera_id, CameraTask.is_active == True)
                        .order_by(CameraTask.priority.desc())
                        .all()
                    )
                    for dt in db_tasks:
                        db_task_queries.append(dt.command)
                    task_db.close()
                except Exception as task_err:
                    logger.warning(f"[CAM-{camera_id}] Failed to load DB tasks: {task_err}")

                active_tasks = cmd_agent.get_active_tasks()
                adhoc_query = None

                if active_tasks:
                    task_id = list(active_tasks.keys())[0]
                    latest_task = active_tasks[task_id]
                    task_command = latest_task.get('command', {})
                    target_object = task_command.get('target', '')
                    understood_intent = task_command.get('understood_intent', '')
                    expected_change = task_command.get('expected_change', '')
                    requires_baseline = task_command.get('requires_baseline', False)
                    query_type = task_command.get('query_type', 'object')

                    objects_to_detect = task_command.get('parameters', {}).get('objects_to_detect', [])
                    activities_to_detect = task_command.get('parameters', {}).get('activities_to_detect', [])

                    if expected_change:
                        adhoc_query = expected_change
                    elif target_object:
                        adhoc_query = target_object
                    elif objects_to_detect:
                        adhoc_query = ', '.join(objects_to_detect)
                    elif activities_to_detect:
                        adhoc_query = ', '.join(activities_to_detect)
                    elif understood_intent:
                        adhoc_query = understood_intent

                all_queries = list(db_task_queries)
                has_monitoring_tasks = len(db_task_queries) > 0
                if adhoc_query:
                    all_queries.append(adhoc_query)

                if len(all_queries) == 1:
                    user_query = all_queries[0]
                elif len(all_queries) > 1:
                    numbered = [f"{i+1}. {q}" for i, q in enumerate(all_queries)]
                    user_query = "\n".join(numbered)

                # ── Build vision context ──────────────────────────────────
                vision_context = None
                if user_query and requires_baseline and task_id and task_id in baseline_states:
                    baseline_info = baseline_states[task_id]
                    vision_context = (
                        f"BASELINE: {baseline_info['state']}\n"
                        f"EXPECTED CHANGE: {expected_change}\n"
                        f"TIME TRACKING: {(datetime.utcnow() - baseline_info['established_at']).seconds}s elapsed"
                    )

                # ── Analyse frame (Claude API — slow) ─────────────────────
                analysis = await vision_agent.analyze_frame(
                    frame, camera_id,
                    previous_context=vision_context,
                    user_query=user_query,
                    monitoring_mode=has_monitoring_tasks and not requires_baseline,
                )

                # ── Establish baseline if needed ──────────────────────────
                if user_query and requires_baseline and task_id and task_id not in baseline_states:
                    if analysis.get('baseline_established', False):
                        current_state = analysis.get('current_state', analysis.get('scene_description', ''))
                        baseline_states[task_id] = {
                            'state': current_state,
                            'established_at': datetime.utcnow()
                        }
                        logger.info(f"[CAM-{camera_id}] Baseline established: {current_state[:100]}")
                        await manager.send_system_message("baseline_established", {
                            "camera_id": camera_id,
                            "task_id": task_id,
                            "message": f"Baseline set for Camera {camera_id}: {current_state[:150]}. Now monitoring...",
                            "baseline_state": current_state
                        })

                # ── Query/confidence resolution ───────────────────────────
                query_match = analysis.get('query_match', False)
                query_confidence = analysis.get('query_confidence', 0)
                baseline_match = analysis.get('baseline_match', None)

                if user_query:
                    logger.info(
                        f"[CAM-{camera_id}] query_match={query_match} "
                        f"query_confidence={query_confidence} "
                        f"monitoring={has_monitoring_tasks} "
                        f"details={str(analysis.get('query_details', ''))[:120]}"
                    )

                if requires_baseline and task_id in baseline_states:
                    if baseline_match is False:
                        if query_confidence >= 40:
                            query_confidence = max(query_confidence, 85)
                            query_match = True
                            analysis['query_confidence'] = query_confidence
                            analysis['query_match'] = True
                        elif query_confidence >= 20:
                            query_confidence = 60
                            query_match = True
                            analysis['query_confidence'] = query_confidence
                            analysis['query_match'] = True

                # ── Claude reasoning override ─────────────────────────────
                if reasoning_agent and user_query:
                    try:
                        reasoning_agent.add_observation(analysis)
                        baseline_for_claude = baseline_states[task_id]['state'] if (task_id and task_id in baseline_states) else None
                        claude_decision = await reasoning_agent.analyze_scene_progression(
                            user_query=user_query,
                            baseline_state=baseline_for_claude,
                            current_observation=analysis,
                            previous_observations=reasoning_agent.get_observation_history()
                        )
                        if claude_decision.get('should_alert') and claude_decision.get('confidence_percentage', 0) > query_confidence:
                            query_confidence = claude_decision.get('confidence_percentage', query_confidence)
                            query_match = True
                            analysis['query_confidence'] = query_confidence
                            analysis['query_match'] = True
                            analysis['query_details'] = claude_decision.get('alert_message', analysis.get('query_details', ''))
                            analysis['claude_reasoning'] = claude_decision.get('reasoning', '')
                            analysis['claude_decision'] = True
                    except Exception as e:
                        logger.warning(f"[CAM-{camera_id}] Claude reasoning error: {e}")

                # ── Context ───────────────────────────────────────────────
                try:
                    context_summary = await context_agent.get_context_for_event(
                        analysis.get('scene_description', ''), datetime.utcnow(), camera_id
                    )
                except Exception as ctx_err:
                    logger.warning(f"[CAM-{camera_id}] Context agent error (non-fatal): {ctx_err}")
                    context_summary = "No historical context available"

                # ── Significance ──────────────────────────────────────────
                significance = vision_agent.calculate_significance_score(analysis)
                if user_query and requires_baseline and query_match:
                    significance = max(significance, query_confidence)

                # ── Save frame ────────────────────────────────────────────
                timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                frame_filename = f"camera{camera_id}_{timestamp_str}.jpg"
                frame_path = event_frames_dir / frame_filename
                cv2.imwrite(str(frame_path), frame)
                frame_url = f"/event_frames/{frame_filename}"

                detections_list = analysis.get('detections', [])
                detected_objects = [d.get('label', '') for d in detections_list]

                # ── Analysis WebSocket update ─────────────────────────────
                await manager.send_analysis_update({
                    "camera_id": camera_id,
                    "scene_description": analysis.get('scene_description', ''),
                    "significance": significance,
                    "detections": detections_list,
                    "detected_objects": detected_objects,
                    "detection_count": len(detections_list),
                    "context": context_summary,
                    "frame_url": frame_url,
                    "frame_base64": frame_base64,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # ── Immediate alert decision ──────────────────────────────
                scene_text = analysis.get('scene_description', '').lower()
                activity_text = analysis.get('activity', '').lower()
                combined_text = scene_text + ' ' + activity_text

                critical_keywords = ['weapon', 'gun', 'knife', 'violence', 'fight', 'attack',
                                      'threat', 'dangerous', 'hazard', 'fire', 'smoke', 'blood',
                                      'injury', 'fall', 'accident', 'emergency']
                has_dangerous_keyword = any(kw in combined_text for kw in critical_keywords)

                query_match = analysis.get('query_match', False)
                query_confidence = analysis.get('query_confidence', 0)
                immediate_threshold = settings.IMMEDIATE_ALERT_THRESHOLD
                activity_threshold = settings.ACTIVITY_DETECTION_THRESHOLD if requires_baseline else immediate_threshold

                should_send_immediate = False
                alert_reason = []

                if has_dangerous_keyword:
                    should_send_immediate = True
                    alert_reason.append("dangerous_keyword")

                if user_query and query_match and query_confidence >= activity_threshold:
                    should_send_immediate = True
                    alert_reason.append(f"query_matched_{query_confidence}%")

                if should_send_immediate:
                    if has_dangerous_keyword:
                        severity = "CRITICAL"
                        title = f"CRITICAL DANGER - Camera {camera_id}"
                    elif requires_baseline:
                        severity = "CRITICAL"
                        title = f"CRITICAL EVENT: {user_query.title()} - Camera {camera_id}"
                    else:
                        severity = "CRITICAL" if query_confidence >= 80 else "WARNING"
                        title = f"{user_query.title()} Detected - Camera {camera_id}"

                    if user_query and query_match and requires_baseline and task_id in baseline_states:
                        baseline_info = baseline_states[task_id]
                        time_elapsed = (datetime.utcnow() - baseline_info['established_at']).seconds
                        time_str = f"{time_elapsed}s" if time_elapsed < 60 else f"{time_elapsed // 60}m"
                        alert_msg = (
                            f"Camera {camera_id} detected {analysis.get('query_details', user_query).lower()}.\n\n"
                            f"Baseline: {baseline_info['state'][:120].lower()}\n"
                            f"Now: {analysis.get('scene_description', '')[:120].lower()}\n\n"
                            f"Confidence: {query_confidence}% | Triggered {time_str} after monitoring started."
                        )
                    elif user_query and query_match:
                        alert_msg = (
                            f"Camera {camera_id} found: {user_query.lower()} ({query_confidence}% confidence).\n\n"
                            f"{analysis.get('query_details', analysis.get('scene_description', ''))}"
                        )
                    else:
                        alert_msg = (
                            f"Camera {camera_id}: {analysis.get('scene_description', 'Hazardous situation detected')}"
                        )

                    immediate_alert_data = {
                        "id": f"immediate_{camera_id}_{int(datetime.utcnow().timestamp())}",
                        "severity": severity,
                        "title": title,
                        "message": alert_msg,
                        "camera_id": camera_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "significance": query_confidence if user_query else significance,
                        "frame_url": frame_url,
                        "frame_base64": frame_base64,
                        "detections": detections_list,
                        "detected_objects": detected_objects,
                        "alert_type": "immediate",
                        "user_query": user_query,
                        "query_confidence": query_confidence,
                        "is_read": False
                    }
                    await manager.send_alert(immediate_alert_data)
                    try:
                        await email_service.send_critical_alert(alert_data=immediate_alert_data)
                    except Exception as e:
                        logger.error(f"[CAM-{camera_id}] Alert email failed: {e}")

                elif not should_send_immediate and significance >= 50:
                    critical_events.append({
                        'timestamp': current_time.isoformat(),
                        'analysis': analysis,
                        'significance': significance,
                        'detected_objects': detected_objects,
                        'detections_list': detections_list,
                        'frame_url': frame_url,
                        'frame_path': frame_path,
                        'frame_base64': frame_base64,
                        'context': context_summary
                    })

                # ── DB persistence ────────────────────────────────────────
                try:
                    db = SessionLocal()
                    event = Event(
                        camera_id=camera_id,
                        event_type="scene_analysis",
                        description=analysis.get('activity', ''),
                        scene_description=analysis.get('scene_description', ''),
                        significance_score=significance,
                        severity=vision_agent.determine_alert_severity(analysis),
                        context_summary=context_summary,
                        event_metadata=analysis
                    )
                    db.add(event)
                    db.flush()

                    try:
                        embedding_id = await context_agent.store_scene_description(
                            event.id, camera_id, event.timestamp,
                            event.scene_description, {"significance": event.significance_score}
                        )
                        event.embedding_id = embedding_id
                    except Exception as emb_err:
                        logger.warning(f"[CAM-{camera_id}] Embedding store failed (non-fatal): {emb_err}")

                    for det in vision_agent.extract_detections_for_storage(analysis):
                        db.add(Detection(event_id=event.id, camera_id=camera_id, **det))

                    if event.significance_score >= settings.WARNING_THRESHOLD:
                        db.add(Alert(
                            event_id=event.id,
                            severity=event.severity,
                            title=f"{event.severity.value} Alert - Camera {camera_id}",
                            message=event.scene_description
                        ))

                    db.commit()
                    db.close()
                except Exception as db_error:
                    logger.warning(f"[CAM-{camera_id}] DB save failed: {db_error}")
                    try:
                        db.rollback()
                        db.close()
                    except Exception:
                        pass

                # ── 2-minute summary ──────────────────────────────────────
                if elapsed_seconds >= ANALYSIS_INTERVAL_SECONDS:
                    if critical_events:
                        most_significant = max(critical_events, key=lambda x: x['significance'])
                        all_objects = set()
                        activities = []
                        for ev in critical_events:
                            all_objects.update(ev['detected_objects'])
                            act = ev['analysis'].get('activity', '')
                            if act and act not in activities:
                                activities.append(act)

                        severity = "CRITICAL" if most_significant['significance'] >= 80 else "WARNING"
                        title = f"Activity Summary (2-min) - Camera {camera_id}"
                        alert_msg = (
                            f"2-Minute Summary for Camera {camera_id} "
                            f"({minute_start_time.strftime('%H:%M:%S')} - {current_time.strftime('%H:%M:%S')})\n\n"
                            f"Most significant: {most_significant['analysis'].get('scene_description', '')}\n\n"
                            f"Activities: {' → '.join(activities[:3]) if activities else 'None'}\n"
                            f"Objects seen: {', '.join(sorted(all_objects)) if all_objects else 'None'}\n"
                            f"Events recorded: {len(critical_events)}"
                        )
                        alert_data = {
                            "id": f"summary_{camera_id}_{int(current_time.timestamp())}",
                            "severity": severity,
                            "title": title,
                            "message": alert_msg,
                            "camera_id": camera_id,
                            "timestamp": current_time.isoformat(),
                            "significance": most_significant['significance'],
                            "frame_url": most_significant['frame_url'],
                            "frame_base64": most_significant['frame_base64'],
                            "detections": most_significant['detections_list'],
                            "detected_objects": list(all_objects),
                            "event_count": len(critical_events),
                            "is_read": False
                        }
                        await manager.send_alert(alert_data)
                        try:
                            await email_service.send_summary_email(alert_data=alert_data)
                        except Exception as e:
                            logger.error(f"[CAM-{camera_id}] Summary email failed: {e}")

                    minute_start_time = current_time
                    critical_events = []
                    logger.info(f"[CAM-{camera_id}] New 2-minute period started")

                consecutive_errors = 0
                await asyncio.sleep(ANALYSIS_EVERY)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                    backoff = min(30, 5 * consecutive_errors)
                    logger.warning(f"[CAM-{camera_id}] Rate limit hit, backing off {backoff}s")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"[CAM-{camera_id}] Analysis error: {e}")
                    await asyncio.sleep(min(10, consecutive_errors))

    # Run both loops concurrently; if either exits, cancel the other
    try:
        await asyncio.gather(_frame_streamer(), _analysis_loop())
    except asyncio.CancelledError:
        logger.info(f"[CAM-{camera_id}] Worker cancelled cleanly")


# ─────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ThirdEye Intelligent Monitoring System...")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing): {e}")

    # Auto-restart cameras that were active before the last shutdown.
    # Workers are in-memory only and don't survive a process restart, so any
    # camera still marked is_active=True in the DB needs its worker re-spawned.
    try:
        from database import SessionLocal, Camera as CameraModel
        db = SessionLocal()
        active_cameras = db.query(CameraModel).filter(CameraModel.is_active == True).all()
        for cam in active_cameras:
            try:
                raw = cam.stream_url or "0"
                source = int(raw) if raw.strip().lstrip('-').isdigit() else raw
                success = await camera_service.initialize_camera(cam.id, source, fps=cam.fps)
                if success:
                    start_camera_worker(cam.id)
                    logger.info(f"[STARTUP] Auto-restarted camera {cam.id} ({cam.name})")
                else:
                    cam.is_active = False
                    db.commit()
                    logger.warning(f"[STARTUP] Could not open camera {cam.id} ({cam.name}), marked inactive")
            except Exception as cam_err:
                logger.warning(f"[STARTUP] Error restarting camera {cam.id}: {cam_err}")
                cam.is_active = False
                db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"[STARTUP] Auto-restart check failed: {e}")

    yield

    logger.info("Shutting down — stopping all camera workers...")
    for camera_id in list(camera_workers.keys()):
        stop_camera_worker(camera_id)
    await camera_service.stop_all_cameras()

    # Mark all cameras inactive in DB on clean shutdown
    try:
        from database import SessionLocal, Camera as CameraModel
        db = SessionLocal()
        db.query(CameraModel).filter(CameraModel.is_active == True).update({"is_active": False})
        db.commit()
        db.close()
        logger.info("All cameras marked inactive in DB")
    except Exception as e:
        logger.warning(f"Could not mark cameras inactive on shutdown: {e}")

    logger.info("All cameras stopped")


# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────
app = FastAPI(
    title="ThirdEye Monitoring API",
    description="AI-powered surveillance system with Gemini integration",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])
app.include_router(ws_router, tags=["websocket"])

event_frames_path = Path(__file__).parent / "event_frames"
event_frames_path.mkdir(exist_ok=True)
app.mount("/event_frames", StaticFiles(directory=str(event_frames_path)), name="event_frames")


@app.get("/")
async def root():
    return {
        "name": "ThirdEye Intelligent Monitoring System",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "active_cameras": len(camera_workers)
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "active_camera_workers": len(camera_workers)}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
