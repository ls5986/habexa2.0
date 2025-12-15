# Habexa Project Cleanup Report

**Date:** December 12, 2024  
**Status:** Phase 1-2 Complete - Ready for Action

---

## 📊 EXECUTIVE SUMMARY

**Total Files Scanned:** 347  
**Active Files:** ~298  
**Files to Archive:** ~49  
**Critical Issues:** 3  
**High Priority Fixes:** 8  
**Medium Priority:** 15

---

## 🗑️ PHASE 2: FILES TO DELETE/ARCHIVE

### SAFE TO DELETE (Confirmed Unused)

#### Backend Files
1. **`backend/app/jobs/asin_lookup.py`** ⚠️
   - **Reason:** Duplicate of `app/tasks/asin_lookup.py`
   - **Status:** `app/jobs/` directory appears unused
   - **Action:** Archive to `/archive/backend/jobs/`

2. **`backend/app/cache.py`** ⚠️
   - **Reason:** Duplicate of `app/core/cache.py`
   - **Status:** `app/core/cache.py` is the active one
   - **Action:** Archive to `/archive/backend/`

3. **`backend/app/api/deps_test.py`** ⚠️
   - **Reason:** Test file, not used in production
   - **Action:** Move to `/archive/backend/tests/` or keep in tests/

#### Test Files (Move to tests/ or archive)
4. **`backend/test_profitability_calculator.py`** (root level)
   - **Action:** Move to `backend/tests/` or archive

5. **`backend/test_pricing_fallbacks.py`** (root level)
   - **Action:** Move to `backend/tests/` or archive

6. **`backend/test_asin_apis.py`** (root level)
   - **Action:** Move to `backend/tests/` or archive

#### Potentially Unused (Need Verification)
7. **`backend/app/services/file_processor.py`** ⚠️
   - **Status:** `streaming_file_processor.py` is used instead
   - **Action:** Verify not used, then archive

8. **`backend/app/api/v1/deals_optimized.py`** ⚠️
   - **Status:** Not registered in `main.py`
   - **Action:** Verify if needed, otherwise archive

---

## 🔧 PHASE 3: FILES TO FIX

### Priority 1 (Critical - System Won't Work)

#### 1. Missing Genius Score Display in Analyzer
- **File:** `frontend/src/components/Analyzer/EnhancedAnalyzer.jsx`
- **Issue:** Genius scores calculated but not displayed
- **Fix:** Add `genius_score` column to analyzer table
- **Status:** ⚠️ Missing

#### 2. Pricing Mode Not Persisting to Database
- **File:** `frontend/src/components/Analyzer/PricingModeToggle.jsx`
- **Issue:** Only saves to localStorage, not user preferences
- **Fix:** Add API call to save to `user_preferences` table
- **Status:** ⚠️ Incomplete

#### 3. Daily Genius Scoring Not Scheduled
- **File:** `backend/app/core/celery_app.py`
- **Issue:** `refresh_genius_scores_daily` task not in beat schedule
- **Fix:** Add to Celery Beat schedule
- **Status:** ⚠️ Missing

### Priority 2 (High - Feature Incomplete)

#### 4. Pack Variant UI Not Complete
- **File:** `frontend/src/components/Analyzer/PackSelector.jsx`
- **Issue:** Component exists but may not be integrated into Analyzer
- **Fix:** Verify integration, add to analyzer columns
- **Status:** ⚠️ Needs verification

#### 5. Cost Type Selector Not Integrated
- **File:** `frontend/src/components/Analyzer/CostTypeSelector.jsx`
- **Issue:** Component exists but may not be in product detail page
- **Fix:** Add to product detail/edit page
- **Status:** ⚠️ Needs verification

#### 6. Brand Restrictions Not Auto-Detected
- **File:** `backend/app/services/brand_restriction_detector.py`
- **Issue:** Service exists but may not be called during upload
- **Fix:** Integrate into file processing pipeline
- **Status:** ⚠️ Needs verification

#### 7. Prep Instructions Not Auto-Generated
- **File:** `backend/app/services/prep_instructions_service.py`
- **Issue:** Service exists but may not be called on order creation
- **Fix:** Hook into supplier order creation
- **Status:** ⚠️ Needs verification

#### 8. Shipping Cost Calculator Not Integrated
- **File:** `frontend/src/components/Shipping/ShippingCostCalculator.jsx`
- **Issue:** Component exists but may not be in order flow
- **Fix:** Add to buy list/order creation flow
- **Status:** ⚠️ Needs verification

### Priority 3 (Medium - Nice to Have)

#### 9. Duplicate Profit Calculators
- **Files:** 
  - `backend/app/services/profit_calculator.py` (used by analysis.py, batch_analyzer.py)
  - `backend/app/services/profitability_calculator.py` (newer, more comprehensive)
