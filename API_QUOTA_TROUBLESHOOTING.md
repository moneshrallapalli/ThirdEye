# 🔑 API Quota & Key Troubleshooting Guide

## ✅ Steps to Fix Quota Issues

### **1. Restart Backend After Updating .env**

**CRITICAL:** The backend loads API keys from `.env` at startup. After updating your API keys, you MUST restart the backend!

```bash
# Stop backend
killall python

# Wait a moment
sleep 2

# Start backend (it will reload .env)
cd /Users/monesh/University/practice/backend
source venv/bin/activate
python main.py
```

---

### **2. Verify Your API Key**

Run the API key test script:

```bash
cd /Users/monesh/University/practice/backend
source venv/bin/activate
python test_api_key.py
```

**Expected Output:**
```
✅ API Key is valid!
✅ Successfully connected to Gemini API
```

**If you see errors:**
- "QUOTA_EXCEEDED" → Your API key has reached its limit
- "INVALID_API_KEY" → The key is wrong or expired
- "PERMISSION_DENIED" → API not enabled for your project

---

### **3. Check Your Gemini API Quota**

1. Go to: https://aistudio.google.com/app/apikey
2. Click on your API key
3. Check usage and limits

**Free Tier Limits (as of 2024):**
- **gemini-2.5-flash**: 15 requests per minute (RPM)
- **Daily limit**: Varies by region

**If quota exceeded:**
- Wait for quota to reset (resets every minute)
- Upgrade to paid tier for higher limits
- Use rate limiting in your application

---

### **4. Gemini API Rate Limits**

The system uses **gemini-2.5-flash** model which has these limits:

| Tier | Requests/min | Tokens/min |
|------|--------------|------------|
| Free | 15 RPM | ~1M tokens |
| Paid | Higher | Much higher |

**Current System Usage:**
- Camera FPS: 1 frame/second
- Each frame = 1 API call
- **Rate: ~60 API calls/minute** (continuous monitoring)

⚠️ **This exceeds free tier limits!**

---

### **5. Solutions to Reduce API Usage**

#### **Option A: Reduce Camera FPS**

Edit `backend/config.py`:

```python
# Reduce to 0.2 FPS = 1 frame every 5 seconds = 12 calls/minute
CAMERA_FPS: int = 0.2  # Was 1

# Or even lower:
CAMERA_FPS: int = 0.1  # 1 frame every 10 seconds = 6 calls/minute
```

Then restart backend.

---

#### **Option B: Use Multiple API Keys (Round-Robin)**

Create multiple free API keys and rotate between them.

Edit `backend/.env`:
```
GEMINI_API_KEY=key1,key2,key3
```

Then update `backend/agents/vision_agent.py` to rotate keys.

---

#### **Option C: Add Rate Limiting**

Add delay between API calls in `backend/main.py`:

```python
# In surveillance_worker()
# Add after each API call:
await asyncio.sleep(4)  # Wait 4 seconds between calls = 15 calls/min
```

---

#### **Option D: Upgrade to Paid Tier**

Get much higher limits:
- Go to https://console.cloud.google.com/
- Enable billing for your project
- Get ~60 RPM or higher

---

### **6. Check .env File Format**

Make sure your `.env` file has the correct format:

```bash
# backend/.env
GEMINI_API_KEY=AIzaSy...your_actual_key_here

# NO quotes around the value
# NO spaces around the equals sign
# NO extra lines or comments after the key
```

**Common Mistakes:**
```bash
# ❌ WRONG - Has quotes
GEMINI_API_KEY="AIzaSy..."

# ❌ WRONG - Has spaces
GEMINI_API_KEY = AIzaSy...

# ❌ WRONG - Placeholder still there
GEMINI_API_KEY=your_api_key_here

# ✅ CORRECT
GEMINI_API_KEY=AIzaSyAbCdEf1234567890
```

---

### **7. Verify .env is Loaded**

Check if the backend is reading your .env file:

```bash
cd /Users/monesh/University/practice/backend
source venv/bin/activate
python -c "from config import settings; print('API Key loaded:', settings.GEMINI_API_KEY[:20] + '...')"
```

This should print the first 20 characters of your API key.

---

### **8. Monitor API Usage**

