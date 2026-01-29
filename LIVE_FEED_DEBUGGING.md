# 🎥 LIVE FEED TROUBLESHOOTING GUIDE

## ✅ WHAT I FIXED

### Frontend Improvements:
1. ✅ Added console logging for WebSocket messages
2. ✅ Better "waiting" messages when camera is active
3. ✅ Visual "● LIVE" indicator when feed is working
4. ✅ Error handling for image loading

### Issue to Monitor:
⚠️ **Gemini API Quota** - If you're hitting the quota, live feed might stop

---

## 🔍 HOW TO DEBUG LIVE FEED ISSUES

### Step 1: Open Browser Console
```
1. Open: http://localhost:3000
2. Press: F12 (or Cmd+Option+I on Mac)
3. Click: "Console" tab
```

### Step 2: Start Camera
```
1. Click "Start Camera 0"
2. Watch console for messages
```

### Step 3: Check Console Messages
Look for these logs:

✅ **WORKING:**
```
Live feed update received: {
  camera_id: 0,
  timestamp: "2025-11-19T...",
  hasFrame: true,
  frameLength: 50000
}
Updated liveFeedData for camera: 0
```

❌ **NOT WORKING:**
```
- No messages appearing
- hasFrame: false
- WebSocket not connected
```

---

## 🐛 COMMON ISSUES & FIXES

### Issue 1: "Waiting for video feed..." Stuck

**Symptoms:**
- Camera shows as active (green indicator)
- But no video appears
- Just shows "Waiting for video feed..."

**Causes:**
1. WebSocket not connected
2. Backend not sending frames
3. Gemini API quota exceeded

**Debug:**
```bash
# Terminal 1: Check backend logs
tail -f /tmp/sentintinel_backend.log | grep -E "LIVE FEED|WebSocket|429"

# Look for:
✅ "[LIVE FEED] Sent frame for camera 0"
✅ "WebSocket connected"
❌ "ERROR 429" (quota exceeded)
❌ "WebSocket error"
```

**Fix:**
```
If you see "ERROR 429":
→ You've hit Gemini API quota
→ Solution: Get new API key or wait for reset
→ See: GEMINI_QUOTA_EXCEEDED.md

If no WebSocket messages:
→ Refresh browser (F5)
→ Check browser console for errors
```

---

### Issue 2: Gemini API Quota Exceeded

**Symptoms:**
```
ERROR 429: You exceeded your current quota
```

**This prevents:**
- Analysis from working
- Live feed from being sent (in old code)

**Fix:**
See earlier sections about getting a new Gemini API key or:
```bash
# Reduce frame rate even more
cd /Users/monesh/University/practice/backend
nano config.py

# Change line 45:
CAMERA_FPS: float = 0.017  # 1 frame every 60 seconds

# Restart:
cd ..
./restart.sh
```

---

### Issue 3: WebSocket Disconnected

**Symptoms:**
- Browser console shows WebSocket errors
- Live feed stops working

**Fix:**
```
1. Refresh browser (F5)
2. Check if backend is running:
   curl http://localhost:8000/health

3. Restart if needed:
   cd /Users/monesh/University/practice
   ./restart.sh
```

---

### Issue 4: Camera State Shows Active But Isn't

**Symptoms:**
- API thinks camera is running
- But no frames being captured

**Fix:**
```bash
# Stop and restart camera
1. Click "Stop Camera 0" in UI
2. Wait 2 seconds
3. Click "Start Camera 0"

# Or restart backend:
cd /Users/monesh/University/practice
./restart.sh
```

---

## 📊 MONITORING LIVE FEED

### Terminal Commands:

**Check if frames are being sent:**
```bash
tail -f /tmp/sentintinel_backend.log | grep "LIVE FEED"
```

**Check WebSocket connections:**
```bash
tail -f /tmp/sentintinel_backend.log | grep "WebSocket"
```

**Check for errors:**
```bash
tail -f /tmp/sentintinel_backend.log | grep "ERROR"
```

**Check API quota issues:**
```bash
tail -f /tmp/sentintinel_backend.log | grep "429"
```

---

## ✅ SUCCESS INDICATORS

### In Browser Console:
```
✅ Live feed update received: {camera_id: 0, hasFrame: true, ...}
✅ Updated liveFeedData for camera: 0
```

### In Backend Logs:
```
✅ [LIVE FEED] Sent frame for camera 0
✅ [ANALYSIS] Camera 0 - Scene: (description)
✅ WebSocket connected to /ws/live-feed
```

### In UI:
```
✅ "● LIVE" indicator in top-right of video
✅ Timestamp updating at bottom-left
✅ Video feed refreshing every 30 seconds
```

---

## 🎯 COMPLETE TEST PROCEDURE

### Step 1: Start Fresh
```bash
cd /Users/monesh/University/practice
./restart.sh
```

### Step 2: Open Browser with Console
```
1. Open: http://localhost:3000
2. Press F12
3. Go to Console tab
```

### Step 3: Start Camera
```
1. Go to "Live Cameras" or "Dashboard" tab
2. Click "Start Camera 0"
3. Watch console for messages
```

### Step 4: Verify Feed
Within 30-60 seconds, you should see:
- ✅ Video frame appears
- ✅ "● LIVE" indicator shows
- ✅ Timestamp updates
- ✅ Console logs appear

### Step 5: If Not Working
```
1. Check console for errors
2. Check backend logs:
   tail -50 /tmp/sentintinel_backend.log

3. Look for:
   - "ERROR 429" → Quota issue
   - "WebSocket" errors → Connection issue
   - No "LIVE FEED" messages → Backend not sending

4. Apply appropriate fix from above
```

---

## 🔧 EMERGENCY FIX

If nothing else works:

```bash
# 1. Complete restart
cd /Users/monesh/University/practice
./stop.sh
sleep 5
./start.sh

# 2. Wait for startup (30 seconds)

# 3. Open fresh browser window
# (Private/Incognito mode)
http://localhost:3000

# 4. Try camera again
```

---

## 📝 WHAT TO REPORT

If still not working, provide:

1. **Browser console output:**
```
(Copy/paste from console after clicking Start Camera)
```

2. **Backend logs:**
```bash
tail -100 /tmp/sentintinel_backend.log
```

3. **What you see:**
- Camera state (active/inactive)?
- Any message displayed?
- Any errors in console?

---

## ✅ CURRENT STATUS

**System Status:**
```
Backend: Running (PID: 58349)
Frontend: Running (PID: 58382)
```

**Improvements Made:**
- ✅ Added console logging
- ✅ Better error messages
- ✅ Visual indicators
- ✅ Image error handling

**Next Steps:**
1. Open browser with console (F12)
2. Start camera
3. Watch console for "Live feed update received"
4. If you see it, feed is working!
5. If not, follow debug steps above

---

**GO TEST NOW AND CHECK YOUR BROWSER CONSOLE!** 🚀

The logging will tell us exactly what's happening!

