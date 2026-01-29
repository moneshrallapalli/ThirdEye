# Activity Detection System - Complete Guide

## 🎯 What's New

The system now understands **ACTIVITY and STATE CHANGE** queries, not just static object detection!

### Supported Query Types

1. **Object Detection** - "alert me if you see scissors"
2. **Activity Detection** - "notify me when person gets up and leaves"  ← **NEW!**
3. **State Change Detection** - "alert when the door opens" ← **NEW!**

## 🚀 Your Example Query

```
"notify me when the person sitting in chair gets up and moves out of the frame"
```

### How It Works

#### Step 1: Command Understanding ✓
```
System receives: "notify me when person sitting in chair gets up and moves out of frame"
                 ↓
CommandAgent parses:
{
  "task_type": "activity_detection",
  "query_type": "activity",
  "requires_baseline": true,
  "baseline_description": "Person sitting in chair",
  "expected_change": "Person gets up from chair AND moves out of frame",
  "activities_to_detect": ["person gets up", "person moves", "person exits frame"]
}
```

#### Step 2: Baseline Establishment ✓
```
Camera starts analyzing
                 ↓
First frame shows: Person sitting in chair
                 ↓
VisionAgent analyzes:
{
  "baseline_established": true,
  "current_state": "Person sitting in office chair, facing desk, working on laptop"
}
                 ↓
System stores: BASELINE STATE
                 ↓
User notification: "✓ Baseline established: Person sitting in office chair. 
                    Now monitoring for changes..."
```

#### Step 3: Continuous Monitoring ✓
```
Every 5 seconds:
Frame → VisionAgent → Compare to baseline
                    ↓
  [Still sitting] → No alert (baseline_match: true)
  [Still sitting] → No alert
  [Still sitting] → No alert
```

#### Step 4: Change Detection ✓
```
New frame shows: Person standing, moving toward edge
                 ↓
VisionAgent with baseline context:
{
  "baseline_match": false,
  "query_match": true,
  "query_confidence": 85,
  "state_analysis": "Person is standing and moving out of frame",
  "changes_detected": ["person stood up", "person moving", "person exiting frame"],
  "query_details": "Person has gotten up from the chair and is moving out of frame, matching the expected activity"
}
                 ↓
Confidence 85% >= 60% threshold
                 ↓
🚨 IMMEDIATE ALERT SENT!
```

#### Step 5: Alert Received ✓
```
🎯 ACTIVITY DETECTED! (Confidence: 85%)

You asked to be notified when: Person gets up from chair AND moves out of frame

What happened: Person has gotten up from the chair and is moving out of frame

Baseline state was: Person sitting in office chair, facing desk, working on laptop

Current state: Person is standing and moving toward the left edge of frame

Changes detected: person stood up, person moving, person exiting frame

Time elapsed: 125s since monitoring started

[Image showing person leaving frame attached]
```

## 📋 Complete Flow Diagram

```
USER TYPES QUERY
      ↓
"notify me when person sitting in chair gets up and moves out of frame"
      ↓
┌─────────────────────────────────────────────────┐
│ 1. COMMAND AGENT                                │
│    - Understands: activity_detection            │
│    - Requires: baseline tracking                │
│    - Expected: person gets up AND leaves frame  │
└─────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────┐
│ 2. SURVEILLANCE WORKER                          │
│    - Starts camera monitoring                   │
│    - Extracts: requires_baseline = true         │
│    - Task type: activity                        │
└─────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────┐
│ 3. FIRST FRAME - BASELINE                       │
│    - Vision Agent analyzes initial state        │
│    - Detects: "Person sitting in chair"         │
│    - Sets: baseline_established = true          │
│    - Stores baseline in memory                  │
│    - Notifies user: "Baseline set"              │
└─────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────┐
│ 4. CONTINUOUS MONITORING (every 5s)             │
│                                                  │
│    Frame → Vision Agent (with baseline context) │
│           ↓                                      │
│    Compare current vs baseline                  │
│           ↓                                      │
│    Still match? → No alert, continue            │
│    Changed? → Check if expected change          │
└─────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────┐
│ 5. CHANGE DETECTED                              │
│    - Person stood up ✓                          │
│    - Person moving ✓                            │
│    - Person leaving frame ✓                     │
│    - Confidence: 85%                            │
│    - Matches expected change: YES               │
└─────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────┐
│ 6. ALERT DECISION                               │
│    - query_match = true                         │
│    - query_confidence (85%) >= threshold (60%)  │
│    - SEND IMMEDIATE ALERT                       │
└─────────────────────────────────────────────────┘
      ↓
🚨 USER RECEIVES ALERT WITH IMAGE
```

