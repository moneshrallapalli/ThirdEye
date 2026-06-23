#!/bin/bash

################################################################################
# ThirdEye Surveillance System - Docker Stop Script
# Stops all Docker containers
################################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_message() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    print_message "$BLUE" "=================================="
    print_message "$BLUE" "$1"
    print_message "$BLUE" "=================================="
}

print_success() {
    print_message "$GREEN" "✓ $1"
}

print_error() {
    print_message "$RED" "✗ $1"
}

print_warning() {
    print_message "$YELLOW" "⚠ $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_header "🛑 Stopping ThirdEye Docker Containers"

# Determine Docker Compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

################################################################################
# Stop Containers
################################################################################

print_header "Stopping Containers"

$COMPOSE_CMD down

if [ $? -eq 0 ]; then
    print_success "All containers stopped successfully"
else
    print_error "Failed to stop containers"
    exit 1
fi

################################################################################
# Optional: Remove Volumes
################################################################################

echo ""
read -p "$(echo -e ${YELLOW}Do you want to remove data volumes (will delete all data)? [y/N]: ${NC})" -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Removing volumes..."
    $COMPOSE_CMD down -v
    print_success "Volumes removed"
else
    print_message "$GREEN" "Data volumes preserved"
fi

################################################################################
# Optional: Remove Images
################################################################################

echo ""
read -p "$(echo -e ${YELLOW}Do you want to remove Docker images? [y/N]: ${NC})" -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Removing images..."
    docker rmi $(docker images -q practice_backend practice_frontend) 2>/dev/null || print_warning "No images to remove"
    print_success "Images removed"
else
    print_message "$GREEN" "Docker images preserved"
fi

################################################################################
# Summary
################################################################################

print_header "✅ ThirdEye Stopped"

echo ""
print_message "$GREEN" "All containers have been stopped successfully"
echo ""
print_message "$BLUE" "To start the system again, run: ./start-docker.sh"
echo ""
