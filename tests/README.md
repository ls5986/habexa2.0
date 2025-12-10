# Habexa Production Tests

Automated test suite for verifying production readiness.

## Quick Start

1. **Ensure `.env.test` exists** in the project root with your credentials
2. **Run the tests:**
   ```bash
   python tests/production_test.py
   ```

## What Gets Tested

1. ✅ **Health Check** - API is responding
2. ✅ **Authentication** - Login works
3. ✅ **Redis Cache** - Cache is working (hit rate >40%)
4. ✅ **Stats Performance** - Cached responses <50ms
5. ✅ **Upload Preview** - CSV upload works (<5s)
6. ✅ **ASIN Lookup Status** - Endpoint works
7. ✅ **Products List** - Can fetch products

## Configuration

All configuration is in `.env.test`:

```env
BASE_URL=https://habexa-backend-w5u5.onrender.com/api/v1
TEST_EMAIL=your@email.com
TEST_PASSWORD=your_password
EXPECTED_REDIS_HIT_RATE_MIN=40
EXPECTED_STATS_CACHE_TIME_MAX=50
EXPECTED_UPLOAD_TIME_MAX=5000
```

## Test Reports

Test reports are automatically saved to `test_report_YYYYMMDD_HHMMSS.json` with:
- Timestamp
- Test results
- Duration
- Success rate

## Continuous Testing

Run after every deploy:

```bash
# After pushing to main
git push

# Wait for Render to deploy (3 minutes)

# Run tests
python tests/production_test.py
```

## Troubleshooting

### Authentication Failed
- Check email/password in `.env.test`
- Verify account exists in production

### Connection Refused
- Check backend is deployed: `https://habexa-backend-w5u5.onrender.com/health`
- Verify Render service is running

### Redis Not Connected
- Check `REDIS_URL` in Render environment variables
- Verify Redis service is running (green status)

## Dependencies

- `requests` - HTTP client
- `python-dotenv` - Environment variable loading

Install with:
```bash
pip install requests python-dotenv
```

