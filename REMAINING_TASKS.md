# Remaining Tasks - Habexa Project

**Last Updated:** December 12, 2024  
**Status:** Priority 1 Complete - Ready for Priority 2

---

## ✅ COMPLETED (Priority 1 - Critical)

- [x] **Genius Score Column Added** - Column exists in Analyzer
- [x] **Genius Score Rendering** - Displays with grade badges
- [x] **Pricing Mode Persistence** - Saves to database
- [x] **Daily Genius Scoring Scheduled** - Runs at 3 AM
- [x] **Preferences API Created** - GET/PUT endpoints
- [x] **Database Migration** - Columns added (fast version)

---

## 🔥 PRIORITY 2 (High - Feature Incomplete)

### 1. **Pack Variant Selector Integration** ⚠️
**Status:** Component exists but needs verification

**What's Missing:**
- Verify `PackSelector.jsx` is integrated into Analyzer
- Add pack variant column to `analyzerColumns.js`
- Connect to backend API for pack variant data
- Display PPU (Profit Per Unit) for each pack size

**Files to Check:**
- `frontend/src/components/Analyzer/PackSelector.jsx`
- `frontend/src/config/analyzerColumns.js`
- `backend/app/api/v1/pack_variants.py`

**Estimated Time:** 1-2 hours

---

### 2. **Cost Type Selector Integration** ⚠️
**Status:** Component exists but needs verification

**What's Missing:**
- Verify `CostTypeSelector.jsx` is in product detail/edit page
- Add cost type (unit/pack/case) to product sources
- Update profitability calculations to use cost type
- Display visual breakdown (unit cost vs pack cost)

**Files to Check:**
- `frontend/src/components/Analyzer/CostTypeSelector.jsx`
- Product detail page (need to find)
- `backend/app/services/cost_intelligence.py`

**Estimated Time:** 1-2 hours

---

### 3. **Brand Restrictions Auto-Detection** ⚠️
**Status:** Service exists but needs integration

**What's Missing:**
- Hook `brand_restriction_detector.py` into file upload pipeline
- Auto-flag products during CSV upload
- Display brand restriction status in Analyzer
- Add warning when adding restricted products to buy list

**Files to Check:**
- `backend/app/services/brand_restriction_detector.py`
- `backend/app/tasks/file_processing.py`
- `frontend/src/components/Analyzer/EnhancedAnalyzer.jsx`

**Estimated Time:** 2-3 hours

---

### 4. **Prep Instructions Auto-Generation** ⚠️
**Status:** Service exists but needs hook

**What's Missing:**
- Hook `prep_instructions_service.py` into supplier order creation
- Auto-generate prep instructions when order is created
- Display prep instructions in order detail page
- Generate PDF for 3PL

**Files to Check:**
- `backend/app/services/prep_instructions_service.py`
- `backend/app/api/v1/supplier_orders.py`
- `frontend/src/pages/SupplierOrderDetail.jsx`

**Estimated Time:** 2-3 hours

---

### 5. **Shipping Cost Calculator Integration** ⚠️
**Status:** Component exists but needs integration

**What's Missing:**
- Add `ShippingCostCalculator.jsx` to buy list/order creation flow
- Calculate shipping costs based on supplier profiles
- Include shipping in profitability calculations
- Display shipping cost breakdown

**Files to Check:**
- `frontend/src/components/Shipping/ShippingCostCalculator.jsx`
- `frontend/src/pages/BuyListDetail.jsx`
- `backend/app/api/v1/shipping_profiles.py`

**Estimated Time:** 1-2 hours

---

### 6. **Genius Score Insights Tooltip** ⚠️
**Status:** Partially done - scores display but insights not shown

**What's Missing:**
- Add tooltip/hover to show genius insights
- Display strengths, weaknesses, opportunities, warnings
- Add insights panel in product detail page

**Files to Check:**
- `frontend/src/components/Analyzer/AnalyzerTableRow.jsx`
- Product detail page

**Estimated Time:** 1 hour

---

### 7. **Genius Score Filtering** ⚠️
**Status:** Column exists but filtering not implemented

**What's Missing:**
- Add "Min Genius Score" filter to AnalyzerFilters
- Add "Genius Grade" filter (EXCELLENT/GOOD/FAIR/POOR)
- Update backend API to support score filtering

**Files to Check:**
- `frontend/src/components/Analyzer/AnalyzerFilters.jsx`
- `backend/app/routers/analyzer.py`

**Estimated Time:** 1 hour

---

## 📋 PRIORITY 3 (Medium - Nice to Have)

### 8. **Archive Unused Files** 📁
**Status:** Identified but not archived

