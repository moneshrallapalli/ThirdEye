# 🧪 TEST YOUR DUAL-AI SYSTEM NOW!

## ✅ System Status: READY!

```
✅ Backend: Running (PID: 50477)
✅ Frontend: Running (PID: 50500)
✅ Claude Reasoning Agent: Initialized ✓
✅ Gemini Vision Agent: Active ✓
```

---

## 🎯 PROPER TEST PROCEDURE

### Step 1: Open Frontend
Go to: **http://localhost:3000**

### Step 2: Enter Command
In the command box, type **EXACTLY**:
```
alert me when person leaves the camera frame
```

Press Enter/Submit.

### Step 3: Wait for Confirmation (2 seconds)
You should see:
```
✓ Command Processed
Task Type: activity_detection
Status: active
Requires Baseline: true
```

### Step 4: Camera Should Auto-Start
Look for message:
```
System Message:
📹 Camera 0 auto-started for activity detection monitoring
```

### Step 5: SIT IN FRONT OF CAMERA (Important!)
**DO THIS:**
- ✅ Sit in a chair
- ✅ Make sure you're clearly visible
- ✅ **Stay completely still for 20 seconds**
- ✅ Good lighting

**Why 20 seconds?**
- The system analyzes every 5 seconds
- Needs 3-4 consistent frames to establish baseline

### Step 6: Wait for Baseline Message
After ~15-20 seconds, you should see:
```
System Message:
✓ Baseline established for activity monitoring:
  "Person seated in chair, visible in frame..."
  
Now monitoring for state changes...
```

**⚠️ IF YOU DON'T SEE THIS MESSAGE:**
- The baseline wasn't established
- System can't detect "leaving" without knowing you were there
- Go back to Step 5 and sit still longer

### Step 7: LEAVE THE FRAME
**DO THIS:**
- ✅ Stand up
- ✅ Walk completely out of camera view
- ✅ Make sure NO PART of you is visible

### Step 8: ALERT SHOULD TRIGGER (Within 5-15 seconds)
```
🚨 CRITICAL EVENT DETECTED! (Confidence: 95%)

Your request: alert me when person leaves camera frame

EVENT DETECTED: Person who was in baseline has LEFT

📸 BASELINE: Person seated in chair, visible...
📸 CURRENT: Empty room with chair, no person detected

🧠 AI REASONING (Claude): Person was consistently 
present in baseline frames. Current frame shows empty 
room. This matches user query about person leaving.

✅ Match confidence: 95% 🔥 VERY HIGH
```

---

## 📊 MONITOR THE LOGS (Open Second Terminal)

```bash
tail -f /tmp/sentintinel_backend.log | grep -E "BASELINE|EMERGENCY|CLAUDE|query_confidence|FORCE"
```

### ✅ What You Should See:

```
[ANALYSIS] Camera 0 - Analyzing for baseline...
[VISION] Scene: Person seated in chair
[BASELINE ESTABLISHED] State: Person seated in chair, visible...
[ANALYSIS] Camera 0 - Monitoring for changes...
[VISION] Query Match: False | Confidence: 15%
[CLAUDE] Event: False | Confidence: 20%
...
(you leave)
...
[ANALYSIS] Camera 0 - Scene: Empty room, chair visible
[PRESENCE CHECK] Baseline had person: True | Current: False
🚨 EMERGENCY DETECTION: Person was present but is now ABSENT!
[FORCE ALERT] Confidence boosted from 45% to 95%
[CLAUDE] Event: True | Confidence: 95%
🧠 CLAUDE OVERRIDE: Claude detected event
🚨 EMERGENCY ALERT TRIGGERED: Activity detected with 95%
```

---

## ❌ Common Mistakes

### Mistake 1: Not Waiting for Baseline
```
User enters command → Immediately leaves frame
❌ NO BASELINE = NO ALERT
```

**Fix:** Wait for "✓ Baseline established" message!

### Mistake 2: Moving While Establishing Baseline
```
User sits but keeps moving/shifting
❌ Baseline keeps changing = Never established
```

**Fix:** Stay completely still for 20 seconds!

### Mistake 3: Partially Out of Frame
```
User walks away but arm/shoulder still visible
❌ Person still detected = No "leaving" event
```

**Fix:** Walk completely out of view!

### Mistake 4: Testing Before Baseline
The 50% message you got earlier was because:
- Command was entered
- No baseline established
- Person left
- System saw "empty room" but didn't know it was a change
- Result: 50% confidence, no alert

**Fix:** Follow steps 1-8 in order!

---

## 🧠 How The Dual-AI System Works

### Phase 1: Baseline (First 15-20 seconds)
```
GEMINI: "I see a person seated"
CLAUDE: "Noting this as baseline state"
SYSTEM: "Baseline established ✓"
```

### Phase 2: Monitoring (While you sit)
```
Every 5 seconds:
GEMINI: "Person still there" (20% change)
CLAUDE: "No event yet" (25% confidence)
SYSTEM: No alert (below 40% threshold)
```

### Phase 3: Event Detection (When you leave)
```
GEMINI: "Empty room, no person" (45% confidence)
EMERGENCY CHECK: "Person was in baseline, now absent!"
EMERGENCY OVERRIDE: Force confidence to 95%
CLAUDE: "Confirms person left" (95% confidence)
SYSTEM: 🚨 IMMEDIATE CRITICAL ALERT!
```

---

## 🎮 Try Now!

**Go to http://localhost:3000 and follow Steps 1-8**

**Expected timeline:**
- 0:00 - Enter command
- 0:02 - Camera starts
- 0:05 - First analysis
- 0:10 - Second analysis
- 0:15 - Baseline established ✓
- 0:20 - You leave
- 0:25 - 🚨 ALERT TRIGGERED ✓

**Total time: ~25-30 seconds from start to alert**

---

## 🐛 Still Not Working?

Run these checks in a new terminal:

### Check 1: Is backend running?
```bash
curl http://localhost:8000/health
```
**Expected:** `{"status":"healthy"}`

### Check 2: Is Claude initialized?
```bash
grep "Reasoning Agent" /tmp/sentintinel_backend.log
```
**Expected:** `✅ Reasoning Agent (Claude) initialized`

### Check 3: Is camera working?
```bash
tail -20 /tmp/sentintinel_backend.log | grep "Camera"
```
**Expected:** `[CAMERA] Camera 0 started successfully`

### Check 4: Check for errors
```bash
tail -50 /tmp/sentintinel_backend.log | grep -E "ERROR|Exception|Traceback"
```
**Expected:** No errors

---

## 📝 What to Report

If it still doesn't work, send me:

1. **The exact command you entered**
2. **How long you waited before leaving**
3. **Did you see "Baseline established"? (Yes/No)**
4. **What confidence % was shown? (if any)**
5. **Copy/paste from logs:**
```bash
tail -100 /tmp/sentintinel_backend.log | grep -E "BASELINE|EMERGENCY|CLAUDE"
```

---

## ✅ SUCCESS CRITERIA

You'll know it works when you see:

1. ✓ "Baseline established" message
2. ✓ 95% confidence alert
3. ✓ "CRITICAL EVENT DETECTED"
4. ✓ Claude reasoning explanation
5. ✓ Before/after images
6. ✓ "Emergency Override" in logs

---

**🚀 GO TEST NOW!**

**http://localhost:3000**

**Remember: Wait for baseline before leaving!** ⏱️

