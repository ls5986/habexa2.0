# Existing Codebase Audit Report

## Models/Tables Found

### Core Tables

**`products` table:**
- `id` (UUID, PK)
- `user_id` (UUID, FK to profiles)
- `asin` (VARCHAR(10), NOT NULL)
- `title`, `image_url`, `category`, `brand_name` (TEXT)
- `sell_price`, `fees_total` (DECIMAL(10,2))
- `bsr` (INTEGER - Best Seller Rank)
- `seller_count`, `fba_seller_count` (INTEGER)
- `amazon_sells` (BOOLEAN)
- `analysis_id` (UUID, FK to analyses)
- `status` (TEXT: 'pending', 'analyzed', 'error')
- `created_at`, `updated_at` (TIMESTAMPTZ)
- **Unique constraint:** `(user_id, asin, supplier_id)` - allows same ASIN from different suppliers

**`product_sources` table:**
- `id` (UUID, PK)
- `product_id` (UUID, FK to products)
- `supplier_id` (UUID, FK to suppliers)
- `buy_cost` (DECIMAL(10,2))
- `moq` (INTEGER, default 1)
- `source` (TEXT: 'telegram', 'csv', 'manual', 'quick_analyze')
- `source_detail` (TEXT)
- `stage` (TEXT: 'new', 'analyzing', 'reviewed', 'buy_list', 'ordered')
- `notes` (TEXT)
- `is_active` (BOOLEAN)
- `created_at`, `updated_at` (TIMESTAMPTZ)
- **Unique constraint:** `(product_id, supplier_id)`

**`analyses` table:**
- `id` (UUID, PK)
- `user_id` (UUID, FK to profiles)
- `supplier_id` (UUID, FK to suppliers, nullable)
- `asin` (TEXT, NOT NULL)
- `deal_id` (UUID, FK to deals, nullable)
- `analysis_data` (JSONB, required)
- **Product info:** `title`, `brand`, `image_url` (TEXT)
- **Pricing:** `sell_price` (DECIMAL(10,2))
- **Fees:** `fees_total`, `fees_referral`, `fees_fba` (DECIMAL(10,2))
- **Market data:** `seller_count`, `fba_seller_count` (INTEGER), `amazon_sells` (BOOLEAN)
- **Keepa data:** `category`, `sales_drops_30/90/180`, `variation_count`, `amazon_in_stock`, `rating`, `review_count`
- **Source tracking:** `price_source` (TEXT: 'sp-api', 'keepa', 'unknown')
- `created_at`, `updated_at` (TIMESTAMPTZ)
- **Unique constraint:** `(user_id, supplier_id, asin)`

**`deals` table (legacy, still exists):**
- `id` (UUID, PK)
- `user_id`, `message_id`, `supplier_id` (UUID, FKs)
- `asin`, `title`, `brand`, `category`, `image_url` (TEXT)
- `buy_cost`, `sell_price`, `lowest_fba_price`, `lowest_fbm_price` (DECIMAL(10,2))
- `fba_fee`, `referral_fee`, `prep_cost`, `inbound_shipping` (DECIMAL(10,2))
- `net_profit`, `roi`, `profit_margin` (DECIMAL)
- `num_fba_sellers`, `num_fbm_sellers` (INTEGER)
- `sales_rank`, `estimated_monthly_sales` (INTEGER)
- `gating_status` (TEXT)
- `deal_score` (CHAR(1): 'A', 'B', 'C', 'D', 'F')
- `status` (TEXT: 'pending', 'analyzed', 'saved', 'ordered', 'dismissed')
- `analyzed_at`, `created_at`, `updated_at` (TIMESTAMPTZ)

**Views:**
- `product_deals` - Flattened view joining `products` + `product_sources` + `suppliers` with calculated fields (net_profit, roi, profit_margin)

### Other Tables
- `profiles` - User profiles
- `suppliers` - Supplier information
- `brands` - Brand tracking for ungating
- `orders` - Purchase orders
- `watchlist` - Product watchlist
- `notifications` - User notifications
- `subscriptions` - Stripe subscription data
- `amazon_connections` - User SP-API OAuth connections
- `eligibility_cache` - Cached eligibility results
- `fee_cache` - Cached fee estimates
- `keepa_cache` - Cached Keepa API responses

---

## SP-API Integration