**What to Do:**
- Review `CLEANUP_REPORT.md` for list of ~49 files
- Move to `/archive/` folder
- Update any imports that reference archived files

**Files Identified:**
- `backend/app/jobs/asin_lookup.py` (duplicate)
- `backend/app/cache.py` (duplicate)
- `backend/test_*.py` (root level test files)
- Various unused components

**Estimated Time:** 30 minutes

---

### 9. **Consolidate Duplicate Services** 🔄
**Status:** Needs review

**What to Do:**
- Review `profit_calculator.py` vs `profitability_calculator.py`
- Review `cost_calculator.py` vs `cost_intelligence.py`
- Review `keepa_data_extractor.py` vs `api_field_extractor.py`
- Decide which to keep, update imports, archive old ones

**Estimated Time:** 2-3 hours

---

### 10. **Add Database Indexes** 📊
**Status:** Columns exist, indexes not added

**What to Do:**
- Add indexes using `CONCURRENTLY` (non-blocking)
- Run during off-peak hours
- See `POST_MIGRATION_STEPS.md` for SQL

**Estimated Time:** 15 minutes (but run during off-peak)

---

### 11. **Update Documentation** 📚
**Status:** Needs consolidation

**What to Do:**
- Consolidate outdated docs
- Update README.md with current setup
- Create ARCHITECTURE.md
- Create API_REFERENCE.md

**Estimated Time:** 2-3 hours

---

## 🧪 TESTING & VERIFICATION

### 12. **End-to-End Workflow Testing** ✅
**Status:** Not verified

**Test These Workflows:**
- [ ] User registration & login
- [ ] Supplier management (CRUD)
- [ ] Product catalog upload (CSV)
- [ ] Background jobs process products
- [ ] Products appear in Analyzer
- [ ] Genius scores calculated and displayed
- [ ] Pricing mode toggle works and persists
- [ ] Buy list creation from Analyzer
- [ ] Supplier order generation
- [ ] PO email sending

**Estimated Time:** 2-3 hours

---

### 13. **Genius Scoring Verification** 🎯
**Status:** Migration done, scoring not verified

**What to Do:**
- [ ] Run scoring job: `calculate_genius_scores.delay()`
- [ ] Verify scores appear in database
- [ ] Verify scores display in Analyzer UI
- [ ] Verify daily job runs at 3 AM
- [ ] Test filtering/sorting by score

**Estimated Time:** 30 minutes

---

## 🎯 RECOMMENDED ORDER

### **This Week (High Priority):**

1. **Genius Score Insights Tooltip** (1 hour) - Quick win
2. **Genius Score Filtering** (1 hour) - Quick win
3. **Pack Variant Selector** (1-2 hours) - Important feature
4. **Cost Type Selector** (1-2 hours) - Important feature
5. **Test Genius Scoring** (30 min) - Verify it works

**Total:** ~5-7 hours

---

### **Next Week (Medium Priority):**

6. **Brand Restrictions Auto-Detection** (2-3 hours)
7. **Prep Instructions Auto-Generation** (2-3 hours)
8. **Shipping Cost Calculator** (1-2 hours)
9. **Archive Unused Files** (30 min)
10. **Add Database Indexes** (15 min)

**Total:** ~6-9 hours

---

### **This Month (Nice to Have):**

11. **Consolidate Duplicate Services** (2-3 hours)
12. **Update Documentation** (2-3 hours)
13. **End-to-End Testing** (2-3 hours)

**Total:** ~6-9 hours

---

## 📊 SUMMARY

**Priority 1 (Critical):** ✅ **COMPLETE** (6/6 tasks)

**Priority 2 (High):** ⚠️ **7 tasks remaining** (~10-15 hours)

**Priority 3 (Medium):** ⚠️ **4 tasks remaining** (~5-6 hours)

**Testing:** ⚠️ **2 verification tasks** (~3 hours)

---

## 🚀 QUICK WINS (Do These First)

These are the easiest and most impactful:

1. **Genius Score Insights Tooltip** (1 hour) - Show insights on hover
2. **Genius Score Filtering** (1 hour) - Filter by score/grade
3. **Test Genius Scoring** (30 min) - Verify everything works

**Total:** ~2.5 hours for 3 quick wins!

---

## 💡 NEXT IMMEDIATE ACTION

**Right Now:**
1. Test genius scoring: `calculate_genius_scores.delay()`
2. Verify scores appear in Analyzer UI
3. Add insights tooltip (quick win)

**This Week:**
4. Add genius score filtering
5. Integrate pack variant selector
6. Integrate cost type selector

---

**You're in great shape!** Priority 1 is done. Focus on Priority 2 quick wins first. 🎉