## 💬 Example Commands You Can Use

### Activity Detection (Requires Baseline)

```bash
"notify me when the person sitting in chair gets up and moves out of frame"

"alert me when someone enters the room"

"let me know when the person leaves the desk"

"notify me if the person picks up an object and walks away"

"alert when someone stands up from sitting position"

"tell me when the door opens"

"notify me when the package on the desk is removed"
```

### Object Detection (No Baseline)

```bash
"alert me if you see scissors"

"find my phone"

"watch for a laptop"

"detect any person"
```

## 🔧 Technical Details

### Files Modified

1. **`backend/agents/vision_agent.py`**
   - Added baseline context handling
   - Two-mode analysis: baseline establishment vs change detection
   - Returns: `baseline_established`, `baseline_match`, `changes_detected`

2. **`backend/agents/command_agent.py`**
   - Added activity_detection task type
   - Parses: `requires_baseline`, `expected_change`, `activities_to_detect`
   - Examples showing activity queries

3. **`backend/main.py`**
   - Baseline state storage: `baseline_states = {}`
   - Passes baseline context to vision agent
   - Compares frames against baseline
   - Alerts only when expected change occurs

### Key Data Structures

#### Baseline State Storage
```python
baseline_states = {
  "task_12345": {
    "state": "Person sitting in office chair, working on laptop",
    "established_at": datetime(2025, 11, 19, 12, 30, 0),
    "frame_saved": "/path/to/baseline/frame.jpg"
  }
}
```

#### Vision Agent Response (With Baseline)
```json
{
  "scene_description": "Person is standing and moving toward edge of frame",
  "baseline_match": false,
  "query_match": true,
  "query_confidence": 85,
  "state_analysis": "Person is standing and moving out of frame",
  "changes_detected": ["person stood up", "person moving", "person exiting frame"],
  "query_details": "Person has gotten up from chair and is moving out of frame"
}
```

## 🧪 Testing Your Query

### Step 1: Start the System
```bash
cd /Users/monesh/University/practice
./restart.sh
```

### Step 2: Open Frontend
```
http://localhost:3000
```

### Step 3: Enter Your Query
In the command box:
```
notify me when the person sitting in chair gets up and moves out of the frame
```

### Step 4: Watch Confirmation
```
✓ Command Processed
Task Type: activity_detection
Requires Baseline: true
Target: person gets up and leaves
Confirmation: I will monitor the scene and alert you when the person 
              sitting in the chair gets up and moves out of frame
```

### Step 5: Sit in Front of Camera
- Make sure you're visible to the camera
- Sit in a chair
- Wait 5-10 seconds

### Step 6: Watch for Baseline
```
System Message:
✓ Baseline established: Person sitting in office chair, facing desk.
  Now monitoring for changes...
```

**Logs show:**
```
[BASELINE ESTABLISHED] State: Person sitting in office chair...
```

### Step 7: Perform the Activity
- Stand up from the chair
- Move out of the camera frame
- Walk away

### Step 8: Receive Alert (5-15 seconds later)
```
🚨 ACTIVITY DETECTED! (Confidence: 85%)

You asked to be notified when: Person gets up from chair AND moves out of frame

What happened: Person has gotten up from the chair and is moving out of frame

Baseline state was: Person sitting in office chair

Current state: Person standing and exiting frame

Changes detected: person stood up, person moving, person exiting frame

Time elapsed: 45s since monitoring started

[Image attached showing you leaving frame]
```

## 📊 Monitoring Logs

Watch real-time detection:

```bash
cd /Users/monesh/University/practice/backend
tail -f logs/*.log
```

