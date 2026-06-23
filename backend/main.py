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

# AI Commands issued from the Intelligence page while zero cameras are active
# live here in-memory until a camera comes online. Each entry is a dict with
# keys: original_command, command, task_type, priority, queued_at.
pending_ai_commands: list[dict] = []

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

    # Flush any AI Commands that were queued while no cameras were running.
    # They attach to every camera that comes online from now on.
    _attach_pending_ai_commands_to_camera(camera_id)

    task = asyncio.create_task(_camera_worker(camera_id))
    camera_workers[camera_id] = task
    logger.info(f"[CAM-{camera_id}] Worker task started")


def _attach_pending_ai_commands_to_camera(camera_id: int) -> int:
    """Persist every queued AI Command as a CameraTask row for `camera_id`.

    Returns the number of commands attached. Safe to call even when the
    queue is empty. Does not clear the queue — pending AI Commands stay
    armed so that any subsequent cameras also pick them up. Use
    `clear_pending_ai_command(...)` to actually drop one.
    """
    if not pending_ai_commands:
        return 0

    try:
        from database import SessionLocal, CameraTask
    except Exception as exc:  # pragma: no cover — DB offline during smoke tests
        logger.warning(f"[CAM-{camera_id}] Cannot flush pending AI commands: {exc}")
        return 0

    attached = 0
    db = SessionLocal()
    try:
        from sqlalchemy import func as _sa_func
        for pending in pending_ai_commands:
            pending_original = (pending.get("original_command") or "").strip()
            if not pending_original:
                continue
            # Skip if the same original command is already attached (e.g. the
            # worker was restarted while DB rows still exist). Match tolerantly
            # so historical rows with trailing whitespace are treated as a
            # match — prevents duplicate re-arming.
            existing = (
                db.query(CameraTask)
                .filter(
                    CameraTask.camera_id == camera_id,
                    CameraTask.source == "ai_command",
                    _sa_func.trim(CameraTask.original_command) == pending_original,
                    CameraTask.is_active == True,  # noqa: E712
                )
                .first()
            )
            if existing:
                continue

            task_row = CameraTask(
                camera_id=camera_id,
                command=(pending.get("command") or pending_original or "").strip(),
                task_type=pending.get("task_type", "custom"),
                is_default=False,
                is_active=True,
                priority=pending.get("priority", 2),
                source="ai_command",
                original_command=pending_original,
            )
            db.add(task_row)
            attached += 1
        if attached:
            db.commit()
            logger.info(
                f"[CAM-{camera_id}] Attached {attached} queued AI command(s) from pending queue"
            )
    except Exception as exc:
        db.rollback()
        logger.warning(f"[CAM-{camera_id}] Failed to attach pending AI commands: {exc}")
    finally:
        db.close()
    return attached


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

    # Shared state between streamer and analyser. `seq` is bumped on every
    # new frame so the analysis loop can tell "is this a new frame or the
    # same one I already analysed?" and avoid wasting Claude calls.
    latest_frame = {"frame": None, "base64": None, "seq": 0}
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

                # Update shared state for the analysis loop. Bumping the seq
                # lets the analyser detect a genuinely new frame vs. the same
                # one it already processed (avoids redundant Claude calls).
                latest_frame["frame"] = frame
                latest_frame["base64"] = frame_b64
                latest_frame["seq"] = latest_frame.get("seq", 0) + 1

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

        # How long to wait between *Claude* calls at minimum. A new frame
        # from the streamer can trigger an analysis sooner than the legacy
        # fixed interval, but never faster than this throttle.
        MIN_INTERVAL = float(getattr(settings, "ANALYSIS_MIN_INTERVAL_SECONDS", 3.0))
        POLL_SLEEP = 0.5  # how often to check for a new frame

        last_analyzed_seq = -1
        last_analyzed_at = 0.0
        consecutive_errors = 0

        while True:
            try:
                current_time = datetime.utcnow()
                elapsed_seconds = (current_time - minute_start_time).total_seconds()

                frame = latest_frame["frame"]
                frame_base64 = latest_frame["base64"]
                frame_seq = latest_frame.get("seq", 0)
                if frame is None:
                    await asyncio.sleep(1)
                    continue

                # Deduplicate + throttle: only hit Claude when we actually
                # have a new frame AND the min-interval has elapsed. This
                # fixes two old bugs at once — (1) calling Claude 6× on the
                # same stale frame, and (2) missing short events because
                # capture FPS was too low.
                now_monotonic = asyncio.get_event_loop().time()
                frame_is_new = frame_seq != last_analyzed_seq
                interval_elapsed = (now_monotonic - last_analyzed_at) >= MIN_INTERVAL
                if not (frame_is_new and interval_elapsed):
                    await asyncio.sleep(POLL_SLEEP)
                    continue

                last_analyzed_seq = frame_seq
                last_analyzed_at = now_monotonic
                cycle_start = now_monotonic
                stage_times: dict[str, float] = {}

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

                # Every ACTIVE in-memory task contributes a query. The first
                # baseline-requiring task wins the baseline slot; all others
                # are appended as plain detection queries.
                active_tasks = cmd_agent.get_active_tasks()
                adhoc_queries: list[str] = []

                for tid, t in active_tasks.items():
                    task_command = t.get('command', {}) or {}
                    tparams = task_command.get('parameters', {}) or {}

                    if task_command.get('requires_baseline') and task_id is None:
                        task_id = tid
                        target_object = task_command.get('target', '')
                        expected_change = task_command.get('expected_change', '')
                        requires_baseline = True
                        query_type = task_command.get('query_type', 'object')

                    q = (
                        task_command.get('expected_change')
                        or task_command.get('target')
                        or (', '.join(tparams.get('objects_to_detect', []) or []) or None)
                        or (', '.join(tparams.get('activities_to_detect', []) or []) or None)
                        or task_command.get('understood_intent')
                    )
                    if q:
                        adhoc_queries.append(q)

                # De-dup while preserving order so multi-arm of the same
                # command doesn't inflate the rule list sent to Claude.
                seen_q = set()
                adhoc_queries = [q for q in adhoc_queries if not (q in seen_q or seen_q.add(q))]

                all_queries = list(db_task_queries)
                has_monitoring_tasks = len(db_task_queries) > 0
                for q in adhoc_queries:
                    if q not in all_queries:
                        all_queries.append(q)

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
                _t0 = asyncio.get_event_loop().time()
                analysis = await vision_agent.analyze_frame(
                    frame, camera_id,
                    previous_context=vision_context,
                    user_query=user_query,
                    monitoring_mode=has_monitoring_tasks and not requires_baseline,
                )
                stage_times["vision"] = asyncio.get_event_loop().time() - _t0

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
                else:
                    logger.debug(
                        f"[CAM-{camera_id}] no active trigger — "
                        f"analysing scene but no alerts will be fired"
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

                # ── Claude reasoning override (conditional) ───────────────
                # The reasoning agent is a ~5s second Claude call. Running it
                # on every cycle roughly doubles our latency and cuts the
                # number of frames we can actually sample per minute in half.
                # Only invoke it when it can meaningfully affect the decision:
                #   • baseline-tracking tasks (need scene-progression context)
                #   • borderline confidence (20–70) where a second opinion
                #     might flip the decision either way
                # Skip it when the vision agent is already very sure (high
                # confidence yes or low confidence no), since reasoning can
                # only *raise* confidence — it never overrides a confident
                # "yes" downward.
                needs_reasoning = bool(
                    reasoning_agent
                    and user_query
                    and (
                        requires_baseline
                        or (20 <= int(query_confidence or 0) < 70)
                        or query_match  # confirm positives
                    )
                )
                if needs_reasoning:
                    try:
                        _t0 = asyncio.get_event_loop().time()
                        reasoning_agent.add_observation(analysis)
                        baseline_for_claude = baseline_states[task_id]['state'] if (task_id and task_id in baseline_states) else None
                        claude_decision = await reasoning_agent.analyze_scene_progression(
                            user_query=user_query,
                            baseline_state=baseline_for_claude,
                            current_observation=analysis,
                            previous_observations=reasoning_agent.get_observation_history()
                        )
                        stage_times["reasoning"] = asyncio.get_event_loop().time() - _t0
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
                else:
                    stage_times["reasoning"] = 0.0
                    if reasoning_agent and user_query:
                        # Still keep observation history in sync so when we DO
                        # run reasoning later it has continuity.
                        try:
                            reasoning_agent.add_observation(analysis)
                        except Exception:
                            pass

                # ── Context ───────────────────────────────────────────────
                _t0 = asyncio.get_event_loop().time()
                try:
                    context_summary = await context_agent.get_context_for_event(
                        analysis.get('scene_description', ''), datetime.utcnow(), camera_id
                    )
                except Exception as ctx_err:
                    logger.warning(f"[CAM-{camera_id}] Context agent error (non-fatal): {ctx_err}")
                    context_summary = "No historical context available"
                stage_times["context"] = asyncio.get_event_loop().time() - _t0

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
                # Only fire an alert if the USER has actually asked us to
                # monitor something on this camera. Raw scene severity (fires,
                # weapons, etc.) without an active user task is logged as an
                # event but does not generate an alert — the user only wants
                # alerts for the things they triggered.
                query_match = analysis.get('query_match', False)
                query_confidence = analysis.get('query_confidence', 0)

                # Safety net for MALFORMED Claude responses only. When
                # monitoring_mode=True we explicitly ask Claude to evaluate
                # every rule and return query_match=true/false. If Claude
                # returned an explicit false (or "none of the rules are
                # triggered"), we MUST respect that — otherwise we'll flag
                # unrelated objects (e.g. a glass bottle) as a water bottle
                # match and produce false positives.
                #
                # This fallback therefore only fires when the field is
                # actually absent from the response (parsing glitch / model
                # skipped the field), not when Claude decided "no".
                claude_evaluated = "query_match" in analysis
                if user_query and not query_match and not claude_evaluated:
                    import re as _re
                    stopwords = {
                        "alert", "me", "if", "you", "see", "any", "a", "an",
                        "the", "is", "are", "there", "on", "in", "of", "for",
                        "to", "and", "or", "when", "camera", "watch", "monitor",
                        "look", "find", "detects", "detect",
                    }
                    query_tokens = {
                        t for t in _re.findall(r"[a-zA-Z]{3,}", user_query.lower())
                        if t not in stopwords
                    }
                    best_det_conf = 0.0
                    matched_label = None
                    for d in analysis.get("detections", []):
                        label = str(d.get("label", "")).lower()
                        if not label or not query_tokens:
                            continue
                        label_tokens = set(_re.findall(r"[a-zA-Z]{3,}", label))
                        # Require the FULL multi-word phrase to appear in the
                        # detection label so "water bottle" does NOT match a
                        # bare "bottle" — that's what produced the false
                        # positive in the screenshot.
                        if len(query_tokens) > 1 and not query_tokens.issubset(label_tokens):
                            continue
                        if len(query_tokens) == 1 and not (query_tokens & label_tokens):
                            continue
                        conf = float(d.get("confidence", 0) or 0)
                        if conf <= 1.0:
                            conf *= 100.0
                        if conf > best_det_conf:
                            best_det_conf = conf
                            matched_label = label
                    if matched_label:
                        inferred = int(max(best_det_conf, 75))
                        logger.info(
                            f"[CAM-{camera_id}] detection-fallback matched "
                            f"'{matched_label}' for trigger '{user_query}' "
                            f"(Claude response was malformed) "
                            f"-> query_match=True confidence={inferred}"
                        )
                        query_match = True
                        query_confidence = max(query_confidence, inferred)
                        analysis["query_match"] = True
                        analysis["query_confidence"] = query_confidence
                        if not analysis.get("query_details"):
                            analysis["query_details"] = (
                                f"Detected '{matched_label}' which matches your "
                                f"trigger \"{user_query}\"."
                            )

                # For a user-defined DB monitoring task, we want to be more
                # sensitive (the user explicitly asked us to watch for this),
                # so fall back to the lower activity threshold instead of the
                # stricter immediate-action one.
                if requires_baseline:
                    activity_threshold = settings.ACTIVITY_DETECTION_THRESHOLD
                elif has_monitoring_tasks:
                    activity_threshold = min(
                        settings.IMMEDIATE_ALERT_THRESHOLD,
                        settings.ACTIVITY_DETECTION_THRESHOLD,
                    )
                else:
                    activity_threshold = settings.IMMEDIATE_ALERT_THRESHOLD

                should_send_immediate = bool(
                    user_query and query_match and query_confidence >= activity_threshold
                )

                if user_query:
                    logger.info(
                        f"[CAM-{camera_id}] decision: match={query_match} "
                        f"conf={query_confidence} threshold={activity_threshold} "
                        f"-> fire={should_send_immediate}"
                    )

                if should_send_immediate:
                    if requires_baseline:
                        severity = "CRITICAL"
                        title = f"Trigger matched: {user_query.title()}"
                    else:
                        severity = "CRITICAL" if query_confidence >= 80 else "WARNING"
                        title = f"Trigger matched: {user_query.title()}"

                    # Human-readable message shown in the alert row
                    if requires_baseline and task_id in baseline_states:
                        baseline_info = baseline_states[task_id]
                        time_elapsed = (datetime.utcnow() - baseline_info['established_at']).seconds
                        time_str = f"{time_elapsed}s" if time_elapsed < 60 else f"{time_elapsed // 60}m"
                        alert_msg = (
                            f"Camera {camera_id} detected {analysis.get('query_details', user_query).lower()}. "
                            f"({query_confidence}% confidence, {time_str} after monitoring began)"
                        )
                    else:
                        alert_msg = (
                            f"Camera {camera_id} matched your monitoring trigger "
                            f"\"{user_query}\" with {query_confidence}% confidence."
                        )

                    # Rich reasoning / evidence payload persisted to DB so the
                    # Alerts page can show WHY the model considered this an alert.
                    claude_reasoning = analysis.get('claude_reasoning', '')
                    query_details = analysis.get('query_details', '')
                    scene_description = analysis.get('scene_description', '')
                    activity = analysis.get('activity', '')

                    reasoning_parts = []
                    if query_details:
                        reasoning_parts.append(f"Match evidence: {query_details}")
                    if claude_reasoning:
                        reasoning_parts.append(f"Model reasoning: {claude_reasoning}")
                    if scene_description:
                        reasoning_parts.append(f"Scene: {scene_description}")
                    if activity:
                        reasoning_parts.append(f"Activity: {activity}")
                    reasoning_text = "\n\n".join(reasoning_parts)

                    alert_metadata = {
                        "camera_id": camera_id,
                        "user_query": user_query,
                        "query_confidence": query_confidence,
                        "query_details": query_details,
                        "claude_reasoning": claude_reasoning,
                        "scene_description": scene_description,
                        "activity": activity,
                        "reasoning": reasoning_text,
                        "frame_url": frame_url,
                        "detected_objects": detected_objects,
                        "detections": [
                            {
                                "label": d.get("label", ""),
                                "confidence": d.get("confidence", 0),
                                "location": d.get("location", ""),
                            }
                            for d in detections_list
                        ],
                        "significance": query_confidence,
                        "requires_baseline": requires_baseline,
                        "alert_type": "trigger_match",
                    }

                    # Persist alert + its backing event so it survives refresh
                    persisted_id = None
                    try:
                        adb = SessionLocal()
                        ev = Event(
                            camera_id=camera_id,
                            event_type="trigger_match",
                            description=user_query,
                            scene_description=scene_description,
                            significance_score=query_confidence,
                            severity=AlertSeverity.CRITICAL if severity == "CRITICAL" else AlertSeverity.WARNING,
                            context_summary=context_summary,
                            event_metadata={**analysis, "user_query": user_query},
                        )
                        adb.add(ev)
                        adb.flush()
                        new_alert = Alert(
                            event_id=ev.id,
                            severity=AlertSeverity.CRITICAL if severity == "CRITICAL" else AlertSeverity.WARNING,
                            title=title,
                            message=alert_msg,
                            alert_metadata=alert_metadata,
                        )
                        adb.add(new_alert)
                        adb.commit()
                        persisted_id = new_alert.id
                        adb.close()
                    except Exception as db_err:
                        logger.warning(f"[CAM-{camera_id}] Failed to persist alert: {db_err}")
                        try:
                            adb.rollback()
                            adb.close()
                        except Exception:
                            pass

                    immediate_alert_data = {
                        "id": persisted_id if persisted_id is not None
                              else f"immediate_{camera_id}_{int(datetime.utcnow().timestamp())}",
                        "severity": severity,
                        "title": title,
                        "message": alert_msg,
                        "camera_id": camera_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "significance": query_confidence,
                        "frame_url": frame_url,
                        "frame_base64": frame_base64,
                        "detections": detections_list,
                        "detected_objects": detected_objects,
                        "alert_type": "trigger_match",
                        "user_query": user_query,
                        "query_confidence": query_confidence,
                        "query_details": query_details,
                        "claude_reasoning": claude_reasoning,
                        "scene_description": scene_description,
                        "activity": activity,
                        "reasoning": reasoning_text,
                        "is_read": False,
                    }
                    await manager.send_alert(immediate_alert_data)
                    try:
                        await email_service.send_critical_alert(alert_data=immediate_alert_data)
                    except Exception as e:
                        logger.error(f"[CAM-{camera_id}] Alert email failed: {e}")

                elif user_query and not should_send_immediate and significance >= 50:
                    # Collect for the 2-minute summary, but only while a user
                    # monitoring task is active on this camera.
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

                    # NOTE: We intentionally do NOT create an Alert row here
                    # anymore. Alerts are only created for user-triggered
                    # matches (see the immediate alert block above) so the
                    # Alerts page shows the things the user asked to monitor
                    # instead of a stream of generic severity events.

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

                # Per-cycle timing summary so we can see exactly where the
                # wall-clock time is going. If the total cycle is much longer
                # than vision+reasoning+context combined, the remainder is
                # DB/frame-save/websocket overhead and we know where to look.
                cycle_total = asyncio.get_event_loop().time() - cycle_start
                try:
                    logger.info(
                        f"[CAM-{camera_id}] cycle={cycle_total:.2f}s "
                        f"vision={stage_times.get('vision', 0):.2f}s "
                        f"reasoning={stage_times.get('reasoning', 0):.2f}s "
                        f"context={stage_times.get('context', 0):.2f}s "
                        f"(reasoning_{'on' if stage_times.get('reasoning', 0) > 0 else 'skipped'})"
                    )
                except Exception:
                    pass

                # Pacing is handled by the dedupe + MIN_INTERVAL gate at the
                # top of the loop; a short sleep here just prevents a tight
                # busy-loop when no new frames are arriving.
                await asyncio.sleep(POLL_SLEEP)

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

    # Lightweight, idempotent column migrations. `init_db()` only creates
    # tables that don't exist — it never adds columns to existing tables,
    # so we bring older databases up to the latest schema here.
    try:
        from sqlalchemy import text as _sql_text
        from database import engine as _engine
        with _engine.begin() as _conn:
            _conn.execute(_sql_text(
                "ALTER TABLE camera_tasks "
                "ADD COLUMN IF NOT EXISTS source VARCHAR(50) "
                "NOT NULL DEFAULT 'manual'"
            ))
            _conn.execute(_sql_text(
                "ALTER TABLE camera_tasks "
                "ADD COLUMN IF NOT EXISTS original_command TEXT"
            ))
            _conn.execute(_sql_text(
                "CREATE INDEX IF NOT EXISTS ix_camera_tasks_source "
                "ON camera_tasks (source)"
            ))
        logger.info("Schema migration: camera_tasks.source/original_command ready")
    except Exception as e:
        logger.warning(f"camera_tasks schema migration skipped: {e}")

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
