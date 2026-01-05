# Getting Started with URL Shortener

A complete, production-ready distributed URL shortener built with FastAPI, PostgreSQL, Redis, and Celery.

## ⚡ Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose installed
- 2GB free disk space

### 1. Clone/Navigate to Project
```bash
cd url-shortener
```

### 2. Start All Services
```bash
# Copy environment variables
cp .env.example .env

# Start with Docker Compose (includes PostgreSQL, Redis, API, Celery)
docker-compose up -d
```

### 3. Verify Services
```bash
docker-compose ps
```

Expected output:
```
NAME                   STATUS
shortener_db          Up (healthy)
shortener_cache       Up (healthy)
shortener_api         Up
shortener_celery      Up
shortener_celery_beat Up
```

### 4. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 5. Test the API

Generate a test user ID:
```bash
USER_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
echo "Your test user ID: $USER_ID"
```

**Shorten a URL:**
```bash
curl -X POST http://localhost:8000/api/v1/shorten/ \
  -H "Authorization: Bearer $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/python/cpython",
    "title": "Python CPython Repository",
    "custom_alias": "python"
  }'
```

Expected response:
```json
{
  "id": "uuid",
  "short_code": "abc123",
  "short_url": "http://localhost:8000/abc123",
  "original_url": "https://github.com/python/cpython",
  "custom_alias": "python",
  "title": "Python CPython Repository",
  "created_at": "2024-01-05T12:00:00",
  "expires_at": null
}
```

**Use the shortened URL:**
```bash
# This will redirect you to the original URL
curl -L http://localhost:8000/python
```

**Get your URLs:**
```bash
curl -X GET http://localhost:8000/api/v1/shorten/user/urls \
  -H "Authorization: Bearer $USER_ID"
```

**Get Analytics:**
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/python?days=30" \
  -H "Authorization: Bearer $USER_ID"
```

## 📊 What's Running

```
┌─────────────────────────────────────┐
│      URL Shortener Services         │
├─────────────────────────────────────┤
│ FastAPI (web)         → :8000       │
│ PostgreSQL (postgres) → :5432       │
│ Redis (redis)         → :6379       │
│ Celery Worker         → background  │
│ Celery Beat           → background  │
└─────────────────────────────────────┘
```

## 🔍 View Logs

```bash
# API logs
docker-compose logs -f web

# Celery worker logs
docker-compose logs -f celery

# Database logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

## 🛑 Stop Services

```bash
# Stop all services (keep data)
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## 📁 Project Structure

```
url-shortener/
├── app/                    # Application code
│   ├── main.py            # FastAPI app entry point
│   ├── config.py          # Configuration
│   ├── database.py        # Database setup
│   ├── models/            # Database models
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   └── workers/           # Celery tasks
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Container image
├── requirements.txt      # Python dependencies
├── README.md            # Full documentation
└── start.sh             # Quick start script
```

## 🔧 API Reference

### POST /api/v1/shorten/
Shorten a URL with optional custom alias

**Headers:**
- `Authorization: Bearer {user_id}`
- `Content-Type: application/json`

**Body:**
```json
{
  "url": "https://example.com/very/long/path",
  "custom_alias": "myalias",        // optional, 3-20 chars
  "title": "My Title",               // optional
  "description": "Description",      // optional
  "expires_in_hours": 24             // optional, 1-8760
}
```

### GET /{short_code}
Redirect to original URL

**Example:**
```bash
curl -L http://localhost:8000/abc123
```

### GET /api/v1/shorten/user/urls
Get all user's shortened URLs

**Headers:**
- `Authorization: Bearer {user_id}`

**Query Parameters:**
- `skip`: Number of results to skip (default: 0)
- `limit`: Number of results to return (default: 50, max: 100)

### GET /api/v1/analytics/{short_code}
Get analytics for a specific URL

**Headers:**
- `Authorization: Bearer {user_id}`

**Query Parameters:**
- `days`: Number of days to analyze (default: 30, range: 1-365)

**Response:**
```json
{
  "total_clicks": 42,
  "unique_days": 15,
  "top_countries": [{"country": "US", "clicks": 25}],
  "top_devices": [{"device_type": "desktop", "clicks": 30}],
  "top_browsers": [{"browser": "Chrome", "clicks": 20}],
  "last_clicked_at": "2024-01-05T18:30:00"
}
```

### GET /api/v1/analytics/stats/dashboard
Get dashboard statistics for all user's URLs

**Headers:**
- `Authorization: Bearer {user_id}`

## 🚀 Advanced Usage

### Local Development (without Docker)

1. **Install Python 3.11+**
2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Start PostgreSQL & Redis** (using Docker or locally installed):
```bash
docker run -d -p 5432:5432 -e POSTGRES_USER=shortener -e POSTGRES_PASSWORD=shortener_pass -e POSTGRES_DB=url_shortener_db postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

5. **Run FastAPI:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Run Celery Worker** (in another terminal):
```bash
celery -A app.workers.tasks worker --loglevel=info
```

7. **Run Celery Beat** (in another terminal):
```bash
celery -A app.workers.tasks beat --loglevel=info
```

### Scale Services

```bash
# Scale API instances
docker-compose up -d --scale web=3

# Scale Celery workers
docker-compose up -d --scale celery=3
```

### Custom Configuration

Edit `.env` file before running:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0
REDIS_CACHE_EXPIRY=86400

# API
DEBUG=False
ENVIRONMENT=production
SHORTENER_DOMAIN=https://short.example.com

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD_SECONDS=60
```

## 📈 Performance Tips

1. **Use custom aliases sparingly** - Increases uniqueness checks
2. **Batch analytics queries** - Reduce database load
3. **Cache frequently accessed URLs** - Already done via Redis
4. **Monitor database connections** - Keep connection pool size appropriate
5. **Scale workers** - Add more Celery workers for high traffic

## 🐛 Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up -d --build
```

### Database connection error
```bash
# Check if PostgreSQL is healthy
docker-compose ps postgres

# View database logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Redis connection error
```bash
# Check if Redis is healthy
docker-compose logs redis

# Test connection
docker exec shortener_cache redis-cli ping
```

### API endpoint returns 401
Make sure you're using a valid Bearer token in Authorization header:
```bash
curl -H "Authorization: Bearer valid-uuid-here" http://localhost:8000/api/v1/shorten/user/urls
```

## 📚 Additional Resources

- **Full Documentation**: See `README.md`
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Celery**: https://docs.celeryproject.org/
- **Redis**: https://redis.io/

## 🤝 Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Review `README.md` for detailed documentation
3. Check API docs: http://localhost:8000/docs

## ✅ Checklist

- [x] Docker & Docker Compose installed
- [x] Services running and healthy
- [x] Can generate shortened URLs
- [x] Can redirect to original URLs
- [x] Can view analytics
- [x] All API endpoints working

You're all set! Start creating shortened URLs now! 🎉