**What to look for:**

```
[USER QUERY ACTIVE] Type: activity | Looking for: person gets up and leaves | Requires baseline: True
[BASELINE ESTABLISHED] State: Person sitting in office chair, facing desk, working on laptop
[BASELINE TRACKING] Comparing to baseline established 15s ago
[ACTIVITY TRACKING] Baseline match: True | Changes: [] | Query match: False (5%)
[ACTIVITY TRACKING] Baseline match: True | Changes: [] | Query match: False (8%)
[ACTIVITY TRACKING] Baseline match: False | Changes: ['person stood up', 'person moving'] | Query match: True (85%)
🚨 IMMEDIATE ALERT: Reasons=['activity_detected_85%']
```

## ⚙️ Configuration

### Alert Threshold
In `backend/config.py`:
```python
IMMEDIATE_ALERT_THRESHOLD = 60  # Alert when confidence >= 60%
```

Change to be more strict:
```python
IMMEDIATE_ALERT_THRESHOLD = 75  # Only alert at 75%+
```

### Camera FPS
In `backend/config.py`:
```python
CAMERA_FPS = 0.2  # 1 frame every 5 seconds
```

For faster detection:
```python
CAMERA_FPS = 0.5  # 1 frame every 2 seconds
```

## 🔍 Troubleshooting

### "Baseline never establishes"
**Problem:** System doesn't detect initial state

**Solution:**
- Make sure you're visible to camera
- Check camera permissions
- Wait 10-15 seconds for first analysis
- Check logs for "baseline_established"

### "Alert doesn't trigger when I move"
**Problem:** Activity not detected

**Check:**
1. Was baseline established? (Check logs)
2. Is change obvious enough? (stand up clearly, move away)
3. Confidence >= 60%? (Check logs for query_confidence)
4. Did you fully leave frame? (Activity requires both standing AND leaving)

### "False positives - alert when I'm still sitting"
**Problem:** Detecting change when nothing changed

**Solution:**
- Increase threshold to 75% or 80%
- Make sure lighting is consistent
- Check if there's movement in frame (other people, objects)

### "System doesn't understand my query"
**Problem:** CommandAgent can't parse query

**Try:**
- Be specific: "when person gets up" ✓
- Not vague: "when something happens" ✗
- Check confirmation message for understood_intent
- Look at logs for task_type and requires_baseline

## 🎯 Success Indicators

You know it's working when you see:

1. ✅ **Command confirmation** with "activity_detection" task type
2. ✅ **Baseline established** message within 10-15 seconds
3. ✅ **Logs show** baseline tracking comparisons
4. ✅ **No alerts** while baseline state matches (sitting)
5. ✅ **Alert triggered** when activity occurs (standing + leaving)
6. ✅ **Alert shows** before/after state comparison
7. ✅ **Confidence score** >= 60%

## 🆚 Difference from Object Detection

### Object Detection
```
Query: "alert if you see scissors"
→ Every frame: "Do I see scissors? Yes/No"
→ Alert when: scissors appear (≥60%)
→ No baseline needed
→ Stateless (each frame independent)
```

### Activity Detection  
```
Query: "notify when person gets up and leaves"
→ First frame: Establish baseline (person sitting)
→ Every frame: "Did state change from baseline?"
→ Alert when: expected change happens (≥60%)
→ Baseline required
→ Stateful (compares to initial state)
```

## 📝 Summary

**What Changed:**
- ✅ System understands temporal/activity queries
- ✅ Establishes baseline state for tracking
- ✅ Compares each frame to baseline
- ✅ Detects when expected activity occurs
- ✅ Alerts with before/after comparison
- ✅ Shows what changed and time elapsed

**Your Query Now Works:**
```
"notify me when the person sitting in chair gets up and moves out of frame"

1. Baseline: Detects you sitting ✓
2. Monitoring: Compares each frame ✓  
3. Detection: You stand up and leave ✓
4. Alert: Sends notification with details ✓
```

---

**Status:** ✅ **READY FOR TESTING**
**Date:** November 19, 2025
**New Features:** Activity Detection, State Change Tracking, Baseline Comparison

