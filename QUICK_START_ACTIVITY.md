# Quick Start - Activity Detection

## Your Query:
```
"notify me when the person sitting in chair gets up and moves out of the frame"
```

## How to Test (3 Minutes)

### 1. Restart Backend
```bash
cd /Users/monesh/University/practice
./restart.sh
```

### 2. Open Frontend
```
http://localhost:3000
```

### 3. Type Your Command
In the command box:
```
notify me when the person sitting in chair gets up and moves out of the frame
```

### 4. See Confirmation
```
✓ Command Processed
Task: activity_detection
Confirmation: I will monitor the scene and alert you when the person 
              sitting in the chair gets up and moves out of frame
```

### 5. Sit Down
- Sit in front of camera
- Stay visible
- Wait 10 seconds

### 6. Watch for Baseline
```
System Message:
✓ Baseline established: Person sitting in chair, working at desk.
  Now monitoring for changes...
```

### 7. Stand Up and Leave
- Stand up from chair
- Walk out of frame
- Go completely out of view

### 8. Get Alert! (Within 10-20 seconds)
```
🚨 ACTIVITY DETECTED! (Confidence: 85%)

You asked to be notified when: Person gets up from chair AND moves out of frame

What happened: Person has gotten up and is exiting the frame

Baseline was: Person sitting in chair
Current state: Frame shows empty chair, person has left

Time elapsed: 45s

[Image attached]
```

## What Makes This Different?

### BEFORE (Object Detection Only)
```
Query: "alert if you see scissors"
Result: Looks for scissors in every frame
Alert: When scissors appear
```

### NOW (Activity Detection)  
```
Query: "notify when person gets up and leaves"
Step 1: Records baseline (you sitting)
Step 2: Compares each frame to baseline
Step 3: Detects when you stand and leave
Alert: When activity completes
```

## Debug Tips

### Check Logs
```bash
cd backend
tail -f logs/*.log
```

**Look for:**
```
[USER QUERY ACTIVE] Type: activity | Requires baseline: True
[BASELINE ESTABLISHED] State: Person sitting...
[ACTIVITY TRACKING] Baseline match: False | Query match: True (85%)
🚨 IMMEDIATE ALERT: Reasons=['activity_detected_85%']
```

### If Baseline Doesn't Establish
- Sit clearly visible to camera
- Wait 15-20 seconds
- Check camera has permission
- Look for "baseline_established" in logs

### If No Alert When You Move
- Make sure you **fully leave frame**
- Stand up **clearly** (don't just lean)
- Wait 10-20 seconds after leaving
- Check logs for query_confidence value

## More Examples

```bash
"alert when someone enters the room"
"notify me if person picks up an object"
"let me know when the door opens"
"alert when package is removed from desk"
```

---

**Ready to test!** Restart backend and try your query. 🚀

