# ⚠️ GEMINI API QUOTA EXCEEDED

## 🔴 Current Error

```
ERROR: 429 You exceeded your current quota
Quota exceeded for: generate_content_free_tier_requests
Limit: 250 requests per day
Model: gemini-2.5-flash
```

**Your Gemini API free tier quota has been exhausted for today.**

---

## 📊 What Happened

### Gemini Free Tier Limits:
- **250 requests per day** per model
- **2 requests per minute** (RPM)

### Your Usage:
- Camera analyzes every 5 seconds
- That's 12 requests per minute
- 720 requests per hour
- **You hit the 250 limit very quickly!**

---

## ✅ SOLUTIONS

### Solution 1: Wait for Quota Reset (FREE)
**Wait until tomorrow** - your quota resets daily at midnight Pacific Time.

**When does it reset?**
```bash
# Check current time
date

# Quota resets at midnight PT (UTC-8)
# If it's 2:00 AM on Nov 19, reset is ~22 hours away
```

---

### Solution 2: Get New API Key (FREE)

Google allows multiple projects with separate quotas!

#### Step 1: Create New Project
1. Go to: https://aistudio.google.com/app/apikey
2. Click **"Get API Key"**
3. Click **"Create API Key in new project"**
4. Copy the new key

#### Step 2: Update Your System
```bash
cd /Users/monesh/University/practice/backend

# Edit .env file
nano .env

# Replace the GEMINI_API_KEY line with your NEW key:
# GEMINI_API_KEY=YOUR_NEW_KEY_HERE

# Save and exit (Ctrl+X, Y, Enter)
```

#### Step 3: Restart
```bash
cd /Users/monesh/University/practice
./restart.sh
```

---

### Solution 3: Reduce Usage (FREE)

Modify the system to use fewer API calls:

#### Current Settings:
```
Camera FPS: 0.2 (1 frame every 5 seconds)
= 12 calls/minute
= 720 calls/hour
```

#### New Settings (Lower Usage):
```bash
cd /Users/monesh/University/practice/backend

# Edit config.py
nano config.py

# Change line 45 from:
CAMERA_FPS: int = 0.2

# To (1 frame every 15 seconds):
CAMERA_FPS: int = 0.067

# This gives you:
# 4 calls/minute
# 240 calls/hour
# Under 250/day limit ✓
```

**Save, then restart:**
```bash
cd /Users/monesh/University/practice
./restart.sh
```

---

### Solution 4: Upgrade to Paid (PAID)

Get much higher limits:

#### Gemini API Pro:
- **1,000 requests per minute** (vs 2)
- **10,000 requests per day** (vs 250)
- Still very cheap (~$0.001 per request)

#### How to Upgrade:
1. Go to: https://console.cloud.google.com/
2. Select your project
3. Enable billing
4. Go to: https://console.cloud.google.com/billing
5. Set up payment method

**Your existing API key will automatically get the higher limits once billing is enabled.**

---

## 🎯 RECOMMENDED: Solution 2 (New API Key)

**This is the fastest and FREE solution:**

1. **Create new project & API key**: https://aistudio.google.com/app/apikey
2. **Update `.env` file** with new key
3. **Restart system**
4. **Test again**

### Quick Commands:
```bash
# 1. Edit .env
cd /Users/monesh/University/practice/backend
nano .env
# (Replace GEMINI_API_KEY value)

# 2. Restart
cd /Users/monesh/University/practice
./restart.sh

# 3. Test
# Open http://localhost:3000
# Start camera - should work!
```

---

## 📊 Check Your Current Quota

Visit: https://ai.google.dev/gemini-api/docs/rate-limits

Or check usage:
https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

---

## 🚨 Why This Happened

### Your Testing Pattern:
```
Camera running continuously
→ 1 request every 5 seconds
→ 12 requests per minute
→ You hit 250 limit in ~20 minutes!
```

### Free Tier is NOT for continuous monitoring:
- Free tier: 250/day = Good for **testing/demos**
- Continuous monitoring needs: Paid tier or multiple keys

---

## 🔧 After You Fix It

### To Prevent This:
1. **Don't run camera continuously** during testing
2. **Start camera only when needed** (it auto-starts with commands)
3. **Stop camera when done** (click "Stop Camera" button)
4. **Use multiple API keys** for different projects
5. **Upgrade to paid tier** for production use

---

## ✅ Quick Fix NOW

### Option A: New API Key (5 minutes)
```
1. Go to: https://aistudio.google.com/app/apikey
2. Click "Create API Key in new project"
3. Copy key
4. Update backend/.env
5. ./restart.sh
6. ✅ Works!
```

### Option B: Wait (22 hours)
```
Quota resets at midnight PT
Come back tomorrow
✅ Works!
```

### Option C: Reduce FPS (2 minutes)
```
1. Edit backend/config.py
2. Change CAMERA_FPS to 0.067
3. ./restart.sh
4. ✅ Works (slower but under limit)
```

---

## 🎮 Test After Fix

Once you've applied a solution:

```bash
# Start system
cd /Users/monesh/University/practice
./restart.sh

# Check logs for success
tail -20 /tmp/sentintinel_backend.log

# Should see:
# ✅ Reasoning Agent (Claude) initialized
# [CAMERA] Camera 0 started successfully
# [ANALYSIS] Camera 0 - Scene: (actual description)

# NOT:
# ❌ ERROR 429 quota exceeded
```

---

## 💡 Understanding API Quotas

### Free Tier (Current):
```
✓ Great for: Testing, demos, learning
✗ NOT for: Continuous monitoring, production
Limit: 250/day
Cost: $0
```

### Paid Tier:
```
✓ Great for: Production, continuous use
✓ High limits: 10,000/day, 1,000/min
Cost: ~$0.001 per request = ~$7.20/day for continuous monitoring
```

---

## 📝 Next Steps

**Choose your solution:**

1. ☑️ **NEW API KEY** (fastest, free) ← Recommended
2. ☑️ **REDUCE FPS** (free, slower)
3. ☑️ **WAIT** (free, slow)
4. ☑️ **UPGRADE** (paid, best for production)

**After fixing, test with:**
```
Command: "alert me when person leaves camera frame"
Wait for: Baseline established
Then: Leave frame
Expect: 🚨 95% alert!
```

---

## 🆘 Need Help?

**If new API key doesn't work:**
```bash
# Check if key is loaded
cd /Users/monesh/University/practice/backend
grep GEMINI_API_KEY .env

# Check logs for new errors
tail -50 /tmp/sentintinel_backend.log | grep ERROR
```

Reply with the error and I'll help!

---

## ✅ Summary

**Problem:** Gemini API free tier limit (250/day) exceeded

**Best Fix:** Create new API key in new project

**Time:** 5 minutes

**Cost:** $0

**Link:** https://aistudio.google.com/app/apikey

**After fix:** Your dual-AI system will work perfectly! 🎯