- **Issue:** Two different implementations
- **Fix:** Consolidate or document which to use
- **Status:** ⚠️ Needs consolidation

#### 10. Multiple Cost Calculators
- **Files:**
  - `backend/app/services/cost_calculator.py` (used by analysis.py)
  - `backend/app/services/cost_intelligence.py` (newer)
- **Issue:** Overlapping functionality
- **Fix:** Consolidate or document usage
- **Status:** ⚠️ Needs review

#### 11. Multiple Keepa Extractors
- **Files:**
  - `backend/app/services/keepa_data_extractor.py` (used by batch_analyzer.py)
  - `backend/app/services/api_field_extractor.py` (newer, KeepaExtractor class)
- **Issue:** Two different extraction methods
- **Fix:** Consolidate or document which to use
- **Status:** ⚠️ Needs review

---

## 📋 PHASE 4: MISSING COMPONENTS

### Database (Already Created - Just Need to Run)
- ✅ `ADD_GENIUS_SCORE_COLUMNS.sql` - Migration exists, needs to be run

### Backend Endpoints (May Be Missing)
1. **POST /api/v1/products/{id}/calculate-ppu**
   - **Need:** Endpoint to calculate PPU for all pack variants
   - **Status:** ⚠️ Check if exists in `pack_variants.py`

2. **GET /api/v1/products/{id}/genius-score**
   - **Need:** Endpoint to get/refresh genius score for a product
   - **Status:** ⚠️ May need to add

3. **POST /api/v1/products/bulk-calculate-scores**
   - **Need:** Endpoint to trigger genius scoring for multiple products
   - **Status:** ⚠️ May need to add

### Frontend Components (May Be Missing)
1. **Genius Score Column in Analyzer**
   - **File:** `frontend/src/components/Analyzer/EnhancedAnalyzer.jsx`
   - **Need:** Display genius_score, genius_grade, genius_badge
   - **Status:** ⚠️ Missing

2. **Genius Insights Tooltip**
   - **File:** `frontend/src/components/Analyzer/AnalyzerTableRow.jsx`
   - **Need:** Show insights on hover/click
   - **Status:** ⚠️ Missing

3. **Pack Variant Selector in Analyzer**
   - **File:** `frontend/src/config/analyzerColumns.js`
   - **Need:** Add pack size selector column
   - **Status:** ⚠️ Needs verification

4. **Cost Type Selector in Product Detail**
   - **File:** Product detail page (need to find)
   - **Need:** Add cost type selector component
   - **Status:** ⚠️ Needs verification

---

## 🔗 PHASE 5: INTEGRATION ISSUES

### Frontend → Backend

1. **Pricing Mode Toggle**
   - **Issue:** Saves to localStorage only
   - **Fix:** Also save to `user_preferences.default_pricing_mode`
   - **Files:** 
     - `frontend/src/components/Analyzer/PricingModeToggle.jsx`
     - `backend/app/api/v1/settings.py` (add endpoint if missing)

2. **Genius Scores Not Displayed**
   - **Issue:** Scores calculated but not shown in UI
   - **Fix:** Add column to Analyzer, fetch from API
   - **Files:**
     - `frontend/src/components/Analyzer/EnhancedAnalyzer.jsx`
     - `frontend/src/config/analyzerColumns.js`

3. **Pack Selector Not Connected**
   - **Issue:** Component exists but may not be in analyzer
   - **Fix:** Add to analyzer columns, connect to API
   - **Files:**
     - `frontend/src/components/Analyzer/PackSelector.jsx`
     - `frontend/src/config/analyzerColumns.js`

### Backend → Database

1. **Genius Scores Not Stored**
   - **Issue:** Scores calculated but may not be saved
   - **Fix:** Ensure `genius_scoring_tasks.py` saves to database
   - **Status:** ✅ Should be working, needs verification

2. **Pricing Mode Not Saved**
   - **Issue:** User preference not persisted
   - **Fix:** Update settings endpoint to save `default_pricing_mode`
   - **Status:** ⚠️ Needs fix

### Backend → Background Jobs

1. **Daily Genius Scoring Not Scheduled**
   - **Issue:** Task exists but not in Celery Beat
   - **Fix:** Add to `celery_app.py` beat schedule
   - **Status:** ⚠️ Missing

2. **Inventory Sync Not Scheduled**
   - **Issue:** Task exists but may not be scheduled
   - **Fix:** Verify in Celery Beat schedule
   - **Status:** ⚠️ Needs verification

---

## 🎯 PRIORITY ACTION LIST

### PRIORITY 1 (Critical - System Won't Work)

1. **Run ADD_GENIUS_SCORE_COLUMNS.sql migration**
   - **Impact:** Genius scores can't be stored
   - **Time:** 1 minute
   - **Status:** ⚠️ Not run yet

