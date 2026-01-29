# 🔑 GET NEW GEMINI API KEY (5 Minutes)

## 🎯 Quick Fix For Quota Exceeded Error

Your current Gemini API key has hit the 250 requests/day limit.
**Get a new key in a new project to get another 250 requests!**

---

## 📋 Step-by-Step

### Step 1: Open Google AI Studio (30 seconds)
🔗 **https://aistudio.google.com/app/apikey**

### Step 2: Create New API Key (1 minute)
1. Click the **"Get API Key"** button (top right)
2. Click **"Create API Key in new project"**
   - ⚠️ Important: Choose "**in new project**" not "existing"
   - This gives you a fresh 250/day quota
3. Wait 5 seconds for key to generate
4. Click **"Copy"** to copy the key

Your new key will look like:
```
AIzaSy.................................... (39 characters)
```

### Step 3: Update Your System (2 minutes)

#### Option A: Using Text Editor
```bash
cd /Users/monesh/University/practice/backend
nano .env
```

Find the line:
```
GEMINI_API_KEY=AIzaSy...kkTZM
```

Replace with your NEW key:
```
GEMINI_API_KEY=AIzaSy...YOUR_NEW_KEY
```

Save and exit:
- Press `Ctrl+X`
- Press `Y`
- Press `Enter`

#### Option B: Using Command Line
```bash
cd /Users/monesh/University/practice/backend

# Backup old .env
cp .env .env.backup

# Replace key (paste your NEW key after the =)
sed -i '' 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY=YOUR_NEW_KEY_HERE/' .env
```

### Step 4: Restart System (1 minute)
```bash
cd /Users/monesh/University/practice
./restart.sh
```

Wait for:
```
✅ Backend started
✅ Frontend started
✅ System ready! 🚀
```

### Step 5: Verify It Works (30 seconds)
```bash
# Check logs
tail -20 /tmp/sentintinel_backend.log

# Should see:
✅ Reasoning Agent (Claude) initialized
[CAMERA] Camera 0 started successfully
[ANALYSIS] Camera 0 - Scene: (actual description)

# Should NOT see:
❌ ERROR 429 quota exceeded
```

---

## ✅ Quick Test

1. Open: **http://localhost:3000**
2. Click **"Start Camera 0"**
3. Wait 5 seconds
4. Check for analysis results (NOT "Analysis failed")

If you see actual scene descriptions = **SUCCESS!** ✅

---

## 🎯 Full Test (After Confirming It Works)

Now test the activity detection:

1. **Enter command:**
   ```
   alert me when person leaves the camera frame
   ```

2. **Sit in front of camera for 20 seconds**
   - Stay still
   - Wait for "Baseline established"

3. **Leave the frame completely**

4. **Watch for alert:**
   ```
   🚨 CRITICAL EVENT DETECTED! (95% confidence)
   Person who was in baseline has LEFT!
   ```

---

## 🔄 If You Still Get Quota Error

### Possibility 1: Old Key Still Cached
```bash
# Force restart
cd /Users/monesh/University/practice
./stop.sh
sleep 5
./start.sh
```

### Possibility 2: Wrong Key Format
```bash
# Check your key
cd /Users/monesh/University/practice/backend
grep GEMINI_API_KEY .env

# Should show:
# GEMINI_API_KEY=AIzaSy... (39 characters)

# Should NOT have:
# - Spaces before/after =
# - Quotes around key
# - Extra characters
```

### Possibility 3: New Project Not Created
- Make sure you clicked **"Create API Key in new project"**
- NOT "Create API Key" (in existing project)
- New project = new quota!

---

## 📊 After You Get It Working

### To Avoid Hitting Limit Again:

1. **Stop camera when not testing**
   - Click "Stop Camera" button in UI
   - Don't leave it running overnight

2. **Test in short bursts**
   - Start camera
   - Test your command
   - Stop camera
   - This uses ~10-20 requests per test

3. **Reduce FPS if needed**
   - Edit `backend/config.py`
   - Change `CAMERA_FPS: int = 0.2` to `0.1`
   - Uses half the requests

4. **Consider upgrading for production**
   - Free tier: 250/day = good for testing
   - Paid tier: 10,000/day = good for real use
   - Enable billing at: https://console.cloud.google.com/billing

---

## 💡 Understanding Quotas

### With New Key:
```
Old key: 250/250 used (0% remaining) ❌
New key: 0/250 used (100% remaining) ✅
```

### Your Usage Pattern:
```
Camera running: 12 requests/minute
In 20 minutes: 240 requests
≈ 96% of daily quota used!
```

### Sustainable Testing:
```
Test 1: Start camera, establish baseline, test leaving (15 requests)
Test 2: Test object detection (10 requests)
Test 3: Test motion detection (10 requests)
Total: 35 requests = 14% of quota ✓
Can do 7 full test sessions per day!
```

---

## 🎮 What To Do NOW

### Immediate Steps:
```
1. ✅ Go to: https://aistudio.google.com/app/apikey
2. ✅ Create API Key in NEW project
3. ✅ Copy the key
4. ✅ Update backend/.env
5. ✅ Run: ./restart.sh
6. ✅ Test: Start Camera 0
7. ✅ Verify: See scene descriptions (not "Analysis failed")
```

### Then Test Your Activity Detection:
```
8. ✅ Enter: "alert me when person leaves camera frame"
9. ✅ Sit still for 20 seconds
10. ✅ Wait for: "Baseline established"
11. ✅ Leave frame
12. ✅ Get: 🚨 95% confidence alert!
```

---

## 🆘 Need Help?

After you update the API key, if you still see errors:

```bash
# Show me these logs:
tail -50 /tmp/sentintinel_backend.log

# And your .env (without showing full key):
grep GEMINI_API_KEY /Users/monesh/University/practice/backend/.env | cut -c 1-30
```

Reply with the output and I'll help debug!

---

## ✅ Summary

**Problem:** Quota exceeded (250 requests used)

**Solution:** New API key in new project

**Time:** 5 minutes

**Steps:**
1. https://aistudio.google.com/app/apikey
2. "Create API Key in new project"
3. Copy key
4. Update backend/.env
5. ./restart.sh

**Result:** Fresh 250 requests quota ✓

**Your dual-AI system will work!** 🎯🚀

