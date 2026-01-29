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

from config import settings
from database import init_db
from api import router, ws_router
from services import camera_service

# Initialize shared agents (must be before importing routes that use them)
from agents import CommandAgent
command_agent = CommandAgent()  # Shared global instance

# Initialize email service
from services.email_service import email_service

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown
    """
    # Startup
    logger.info("Starting ThirdEye Intelligent Monitoring System...")

    # Initialize database (optional - continue if fails)
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing without database): {e}")
        logger.info("Some features requiring database access will not be available")

    # Start background tasks
    asyncio.create_task(surveillance_worker())
    logger.info("Surveillance worker started")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await camera_service.stop_all_cameras()
    logger.info("All cameras stopped")


# Create FastAPI app
app = FastAPI(
    title="ThirdEye Monitoring API",
    description="AI-powered surveillance system with Gemini integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api", tags=["api"])
app.include_router(ws_router, tags=["websocket"])

# Mount event frames directory for static file access
from pathlib import Path
event_frames_path = Path(__file__).parent / "event_frames"
event_frames_path.mkdir(exist_ok=True)
app.mount("/event_frames", StaticFiles(directory=str(event_frames_path)), name="event_frames")


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "name": "ThirdEye Intelligent Monitoring System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """
    Health check endpoint
    """
    return {"status": "healthy"}


# Background worker for surveillance processing
async def surveillance_worker():
    """
    Background worker with 1-minute analysis intervals to reduce noise
    """
    from agents import VisionAgent, ContextAgent, CommandAgent
    from api import manager
    from database import SessionLocal, Event, Detection, Alert, AlertSeverity
    from datetime import datetime, timedelta
    import base64
    import cv2
    import os
    from pathlib import Path

    vision_agent = VisionAgent()
    context_agent = ContextAgent()
    # Use the global command_agent instance (defined at module level)
    global command_agent
    
    # Initialize Claude-based reasoning agent
    try:
        from agents.reasoning_agent import ReasoningAgent
        reasoning_agent = ReasoningAgent()
        logger.info("✅ Reasoning Agent (Claude) initialized")
    except Exception as e:
        logger.warning(f"⚠️ Reasoning Agent not available: {e}")
        reasoning_agent = None

    # Create event frames directory
    event_frames_dir = Path(__file__).parent / "event_frames"
    event_frames_dir.mkdir(exist_ok=True)

    logger.info("🎯 Surveillance worker started with 2-MINUTE summaries (immediate alerts >=60%)")

    # 2-minute aggregation state
    ANALYSIS_INTERVAL_SECONDS = 120  # 2 minutes for summary
    minute_start_time = datetime.utcnow()
    critical_events = []  # Store events for 2-min summary (non-immediate alerts)
    
    # Baseline state tracking for activity detection
    baseline_states = {}  # {task_id: {"state": "...", "established_at": timestamp}}

    iteration = 0
    while True:
        try:
            iteration += 1
            current_time = datetime.utcnow()
            elapsed_seconds = (current_time - minute_start_time).total_seconds()
            
            logger.info(f"[WORKER] Iteration {iteration} - Elapsed: {int(elapsed_seconds)}s/{ANALYSIS_INTERVAL_SECONDS}s, Critical events: {len(critical_events)}")

            # Get active cameras
            active_camera_count = camera_service.get_active_camera_count()
            logger.debug(f"[WORKER] Active camera count: {active_camera_count}")

            if active_camera_count > 0:
                logger.info(f"Processing {active_camera_count} active camera(s)")
                
                # Check for active user tasks
                active_tasks = command_agent.get_active_tasks()
                user_query = None
                target_object = None
                requires_baseline = False
                task_id = None
                expected_change = None
                query_type = None
                
                # Extract user query from active tasks
                if active_tasks:
                    # Get the most recent active task
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
                    
                    # Build focused query for vision agent
                    if expected_change:
                        user_query = expected_change
                    elif target_object:
                        user_query = target_object
                    elif objects_to_detect:
                        user_query = ', '.join(objects_to_detect)
                    elif activities_to_detect:
                        user_query = ', '.join(activities_to_detect)
                    elif understood_intent:
                        user_query = understood_intent
                    
                    logger.info(f"[USER QUERY ACTIVE] Type: {query_type} | Looking for: {user_query} | Requires baseline: {requires_baseline}")
                
                # Process each active camera
                for camera_id in list(camera_service.active_cameras.keys()):
                    # Capture frame
                    frame = await camera_service.capture_frame(camera_id)

                    if frame is None:
                        logger.debug(f"No frame captured from camera {camera_id}")
                        continue

                    if frame is not None:
                        logger.info(f"Processing frame from camera {camera_id}, shape: {frame.shape}")
                        try:
                            # Build context for vision agent (includes baseline for activity detection)
                            vision_context = None
                            if user_query and requires_baseline and task_id:
                                # Check if we have a baseline established
                                if task_id in baseline_states:
                                    baseline_info = baseline_states[task_id]
                                    vision_context = f"""BASELINE: {baseline_info['state']}
