# HABEXA Implementation Action Plan

**Based on Functionality Checklist**  
**Status:** 30% Complete  
**Next:** Build critical missing features

---

## ✅ VERIFIED: What EXISTS

### 1. Pricing Intelligence
- ✅ Database migration created for `buy_box_price_365d_avg`, `buy_box_price_90d_avg`, `buy_box_price_30d_avg`
- ✅ Pricing Mode Toggle UI component
- ✅ Keepa integration extracts averages
- ⚠️ **NEEDS:** Migration must be run in Supabase
- ⚠️ **NEEDS:** Profit calculator to use selected pricing mode

### 2. Multi-Pack PPU System
- ✅ Database: `product_pack_variants` table (migration exists)
- ✅ Backend: `PackVariantCalculator` service
- ❌ **MISSING:** Pack variant discovery (finding all pack sizes)
- ❌ **MISSING:** API endpoint to discover variants
- ❌ **MISSING:** PPU comparison UI
- ❌ **MISSING:** Pack selector component

### 3. Supplier Management
- ✅ Full CRUD operations
- ✅ Supplier detail pages
- ✅ Delete with confirmation

### 4. Prep Instructions
- ✅ Database: `prep_instructions` table (migration exists)
- ✅ Backend method: `generate_prep_instructions()`
- ❌ **MISSING:** Auto-generation on order creation
- ❌ **MISSING:** PDF generation
- ❌ **MISSING:** Email to 3PL

### 5. Buy Lists & Orders
- ✅ Tables exist
- ✅ Basic creation workflow
- ⚠️ **NEEDS:** Enhancements for pack variants

---

## ❌ VERIFIED: What's MISSING

### 6. Brand Restrictions
**Status:** 0% - Not implemented
- ❌ No `brand_restrictions` table
- ❌ No detection logic
- ❌ No Analyzer column
- ❌ No supplier overrides

**Priority:** HIGH  
**Time:** 6-8 hours

---

### 7. Pack Type & Cost Intelligence
**Status:** 0% - Not implemented
- ❌ No `cost_type` column (Unit/Pack/Case)
- ❌ No case size tracking
- ❌ No UI selectors
- ❌ No cost per Amazon unit calculation

**Priority:** HIGH  
**Time:** 4-5 hours

---

### 8. True Landed Cost
**Status:** 30% - Basic costs exist, not complete
- ✅ Basic shipping/prep costs in calculator
- ❌ No shipping profiles per supplier
- ❌ No 3PL fee structures database (partial - prep_centers exists)
- ❌ No complete landed cost formula UI

**Priority:** MEDIUM  
**Time:** 6-8 hours

---

### 9. Automated PO Emails
**Status:** 0% - Not implemented
- ❌ No PO PDF generation
- ❌ No email template system
- ❌ No SendGrid integration
- ❌ No email tracking

**Priority:** HIGH  
**Time:** 8-10 hours

---

### 10. Inventory Forecasting
**Status:** 0% - Not implemented
- ❌ No FBA inventory sync
- ❌ No sales velocity calculation
- ❌ No reorder point calculator
- ❌ No stockout alerts

**Priority:** MEDIUM  
**Time:** 10-12 hours

---

### 11. Catalog Import Enhancements
**Status:** 50% - Basic exists, needs enhancement
- ✅ Basic file upload
- ❌ No intelligent column auto-detection
- ❌ No template system
- ❌ No real-time progress (WebSockets)
- ❌ No error log downloads

**Priority:** MEDIUM  
**Time:** 6-8 hours

---

## 🎯 IMMEDIATE NEXT STEPS

### Step 1: Run Database Migration (5 minutes)
**Action:** Run `ADD_PACK_VARIANTS_AND_PREP_INSTRUCTIONS.sql` in Supabase
- Adds `buy_box_price_365d_avg` columns to products
- Creates `product_pack_variants` table
- Creates `prep_instructions` table

---

### Step 2: Quick Win - PPU Column (1 hour)
**Action:** Add PPU column to Analyzer showing `profit / pack_size`
- Uses existing profit calculations
- Shows profit per unit at a glance
- No new backend work needed

---

### Step 3: Pack Variant Discovery (4-6 hours)
**Action:** Build system to find all pack sizes for a product
1. Create `PackVariantDiscovery` service
2. Methods:
   - SP-API variation search
   - Keepa product family search
   - UPC pattern matching
3. API endpoint: `POST /products/{id}/discover-variants`
4. Store results in `product_pack_variants` table

---

### Step 4: Brand Restrictions (6-8 hours)
**Action:** Build brand restriction system
1. Create `brand_restrictions` table
2. Create `product_brand_flags` table
3. Detection logic in import pipeline
4. Brand status column in Analyzer
5. Filter to hide restricted brands

---

### Step 5: Pack Type & Cost Intelligence (4-5 hours)
**Action:** Add cost type system
1. Add `cost_type` column to `product_sources` (Unit/Pack/Case)
2. Add `case_size` column
3. UI radio buttons for cost type selection
4. Calculate true unit cost based on type
5. Show cost breakdown in Analyzer

---

### Step 6: PO Email System (8-10 hours)
**Action:** Automated PO generation and email
1. PDF generation library (reportlab or similar)
2. Email template system
3. SendGrid integration
4. Email tracking table
5. "Send Order" button workflow

---

## 📋 IMPLEMENTATION CHECKLIST

For each missing feature:

- [ ] Database migration (if needed)
- [ ] Backend service/logic
- [ ] API endpoint
- [ ] Frontend component
- [ ] Integration testing
- [ ] Documentation

---

## 🚀 RECOMMENDED ORDER

**This Week:**
1. Run database migration
2. Add PPU column (quick win)
3. Build Pack Variant Discovery
4. Start Brand Restrictions

**Next Week:**
5. Complete Brand Restrictions
6. Pack Type & Cost Intelligence
7. PO Email System

**Week 3:**
8. Prep Instructions auto-generation
9. Inventory Forecasting
10. Catalog Import enhancements

---

**Estimated Total Time:** 60-80 hours for all features  
**Current Completion:** ~30%  
**Target:** 100% in 6-8 weeks

