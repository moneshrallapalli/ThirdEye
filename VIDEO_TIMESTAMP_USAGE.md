# Video Timestamp Feature - Usage Guide

## Overview

Your surveillance system now supports **video timestamp queries** using Google's Gemini API! You can:

1. **Query for specific scenes** and get exact timestamps when they occur
2. **Analyze complete videos** and get a timeline of all events
3. **Only get timestamps when asking about specific scenes** (not in regular frame analysis)

---

## Features

### 1. Scene Query with Timestamps

Ask questions about when specific events occur in a video and get MM:SS timestamps.

**Endpoint**: `POST /api/video/query-scene`

**Example Questions**:
- "when does a person wearing red appear?"
- "when does someone enter through the door?"
- "when is there a vehicle in the frame?"
- "when does suspicious activity occur?"

### 2. Video Timeline Analysis

Get a complete timeline of all significant events in a video with timestamps.

**Endpoint**: `POST /api/video/timeline`

---

## Usage Examples

### Python Examples

#### Example 1: Query for Specific Scene

```python
import requests
import json

# API endpoint
url = "http://localhost:8000/api/video/query-scene"

# Request payload
payload = {
    "video_file_path": "/path/to/surveillance_footage.mp4",
    "scene_query": "when does a person wearing red clothing appear?",
    "camera_id": 1,
    "fps": 2  # Optional: higher FPS for more detail (costs more tokens)
}

# Make request
response = requests.post(url, json=payload)
result = response.json()

# Process results
if result['found']:
    print(f"Scene found at {len(result['timestamps'])} timestamp(s):")
    for desc in result['descriptions']:
        print(f"\n  ⏰ {desc['timestamp']}")
        print(f"     {desc['description']}")
        print(f"     Confidence: {desc['confidence']}")
        print(f"     Details: {', '.join(desc['key_details'])}")
else:
    print("Scene not found in video")
```

**Example Output**:
```
Scene found at 3 timestamp(s):

  ⏰ 00:15
     Person in red shirt enters from left side of frame
     Confidence: 0.95
     Details: red shirt, walking, carrying bag

  ⏰ 01:23
     Same person in red returns to view
     Confidence: 0.92
     Details: red clothing, standing, facing camera

  ⏰ 02:45
     Person in red exits through main door
     Confidence: 0.88
     Details: red shirt, exiting, door opening
```

#### Example 2: Get Video Timeline

```python
import requests

url = "http://localhost:8000/api/video/timeline"

payload = {
    "video_file_path": "/path/to/surveillance.mp4",
    "camera_id": 1,
    "fps": 2
}

response = requests.post(url, json=payload)
timeline = response.json()

print(f"Video Duration: {timeline['total_duration']}")
print(f"\nSummary: {timeline['summary']}")
print(f"\nKey Moments: {', '.join(timeline['key_moments'])}")
print(f"\n{'='*60}")
print("Timeline of Events:")
print('='*60)

for event in timeline['events']:
    print(f"\n⏰ {event['timestamp']} - {event['event_type'].upper()}")
    print(f"   {event['description']}")
    print(f"   Significance: {event['significance']}/100")
    print(f"   Detections: {', '.join(event['detections'])}")
```

**Example Output**:
```
Video Duration: 05:30

Summary: Video shows normal activity with 3 people and 2 vehicles throughout the 5.5 minute period

Key Moments: 00:45, 02:15, 04:30

============================================================
Timeline of Events:
============================================================

⏰ 00:00 - PERSON_DETECTED
   Person enters frame from left side
   Significance: 60/100
   Detections: person

⏰ 00:45 - VEHICLE_DETECTED
   Car parks in designated area
   Significance: 75/100
   Detections: vehicle, person

⏰ 02:15 - OBJECT_MOVED
   Person picks up package from ground
   Significance: 85/100
   Detections: person, package

⏰ 04:30 - PERSON_DETECTED
   Two people appear in conversation
   Significance: 70/100
   Detections: person, person
```

### cURL Examples

#### Query Scene

```bash
curl -X POST http://localhost:8000/api/video/query-scene \
  -H "Content-Type: application/json" \
  -d '{
    "video_file_path": "/path/to/video.mp4",
    "scene_query": "when does a person enter the room?",
    "fps": 2
  }'
```

#### Get Timeline

```bash
curl -X POST http://localhost:8000/api/video/timeline \
  -H "Content-Type: application/json" \
  -d '{
    "video_file_path": "/path/to/video.mp4",
    "camera_id": 1,
    "fps": 1
  }'
```

### JavaScript/Frontend Example

