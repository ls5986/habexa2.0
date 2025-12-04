# Product Analysis APIs - Complete Documentation

This document provides a comprehensive overview of all APIs, API keys, and endpoints used for product analysis in the Habexa platform.

---

## 📋 Table of Contents

1. [External APIs](#external-apis)
2. [API Keys & Credentials](#api-keys--credentials)
3. [Backend Endpoints](#backend-endpoints)
4. [Analysis Pipeline Flow](#analysis-pipeline-flow)
5. [Rate Limits & Optimization](#rate-limits--optimization)

---

## 🔌 External APIs

### 1. **Amazon SP-API (Seller Partner API)**

**Purpose:** Primary source for real-time pricing, fees, and product catalog data.

**Base URLs:**
- **North America:** `https://sellingpartnerapi-na.amazon.com`
- **Europe:** `https://sellingpartnerapi-eu.amazon.com`
- **Far East:** `https://sellingpartnerapi-fe.amazon.com`

**Endpoints Used:**

| Endpoint | Method | Purpose | Data Retrieved |
|----------|--------|---------|----------------|
| `/products/pricing/v0/competitivePrice` | GET | Get buy box price & seller count | Buy box price, offer counts |
| `/products/fees/v0/feesEstimate` | POST | Calculate FBA fees | Referral fee, FBA fee, total fees |
| `/catalog/v0/items/{asin}` | GET | Get catalog item details | Title, brand, images, category |
| `/catalog/v0/items/{asin}/variations` | GET | Get product variations | Child ASINs, variation data |

**Authentication:**
- Uses **app-level credentials** (shared for all users)
- LWA (Login with Amazon) OAuth 2.0
- Automatic token refresh (1-hour expiration)

**Rate Limits:**
- Competitive Pricing: ~0.5 requests/second
- Fees Estimate: ~0.5 requests/second
- Catalog Items: ~0.5 requests/second
- Batch size: **20 ASINs per request**

**Implementation:**
- Client: `backend/app/services/sp_api_client.py`
- Singleton pattern (shared instance)
- Automatic rate limiting with token bucket
- Error handling with Keepa fallback

---

### 2. **Keepa API**

**Purpose:** Catalog data, price history, BSR (Best Seller Rank), and sales estimates.

**Base URL:** `https://api.keepa.com`

**Endpoints Used:**

| Endpoint | Method | Purpose | Data Retrieved |
|----------|--------|---------|----------------|
| `/product` | GET | Get product data & price history | Title, brand, images, BSR, price history, sales rank drops |

**Parameters:**
- `key`: Keepa API key
- `domain`: 1 (US), 2 (UK), etc.
- `asin`: Comma-separated ASINs (max 100)
- `stats`: Days of history (30-365)
- `history`: 0 or 1 (include price history)
- `rating`: 1 (include rating data)

**Authentication:**
- API key in query parameter

**Rate Limits:**
- Batch size: **100 ASINs per request**
- Token-based pricing model
- No strict rate limit (but API has quotas)

**Implementation:**
- Client: `backend/app/services/keepa_client.py`
- Database caching: 24-hour cache in `keepa_cache` table
- Batch processing: Up to 100 ASINs per API call

**Data Retrieved:**
- Product title, brand, images
- Current price (Amazon and marketplace)
- Best Seller Rank (BSR)
- Category
- Sales rank drops (30/90/180 days)
- Rating and review count
- Variation count
- Amazon in-stock status

---

### 3. **ASIN Data API** (Optional/Unused)

**Purpose:** Alternative product data source (currently not used in production).

**Base URL:** `https://api.asindataapi.com/request`

**Status:** ⚠️ **Not actively used** - We use `batch_analyzer` instead which uses SP-API + Keepa.

**Implementation:**
- Client: `backend/app/services/asin_data_client.py`
- Only used if explicitly called (not in main analysis flow)

---

### 4. **OpenAI API** (Not for Product Analysis)

**Purpose:** Used for extracting products from Telegram messages (not for product analysis).

**Base URL:** `https://api.openai.com/v1`

**Used For:**
- Extracting product details from supplier messages
- Parsing ASINs, prices, MOQ from text

**Implementation:**
- Client: `backend/app/services/product_extractor.py`
- **Note:** Not used in the product analysis pipeline itself

---

## 🔑 API Keys & Credentials

### Required Environment Variables

#### 1. **Amazon SP-API Credentials**

```bash
# App-level credentials (for public data - works for all users)
SP_API_LWA_APP_ID=amzn1.application-oa2-client.xxxxx
SP_API_LWA_CLIENT_SECRET=xxxxx
SP_API_REFRESH_TOKEN=Atzr|xxxxx  # Permanent refresh token

# Legacy names (also supported)
SPAPI_LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxx
SPAPI_LWA_CLIENT_SECRET=xxxxx
SPAPI_REFRESH_TOKEN=Atzr|xxxxx

# AWS IAM (for request signing - optional, depends on SP-API setup)
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_REGION=us-east-1
SP_API_ROLE_ARN=arn:aws:iam::xxxxx:role/xxxxx
```

**How to Get:**
1. Create SP-API application in Amazon Seller Central
2. Generate LWA credentials
3. Self-authorize to get refresh token
4. Configure IAM role (if using AWS signature version 4)

**Required:** ✅ **Yes** - Primary data source for pricing and fees

---

#### 2. **Keepa API Key**

```bash
KEEPA_API_KEY=xxxxx  # Your Keepa API key
```

**How to Get:**
1. Sign up at https://keepa.com
2. Go to https://keepa.com/#!api
3. Subscribe to a plan (Individual: $19/mo, Business: $49/mo)
4. Copy API key from dashboard

**Required:** ✅ **Yes** - Primary source for catalog data and price history

**Cost:**
- Individual: 250,000 tokens/month ($19/mo)
- Business: 1,000,000 tokens/month ($49/mo)
- Tokens consumed per product lookup (varies by data requested)

---

#### 3. **OpenAI API Key** (Not for Product Analysis)

```bash
OPENAI_API_KEY=sk-xxxxx
```

**Purpose:** Telegram message extraction only (not product analysis)

**Required:** ❌ **No** - Only needed for Telegram integration

---

#### 4. **ASIN Data API Key** (Optional/Unused)

```bash
ASIN_DATA_API_KEY=xxxxx
```

**Status:** ⚠️ **Not used in production** - We use SP-API + Keepa instead

**Required:** ❌ **No**

---

### Database Tables Used for Caching

1. **`keepa_cache`**
   - Stores Keepa product data
   - 24-hour expiration
   - Reduces API calls

2. **`eligibility_cache`** (SP-API)
   - Stores product eligibility checks
   - 24-hour expiration

3. **`fee_cache`** (SP-API)
   - Stores fee calculations
   - 7-day expiration

---

## 🔗 Backend Endpoints

### Product Analysis Endpoints

#### 1. **Analyze Single Product**

```
POST /api/v1/analyze/single
```

**Request:**
```json
{
  "asin": "B07VRZ8TK3",
  "buy_cost": 15.99,
  "moq": 1,
  "supplier_id": "optional-uuid"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "asin": "B07VRZ8TK3",
  "status": "queued"
}
```

**Implementation:** `backend/app/api/v1/analysis.py`

---

#### 2. **Batch Analyze Products**

```
POST /api/v1/analyze/batch
```

**Request:**
```json
{
  "asins": ["B07VRZ8TK3", "B08N5WRWNW"],
  "buy_costs": [15.99, 22.50],
  "moq": 1
}
```

**Implementation:** `backend/app/api/v1/analysis.py`

---

#### 3. **Get Products/Deals**

```
GET /api/v1/products?stage=new&limit=100
```

**Query Parameters:**
- `stage`: `new`, `analyzing`, `reviewed`, `buy_list`, `ordered`
- `min_roi`: Minimum ROI filter
- `min_profit`: Minimum profit filter
- `search`: Search ASIN or title
- `supplier_id`: Filter by supplier
- `limit`: Results limit (default: 100)

**Response:**
```json
{
  "deals": [
    {
      "deal_id": "uuid",
      "asin": "B07VRZ8TK3",
      "title": "Product Title",
      "roi": 45.5,
      "profit": 8.99,
      "buy_cost": 15.99,
      "sell_price": 29.99,
      "stage": "reviewed",
      ...
    }
  ]
}
```

**Implementation:** `backend/app/api/v1/products.py`

---

#### 4. **Get Product Stats**

```
GET /api/v1/products/stats
```

**Response:**
```json
{
  "stages": {
    "new": 500,
    "analyzing": 10,
    "reviewed": 300,
    "buy_list": 50,
    "ordered": 100
  },
  "total": 960
}
```

**Implementation:** `backend/app/api/v1/products.py`

---

### Keepa API Endpoints (Backend)

#### 1. **Get Keepa Product Data**

```
GET /api/v1/keepa/product/{asin}?days=90
```

**Query Parameters:**
- `days`: History days (30-365, default: 90)

**Response:**
```json
{
  "asin": "B07VRZ8TK3",
  "title": "Product Title",
  "brand": "Brand Name",
  "image_url": "https://...",
  "bsr": 1250,
  "category": "Electronics",
  "current_price": 29.99,
  "price_history": [...],
  ...
}
```

**Implementation:** `backend/app/api/v1/keepa.py`

---

#### 2. **Get Sales Estimate**

```
GET /api/v1/keepa/sales-estimate/{asin}
```

**Implementation:** `backend/app/api/v1/keepa.py`

---

### SP-API Endpoints (Backend)

#### 1. **Get Competitive Pricing**

```
GET /api/v1/sp-api/product/{asin}/offers
```

**Implementation:** `backend/app/api/v1/sp_api.py`

---

#### 2. **Get Fee Estimate**

```
GET /api/v1/sp-api/product/{asin}/fees?price=29.99
```

**Query Parameters:**
- `price`: Sale price (required)
- `marketplace_id`: Marketplace ID (default: US)

**Response:**
```json
{
  "asin": "B07VRZ8TK3",
  "price": 29.99,
  "referralFee": 4.20,
  "fbaFee": 3.50,
  "totalFees": 7.70,
  "source": "sp-api"
}
```

**Implementation:** `backend/app/api/v1/sp_api.py`

---

#### 3. **Get Sales Estimate**

```
GET /api/v1/sp-api/product/{asin}/sales-estimate
```

**Implementation:** `backend/app/api/v1/sp_api.py`

---

## 🔄 Analysis Pipeline Flow

### Step-by-Step Process

1. **User initiates analysis** (Quick Analyze, Batch Analyze, or CSV upload)

2. **Backend creates Celery job** (`backend/app/tasks/analysis.py`)

3. **Batch Analyzer runs** (`backend/app/services/batch_analyzer.py`):

   **STEP 1: Keepa - Catalog Data (100 ASINs)**
   - Fetches title, brand, images, BSR, category
   - Checks database cache first
   - Batch API call: Up to 100 ASINs at once
   - Caches results for 24 hours

   **STEP 2: SP-API - Pricing (20 ASINs)**
   - Fetches buy box price and seller count
   - Batch API call: Up to 20 ASINs at once
   - Rate limited to ~0.5 req/sec

   **STEP 2B: Keepa Pricing Fallback**
   - If SP-API fails, uses Keepa current price
   - Ensures we always get pricing data if available

   **STEP 3: SP-API - Fees (20 ASINs)**
   - Calculates FBA fees for products with pricing
   - Batch API call: Up to 20 ASINs at once
   - Caches results for 7 days

4. **Profit Calculation** (`backend/app/services/profit_calculator.py`):
   - Net Profit = Sell Price - Buy Cost - All Fees
   - ROI = (Net Profit / Total Investment) * 100
   - Deal Score = Combined metric (ROI + sales rank + gating status)

5. **Save Results**:
   - Updates `products` table
   - Creates/updates `analyses` table
   - Updates `product_sources` table (for deals view)

6. **Frontend Updates**:
   - Polls job status
   - Displays results when complete

---

## ⚡ Rate Limits & Optimization

### Batch Sizes

| API | Batch Size | Calls Per 100 Products |
|-----|------------|------------------------|
| Keepa | 100 ASINs | 1 call |
| SP-API Pricing | 20 ASINs | 5 calls |
| SP-API Fees | 20 ASINs | 5 calls |
| **Total** | - | **11 API calls** |

### Caching Strategy

1. **Keepa Cache:**
   - Database cache: 24 hours
   - Reduces API calls by ~80-90%
   - Table: `keepa_cache`

2. **SP-API Fee Cache:**
   - Database cache: 7 days
   - Fees don't change frequently
   - Table: `fee_cache`

3. **SP-API Eligibility Cache:**
   - Database cache: 24 hours
   - Table: `eligibility_cache`

### Rate Limiting

1. **SP-API:**
   - Token bucket rate limiter
   - ~0.5 requests/second per endpoint
   - Automatic retry with backoff

2. **Keepa:**
   - No strict rate limit
   - Token-based quotas
   - Batch requests reduce API usage

### Optimization Techniques

1. **Batch Processing:**
   - Process multiple ASINs in single API call
   - Reduces overhead and improves speed

2. **Parallel Requests:**
   - Keepa and SP-API calls run in parallel
   - Uses `asyncio` for concurrent execution

3. **Cache-First Strategy:**
   - Check database cache before API call
   - Only fetch uncached products

4. **Graceful Degradation:**
   - If SP-API fails → Use Keepa fallback
   - If Keepa fails → Mark as partial success
   - Never completely fail if any data available

---

## 📊 Data Sources Summary

| Data Type | Primary Source | Fallback Source | Required |
|-----------|---------------|-----------------|----------|
| **Title** | Keepa | SP-API Catalog | ✅ |
| **Brand** | Keepa | SP-API Catalog | ✅ |
| **Images** | Keepa | SP-API Catalog | ✅ |
| **Buy Box Price** | SP-API | Keepa | ✅ |
| **FBA Fees** | SP-API | Calculated Estimate | ✅ |
| **BSR** | Keepa | SP-API Pricing | ✅ |
| **Category** | Keepa | SP-API Catalog | ✅ |
| **Price History** | Keepa | None | ❌ |
| **Sales Rank Drops** | Keepa | None | ❌ |
| **Seller Count** | SP-API | Keepa | ✅ |

---

## 🛠️ Service Files

### Core Services

1. **`backend/app/services/batch_analyzer.py`**
   - Main analysis orchestrator
   - Coordinates SP-API and Keepa calls
   - Handles batch processing

2. **`backend/app/services/sp_api_client.py`**
   - SP-API client (singleton)
   - Handles authentication and token refresh
   - Rate limiting and error handling

3. **`backend/app/services/keepa_client.py`**
   - Keepa API client (singleton)
   - Database caching
   - Batch processing (100 ASINs)

4. **`backend/app/services/profit_calculator.py`**
   - Profit and ROI calculations
   - Deal score algorithm

5. **`backend/app/tasks/analysis.py`**
   - Celery tasks for async analysis
   - Job management and progress tracking

---

## 🔐 Security & Credentials

### Environment Variables Location

- **Development:** `.env` file in project root
- **Production:** Render.com environment variables

### Credential Management

1. **SP-API:**
   - App-level credentials (shared)
   - Stored in environment variables
   - Automatic token refresh

2. **Keepa:**
   - Single API key
   - Stored in environment variables

3. **Database:**
   - Supabase credentials
   - Used for caching

---

## 📝 Summary

### Required APIs for Product Analysis

1. ✅ **Amazon SP-API** - Pricing, fees, catalog
2. ✅ **Keepa API** - Catalog data, price history, BSR

### Optional/Unused APIs

1. ❌ **ASIN Data API** - Not used in production
2. ❌ **OpenAI API** - Only for Telegram message extraction (not product analysis)

### Total API Calls Per Product Analysis

- **Keepa:** 1 call (batch of 100)
- **SP-API Pricing:** 5 calls (batch of 20)
- **SP-API Fees:** 5 calls (batch of 20)
- **Total:** ~11 calls for 100 products

### Cost Estimate

- **Keepa:** $19-49/month (based on plan)
- **SP-API:** Free (included with Amazon Seller account)
- **Total:** ~$19-49/month for unlimited analysis

---

## 🔗 Related Documentation

- `ANALYSIS_PIPELINE_FIXES.md` - Analysis resilience fixes
- `SP_API_AVAILABILITY_EXPLANATION.md` - Why SP-API might fail
- `KEEPA_SETUP_GUIDE.md` - Keepa setup instructions
- `SP_API_SETUP_GUIDE.md` - SP-API setup instructions