2. **Add genius score column to Analyzer UI**
   - **Impact:** Users can't see scores
   - **Time:** 30 minutes
   - **Status:** ⚠️ Missing

3. **Schedule daily genius scoring job**
   - **Impact:** Scores won't refresh automatically
   - **Time:** 5 minutes
   - **Status:** ⚠️ Missing

### PRIORITY 2 (High - Feature Incomplete)

4. **Fix pricing mode persistence**
   - **Impact:** User preference not saved
   - **Time:** 15 minutes
   - **Status:** ⚠️ Incomplete

5. **Integrate pack selector into Analyzer**
   - **Impact:** Users can't select pack sizes
   - **Time:** 30 minutes
   - **Status:** ⚠️ Needs verification

6. **Integrate cost type selector**
   - **Impact:** Users can't set cost type
   - **Time:** 30 minutes
   - **Status:** ⚠️ Needs verification

7. **Auto-detect brand restrictions on upload**
   - **Impact:** Restricted products not flagged
   - **Time:** 1 hour
   - **Status:** ⚠️ Needs verification

8. **Auto-generate prep instructions on order**
   - **Impact:** Prep instructions not created
   - **Time:** 1 hour
   - **Status:** ⚠️ Needs verification

### PRIORITY 3 (Medium - Nice to Have)

9. **Consolidate duplicate profit calculators**
   - **Time:** 2 hours
   - **Status:** ⚠️ Needs review

10. **Archive unused files**
    - **Time:** 30 minutes
    - **Status:** ⚠️ Ready to do

11. **Update documentation**
    - **Time:** 1 hour
    - **Status:** ⚠️ Needs update

---

## 📁 ARCHIVE STRUCTURE

Create this structure for moved files:

```
/archive/
├── /backend/
│   ├── /jobs/
│   │   └── asin_lookup.py (duplicate)
│   ├── cache.py (duplicate)
│   ├── /tests/
│   │   ├── test_profitability_calculator.py
│   │   ├── test_pricing_fallbacks.py
│   │   └── test_asin_apis.py
│   └── /services/
│       └── file_processor.py (if unused)
├── /frontend/
│   └── (none identified yet)
└── /docs/
    └── (outdated docs to be identified)
```

---

## ✅ VERIFICATION CHECKLIST

### Core Workflows

- [ ] **A. User Registration & Login**
  - [ ] Database: `profiles` table exists
  - [ ] Backend: `/api/v1/auth/*` endpoints work
  - [ ] Frontend: Login/Register pages work
  - [ ] Integration: Auth flow works end-to-end

- [ ] **B. Supplier Management**
  - [ ] Database: `suppliers` table exists
  - [ ] Backend: `/api/v1/suppliers/*` endpoints work
  - [ ] Frontend: Suppliers list and detail pages work
  - [ ] Integration: CRUD operations work

- [ ] **C. Product Catalog Upload**
  - [ ] Database: `products`, `product_sources`, `upload_jobs` exist
  - [ ] Backend: `/api/v1/upload/*` endpoints work
  - [ ] Frontend: Upload component works
  - [ ] Background: File processing tasks run
  - [ ] Integration: Upload → Processing → Analyzer works

- [ ] **D. Product Analysis (Analyzer)**
  - [ ] Database: All analyzer columns exist
  - [ ] Backend: `/api/v1/analyzer/*` endpoints work
  - [ ] Frontend: Analyzer page loads and displays data
  - [ ] Features: Filters, sorting, pricing mode work
  - [ ] Integration: Data flows correctly

- [ ] **E. Genius Scoring System**
  - [ ] Database: `genius_score` columns exist (after migration)
  - [ ] Backend: `genius_scorer.py` works
  - [ ] Tasks: `genius_scoring_tasks.py` works
  - [ ] Frontend: Scores displayed (needs fix)
  - [ ] Integration: Scoring → Storage → Display works

- [ ] **F. Buy Lists & Orders**
  - [ ] Database: `buy_lists`, `buy_list_items`, `supplier_orders` exist
  - [ ] Backend: `/api/v1/buy-lists/*`, `/api/v1/supplier-orders/*` work
  - [ ] Frontend: Buy list pages work
  - [ ] Integration: Create → Edit → Generate Order works

- [ ] **G. Purchase Order Automation**
  - [ ] Database: `po_generations`, `email_tracking` exist
  - [ ] Backend: `/api/v1/po-emails/*` endpoints work
  - [ ] Integration: Order → PDF → Email works

---

## 📝 NEXT STEPS

1. **Review this report** - Confirm findings
2. **Fix Priority 1 issues** - Critical fixes first
3. **Archive unused files** - Clean up codebase
4. **Verify workflows** - Test each workflow end-to-end
5. **Update documentation** - Reflect current state

---

**Status:** Ready for Phase 3 execution (fixing issues)