EXPECTED CHANGE: {expected_change}
TIME TRACKING: {(datetime.utcnow() - baseline_info['established_at']).seconds}s elapsed"""
                                    logger.info(f"[BASELINE TRACKING] Comparing to baseline established {(datetime.utcnow() - baseline_info['established_at']).seconds}s ago")
                            
                            # Analyze frame with Vision Agent - pass user query and context
                            analysis = await vision_agent.analyze_frame(
                                frame, 
                                camera_id, 
                                previous_context=vision_context,
                                user_query=user_query
                            )
                            
                            # Handle baseline establishment for activity detection
                            if user_query and requires_baseline and task_id and task_id not in baseline_states:
                                # Check if this frame establishes the baseline
                                if analysis.get('baseline_established', False):
                                    current_state = analysis.get('current_state', analysis.get('scene_description', ''))
                                    baseline_states[task_id] = {
                                        'state': current_state,
                                        'established_at': datetime.utcnow(),
                                        'frame_saved': frame_path if 'frame_path' in locals() else None
                                    }
                                    logger.info(f"[BASELINE ESTABLISHED] State: {current_state[:100]}")
                                    
                                    # Notify user that baseline is set
                                    await manager.send_system_message("baseline_established", {
                                        "task_id": task_id,
                                        "message": f"✓ Baseline established: {current_state[:150]}. Now monitoring for changes...",
                                        "baseline_state": current_state
                                    })
                            
                            # Log analysis with query match info
                            query_match = analysis.get('query_match', False)
                            query_confidence = analysis.get('query_confidence', 0)
                            baseline_match = analysis.get('baseline_match', None)
                            changes_detected = analysis.get('changes_detected', [])
                            person_present = analysis.get('person_present', None)
                            person_was_in_baseline = analysis.get('person_was_present_in_baseline', None)
                            
                            # GENERIC EMERGENCY DETECTION: Detect ANY significant change based on user query
                            if requires_baseline and task_id in baseline_states:
                                baseline_state_text = baseline_states[task_id]['state'].lower()
                                current_scene_text = analysis.get('scene_description', '').lower()
                                
                                logger.info(f"[STATE COMPARISON] Baseline match from vision: {baseline_match}")
                                logger.info(f"[STATE COMPARISON] Query confidence from vision: {query_confidence}%")
                                
                                # Check if vision agent detected a significant change (baseline_match = False)
                                # This works for ANY query, not just person leaving
                                if baseline_match == False:
                                    logger.info(f"[STATE CHANGE DETECTED] Vision agent detected baseline mismatch!")
                                    logger.info(f"[BASELINE] {baseline_state_text[:100]}")
                                    logger.info(f"[CURRENT] {current_scene_text[:100]}")
                                    
                                    # If confidence is reasonable (>= 40%), this is likely the event the user wants
                                    if query_confidence >= 40:
                                        # Boost confidence for baseline changes that match the query
                                        if query_confidence < 75:
                                            logger.warning(f"[CONFIDENCE BOOST] Baseline changed and query matched - boosting from {query_confidence}% to 85%")
                                            query_confidence = 85
                                            query_match = True
                                            analysis['query_confidence'] = 85
                                            analysis['query_match'] = True
                                            analysis['query_details'] = analysis.get('query_details', '') + f" [Baseline change detected with {query_confidence}% initial confidence]"
                                    
                                    # Even if confidence is low, if baseline doesn't match, something changed
                                    elif query_confidence >= 20:
                                        logger.warning(f"[STATE CHANGE] Baseline mismatch with low confidence ({query_confidence}%) - boosting to 60%")
                                        query_confidence = 60
                                        query_match = True
                                        analysis['query_confidence'] = 60
                                        analysis['query_match'] = True
                            
                            logger.info(f"[ANALYSIS] Camera {camera_id} - Scene: {analysis.get('scene_description', 'N/A')[:100]}")
                            if user_query:
                                if requires_baseline:
                                    logger.info(f"[ACTIVITY TRACKING] Baseline match: {baseline_match} | Person in baseline: {person_was_in_baseline} | Person now: {person_present} | Changes: {changes_detected} | Query match: {query_match} ({query_confidence}%)")
                                else:
                                    logger.info(f"[QUERY MATCH] Query: '{user_query}' | Match: {query_match} | Confidence: {query_confidence}%")
                            
                            # 🧠 CLAUDE REASONING AGENT - Analyze with AI reasoning
                            if reasoning_agent and user_query:
                                try:
                                    # Add current observation to history
                                    reasoning_agent.add_observation(analysis)
                                    
                                    # Get Claude's reasoning about whether query is satisfied
                                    baseline_for_claude = baseline_states[task_id]['state'] if (task_id and task_id in baseline_states) else None
                                    
                                    claude_decision = await reasoning_agent.analyze_scene_progression(
                                        user_query=user_query,
                                        baseline_state=baseline_for_claude,
                                        current_observation=analysis,
                                        previous_observations=reasoning_agent.get_observation_history()
                                    )
                                    
                                    logger.info(f"[CLAUDE REASONING] Event occurred: {claude_decision.get('event_occurred')} | Confidence: {claude_decision.get('confidence_percentage')}% | Should alert: {claude_decision.get('should_alert')}")
                                    logger.info(f"[CLAUDE REASONING] Reasoning: {claude_decision.get('reasoning', 'N/A')[:150]}")
                                    
                                    # Override with Claude's decision if it's more confident
                                    if claude_decision.get('should_alert') and claude_decision.get('confidence_percentage', 0) > query_confidence:
                                        logger.critical(f"🧠 CLAUDE OVERRIDE: Claude detected event with {claude_decision.get('confidence_percentage')}% confidence (higher than vision agent's {query_confidence}%)")
                                        query_confidence = claude_decision.get('confidence_percentage', query_confidence)
                                        query_match = True
                                        analysis['query_confidence'] = query_confidence
                                        analysis['query_match'] = True
                                        analysis['query_details'] = claude_decision.get('alert_message', analysis.get('query_details', ''))
                                        analysis['claude_reasoning'] = claude_decision.get('reasoning', '')
                                        analysis['claude_decision'] = True
                                        
                                except Exception as claude_error:
                                    logger.warning(f"[CLAUDE REASONING] Error: {claude_error}")

                            # Get context from Context Agent
                            context_summary = await context_agent.get_context_for_event(
                                analysis.get('scene_description', ''),
                                datetime.utcnow(),
                                camera_id
                            )

                            # Send live feed update via WebSocket (works without database)
                            _, buffer = cv2.imencode('.jpg', frame)
                            frame_base64 = base64.b64encode(buffer).decode('utf-8')

                            await manager.send_live_feed_update(
                                camera_id,
                                frame_base64,
                                analysis
                            )

                            # Calculate significance (boost for activity detection matches)
                            significance = vision_agent.calculate_significance_score(analysis)
                            
                            # Boost significance for activity matches
                            if user_query and requires_baseline and query_match:
                                significance = max(significance, query_confidence)
                                logger.info(f"[SIGNIFICANCE BOOST] Activity match detected, significance: {significance}%")

                            # Save EVERY frame with timestamp for quick access
                            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                            frame_filename = f"camera{camera_id}_{timestamp_str}.jpg"
                            frame_path = event_frames_dir / frame_filename
                            cv2.imwrite(str(frame_path), frame)
                            frame_url = f"/event_frames/{frame_filename}"
                            logger.info(f"[FRAME SAVED] Frame saved: {frame_filename}")

                            # Extract detection list for easier access
                            detections_list = analysis.get('detections', [])
                            detected_objects = [d.get('label', '') for d in detections_list]

                            # Send analysis update (works without database) with frame
                            analysis_update = {
                                "camera_id": camera_id,
                                "scene_description": analysis.get('scene_description', ''),
                                "significance": significance,
                                "detections": detections_list,  # Full detection list
                                "detected_objects": detected_objects,  # List of object names
                                "detection_count": len(detections_list),
                                "context": context_summary,
                                "frame_url": frame_url,  # Always include frame URL
                                "frame_base64": frame_base64,  # Include base64 for direct display
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            await manager.send_analysis_update(analysis_update)
                            logger.debug(f"[LIVE FEED] Updated (significance={significance}%)")

                            # Check for IMMEDIATE CRITICAL ALERTS - FOCUSED ON USER QUERY
                            scene_text = analysis.get('scene_description', '').lower()
                            activity_text = analysis.get('activity', '').lower()
                            combined_text = scene_text + ' ' + activity_text
                            
                            # Critical keywords for immediate alert (always trigger for safety)
                            critical_keywords = ['weapon', 'gun', 'knife', 'violence', 'fight', 'attack', 
                                                'threat', 'dangerous', 'hazard', 'fire', 'smoke', 'blood',
                                                'injury', 'fall', 'accident', 'emergency']
                            
                            has_dangerous_keyword = any(keyword in combined_text for keyword in critical_keywords)
                            
                            # Get query match information from analysis
                            query_match = analysis.get('query_match', False)
                            query_confidence = analysis.get('query_confidence', 0)
                            immediate_threshold = settings.IMMEDIATE_ALERT_THRESHOLD
                            
                            # IMMEDIATE ALERT TRIGGERS (FOCUSED DETECTION):
                            # 1. Dangerous keywords detected (safety - always trigger)
                            # 2. User query SPECIFICALLY MATCHED with >= threshold confidence
                            # NOTE: General activity without query match does NOT trigger immediate alerts
                            should_send_immediate = False
                            alert_reason = []
                            
                            if has_dangerous_keyword:
                                should_send_immediate = True
                                alert_reason.append("dangerous_keyword_detected")
                            
                            # Check for activity/state change match (EMERGENCY MODE - lower threshold)
                            activity_threshold = settings.ACTIVITY_DETECTION_THRESHOLD if requires_baseline else immediate_threshold
                            
                            if user_query and query_match and query_confidence >= activity_threshold:
                                should_send_immediate = True
                                if requires_baseline:
                                    alert_reason.append(f"🚨EMERGENCY_activity_detected_{query_confidence}%")
                                    logger.critical(f"🚨 EMERGENCY ALERT TRIGGERED: Activity detected with {query_confidence}% confidence (threshold: {activity_threshold}%)")
                                else:
                                    alert_reason.append(f"user_query_matched_{query_confidence}%")
                            
                            if should_send_immediate:
                                
                                logger.info(f"🚨 IMMEDIATE ALERT: Reasons={alert_reason}, Query='{user_query}', Confidence={query_confidence}%")
                                
                                # Determine alert type based on what triggered it
                                if has_dangerous_keyword:
                                    alert_type_text = "⚠️ HAZARDOUS/DANGEROUS EVENT"
                                    severity = "CRITICAL"
                                    title = f"🚨 CRITICAL DANGER ALERT - Camera {camera_id}"
                                else:
                                    # For activity detection, always use CRITICAL severity
                                    if requires_baseline:
                                        alert_type_text = f"🚨 EMERGENCY: {user_query.upper()}"
                                        severity = "CRITICAL"
                                        title = f"🚨 CRITICAL EVENT: {user_query.title()} - Camera {camera_id}"
                                    else:
                                        alert_type_text = f"🎯 FOUND: {user_query.upper()}"
                                        severity = "CRITICAL" if query_confidence >= 80 else "WARNING"
                                        title = f"✓ {user_query.title()} Detected - Camera {camera_id}"
                                
                                # Build alert message
                                if user_query and query_match:
                                    if requires_baseline and task_id in baseline_states:
                                        # Activity/State change detected - EMERGENCY FORMAT
                                        baseline_info = baseline_states[task_id]
                                        time_elapsed = (datetime.utcnow() - baseline_info['established_at']).seconds
                                        
                                        is_emergency = analysis.get('emergency_detection', False)
                                        is_claude_decision = analysis.get('claude_decision', False)
                                        claude_reasoning = analysis.get('claude_reasoning', '')
                                        
                                        # Professional voice assistant style notification
                                        time_str = f"{time_elapsed} seconds" if time_elapsed < 60 else f"{time_elapsed // 60} minute{'s' if time_elapsed // 60 > 1 else ''}"
                                        confidence_desc = 'very confident' if query_confidence >= 90 else 'confident' if query_confidence >= 70 else 'reasonably certain'
                                        
                                        alert_summary = f"""Hey, I need to notify you about something important.

