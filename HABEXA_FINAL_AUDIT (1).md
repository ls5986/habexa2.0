# HABEXA AUTONOMOUS AUDIT & FIX SESSION
# SINGLE FILE - COPY ENTIRE CONTENTS INTO CURSOR

## ⛔ CRITICAL RULES - YOU MUST FOLLOW THESE

```
╔══════════════════════════════════════════════════════════════════╗
║                    MANDATORY EXECUTION RULES                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. DO NOT STOP FOR ANY REASON                                   ║
║  2. DO NOT ASK ANY QUESTIONS - ZERO EXCEPTIONS                   ║
║  3. DO NOT WAIT FOR USER INPUT                                   ║
║  4. DO NOT SAY "Would you like me to..."                         ║
║  5. DO NOT SAY "Should I proceed..."                             ║
║  6. DO NOT SAY "Let me know if..."                               ║
║  7. MAKE ASSUMPTIONS AND DOCUMENT THEM                           ║
║  8. IF SOMETHING FAILS, TRY DIFFERENT APPROACH (3x MAX)          ║
║  9. AFTER 3 FAILURES, DOCUMENT AND MOVE ON                       ║
║  10. KEEP GOING UNTIL ALL 6 PHASES ARE COMPLETE                  ║
║                                                                   ║
║  EXTERNAL SERVICES - DOCUMENT FOR MANUAL ACTION:                 ║
║  • Supabase SQL/migrations → Document SQL in 11_REMAINING.md     ║
║  • Render env variables → Document what's needed in 11_REMAINING ║
║  • Stripe config → Document in 11_REMAINING.md                   ║
║  • DO NOT try to run SQL on Supabase directly                    ║
║  • DO NOT try to modify Render dashboard                         ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🎯 MISSION

1. **AUDIT** - Map entire codebase, document every function
2. **TEST** - Test all API endpoints
3. **FIX** - Fix all broken functionality (3 attempts each)
4. **DOCUMENT** - Generate comprehensive technical docs

**PROJECT PATH:** `/Users/lindseystevens/habexa2.0`

---

## 📁 OUTPUT FILES TO CREATE

Create ALL files in `/Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/`:

```
AUDIT_OUTPUT/
├── SESSION_LOG.md
├── 01_SUMMARY.md
├── 02_ARCHITECTURE.md
├── 03_DATABASE.md
├── 04_API_ENDPOINTS.md
├── 05_SERVICES.md
├── 06_FRONTEND.md
├── 07_WORKFLOWS.md
├── 08_INTEGRATIONS.md
├── 09_TEST_RESULTS.md
├── 10_FIXES.md
└── 11_REMAINING.md
```

---

## 🔴 KNOWN ERRORS FROM PRODUCTION LOGS

These are REAL errors - fix them:

| Error | Log Message | Priority |
|-------|-------------|----------|
| Keepa 404 | `GET /api/v1/keepa/product/{asin} 404 Not Found` | CRITICAL |
| Keepa method missing | `'KeepaClient' object has no attribute 'get_product'` | CRITICAL |
| SP-API fees param | `SPAPIClient.get_fee_estimate() got an unexpected keyword argument 'is_fba'` | HIGH |
| Slow requests | `VERY SLOW REQUEST: took 2.905s` | MEDIUM |

---

# 🚀 PHASE 0: SETUP

```bash
# Create output directory
mkdir -p /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT

# Initialize log
cat > /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/SESSION_LOG.md << 'EOF'
# Habexa Audit Session
Started: $(date)

## Progress
| Phase | Status |
|-------|--------|
| 0: Setup | ✅ |
| 1: Discovery | 🔄 |
| 2: Backend | ⏳ |
| 3: Frontend | ⏳ |
| 4: Testing | ⏳ |
| 5: Fixing | ⏳ |
| 6: Docs | ⏳ |

## Log
EOF

