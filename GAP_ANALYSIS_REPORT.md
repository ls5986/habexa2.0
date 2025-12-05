# Gap Analysis Report - MASTER_WORKFLOW Implementation

## 3A: Database Column Check

### Columns to Check in `analyses` Table

Based on migration files (`ENSURE_ANALYSES_COLUMNS.sql`, `ADD_FEES_COLUMNS_TO_ANALYSES.sql`, etc.):

**✅ Already Exist:**
- `fees_total` (DECIMAL(10,2))
- `fees_referral` (DECIMAL(10,2))
- `fees_fba` (DECIMAL(10,2))
- `seller_count` (INTEGER)
- `category` (TEXT)
- `title` (TEXT)
- `brand` (TEXT)
- `image_url` (TEXT)
- `supplier_id` (UUID)

**❌ Missing (Need to Add):**
- `sell_price` (DECIMAL(10,2)) - **CRITICAL** - Currently stored in `products` table only
- `net_profit` (DECIMAL(10,2)) - **CRITICAL** - Not calculated or stored
- `roi` (DECIMAL(5,2)) - **CRITICAL** - Not calculated or stored
- `profit_margin` (DECIMAL(5,2)) - **CRITICAL** - Not calculated or stored
- `deal_score` (CHAR(1) or VARCHAR(1)) - **CRITICAL** - Scoring not implemented
- `meets_threshold` (BOOLEAN) - **CRITICAL** - Threshold checking not implemented
- `stage1_score` (DECIMAL(5,2)) - **NEW** - Stage 1 quick score
- `analysis_stage` (VARCHAR) - **NEW** - Track pipeline stage: 'pending', 'stage1_complete', 'stage2_complete', 'filtered_out'

**Note:** The `deals` table has `net_profit`, `roi`, `profit_margin`, `deal_score` columns, but `analyses` table does NOT. The current code saves to `analyses` table, not `deals` table.

---

## 3B: Review Current batch_analyzer.py Flow

### Current Function Signature

```python
async def analyze_products(
    self,
    asins: List[str],
    marketplace_id: str = "ATVPDKIKX0DER"
) -> Dict[str, dict]:
```

**Answer 1:** Function signature does NOT accept `buy_cost` as a parameter.

**Answer 2:** No, `buy_cost` is not accepted. It's only passed as part of the ASIN list.

**Answer 3: Stage 1 Filtering Logic Insertion Point:**

After **Step 1 (Keepa batch)** and before **Step 2 (SP-API pricing)**:

```python
# Current flow (lines 40-64):
# STEP 1: KEEPA - Batch of 100
keepa_data = await keepa_client.get_products_batch(asins, domain=1, history=False, days=90)
# ... update results with Keepa data ...

# ⬇️ INSERT STAGE 1 FILTERING HERE ⬇️
# After Keepa data is collected, before SP-API calls
# Calculate Stage 1 score using Keepa pricing + buy_cost
# Filter out products with stage1_score < 50

# Current flow (lines 65-84):
# STEP 2: SP-API PRICING - Batch of 20
# ... SP-API calls ...
```

**Answer 4: Profitability Calculations Insertion Point:**

After **Step 3 (SP-API fees)** and before **Step 4 (Mark success)**:

```python
# Current flow (lines 107-130):
# STEP 3: SP-API FEES - Batch of 20
# ... fees data collected ...

# ⬇️ INSERT PROFITABILITY CALCULATIONS HERE ⬇️
# After all pricing and fees are collected
# Calculate: net_profit, roi, profit_margin, deal_score, meets_threshold
# Add these to results dict

# Current flow (lines 132-161):
# STEP 4: Mark success
# ... success criteria ...
```

**Required Changes:**
1. Add `buy_costs: Dict[str, float]` parameter to `analyze_products()` method
2. Add Stage 1 filtering logic after Keepa step
3. Add profitability calculations after fees step
4. Return filtered ASINs list for Stage 2 processing

---

## 3C: Review Current analysis.py Task

### How `buy_cost` is Currently Retrieved

**Answer 1:** `buy_cost` is retrieved from `product_sources` table:

```python
# In analyze_single_product() (lines 34-39):
metadata = job_data.get("metadata", {})
buy_cost = buy_cost or metadata.get("buy_cost") or metadata.get("original_buy_cost")

# In batch_analyze_products() (lines 270-274):
# buy_cost is NOT retrieved - it's missing!
# The task only gets product_id and asin from products table
# buy_cost must be fetched from product_sources table
```

**Current Issue:** `batch_analyze_products()` does NOT fetch `buy_cost` from `product_sources`. It only gets `id` and `asin` from `products` table.

