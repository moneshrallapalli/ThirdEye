# 🚀 SentinTinel Scripts Usage Guide

## 📋 Available Scripts

You now have 4 powerful scripts to manage your surveillance system:

| Script | Purpose | Usage |
|--------|---------|-------|
| `start.sh` | Start the entire system | `./start.sh` |
| `stop.sh` | Stop all services | `./stop.sh` |
| `restart.sh` | Restart everything | `./restart.sh` |
| `status.sh` | Check system status | `./status.sh` |

---

## 🎯 Quick Start

```bash
# Start the system
./start.sh

# Check if it's running
./status.sh

# Stop when done
./stop.sh
```

---

## 📖 Detailed Usage

### 1. `start.sh` - Start System

**What it does:**
- ✅ Checks if ports 3000 and 8000 are available
- ✅ Verifies Python, Node.js, and npm are installed
- ✅ Checks for `.env` file and API keys
- ✅ Creates Python virtual environment if needed
- ✅ Installs dependencies (first time only)
- ✅ Starts backend (FastAPI)
- ✅ Starts frontend (React)
- ✅ Verifies services are running
- ✅ Opens browser automatically

**Usage:**
```bash
cd /Users/monesh/University/practice
./start.sh
```

**First Time Setup:**
If `.env` doesn't exist, it will create one from `.env.example` and prompt you to add API keys.

**If Ports Busy:**
The script will ask if you want to stop existing processes and restart.

**Expected Output:**
```
╔═══════════════════════════════════════════════════════════════╗
║        🚀 SENTINTINEL SURVEILLANCE SYSTEM STARTUP            ║
╚═══════════════════════════════════════════════════════════════╝

✅ Python found
✅ Node.js found (v18.x.x)
✅ npm found (v9.x.x)
✅ All directories found
✅ .env file found
✅ API key configured
...
╔═══════════════════════════════════════════════════════════════╗
║              ✅ SYSTEM STARTED SUCCESSFULLY                   ║
╚═══════════════════════════════════════════════════════════════╝

🌐 Access Points:
   Frontend:  http://localhost:3000
   Backend:   http://localhost:8000
   API Docs:  http://localhost:8000/docs
```

---

### 2. `stop.sh` - Stop System

**What it does:**
- 🛑 Stops backend (Python/FastAPI)
- 🛑 Stops frontend (React/Node)
- 🛑 Kills processes by PID, name, and port
- 🛑 Cleans up PID files
- 🛑 Verifies all ports are free
- 🛑 Optionally deletes log files

**Usage:**
```bash
./stop.sh
```

**Stop Methods:**
The script uses 3 methods to ensure everything stops:
1. **PID File:** Reads saved process IDs
2. **Process Name:** Kills by process name (python, react-scripts)
3. **Port:** Kills anything on ports 3000 and 8000

**Expected Output:**
```
╔═══════════════════════════════════════════════════════════════╗
║         🛑 SENTINTINEL SURVEILLANCE SYSTEM SHUTDOWN          ║
╚═══════════════════════════════════════════════════════════════╝

✅ Backend stopped (PID: 12345)
✅ Frontend stopped (PID: 67890)
✅ Cleanup complete
✅ Port 8000 is free
✅ Port 3000 is free

╔═══════════════════════════════════════════════════════════════╗
║              ✅ SYSTEM STOPPED SUCCESSFULLY                   ║
╚═══════════════════════════════════════════════════════════════╝
```

---

### 3. `restart.sh` - Restart System

**What it does:**
- 🔄 Runs `stop.sh` to stop everything
- ⏳ Waits 3 seconds
- 🚀 Runs `start.sh` to start fresh

**Usage:**
```bash
./restart.sh
```

**When to use:**
- After updating code
- After changing `.env` configuration
- When system becomes unresponsive
- After installing new dependencies

**Expected Output:**
```
╔═══════════════════════════════════════════════════════════════╗
║         🔄 SENTINTINEL SURVEILLANCE SYSTEM RESTART           ║
╚═══════════════════════════════════════════════════════════════╝

[Stop output...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Waiting 3 seconds...
[Start output...]

✅ Restart complete!
```

---

### 4. `status.sh` - Check Status

**What it does:**
- 📊 Shows if backend is running (port 8000)
- 📊 Shows if frontend is running (port 3000)
- 📊 Displays process IDs and resource usage
- 📊 Shows log file sizes
- 📊 Displays recent errors
- 📊 Provides overall system health

**Usage:**
```bash
./status.sh
```

**Example Output:**
```
╔═══════════════════════════════════════════════════════════════╗
║         📊 SENTINTINEL SURVEILLANCE SYSTEM STATUS            ║
╚═══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 BACKEND (Port 8000)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Backend is RUNNING
   PID: 12345
✅ Backend responding to requests
   URL: http://localhost:8000
   
   Process details:
   12345  1234  2.3  1.5  05:23  python main.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 FRONTEND (Port 3000)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Frontend is RUNNING
   PID: 67890
✅ Frontend responding to requests
   URL: http://localhost:3000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ System is FULLY OPERATIONAL

   🌐 Access: http://localhost:3000
   📚 API Docs: http://localhost:8000/docs
```

---

## 🔧 Edge Cases Handled

### 1. **Ports Already in Use**
```bash
./start.sh
# Script detects port 8000 is busy
# Asks: "Stop and restart? (y/n)"
# If yes: Stops old process and starts new one
# If no: Exits safely
```

### 2. **Missing Dependencies**
```bash
./start.sh
# Detects missing Python packages
# Automatically runs: pip install -r requirements.txt
# Marks as installed to skip next time
```

