# HABEXA v3.0 - Implementation Roadmap

**Last Updated:** December 12, 2024  
**Status:** Foundation Complete ✅ | Next: Multi-Pack PPU UI

---

## 🎯 IMPLEMENTATION PRIORITY

### ✅ **COMPLETED (Foundation)**

1. ✅ Database schema for `product_pack_variants` and `prep_instructions`
2. ✅ `PackVariantCalculator` service (backend logic)
3. ✅ 365-day average extraction from Keepa
4. ✅ Supplier management with delete & detail pages
5. ✅ Analyzer dashboard with inline editing

---

## 📋 **NEXT: PHASE 1 - Multi-Pack PPU UI (WEEK 1)**

### **Priority 1.1: Pricing Mode Toggle** ⚠️ CRITICAL
**Time:** 2-3 hours  
**Impact:** High - More accurate profitability calculations

**Implementation:**
- Frontend component: `PricingModeToggle.jsx`
- Store user preference in localStorage/settings
- Update Analyzer table to use selected pricing mode
- Show price deviation warnings (spike/dip indicators)

**Files:**
- `frontend/src/components/Analyzer/PricingModeToggle.jsx` (NEW)
- `frontend/src/components/Analyzer/EnhancedAnalyzer.jsx` (UPDATE)
- `frontend/src/pages/Analyzer.jsx` (UPDATE)

---

### **Priority 1.2: Pack Variant Discovery API** ⚠️ CRITICAL
**Time:** 4-6 hours  
**Impact:** Critical - Need to find all pack sizes before calculating PPU

**Implementation:**
- Backend endpoint: `POST /products/{id}/discover-variants`
- Service: `PackVariantDiscovery` class
- Methods:
  - SP-API variation search
  - Keepa product family search
  - UPC pattern matching
- Store variants in `product_pack_variants` table

**Files:**
- `backend/app/services/pack_variant_discovery.py` (NEW)
- `backend/app/api/v1/products.py` (ADD endpoint)
- Background task to auto-discover on product import

---

### **Priority 1.3: Pack Selector Component** 🔶 HIGH
**Time:** 3-4 hours  
**Impact:** High - Core feature for pack selection

**Implementation:**
- Component: `PackSelector.jsx`
- Shows all pack variants with PPU comparison
- Highlights recommended pack (highest PPU)
- Updates `product_source.target_pack_size` on selection
- Integration with Analyzer table

**Files:**
- `frontend/src/components/Analyzer/PackSelector.jsx` (NEW)
- `backend/app/api/v1/product-sources/{id}/pack-variants` (NEW endpoint)

---

### **Priority 1.4: PPU Comparison Table** 🔶 HIGH
**Time:** 4-5 hours  
**Impact:** High - Visual comparison of all pack sizes

**Implementation:**
- Modal/Dialog component
- Table showing all variants with:
  - Pack size, Price, Cost, Fees, Profit, PPU, ROI
  - Sellable packs, Leftover units, Total profit
- Recommendation highlight
- Click to select target pack

**Files:**
- `frontend/src/components/ProductDetail/PackComparisonDialog.jsx` (NEW)
- `frontend/src/components/Analyzer/PPUComparisonTable.jsx` (NEW)

---

## 📋 **PHASE 2 - Brand Restrictions (WEEK 2)**

### **Priority 2.1: Brand Restriction Detection** 🔶 HIGH
**Time:** 6-8 hours  
**Impact:** Critical - Save hours of research

**Database:**
- `brand_restrictions` table
- `product_brand_flags` table

**Implementation:**
- Background job to check brand restrictions
- Integration with SP-API brand registry check
- Flag products in Analyzer table
- Warning badges on restricted products

---

### **Priority 2.2: Brand Restriction Management UI** 🔵 MEDIUM
**Time:** 3-4 hours  
**Impact:** Medium - Manual override and management

**Implementation:**
- Brand restrictions management page
- Add/remove brands from restriction list
- Override flags for specific products
- Bulk operations

