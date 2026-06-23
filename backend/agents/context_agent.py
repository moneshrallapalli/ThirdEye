"""
Context Agent - Manages historical context, pattern recognition, and anomaly detection
Uses ChromaDB for semantic search of past events
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database.models import Event, ContextPattern, AlertSeverity


class ContextAgent:
    """
    Manages context building, pattern recognition, and anomaly detection
    using ChromaDB for semantic search and historical analysis
    """

    def __init__(self, persist_directory: str = None):
        """
        Initialize Context Agent with ChromaDB

        Args:
            persist_directory: Directory for ChromaDB persistence
        """
        persist_dir = persist_directory or settings.CHROMA_PERSIST_DIRECTORY

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Use ChromaDB's built-in embedding function (onnxruntime, no torch needed)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Create or get collections
        self.scene_collection = self.client.get_or_create_collection(
            name="scene_descriptions",
            embedding_function=self.embedding_function,
            metadata={"description": "Scene descriptions from Gemini"}
        )

        self.pattern_collection = self.client.get_or_create_collection(
            name="behavior_patterns",
            embedding_function=self.embedding_function,
            metadata={"description": "Learned behavior patterns"}
        )

    async def store_scene_description(
        self,
        event_id: int,
        camera_id: int,
        timestamp: datetime,
        scene_description: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store scene description as vector embedding

        Args:
            event_id: Event ID
            camera_id: Camera ID
            timestamp: Event timestamp
            scene_description: Gemini's scene description
            metadata: Additional metadata

        Returns:
            Embedding ID
        """
        embedding_id = f"event_{event_id}_{timestamp.isoformat()}"

        # Prepare metadata
        meta = {
            "event_id": event_id,
            "camera_id": camera_id,
            "timestamp": timestamp.isoformat(),
            "hour_of_day": timestamp.hour,
            "day_of_week": timestamp.weekday(),
            **metadata
        }

        # Add to collection
        self.scene_collection.add(
            documents=[scene_description],
            ids=[embedding_id],
            metadatas=[meta]
        )

        return embedding_id

    async def find_similar_events(
        self,
        scene_description: str,
        n_results: int = 5,
        camera_id: Optional[int] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar past events using semantic search

        Args:
            scene_description: Current scene description
            n_results: Number of results to return
            camera_id: Filter by camera ID
            time_range: Filter by time range (start, end)

        Returns:
            List of similar events with metadata
        """
        # Build where clause for filtering
        where_clause = {}
        if camera_id is not None:
            where_clause["camera_id"] = camera_id

        # Cap n_results to collection size to avoid hnswlib errors
        collection_count = self.scene_collection.count()
        if collection_count == 0:
            return []
        actual_n = min(n_results, collection_count)

        # Query ChromaDB
        results = self.scene_collection.query(
            query_texts=[scene_description],
            n_results=actual_n,
            where=where_clause if where_clause else None
        )

        # Format results
        similar_events = []
        if results and results['ids']:
            for i, doc_id in enumerate(results['ids'][0]):
                similar_events.append({
                    "embedding_id": doc_id,
                    "description": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })

        return similar_events

    async def build_temporal_context(
        self,
        event_id: int,
        camera_id: int,
        timestamp: datetime,
        lookback_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Build temporal context - what happened before and after

        Args:
            event_id: Current event ID
            camera_id: Camera ID
            timestamp: Event timestamp
            lookback_minutes: How far back to look

        Returns:
            Temporal context summary
        """
        start_time = timestamp - timedelta(minutes=lookback_minutes)
        end_time = timestamp + timedelta(minutes=lookback_minutes)

        # Query events in time window (cap to collection size)
        collection_count = self.scene_collection.count()
        if collection_count == 0:
            return {"before": [], "after": [], "total_events": 0}
        results = self.scene_collection.query(
            query_texts=["temporal context"],
            n_results=min(50, collection_count),
            where={
                "camera_id": camera_id
            }
        )

        # Filter by time range
        temporal_events = []
        if results and results['metadatas']:
            for i, meta in enumerate(results['metadatas'][0]):
                event_time = datetime.fromisoformat(meta['timestamp'])
                if start_time <= event_time <= end_time and meta.get('event_id') != event_id:
                    temporal_events.append({
                        "timestamp": meta['timestamp'],
                        "description": results['documents'][0][i],
                        "metadata": meta
                    })

        # Sort by timestamp
        temporal_events.sort(key=lambda x: x['timestamp'])

        return {
            "before": [e for e in temporal_events if datetime.fromisoformat(e['timestamp']) < timestamp],
            "after": [e for e in temporal_events if datetime.fromisoformat(e['timestamp']) > timestamp],
            "total_events": len(temporal_events)
        }

    async def detect_anomaly(
        self,
        scene_description: str,
        timestamp: datetime,
        camera_id: int,
        similarity_threshold: float = 0.7
    ) -> Tuple[bool, float, str]:
        """
        Detect if current scene is anomalous compared to historical patterns

        Args:
            scene_description: Current scene description
            timestamp: Event timestamp
            camera_id: Camera ID
            similarity_threshold: Threshold for anomaly detection

        Returns:
            Tuple of (is_anomaly, confidence, explanation)
        """
        # Get similar events from same time of day and day of week
        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        # Find similar events
        similar_events = await self.find_similar_events(
            scene_description,
            n_results=10,
            camera_id=camera_id
        )

        if not similar_events:
            return True, 0.9, "No historical data for comparison - potentially novel event"

        # Calculate average similarity distance
        avg_distance = sum(e.get('distance', 1.0) for e in similar_events) / len(similar_events)

        # Check if distances are all high (indicating anomaly)
        is_anomaly = avg_distance > similarity_threshold
        confidence = min(avg_distance, 1.0)

        if is_anomaly:
            explanation = f"Scene differs significantly from {len(similar_events)} historical events (avg distance: {avg_distance:.2f})"
        else:
            explanation = f"Scene matches historical patterns (avg distance: {avg_distance:.2f})"

        return is_anomaly, confidence, explanation

    async def identify_patterns(
        self,
        camera_id: Optional[int] = None,
        min_frequency: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Identify recurring patterns from historical data

        Args:
            camera_id: Filter by camera ID
            min_frequency: Minimum occurrences to be considered a pattern

        Returns:
            List of identified patterns
        """
        # Query all events
        where_clause = {"camera_id": camera_id} if camera_id else None

        # Get all events (in batches if needed)
        all_results = self.scene_collection.get(
            where=where_clause,
            limit=1000
        )

        if not all_results or not all_results['metadatas']:
            return []

        # Group by hour of day and day of week
        time_patterns = {}
        for i, meta in enumerate(all_results['metadatas']):
            hour = meta.get('hour_of_day', 0)
            day = meta.get('day_of_week', 0)
            key = f"hour_{hour}_day_{day}"

            if key not in time_patterns:
                time_patterns[key] = []

            time_patterns[key].append({
                "description": all_results['documents'][i],
                "metadata": meta
            })

        # Identify patterns with sufficient frequency
        patterns = []
        for time_key, events in time_patterns.items():
            if len(events) >= min_frequency:
                # Extract hour and day from key
                parts = time_key.split('_')
                hour = int(parts[1])
                day = int(parts[3])

                patterns.append({
                    "pattern_type": "temporal_routine",
                    "hour_of_day": hour,
                    "day_of_week": day,
                    "frequency": len(events),
                    "description": f"Regular activity at hour {hour} on day {day}",
                    "sample_events": events[:3]  # Include sample events
                })

        return patterns

    async def get_context_for_event(
        self,
        scene_description: str,
        timestamp: datetime,
        camera_id: int
    ) -> str:
        """
        Build comprehensive context summary for an event

        Args:
            scene_description: Scene description
            timestamp: Event timestamp
            camera_id: Camera ID

        Returns:
            Context summary text
        """
        # Get similar events
        similar = await self.find_similar_events(scene_description, n_results=3, camera_id=camera_id)

        # Get temporal context
        temporal = await self.build_temporal_context(0, camera_id, timestamp)

        # Detect anomaly
        is_anomaly, confidence, explanation = await self.detect_anomaly(
            scene_description, timestamp, camera_id
        )

        # Build context summary
        context_parts = []

        if similar:
            context_parts.append(f"Similar past events: {len(similar)} found")
            for evt in similar[:2]:
                context_parts.append(f"  - {evt['description'][:100]}...")

        if temporal['before']:
            context_parts.append(f"\nRecent activity (last 30 min): {len(temporal['before'])} events")

        if is_anomaly:
            context_parts.append(f"\n⚠️ ANOMALY DETECTED: {explanation}")

        context_summary = "\n".join(context_parts) if context_parts else "No historical context available"

        return context_summary

    async def track_object_history(
        self,
        object_type: str,
        tracking_id: str,
        description: str,
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Track appearances of a specific object/person over time

        Args:
            object_type: Type of object (person, vehicle, etc.)
            tracking_id: Tracking ID
            description: Object description
            timestamp: Current timestamp

        Returns:
            Historical appearances of this object
        """
        # Search for similar objects (cap to collection size)
        collection_count = self.scene_collection.count()
        if collection_count == 0:
            return []
        results = self.scene_collection.query(
            query_texts=[f"{object_type}: {description}"],
            n_results=min(20, collection_count)
        )

        # Filter to find same tracking ID or very similar descriptions
        appearances = []
        if results and results['metadatas']:
            for i, meta in enumerate(results['metadatas']):
                if meta.get('tracking_id') == tracking_id or results['distances'][0][i] < 0.3:
                    appearances.append({
                        "timestamp": meta['timestamp'],
                        "description": results['documents'][0][i],
                        "metadata": meta,
                        "similarity": 1 - results['distances'][0][i]
                    })

        return sorted(appearances, key=lambda x: x['timestamp'], reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored data

        Returns:
            Statistics dictionary
        """
        scene_count = self.scene_collection.count()
        pattern_count = self.pattern_collection.count()

        return {
            "total_scenes": scene_count,
            "total_patterns": pattern_count,
            "collections": {
                "scenes": scene_count,
                "patterns": pattern_count
            }
        }