**Status:** ✅ **FULLY IMPLEMENTED**

**Files:**
- `backend/app/services/sp_api_client.py` (1043 lines) - Main SP-API client
- `backend/app/api/v1/sp_api.py` - SP-API endpoints
- `backend/app/services/amazon_oauth.py` - OAuth flow

**Endpoints Implemented:**

**Backend API Endpoints (`/api/v1/sp-api/`):**
1. `GET /product/{asin}/offers` - Get all offers/sellers
2. `GET /product/{asin}/fees` - Get FBA fees estimate
3. `GET /product/{asin}/eligibility` - Check seller eligibility
4. `GET /product/{asin}/sales-estimate` - Get sales rank and monthly sales estimate

**SP-API Client Methods:**
1. `get_competitive_pricing(asin)` - Single ASIN pricing
2. `get_competitive_pricing_batch(asins)` - **Batch of up to 20 ASINs** ✅
3. `get_fee_estimate(user_id, asin, price)` - Single fee estimate
4. `get_fees_estimate_batch(items)` - **Batch of up to 20 items** ✅
5. `get_catalog_item(asin)` - Single catalog item
6. `get_catalog_items_batch(asins)` - **Parallel batch (semaphore-based)** ✅
7. `search_catalog_items(identifiers, identifiers_type="UPC")` - **UPC to ASIN conversion** ✅
8. `get_eligibility(asin, seller_id)` - Seller eligibility check

**Batch Support:** ✅ **YES**
- `get_competitive_pricing_batch()` - Up to 20 ASINs per call
- `get_fees_estimate_batch()` - Up to 20 items per call
- `get_catalog_items_batch()` - Parallel requests with semaphore (not true batch, but optimized)
- `search_catalog_items()` - Supports multiple identifiers (UPC/EAN/GTIN)

**Rate Limiting:**
- Token bucket rate limiter implemented (`app/services/rate_limiter.py`)
- Simple rate limiter fallback (0.4s min interval = ~2.5 req/sec)
- Distributed rate limiter support (`app/tasks/rate_limiter.py`)

**Authentication:**
- Hybrid approach: App credentials for public data, user credentials for seller-specific data
- OAuth flow for user connections
- Token caching and refresh

---

## Analysis System

**Current Approach:** ✅ **BATCH PROCESSING**

**Task File:** `backend/app/tasks/analysis.py` (693 lines)

**Main Tasks:**
1. `analyze_single_product()` - Single product analysis (uses batch analyzer internally)
2. `batch_analyze_products()` - Main batch analysis task
3. `analyze_batch_chunk()` - Processes chunks in parallel

**Batch Analyzer:** `backend/app/services/batch_analyzer.py`
- **Keepa:** Batch of 100 ASINs per API call
- **SP-API Pricing:** Batch of 20 ASINs per API call
- **SP-API Fees:** Batch of 20 items per API call
- **Fallback:** Keepa pricing if SP-API fails

**What It Saves:**

**To `analyses` table:**
- `user_id`, `asin`, `supplier_id`
- `sell_price`, `fees_total`, `fees_referral`, `fees_fba`
- `seller_count`, `price_source`
- `title`, `brand`, `image_url`
- `category`, `sales_drops_30/90/180`, `variation_count`, `amazon_in_stock`, `rating`, `review_count`
- `analysis_data` (JSONB, currently empty `{}`)

**To `products` table:**
- `title`, `image_url`, `brand_name`
- `sell_price`, `fees_total` (if pricing available)
- `bsr` (Best Seller Rank)
- `seller_count`
- `analysis_id` (link to analyses)
- `status` ('analyzed' or 'error')

**To `product_sources` table:**
- Updated `stage` to 'reviewed' when analysis completes

**Current Flow:**
1. Products created via CSV upload or manual entry
2. Celery task `batch_analyze_products` called with list of product IDs
3. Extracts ASINs, calls `batch_analyzer.analyze_products(asins)`
4. Batch analyzer:
   - Step 1: Keepa batch (100 ASINs) for catalog data
   - Step 2: SP-API pricing batch (20 ASINs)
   - Step 2B: Keepa pricing fallback if SP-API fails
   - Step 3: SP-API fees batch (20 ASINs)
5. Results saved to `analyses` and `products` tables
6. Product `status` updated to 'analyzed' or 'error'

