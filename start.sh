#!/bin/bash

###############################################################################
#                   SENTINTINEL SURVEILLANCE SYSTEM
#                        START SCRIPT v2.0
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Log files
BACKEND_LOG="/tmp/sentintinel_backend.log"
FRONTEND_LOG="/tmp/sentintinel_frontend.log"

###############################################################################
# FUNCTIONS
###############################################################################

print_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║        🚀 SENTINTINEL SURVEILLANCE SYSTEM STARTUP            ║"
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

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    print_step "Waiting for $name to start..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$name is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
        echo -n "."
    done
    
    echo ""
    print_error "$name failed to start within ${max_attempts} seconds"
    return 1
}

###############################################################################
# PRE-FLIGHT CHECKS
###############################################################################

print_header

print_step "Running pre-flight checks..."
echo ""

# Check if already running
if check_port 8000; then
    print_warning "Backend already running on port 8000"
    read -p "Stop and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Stopping existing backend..."
        killall python 2>/dev/null || true
        sleep 2
    else
        print_error "Cannot start - port 8000 already in use"
        exit 1
    fi
fi

if check_port 3000; then
    print_warning "Frontend already running on port 3000"
    read -p "Stop and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Stopping existing frontend..."
        lsof -ti :3000 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        print_error "Cannot start - port 3000 already in use"
        exit 1
    fi
fi

# Check Python
if ! check_command python3 && ! check_command python; then
    print_error "Python 3 is not installed!"
    print_info "Install Python 3: https://www.python.org/downloads/"
    exit 1
fi
print_success "Python found"

# Check Node.js
if ! check_command node; then
    print_error "Node.js is not installed!"
    print_info "Install Node.js: https://nodejs.org/"
    exit 1
fi
print_success "Node.js found ($(node --version))"

# Check npm
if ! check_command npm; then
    print_error "npm is not installed!"
    exit 1
fi
print_success "npm found ($(npm --version))"

# Check directories
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    print_error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

print_success "All directories found"

###############################################################################
# BACKEND SETUP
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_step "BACKEND SETUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$BACKEND_DIR"

# Check .env file
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_info "Creating .env from .env.example..."
    
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning ".env created. Please add your API keys!"
        print_info "Edit: $BACKEND_DIR/.env"
        exit 1
    else
        print_error ".env.example not found!"
        exit 1
    fi
fi

print_success ".env file found"

# Check if GEMINI_API_KEY is set
if grep -q "your_api_key_here" .env 2>/dev/null; then
    print_error "GEMINI_API_KEY not configured in .env!"
    print_info "Please edit $BACKEND_DIR/.env and add your Gemini API key"
    print_info "Get your key from: https://aistudio.google.com/app/apikey"
    exit 1
fi

print_success "API key configured"

# Check/Create virtual environment
if [ ! -d "venv" ]; then
    print_step "Creating Python virtual environment..."
    python3 -m venv venv || python -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source venv/bin/activate

# Install/Update Python dependencies
if [ ! -f "venv/.dependencies_installed" ]; then
    print_step "Installing Python dependencies (first time)..."
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    touch venv/.dependencies_installed
    print_success "Python dependencies installed"
else
    print_success "Python dependencies already installed"
fi

# Create necessary directories
print_step "Creating required directories..."
mkdir -p event_frames
mkdir -p chromadb_data
mkdir -p logs
print_success "Directories ready"

###############################################################################
# FRONTEND SETUP
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_step "FRONTEND SETUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$FRONTEND_DIR"

# Install node modules if needed
if [ ! -d "node_modules" ]; then
    print_step "Installing Node.js dependencies (this may take a few minutes)..."
    npm install --legacy-peer-deps > /dev/null 2>&1
    print_success "Node.js dependencies installed"
else
    print_success "Node.js dependencies already installed"
fi

###############################################################################
# START SERVICES
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_step "STARTING SERVICES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Backend
print_step "Starting backend server..."
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python main.py > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/sentintinel_backend.pid
print_success "Backend started (PID: $BACKEND_PID)"
print_info "Backend log: $BACKEND_LOG"

# Wait for backend
if ! wait_for_service "http://localhost:8000" "Backend"; then
    print_error "Backend failed to start. Check logs:"
    print_info "tail -50 $BACKEND_LOG"
    exit 1
fi

# Start Frontend
print_step "Starting frontend server..."
cd "$FRONTEND_DIR"
export BROWSER=none  # Don't auto-open browser
nohup npm start > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/sentintinel_frontend.pid
print_success "Frontend started (PID: $FRONTEND_PID)"
print_info "Frontend log: $FRONTEND_LOG"

# Wait for frontend
if ! wait_for_service "http://localhost:3000" "Frontend"; then
    print_error "Frontend failed to start. Check logs:"
    print_info "tail -50 $FRONTEND_LOG"
    exit 1
fi

###############################################################################
# VERIFICATION
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_step "VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sleep 2

# Check backend health
if curl -s http://localhost:8000/health > /dev/null 2>&1 || curl -s http://localhost:8000/ > /dev/null 2>&1; then
    print_success "Backend health check passed"
else
    print_warning "Backend health check failed (may still be starting)"
fi

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_success "Frontend health check passed"
else
    print_warning "Frontend health check failed (may still be starting)"
fi

###############################################################################
# SUCCESS
###############################################################################

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              ✅ SYSTEM STARTED SUCCESSFULLY                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Access Points:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📊 Process IDs:"
echo "   Backend:   $BACKEND_PID (PID file: /tmp/sentintinel_backend.pid)"
echo "   Frontend:  $FRONTEND_PID (PID file: /tmp/sentintinel_frontend.pid)"
echo ""
echo "📝 Logs:"
echo "   Backend:   tail -f $BACKEND_LOG"
echo "   Frontend:  tail -f $FRONTEND_LOG"
echo ""
echo "🛑 To stop:"
echo "   Run: ./stop.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_info "Opening browser in 3 seconds..."
sleep 3

# Try to open browser (macOS)
if check_command open; then
    open http://localhost:3000 2>/dev/null || true
fi

print_success "System ready! 🚀"
echo ""
