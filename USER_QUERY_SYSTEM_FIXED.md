# User Query System - FIXED ✅

## Problem Solved
The system was doing generic scene narration and sending alerts for general activity instead of understanding and searching for what you specifically asked for in plain English.

## What's Fixed Now ✅

### 1. **Natural Language Understanding**
- ✅ System now understands plain English queries
- ✅ Extracts what you're looking for from your question
- ✅ Focuses detection on YOUR specific query

### 2. **Targeted Detection**
- ✅ Vision agent focuses ONLY on what you asked for
- ✅ Returns `query_match` and `query_confidence` for your query
- ✅ Ignores general activity when you have an active search

### 3. **Smart Alerting**
- ✅ **Critical alerts ONLY when:**
  - Your specific query is found (≥60% confidence)
  - OR dangerous keywords detected (safety)
- ✅ **NO MORE general activity alerts** when you're searching for something specific
- ✅ 2-minute summaries still work for background monitoring

## How To Use It 🎯

### Example 1: Search for Specific Object
```
You type: "alert me if you see scissors"

System:
1. ✓ Understands you want to find "scissors"
2. ✓ Starts monitoring camera
3. ✓ Focuses detection on scissors only
4. ✓ Sends alert ONLY when scissors detected (≥60% confidence)
5. ✓ Ignores other objects (phone, laptop, etc.)
```

### Example 2: Look for Person
```
You type: "watch for people entering"

System:
1. ✓ Understands you want to detect "person"
2. ✓ Monitors for people
3. ✓ Sends alert when person detected
4. ✓ Shows confidence score
```

### Example 3: Find Specific Item
```
You type: "look for my phone"

System:
1. ✓ Understands you want to find "phone"
2. ✓ Scans frames for phone
3. ✓ Alerts when phone found (≥60%)
4. ✓ Shows image with the phone
```

## Alert Types 🚨

### Immediate Alerts (Sent Instantly)
✅ **User Query Match** - Your specific search found (≥60% confidence)
- Title: "✓ [Object] Detected - Camera 0"
- Shows what you were looking for
- Shows confidence score
- Includes image evidence

✅ **Danger Detected** - Safety keywords found
- Title: "🚨 CRITICAL DANGER ALERT"
- Always triggers (safety first)
- Includes details

### 2-Minute Summaries (Background)
- Sent every 2 minutes
- Summarizes general activity
- Does NOT interrupt your specific search
- Only for events not matching your query

## Technical Changes Made 🔧

### 1. Vision Agent (`vision_agent.py`)
```python
# Added user_query parameter
async def analyze_frame(frame, camera_id, user_query=None):
    # If user_query provided, focus detection on it
    # Returns:
    # - query_match: true/false
    # - query_confidence: 0-100
    # - query_details: explanation
```

### 2. Surveillance Worker (`main.py`)
```python
# Extract user query from active tasks
if active_tasks:
    user_query = task.get('target')  # e.g., "scissors"
    
# Pass to vision agent
analysis = await vision_agent.analyze_frame(frame, camera_id, user_query=user_query)

# Alert ONLY if query matches
if user_query and query_match and query_confidence >= 60:
    send_alert()  # ✓ Found what you're looking for!
```

### 3. Alert Logic
**BEFORE:**
- Alerts for ANY activity ≥60%
- Too many false positives
- Generic notifications

**AFTER:**
- Alerts ONLY when your query matches ≥60%
- Focused on what YOU asked for
- Meaningful notifications

## Configuration ⚙️

### Threshold Setting (`config.py`)
```python
IMMEDIATE_ALERT_THRESHOLD = 60  # Confidence needed for alerts
```

To change:
```python
# Option 1: Edit backend/config.py
IMMEDIATE_ALERT_THRESHOLD = 70  # More strict

# Option 2: Add to backend/.env
IMMEDIATE_ALERT_THRESHOLD=70
```

## Example Usage Flow 📝

### Step 1: Ask in Plain English
In the frontend command box, type:
```
"alert me if you see a nail cutter"
```

### Step 2: System Confirms Understanding
```
✓ Command Processed
Task: Object Detection
Target: nail cutter
Looking for: nail cutter
```

### Step 3: Monitoring Starts
```
🎯 USER QUERY ACTIVE: Looking for nail cutter
Camera 0 analyzing frames...
Query: 'nail cutter' | Match: false | Confidence: 0%
```

