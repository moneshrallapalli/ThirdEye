"""
Vision Agent - Handles Gemini Live API integration for real-time video analysis
"""
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
import asyncio
import base64
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
import cv2
import numpy as np
from PIL import Image
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database.models import AlertSeverity


class VisionAgent:
    """
    Vision Agent for real-time video analysis using Gemini Live API
    """

    def __init__(self, api_key: str = None):
        """
        Initialize Vision Agent

        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)

        # Initialize Gemini model
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',  # Use flash for real-time processing
            generation_config=GenerationConfig(
                temperature=0.4,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        # System prompt for surveillance analysis
        self.system_prompt = """You are an intelligent surveillance analysis system. Analyze frames and provide detailed object detection.

CRITICAL: Always respond with VALID JSON ONLY. No markdown, no code blocks, just pure JSON.

Detect ALL objects including:
- People (number of people, actions, clothing)
- Objects (phones, laptops, bags, tools, scissors, nail cutters, keys, etc.)
- Furniture and environment
- Actions and activities

Response format (PURE JSON):
{
  "timestamp": "2024-01-01T12:00:00",
  "scene_description": "Brief description of the scene",
  "detections": [
    {
      "object_type": "object",
      "label": "nail cutter",
      "confidence": 0.95,
      "location": "center of frame, on desk",
      "attributes": ["metal", "small"]
    }
  ],
  "activity": "what is happening",
  "significance": 60,
  "changes": "what changed",
  "alerts": []
}

