#!/bin/bash

###############################################################################
#                   SENTINTINEL SURVEILLANCE SYSTEM
#                        RESTART SCRIPT v2.0
###############################################################################

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         🔄 SENTINTINEL SURVEILLANCE SYSTEM RESTART           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stop services
echo -e "${CYAN}▶ Stopping services...${NC}"
"$SCRIPT_DIR/stop.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait a moment
echo "Waiting 3 seconds..."
sleep 3

# Start services
echo -e "${CYAN}▶ Starting services...${NC}"
echo ""
"$SCRIPT_DIR/start.sh"

echo ""
echo -e "${GREEN}✅ Restart complete!${NC}"
echo ""



