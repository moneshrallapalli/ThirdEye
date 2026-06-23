#!/bin/bash

###############################################################################
#                   THIRDEYE SURVEILLANCE SYSTEM
#                        RESTART SCRIPT v2.1
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step()    { echo -e "${CYAN}▶ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error()   { echo -e "${RED}❌ $1${NC}"; }

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         🔄 THIRDEYE SURVEILLANCE SYSTEM RESTART           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Force stop.sh and start.sh into non-interactive mode so chained execution
# never blocks on a prompt.
export THIRDEYE_NONINTERACTIVE=1

###############################################################################
# STOP
###############################################################################

print_step "Stopping services..."
if ! "$SCRIPT_DIR/stop.sh"; then
    print_warning "stop.sh reported an issue — continuing anyway."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

###############################################################################
# WAIT FOR PORTS TO FREE (actively, up to 15s)
###############################################################################

wait_port_free() {
    local port=$1
    local attempt=0
    while lsof -ti :"$port" > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 30 ]; then
            print_warning "Port $port still in use after 15s — forcing..."
            lsof -ti :"$port" | xargs kill -9 2>/dev/null || true
            sleep 1
            return 0
        fi
        sleep 0.5
    done
}

print_step "Waiting for ports 8000 and 3000 to be released..."
wait_port_free 8000
wait_port_free 3000
print_success "Ports are free"

echo ""

###############################################################################
# START
###############################################################################

print_step "Starting services..."
echo ""

if ! "$SCRIPT_DIR/start.sh"; then
    print_error "start.sh failed — check the logs:"
    echo "  tail -80 /tmp/thirdeye_backend.log"
    echo "  tail -80 /tmp/thirdeye_frontend.log"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Restart complete!${NC}"
echo ""
