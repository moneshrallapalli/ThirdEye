#!/bin/bash

###############################################################################
#                   SENTINTINEL SURVEILLANCE SYSTEM
#                        STATUS SCRIPT v2.0
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         📊 SENTINTINEL SURVEILLANCE SYSTEM STATUS            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

###############################################################################
# CHECK BACKEND
###############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 BACKEND (Port 8000)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -ti :8000 > /dev/null 2>&1; then
    print_success "Backend is RUNNING"
    
    # Get PID
    PID=$(lsof -ti :8000)
    echo "   PID: $PID"
    
    # Check health
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_success "Backend responding to requests"
        echo "   URL: http://localhost:8000"
    else
        print_warning "Backend port open but not responding"
    fi
    
    # Show process info
    echo ""
    echo "   Process details:"
    ps -p $PID -o pid,ppid,%cpu,%mem,etime,command | tail -1 | sed 's/^/   /'
    
else
    print_error "Backend is NOT RUNNING"
fi

echo ""

###############################################################################
# CHECK FRONTEND
###############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 FRONTEND (Port 3000)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -ti :3000 > /dev/null 2>&1; then
    print_success "Frontend is RUNNING"
    
    # Get PID
    PID=$(lsof -ti :3000)
    echo "   PID: $PID"
    
    # Check health
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend responding to requests"
        echo "   URL: http://localhost:3000"
    else
        print_warning "Frontend port open but not responding"
    fi
    
    # Show process info
    echo ""
    echo "   Process details:"
    ps -p $PID -o pid,ppid,%cpu,%mem,etime,command | tail -1 | sed 's/^/   /'
    
else
    print_error "Frontend is NOT RUNNING"
fi

echo ""

###############################################################################
# SYSTEM RESOURCES
###############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💻 SYSTEM RESOURCES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# CPU usage of Python processes
if pgrep -f "python.*main.py" > /dev/null; then
    echo "Backend CPU/Memory:"
    ps aux | grep "[p]ython.*main.py" | awk '{printf "   CPU: %s%%  Memory: %s%%  Runtime: %s\n", $3, $4, $10}'
fi

# CPU usage of Node processes
if pgrep -f "react-scripts" > /dev/null; then
    echo "Frontend CPU/Memory:"
    ps aux | grep "[r]eact-scripts" | awk '{printf "   CPU: %s%%  Memory: %s%%  Runtime: %s\n", $3, $4, $10}'
fi

echo ""

###############################################################################
# LOG FILES
###############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 LOG FILES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "/tmp/sentintinel_backend.log" ]; then
    SIZE=$(du -h /tmp/sentintinel_backend.log | awk '{print $1}')
    print_info "Backend log: /tmp/sentintinel_backend.log ($SIZE)"
    echo "   Last 3 lines:"
    tail -3 /tmp/sentintinel_backend.log 2>/dev/null | sed 's/^/   /'
else
    print_warning "Backend log not found"
fi

echo ""

if [ -f "/tmp/sentintinel_frontend.log" ]; then
    SIZE=$(du -h /tmp/sentintinel_frontend.log | awk '{print $1}')
    print_info "Frontend log: /tmp/sentintinel_frontend.log ($SIZE)"
else
    print_warning "Frontend log not found"
fi

echo ""

###############################################################################
# RECENT ERRORS
###############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  RECENT ERRORS (Last 5 minutes)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "/tmp/sentintinel_backend.log" ]; then
    ERRORS=$(grep -i "error\|exception\|failed" /tmp/sentintinel_backend.log 2>/dev/null | tail -5)
    if [ -n "$ERRORS" ]; then
        echo "$ERRORS" | sed 's/^/   /'
    else
        print_success "No recent errors in backend log"
    fi
else
    print_info "No backend log file to check"
fi

echo ""

###############################################################################
# SUMMARY
###############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

BACKEND_UP=false
FRONTEND_UP=false

if lsof -ti :8000 > /dev/null 2>&1; then
    BACKEND_UP=true
fi

if lsof -ti :3000 > /dev/null 2>&1; then
    FRONTEND_UP=true
fi

if [ "$BACKEND_UP" = true ] && [ "$FRONTEND_UP" = true ]; then
    print_success "System is FULLY OPERATIONAL"
    echo ""
    echo "   🌐 Access: http://localhost:3000"
    echo "   📚 API Docs: http://localhost:8000/docs"
elif [ "$BACKEND_UP" = true ] || [ "$FRONTEND_UP" = true ]; then
    print_warning "System is PARTIALLY RUNNING"
    echo ""
    if [ "$BACKEND_UP" = false ]; then
        print_error "Backend needs to be started"
    fi
    if [ "$FRONTEND_UP" = false ]; then
        print_error "Frontend needs to be started"
    fi
    echo ""
    print_info "Run: ./restart.sh"
else
    print_error "System is NOT RUNNING"
    echo ""
    print_info "Run: ./start.sh"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_info "Commands:"
echo "   Start:   ./start.sh"
echo "   Stop:    ./stop.sh"
echo "   Restart: ./restart.sh"
echo "   Status:  ./status.sh"
echo ""



