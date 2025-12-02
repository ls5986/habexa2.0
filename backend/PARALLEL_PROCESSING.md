# Parallel Processing with Multiple Celery Workers

## Overview

The batch analysis system now supports parallel processing with multiple Celery workers, distributed rate limiting, and atomic progress tracking. This can reduce processing time from ~33 minutes to ~4-5 minutes for 1000 products.

## Architecture

```
User clicks "Analyze 1000 Products"
           │
           ▼
    Create parent job
           │
           ▼
    Split into 8 chunks (125 products each)
           │
           ▼
    Queue 8 sub-tasks
           │
    ┌──────┼──────┬──────┬──────┬──────┬──────┬──────┐
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 Worker1 Worker2 Worker3 Worker4 Worker5 Worker6 Worker7 Worker8
 125     125     125     125     125     125     125     125
    │      │      │      │      │      │      │      │
    └──────┴──────┴──────┴──────┴──────┴──────┴──────┘
                         │
                         ▼
              All update same parent job
              (atomic progress tracking)
                         │
                         ▼
                   ~4-5 minutes total
```

## Components

### 1. Distributed Rate Limiter (`backend/app/tasks/rate_limiter.py`)
- Coordinates rate limiting across multiple workers using Redis
- SP-API: 8 requests/second
- Keepa: 5 requests/second
- Automatically falls back to simple sleep if Redis unavailable

### 2. Atomic Progress Tracking (`backend/app/tasks/progress.py`)
- Uses Redis for real-time counters across workers
- Syncs to Supabase periodically
- Handles cancellation checks

### 3. Parallel Chunk Processing (`backend/app/tasks/analysis.py`)
- `batch_analyze_parallel`: Main entry point, splits into chunks
- `analyze_chunk`: Processes one chunk (runs in parallel with other chunks)
- `finalize_batch`: Called after all chunks complete

## Running Multiple Workers

### Option 1: Single Worker with High Concurrency

```bash
# Start one worker with 8 concurrent tasks
celery -A app.core.celery_app worker \
  --loglevel=info \
  --concurrency=8 \
  --pool=prefork \
  --queues=default,analysis \
  -n worker@%h
```

### Option 2: Multiple Worker Processes

```bash
# Terminal 1
celery -A app.core.celery_app worker --concurrency=2 -n worker1@%h --queues=analysis &

# Terminal 2
celery -A app.core.celery_app worker --concurrency=2 -n worker2@%h --queues=analysis &

# Terminal 3
celery -A app.core.celery_app worker --concurrency=2 -n worker3@%h --queues=analysis &

# Terminal 4
celery -A app.core.celery_app worker --concurrency=2 -n worker4@%h --queues=analysis &
```

### Option 3: Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery_worker:
    build: ./backend
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=8 --pool=prefork --queues=analysis
    environment:
      - REDIS_URL=redis://redis:6379/0
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '4'
          memory: 2G
```

## Performance Expectations

| Workers | Rate Limit | Products/sec | 1000 products |
|---------|------------|--------------|---------------|
| 1       | 3/sec      | ~0.5         | ~33 min       |
| 4       | 8/sec      | ~2           | ~8 min        |
| 8       | 8/sec      | ~4           | ~4-5 min      |

**Note**: The bottleneck is SP-API rate limit (5-10/sec), not workers. 8 workers with distributed rate limiting = **~4-5 minutes for 1000 products**.

## Automatic Selection

The system automatically uses parallel processing for batches > 100 products:

- **> 100 products**: Uses `batch_analyze_parallel` (8 workers, distributed rate limiting)
- **≤ 100 products**: Uses `batch_analyze_products` (sequential, simpler)

## Configuration

### Number of Workers

Edit `WORKERS` in `backend/app/tasks/analysis.py`:

```python
WORKERS = 8  # Number of parallel chunks
```

### Rate Limits

Edit `backend/app/tasks/rate_limiter.py`:

```python
sp_api_limiter = DistributedRateLimiter("sp_api", requests_per_second=8)
keepa_limiter = DistributedRateLimiter("keepa", requests_per_second=5)
```

### Progress Sync Frequency

Edit `SYNC_EVERY` in `backend/app/tasks/analysis.py`:

```python
SYNC_EVERY = 10  # Sync progress to DB every N products
```

## Monitoring

### Check Job Progress

```bash
# Via API
GET /api/v1/jobs/{job_id}

# Response includes:
{
  "status": "processing",
  "progress": 45,
  "processed_items": 450,
  "total_items": 1000,
  "success_count": 445,
  "error_count": 5
}
```

### Check Redis Rate Limiter

```bash
redis-cli
> KEYS rate_limit:*
> ZRANGE rate_limit:sp_api 0 -1 WITHSCORES
```

### Check Celery Workers

```bash
celery -A app.core.celery_app inspect active
celery -A app.core.celery_app inspect stats
```

## Troubleshooting

### Workers Not Processing

1. Check Redis is running: `redis-cli ping` (should return `PONG`)
2. Check Celery workers are running: `celery -A app.core.celery_app inspect active`
3. Check queues: `celery -A app.core.celery_app inspect active_queues`

### Rate Limiting Not Working

1. Check Redis connection: `redis-cli ping`
2. Check rate limiter keys: `redis-cli KEYS rate_limit:*`
3. Check logs for "Rate limiter error" messages

### Progress Not Updating

1. Check Redis connection
2. Check `AtomicJobProgress.sync_to_db()` is being called
3. Check Supabase `jobs` table for updates

### Too Many API Errors

1. Reduce `requests_per_second` in rate limiter
2. Increase `WORKERS` to spread load
3. Check SP-API/Keepa API status

