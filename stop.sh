#!/bin/bash

###############################################################################
#                   SENTINTINEL SURVEILLANCE SYSTEM
#                        STOP SCRIPT v2.0
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# PID files
BACKEND_PID_FILE="/tmp/sentintinel_backend.pid"
FRONTEND_PID_FILE="/tmp/sentintinel_frontend.pid"

###############################################################################
# FUNCTIONS
###############################################################################

print_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║         🛑 SENTINTINEL SURVEILLANCE SYSTEM SHUTDOWN          ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

kill_process() {
    local pid=$1
    local name=$2
    
    if ps -p $pid > /dev/null 2>&1; then
        kill $pid 2>/dev/null && print_success "$name stopped (PID: $pid)" || print_warning "$name already stopped"
        sleep 1
        
        # Force kill if still running
        if ps -p $pid > /dev/null 2>&1; then
            kill -9 $pid 2>/dev/null
            print_info "Forced $name to stop"
        fi
    else
        print_info "$name was not running"
    fi
}

kill_by_port() {
    local port=$1
    local name=$2
    
    local pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo $pids | xargs kill -9 2>/dev/null
        print_success "$name on port $port stopped"
    else
        print_info "No process running on port $port"
    fi
}

###############################################################################
# MAIN STOP LOGIC
###############################################################################

print_header

print_step "Stopping SentinTinel Surveillance System..."
echo ""

# Track if anything was stopped
STOPPED_SOMETHING=false

###############################################################################
# STOP BACKEND
###############################################################################

print_step "Stopping backend..."

# Method 1: Stop by PID file
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    kill_process $BACKEND_PID "Backend"
    rm -f "$BACKEND_PID_FILE"
    STOPPED_SOMETHING=true
fi

# Method 2: Kill all Python processes (main.py)
if pgrep -f "python.*main.py" > /dev/null; then
    print_step "Stopping Python processes..."
    pkill -f "python.*main.py" 2>/dev/null && print_success "Python processes stopped" || true
    STOPPED_SOMETHING=true
fi

# Method 3: Kill by port
if lsof -ti :8000 > /dev/null 2>&1; then
    kill_by_port 8000 "Backend"
    STOPPED_SOMETHING=true
fi

# Extra: Kill any remaining Python processes
if pgrep -x python > /dev/null 2>&1; then
    print_warning "Found other Python processes, stopping them..."
    killall python 2>/dev/null || true
fi

print_success "Backend shutdown complete"

###############################################################################
# STOP FRONTEND
###############################################################################

echo ""
print_step "Stopping frontend..."

# Method 1: Stop by PID file
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    kill_process $FRONTEND_PID "Frontend"
    rm -f "$FRONTEND_PID_FILE"
    STOPPED_SOMETHING=true
fi

# Method 2: Kill Node/React processes
if pgrep -f "react-scripts" > /dev/null; then
    print_step "Stopping React processes..."
    pkill -f "react-scripts" 2>/dev/null && print_success "React processes stopped" || true
    STOPPED_SOMETHING=true
fi

if pgrep -f "node.*start" > /dev/null; then
    print_step "Stopping Node processes..."
    pkill -f "node.*start" 2>/dev/null && print_success "Node processes stopped" || true
    STOPPED_SOMETHING=true
fi

# Method 3: Kill by port
if lsof -ti :3000 > /dev/null 2>&1; then
    kill_by_port 3000 "Frontend"
    STOPPED_SOMETHING=true
fi

print_success "Frontend shutdown complete"

###############################################################################
# CLEANUP
###############################################################################

echo ""
print_step "Cleanup..."

# Remove PID files
rm -f "$BACKEND_PID_FILE" 2>/dev/null
rm -f "$FRONTEND_PID_FILE" 2>/dev/null

# Clean up any orphaned processes
if pgrep -f "uvicorn" > /dev/null; then
    pkill -f "uvicorn" 2>/dev/null || true
    print_info "Cleaned up uvicorn processes"
fi

print_success "Cleanup complete"

###############################################################################
# VERIFICATION
###############################################################################

echo ""
print_step "Verifying shutdown..."

sleep 1

# Check if ports are free
if lsof -ti :8000 > /dev/null 2>&1; then
    print_warning "Port 8000 still in use!"
    print_info "Run: lsof -ti :8000 | xargs kill -9"
else
    print_success "Port 8000 is free"
fi

if lsof -ti :3000 > /dev/null 2>&1; then
    print_warning "Port 3000 still in use!"
    print_info "Run: lsof -ti :3000 | xargs kill -9"
else
    print_success "Port 3000 is free"
fi

###############################################################################
# SUMMARY
###############################################################################

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              ✅ SYSTEM STOPPED SUCCESSFULLY                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$STOPPED_SOMETHING" = true ]; then
    print_success "All services have been stopped"
else
    print_info "No services were running"
fi

echo ""
print_info "To start again: ./start.sh"
echo ""

###############################################################################
# OPTIONAL: Clean logs
###############################################################################

read -p "Delete log files? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f /tmp/sentintinel_*.log 2>/dev/null
    print_success "Log files deleted"
fi

echo ""
print_success "Shutdown complete! 🛑"
echo ""
