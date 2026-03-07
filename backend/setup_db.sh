#!/bin/bash
# Script to set up PostgreSQL database and user for SentinTinel

echo "Setting up PostgreSQL database for SentinTinel..."
echo ""
echo "You'll need to enter your PostgreSQL admin password (usually 'postgres' user)"
echo ""

# Read database credentials from .env file
DB_NAME=$(grep POSTGRES_DB .env | cut -d '=' -f2 | tr -d ' ')
DB_USER=$(grep POSTGRES_USER .env | cut -d '=' -f2 | tr -d ' ')
DB_PASSWORD=$(grep POSTGRES_PASSWORD .env | cut -d '=' -f2 | tr -d ' ')

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Error: Could not read database credentials from .env file"
    exit 1
fi

echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Create database and user
psql -U postgres << EOF
-- Create user if not exists
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    RAISE NOTICE 'User $DB_USER created';
  ELSE
    RAISE NOTICE 'User $DB_USER already exists';
  END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Database and user created!"
    echo ""

    # Initialize tables
    echo "Creating database tables..."
    python -c "from database import init_db; init_db()"

    if [ $? -eq 0 ]; then
        echo "✓ Database tables created!"
        echo ""

        # Seed admin user
        echo "Creating admin user..."
        python seed_admin.py

        if [ $? -eq 0 ]; then
            echo ""
            echo "╔════════════════════════════════════════════════════════╗"
            echo "║           ✅ SETUP COMPLETE!                          ║"
            echo "╚════════════════════════════════════════════════════════╝"
            echo ""
            echo "Admin credentials:"
            echo "  Email:    moneshrallapalli@gmail.com"
            echo "  Password: admin123"
            echo ""
            echo "⚠️  Please change the password after first login!"
        fi
    else
        echo "✗ Failed to create database tables"
    fi
else
    echo ""
    echo "✗ Database setup failed. Please check your PostgreSQL connection."
    echo "Make sure PostgreSQL is running and you have the correct admin password."
fi

