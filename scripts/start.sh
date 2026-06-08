#!/bin/bash
# Quick start script for PixelGuard

set -e

echo "🔒 PixelGuard - Quick Start"
echo "=========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

echo "✓ Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✓ Docker Compose found"

# Create .env files if they don't exist
if [ ! -f backend/.env ]; then
    echo "Creating backend/.env..."
    cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env ]; then
    echo "Creating frontend/.env..."
    cp frontend/.env.example frontend/.env
fi

# Start services
echo ""
echo "Starting services..."
docker-compose up -d

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if docker-compose exec backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ Backend is ready"
        break
    fi
    sleep 1
done

# Initialize database
echo "Initializing database..."
docker-compose exec backend python scripts/setup_db.py

echo ""
echo "=========================================="
echo "✓ PixelGuard is ready!"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "Docs:     http://localhost:8000/docs"
echo ""
echo "To stop: docker-compose down"
