"""
Reasoning Agent - Uses Claude to analyze vision outputs and make intelligent alert decisions
"""
import anthropic
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class ReasoningAgent:
    """
    Claude-powered reasoning agent that monitors vision agent outputs
    and makes intelligent decisions about when to alert users
    """

    def __init__(self, api_key: str = None):
        """
        Initialize Reasoning Agent with Claude

        Args:
            api_key: Anthropic API key for Claude
        """
        self.api_key = api_key or settings.CLAUDE_API_KEY
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Maintain conversation history for context
        self.observation_history: List[Dict[str, Any]] = []
        self.max_history = 10  # Keep last 10 observations
        
    async def analyze_scene_progression(
        self,
        user_query: str,
        baseline_state: Optional[str],
        current_observation: Dict[str, Any],
        previous_observations: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze scene progression using Claude to determine if user's query is satisfied
        
        Args:
            user_query: User's original query/request
            baseline_state: Initial baseline state (if applicable)
            current_observation: Latest observation from vision agent
            previous_observations: Recent history of observations
            
        Returns:
            Decision about whether to alert and confidence
        """
        try:
            # Build context from observations
            context = self._build_observation_context(
                user_query,
                baseline_state,
                current_observation,
                previous_observations or []
            )
            
            # Create Claude prompt
            system_prompt = """You are an intelligent surveillance monitoring system that analyzes vision agent outputs to detect when specific user-requested events occur.

Your role:
1. Understand EXACTLY what the user is asking for
2. Analyze the PROGRESSION of observations from the vision agent
3. Detect when the user's specific condition/event has occurred
4. Provide HIGH CONFIDENCE alerts when conditions are met

Key principles:
- Focus on CHANGE and TEMPORAL PROGRESSION, not just static states
- If baseline had person and now has NO person → Person LEFT (HIGH confidence!)
- If user asks "when X leaves" and X is now absent → IMMEDIATE ALERT
- Analyze the SEQUENCE of observations to understand what happened
- Be DECISIVE - when the condition is clearly met, give 95%+ confidence

CRITICAL for "person leaves" queries:
- Baseline: Person present
- Current: No person visible
- Conclusion: Person has LEFT → 95%+ confidence, IMMEDIATE ALERT"""

            user_prompt = f"""Analyze this surveillance scenario and determine if the user's query has been satisfied.

USER'S REQUEST: {user_query}

{context}

Analyze:
1. What is the user looking for? (Extract the key condition/event)
2. What was the baseline/initial state?
3. How has the scene progressed over recent observations?
4. Has the user's requested event/condition occurred?
5. What is your confidence that the query is satisfied?

Respond with JSON ONLY:
{{
  "query_understood": "Clear explanation of what user wants",
  "baseline_state_summary": "Summary of initial state",
  "current_state_summary": "Summary of current state",
  "progression_analysis": "How the scene has changed over time",
  "event_occurred": true/false,
  "confidence_percentage": 0-100,
  "reasoning": "Detailed explanation of why event occurred or not",
  "should_alert": true/false,
  "alert_priority": "CRITICAL|HIGH|MEDIUM|LOW",
  "alert_message": "Clear message for user if alert needed"
}}

CRITICAL: If user asked about "person leaving" and person was present but is now ABSENT, set:
- event_occurred: true
- confidence_percentage: 95
- should_alert: true
- alert_priority: "CRITICAL"
"""

            # Call Claude API
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",  # Claude 3 Haiku (fast and available)
                max_tokens=2000,
                temperature=0.3,  # Lower temp for more consistent reasoning
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse response
            response_text = response.content[0].text
            decision = self._parse_claude_response(response_text)
            
            # Add metadata
            decision['timestamp'] = datetime.utcnow().isoformat()
            decision['model_used'] = 'claude-3-5-sonnet'
            
            return decision
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Reasoning Agent error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "error": str(e),
                "event_occurred": False,
                "should_alert": False,
                "confidence_percentage": 0,
                "reasoning": f"Error in reasoning: {str(e)}"
            }
    
    def _build_observation_context(
        self,
        user_query: str,
        baseline_state: Optional[str],
        current_observation: Dict[str, Any],
        previous_observations: List[Dict[str, Any]]
    ) -> str:
        """Build context string from observations"""
        
        context = ""
        
        if baseline_state:
            context += f"""BASELINE STATE (Initial):
{baseline_state}

"""
        
        if previous_observations:
            context += "RECENT OBSERVATIONS (Chronological):\n"
            for i, obs in enumerate(previous_observations[-5:], 1):  # Last 5
                scene = obs.get('scene_description', 'N/A')
                timestamp = obs.get('timestamp', 'N/A')
                context += f"{i}. [{timestamp}] {scene}\n"
            context += "\n"
        
        context += f"""CURRENT OBSERVATION (Latest):
Timestamp: {current_observation.get('timestamp', 'N/A')}
Scene Description: {current_observation.get('scene_description', 'N/A')}
Detections: {current_observation.get('detections', [])}
Significance: {current_observation.get('significance', 0)}%
Activity: {current_observation.get('activity', 'N/A')}
"""
        
        # Add vision agent's own assessment if available
        if 'query_match' in current_observation:
            context += f"""
Vision Agent Assessment:
- Query Match: {current_observation.get('query_match', False)}
- Query Confidence: {current_observation.get('query_confidence', 0)}%
- Query Details: {current_observation.get('query_details', 'N/A')}
- Baseline Match: {current_observation.get('baseline_match', 'N/A')}
- Changes Detected: {current_observation.get('changes_detected', [])}
"""
        
        return context
    
    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
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
            decision = json.loads(text)
            
            # Ensure required fields
            if 'event_occurred' not in decision:
                decision['event_occurred'] = False
            if 'should_alert' not in decision:
                decision['should_alert'] = False
            if 'confidence_percentage' not in decision:
                decision['confidence_percentage'] = 0
                
            return decision
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, extract key information
            return {
                "event_occurred": "true" in response_text.lower() and "event_occurred" in response_text.lower(),
                "should_alert": "should_alert" in response_text.lower() and "true" in response_text.lower(),
                "confidence_percentage": 50,
                "reasoning": response_text[:500],
                "parse_error": str(e)
            }
    
    def add_observation(self, observation: Dict[str, Any]):
        """Add observation to history for context"""
        self.observation_history.append(observation)
        
        # Keep only recent observations
        if len(self.observation_history) > self.max_history:
            self.observation_history = self.observation_history[-self.max_history:]
    
    def get_observation_history(self) -> List[Dict[str, Any]]:
        """Get recent observation history"""
        return self.observation_history.copy()
    
    def clear_history(self):
        """Clear observation history"""
        self.observation_history = []