# Verify project exists
ls -la /Users/lindseystevens/habexa2.0/backend/
ls -la /Users/lindseystevens/habexa2.0/frontend/
```

**IMMEDIATELY CONTINUE TO PHASE 1.**

---

# 🔍 PHASE 1: DISCOVERY

### 1.1 Map Backend

```bash
echo "## Backend Structure" >> /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/SESSION_LOG.md
find /Users/lindseystevens/habexa2.0/backend -name "*.py" -type f | wc -l
find /Users/lindseystevens/habexa2.0/backend -name "*.py" -type f | head -50
```

### 1.2 Map Frontend

```bash
echo "## Frontend Structure" >> /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/SESSION_LOG.md
find /Users/lindseystevens/habexa2.0/frontend/src -name "*.tsx" -o -name "*.ts" 2>/dev/null | grep -v node_modules | wc -l
```

### 1.3 Find Environment Variables

```bash
echo "## Environment Variables" >> /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/SESSION_LOG.md
grep -rh "os.getenv" /Users/lindseystevens/habexa2.0/backend --include="*.py" 2>/dev/null | grep -oE '"[A-Z_]+"' | tr -d '"' | sort -u
```

### 1.4 Find Config Files

```bash
cat /Users/lindseystevens/habexa2.0/backend/requirements.txt 2>/dev/null
cat /Users/lindseystevens/habexa2.0/frontend/package.json 2>/dev/null
```

**IMMEDIATELY CONTINUE TO PHASE 2.**

---

# 📊 PHASE 2: BACKEND AUDIT

### 2.1 Document ALL Database Models

```bash
# Find and read all model files
for f in $(find /Users/lindseystevens/habexa2.0/backend -path "*models*" -name "*.py" -type f); do
    echo "=== $f ===" 
    cat "$f"
done
```

**Create 03_DATABASE.md documenting each table:**
- Table name
- All columns with types
- Relationships
- Indexes

### 2.2 Document ALL API Endpoints

```bash
# Find all router files
for f in $(find /Users/lindseystevens/habexa2.0/backend -name "*.py" -exec grep -l "APIRouter\|@router" {} \;); do
    echo "=== $f ==="
    cat "$f"
done
```

**Create 04_API_ENDPOINTS.md documenting each endpoint:**
- Method + Path
- Parameters
- Response format
- Status (Working/Broken)

### 2.3 Document ALL Services

```bash
# Find and read all service files
for f in $(find /Users/lindseystevens/habexa2.0/backend -path "*services*" -name "*.py" -type f); do
    echo "=== $f ==="
    cat "$f"
