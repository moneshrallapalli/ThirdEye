#!/bin/bash

################################################################################
# ThirdEye Surveillance System - Docker Start Script
# Starts all services using Docker Compose
################################################################################

set -e

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

print_header "🛡️  Starting ThirdEye with Docker"

################################################################################
# Check Prerequisites
################################################################################

print_header "Checking Prerequisites"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    print_warning "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker found: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed"
    print_warning "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    print_success "Docker Compose found: $(docker-compose --version)"
else
    COMPOSE_CMD="docker compose"
    print_success "Docker Compose found: $(docker compose version)"
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running"
    print_warning "Please start Docker Desktop or Docker daemon"
    exit 1
fi
print_success "Docker daemon is running"

################################################################################
# Setup Environment
################################################################################

print_header "Environment Setup"

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    print_warning ".env file not found. Creating from template..."
    cp backend/.env.example backend/.env
    print_warning "⚠️  IMPORTANT: Please edit backend/.env and add your Gemini API key!"
    print_warning "The file is located at: $SCRIPT_DIR/backend/.env"
    echo ""
    read -p "Press Enter after you've added your API key, or Ctrl+C to cancel..."
fi

# Verify API key is set
if grep -q "your_gemini_api_key_here" backend/.env || grep -q "your_api_key_here" backend/.env; then
    print_error "Gemini API key not configured!"
    print_warning "Please edit backend/.env and replace 'your_api_key_here' with your actual Gemini API key"
    print_warning "Get your API key from: https://ai.google.dev/"
    exit 1
fi

print_success "Environment configuration found"

################################################################################
# Start Services
################################################################################

print_header "Starting Services"

print_message "$YELLOW" "Building and starting containers..."
echo ""

# Stop any existing containers
$COMPOSE_CMD down 2>/dev/null || true

# Start services
$COMPOSE_CMD up -d --build

if [ $? -eq 0 ]; then
    print_success "All containers started successfully"
else
    print_error "Failed to start containers"
    exit 1
fi

################################################################################
# Wait for Services
################################################################################

print_header "Waiting for Services to Initialize"

print_message "$YELLOW" "Waiting for PostgreSQL..."
for i in {1..30}; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U thirdeye_user &> /dev/null; then
        print_success "PostgreSQL is ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        print_error "PostgreSQL failed to start"
        $COMPOSE_CMD logs postgres
        exit 1
    fi
done

print_message "$YELLOW" "Waiting for Redis..."
for i in {1..30}; do
    if $COMPOSE_CMD exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis is ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        print_warning "Redis timeout (optional service)"
        break
    fi
done

print_message "$YELLOW" "Waiting for Backend..."
for i in {1..60}; do
    if curl -s http://localhost:8000/health &> /dev/null; then
        print_success "Backend is ready"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        print_error "Backend failed to start"
        print_warning "Checking logs..."
        $COMPOSE_CMD logs backend
        exit 1
    fi
done

print_message "$YELLOW" "Waiting for Frontend..."
sleep 5
print_success "Frontend should be ready"

################################################################################
# Summary
################################################################################

print_header "✅ ThirdEye Started Successfully!"

echo ""
print_message "$GREEN" "Services Status:"
$COMPOSE_CMD ps
echo ""

print_message "$GREEN" "Access Points:"
print_message "$GREEN" "  • Frontend:  http://localhost:3000"
print_message "$GREEN" "  • Backend:   http://localhost:8000"
print_message "$GREEN" "  • API Docs:  http://localhost:8000/docs"
echo ""

print_message "$YELLOW" "Useful Commands:"
print_message "$YELLOW" "  • View logs:        $COMPOSE_CMD logs -f"
print_message "$YELLOW" "  • View backend:     $COMPOSE_CMD logs -f backend"
print_message "$YELLOW" "  • View frontend:    $COMPOSE_CMD logs -f frontend"
print_message "$YELLOW" "  • Stop system:      ./stop-docker.sh"
echo ""

print_message "$BLUE" "Opening dashboard in browser..."
sleep 2

# Try to open browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000 &> /dev/null
elif command -v open &> /dev/null; then
    open http://localhost:3000 &> /dev/null
else
    print_warning "Could not open browser automatically. Please visit: http://localhost:3000"
fi

print_message "$GREEN" "🎉 Happy Monitoring!"
