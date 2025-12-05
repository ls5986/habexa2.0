# Pack Size & Staged Analysis - Code Discovery

**Complete inventory of existing code and exact changes needed**

---

## Table of Contents

1. [Current Quick Analyze Modal](#1-current-quick-analyze-modal)
2. [Current Add Product Dialog](#2-current-add-product-dialog)
3. [Current Keepa Client](#3-current-keepa-client)
4. [Current Analysis Endpoint](#4-current-analysis-endpoint)
5. [Current Analysis Task](#5-current-analysis-task)
6. [Current Batch Analyzer](#6-current-batch-analyzer)
7. [Current File Processing](#7-current-file-processing)
8. [Required Changes Summary](#8-required-changes-summary)

---

## 1. Current Quick Analyze Modal

**File:** `frontend/src/components/features/analyze/QuickAnalyzeModal.jsx`

### Current State

**Lines 15-21:** State variables
```jsx
const [identifierType, setIdentifierType] = useState('asin'); // 'asin' or 'upc'
const [asin, setAsin] = useState('');
const [upc, setUpc] = useState('');
const [quantity, setQuantity] = useState(1); // Pack quantity for UPC
const [buyCost, setBuyCost] = useState('');
const [moq, setMoq] = useState(1);
const [supplierId, setSupplierId] = useState('');
```

**Lines 369-392:** UPC input with pack quantity
```jsx
<Box display="flex" gap={2}>
  <TextField
    label="UPC"
    placeholder="123456789012"
    value={upc}
    onChange={(e) => setUpc(e.target.value.replace(/[^0-9]/g, '').slice(0, 14))}
    required
    fullWidth
    sx={{ fontFamily: 'monospace' }}
    disabled={loading}
    helperText="12-14 digit product code"
  />
  <TextField
    label="Pack Qty"
    placeholder="1"
    type="number"
    value={quantity}
    onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
    disabled={loading}
    sx={{ width: 120 }}
    helperText="Items per pack"
    inputProps={{ min: 1 }}
  />
</Box>
```

**Lines 395-416:** Cost input (single field)
```jsx
<Box display="flex" gap={2}>
  <TextField
    label="Your Cost"
    type="number"
    value={buyCost}
    onChange={(e) => setBuyCost(e.target.value)}
    required
    InputProps={{ startAdornment: '$' }}
    fullWidth
    disabled={loading}
    helperText={identifierType === 'upc' ? `Cost per pack of ${quantity}` : 'Cost per unit'}
  />
  <TextField
    label="MOQ"
    type="number"
    value={moq}
    onChange={(e) => setMoq(parseInt(e.target.value) || 1)}
    fullWidth
    disabled={loading}
    helperText="Minimum order quantity"
  />
</Box>
```

**Lines 47-56:** Submit handler
```jsx
const response = await analyzeSingle(
  identifier, 
  parseFloat(buyCost), 
  moq, 
  supplierId || null,
  identifierType,
  identifierType === 'upc' ? quantity : 1
);
```

### What's Missing

1. **Pack size toggle** - No checkbox to indicate "this is a case/pack"
2. **Wholesale cost field** - Only has single "Your Cost" field
3. **Per-unit calculation display** - Doesn't show calculated per-unit cost
4. **Pack size vs MOQ confusion** - `quantity` is used for pack size, but MOQ is separate

### Required Changes

**Add state:**
```jsx
const [isPack, setIsPack] = useState(false);
const [packSize, setPackSize] = useState(1);
const [wholesaleCost, setWholesaleCost] = useState('');
const [unitCost, setUnitCost] = useState('');
```

**Add calculated buy_cost:**
```jsx
const buyCost = useMemo(() => {
  if (isPack && packSize > 0 && wholesaleCost) {
    return (parseFloat(wholesaleCost) / packSize).toFixed(4);
  }
  return unitCost || buyCost; // Fallback to existing buyCost
}, [isPack, packSize, wholesaleCost, unitCost]);
```

**Replace cost input section (lines 395-416) with pack toggle UI**

---

## 2. Current Add Product Dialog

**File:** `frontend/src/pages/Products.jsx` (lines 847-935)

### Current State

**Lines 849:** Form state
```jsx
const [form, setForm] = useState({ 
  asin: '', 
  buy_cost: '', 
  supplier_id: '', 
  supplier_name: '', 
  moq: '1', 
  notes: '' 
});
```

**Lines 879-892:** ASIN and cost inputs
```jsx
<TextField
  label="ASIN"
  value={form.asin}
  onChange={(e) => setForm({ ...form, asin: e.target.value.toUpperCase() })}
  placeholder="B08VBVBS7N"
  required
/>
<TextField
  label="Buy Cost"
  type="number"
  value={form.buy_cost}
  onChange={(e) => setForm({ ...form, buy_cost: e.target.value })}
  InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
/>
```

**Lines 857-864:** Submit handler
```jsx
await api.post('/products', {
  asin: form.asin,
  buy_cost: form.buy_cost ? parseFloat(form.buy_cost) : null,
  supplier_id: form.supplier_id || null,
  supplier_name: form.supplier_name || null,
  moq: parseInt(form.moq) || 1,
  notes: form.notes
});
```

### What's Missing

1. **No UPC support** - Only ASIN input
2. **No pack size support** - Single cost field
3. **No identifier type toggle** - ASIN only

### Required Changes

**Same as Quick Analyze Modal** - Add pack size toggle, wholesale cost, UPC support

---

## 3. Current Keepa Client

**File:** `backend/app/services/keepa_client.py`

### Current State

**Lines 100-106:** `get_products_batch` method signature
```python
async def get_products_batch(
    self,
    asins: List[str],
    domain: int = 1,
    history: bool = False,
    days: int = 90
) -> Dict[str, dict]:
```

**Lines 139-150:** API call parameters
```python
params={
    "key": self.api_key,
    "domain": domain,
    "asin": ",".join(batch),
    "stats": days,
    "history": 1 if history else 0,
    "rating": 1,
}
```

**Lines 195-252:** `_parse_product` method - **ONLY EXTRACTS BASIC FIELDS**
```python
def _parse_product(self, product: dict) -> dict:
    """Parse Keepa product response into our format."""
    stats = product.get("stats", {})
    current_stats = stats.get("current", [])
    
    # ... extracts: title, brand, image_url, bsr, category, current_price, 
    # sales_drops_30/90/180, variation_count, amazon_in_stock, rating, review_count
```

### What's Missing

1. **No 365-day stats extraction** - Only uses `current` array
2. **No FBA/FBM seller counts** - Doesn't parse `offers` array
3. **No lowest price extraction** - Doesn't use `stats.365` field
4. **No date extraction** - Doesn't convert Keepa time to dates

### Required Changes

**Create new method:** `extract_all_keepa_data(keepa_product: dict) -> dict`

**Extract from `stats.365`:**
- `fba_lowest_365d` (from `stats.365.NEW_FBA_MIN[0]`)
- `fba_lowest_date` (from `stats.365.NEW_FBA_MIN[1]` - convert Keepa time)
- `fbm_lowest_365d` (from `stats.365.NEW_FBM_MIN[0]`)
- `fbm_lowest_date` (from `stats.365.NEW_FBM_MIN[1]`)
- `amazon_lowest_365d` (from `stats.365.AMAZON_MIN[0]`)

**Extract from `offers` array:**
- `fba_seller_count` (count where `isFBA: true`)
- `fbm_seller_count` (count where `isFBA: false`)

**Add helper functions:**
- `keepa_to_date(keepa_time)` - Convert Keepa time to datetime
- `cents_to_dollars(cents)` - Convert cents to dollars

---

## 4. Current Analysis Endpoint

**File:** `backend/app/api/v1/analysis.py`

### Current State

**Lines 22-30:** Request model
```python
class ASINInput(BaseModel):
    asin: Optional[str] = None
    upc: Optional[str] = None
    identifier_type: str = "asin"
    quantity: Optional[int] = 1  # Pack quantity for UPC products
    buy_cost: float
    moq: int = 1
    supplier_id: Optional[str] = None
```

**Lines 124-128:** Pack quantity adjustment (WRONG LOGIC)
```python
# Adjust buy_cost if UPC and pack quantity > 1
adjusted_buy_cost = request.buy_cost
if identifier_type == "upc" and pack_quantity > 1:
    # buy_cost is per pack, calculate per unit for analysis
    adjusted_buy_cost = request.buy_cost / pack_quantity
```

**Lines 138-148:** Job metadata
```python
"metadata": {
    "asin": asin,
    "upc": upc_value,
    "identifier_type": identifier_type,
    "pack_quantity": pack_quantity,
    "product_id": product_id,
    "buy_cost": adjusted_buy_cost,
    "original_buy_cost": request.buy_cost,
    "moq": request.moq,
    "supplier_id": request.supplier_id
}
```

### What's Missing

1. **No pack_size field** - Uses `quantity` which is confusing
2. **No wholesale_cost field** - Can't track original case cost
3. **Wrong calculation logic** - Assumes `buy_cost` is per pack, but should be explicit

### Required Changes

**Update request model:**
```python
class ASINInput(BaseModel):
    asin: Optional[str] = None
    upc: Optional[str] = None
    identifier_type: str = "asin"
    buy_cost: float  # Per-unit cost (calculated from wholesale_cost / pack_size)
    pack_size: int = 1  # Units per case
    wholesale_cost: Optional[float] = None  # Cost for entire case
    moq: int = 1  # Minimum cases to order
    supplier_id: Optional[str] = None
```

**Remove pack quantity adjustment logic** - `buy_cost` is already per-unit

**Update metadata:**
```python
"metadata": {
    "asin": asin,
    "upc": upc_value,
    "identifier_type": identifier_type,
    "product_id": product_id,
    "buy_cost": request.buy_cost,  # Already per-unit
    "pack_size": request.pack_size,
    "wholesale_cost": request.wholesale_cost,
    "moq": request.moq,
    "supplier_id": request.supplier_id
}
```

---

## 5. Current Analysis Task

**File:** `backend/app/tasks/analysis.py`

### Current State

**Lines 24-28:** Task signature
```python
def analyze_single_product(self, job_id: str, user_id: str, product_id: str, asin: str, buy_cost: float = None):
```

**Lines 34-39:** Get metadata
```python
job_data = job.get()
metadata = job_data.get("metadata", {})
buy_cost = buy_cost or metadata.get("buy_cost") or metadata.get("original_buy_cost")
moq = metadata.get("moq", 1)
supplier_id = metadata.get("supplier_id")
```

**Lines 80-88:** Create product_source
```python
supabase.table("product_sources").insert({
    "user_id": user_id,
    "product_id": product_id,
    "supplier_id": supplier_id,
    "buy_cost": buy_cost,
    "moq": moq,
    "stage": "reviewed",
    "source": "quick_analyze"
}).execute()
```

### What's Missing

1. **No pack_size in product_source** - Missing field
2. **No wholesale_cost in product_source** - Missing field
3. **No staged analysis** - Runs all stages immediately
4. **No Keepa 365-day extraction** - Only basic Keepa data

### Required Changes

**Update product_source insert (lines 80-88):**
```python
supabase.table("product_sources").insert({
    "user_id": user_id,
    "product_id": product_id,
    "supplier_id": supplier_id,
    "buy_cost": buy_cost,  # Per-unit
    "pack_size": metadata.get("pack_size", 1),
    "wholesale_cost": metadata.get("wholesale_cost"),
    "moq": moq,
    "stage": "reviewed",
    "source": "quick_analyze"
}).execute()
```

**Implement staged analysis:**
- Stage 2: SP-API (pricing + fees) → Calculate ROI → Filter if ROI < 30%
- Stage 3: Keepa Basic (stats=1, history=0) → Extract BSR, competition
- Stage 4: Keepa Full (stats=1, history=1, days=365) → Extract 365-day lows

**Update analyses table with new fields:**
- `analysis_stage`, `stage2_roi`, `passed_stage2`
- `fba_lowest_365d`, `fba_lowest_date`, `fbm_lowest_365d`, `fbm_lowest_date`
- `lowest_was_fba`, `amazon_was_seller`
- `worst_case_profit`, `still_profitable_at_worst`
- `fba_seller_count`, `fbm_seller_count`

---

## 6. Current Batch Analyzer

**File:** `backend/app/services/batch_analyzer.py`

### Current State

**Lines 24-28:** `analyze_products` signature
```python
async def analyze_products(
    self,
    asins: List[str],
    marketplace_id: str = "ATVPDKIKX0DER"
) -> Dict[str, dict]:
```

**Lines 40-63:** Step 1 - Keepa Basic (history=False)
```python
keepa_data = await keepa_client.get_products_batch(asins, domain=1, history=False, days=90)
```

**Lines 65-85:** Step 2 - SP-API Pricing
```python
pricing_data = await sp_api_client.get_competitive_pricing_batch(batch, marketplace_id)
```

**Lines 107-130:** Step 3 - SP-API Fees
```python
fees_data = await sp_api_client.get_fees_estimate_batch(batch, marketplace_id)
```

### What's Missing

1. **No buy_cost parameter** - Can't calculate ROI/profit
2. **No staged filtering** - Processes all products through all stages
3. **No Keepa Full stage** - Only uses Keepa Basic
4. **No 365-day extraction** - Doesn't extract lowest prices

### Required Changes

**Add buy_cost parameter:**
```python
async def analyze_products(
    self,
    asins: List[str],
    buy_costs: Dict[str, float],  # {asin: buy_cost}
    marketplace_id: str = "ATVPDKIKX0DER"
) -> Dict[str, dict]:
```

**Add Stage 2 filtering:**
```python
# After SP-API fees, calculate ROI
for asin in asins:
    buy_cost = buy_costs.get(asin, 0)
    sell_price = results[asin].get("sell_price", 0)
    fees_total = results[asin].get("fees_total", 0)
    
    net_profit = sell_price - fees_total - buy_cost
    roi = (net_profit / buy_cost) * 100 if buy_cost > 0 else 0
    
    results[asin]["net_profit"] = net_profit
    results[asin]["roi"] = roi
    results[asin]["passed_stage2"] = roi >= 30 and net_profit >= 3
```

**Add Stage 3 - Keepa Basic (only for products passing Stage 2):**
```python
# Only fetch Keepa Basic for products that passed Stage 2
passed_stage2_asins = [a for a in asins if results[a].get("passed_stage2")]
if passed_stage2_asins:
    keepa_basic = await keepa_client.get_products_batch(
        passed_stage2_asins, 
        domain=1, 
        history=False, 
        days=90,
        offers=20  # Get offers for FBA/FBM counts
    )
    # Extract FBA/FBM counts, BSR, sales drops
```

**Add Stage 4 - Keepa Full (only for top candidates):**
```python
# Only fetch Keepa Full for products that passed Stage 3
passed_stage3_asins = [a for a in passed_stage2_asins if results[a].get("passed_stage3")]
if passed_stage3_asins:
    keepa_full = await keepa_client.get_products_batch(
        passed_stage3_asins,
        domain=1,
        history=True,  # Enable history
        days=365,  # 365 days
        offers=20
    )
    # Extract 365-day lows using extract_all_keepa_data()
```

---

## 7. Current File Processing

**File:** `backend/app/tasks/file_processing.py`

### Current State

**Lines 85-139:** `parse_kehe_row` function
```python
def parse_kehe_row(row: dict) -> Optional[Dict]:
    # ...
    wholesale = row.get("WHOLESALE") or row.get("wholesale")
    pack = row.get("PACK") or row.get("pack")
    
    # Parse cost
    buy_cost = None
    if wholesale is not None:
        try:
            buy_cost = float(str(wholesale).replace("$", "").replace(",", "").strip())
        except (ValueError, TypeError):
            pass
    
    # Parse MOQ (PACK column)
    moq = 1
    if pack is not None:
        try:
            pack_val = str(pack).replace(",", "").strip().replace(".0", "")
            moq = max(1, int(float(pack_val)))
        except (ValueError, TypeError):
            pass
    
    return {
        "upc": upc_str,
        "buy_cost": buy_cost,  # WRONG - this is wholesale_cost, not per-unit
        "moq": moq,  # WRONG - this is pack_size, not MOQ
        # ...
    }
```

**Lines 491-501:** Deal creation
```python
deals_dict[key] = {
    "product_id": product_id,
    "supplier_id": supplier_id,
    "buy_cost": parsed.get("buy_cost"),  # WRONG - wholesale cost
    "moq": parsed.get("moq", 1),  # WRONG - pack_size
    # Missing: pack_size, wholesale_cost, supplier_sku
    # ...
}
```

### What's Missing

1. **Wrong calculation** - Sets `buy_cost = wholesale_cost` (should divide by pack_size)
2. **Confused fields** - Uses `moq` for `pack_size`
3. **Missing fields** - No `supplier_sku`, `wholesale_cost`, `promo_qty`

### Required Changes

**Update `parse_kehe_row` (lines 85-139):**
- Extract `ITEM` column → `supplier_sku`
- Extract `PACK` column → `pack_size` (not `moq`)
- Extract `WHOLESALE` column → `wholesale_cost`
- Calculate `buy_cost = wholesale_cost / pack_size`
- Extract `PROMO QTY` column → `promo_qty`
- Return all new fields

**Update deal creation (lines 491-501):**
- Include `pack_size`, `wholesale_cost`, `supplier_sku`, `promo_qty`

---

## 8. Required Changes Summary

### Database Migration

**File:** `migrations/ADD_PACK_AND_ANALYSIS_FIELDS.sql`

```sql
-- Product Sources
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS pack_size INTEGER DEFAULT 1;
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS wholesale_cost NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS supplier_sku TEXT;
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS promo_wholesale_cost NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS promo_qty INTEGER;

-- Analyses
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS analysis_stage TEXT DEFAULT 'pending';
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS stage2_roi NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS passed_stage2 BOOLEAN DEFAULT FALSE;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fba_lowest_365d NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fba_lowest_date TIMESTAMPTZ;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fbm_lowest_365d NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fbm_lowest_date TIMESTAMPTZ;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS lowest_was_fba BOOLEAN;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_was_seller BOOLEAN DEFAULT FALSE;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS worst_case_profit NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS still_profitable_at_worst BOOLEAN;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fba_seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fbm_seller_count INTEGER;
```

### Backend Files to Modify

| File | Changes |
|------|---------|
| `backend/app/tasks/file_processing.py` | Fix `parse_kehe_row` to calculate `buy_cost = wholesale_cost / pack_size` |
| `backend/app/api/v1/analysis.py` | Add `pack_size`, `wholesale_cost` to request model |
| `backend/app/tasks/analysis.py` | Add pack fields to product_source, implement staged analysis |
| `backend/app/services/batch_analyzer.py` | Add `buy_costs` parameter, implement Stage 2/3/4 filtering |
| `backend/app/services/keepa_client.py` | Add `extract_all_keepa_data()` method for 365-day extraction |

### Frontend Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/features/analyze/QuickAnalyzeModal.jsx` | Add pack toggle, wholesale cost field, per-unit calculation display |
| `frontend/src/pages/Products.jsx` (AddProductDialog) | Same as Quick Analyze Modal |

### New Files to Create

| File | Purpose |
|------|---------|
| `backend/app/services/keepa_data_extractor.py` | Extract 365-day stats, FBA/FBM counts from Keepa response |

---

## Next Steps

1. **Run database migration** - Add all new columns
2. **Update file_processing.py** - Fix pack size calculation
3. **Create keepa_data_extractor.py** - Extract 365-day data
4. **Update batch_analyzer.py** - Add staged filtering
5. **Update analysis.py** - Add pack fields to request/response
6. **Update analysis task** - Save pack fields, implement stages
7. **Update frontend modals** - Add pack size UI

**Ready for line-by-line implementation!**

