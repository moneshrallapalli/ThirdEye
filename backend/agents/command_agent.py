"""
Command Agent - Processes user commands using Gemini for real-time surveillance control
"""
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class CommandAgent:
    """
    Processes natural language user commands for surveillance control
    """

    def __init__(self, api_key: str = None):
        """
        Initialize Command Agent

        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)

        # Initialize Gemini model for command processing
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config=GenerationConfig(
                temperature=0.3,  # Lower temperature for more consistent command parsing
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        # System prompt for command understanding with improved interpretation
        self.system_prompt = """You are an intelligent surveillance system command processor with advanced natural language understanding.
Your role is to ACCURATELY understand user commands and translate them into precise, actionable surveillance tasks.

CRITICAL: Pay close attention to:
- Specific objects mentioned (scissors, nail cutter, phone, laptop, etc.)
- Actions and activities (entering, leaving, picking up, holding, using)
- Conditions (if/when/whenever/alert me if)
- Context and intent

You can perform the following tasks:
1. OBJECT DETECTION - Detect ANY specific objects (people, vehicles, animals, tools, items, devices)
2. ACTIVITY DETECTION - Detect when specific activities or actions occur (person gets up, leaves, enters, picks up object)
3. STATE CHANGE DETECTION - Monitor for changes in state (person sitting → standing, object present → absent)
4. SCENE ANALYSIS - Analyze and describe current scenes
5. ALERT GENERATION - Create alerts based on specific conditions
6. TRACKING - Track specific objects or people across cameras
7. ANOMALY DETECTION - Identify unusual activities or patterns