**Success Criteria:**
- Product marked as "success" if it has:
  - Sell price (full success), OR
  - Catalog data (title/brand/image) even without pricing (partial success)

---

## Services

**Core Services:**
- `sp_api_client.py` - SP-API client with batch support
- `keepa_client.py` - Keepa API client with batch support (100 ASINs)
- `batch_analyzer.py` - Orchestrates Keepa + SP-API batch calls
- `upc_converter.py` - UPC to ASIN conversion using SP-API catalog search
- `profit_calculator.py` - Profitability calculations
- `supabase_client.py` - Supabase database client
- `redis_client.py` - Redis caching (with `@cached` decorator)
- `rate_limiter.py` - Token bucket rate limiter
- `stripe_service.py` - Stripe integration
- `telegram_service.py` - Telegram integration
- `email_service.py` - Email sending
- `openai_extractor.py` - OpenAI for message extraction
- `product_extractor.py` - Product extraction from messages
- `asin_analyzer.py` - ASIN analysis utilities
- `asin_data_client.py` - ASIN Data API client (optional)
- `keepa_analysis_service.py` - Keepa-specific analysis logic
- `feature_gate.py` - Feature gating logic
- `permissions_service.py` - Permission checks
- `amazon_oauth.py` - Amazon OAuth flow
- `file_processor.py` - File processing utilities

---

## Environment/Config

**API Credentials Configured:**

**SP-API:**
- `SP_API_LWA_APP_ID` - App-level LWA App ID
- `SP_API_LWA_CLIENT_SECRET` - App-level LWA Client Secret
- `SP_API_REFRESH_TOKEN` - App-level refresh token
- Legacy names also supported: `SPAPI_LWA_CLIENT_ID`, `SPAPI_LWA_CLIENT_SECRET`, `SPAPI_REFRESH_TOKEN`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - For request signing (if needed)
- `MARKETPLACE_ID` - Default: "ATVPDKIKX0DER" (US)

**Keepa:**
- `KEEPA_API_KEY` - ✅ **REQUIRED** for analysis workers
- `KEEPA_CACHE_HOURS` - Cache duration (default: 24 hours)
- `KEEPA_BATCH_SIZE` - Batch size limit (default: 100)

