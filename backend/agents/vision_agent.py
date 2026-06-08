"""
Vision Agent - Uses Claude for real-time video frame analysis
"""
import anthropic
import asyncio
import base64
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
import cv2
import numpy as np
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database.models import AlertSeverity


# Keywords that flip the vision + reasoning agents into "aggressive surveillance
# mode". Home-security intents — break-in, theft, intruder, etc. — should treat
# any unknown person in frame as a potential match, not dismiss them as
# "looks like the owner". Keep this list narrow: expand only when a specific
# phrasing demonstrably gets dismissed by the model.
_AGGRESSIVE_KEYWORDS = (
    "break in", "break-in", "breaks in", "breaks into", "breaking in",
    "intruder", "intrusion", "trespass", "burglar", "burglary", "robbery",
    "theft", "stealing", "stolen",
    "unauthorized", "unknown person", "stranger",
    "someone enters", "someone entering", "someone breaks",
    "suspicious activity", "suspicious person",
)


def _is_aggressive_surveillance(user_query: Optional[str]) -> bool:
    """Return True when the query describes an intrusion/theft-style intent.

    Matched case-insensitively on substring so compound OR-joined targets
    from the command agent still trip (e.g. "unauthorized person entering
    the house OR an object being removed ...").
    """
    if not user_query:
        return False
    q = user_query.lower()
    return any(k in q for k in _AGGRESSIVE_KEYWORDS)


class VisionAgent:
    """
    Vision Agent for real-time video analysis using Claude vision
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.CLAUDE_API_KEY
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

        self.system_prompt = """You are an intelligent surveillance analysis system. Analyze frames and provide detailed object detection.

CRITICAL: Always respond with VALID JSON ONLY. No markdown, no code blocks, just pure JSON.

Detect ALL objects including:
- People (number of people, actions, clothing)
- Objects (phones, laptops, bags, tools, scissors, nail cutters, keys, etc.)
- Furniture and environment
- Actions and activities