**Answer 2: Where Results Are Saved:**

**To `analyses` table:**
- Lines 107-126 (`analyze_single_product`)
- Lines 332-335 (`batch_analyze_products`)
- Lines 525-548 (`analyze_chunk`)

**To `products` table:**
- Lines 131-153 (`analyze_single_product`)
- Lines 340-351 (`batch_analyze_products`)
- Lines 553-564 (`analyze_chunk`)

**Answer 3: Changes Needed for Two-Stage Processing:**

1. **Fetch `buy_cost` from `product_sources` table:**
   ```python
   # Need to join products with product_sources to get buy_cost
   products_result = supabase.table("products")\
       .select("id, asin, product_sources(buy_cost, supplier_id)")\
       .eq("user_id", user_id)\
       .in_("id", batch_ids)\
       .execute()
   ```

2. **Pass `buy_costs` dict to `batch_analyzer.analyze_products()`:**
   ```python
   buy_costs = {asin: buy_cost for asin, buy_cost in ...}
   results = run_async(batch_analyzer.analyze_products(batch_asins, marketplace_id, buy_costs=buy_costs))
   ```

3. **Handle Stage 1 filtering:**
   - After Stage 1, only process profitable products in Stage 2
   - Mark filtered-out products with `analysis_stage = 'filtered_out'`

4. **Save profitability fields to `analyses` table:**
   - Add `net_profit`, `roi`, `profit_margin`, `deal_score`, `meets_threshold` to upsert

5. **Update `analysis_stage` field:**
   - Set to `'stage1_complete'` after Stage 1
   - Set to `'stage2_complete'` after Stage 2
   - Set to `'filtered_out'` if Stage 1 score < threshold

---

## 3D: Check profit_calculator.py

### Existing Functions

**Answer 1: Functions Already Exist:**

1. `calculate_profit(buy_cost, sell_price, fba_fee, referral_fee, prep_cost, inbound_shipping, category)`
   - Returns: `net_profit`, `roi`, `margin`, `is_profitable`
   - **Note:** Uses `margin` not `profit_margin` (naming difference)

2. `get_referral_rate(category)` - Returns referral fee rate by category

3. `estimate_fba_fee(sell_price)` - Estimates FBA fee based on price

4. `calculate_deal_score(roi, sales_rank, gating_status, amazon_is_seller, num_fba_sellers)`
   - Returns: `'A'`, `'B'`, `'C'`, `'D'`, or `'F'`

**Answer 2: Does It Calculate Required Fields?**

✅ **YES** - It calculates:
- `net_profit` ✅
- `roi` ✅
- `margin` (same as `profit_margin`) ✅
- `deal_score` ✅

❌ **NO** - It does NOT calculate:
- `meets_threshold` (boolean) - needs to be added
- `stage1_score` - needs to be added

**Answer 3: Can We Reuse It?**

✅ **YES** - Can reuse with modifications:

1. **`calculate_profit()`** - ✅ Can use as-is, but:
   - Currently uses `fba_fee` and `referral_fee` separately
   - Need to adapt to use `fees_total` from SP-API
   - Returns `margin` but schema expects `profit_margin` (rename or map)

2. **`calculate_deal_score()`** - ✅ Can use as-is, but:
   - Requires `sales_rank` (from Keepa or SP-API)
   - Requires `gating_status` (from SP-API eligibility check)
   - Requires `amazon_is_seller` (from SP-API)
   - Requires `num_fba_sellers` (from SP-API)

3. **Missing Functions to Add:**
   - `calculate_stage1_score(buy_cost, sell_price, estimated_fees)` - Quick score using Keepa pricing
   - `meets_threshold(roi, min_roi=30)` - Check if ROI meets minimum threshold

---

## 3E: Implementation Checklist

### Database Changes Needed

- [ ] **Add `sell_price` column to `analyses` table** (DECIMAL(10,2))
  - Currently only in `products` table, but needed in `analyses` for calculations

- [ ] **Add `net_profit` column to `analyses` table** (DECIMAL(10,2))
  - Calculated: `sell_price - fees_total - buy_cost`

- [ ] **Add `roi` column to `analyses` table** (DECIMAL(5,2))
  - Calculated: `(net_profit / buy_cost) * 100`

- [ ] **Add `profit_margin` column to `analyses` table** (DECIMAL(5,2))
  - Calculated: `(net_profit / sell_price) * 100`
  - Note: `profit_calculator.py` returns `margin`, need to map to `profit_margin`

