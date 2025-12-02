# Redis Setup for Caching

Redis is used for caching to improve performance. It's **optional** - the app will work without it, but will be slower.

## Quick Setup (Local Development)

### Option 1: Install Redis Locally

**macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

**Docker:**
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Option 2: Use Redis Cloud (Free Tier)

1. Sign up at https://redis.com/try-free/
2. Create a free database
3. Copy the connection URL (looks like `redis://default:password@host:port`)

## Configuration

Add to your `.env` file:

```bash
# Local Redis
REDIS_URL=redis://localhost:6379/0

# Or Redis Cloud
REDIS_URL=rediss://default:password@redis-12345.c1.us-east-1-1.ec2.cloud.redislabs.com:12345
```

## What Gets Cached

- **User tier/subscription** (5 min TTL)
- **Keepa product data** (1 hour TTL)
- **Feature limits** (5 min TTL)
- **Analysis results** (optional, 15 min TTL)

## Verify Redis is Working

Check backend logs - you should see:
```
✅ Redis connected successfully
```

If Redis is not configured, you'll see:
```
⚠️  REDIS_URL not configured, caching disabled
```

The app will still work, just without caching.

## Production

For production, use:
- **Redis Cloud** (managed service)
- **AWS ElastiCache**
- **Upstash Redis** (serverless)
- **Railway Redis**

All provide free tiers for small apps.

