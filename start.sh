#!/bin/bash

###############################################################################
#                      THIRDEYE SURVEILLANCE SYSTEM
#                          START SCRIPT v2.0
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
BACKEND_LOG="/tmp/thirdeye_backend.log"
FRONTEND_LOG="/tmp/thirdeye_frontend.log"

###############################################################################
# FUNCTIONS
###############################################################################

print_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║        🚀 THIRDEYE SURVEILLANCE SYSTEM STARTUP            ║"
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

# Non-interactive mode: restart.sh / CI / piped invocations auto-reclaim ports
# instead of blocking on an interactive prompt.
NONINTERACTIVE=0
for arg in "$@"; do
    case "$arg" in
        --yes|-y|--no-prompt) NONINTERACTIVE=1 ;;
    esac
done
if [ -n "$THIRDEYE_NONINTERACTIVE" ]; then NONINTERACTIVE=1; fi
if ! [ -t 0 ];                         then NONINTERACTIVE=1; fi

reclaim_port() {
    local port=$1
    local label=$2
    print_step "Reclaiming port $port ($label)..."
    # Only kill processes that are genuinely ours: backend main.py / react-scripts,
    # plus a final lsof-based sweep on the port itself.
    if [ "$port" = "8000" ]; then
        pkill -f "python.*main\.py" 2>/dev/null || true
        pkill -f "uvicorn.*main:app" 2>/dev/null || true
    elif [ "$port" = "3000" ]; then
        pkill -f "react-scripts" 2>/dev/null || true
        pkill -f "node.*$FRONTEND_DIR" 2>/dev/null || true
    fi
    if lsof -ti :"$port" > /dev/null 2>&1; then
        lsof -ti :"$port" | xargs kill -9 2>/dev/null || true
    fi
    sleep 1
}

# Check if already running
if check_port 8000; then
    print_warning "Backend already running on port 8000"
    if [ "$NONINTERACTIVE" = "1" ]; then
        reclaim_port 8000 "backend"
    else
        read -r -p "Stop and restart? (y/n) " -n 1 REPLY
        echo
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            reclaim_port 8000 "backend"
        else
            print_error "Cannot start - port 8000 already in use"
            exit 1
        fi
    fi
fi

if check_port 3000; then
    print_warning "Frontend already running on port 3000"
    if [ "$NONINTERACTIVE" = "1" ]; then
        reclaim_port 3000 "frontend"
    else
        read -r -p "Stop and restart? (y/n) " -n 1 REPLY
        echo
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            reclaim_port 3000 "frontend"
        else
            print_error "Cannot start - port 3000 already in use"
            exit 1
        fi
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

# Docker services: bring up postgres + redis and wait for readiness
print_step "Checking Docker services..."
if ! check_command docker; then
    print_error "Docker is required but not installed."
    print_info "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop and retry."
    exit 1
fi
print_success "Docker is running"