- [ ] **Add `deal_score` column to `analyses` table** (CHAR(1))
  - Values: 'A', 'B', 'C', 'D', 'F'
  - Use `profit_calculator.calculate_deal_score()`

- [ ] **Add `meets_threshold` column to `analyses` table** (BOOLEAN)
  - True if `roi >= 30` (or configurable threshold)

- [ ] **Add `stage1_score` column to `analyses` table** (DECIMAL(5,2))
  - Quick profitability score from Stage 1 (0-100)

- [ ] **Add `analysis_stage` column to `analyses` table** (VARCHAR(50))
  - Values: 'pending', 'stage1_complete', 'stage2_complete', 'filtered_out'

- [ ] **Create index on `analyses.roi`** for fast filtering
  - `CREATE INDEX idx_analyses_roi ON analyses(roi DESC) WHERE roi IS NOT NULL;`

- [ ] **Create index on `analyses.analysis_stage`** for pipeline tracking
  - `CREATE INDEX idx_analyses_stage ON analyses(analysis_stage) WHERE analysis_stage IS NOT NULL;`

---

### Files to MODIFY (not create)

| File | Change Required | Line Numbers |
|------|-----------------|--------------|
| `backend/app/services/batch_analyzer.py` | Add `buy_costs: Dict[str, float]` parameter to `analyze_products()` | ~24 |
| `backend/app/services/batch_analyzer.py` | Add Stage 1 filtering logic after Keepa step (before SP-API pricing) | ~64-65 |
| `backend/app/services/batch_analyzer.py` | Add profitability calculations after fees step (before success marking) | ~130-131 |
| `backend/app/services/batch_analyzer.py` | Return `stage1_scores` and `filtered_asins` for Stage 2 processing | ~161 |
| `backend/app/tasks/analysis.py` | Fetch `buy_cost` from `product_sources` table in `batch_analyze_products()` | ~198-202 |
| `backend/app/tasks/analysis.py` | Pass `buy_costs` dict to `batch_analyzer.analyze_products()` | ~268 |
| `backend/app/tasks/analysis.py` | Handle Stage 1 filtered products (set `analysis_stage = 'filtered_out'`) | ~270-378 |
| `backend/app/tasks/analysis.py` | Save profitability fields (`net_profit`, `roi`, `profit_margin`, `deal_score`, `meets_threshold`) to `analyses` table | ~332-335, ~525-548 |
| `backend/app/tasks/analysis.py` | Update `analysis_stage` field: 'stage1_complete' → 'stage2_complete' | ~332-335, ~525-548 |
| `backend/app/services/profit_calculator.py` | Add `calculate_stage1_score()` function | New function |
| `backend/app/services/profit_calculator.py` | Add `meets_threshold(roi, min_roi=30)` function | New function |
| `backend/app/services/profit_calculator.py` | Update `calculate_profit()` to accept `fees_total` instead of separate fees | ~4-12 |
| `backend/app/services/profit_calculator.py` | Map `margin` to `profit_margin` in return dict | ~44 |

---

### Files to CREATE (if any)

| File | Purpose |
|------|---------|
| `database/ADD_PROFITABILITY_COLUMNS.sql` | Migration to add `sell_price`, `net_profit`, `roi`, `profit_margin`, `deal_score`, `meets_threshold`, `stage1_score`, `analysis_stage` to `analyses` table |
| `backend/app/services/stage1_filter.py` | **OPTIONAL** - Extract Stage 1 logic into separate module for clarity |

---

### Functions to Add

| Function | Location | Purpose | Parameters | Returns |
|----------|----------|---------|------------|---------|
| `calculate_stage1_score()` | `profit_calculator.py` | Quick profitability score using Keepa pricing (no SP-API fees) | `buy_cost`, `sell_price`, `estimated_fees` | `float` (0-100) |
| `meets_threshold()` | `profit_calculator.py` | Check if ROI meets minimum threshold | `roi`, `min_roi=30` | `bool` |
| `filter_stage1_results()` | `batch_analyzer.py` | Filter products based on Stage 1 score | `results`, `buy_costs`, `threshold=50` | `(filtered_results, filtered_asins)` |
| `calculate_profitability()` | `batch_analyzer.py` | Calculate all profitability metrics | `buy_cost`, `sell_price`, `fees_total`, `category`, `sales_rank`, `gating_status`, `amazon_is_seller`, `num_fba_sellers` | `dict` with `net_profit`, `roi`, `profit_margin`, `deal_score`, `meets_threshold` |

---

### Integration Points