### 3. **Missing .env File**
```bash
./start.sh
# Detects .env missing
# Copies from .env.example
# Tells you to add API keys
# Exits safely with instructions
```

### 4. **API Key Not Configured**
```bash
./start.sh
# Detects placeholder API key
# Shows error with link to get key
# Exits safely
```

### 5. **Zombie Processes**
```bash
./stop.sh
# Tries graceful shutdown (kill)
# If process still running: Force kill (kill -9)
# Cleans up all orphaned processes
# Verifies ports are truly free
```

### 6. **Services Fail to Start**
```bash
./start.sh
# Waits up to 30 seconds for each service
# If timeout: Shows error
# Points to log file for debugging
# Exits with error code
```

### 7. **System Not Running**
```bash
./stop.sh
# Detects nothing is running
# Shows: "No services were running"
# Exits successfully (not an error)
```

### 8. **Partial Failure**
```bash
./status.sh
# Backend running but frontend down
# Shows: "System is PARTIALLY RUNNING"
# Tells you which service failed
# Suggests: ./restart.sh
```

---

## 📝 Log Files

### Location:
- Backend: `/tmp/sentintinel_backend.log`
- Frontend: `/tmp/sentintinel_frontend.log`

### View Logs:
```bash
# Backend logs
tail -f /tmp/sentintinel_backend.log

# Frontend logs
tail -f /tmp/sentintinel_frontend.log

# Last 50 lines
tail -50 /tmp/sentintinel_backend.log

# Search for errors
grep -i "error" /tmp/sentintinel_backend.log

# Clear logs
rm /tmp/sentintinel_*.log
```

---

## 🚨 Troubleshooting

### Problem: Script won't run
```bash
# Make sure it's executable
chmod +x start.sh stop.sh restart.sh status.sh
```

### Problem: "Command not found"
```bash
# Make sure you're in the right directory
cd /Users/monesh/University/practice

# Then run
./start.sh
```

### Problem: Backend fails to start
```bash
# Check the log
tail -50 /tmp/sentintinel_backend.log

# Common issues:
# 1. API key not configured → Edit backend/.env
# 2. Port 8000 busy → Run ./stop.sh first
# 3. Python packages missing → Delete venv/ and run ./start.sh
```

### Problem: Frontend fails to start
```bash
# Check the log
tail -50 /tmp/sentintinel_frontend.log

# Common issues:
# 1. Port 3000 busy → Run ./stop.sh first
# 2. node_modules corrupt → Delete frontend/node_modules and run ./start.sh
# 3. npm version issues → Update Node.js
```

### Problem: "Python not found"
```bash
# Install Python 3
# macOS: brew install python3
# Or download from: https://www.python.org/downloads/
```

### Problem: "Node not found"
```bash
# Install Node.js
# macOS: brew install node
# Or download from: https://nodejs.org/
```

### Problem: Can't stop services
```bash
# Nuclear option - force kill everything
killall python
killall node
lsof -ti :8000 | xargs kill -9
lsof -ti :3000 | xargs kill -9
```

---

## 📊 Complete Workflow Examples

### Daily Use:
```bash
# Morning - Start system
./start.sh

# Check it's working
./status.sh

# Evening - Stop system
./stop.sh
```

### Development:
```bash
# Start system
./start.sh

# Make code changes...

# Restart to see changes
./restart.sh

# Check for errors
./status.sh
tail -f /tmp/sentintinel_backend.log
```

### After Updating API Key:
```bash
# 1. Stop system
./stop.sh

# 2. Edit .env file
nano backend/.env
# Update GEMINI_API_KEY=your_new_key

# 3. Start with new key
./start.sh
```

### Debugging Issues:
```bash
# 1. Check what's running
./status.sh

# 2. Stop everything
./stop.sh

# 3. Check logs
tail -100 /tmp/sentintinel_backend.log | grep -i error

# 4. Start fresh
./start.sh

# 5. Watch logs in real-time
tail -f /tmp/sentintinel_backend.log
```

---

## 🎯 Best Practices

1. **Always use `./stop.sh` before shutting down your computer**
   - Prevents orphaned processes
   - Ensures clean shutdown

2. **Run `./status.sh` if something seems wrong**
   - Quick health check
   - See resource usage
   - Find errors quickly

3. **Use `./restart.sh` after code or config changes**
   - Ensures new settings are loaded
   - Cleaner than manual stop/start

4. **Check logs when debugging**
   - Logs show detailed error messages
   - Help identify root cause

5. **Keep log files small**
   - Delete old logs periodically
   - `./stop.sh` offers to delete logs

---

## 📞 Quick Reference

```bash
# Basic operations
./start.sh    # Start everything
./stop.sh     # Stop everything
./restart.sh  # Restart everything
./status.sh   # Check status

# View logs
tail -f /tmp/sentintinel_backend.log   # Backend logs
tail -f /tmp/sentintinel_frontend.log  # Frontend logs

# Force stop (if normal stop fails)
./stop.sh
killall python
killall node

# Check what's using ports
lsof -ti :8000  # Backend port
lsof -ti :3000  # Frontend port

# Manual start (if script fails)
cd backend && source venv/bin/activate && python main.py
cd frontend && npm start
```

---

## ✅ Summary

You now have **production-ready scripts** that handle:
- ✅ All edge cases (missing files, busy ports, etc.)
- ✅ Automatic dependency management
- ✅ Health checks and verification
- ✅ Detailed logging
- ✅ Graceful shutdown
- ✅ Process cleanup
- ✅ Status monitoring

**Just run:** `./start.sh` to begin! 🚀