Response format (PURE JSON):
{
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
        user_query: Optional[str] = None,
        monitoring_mode: bool = False
    ) -> Dict[str, Any]:
        try:
            # Encode frame as JPEG base64 for Claude vision
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            image_base64 = base64.b64encode(buffer).decode('utf-8')

            # Build prompt
            prompt = self.system_prompt
            if previous_context:
                prompt += f"\n\nPrevious context: {previous_context}"

            if user_query:
                if monitoring_mode:
                    # ── Continuous monitoring tasks (from DB) ──
                    # Directly check each condition against the CURRENT frame.
                    prompt += f"""

ACTIVE MONITORING TASKS (HIGH PRIORITY):
You are a real-time surveillance monitor. Check the current frame against
each monitoring rule below and report which ones are triggered RIGHT NOW.

Rules to check:
{user_query}

For EVERY rule, decide: is this condition TRUE in the current frame?

YOU MUST INCLUDE THESE FIELDS IN YOUR JSON RESPONSE:
- "query_match": true if ANY rule is triggered, false if none are
- "query_confidence": 0-100 (how confident you are that a rule is triggered)
- "query_details": "Which rule(s) matched and why, or why none matched"
- "matched_rules": ["list of rules that are currently triggered"]

IMPORTANT:
- Check each rule independently against what you SEE in this frame.
- If a rule says "alert if person enters" and there IS a person → query_match=true
- If a rule says "watch for fire" and you see flames/smoke → query_match=true
- Be decisive. If the condition is clearly visible, set query_confidence >= 70.
- Only set query_match=false if NONE of the rules apply to the current frame.
"""
                    if _is_aggressive_surveillance(user_query):
                        prompt += """

AGGRESSIVE HOME-SECURITY MODE (OVERRIDES ABOVE):
This rule is an intrusion/theft watch. The camera owner is AWAY or wants to be
notified about ANY human presence. Your job is to ALERT, not to reason about
who belongs in the scene. Follow these rules strictly:

1. If ANY person, silhouette, or body part is visible in the frame → set
   query_match=true with query_confidence between 75 and 95.
2. DO NOT reason "the person looks like a resident", "appears authorized",
   "is in their own home", "seems legitimate", "is adjusting their own TV",
   "is doing normal activity", or any similar softening. You CANNOT verify
   who is authorized. The default is ALERT.
3. DO NOT require forced entry, weapons, masks, or suspicious behavior. Mere
   presence of a human when the owner is monitoring is enough.
4. Also match on: objects being carried toward/out of the frame, drawers or
   cabinets being opened, hands reaching for electronics/bags/valuables,
   someone climbing through a window, flashlight beams in the dark.
5. Only set query_match=false if the frame is EMPTY of humans AND shows no
   object being removed. Empty room with no activity = query_match=false.
6. If the frame is too dark / too blurry to tell, set query_match=true with
   query_confidence=60 and say so in query_details — the owner would rather
   see a false alarm than miss an intruder.

Remember: under aggressive mode, the cost of a missed intruder is far higher
than the cost of a false alarm. When in doubt, ALERT.
"""
                elif previous_context and "BASELINE:" in previous_context:
                    prompt += f"""

CRITICAL STATE CHANGE DETECTION (HIGH PRIORITY):
The user asked: "{user_query}"

{previous_context}

IMPORTANT - Compare current frame to BASELINE state:
1. What has CHANGED from the baseline?
2. Did the expected activity/state change occur?
3. Is the condition the user is waiting for now TRUE?

KEY DETECTION RULES:
- If baseline had "person sitting" and now there's NO person -> Person LEFT (HIGH confidence match!)
- If baseline had "person present" and now frame is EMPTY -> Person DEPARTED (HIGH confidence match!)
- If baseline had object and now it's GONE -> Object REMOVED (HIGH confidence match!)
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
If baseline had person AND current frame has NO person -> query_match=TRUE, query_confidence=90%+
If person was sitting and now chair is empty -> query_match=TRUE, query_confidence=90%+
The ABSENCE of person (when they were present) IS THE KEY CHANGE!
"""
                else:
                    prompt += f"""

CRITICAL USER QUERY (HIGH PRIORITY):
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
"""

            # Call Claude vision API
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            # Parse response
            response_text = response.content[0].text
            analysis = self._parse_response(response_text)
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

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        try:
            text = response_text.strip()

            # Remove markdown code block if present
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]

            text = text.strip()

            # Find JSON object if embedded in other text
            if not text.startswith('{'):
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    text = text[start:end+1]

            analysis = json.loads(text)

            # Ensure required fields
            if 'scene_description' not in analysis or not analysis['scene_description']:
                analysis['scene_description'] = text[:200] if len(text) < 500 else "Scene analysis"
            if 'significance' not in analysis:
                analysis['significance'] = 50
            if 'detections' not in analysis or not isinstance(analysis['detections'], list):
                analysis['detections'] = []
            else:
                # Claude occasionally returns strings instead of dicts; coerce.
                analysis['detections'] = [
                    d if isinstance(d, dict)
                    else {"object_type": "object", "label": str(d), "confidence": 0.0}
                    for d in analysis['detections']
                ]
            if 'alerts' not in analysis or not isinstance(analysis['alerts'], list):
                analysis['alerts'] = []
            else:
                analysis['alerts'] = [
                    a if isinstance(a, dict) else {"severity": "INFO", "message": str(a)}
                    for a in analysis['alerts']
                ]
            if 'activity' not in analysis:
                analysis['activity'] = analysis.get('scene_description', '')[:100]

            return analysis

        except json.JSONDecodeError:
            return {
                "scene_description": response_text[:500],
                "significance": 50,
                "detections": [],
                "activity": response_text[:200],
                "changes": "",
                "alerts": []
            }

    def calculate_significance_score(self, analysis: Dict[str, Any]) -> int:
        base_score = analysis.get('significance', 50)

        detections = analysis.get('detections', [])
        detection_boost = min(len(detections) * 5, 20)

        alerts = analysis.get('alerts', [])
        alert_boost = 0
        for alert in alerts:
            if alert.get('severity') == 'CRITICAL':
                alert_boost += 30
            elif alert.get('severity') == 'WARNING':
                alert_boost += 15
            elif alert.get('severity') == 'INFO':
                alert_boost += 5

        return min(base_score + detection_boost + alert_boost, 100)

    def determine_alert_severity(self, analysis: Dict[str, Any]) -> AlertSeverity:
        significance = self.calculate_significance_score(analysis)
        alerts = analysis.get('alerts', [])

        for alert in alerts:
            if alert.get('severity') == 'CRITICAL':
                return AlertSeverity.CRITICAL

        if significance >= settings.CRITICAL_THRESHOLD:
            return AlertSeverity.CRITICAL
        elif significance >= settings.WARNING_THRESHOLD:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    def extract_detections_for_storage(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        detections = []
        for det in analysis.get('detections', []):
            detections.append({
                "object_type": det.get('object_type', 'unknown'),
                "object_label": det.get('label', ''),
                "confidence_score": det.get('confidence', 0.0),
                "bounding_box": det.get('bounding_box', {}),
                "attributes": det.get('attributes', []),
            })
        return detections
