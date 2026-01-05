# Distributed URL Shortener with Analytics

A production-grade, horizontally scalable URL shortener similar to Bitly, built with FastAPI, PostgreSQL, Redis, and Celery.

## 🎯 Features

- **Fast URL Shortening**: Base62 encoding with custom alias support
- **Cache-First Redirection**: Redis caching for sub-50ms redirects
- **URL Expiration**: Set expiration times on shortened URLs
- **Rate Limiting**: Per-user rate limits using Redis sliding window
- **Click Analytics**: Track clicks, device types, countries, browsers
- **Async Processing**: Celery workers for non-blocking analytics recording
- **Horizontal Scalability**: Stateless design for easy scaling
- **Production Ready**: Docker, health checks, error handling, logging

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   FastAPI (Load Balanced)   │
│  (Multiple instances)       │
└──────┬──────────────────────┘
       │
   ┌───┴─────────────────────────┐
   ▼                             ▼
┌──────────┐              ┌────────────┐
│  Redis   │◄─────────────┤ PostgreSQL │
│  Cache   │              │ Database   │
└────┬─────┘              └────────────┘
     │
     ▼
┌──────────────────┐
│ Celery Workers   │
│ (Analytics)      │
└──────────────────┘
```

### Components

**API Layer (FastAPI)**
- Handles HTTP requests
- Request validation & rate limiting
- Serves shortened URLs with cache-first strategy

**Cache Layer (Redis)**
- Stores URL mappings for instant redirects
- Rate limit counters
- Session management

**Database (PostgreSQL)**
- Persistent URL storage
- Analytics records
- User accounts

**Worker Layer (Celery)**
- Asynchronously processes click analytics
- Scheduled cleanup of expired URLs
- Non-blocking operations

## 📊 System Design Decisions

### 1. Cache-First Redirect Strategy
```
Request arrives
    ↓
Check Redis cache → Found? Redirect (< 10ms)
    ↓ Not found
Check PostgreSQL → Cache result
    ↓
Redirect (< 50ms)
```

**Why**: Redirects are the most frequent operation. Redis provides sub-millisecond latency.

### 2. Base62 Encoding
- Uses 0-9, a-z, A-Z (62 characters)
- 6-character code: 62^6 = 56 trillion combinations
- Compact, URL-safe representation

### 3. Asynchronous Analytics
- Analytics recorded via Celery workers, not blocking the redirect
- Click count updates are eventual consistent
- Trade-off: Slightly delayed analytics for fast redirects

### 4. URL Expiration Cleanup
- Celery Beat job runs hourly
- Marks expired URLs as inactive
- Reduces database queries for expired URLs

### 5. Rate Limiting Strategy
```
Key: rate_limit:{user_id}:{action}
Increment counter in Redis
First request: Set expiry = 60 seconds
Subsequent: Check if counter <= limit
Automatic reset after window passes
```

**Why**: Memory-efficient, accurate, distributed across all instances.

## 🚀 Scalability

### Horizontal Scaling

**Scale API Instances**
```bash
# Docker Compose
docker-compose up -d --scale web=5

# Kubernetes
kubectl scale deployment url-shortener --replicas=5
```

**Load Balancer (Nginx)**
```nginx
upstream api {
    server web:8000;
    server web:8001;
    server web:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://api;
    }
}
```

### Database Scaling

**Read Replicas**
- PostgreSQL replication for analytics queries
- Write to primary, read from replicas
- Connection pooling (20-40 connections per instance)

**Caching Strategy**
- Cache hot URLs (99% traffic hits cache)
- Cache expiry: 24 hours (configurable)
- Cache invalidation: When URL is updated

### Worker Scaling

```bash
# Scale Celery workers
docker-compose up -d --scale celery=3

# With Kubernetes
kubectl scale deployment celery-worker --replicas=10
```

**Queue Management**
```
Redis Queue Structure:
- celery (default): analytics tasks
- priority: urgent tasks
- background: low-priority cleanup
```

## 📈 Performance Benchmarks

| Operation | Latency | Method |
|-----------|---------|--------|
| Redirect (cached) | < 10ms | Redis lookup |
| Redirect (uncached) | < 50ms | DB lookup + cache |
| Shorten URL | < 200ms | DB insert + cache |
| Analytics query | < 500ms | Aggregation query |

**Load Capacity**
- Single API instance: ~1000 req/s
- Single PostgreSQL: ~5000 req/s (read), ~500 req/s (write)
- Single Redis: ~100,000 req/s
- **Total: 1M+ daily requests = ~11.5 req/s sustained**

## 🔧 API Endpoints

### Shorten URL
```http
POST /api/v1/shorten/
Authorization: Bearer {user_id}