I've detected {analysis.get('query_details', 'the activity you asked me to watch for').lower()}.

Here's what happened: Initially, I observed {baseline_info['state'][:120].lower()}. Now, {analysis.get('state_analysis', analysis.get('scene_description', 'the situation has changed')).lower()}.

{f"After analyzing the scene progression, I'm {confidence_desc} ({query_confidence}% match) that {user_query.lower()}." if query_confidence >= 60 else f"I noticed some changes that seem to match what you asked me to look for ({query_confidence}% match)."}

{'This was verified through advanced AI reasoning to ensure accuracy.' if is_claude_decision and claude_reasoning else ''}

This alert was triggered {time_str} after I started monitoring. I've attached visual evidence for you to review – you can see the before and after states clearly.

Would you like me to continue monitoring, or should I take any other action?"""
                                    else:
                                        # Object detection - Professional voice assistant style
                                        time_now = datetime.utcnow().strftime('%I:%M %p')
                                        confidence_level = 'quite sure' if query_confidence >= 80 else 'fairly confident' if query_confidence >= 60 else 'reasonably certain'
                                        
                                        alert_summary = f"""Good news – I found what you were looking for!

You asked me to watch for {user_query.lower()}, and I've just spotted it on Camera {camera_id} at {time_now}.

Here's what I see: {analysis.get('query_details', analysis.get('scene_description', 'Your requested item is in view')).lower().capitalize()}.