CRITICAL OUTPUT FORMAT - Respond ONLY with valid JSON (no markdown, no code blocks):
{
  "task_type": "object_detection|activity_detection|state_change_detection|surveillance|scene_analysis|alert|tracking|anomaly_detection",
  "target": "EXACT object/activity/change to look for",
  "query_type": "object|activity|state_change",
  "requires_baseline": true/false,
  "baseline_description": "What is the starting state to track from? (for activity/state change)",
  "expected_change": "What change/activity should trigger the alert?",
  "parameters": {
    "camera_ids": ["all"],
    "duration": "continuous",
    "alert_threshold": "medium",
    "specific_conditions": ["list of SPECIFIC conditions"],
    "objects_to_detect": ["list ALL specific objects mentioned"],
    "activities_to_detect": ["list of activities like 'person gets up', 'leaves frame', 'picks up object']",
    "track_state_changes": true/false
  },
  "confirmation": "Natural language confirmation",
  "understood_intent": "Detailed explanation of what you understood"
}

EXAMPLES showing proper understanding:

User: "alert me if you see scissors"
Response: {
  "task_type": "object_detection",
  "target": "scissors",
  "query_type": "object",
  "requires_baseline": false,
  "parameters": {
    "camera_ids": ["all"],
    "duration": "continuous",
    "alert_threshold": "medium",
    "specific_conditions": ["detect scissors in frame", "alert when scissors appear"],
    "objects_to_detect": ["scissors"],
    "track_state_changes": false
  },
  "confirmation": "I will continuously monitor all cameras and alert you immediately when scissors are detected",
  "understood_intent": "User wants to be alerted when scissors appear in any camera view"
}

User: "notify me when the person sitting in chair gets up and moves out of frame"
Response: {
  "task_type": "activity_detection",
  "target": "person gets up and leaves",
  "query_type": "activity",
  "requires_baseline": true,
  "baseline_description": "Person sitting in chair (initial state)",
  "expected_change": "Person gets up from chair AND moves out of frame",
  "parameters": {
    "camera_ids": ["all"],
    "duration": "continuous",
    "alert_threshold": "medium",
    "specific_conditions": ["person stands up from chair", "person leaves frame"],
    "activities_to_detect": ["person gets up", "person moves", "person exits frame"],
    "track_state_changes": true
  },
  "confirmation": "I will monitor the scene and alert you when the person sitting in the chair gets up and moves out of frame",
  "understood_intent": "User wants to track activity: starting state is person sitting in chair, alert when person gets up and exits the frame"
}

User: "Watch for any person entering the building"
Response: {
  "task_type": "object_detection",
  "target": "person",
  "parameters": {
    "camera_ids": ["all"],
    "duration": "continuous",
    "alert_threshold": "medium",
    "specific_conditions": ["person entering", "movement detection"]
  },
  "confirmation": "I will monitor all cameras for people entering the building and alert you when detected.",
  "understood_intent": "Continuous monitoring for people entering the building"
}

User: "Alert me if there's any suspicious activity in camera 1"
Response: {
  "task_type": "anomaly_detection",
  "target": "suspicious activity",
  "parameters": {
    "camera_ids": [1],
    "duration": "continuous",
    "alert_threshold": "high",
    "specific_conditions": ["unusual behavior", "unexpected objects", "abnormal movements"]
  },
  "confirmation": "I will monitor camera 1 for suspicious activities and send high-priority alerts.",
  "understood_intent": "Monitor camera 1 for anomalies and suspicious behavior"
}

Always be clear, concise, and security-focused. Respond only with valid JSON."""

        # Active tasks tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

    async def process_command(
        self,
        user_command: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user command and determine action

        Args:
            user_command: Natural language command from user
            context: Additional context (current cameras, recent events, etc.)

        Returns:
            Parsed command with actions to take
        """
        try:
            # Build prompt with context
            prompt = self.system_prompt

            if context:
                prompt += f"\n\nCurrent context:\n"
                if context.get('active_cameras'):
                    prompt += f"Active cameras: {context['active_cameras']}\n"
                if context.get('recent_events'):
                    prompt += f"Recent events: {context['recent_events']}\n"

            prompt += f"\n\nUser command: {user_command}"

            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            # Check if response was blocked by safety filters
            if not response.parts or not response.text:
                # Handle safety block or empty response
                from loguru import logger
                logger.warning(f"Command response blocked or empty. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")

                # Create a default surveillance task for the command
                parsed_command = {
                    "task_type": "surveillance",
                    "target": user_command,
                    "parameters": {
                        "camera_ids": ["all"],
                        "duration": "continuous",
                        "alert_threshold": "medium",
                        "specific_conditions": [user_command]
                    },
                    "confirmation": f"I will monitor for: {user_command}",
                    "understood_intent": user_command
                }
            else:
                # Parse response with better error handling
                parsed_command = self._parse_command_response(response.text)
                
                # Log parsed command for debugging
                from loguru import logger
                logger.info(f"[COMMAND] Parsed task_type: {parsed_command.get('task_type')}")
                logger.info(f"[COMMAND] Parsed target: {parsed_command.get('target')}")
                logger.info(f"[COMMAND] Parsed objects_to_detect: {parsed_command.get('parameters', {}).get('objects_to_detect')}")

            parsed_command['original_command'] = user_command
            parsed_command['timestamp'] = datetime.utcnow().isoformat()

            # Generate task ID
            task_id = f"task_{datetime.utcnow().timestamp()}"
            parsed_command['task_id'] = task_id

            # Store active task with command details
            self.active_tasks[task_id] = {
                "command": parsed_command,
                "status": "active",
                "created_at": datetime.utcnow(),
                "results": []
            }

            return parsed_command

        except Exception as e:
            return {
                "error": str(e),
                "task_type": "error",
                "confirmation": f"Sorry, I couldn't process that command: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    def _parse_command_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini's command response

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed command dictionary
        """
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()

            # Parse JSON
            command = json.loads(text)

            # Ensure required fields
            if 'task_type' not in command:
                command['task_type'] = 'scene_analysis'
            if 'confirmation' not in command:
                command['confirmation'] = "Command received and will be processed."
            if 'parameters' not in command:
                command['parameters'] = {}

            return command

        except json.JSONDecodeError:
            # If JSON parsing fails, create basic response
            return {
                "task_type": "scene_analysis",
                "target": response_text[:100],
                "parameters": {},
                "confirmation": "I'll analyze the scene as requested.",
                "understood_intent": response_text[:200]
            }

    async def analyze_with_context(
        self,
        task_id: str,
        scene_data: Dict[str, Any],
        vision_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze scene data in context of active task

        Args:
            task_id: Active task ID
            scene_data: Current scene information
            vision_analysis: Analysis from vision agent

        Returns:
            Task-specific analysis result
        """
        if task_id not in self.active_tasks:
            return {"error": "Task not found"}

        task = self.active_tasks[task_id]
        command = task['command']

        # Build analysis prompt
        prompt = f"""Analyze this surveillance data in context of the user's command.

User wanted: {command.get('understood_intent', '')}
Task type: {command.get('task_type', '')}
Target: {command.get('target', '')}

Current scene analysis:
{json.dumps(vision_analysis, indent=2)}

Respond with JSON:
{{
  "task_status": "in_progress|completed|alert_triggered",
  "findings": "What you found relevant to the user's request",
  "alert_needed": true/false,
  "alert_message": "Message for user if alert needed",
  "next_actions": ["What to do next"]
}}"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            # Parse response
            result = self._parse_command_response(response.text)

            # Store result
            task['results'].append({
                "timestamp": datetime.utcnow().isoformat(),
                "analysis": result,
                "scene_data": scene_data
            })

            return result

        except Exception as e:
            return {
                "error": str(e),
                "task_status": "error"
            }

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of active task

        Args:
            task_id: Task ID

        Returns:
            Task status or None
        """
        return self.active_tasks.get(task_id)

    async def stop_task(self, task_id: str) -> bool:
        """
        Stop an active task

        Args:
            task_id: Task ID

        Returns:
            Success status
        """
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['status'] = 'stopped'
            self.active_tasks[task_id]['stopped_at'] = datetime.utcnow()
            return True
        return False

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active tasks

        Returns:
            Dictionary of active tasks
        """
        return {
            task_id: task
            for task_id, task in self.active_tasks.items()
            if task['status'] == 'active'
        }
