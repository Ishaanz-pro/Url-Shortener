#!/bin/bash

# URL Shortener - Quick Start Script

echo "🚀 Starting URL Shortener with Docker Compose..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

echo "📦 Building and starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Services started successfully!"
    echo ""
    echo "📍 API is running at: http://localhost:8000"
    echo ""
    echo "📚 Interactive API docs: http://localhost:8000/docs"
    echo "📖 ReDoc documentation: http://localhost:8000/redoc"
    echo ""
    echo "🧪 Test the API with:"
    echo ""
    echo "# Generate a UUID for testing"
    echo "USER_ID=\$(python3 -c 'import uuid; print(uuid.uuid4())')"
    echo ""
    echo "# Shorten a URL"
    echo "curl -X POST http://localhost:8000/api/v1/shorten/ \\"
    echo "  -H \"Authorization: Bearer \$USER_ID\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"url\": \"https://github.com\", \"title\": \"GitHub\"}'"
    echo ""
    echo "🛑 To stop services, run: docker-compose down"
    echo ""
else
    echo "❌ Failed to start services. Check logs with: docker-compose logs"
    exit 1
fi
