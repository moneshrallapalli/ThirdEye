#!/bin/bash

###############################################################################
#                   SENTINTINEL AUTHENTICATION SETUP
#                          Quick Setup Script
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║        🔐 SENTINTINEL AUTHENTICATION SETUP                   ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_header

# Check if we're in the backend directory
if [ ! -f "main.py" ]; then
    print_error "Please run this script from the backend directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    print_step "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
fi

# Check if database is accessible
print_step "Checking database connection..."
python -c "from database import engine; engine.connect()" 2>/dev/null

if [ $? -ne 0 ]; then
    print_error "Cannot connect to database!"
    print_info "Make sure PostgreSQL is running:"
    print_info "  docker-compose up -d"
    echo ""
    exit 1
fi

print_success "Database connection successful"

# Initialize database tables
print_step "Creating/updating database tables..."
python -c "from database import init_db; init_db()"

if [ $? -eq 0 ]; then
    print_success "Database tables ready"
else
    print_error "Failed to create database tables"
    exit 1
fi

# Seed admin user
print_step "Creating admin user..."
python seed_admin.py

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           ✅ AUTHENTICATION SETUP COMPLETE!               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🔐 Admin Credentials:"
    echo "   Email:     moneshrallapalli@gmail.com"
    echo "   Password:  admin123"
    echo ""
    print_info "⚠️  Please change the password after first login!"
    echo ""
    print_info "Start the application with: ./start.sh"
    echo ""
else
    print_error "Failed to create admin user"
    exit 1
fi