Be specific about objects. If you see a nail cutter, phone, or any tool - LIST IT in detections."""

    async def analyze_frame(
        self,
        frame: np.ndarray,
        camera_id: int,
        previous_context: Optional[str] = None,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single video frame using Gemini

        Args:
            frame: Video frame (numpy array)
            camera_id: Camera ID
            previous_context: Context from previous analysis
            user_query: Optional user query to focus detection on (e.g., "look for scissors")

        Returns:
            Analysis results with query_match_confidence if user_query provided
        """
        try:
            # Convert frame to PIL Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Build prompt with context and user query
            prompt = self.system_prompt
            if previous_context:
                prompt += f"\n\nPrevious context: {previous_context}"
            
            # Add user query for focused detection (with baseline context for state changes)
            if user_query:
                if previous_context and "BASELINE:" in previous_context:
                    # User is tracking state changes - compare to baseline
                    prompt += f"""

🎯 CRITICAL STATE CHANGE DETECTION (HIGH PRIORITY):
The user asked: "{user_query}"

{previous_context}

IMPORTANT - Compare current frame to BASELINE state:
1. What has CHANGED from the baseline?
2. Did the expected activity/state change occur?
3. Is the condition the user is waiting for now TRUE?

KEY DETECTION RULES:
- If baseline had "person sitting" and now there's NO person → Person LEFT (HIGH confidence match!)
- If baseline had "person present" and now frame is EMPTY → Person DEPARTED (HIGH confidence match!)
- If baseline had object and now it's GONE → Object REMOVED (HIGH confidence match!)
- Empty room AFTER person was there = SUCCESSFUL DEPARTURE (90%+ confidence!)

CRITICAL: An EMPTY scene when person was there before IS A MATCH for "person leaves"!

RESPOND WITH THESE EXTRA FIELDS:
- "state_analysis": "Current state of the scene"
- "baseline_match": true/false (does it still match the baseline, or has it changed?)
- "query_match": true/false (did the user's expected change/activity happen?)
- "query_confidence": 0-100 (MUST BE HIGH 80-95% if person left when they were sitting before!)
- "query_details": "Detailed explanation of what changed and if it matches the query"
- "changes_detected": ["list of changes from baseline"]
- "person_present": true/false (is there a person in current frame?)
- "person_was_present_in_baseline": true/false (was person in baseline?)

USER'S EXPECTED CHANGE: {user_query}

CRITICAL LOGIC:
If baseline had person AND current frame has NO person → query_match=TRUE, query_confidence=90%+
If person was sitting and now chair is empty → query_match=TRUE, query_confidence=90%+
The ABSENCE of person (when they were present) IS THE KEY CHANGE!
"""
                else:
                    # First frame or object detection - establish baseline or look for object
                    prompt += f"""

🎯 CRITICAL USER QUERY (HIGH PRIORITY):
The user is looking for: "{user_query}"

ANALYZE THE QUERY TYPE:
- Is this about DETECTING AN OBJECT? (e.g., "find scissors")
- Is this about DETECTING ACTIVITY/CHANGE? (e.g., "when person gets up")

RESPOND WITH THESE EXTRA FIELDS:
- "query_type": "object_detection" OR "activity_detection" OR "state_change_detection"
- "current_state": "Describe the current state/scene in detail"
- "baseline_established": true/false (is this the baseline state to track from?)
- "query_match": true/false (is the query condition met in THIS frame?)
- "query_confidence": 0-100 (confidence the query is satisfied)
- "query_details": "Detailed explanation"

For ACTIVITY/STATE CHANGE queries (like "when person gets up and leaves"):
- Describe the CURRENT STATE thoroughly including ALL people present
- Count people: "1 person sitting", "2 people standing", "0 people (empty)"
- This may be the BASELINE to compare future frames against
- Set baseline_established=true if this looks like the starting condition
- CRITICAL: If query mentions "leaves" or "moves out", note the PRESENCE of people/objects

For OBJECT DETECTION queries:
- Just look for the specific object
- Set query_match=true if found

CRITICAL DETECTION LOGIC FOR "PERSON LEAVES" QUERIES:
- Baseline: "Person sitting in chair" (person_count: 1)
- Current: "Empty chair, no person" (person_count: 0)
- Result: Person LEFT → query_match=TRUE, confidence=90%+
"""

            # Generate analysis
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, pil_image]
            )

            # Parse response
            analysis = self._parse_gemini_response(response.text)
            analysis['camera_id'] = camera_id
            analysis['timestamp'] = datetime.utcnow().isoformat()

            return analysis

        except Exception as e:
            import traceback
            from loguru import logger
            logger.error(f"Vision Agent error for camera {camera_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "scene_description": "Analysis failed",
                "significance": 0,
                "detections": [],
                "alerts": []
            }

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini's response into structured format

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed analysis dictionary
        """
        try:
            # Try to extract JSON from response
            # Gemini might wrap JSON in markdown code blocks
            text = response_text.strip()

            # Remove markdown code block if present
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]

            text = text.strip()

            # Try to find JSON object if it's embedded in other text
            if not text.startswith('{'):
                # Find first { and last }
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    text = text[start:end+1]

            # Parse JSON
            analysis = json.loads(text)

            # Ensure required fields with defaults
            if 'scene_description' not in analysis or not analysis['scene_description']:
                analysis['scene_description'] = text[:200] if len(text) < 500 else "Scene analysis"
            if 'significance' not in analysis:
                analysis['significance'] = 50
            if 'detections' not in analysis or not isinstance(analysis['detections'], list):
                analysis['detections'] = []
            if 'alerts' not in analysis or not isinstance(analysis['alerts'], list):
                analysis['alerts'] = []
            if 'activity' not in analysis:
                analysis['activity'] = analysis.get('scene_description', '')[:100]

            return analysis

        except json.JSONDecodeError:
            # If JSON parsing fails, create structured response from text
            return {
                "scene_description": response_text[:500],
                "significance": 50,
                "detections": [],
                "activity": response_text[:200],
                "changes": "",
                "alerts": []
            }

    async def analyze_stream(
        self,
        camera_id: int,
        video_source: Any,
        fps: int = 2
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Continuously analyze video stream

        Args:
            camera_id: Camera ID
            video_source: Video source (file path, URL, or camera index)
            fps: Frames per second to analyze

        Yields:
            Analysis results for each frame
        """
        cap = cv2.VideoCapture(video_source)
        frame_interval = 1.0 / fps
        previous_context = None

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Analyze frame
                analysis = await self.analyze_frame(frame, camera_id, previous_context)

                # Update context for next frame
                previous_context = analysis.get('scene_description', '')[:200]

                yield analysis

                # Wait for next frame
                await asyncio.sleep(frame_interval)

        finally:
            cap.release()

    def calculate_significance_score(self, analysis: Dict[str, Any]) -> int:
        """
        Calculate significance score for an event

        Args:
            analysis: Analysis results

        Returns:
            Significance score (0-100)
        """
        base_score = analysis.get('significance', 50)

        # Boost score based on detections
        detections = analysis.get('detections', [])
        detection_boost = min(len(detections) * 5, 20)

        # Boost score based on alerts
        alerts = analysis.get('alerts', [])
        alert_boost = 0
        for alert in alerts:
            if alert.get('severity') == 'CRITICAL':
                alert_boost += 30
            elif alert.get('severity') == 'WARNING':
                alert_boost += 15
            elif alert.get('severity') == 'INFO':
                alert_boost += 5

        total_score = min(base_score + detection_boost + alert_boost, 100)
        return total_score

    def determine_alert_severity(self, analysis: Dict[str, Any]) -> AlertSeverity:
        """
        Determine alert severity based on analysis

        Args:
            analysis: Analysis results

        Returns:
            Alert severity
        """
        significance = self.calculate_significance_score(analysis)
        alerts = analysis.get('alerts', [])

        # Check for critical alerts
        for alert in alerts:
            if alert.get('severity') == 'CRITICAL':
                return AlertSeverity.CRITICAL

        # Check significance thresholds
        if significance >= settings.CRITICAL_THRESHOLD:
            return AlertSeverity.CRITICAL
        elif significance >= settings.WARNING_THRESHOLD:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    async def batch_analyze_frames(
        self,
        frames: List[np.ndarray],
        camera_id: int
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple frames in batch

        Args:
            frames: List of video frames
            camera_id: Camera ID

        Returns:
            List of analysis results
        """
        tasks = [self.analyze_frame(frame, camera_id) for frame in frames]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            else:
                valid_results.append({
                    "error": str(result),
                    "camera_id": camera_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "scene_description": "Analysis failed",
                    "significance": 0,
                    "detections": [],
                    "alerts": []
                })

        return valid_results

    def extract_detections_for_storage(
        self,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract detections in format suitable for database storage

        Args:
            analysis: Analysis results

        Returns:
            List of detection dictionaries
        """
        detections = []
        for det in analysis.get('detections', []):
            detections.append({
                "object_type": det.get('object_type', 'unknown'),
                "object_label": det.get('label', ''),
                "confidence_score": det.get('confidence', 0.0),
                "bounding_box": det.get('bounding_box', {}),
                "attributes": det.get('attributes', []),
                "location": det.get('location', '')
            })

        return detections

    async def query_scene_in_video(
        self,
        video_file_path: str,
        scene_query: str,
        camera_id: Optional[int] = None,
        fps: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query for specific scenes in a video and return timestamps when they occur

        This method uploads a video file to Gemini API and asks about specific scenes,
        getting timestamps for when those scenes occur.

        Args:
            video_file_path: Path to the video file
            scene_query: Description of the scene to find (e.g., "when does a person enter the room?")
            camera_id: Optional camera ID for tracking
            fps: Optional frame rate for video processing (default: 1 FPS)

        Returns:
            Dictionary containing:
            - scene_query: The original query
            - found: Boolean indicating if scene was found
            - timestamps: List of timestamps (MM:SS format) where scene occurs
            - descriptions: Detailed descriptions for each timestamp
            - full_response: Complete response from Gemini

        Example:
            >>> agent = VisionAgent()
            >>> result = await agent.query_scene_in_video(
            ...     "surveillance_footage.mp4",
            ...     "when does a person wearing red clothing appear?"
            ... )
            >>> print(result['timestamps'])  # ['00:15', '01:23', '02:45']
        """
        try:
            from loguru import logger
            logger.info(f"Uploading video file: {video_file_path}")

            # Upload video file to Gemini
            video_file = genai.upload_file(path=video_file_path)

            logger.info(f"Processing video file: {video_file.name}")

            # Wait for video processing
            while video_file.state.name == "PROCESSING":
                await asyncio.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.state}")

            logger.info("Video processed successfully")

            # Build prompt specifically for timestamp queries
            timestamp_prompt = f"""Analyze this surveillance video and identify when the following scene occurs:

SCENE TO FIND: {scene_query}

Provide your response in the following JSON format:
{{
  "found": true/false,
  "timestamps": ["MM:SS", "MM:SS", ...],  // List of timestamps where the scene occurs
  "descriptions": [
    {{
      "timestamp": "MM:SS",
      "description": "Detailed description of what is happening at this moment",
      "confidence": 0.95,  // Confidence that this matches the query (0-1)
      "key_details": ["detail1", "detail2"]  // Key visual details
    }}
  ],
  "summary": "Overall summary of findings"
}}

IMPORTANT:
- Only include timestamps where the described scene ACTUALLY occurs
- Use MM:SS format for all timestamps
- Be precise with timing
- Include confidence scores
- If the scene never occurs, set "found" to false and return empty lists"""

            # Create content parts with video metadata if FPS is specified
            if fps:
                from google.generativeai import types
                content = [
                    types.Part.from_dict({
                        'file_data': {
                            'file_uri': video_file.uri,
                            'mime_type': video_file.mime_type
                        },
                        'video_metadata': types.VideoMetadata(fps=fps)
                    }),
                    timestamp_prompt
                ]
            else:
                content = [video_file, timestamp_prompt]

            logger.info("Generating timestamp analysis...")

            # Generate analysis with timestamps
            response = await asyncio.to_thread(
                self.model.generate_content,
                content
            )

            # Parse response
            analysis = self._parse_gemini_response(response.text)

            # Add metadata
            result = {
                "scene_query": scene_query,
                "camera_id": camera_id,
                "video_file": video_file_path,
                "found": analysis.get('found', False),
                "timestamps": analysis.get('timestamps', []),
                "descriptions": analysis.get('descriptions', []),
                "summary": analysis.get('summary', ''),
                "full_response": response.text,
                "processed_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Scene query complete. Found: {result['found']}, Timestamps: {result['timestamps']}")

            # Cleanup: delete uploaded file
            genai.delete_file(video_file.name)
            logger.info("Cleaned up uploaded video file")

            return result

        except Exception as e:
            import traceback
            from loguru import logger
            logger.error(f"Video scene query error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "scene_query": scene_query,
                "camera_id": camera_id,
                "found": False,
                "timestamps": [],
                "descriptions": [],
                "summary": "Analysis failed"
            }

    async def analyze_video_with_timestamps(
        self,
        video_file_path: str,
        camera_id: Optional[int] = None,
        fps: Optional[int] = 1,
        include_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a complete video file and get timestamped events

        This provides a timeline of significant events in the video with timestamps.

        Args:
            video_file_path: Path to the video file
            camera_id: Optional camera ID for tracking
            fps: Frame rate for processing (default: 1 FPS)
            include_timestamps: Whether to include timestamps in analysis

        Returns:
            Dictionary containing timeline of events with timestamps
        """
        try:
            from loguru import logger
            logger.info(f"Uploading video for timeline analysis: {video_file_path}")

            # Upload video file
            video_file = genai.upload_file(path=video_file_path)

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                await asyncio.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed")

            # Build prompt for timeline analysis
            timeline_prompt = """Analyze this surveillance video and create a timeline of significant events.

Provide your response in JSON format:
{
  "events": [
    {
      "timestamp": "MM:SS",
      "event_type": "person_detected|vehicle_detected|object_moved|suspicious_activity|other",
      "description": "What happened",
      "significance": 75,
      "detections": ["person", "vehicle", etc.]
    }
  ],
  "summary": "Overall summary of the video",
  "total_duration": "MM:SS",
  "key_moments": ["MM:SS", "MM:SS"]  // Most important timestamps
}

Include timestamps for all significant events. Focus on security-relevant activities."""

            # Generate analysis
            if fps and fps != 1:
                from google.generativeai import types
                content = [
                    types.Part.from_dict({
                        'file_data': {
                            'file_uri': video_file.uri,
                            'mime_type': video_file.mime_type
                        },
                        'video_metadata': types.VideoMetadata(fps=fps)
                    }),
                    timeline_prompt
                ]
            else:
                content = [video_file, timeline_prompt]

            response = await asyncio.to_thread(
                self.model.generate_content,
                content
            )

            # Parse response
            analysis = self._parse_gemini_response(response.text)

            result = {
                "camera_id": camera_id,
                "video_file": video_file_path,
                "events": analysis.get('events', []),
                "summary": analysis.get('summary', ''),
                "total_duration": analysis.get('total_duration', ''),
                "key_moments": analysis.get('key_moments', []),
                "full_response": response.text,
                "processed_at": datetime.utcnow().isoformat()
            }

            # Cleanup
            genai.delete_file(video_file.name)

            return result

        except Exception as e:
            import traceback
            from loguru import logger
            logger.error(f"Video timeline analysis error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "camera_id": camera_id,
                "events": [],
                "summary": "Analysis failed"
            }