1. **Where Stage 1 filter gets called:**
   - **File:** `backend/app/services/batch_analyzer.py`
   - **Location:** After line 64 (after Keepa data is collected, before SP-API pricing calls)
   - **Code:**
     ```python
     # After Keepa step (line 46-63)
     keepa_data = await keepa_client.get_products_batch(asins, domain=1, history=False, days=90)
     # ... update results ...
     
     # ⬇️ STAGE 1 FILTERING ⬇️
     if buy_costs:
         stage1_results = {}
         for asin in asins:
             buy_cost = buy_costs.get(asin)
             if not buy_cost:
                 continue
             
             # Get Keepa pricing (fallback to estimated)
             sell_price = results[asin].get("sell_price") or results[asin].get("current_price")
             if not sell_price:
                 continue
             
             # Estimate fees (use category-based referral + estimated FBA)
             estimated_fees = estimate_fees_from_keepa(sell_price, results[asin].get("category"))
             
             # Calculate Stage 1 score
             stage1_score = calculate_stage1_score(buy_cost, sell_price, estimated_fees)
             results[asin]["stage1_score"] = stage1_score
             
             # Filter: Only proceed to Stage 2 if score >= 50
             if stage1_score >= 50:
                 stage1_results[asin] = results[asin]
         
         # Update asins list to only include profitable products
         asins = list(stage1_results.keys())
         logger.info(f"✅ Stage 1 filter: {len(asins)}/{len(buy_costs)} products passed threshold")
     ```

2. **Where Stage 2 gets triggered:**
   - **File:** `backend/app/services/batch_analyzer.py`
   - **Location:** After Stage 1 filtering (line 65+)
   - **Code:** Stage 2 is the existing SP-API pricing and fees steps (lines 65-130)
   - **Note:** Only products that passed Stage 1 will get SP-API calls

3. **Where scores get saved:**
   - **File:** `backend/app/tasks/analysis.py`
   - **Location:** 
     - `batch_analyze_products()`: Lines 332-335 (upsert to `analyses` table)
     - `analyze_chunk()`: Lines 525-548 (upsert to `analyses` table)
   - **Code:**
     ```python
     analysis_data = {
         "user_id": user_id,
         "asin": asin,
         "supplier_id": supplier_id,
         "analysis_data": {},
         "sell_price": result.get("sell_price"),  # NEW
         "fees_total": result.get("fees_total"),
         "fees_referral": result.get("fees_referral"),
         "fees_fba": result.get("fees_fba"),
         "net_profit": result.get("net_profit"),  # NEW
         "roi": result.get("roi"),  # NEW
         "profit_margin": result.get("profit_margin"),  # NEW
         "deal_score": result.get("deal_score"),  # NEW
         "meets_threshold": result.get("meets_threshold"),  # NEW
         "stage1_score": result.get("stage1_score"),  # NEW
         "analysis_stage": "stage2_complete",  # NEW
         # ... existing fields ...
     }
     ```

4. **Where buy_cost is fetched:**
   - **File:** `backend/app/tasks/analysis.py`
   - **Location:** `batch_analyze_products()` function, around line 198-202
   - **Current:** Only fetches `id, asin` from `products` table
   - **Needed:** Join with `product_sources` to get `buy_cost`
   - **Code:**
     ```python
     # Current (line 198-202):
     products_result = supabase.table("products")\
         .select("id, asin, status")\
         .eq("user_id", user_id)\
         .in_("id", batch_ids)\
         .execute()
     
     # Needed:
     products_result = supabase.table("products")\
         .select("id, asin, status, product_sources(buy_cost, supplier_id)")\
         .eq("user_id", user_id)\
         .in_("id", batch_ids)\
         .execute()
     
     # Extract buy_costs dict
     buy_costs = {}
     for product in products_result.data:
         asin = product["asin"]
         sources = product.get("product_sources", [])
         if sources and sources[0].get("buy_cost"):
             buy_costs[asin] = float(sources[0]["buy_cost"])
     ```

---

## Summary

### Critical Missing Pieces:

1. **Database:** 8 new columns needed in `analyses` table
2. **batch_analyzer.py:** Stage 1 filtering logic + profitability calculations
3. **analysis.py:** Fetch `buy_cost` from `product_sources` + pass to batch_analyzer
4. **profit_calculator.py:** Add `calculate_stage1_score()` and `meets_threshold()` functions

### Estimated Implementation Time:

- Database migration: **30 minutes**
- `profit_calculator.py` updates: **1 hour**
- `batch_analyzer.py` Stage 1 + profitability: **3 hours**
- `analysis.py` buy_cost fetching + saving: **2 hours**
- Testing & debugging: **2 hours**

**Total: ~8-10 hours**