**Other APIs:**
- `ASIN_DATA_API_KEY` - Optional (only if using asin_data_client)
- `OPENAI_API_KEY` - Required for telegram worker
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` - Telegram integration

**Config Settings:**
- `CELERY_WORKERS` - Number of parallel workers (default: 8)
- `CELERY_PROCESS_BATCH_SIZE` - Batch size for processing (default: 100, matches Keepa)
- `SP_API_BATCH_SIZE` - SP-API batch size limit (default: 20)
- `KEEPA_BATCH_SIZE` - Keepa batch size limit (default: 100)

---

## Missing for MASTER_WORKFLOW

Based on `MASTER_WORKFLOW.md` requirements:

### ✅ Already Implemented:
- [x] Batch SP-API pricing calls (20 ASINs)
- [x] Batch SP-API fees calls (20 items)
- [x] Batch Keepa calls (100 ASINs)
- [x] UPC to ASIN conversion (SP-API catalog search)
- [x] Keepa pricing fallback
- [x] Analysis pipeline with Celery tasks
- [x] Database tables (`products`, `analyses`, `product_sources`)
- [x] Rate limiting

### ❌ Missing/Needs Implementation:

1. **Two-Stage Analysis Pipeline:**
   - [ ] **Stage 1:** Quick profitability filter (fast, low-cost APIs)
   - [ ] **Stage 2:** Deep analysis (only for profitable products)
   - Currently: All products get full analysis regardless of profitability

2. **Stage 1 Quick Filter:**
   - [ ] Use Keepa only (no SP-API) for initial screening
   - [ ] Calculate basic ROI/profit from Keepa data
   - [ ] Filter products that don't meet minimum threshold
   - [ ] Only pass profitable products to Stage 2

3. **Stage 2 Deep Analysis:**
   - [ ] SP-API pricing (batch of 20)
   - [ ] SP-API fees (batch of 20)
   - [ ] SP-API eligibility check (if user connected)
   - [ ] Additional Keepa data (sales drops, variations, etc.)
   - [ ] Save full analysis to `analyses` table

4. **Scoring System:**
   - [ ] **Stage 1 Score:** Basic profitability check (ROI > threshold?)
   - [ ] **Final Score:** Comprehensive scoring (A/B/C/D/F) based on:
     - ROI percentage
     - Profit margin
     - Competition level
     - Sales rank
     - Gating status
     - Historical trends
   - Currently: No scoring system implemented

5. **Core Profitability Fields (9 fields from MASTER_WORKFLOW):**
   - [x] `buy_cost` - ✅ Exists in `product_sources.buy_cost`
   - [x] `sell_price` - ✅ Exists in `analyses.sell_price` and `products.sell_price`
   - [x] `fees_total` - ✅ Exists in `analyses.fees_total`
   - [x] `fees_referral` - ✅ Exists in `analyses.fees_referral`
   - [x] `fees_fba` - ✅ Exists in `analyses.fees_fba`
   - [x] `net_profit` - ❌ **NOT CALCULATED** (needs calculation: sell_price - fees_total - buy_cost)
   - [x] `roi` - ❌ **NOT CALCULATED** (needs calculation: (net_profit / buy_cost) * 100)
   - [x] `profit_margin` - ❌ **NOT CALCULATED** (needs calculation: (net_profit / sell_price) * 100)
   - [x] `meets_threshold` - ❌ **NOT CALCULATED** (needs threshold check)

6. **Profitability Calculations:**
   - [ ] Calculate `net_profit` = `sell_price` - `fees_total` - `buy_cost`
   - [ ] Calculate `roi` = (`net_profit` / `buy_cost`) * 100
   - [ ] Calculate `profit_margin` = (`net_profit` / `sell_price`) * 100
   - [ ] Check if `roi >= threshold` (e.g., 30%)
   - [ ] Save to `analyses` table (or `product_deals` view)

7. **Database Fields:**
   - [ ] Add `net_profit`, `roi`, `profit_margin` columns to `analyses` table (if not exists)
   - [ ] Add `meets_threshold` (BOOLEAN) to `analyses` table
   - [ ] Add `deal_score` (CHAR(1): 'A', 'B', 'C', 'D', 'F') to `analyses` table
   - [ ] Update `product_deals` view to include calculated fields

8. **Batch Processing Optimization:**
   - [ ] Process products in chunks matching API batch sizes
   - [ ] Stage 1: Process 100 at a time (Keepa batch size)
   - [ ] Stage 2: Process 20 at a time (SP-API batch size)
   - [ ] Parallelize chunks across Celery workers

9. **Error Handling:**
   - [ ] Handle SP-API failures gracefully (fallback to Keepa)
   - [ ] Handle Keepa failures gracefully (mark as error, continue)
   - [ ] Log failures but don't crash entire batch

10. **Performance:**
    - [ ] Estimate processing time: ~2-3 seconds per product (Stage 1 + Stage 2)
    - [ ] For 100 products: ~3-5 minutes total
    - [ ] Use materialized views for stats aggregation

---

## Summary

**What Exists:**
- ✅ Full SP-API integration with batch support
- ✅ Keepa integration with batch support
- ✅ Database schema with `products`, `analyses`, `product_sources` tables
- ✅ Celery task system for async processing
- ✅ Batch analyzer service that orchestrates API calls
- ✅ UPC to ASIN conversion
- ✅ Rate limiting
- ✅ Caching (Redis + Keepa cache table)

**What's Missing:**
- ❌ Two-stage analysis pipeline (Stage 1 quick filter, Stage 2 deep analysis)
- ❌ Profitability calculations (net_profit, roi, profit_margin)
- ❌ Scoring system (A/B/C/D/F grades)
- ❌ Threshold checking (meets_threshold boolean)
- ❌ Database columns for profitability metrics (may need to add to `analyses` table)

**Next Steps:**
1. Review `MASTER_WORKFLOW.md` to understand exact requirements
2. Implement Stage 1 quick filter (Keepa-only, basic ROI check)
3. Implement Stage 2 deep analysis (SP-API + full Keepa data)
4. Add profitability calculations to `batch_analyzer.py`
5. Add scoring logic based on ROI, competition, sales rank, etc.
6. Update database schema if needed (add `net_profit`, `roi`, `profit_margin`, `deal_score`, `meets_threshold`)
7. Update `analyses` table inserts to include calculated fields
8. Test with sample products to verify performance