# Read Postgres host/port from backend/.env so checks match the backend's config
PG_HOST=$(grep -E '^POSTGRES_HOST=' "$BACKEND_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
PG_PORT=$(grep -E '^POSTGRES_PORT=' "$BACKEND_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
PG_HOST=${PG_HOST:-127.0.0.1}
PG_PORT=${PG_PORT:-5432}

# Pick the right compose CLI (v2 plugin preferred, v1 fallback)
if docker compose version > /dev/null 2>&1; then
    COMPOSE="docker compose"
elif check_command docker-compose; then
    COMPOSE="docker-compose"
else
    print_error "Neither 'docker compose' nor 'docker-compose' is available."
    exit 1
fi

# Self-heal common stuck states before bringing things up. If there's a
# container with our fixed name hanging around in Exited / Created state,
# `compose up` will often fail rather than reuse it — remove it so the
# next call creates a fresh one.
for cname in sentintinel_postgres sentintinel_redis; do
    state=$(docker inspect -f '{{.State.Status}}' "$cname" 2>/dev/null || true)
    if [ -n "$state" ] && [ "$state" != "running" ]; then
        print_warning "Found stale container $cname in state '$state' — removing"
        docker rm -f "$cname" > /dev/null 2>&1 || true
    fi
done

# Port conflict diagnosis. For each host port we publish, figure out
# who is listening on it. Common causes on macOS:
#  - An older compose run (different container names) is still up
#    under a previous project name. These are "orphans" — safe to nuke.
#  - `brew services` has started a local postgres/redis that's bound
#    to the same port. The user has to stop it themselves.
#
# We auto-remove orphan docker containers (anything whose name is not
# sentintinel_* that binds our port), and loudly warn on host-level
# daemons so the user can make an informed decision.
declare -a HOST_PORT_WARNINGS=()
for hp in 5433 6379; do
    # Find any docker container publishing this host port.
    blocker_container=$(docker ps --format '{{.Names}}|{{.Ports}}' 2>/dev/null \
        | awk -F'|' -v p=":${hp}->" '$2 ~ p {print $1; exit}')
    if [ -n "$blocker_container" ] \
        && [ "$blocker_container" != "sentintinel_postgres" ] \
        && [ "$blocker_container" != "sentintinel_redis" ]; then
        print_warning "Orphan container '$blocker_container' is holding host port ${hp} — removing"
        docker rm -f "$blocker_container" > /dev/null 2>&1 || true
    fi

    # Anything *else* (host daemon like brew postgres/redis) still on
    # the port? Surface it as a warning, don't auto-kill.
    if lsof -iTCP:${hp} -sTCP:LISTEN -P 2>/dev/null | awk 'NR>1 {print $1}' \
        | grep -vE '^(com\.docke|docker|vpnkit)' | grep -q .; then
        owner=$(lsof -iTCP:${hp} -sTCP:LISTEN -P 2>/dev/null \
            | awk 'NR>1 && $1 !~ /^(com\.docke|docker|vpnkit)/ {print $1 " (pid " $2 ")"; exit}')
        HOST_PORT_WARNINGS+=("Port ${hp} is also held by host process ${owner}.")
    fi
done
if [ ${#HOST_PORT_WARNINGS[@]} -gt 0 ]; then
    for w in "${HOST_PORT_WARNINGS[@]}"; do
        print_warning "$w"
    done
    print_info "This usually means a Homebrew service (e.g. 'brew services list') is"
    print_info "running a duplicate postgres/redis. Docker can still start our"
    print_info "containers, but the backend may connect to the brew instance first."
    print_info "To silence this, stop it with: brew services stop postgresql && brew services stop redis"
fi

# Idempotent bring-up: no-op if already running, starts/creates if not.
# Stderr is captured (not discarded) so failures surface in the terminal
# instead of producing a silent "Failed to start database containers."
# NOTE: 'set -e' is active in this script, so we must temporarily disable
# it — otherwise a non-zero command substitution aborts before we can
# print the diagnostic block below.
print_step "Starting database containers (postgres + redis)..."
set +e
COMPOSE_ERR=$(cd "$SCRIPT_DIR" && $COMPOSE up -d postgres redis 2>&1)
COMPOSE_RC=$?
set -e
if [ $COMPOSE_RC -ne 0 ]; then
    print_error "Failed to start database containers (exit $COMPOSE_RC)."
    echo "----- compose output -----"
    echo "$COMPOSE_ERR"
    echo "--------------------------"
    echo "----- current docker state -----"
    docker ps -a --filter "name=sentintinel_" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
    echo "--------------------------------"
    print_info "Common fixes:"
    print_info "  1. Make sure Docker Desktop is fully started (whale icon solid, not animating)"
    print_info "  2. Remove stale containers: docker rm -f sentintinel_postgres sentintinel_redis"
    print_info "  3. Free the host ports: lsof -iTCP:5433 -sTCP:LISTEN ; lsof -iTCP:6379 -sTCP:LISTEN"
    print_info "  4. Retry manually: (cd $SCRIPT_DIR && $COMPOSE up -d postgres redis)"
    exit 1
fi
print_success "Database containers up"

# Wait for PostgreSQL to actually accept connections
print_step "Waiting for PostgreSQL at ${PG_HOST}:${PG_PORT}..."
attempt=0
max_attempts=30
until docker exec sentintinel_postgres pg_isready -h localhost -p 5432 > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo ""
        print_error "PostgreSQL did not become ready within ${max_attempts}s"
        print_info "Check container logs: docker logs sentintinel_postgres"
        exit 1
    fi
    sleep 1
    echo -n "."
done
echo ""
print_success "PostgreSQL ready at ${PG_HOST}:${PG_PORT}"

# Initialize database tables (first time only)
if [ ! -f "venv/.database_initialized" ]; then
    print_step "Initializing database tables..."
    if python -c "from database import init_db; init_db()"; then
        touch venv/.database_initialized
        print_success "Database tables created"

        # Seed admin user
        print_step "Seeding admin user..."
        python seed_admin.py
        if [ $? -eq 0 ]; then
            print_success "Admin user created"
            print_info "   Email: moneshrallapalli@gmail.com"
            print_info "   Password: admin123"
        else
            print_warning "Failed to seed admin user (may already exist)"
        fi
    else
        print_warning "Database initialization skipped (database not available)"
        print_info "The system will work without database - start Docker and restart"
    fi
else
    print_success "Database already initialized"
fi

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
echo $BACKEND_PID > /tmp/thirdeye_backend.pid
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
echo $FRONTEND_PID > /tmp/thirdeye_frontend.pid
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
echo "🔐 Login Credentials:"
echo "   Email:     moneshrallapalli@gmail.com"
echo "   Password:  admin123"
echo ""
echo "📊 Process IDs:"
echo "   Backend:   $BACKEND_PID (PID file: /tmp/thirdeye_backend.pid)"
echo "   Frontend:  $FRONTEND_PID (PID file: /tmp/thirdeye_frontend.pid)"
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