### Step 4: When Found
```
🎯 QUERY MATCH! 
Query: 'nail cutter' | Match: true | Confidence: 85%

🚨 IMMEDIATE ALERT SENT:
✓ Nail Cutter Detected - Camera 0
Confidence: 85%
[Image attached]
```

## What No Longer Happens ❌

### BEFORE (Problems):
❌ Alerts for ANY object detected
❌ "Phone detected" when you're looking for scissors
❌ Too many irrelevant notifications
❌ Generic scene narration alerts
❌ Confusion about what triggered the alert

### AFTER (Fixed):
✅ Alerts ONLY for YOUR specific query
✅ Focused detection
✅ Relevant notifications only
✅ Clear what was found
✅ Confidence scores shown

## Testing Your Queries 🧪

### Test 1: Specific Object
```bash
Command: "look for scissors"
Expected: Alert ONLY when scissors detected
Should NOT alert: Phone, laptop, pen, etc.
```

### Test 2: Person Detection
```bash
Command: "watch for people"
Expected: Alert when person enters frame
Should NOT alert: Empty room, objects only
```

### Test 3: Multiple Objects
```bash
Command: "alert me if you see a phone or laptop"
Expected: Alert when either detected
Confidence: ≥60% required
```

## Scene Narration Still Works ✅

**Live Feed:**
- Still shows continuous scene descriptions
- Updates every 5 seconds
- Shows all detected objects
- No alerts (just information)

**2-Minute Summaries:**
- Still sent every 2 minutes
- Summarizes general activity
- Includes all objects seen
- Low priority (not immediate)

## API Endpoints Updated 🔌

### POST /system/command
```json
{
  "command": "alert me if you see scissors"
}

Response:
{
  "task_id": "task_12345",
  "task_type": "object_detection",
  "target": "scissors",
  "confirmation": "I will monitor for scissors and alert you when detected",
  "understood_intent": "User wants to be alerted when scissors appear"
}
```

## How Confidence Works 📊

```
90-100% = Very High Confidence - Definitely found it
75-89%  = High Confidence - Very likely found it
60-74%  = Medium Confidence - Probably found it (alerts)
40-59%  = Low Confidence - Might be it (no alert)
0-39%   = Very Low - Not found (no alert)
```

## Restart Required ♻️

To apply all changes:

```bash
cd /Users/monesh/University/practice

# Option 1: Use restart script
./restart.sh

# Option 2: Manual restart
./stop.sh
./start.sh

# Option 3: Backend only
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Verification Checklist ✓

After restart, verify:

1. ✅ Enter command: "alert me if you see [object]"
2. ✅ System confirms understanding
3. ✅ Camera starts (if not already running)
4. ✅ Logs show: `[USER QUERY ACTIVE] Looking for: [object]`
5. ✅ Alerts sent ONLY when object found ≥60%
6. ✅ Alert shows confidence score
7. ✅ Image attached to alert
8. ✅ 2-minute summaries still work

## Example Commands to Try 💬

```
"alert me if you see scissors"
"watch for my phone"
"look for a person entering"
"detect any nail cutters"
"monitor for suspicious activity"
"find my laptop"
"watch for someone at the door"
"alert if you see any tools"
```

## Logging for Debugging 📝

Watch logs to see what's happening:

```bash
cd /Users/monesh/University/practice/backend
tail -f logs/*.log
```

Key log messages:
```
[USER QUERY ACTIVE] Looking for: scissors
[QUERY MATCH] Query: 'scissors' | Match: true | Confidence: 85%
🚨 IMMEDIATE ALERT: Reasons=['user_query_matched_85%']
```

## Troubleshooting 🔧

### "No alerts when object detected"
**Check:**
- Is confidence ≥60%?
- Look at logs for query_confidence value
- Object might not be clearly visible

### "Still getting general alerts"
**Check:**
- Do you have an active user query?
- Dangerous keywords trigger regardless (safety)
- Check if it's a 2-minute summary (background)

### "System doesn't understand my query"
**Try:**
- Be specific: "look for scissors" not "find that thing"
- Name the object clearly
- Check system confirms understanding

---

**Status**: ✅ **FIXED AND READY**
**Date**: November 19, 2025
**Changes**: Vision Agent + Surveillance Worker + Alert Logic
**Benefits**: Focused detection, relevant alerts, user-driven search