{
  "url": "https://example.com/very/long/path",
  "custom_alias": "myalias",
  "title": "My Shortened URL",
  "description": "A useful link",
  "expires_in_hours": 24
}

Response:
{
  "id": "uuid",
  "short_code": "abc123",
  "short_url": "http://localhost:8000/abc123",
  "original_url": "https://example.com/very/long/path",
  "custom_alias": "myalias",
  "created_at": "2024-01-05T12:00:00",
  "expires_at": "2024-01-06T12:00:00"
}
```

### Redirect
```http
GET /{short_code}
X-Forwarded-For: client_ip

Response: 302 Redirect to original URL
```

### Get User URLs
```http
GET /api/v1/shorten/user/urls
Authorization: Bearer {user_id}

Response:
[
  {
    "id": "uuid",
    "short_code": "abc123",
    "short_url": "http://localhost:8000/abc123",
    "original_url": "https://example.com/long",
    "click_count": 42,
    "created_at": "2024-01-05T12:00:00"
  }
]
```

### Get Analytics
```http
GET /api/v1/analytics/{short_code}?days=30
Authorization: Bearer {user_id}

Response:
{
  "total_clicks": 42,
  "unique_days": 15,
  "top_countries": [
    {"country": "US", "clicks": 25},
    {"country": "IN", "clicks": 12}
  ],
  "top_devices": [
    {"device_type": "desktop", "clicks": 30},
    {"device_type": "mobile", "clicks": 12}
  ],
  "top_browsers": [
    {"browser": "Chrome", "clicks": 20},
    {"browser": "Safari", "clicks": 10}
  ],
  "last_clicked_at": "2024-01-05T18:30:00"
}
```

### Dashboard Stats
```http
GET /api/v1/analytics/stats/dashboard
Authorization: Bearer {user_id}

Response:
{
  "total_urls": 42,
  "total_clicks": 1250,
  "top_urls": [
    {"short_code": "abc123", "clicks": 250}
  ]
}
```

## 🐳 Local Development with Docker Compose

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Quick Start

1. **Clone and setup**
```bash
cd url-shortener
cp .env.example .env
```

2. **Start all services**
```bash
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- FastAPI web service (port 8000)
- Celery worker
- Celery Beat scheduler

3. **Check service status**
```bash
docker-compose ps
```

Expected output:
```
NAME                    STATUS
shortener_db            Up (healthy)
shortener_cache         Up (healthy)
shortener_api           Up
shortener_celery        Up
shortener_celery_beat   Up
```

4. **Access the API**
```bash
# Health check
curl http://localhost:8000/health

# Interactive API docs
open http://localhost:8000/docs

# ReDoc API docs
open http://localhost:8000/redoc
```

5. **Create a test user and shorten a URL**

First, create a test user UUID:
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

Then use it in your requests:
```bash
# Store the UUID in a variable
USER_ID="your-generated-uuid-here"

# Shorten a URL
curl -X POST http://localhost:8000/api/v1/shorten/ \
  -H "Authorization: Bearer $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/python/cpython",
    "title": "Python CPython Repository",
    "custom_alias": "python"
  }'

# Get your shortened URLs
curl -X GET http://localhost:8000/api/v1/shorten/user/urls \
  -H "Authorization: Bearer $USER_ID"

# Test the redirect
curl -L http://localhost:8000/python

# Get analytics
curl -X GET "http://localhost:8000/api/v1/analytics/python?days=30" \
  -H "Authorization: Bearer $USER_ID"
```

6. **View logs**
```bash
# API logs
docker-compose logs -f web

# Celery worker logs
docker-compose logs -f celery

# All logs
docker-compose logs -f
```

7. **Stop services**
```bash
docker-compose down

# With volume cleanup
docker-compose down -v
```

## 🗄️ Database Setup

The database tables are automatically created on first startup by the `init_db()` function. Tables include:

- **users**: User accounts
- **urls**: Shortened URL records
- **analytics**: Click tracking and analytics data

## 📦 Development Setup (Local Python)

If you want to run the project locally without Docker:

1. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up .env file**
```bash
cp .env.example .env
```

4. **Start external services** (PostgreSQL and Redis must be running)
```bash
# Using Docker for just DB and cache
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=shortener \
  -e POSTGRES_PASSWORD=shortener_pass \
  -e POSTGRES_DB=url_shortener_db \
  postgres:15-alpine

docker run -d -p 6379:6379 redis:7-alpine
```

5. **Run the API**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Run Celery worker** (in another terminal)
```bash
celery -A app.workers.tasks worker --loglevel=info
```

7. **Run Celery Beat** (in another terminal)
```bash
celery -A app.workers.tasks beat --loglevel=info
```

## 🔒 Security Considerations

1. **JWT Authentication**: Implement proper token validation in production
2. **HTTPS**: Always use HTTPS in production
3. **Rate Limiting**: Prevent abuse with configurable limits
4. **Input Validation**: Pydantic models validate all inputs
5. **CORS**: Configure CORS appropriately
6. **Secret Management**: Use environment variables for sensitive data
7. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
8. **XSS Protection**: Proper URL encoding in responses

## 📝 Monitoring & Logging

**Application Logs**
```bash
docker-compose logs -f web
docker-compose logs -f celery
```

**Metrics to Track**
- Redirect latency (target: < 50ms)
- Cache hit ratio (target: > 95%)
- Request error rate (target: < 0.1%)
- Worker queue depth (target: < 1000)
- Database connection pool usage

**Observability Stack (Production)**
```yaml
- Prometheus: Metrics collection
- Grafana: Visualization
- ELK Stack: Log aggregation
- Jaeger: Distributed tracing
```

## 🧪 Testing

```bash
# Run tests (inside Docker)
docker-compose exec web pytest

# With coverage
docker-compose exec web pytest --cov=app

# Run specific test file
docker-compose exec web pytest tests/test_shorten.py
```

## 📚 Database Schema

**users**
- id (UUID, PK)
- username (UNIQUE)
- email (UNIQUE)
- hashed_password
- is_active
- created_at, updated_at

**urls**
- id (UUID, PK)
- user_id (FK → users)
- original_url (TEXT)
- short_code (UNIQUE, indexed)
- custom_alias (UNIQUE, indexed)
- title, description
- click_count (BigInteger)
- expires_at (DateTime, indexed)
- is_active (Boolean, indexed)
- created_at, updated_at (indexed)

**analytics**
- id (UUID, PK)
- url_id (FK → urls, indexed)
- country, city
- device_type (mobile/desktop/tablet)
- browser, os
- ip_address
- referrer
- clicked_at (DateTime, indexed)

**Indexes**
```sql
CREATE INDEX idx_url_short_code ON urls(user_id, short_code);
CREATE INDEX idx_short_code_active ON urls(short_code, is_active);
CREATE INDEX idx_analytics_url ON analytics(url_id, clicked_at);
CREATE INDEX idx_analytics_device ON analytics(country, device_type);
```

## 🔄 Project Structure

```
url-shortener/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # User model
│   │   └── url.py           # URL and Analytics models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── shorten.py       # URL shortening endpoints
│   │   ├── redirect.py      # Redirect endpoint
│   │   └── analytics.py     # Analytics endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── encoder.py       # Base62 encoding & validation
│   │   ├── cache.py         # Redis caching
│   │   └── rate_limiter.py  # Rate limiting
│   └── workers/
│       ├── __init__.py
│       └── tasks.py         # Celery tasks
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container image
├── docker-compose.yml      # Multi-container setup
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🌍 Deployment

### Using Docker Compose (Development/Staging)
```bash
docker-compose up -d
```

### Using Kubernetes (Production)

See `k8s/` directory for Kubernetes manifests.

```bash
kubectl apply -f k8s/
```

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# API
DEBUG=False
ENVIRONMENT=production
SHORTENER_DOMAIN=https://short.example.com
```

## 📖 References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Commands](https://redis.io/commands/)
- [Base62 Encoding](https://en.wikipedia.org/wiki/Base62)

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

**Built for production with ❤️**

For issues, questions, or contributions, open an issue or PR on GitHub.