---

## 📋 **PHASE 3 - Prep Instructions (WEEK 2-3)**

### **Priority 3.1: Prep Instructions Generator** 🔶 HIGH
**Time:** 4-5 hours  
**Impact:** High - Automate 3PL communication

**Implementation:**
- Use `PackVariantCalculator.generate_prep_instructions()`
- Generate instructions on order creation
- Store in `prep_instructions` table
- PDF generation service

---

### **Priority 3.2: Prep Instructions UI** 🔵 MEDIUM
**Time:** 3-4 hours  
**Impact:** Medium - View and manage prep instructions

**Implementation:**
- Prep instructions preview component
- PDF download
- Email to 3PL functionality
- Status tracking (pending/sent/completed)

---

## 📋 **PHASE 4 - Enhanced Upload System (WEEK 3-4)**

### **Priority 4.1: Column Auto-Detection** 🔶 HIGH
**Time:** 3-4 hours  
**Impact:** High - Faster uploads

**Implementation:**
- `ColumnMapper` class with pattern matching
- Auto-detect mappings on CSV upload
- User confirmation/adjustment interface
- Save as template

---

### **Priority 4.2: Template System** 🔵 MEDIUM
**Time:** 4-5 hours  
**Impact:** Medium - Reuse mappings

**Implementation:**
- Save/load templates
- Template management UI
- Share templates with team
- Default templates per supplier

---

## 📋 **PHASE 5 - Inventory & Forecasting (WEEK 4-5)**

### **Priority 5.1: Inventory Tracking** 🔵 MEDIUM
**Time:** 8-10 hours  
**Impact:** Medium - Better inventory management

**Implementation:**
- Track inventory at supplier/3PL/FBA
- Receiving and reconciliation
- Variance tracking

---

### **Priority 5.2: Reorder Automation** 🔵 MEDIUM
**Time:** 6-8 hours  
**Impact:** Medium - Automated reordering

**Implementation:**
- Reorder point calculation
- Automated PO generation
- Email to supplier

---

## 🚀 **QUICK WINS (Can Do Now)**

These can be implemented immediately and provide immediate value:

1. **Pricing Mode Toggle** (2-3 hours) - Already have data, just need UI
2. **Price Deviation Warnings** (1-2 hours) - Show when current price differs from 365d avg
3. **Pack Size Column in Analyzer** (1 hour) - Show recommended pack size
4. **PPU Column in Analyzer** (1 hour) - Show profit per unit

---

## 📊 **IMPACT vs EFFORT MATRIX**

```
HIGH IMPACT                  LOW EFFORT
───────────────────────────────────────
│ Pricing Mode Toggle      │          │
│ Pack Size Column         │          │
│ PPU Column               │          │
│                          │          │
│                          │          │
└──────────────────────────┴──────────┘
                          HIGH EFFORT

MEDIUM IMPACT              LOW EFFORT
───────────────────────────────────────
│ Price Deviation Warnings │          │
│ Prep Instructions UI     │          │
│                          │          │
└──────────────────────────┴──────────┘
                          HIGH EFFORT

HIGH IMPACT                MEDIUM EFFORT
───────────────────────────────────────
│ Pack Variant Discovery   │          │
│ PPU Comparison Table     │          │
│ Brand Restrictions       │          │
│                          │          │
└──────────────────────────┴──────────┘
                          HIGH EFFORT
```

---

## 🎯 **RECOMMENDED NEXT STEPS**

**This Week:**
1. ✅ Pricing Mode Toggle (2-3 hours)
2. ✅ Pack Variant Discovery API (4-6 hours)
3. ✅ PPU Column in Analyzer (1 hour)

**Next Week:**
4. Pack Selector Component
5. PPU Comparison Table
6. Brand Restriction Detection

---

**Total Estimated Time for Core Features:** 30-40 hours  
**Expected Impact:** 15-20 hours/week saved, 5-10% margin improvement