```javascript
// Query for specific scene
async function queryScene(videoPath, sceneQuery) {
  const response = await fetch('http://localhost:8000/api/video/query-scene', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_file_path: videoPath,
      scene_query: sceneQuery,
      fps: 2
    })
  });

  const result = await response.json();

  if (result.found) {
    console.log(`Found at: ${result.timestamps.join(', ')}`);
    result.descriptions.forEach(desc => {
      console.log(`${desc.timestamp}: ${desc.description}`);
    });
  } else {
    console.log('Scene not found');
  }

  return result;
}

// Usage
await queryScene(
  '/recordings/camera1_20251116.mp4',
  'when does a person wearing red appear?'
);
```

---

## API Response Formats

### Scene Query Response

```json
{
  "scene_query": "when does a person wearing red appear?",
  "camera_id": 1,
  "video_file": "/path/to/video.mp4",
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
  "summary": "Person in red clothing appears 3 times throughout the video",
  "processed_at": "2025-11-16T06:45:00.000Z"
}
```

### Timeline Response

```json
{
  "camera_id": 1,
  "video_file": "/path/to/video.mp4",
  "events": [
    {
      "timestamp": "00:00",
      "event_type": "person_detected",
      "description": "Person enters frame from left",
      "significance": 60,
      "detections": ["person"]
    }
  ],
  "summary": "Video shows normal activity",
  "total_duration": "05:30",
  "key_moments": ["00:45", "02:15"],
  "processed_at": "2025-11-16T06:45:00.000Z"
}
```

---

## Configuration

### FPS (Frames Per Second) Settings

- **Default: 1 FPS** - Good for static scenes, cost-efficient
- **2-5 FPS** - Better for dynamic scenes with movement
- **Higher FPS** - More detail but higher token costs

**Token Cost Estimates** (per second of video):
- 1 FPS: ~300 tokens
- 5 FPS: ~1500 tokens
- Audio: +32 tokens per second

### Supported Video Formats

- MP4
- AVI
- MOV
- MKV

---

## Important Notes

1. **Timestamps only on query**: Regular frame analysis doesn't include timestamps. You must explicitly query for scenes to get timestamps.

2. **Video Upload**: Videos are temporarily uploaded to Gemini API for processing and automatically deleted after analysis.

3. **Processing Time**: Video processing happens in real-time. Longer videos take more time.

4. **File Paths**: Must be absolute paths to video files on your server.

5. **Timestamp Format**: Always returned in MM:SS format (e.g., "02:15" for 2 minutes 15 seconds).

---

## Best Practices

1. **Start with Timeline Analysis**: Get an overview of the video first
2. **Then Query Specific Scenes**: Ask about particular events you're interested in
3. **Adjust FPS Based on Content**:
   - Static scenes (lecture, parking lot): 1 FPS
   - Dynamic scenes (retail, entrance): 2-5 FPS
4. **Be Specific in Queries**: "when does a person in red shirt enter?" is better than "when is there a person?"
5. **Consider Token Costs**: Higher FPS = more detail but higher costs

---

## API Capabilities Endpoint

Get information about all available features:

```bash
curl http://localhost:8000/api/video/capabilities
```

This returns detailed documentation about supported features, formats, and usage tips.

---

## Integration with Existing System

The video timestamp features are **separate** from your real-time surveillance:

- **Real-time analysis** (`analyze_frame()`): Continues as normal, no timestamps
- **Video queries** (`query_scene_in_video()`): Only when you explicitly query recorded videos
- **Timeline analysis** (`analyze_video_with_timestamps()`): For post-event review

---

## Example Use Cases

### Security Review
```python
# Review yesterday's footage for specific incident
result = await query_scene_in_video(
    "/recordings/camera1_yesterday.mp4",
    "when does someone approach the back door?"
)
```

### Incident Investigation
```python
# Get full timeline of suspicious activity
timeline = await analyze_video_with_timestamps(
    "/recordings/incident_footage.mp4",
    fps=3  # Higher detail for investigation
)
```

### Pattern Analysis
```python
# Check multiple times a specific event occurred
result = await query_scene_in_video(
    "/recordings/parking_lot_week.mp4",
    "when does a red car enter the parking lot?"
)
print(f"Red car appeared {len(result['timestamps'])} times this week")
```

---

## Troubleshooting

### "Video file not found"
- Ensure the path is absolute, not relative
- Check file permissions
- Verify the file exists on the server

### "Video processing failed"
- Check video format is supported
- Ensure video isn't corrupted
- Try reducing FPS if video is very long

### "Analysis failed"
- Check your Gemini API key is valid
- Ensure you have API quota remaining
- Try with a shorter video clip first

---

## Need Help?

- Check API docs: `http://localhost:8000/docs`
- View capabilities: `GET /api/video/capabilities`
- Check server logs for detailed error messages
