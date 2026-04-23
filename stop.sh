#!/bin/bash

###############################################################################
#                   THIRDEYE SURVEILLANCE SYSTEM
#                        STOP SCRIPT v2.1
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# PID files
BACKEND_PID_FILE="/tmp/thirdeye_backend.pid"
FRONTEND_PID_FILE="/tmp/thirdeye_frontend.pid"

# Non-interactive mode is enabled when:
#   * $THIRDEYE_NONINTERACTIVE is set (e.g. by restart.sh)
#   * stdin is not a TTY (script is piped / chained)
#   * any of --yes / -y / --no-prompt is passed
NONINTERACTIVE=0
PURGE_LOGS=0
for arg in "$@"; do
    case "$arg" in
        --yes|-y|--no-prompt) NONINTERACTIVE=1 ;;
        --purge-logs)         PURGE_LOGS=1 ;;
    esac
done
if [ -n "$THIRDEYE_NONINTERACTIVE" ]; then NONINTERACTIVE=1; fi
if ! [ -t 0 ];                         then NONINTERACTIVE=1; fi

###############################################################################
# FUNCTIONS
###############################################################################

print_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║         🛑 THIRDEYE SURVEILLANCE SYSTEM SHUTDOWN          ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

print_step()    { echo -e "${CYAN}▶ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error()   { echo -e "${RED}❌ $1${NC}"; }
print_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }

kill_process() {
    local pid=$1
    local name=$2

    # Guard against empty/invalid PID values in stale PID files.
    if [ -z "$pid" ] || ! [[ "$pid" =~ ^[0-9]+$ ]]; then
        print_info "$name has no valid PID recorded"
        return 0
    fi

    if ps -p "$pid" > /dev/null 2>&1; then
        kill "$pid" 2>/dev/null && print_success "$name stopped (PID: $pid)" || print_warning "$name already stopped"
        sleep 1
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null
            print_info "Forced $name to stop"
        fi
    else
        print_info "$name was not running"
    fi
}

kill_by_port() {
    local port=$1
    local name=$2
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null
        print_success "$name on port $port stopped"
    else
        print_info "No process running on port $port"
    fi
}

# Wait (up to 10s) for a port to become free so a subsequent start won't
# race the TCP TIME_WAIT / process shutdown.
wait_port_free() {
    local port=$1
    local label=$2
    local attempt=0
    while lsof -ti :"$port" > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 20 ]; then
            print_warning "Port $port ($label) is still in use after 10s"
            return 1
        fi
        sleep 0.5
    done
    return 0
}

###############################################################################
# MAIN STOP LOGIC
###############################################################################

print_header

print_step "Stopping ThirdEye Surveillance System..."
echo ""

STOPPED_SOMETHING=false

###############################################################################
# STOP BACKEND
###############################################################################

print_step "Stopping backend..."

# 1. PID file
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
    kill_process "$BACKEND_PID" "Backend"
    rm -f "$BACKEND_PID_FILE"
    STOPPED_SOMETHING=true
fi

# 2. Only our backend process — NOT every Python on the machine.
if pgrep -f "python.*main\.py" > /dev/null; then
    print_step "Stopping backend Python processes..."
    pkill -f "python.*main\.py" 2>/dev/null && print_success "Backend Python processes stopped" || true
    STOPPED_SOMETHING=true
fi

# 3. Any stray uvicorn spawned by the backend
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    STOPPED_SOMETHING=true
fi

# 4. By port (final safety net, scoped)
if lsof -ti :8000 > /dev/null 2>&1; then
    kill_by_port 8000 "Backend"
    STOPPED_SOMETHING=true
fi

print_success "Backend shutdown complete"

###############################################################################
# STOP FRONTEND
###############################################################################

echo ""
print_step "Stopping frontend..."

if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE" 2>/dev/null)
    kill_process "$FRONTEND_PID" "Frontend"
    rm -f "$FRONTEND_PID_FILE"
    STOPPED_SOMETHING=true
fi

if pgrep -f "react-scripts" > /dev/null; then
    print_step "Stopping React dev server..."
    pkill -f "react-scripts" 2>/dev/null && print_success "React processes stopped" || true
    STOPPED_SOMETHING=true
fi

# Scope node kill to the frontend directory so we don't nuke unrelated Node
# processes the user is running.
FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/frontend"
if pgrep -fl "node.*$FRONTEND_DIR" > /dev/null 2>&1; then
    pkill -f "node.*$FRONTEND_DIR" 2>/dev/null || true
    STOPPED_SOMETHING=true
fi

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

rm -f "$BACKEND_PID_FILE" 2>/dev/null
rm -f "$FRONTEND_PID_FILE" 2>/dev/null

print_success "Cleanup complete"

###############################################################################
# VERIFICATION — actively wait for ports to free up
###############################################################################

echo ""
print_step "Verifying shutdown..."

wait_port_free 8000 "backend"  && print_success "Port 8000 is free" || print_warning "Port 8000 still in use — run: lsof -ti :8000 | xargs kill -9"
wait_port_free 3000 "frontend" && print_success "Port 3000 is free" || print_warning "Port 3000 still in use — run: lsof -ti :3000 | xargs kill -9"

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
# OPTIONAL: Clean logs — never blocks a non-interactive caller
###############################################################################

if [ "$PURGE_LOGS" = "1" ]; then
    rm -f /tmp/thirdeye_*.log 2>/dev/null
    print_success "Log files deleted"
elif [ "$NONINTERACTIVE" = "1" ]; then
    # Called from restart.sh or a pipeline — just leave logs in place.
    :
else
    read -r -p "Delete log files? (y/n) " -n 1 REPLY
    echo
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        rm -f /tmp/thirdeye_*.log 2>/dev/null
        print_success "Log files deleted"
    fi
fi

echo ""
print_success "Shutdown complete! 🛑"
echo ""