done
```

**Create 05_SERVICES.md documenting each service class and method.**

### 2.4 Document Celery Tasks

```bash
grep -r "@celery_app.task\|@shared_task" /Users/lindseystevens/habexa2.0/backend --include="*.py" -A 20
```

### 2.5 Document Auth System

```bash
find /Users/lindseystevens/habexa2.0/backend -name "*.py" | xargs grep -l "get_current_user\|JWT\|Bearer" 2>/dev/null | xargs cat
```

**IMMEDIATELY CONTINUE TO PHASE 3.**

---

# 🎨 PHASE 3: FRONTEND AUDIT

### 3.1 Document Routes

```bash
grep -r "Route\|path=" /Users/lindseystevens/habexa2.0/frontend/src --include="*.tsx" 2>/dev/null | grep -v node_modules
```

### 3.2 Read Main Files

```bash
cat /Users/lindseystevens/habexa2.0/frontend/src/App.tsx 2>/dev/null
cat /Users/lindseystevens/habexa2.0/frontend/src/main.tsx 2>/dev/null
```

### 3.3 Read Page Components

```bash
find /Users/lindseystevens/habexa2.0/frontend/src -name "*Page*.tsx" | grep -v node_modules | xargs cat
```

### 3.4 Read API Client

```bash
cat /Users/lindseystevens/habexa2.0/frontend/src/services/api.ts 2>/dev/null || \
cat /Users/lindseystevens/habexa2.0/frontend/src/api/*.ts 2>/dev/null
```

### 3.5 Read Key Components

```bash
find /Users/lindseystevens/habexa2.0/frontend/src -name "*Product*" -name "*.tsx" | grep -v node_modules | xargs cat
find /Users/lindseystevens/habexa2.0/frontend/src -name "*Detail*" -name "*.tsx" | grep -v node_modules | xargs cat
```

**Create 06_FRONTEND.md documenting all components.**

**IMMEDIATELY CONTINUE TO PHASE 4.**

---

# 🧪 PHASE 4: API TESTING

### 4.1 Create Test Script

Create `/Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/test_api.py`:

```python
#!/usr/bin/env python3
import urllib.request
import urllib.error
import json
import ssl
from datetime import datetime

BASE_URL = "https://habexa-backend-w5u5.onrender.com"

# GET A FRESH TOKEN:
# 1. Go to https://habexa-frontend.onrender.com
# 2. Login
# 3. Open DevTools > Network
# 4. Copy Authorization header from any API call
TOKEN = "PASTE_YOUR_TOKEN_HERE"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

ENDPOINTS = [
    ("GET", "/health", 200),
    ("GET", "/api/v1/auth/me", 200),
    ("GET", "/api/v1/products", 200),
    ("GET", "/api/v1/products/stats", 200),
    ("GET", "/api/v1/deals", 200),
    ("GET", "/api/v1/deals/stats", 200),
    ("GET", "/api/v1/suppliers", 200),
    ("GET", "/api/v1/keepa/health", 200),
    ("GET", "/api/v1/keepa/product/B07Y93SMRV", 200),
    ("GET", "/api/v1/favorites", 200),
    ("GET", "/api/v1/favorites/count", 200),
    ("GET", "/api/v1/billing/subscription", 200),
    ("GET", "/api/v1/billing/usage", 200),
    ("GET", "/api/v1/billing/user/limits", 200),
    ("GET", "/api/v1/jobs", 200),
    ("GET", "/api/v1/sp-api/product/B07Y93SMRV/offers", 200),
    ("GET", "/api/v1/sp-api/product/B07Y93SMRV/fees?price=19.99", 200),
]

def test(method, path, expected):
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, headers=headers, method=method)
        start = datetime.now()
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as resp:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            status = "✅" if resp.status == expected else "⚠️"
            return status, resp.status, round(elapsed), None
    except urllib.error.HTTPError as e:
        status = "✅" if e.code == expected else "❌"
        return status, e.code, 0, str(e)
    except Exception as e:
        return "❌", "ERR", 0, str(e)

def main():
    print("=" * 60)
    print("HABEXA API TESTS")
    print("=" * 60)
    
    results = []
    for method, path, expected in ENDPOINTS:
        status, code, ms, err = test(method, path, expected)
        results.append((method, path, expected, status, code, ms, err))
        print(f"{status} {method} {path} -> {code} ({ms}ms)")
        if err:
            print(f"   Error: {err[:80]}")
    
    passed = sum(1 for r in results if r[3] == "✅")
    print(f"\nRESULTS: {passed}/{len(results)} passed")
    
    # Write report
    with open("/Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/09_TEST_RESULTS.md", "w") as f:
        f.write("# API Test Results\n\n")
        f.write(f"**Date:** {datetime.now()}\n")
        f.write(f"**Passed:** {passed}/{len(results)}\n\n")
        f.write("| Status | Method | Path | Expected | Actual | Time |\n")
        f.write("|--------|--------|------|----------|--------|------|\n")
        for method, path, expected, status, code, ms, err in results:
            f.write(f"| {status} | {method} | `{path}` | {expected} | {code} | {ms}ms |\n")
        
        f.write("\n## Failures\n\n")
        for method, path, expected, status, code, ms, err in results:
            if status != "✅":
                f.write(f"### {method} {path}\n")
                f.write(f"- Expected: {expected}, Got: {code}\n")
                if err:
                    f.write(f"- Error: {err}\n")
                f.write("\n")

if __name__ == "__main__":
    main()
```

### 4.2 Run Tests

```bash
cd /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT
python3 test_api.py
```

**IF TOKEN ERROR:** Document and continue. The code analysis is more important.

**IMMEDIATELY CONTINUE TO PHASE 5.**

---

# 🔧 PHASE 5: FIX ALL ISSUES

## Fix Strategy

```
FOR EACH ISSUE:
├── Attempt 1: Apply fix, test
│   └── If works → Document, continue
│   └── If fails → Attempt 2
├── Attempt 2: Try alternative, test
│   └── If works → Document, continue
│   └── If fails → Attempt 3
├── Attempt 3: Try different approach, test
│   └── If works → Document, continue
│   └── If fails → Document "NEEDS MANUAL FIX", continue
└── NEVER STOP - ALWAYS CONTINUE TO NEXT ISSUE
```

---

## 🔴 ISSUE 1: Keepa Endpoint Returns 404

**ERROR:** `GET /api/v1/keepa/product/B0CV4FN2DN?days=90 HTTP/1.1" 404 Not Found`

**DIAGNOSIS:**
```bash
# Check if keepa router exists
find /Users/lindseystevens/habexa2.0/backend -name "*keepa*" -type f

# Check if router is registered
grep -r "keepa" /Users/lindseystevens/habexa2.0/backend/app/api --include="*.py"
grep -r "include_router" /Users/lindseystevens/habexa2.0/backend/app/api --include="*.py" | grep -i keepa
```

**FIX - Create/Fix Keepa Router:**

```python
# File: backend/app/api/v1/keepa.py

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keepa", tags=["keepa"])

@router.get("/health")
async def keepa_health():
    """Check Keepa status."""
    try:
        from app.services.keepa_client import KeepaClient
        client = KeepaClient()
        return {"configured": client.is_configured(), "status": "ok"}
    except Exception as e:
        return {"configured": False, "status": "error", "error": str(e)}

@router.get("/product/{asin}")
async def get_keepa_product(
    asin: str,
    days: int = Query(default=90, ge=1, le=365),
    current_user = Depends(get_current_user)
):
    """Get Keepa data for product."""
    logger.info(f"Keepa request for {asin}")
    
    try:
        from app.services.keepa_client import KeepaClient
        client = KeepaClient()
        
        if not client.is_configured():
            return {"asin": asin, "error": "Keepa not configured", "stats": {}, "price_history": [], "rank_history": []}
        
        # Try get_product_data or get_product (handle both method names)
        if hasattr(client, 'get_product_data'):
            data = await client.get_product_data(asin, days)
        elif hasattr(client, 'get_product'):
            data = await client.get_product(asin, days)
        else:
            return {"asin": asin, "error": "KeepaClient missing get_product method", "stats": {}, "price_history": [], "rank_history": []}
        
        if not data:
            return {"asin": asin, "error": "No data found", "stats": {}, "price_history": [], "rank_history": []}
        
        return data
        
    except Exception as e:
        logger.error(f"Keepa error: {e}")
        return {"asin": asin, "error": str(e), "stats": {}, "price_history": [], "rank_history": []}
```

**FIX - Register Router (find main API file and add):**

```python
# Add to backend/app/api/v1/__init__.py or main.py:
from app.api.v1.keepa import router as keepa_router
api_router.include_router(keepa_router)
```

**VERIFICATION:**
```bash
curl -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/keepa/health"
# Should return {"configured": true/false, "status": "ok"}
```

---

## 🔴 ISSUE 2: KeepaClient Missing get_product Method

**ERROR:** `'KeepaClient' object has no attribute 'get_product'`

**DIAGNOSIS:**
```bash
# Find KeepaClient class
grep -r "class KeepaClient" /Users/lindseystevens/habexa2.0/backend --include="*.py"

# Check what methods it has
grep -A 50 "class KeepaClient" /Users/lindseystevens/habexa2.0/backend/app/services/keepa_client.py 2>/dev/null
```

**FIX - Add missing method to KeepaClient:**

```python
# Add to KeepaClient class:

async def get_product(self, asin: str, days: int = 90):
    """Get product data from Keepa. Alias for get_product_data."""
    return await self.get_product_data(asin, days)

async def get_product_data(self, asin: str, days: int = 90):
    """Fetch product data from Keepa API."""
    if not self.is_configured():
        return None
    
    try:
        import keepa
        api = keepa.Keepa(self.api_key)
        products = api.query(asin, domain='US', history=True, days=days)
        
        if not products:
            return None
        
        product = products[0]
        
        return {
            "asin": asin,
            "title": product.get("title"),
            "brand": product.get("brand"),
            "stats": {
                "current_price": self._get_price(product),
                "current_rank": self._get_rank(product),
                "fba_sellers": product.get("fbaSellerCount"),
                "fbm_sellers": product.get("fbmSellerCount"),
            },
            "price_history": self._parse_history(product, 0, days),
            "rank_history": self._parse_history(product, 3, days),
        }
    except Exception as e:
        logger.error(f"Keepa error: {e}")
        return None

def _get_price(self, product):
    csv = product.get("csv", [])
    if csv and len(csv) > 0 and csv[0] and len(csv[0]) >= 2:
        price = csv[0][-1]
        return price / 100.0 if price and price > 0 else None
    return None

def _get_rank(self, product):
    csv = product.get("csv", [])
    if csv and len(csv) > 3 and csv[3] and len(csv[3]) >= 2:
        rank = csv[3][-1]
        return int(rank) if rank and rank > 0 else None
    return None

def _parse_history(self, product, index, days):
    from datetime import datetime, timedelta
    history = []
    csv = product.get("csv", [])
    if not csv or len(csv) <= index or not csv[index]:
        return history
    
    data = csv[index]
    keepa_epoch = datetime(2011, 1, 1)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    for i in range(0, len(data) - 1, 2):
        ts, val = data[i], data[i + 1]
        if ts is None or val is None or val <= 0:
            continue
        dt = keepa_epoch + timedelta(minutes=ts)
        if dt < cutoff:
            continue
        history.append({
            "date": dt.isoformat(),
            "value": val / 100.0 if index == 0 else val
        })
    return history
```

---

## 🔴 ISSUE 3: SP-API Fees Wrong Parameter

**ERROR:** `SPAPIClient.get_fee_estimate() got an unexpected keyword argument 'is_fba'`

**DIAGNOSIS:**
```bash
# Find where is_fba is being passed
grep -r "is_fba" /Users/lindseystevens/habexa2.0/backend --include="*.py"

# Check get_fee_estimate signature
grep -A 10 "def get_fee_estimate" /Users/lindseystevens/habexa2.0/backend/app/services/sp_api_client.py
```

**FIX - Either update method or fix caller:**

**Option A - Update the method to accept is_fba:**
```python
async def get_fee_estimate(self, asin: str, price: float, is_fba: bool = True) -> dict:
    """Get fee estimate. is_fba determines fulfillment channel."""
    # Implementation using is_fba to set fulfillment type
    pass
```

**Option B - Remove is_fba from caller:**
```bash
# Find the caller and remove the is_fba parameter
grep -r "get_fee_estimate.*is_fba" /Users/lindseystevens/habexa2.0/backend --include="*.py"
# Edit to remove is_fba=True
```

---

## 🔴 ISSUE 4: Favorites Endpoint Missing/Broken

**DIAGNOSIS:**
```bash
# Check if favorites router exists
find /Users/lindseystevens/habexa2.0/backend -name "*favorite*" -type f
grep -r "favorites" /Users/lindseystevens/habexa2.0/backend/app/api --include="*.py"
```

**FIX - Create Favorites Router:**

```python
# File: backend/app/api/v1/favorites.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.db.session import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteCreate(BaseModel):
    product_id: UUID
    notes: Optional[str] = None


@router.get("")
async def list_favorites(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List user's favorites."""
    # Query favorites from DB
    return []


@router.post("")
async def add_favorite(
    data: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add to favorites."""
    logger.info(f"Adding favorite: {data.product_id}")
    return {"message": "Added", "product_id": str(data.product_id)}


@router.delete("/{product_id}")
async def remove_favorite(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove from favorites."""
    return {"message": "Removed"}


@router.get("/check/{product_id}")
async def check_favorite(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Check if favorited."""
    return {"is_favorite": False}


@router.get("/count")
async def count_favorites(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Count favorites."""
    return {"count": 0}
```

**Register router in main API file.**

---

## 🟡 ISSUE 5: UPC Normalization Missing

**DIAGNOSIS:**
```bash
grep -r "normalize_upc\|pad.*upc\|zfill" /Users/lindseystevens/habexa2.0/backend --include="*.py"
```

**FIX - Add normalization function:**

```python
def normalize_upc(upc: str) -> Optional[str]:
    """Normalize UPC to valid format."""
    if not upc:
        return None
    
    clean = ''.join(c for c in str(upc) if c.isdigit())
    
    if len(clean) == 11:
        return clean.zfill(12)  # Pad leading zero
    elif len(clean) in (12, 13, 14):
        return clean
    else:
        return None
```

---

## 🟡 ISSUE 6: "drops in 30d" Bug

**DIAGNOSIS:**
```bash
grep -r "drops in 30d\|drops" /Users/lindseystevens/habexa2.0/frontend/src --include="*.tsx"
```

**FIX:** Replace placeholder with actual data check:
```typescript
// Change from:
const salesText = data?.sales || "drops in 30d";

// To:
const salesText = data?.estimated_sales != null 
  ? `${data.estimated_sales.toLocaleString()} units/mo`
  : "—";
```

---

## 🟡 ISSUE 7: Slow API Requests (2-3 seconds)

**FIX - Add caching:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

_cache = {}

def get_cached(key: str, ttl_seconds: int = 300):
    if key in _cache:
        value, timestamp = _cache[key]
        if datetime.now() - timestamp < timedelta(seconds=ttl_seconds):
            return value
    return None

def set_cached(key: str, value):
    _cache[key] = (value, datetime.now())
```

**DOCUMENT FOR MANUAL ACTION - Database indexes:**

Add to `11_REMAINING.md`:
```markdown
## Manual Action Required: Database Indexes

Run this SQL in Supabase Dashboard → SQL Editor:

```sql
CREATE INDEX IF NOT EXISTS idx_deals_user_id ON deals(user_id);
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin);
```

This will speed up the slow queries (currently 0.8-2.9 seconds).
```

---

**DOCUMENT ALL FIXES IN 10_FIXES.md**

**IMMEDIATELY CONTINUE TO PHASE 6.**

---

# 📝 PHASE 6: GENERATE DOCUMENTATION

### Create 01_SUMMARY.md

```markdown
# Habexa - Executive Summary

## Overview
Product analysis platform for Amazon sellers.

## Tech Stack
- Frontend: React, TypeScript, Material-UI, Vite
- Backend: Python, FastAPI, SQLAlchemy
- Database: PostgreSQL (Supabase)
- Auth: Supabase Auth
- Queue: Celery + Redis
- Hosting: Render.com
- External: Amazon SP-API, Keepa, Stripe

## Status

| Feature | Status |
|---------|--------|
| Auth | [status] |
| Products | [status] |
| Deals | [status] |
| Analysis | [status] |
| Favorites | [status] |
| Billing | [status] |

## Test Results
Passed: X/Y

## Fixes Applied
[list]

## Remaining Issues
[list]
```

### Create All Other Docs

Fill in all documentation files based on discoveries:
- 02_ARCHITECTURE.md - System diagram
- 03_DATABASE.md - All tables
- 04_API_ENDPOINTS.md - All endpoints
- 05_SERVICES.md - All services
- 06_FRONTEND.md - All components
- 07_WORKFLOWS.md - User flows
- 08_INTEGRATIONS.md - External APIs
- 10_FIXES.md - What was fixed
- 11_REMAINING.md - What needs manual work

---

# ✅ SESSION COMPLETE

When done, output:

```
════════════════════════════════════════════════════════════════
                    HABEXA AUDIT COMPLETE
════════════════════════════════════════════════════════════════

📁 Files created in /Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/

📊 Summary:
- Files analyzed: X
- Endpoints tested: X
- Tests passed: X/Y
- Fixes applied: X
- Issues remaining: X

Read 01_SUMMARY.md for overview.
Read 11_REMAINING.md for manual tasks.
════════════════════════════════════════════════════════════════
```

---

# 📋 WHAT GOES IN 11_REMAINING.md

Document these for manual action (DO NOT attempt to do them):

```markdown
# Manual Actions Required

## 1. Supabase SQL (Run in SQL Editor)
[Any SQL that needs to be run - indexes, migrations, etc.]

## 2. Render Environment Variables
[Any env vars that are missing or need to be added]
- KEEPA_API_KEY - Check if set in habexa-backend
- SP_API credentials - Check if set in habexa-celery-worker

## 3. Render Deployment
[If code changes need redeployment]

## 4. Stripe Configuration
[Any Stripe webhook or config changes]

## 5. Code Changes That Couldn't Be Applied
[If file permissions or other issues prevented changes]
```

---

# ⚠️ FINAL REMINDER

```
DO NOT STOP UNTIL PHASE 6 IS COMPLETE.
DO NOT ASK ANY QUESTIONS.
IF SOMETHING FAILS, TRY DIFFERENT APPROACH.
AFTER 3 FAILURES, DOCUMENT AND MOVE ON.
GENERATE ALL OUTPUT FILES.
```

**BEGIN EXECUTION NOW.**
