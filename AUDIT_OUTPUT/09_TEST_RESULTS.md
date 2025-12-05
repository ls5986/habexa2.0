# API Test Results

**Date:** 2025-12-05
**Status:** ⏳ Pending - Run `test_api.py` with valid token

## Instructions

1. Get auth token from browser:
   - Login to https://habexa-frontend.onrender.com
   - Open DevTools > Network
   - Copy `Authorization: Bearer <token>` from any API request

2. Update `test_api.py`:
   - Set `TOKEN = "your_token_here"`

3. Run test:
   ```bash
   cd /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT
   python3 test_api.py
   ```

4. Review results below (will be populated after running)

## Test Endpoints

| Status | Method | Path | Expected | Actual | Time |
|--------|--------|------|----------|--------|------|
| ⏳ | GET | `/health` | 200 | - | - |
| ⏳ | GET | `/api/v1/auth/me` | 200 | - | - |
| ⏳ | GET | `/api/v1/products` | 200 | - | - |
| ⏳ | GET | `/api/v1/products/stats` | 200 | - | - |
| ⏳ | GET | `/api/v1/deals` | 200 | - | - |
| ⏳ | GET | `/api/v1/deals/stats` | 200 | - | - |
| ⏳ | GET | `/api/v1/suppliers` | 200 | - | - |
| ⏳ | GET | `/api/v1/keepa/product/B07Y93SMRV` | 200 | - | - |
| ⏳ | GET | `/api/v1/keepa/tokens` | 200 | - | - |
| ⏳ | GET | `/api/v1/favorites` | 200 | - | - |
| ⏳ | GET | `/api/v1/favorites/count` | 200 | - | - |
| ⏳ | GET | `/api/v1/billing/subscription` | 200 | - | - |
| ⏳ | GET | `/api/v1/billing/usage` | 200 | - | - |
| ⏳ | GET | `/api/v1/billing/user/limits` | 200 | - | - |
| ⏳ | GET | `/api/v1/jobs` | 200 | - | - |
| ⏳ | GET | `/api/v1/sp-api/product/B07Y93SMRV/offers` | 200 | - | - |
| ⏳ | GET | `/api/v1/sp-api/product/B07Y93SMRV/fees?price=19.99` | 200 | - | - |
| ⏳ | GET | `/api/v1/sp-api/product/B07Y93SMRV/eligibility` | 200 | - | - |
| ⏳ | GET | `/api/v1/sp-api/product/B07Y93SMRV/sales-estimate` | 200 | - | - |

## Failures

_Will be populated after running tests_

---

**Note:** Tests require valid authentication token. Update `test_api.py` with your token before running.

