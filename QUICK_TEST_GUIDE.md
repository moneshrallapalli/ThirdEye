# Quick Test Guide - User Query System

## ✅ All Fixed! Here's What Changed

### The Problem (BEFORE)
- ❌ System sent alerts for general activity
- ❌ Didn't understand plain English queries
- ❌ You got notified about everything, not what you asked for

### The Solution (NOW)
- ✅ Understands plain English: "alert me if you see scissors"
- ✅ Searches ONLY for what you asked
- ✅ Alerts ONLY when YOUR specific query matches (≥60%)
- ✅ 2-minute summaries still work for background

## 🚀 How to Test It Now

### Step 1: Restart Backend
```bash
cd /Users/monesh/University/practice
./restart.sh

# OR manually:
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Open Frontend
```
http://localhost:3000
```

### Step 3: Test a Query
In the command box, type:
```
alert me if you see scissors
```

### Step 4: Watch What Happens
**System responds:**
```
✓ Command Processed
Task: object_detection
Target: scissors
Confirmation: "I will continuously monitor all cameras 
and alert you immediately when scissors are detected"
```

**Camera starts analyzing:**
```
[Logs show]
[USER QUERY ACTIVE] Looking for: scissors
[QUERY MATCH] Query: 'scissors' | Match: false | Confidence: 0%
[QUERY MATCH] Query: 'scissors' | Match: false | Confidence: 0%
```

**When scissors appear:**
```
[QUERY MATCH] Query: 'scissors' | Match: true | Confidence: 85%
🚨 IMMEDIATE ALERT: Reasons=['user_query_matched_85%']
```

**You get alert:**
```
🎯 YOUR SEARCH FOUND! (Confidence: 85%)

You were looking for: scissors

What we found: Sharp metal scissors visible on desk

[Image attached]
```

## 🎯 Example Commands to Try

```
"alert me if you see scissors"
"watch for my phone"
"look for a person"
"detect a laptop"
"find my nail cutter"
"watch for someone entering"
```

## 📊 What You'll See

### 1. Scene Narration (Continuous)
- Updates every 5 seconds
- Shows what's in frame
- No alerts (just info)

### 2. Immediate Alerts (When YOUR query matches)
- **Title:** "✓ Scissors Detected"
- **Confidence:** 85%
- **Image:** Attached
- **Only sent when:** Your object found ≥60%

### 3. 2-Minute Summaries (Background)
- Every 2 minutes
- General activity summary
- Low priority

## ✅ Success Indicators

You'll know it's working when:

1. ✅ Type command → System confirms understanding
2. ✅ Logs show: `[USER QUERY ACTIVE] Looking for: [object]`
3. ✅ Live feed updates (but NO alerts for other objects)
4. ✅ Alert ONLY when your object detected ≥60%
5. ✅ Alert title shows what you searched for
6. ✅ Image attached to alert

## ❌ What WON'T Happen Anymore

1. ❌ No alerts for random objects when you're searching for something specific
2. ❌ No "phone detected" alert when you asked for scissors
3. ❌ No general activity alerts (unless dangerous keywords)
4. ❌ No confusion about why you got an alert

## 🔍 Check Logs to See It Working

```bash
cd /Users/monesh/University/practice/backend
tail -f logs/*.log
```

**Look for:**
```
[USER QUERY ACTIVE] Looking for: scissors
[ANALYSIS] Camera 0 - Scene: A desk with...
[QUERY MATCH] Query: 'scissors' | Match: false | Confidence: 5%
[QUERY MATCH] Query: 'scissors' | Match: false | Confidence: 10%
[QUERY MATCH] Query: 'scissors' | Match: TRUE | Confidence: 85%
🚨 IMMEDIATE ALERT: Reasons=['user_query_matched_85%']
🚨 IMMEDIATE ALERT SENT: ✓ Scissors Detected - Confidence: 85%
```

## 🎮 Interactive Test

1. **Start system** → `./restart.sh`
2. **Open frontend** → http://localhost:3000
3. **Type command** → "alert me if you see a phone"
4. **Hold up phone** → to camera
5. **Wait 5-10 seconds** → System analyzing
6. **Get alert** → "✓ Phone Detected - 90% confidence"
7. **Review image** → See your phone in the frame

## 🐛 If Something's Wrong

### No alerts at all?
- Check confidence ≥60%
- Object must be clearly visible
- Check logs for `query_confidence` value

### Still getting general alerts?
- Dangerous keywords always trigger (safety)
- Make sure you entered a command
- Check for 2-minute summaries (background)

### System doesn't understand?
- Be specific: "look for scissors" ✓
- Not vague: "find that thing" ✗
- Check confirmation message

## 📝 Summary of Files Changed

1. **`backend/agents/vision_agent.py`**
   - Added `user_query` parameter
   - Returns `query_match`, `query_confidence`, `query_details`
   - Focuses detection on user's specific query

2. **`backend/main.py`**
   - Extracts user query from active tasks
   - Passes query to vision agent
   - Alerts ONLY when query matches ≥60%
   - 2-minute summaries unchanged

3. **`backend/config.py`**
   - Added `IMMEDIATE_ALERT_THRESHOLD = 60`

## 🎉 You're Ready!

The system now:
- ✅ Understands plain English
- ✅ Searches for what YOU ask for
- ✅ Alerts ONLY when YOUR query matches
- ✅ Shows confidence scores
- ✅ Keeps 2-minute summaries working

**Restart the backend and try it!** 🚀

---

**Questions?** Check the detailed guide: `USER_QUERY_SYSTEM_FIXED.md`