I'm {confidence_level} this is a match ({query_confidence}% confidence). {f"I also noticed {', '.join(detected_objects[:3])} in the frame." if detected_objects and len(detected_objects) > 0 else ""}

I've captured an image for you to verify. Take a look and let me know if you need me to keep watching or if there's anything else you'd like me to do."""
                                else:
                                    # Dangerous situation - Professional but urgent voice
                                    time_now = datetime.utcnow().strftime('%I:%M %p')
                                    alert_summary = f"""URGENT: I need your immediate attention.

I've detected something concerning on Camera {camera_id} at {time_now}.

What I'm seeing: {analysis.get('scene_description', 'A potentially hazardous situation').lower().capitalize()}

**Activity:** {analysis.get('activity', 'Unknown activity')}

**Objects Detected:** {', '.join(detected_objects) if detected_objects else 'None'}

**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
**Camera:** {camera_id}

**⚠️ URGENT:** Potential safety concern - review immediately
**Evidence:** Image attached below"""

                                # Send immediate alert
                                immediate_alert_data = {
                                    "id": f"immediate_{camera_id}_{int(datetime.utcnow().timestamp())}",
                                    "severity": severity,
                                    "title": title,
                                    "message": alert_summary,
                                    "camera_id": camera_id,
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "significance": query_confidence if user_query else significance,
                                    "frame_url": frame_url,
                                    "frame_path": str(frame_path),
                                    "frame_base64": frame_base64,
                                    "detections": detections_list,
                                    "detected_objects": detected_objects,
                                    "alert_type": "immediate",
                                    "user_query": user_query,
                                    "query_match": query_match,
                                    "query_confidence": query_confidence,
                                    "is_read": False
                                }

                                await manager.send_alert(immediate_alert_data)
                                logger.info(f"🚨 IMMEDIATE ALERT SENT: {title} - Confidence: {query_confidence if user_query else significance}%")
                                
                                # Send email notification for critical alerts (using same data as frontend)
                                try:
                                    await email_service.send_critical_alert(alert_data=immediate_alert_data)
                                except Exception as email_error:
                                    logger.error(f"Failed to send alert email: {email_error}")

                            # Don't collect for 2-minute summary if already sent immediate alert
                            # This prevents duplicate notifications
                            # Only collect events that didn't trigger immediate alerts
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
                                logger.info(f"✓ Event collected for 2-min summary (significance={significance}%)")

                            # Try to store event in database (optional - continue if fails)
                            try:
                                db = SessionLocal()
                                
                                # Create event
                                event = Event(
                                    camera_id=camera_id,
                                    event_type="scene_analysis",
                                    description=analysis.get('activity', ''),
                                    scene_description=analysis.get('scene_description', ''),
                                    significance_score=vision_agent.calculate_significance_score(analysis),
                                    severity=vision_agent.determine_alert_severity(analysis),
                                    context_summary=context_summary,
                                    event_metadata=analysis
                                )

                                db.add(event)
                                db.flush()  # Get event ID

                                # Store in ChromaDB
                                embedding_id = await context_agent.store_scene_description(
                                    event.id,
                                    camera_id,
                                    event.timestamp,
                                    event.scene_description,
                                    {"significance": event.significance_score}
                                )

                                event.embedding_id = embedding_id

                                # Create detections
                                for det in vision_agent.extract_detections_for_storage(analysis):
                                    detection = Detection(
                                        event_id=event.id,
                                        camera_id=camera_id,
                                        **det
                                    )
                                    db.add(detection)

                                # Create alert if significant (this is for DB storage, not WS notification)
                                if event.significance_score >= settings.WARNING_THRESHOLD:
                                    alert = Alert(
                                        event_id=event.id,
                                        severity=event.severity,
                                        title=f"{event.severity.value} Alert - Camera {camera_id}",
                                        message=event.scene_description
                                    )
                                    db.add(alert)
                                    db.flush()

                                db.commit()
                                db.close()
                            except Exception as db_error:
                                logger.warning(f"Failed to save event to database (continuing without DB): {db_error}")
                                try:
                                    if 'db' in locals():
                                        db.rollback()
                                        db.close()
                                except:
                                    pass
                        except Exception as frame_error:
                            logger.error(f"Error processing frame from camera {camera_id}: {frame_error}")
                            continue

                    # Check active tasks and analyze in context (for successfully processed frames)
                    if frame is not None:
                        try:
                            active_tasks = command_agent.get_active_tasks()
                            for task_id, task_data in active_tasks.items():
                                task_command = task_data.get('command', {})
                                task_params = task_command.get('parameters', {})
                                target_cameras = task_params.get('camera_ids', ['all'])

                                # Check if this camera is relevant to the task
                                if target_cameras == ['all'] or 'all' in target_cameras or camera_id in target_cameras:
                                    # Get analysis if we have it
                                    try:
                                        analysis = await vision_agent.analyze_frame(frame, camera_id)
                                        # Analyze in context of task
                                        task_result = await command_agent.analyze_with_context(
                                            task_id,
                                            {"camera_id": camera_id, "timestamp": datetime.utcnow().isoformat()},
                                analysis
                            )

                                        # Send task update if alert needed
                                        if task_result.get('alert_needed'):
                                            # Save frame for task alert
                                            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                                            frame_filename = f"camera{camera_id}_{timestamp_str}_task{task_id[-8:]}.jpg"
                                            frame_path = event_frames_dir / frame_filename
                                            cv2.imwrite(str(frame_path), frame)
                                            logger.info(f"[FRAME SAVED] Task alert triggered for task {task_id}, frame saved to: {frame_filename}")

                                            await manager.send_system_message("task_alert", {
                                                "task_id": task_id,
                                "camera_id": camera_id,
                                                "task_type": task_command.get('task_type'),
                                                "target": task_command.get('target'),
                                                "findings": task_result.get('findings'),
                                                "alert_message": task_result.get('alert_message'),
                                                "timestamp": datetime.utcnow().isoformat(),
                                                "frame_path": str(frame_path)  # Include frame path
                                            })
                                    except Exception as task_error:
                                        logger.debug(f"Task analysis error: {task_error}")
                        except Exception as task_check_error:
                            logger.debug(f"Error checking tasks: {task_check_error}")

            # Check if 2 minutes have elapsed - send summary alert
            logger.debug(f"[TIMER] Elapsed: {elapsed_seconds}s / {ANALYSIS_INTERVAL_SECONDS}s | Events: {len(critical_events)}")
            if elapsed_seconds >= ANALYSIS_INTERVAL_SECONDS:
                logger.info(f"⏰ 2-MINUTE INTERVAL COMPLETE - Analyzing {len(critical_events)} events")
                
                if critical_events:
                    # Find most significant event
                    most_significant = max(critical_events, key=lambda x: x['significance'])
                    
                    # Collect all unique objects from the minute
                    all_objects = set()
                    activities = []
                    for event in critical_events:
                        all_objects.update(event['detected_objects'])
                        activity = event['analysis'].get('activity', '')
                        if activity and activity not in activities:
                            activities.append(activity)
                    
                    # Create comprehensive 2-minute summary
                    alert_summary = f"""**2-Minute Activity Summary** (Peak Confidence: {most_significant['significance']}%)

**Period:** {minute_start_time.strftime('%H:%M:%S')} - {current_time.strftime('%H:%M:%S')}

**Most Significant Scene:** {most_significant['analysis'].get('scene_description', 'No description')}

**Activities Detected:** {' → '.join(activities[:3]) if activities else 'No significant activity changes'}

**All Objects Seen:** {', '.join(sorted(all_objects)) if all_objects else 'None'}

**Events Recorded:** {len(critical_events)} detected in last 2 minutes
**Camera:** {camera_id if 'camera_id' in locals() else 0}

**Analysis:** This summary represents activities from the last 120 seconds."""

                    # Determine severity
                    if most_significant['significance'] >= 80:
                        severity = "CRITICAL"
                        title = f"🚨 Critical Activity Summary (2-min) - Camera {camera_id if 'camera_id' in locals() else 0}"
                    else:
                        severity = "WARNING"
                        title = f"⚠️ Activity Summary (2-min) - Camera {camera_id if 'camera_id' in locals() else 0}"

                    # Create ONE consolidated alert for the entire minute
                    alert_data = {
                        "id": f"summary_{int(current_time.timestamp())}",
                        "severity": severity,
                        "title": title,
                        "message": alert_summary,
                        "camera_id": camera_id if 'camera_id' in locals() else 0,
                        "timestamp": current_time.isoformat(),
                        "significance": most_significant['significance'],
                        "frame_url": most_significant['frame_url'],
                        "frame_path": str(most_significant['frame_path']),
                        "frame_base64": most_significant['frame_base64'],
                        "detections": most_significant['detections_list'],
                        "detected_objects": list(all_objects),
                        "event_count": len(critical_events),
                        "is_read": False
                    }

                    # Send single alert for entire 2-minute period
                    await manager.send_alert(alert_data)
                    logger.info(f"📩 2-MINUTE SUMMARY SENT: {severity} - {len(critical_events)} events, max={most_significant['significance']}%")
                    
                    # Send email notification for 2-minute summary (using same data as frontend)
                    try:
                        await email_service.send_summary_email(alert_data=alert_data)
                    except Exception as email_error:
                        logger.error(f"Failed to send summary email: {email_error}")
                else:
                    logger.info(f"✓ 2-minute period complete - No events to summarize")
                
                # Reset for next 2-minute period
                minute_start_time = current_time
                critical_events = []
                logger.info(f"🔄 Starting new 2-minute analysis period")

            # Wait before next iteration (based on FPS)
            await asyncio.sleep(1.0 / settings.CAMERA_FPS)

        except Exception as e:
            logger.error(f"Error in surveillance worker: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