Add logging to see when API calls are made:

Check backend logs:
```bash
tail -f /tmp/backend_new_key.log | grep -i "gemini\|api\|quota"
```

---

### **9. Temporary Workaround**

If you need the system working NOW while you fix quota issues:

1. **Reduce FPS drastically:**
   ```python
   # backend/config.py
   CAMERA_FPS: int = 0.1  # 1 frame every 10 seconds
   ```

2. **Only analyze on command:**
   Comment out auto-monitoring in `backend/main.py` and only analyze when user sends a command.

---

### **10. Error Messages & Solutions**

#### **"RESOURCE_EXHAUSTED" or "429"**
- **Cause:** Too many requests
- **Fix:** Reduce FPS or wait for quota reset

#### **"QUOTA_EXCEEDED"**
- **Cause:** Daily/monthly limit reached
- **Fix:** Wait until tomorrow or upgrade to paid

#### **"INVALID_ARGUMENT"**
- **Cause:** Bad request format
- **Fix:** Check if image encoding is correct

#### **"UNAUTHENTICATED" or "401"**
- **Cause:** Invalid API key
- **Fix:** Double-check your API key is correct

---

## 🎯 Recommended Configuration for Free Tier

To stay within free tier limits (15 RPM):

```python
# backend/config.py

# Option 1: Very low FPS (safest)
CAMERA_FPS: int = 0.1  # 6 calls/minute ✅

# Option 2: Low FPS (reasonable)
CAMERA_FPS: int = 0.2  # 12 calls/minute ✅

# Option 3: Current (EXCEEDS free tier)
CAMERA_FPS: int = 1  # 60 calls/minute ❌
```

**Restart backend after changing:**
```bash
killall python
cd /Users/monesh/University/practice/backend
source venv/bin/activate
python main.py
```

---

## 🔍 Quick Diagnostic

Run this to check everything:

```bash
cd /Users/monesh/University/practice/backend

echo "1. Checking .env file exists..."
test -f .env && echo "✅ .env found" || echo "❌ .env missing"

echo ""
echo "2. Testing API key..."
source venv/bin/activate
python test_api_key.py

echo ""
echo "3. Checking backend status..."
curl -s http://localhost:8000/ > /dev/null && echo "✅ Backend running" || echo "❌ Backend not running"

echo ""
echo "4. Checking recent errors..."
tail -20 /tmp/backend_new_key.log | grep -i "error\|quota"
```

---

## 📊 Current System Settings

**Location:** `backend/config.py`

```python
CAMERA_FPS: int = 1          # ← This is the key setting
VIDEO_RESOLUTION_WIDTH: int = 640
VIDEO_RESOLUTION_HEIGHT: int = 480
```

**API calls per minute:** `CAMERA_FPS * 60`
- If FPS = 1 → 60 calls/min ❌ (exceeds free tier)
- If FPS = 0.2 → 12 calls/min ✅ (within free tier)
- If FPS = 0.1 → 6 calls/min ✅ (safe)

---

## ✅ Checklist

- [ ] Updated API key in `backend/.env`
- [ ] Restarted backend (`killall python && python main.py`)
- [ ] Tested API key (`python test_api_key.py`)
- [ ] Checked API quota on Google AI Studio
- [ ] Reduced FPS if on free tier
- [ ] Verified backend is running (`curl http://localhost:8000`)
- [ ] No quota errors in logs

---

## 🆘 Still Having Issues?

1. **Check exact error message:**
   ```bash
   tail -50 /tmp/backend_new_key.log | grep -i "error" -A 5
   ```

2. **Verify API key manually:**
   ```bash
   curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"
   ```

3. **Get new API key:**
   - Go to https://aistudio.google.com/app/apikey
   - Revoke old key
   - Create new key
   - Update `.env`
   - Restart backend

---

## 📝 Summary

**Most Common Issue:** Not restarting backend after updating `.env`

**Quick Fix:**
```bash
# 1. Stop backend
killall python

# 2. Start backend (reloads .env)
cd /Users/monesh/University/practice/backend
source venv/bin/activate  
python main.py

# 3. Backend now uses new API key! ✅
```

**If quota exceeded:** Reduce FPS to 0.2 or lower in `config.py`



