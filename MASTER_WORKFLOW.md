# Master Product Profitability Analysis Workflow

**Complete documentation for Celery workers - Single source of truth**

---

## Table of Contents

1. [Overview](#overview)
2. [Stage 1: Quick Profitability Filter](#stage-1-quick-profitability-filter)
3. [Stage 2: Deep Analysis](#stage-2-deep-analysis)
4. [Profitability Scoring System](#profitability-scoring-system)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Implementation Guide](#implementation-guide)

---

## Overview

**Two-stage pipeline:**
1. **Stage 1:** Quick filter using batch APIs (20 items per request) - filters out unprofitable products
2. **Stage 2:** Deep analysis for profitable products - gets all 9 profitability fields

**Input:** List of UPCs or ASINs with Buy Costs  
**Output:** Complete profitability data with scores

**Note:** If input is already ASINs, skip Step 1.1 (UPC → ASIN conversion)

---

## Stage 1: Quick Profitability Filter

**Purpose:** Quickly identify profitable products using batch APIs  
**Goal:** Filter out unprofitable products before expensive API calls  
**Threshold:** Stage 1 Score >= 50 → Proceed to Stage 2

**Input Handling:**
- If input is **UPCs**: Execute Step 1.1 to convert UPC → ASIN
- If input is **ASINs**: Skip Step 1.1, proceed directly to Step 1.2

### Step 1.1: Batch UPC → ASIN Conversion (Skip if input is already ASINs)

**API:** Amazon SP-API Catalog Items  
**Endpoint:** `GET /catalog/2022-04-01/items`  
**Batch Size:** 20 UPCs per request  
**Rate Limit:** 2 requests/second, burst of 2  
**Delay Between Batches:** 0.5 seconds

**Request:**
```
GET /catalog/2022-04-01/items
  ?identifiers=UPC1,UPC2,UPC3,...,UPC20
  &identifiersType=UPC
  &marketplaceIds=ATVPDKIKX0DER
  &includedData=summaries,identifiers,images,salesRanks
```

**Response:**
```json
{
  "items": [
    {
      "asin": "B005HNOCHW",
      "identifiers": [
        {"identifierType": "UPC", "identifier": "607959300047"}
      ],
      "attributes": {
        "item_name": [{"value": "Product Title"}],
        "brand": [{"value": "Brand Name"}]
      }
    }
  ]
}
```

**Data Extracted:**
- ASIN (required for all next steps)
- Title
- Brand

**Implementation:**
```python
def batch_upc_to_asin(upcs: List[str]) -> Dict[str, str]:
    """Convert UPCs to ASINs in batches of 20."""
    upc_to_asin = {}
    
    for i in range(0, len(upcs), 20):
        batch_upcs = upcs[i:i+20]
        response = sp_api.search_catalog_batch(batch_upcs)
        
        for upc, item in response.items():
            if item and 'asin' in item:
                upc_to_asin[upc] = item['asin']
        
        time.sleep(0.5)  # Rate limiting
    
    return upc_to_asin

def is_asin(identifier: str) -> bool:
    """
    Check if identifier is an ASIN.
    ASINs: Start with B and are 10 characters, or numeric and 10 digits
    """
    identifier = identifier.strip()
    # ASIN format: B followed by 9 alphanumeric, or 10 alphanumeric starting with letter
    if len(identifier) == 10:
        # Amazon ASINs typically start with B, but can also be numeric
        # Most common: B + 9 alphanumeric characters
        if identifier.startswith('B') and identifier[1:].isalnum():
            return True
        # Some ASINs are all numeric (10 digits)
        if identifier.isdigit():
            return True
    return False

def normalize_input(identifiers: List[str]) -> Dict[str, str]:
    """
    Normalize input - determine if UPCs or ASINs and convert if needed.
    
    Args:
        identifiers: List of UPCs or ASINs
        
    Returns: {identifier: asin, ...}
    """
    asin_map = {}
    upcs_to_convert = []
    
    for identifier in identifiers:
        if is_asin(identifier):
            # Already an ASIN - use directly
            asin_map[identifier] = identifier
        else:
            # Assume it's a UPC - needs conversion
            upcs_to_convert.append(identifier)
    
    # Convert UPCs to ASINs if needed
    if upcs_to_convert:
        upc_to_asin = batch_upc_to_asin(upcs_to_convert)
        asin_map.update(upc_to_asin)
    
    return asin_map
```

**Output:** `{identifier: ASIN}` - Map of input identifier (UPC or ASIN) to ASIN. Filter out products without ASINs.

---

### Step 1.2: Batch Competitive Pricing

**API:** Amazon SP-API Batch Pricing  
**Endpoint:** `POST /batches/products/pricing/v0/itemOffers`  
**Batch Size:** 20 ASINs per request  
**Rate Limit:** 0.1 requests/second, burst of 1  
**Delay Between Batches:** 10 seconds

**Request:**
```json
POST /batches/products/pricing/v0/itemOffers
{
  "requests": [
    {
      "uri": "/products/pricing/v0/items/B005HNOCHW/offers",
      "method": "GET",
      "MarketplaceId": "ATVPDKIKX0DER",
      "ItemCondition": "New"
    }
    // ... up to 20 items
  ]
}
```

**Response:**
```json
{
  "responses": [
    {
      "body": {
        "payload": {
          "Summary": {
            "BuyBoxPrices": [{
              "LandedPrice": {"Amount": 69.14, "CurrencyCode": "USD"}
            }],
            "NumberOfOffers": [{"Count": 1}]
          },
          "Offers": [
            {
              "SellerId": "Amazon",
              "Price": {
                "LandedPrice": {"Amount": 69.14, "CurrencyCode": "USD"}
              },
              "Quantity": {"Value": 0}
            }
          ]
        }
      }
    }
  ]
}
```

**Data Extracted:**
- **Sell Price**: `payload.Summary.BuyBoxPrices[0].LandedPrice.Amount`
- **Seller Count**: `payload.Summary.NumberOfOffers[0].Count`
- **Amazon is Seller**: Check if any `Offers[].SellerId == "Amazon"`
- **Amazon Qty**: `Offers[].Quantity.Value` (if Amazon is seller)

**Implementation:**
```python
def batch_get_pricing(asins: List[str]) -> Dict[str, Dict]:
    """Get competitive pricing for ASINs in batches of 20."""
    results = {}
    
    for i in range(0, len(asins), 20):
        batch_asins = asins[i:i+20]
        pricing_data = sp_api.get_competitive_pricing(batch_asins)
        results.update(pricing_data)
        time.sleep(10)  # Rate limiting
    
    return results
```

**Output:** `{ASIN: {sell_price, seller_count, amazon_is_seller, amazon_qty}}`

---

### Step 1.3: Batch Fee Estimates

**API:** Amazon SP-API Fees Estimate  
**Endpoint:** `POST /products/fees/v0/feesEstimate`  
**Batch Size:** 20 items per request  
**Rate Limit:** 0.5 requests/second, burst of 1  
**Delay Between Batches:** 2 seconds

**Request:**
```json
POST /products/fees/v0/feesEstimate
[
  {
    "FeesEstimateRequest": {
      "MarketplaceId": "ATVPDKIKX0DER",
      "IsAmazonFulfilled": true,
      "PriceToEstimateFees": {
        "ListingPrice": {
          "Amount": 69.14,
          "CurrencyCode": "USD"
        },
        "Shipping": {"Amount": 0.0, "CurrencyCode": "USD"},
        "Points": {
          "PointsNumber": 0,
          "PointsMonetaryValue": {"Amount": 0.0, "CurrencyCode": "USD"}
        }
      },
      "Identifier": "B005HNOCHW"
    },
    "IdType": "ASIN",
    "IdValue": "B005HNOCHW"
  }
  // ... up to 20 items
]
```

**Response:**
```json
[
  {
    "FeesEstimateResult": {
      "FeesEstimate": {
        "TotalFeesEstimate": {"Amount": 14.37, "CurrencyCode": "USD"},
        "FeeDetailList": [
          {
            "FeeType": "ReferralFee",
            "FeeAmount": {"Amount": 10.37, "CurrencyCode": "USD"}
          },
          {
            "FeeType": "FBAFees",
            "FeeAmount": {"Amount": 4.00, "CurrencyCode": "USD"}
          }
        ]
      }
    }
  }
]
```

**Data Extracted:**
- **Total Fees**: `FeesEstimateResult.FeesEstimate.TotalFeesEstimate.Amount`
- **Referral Fee**: `FeeDetailList[]` where `FeeType == "ReferralFee"`
- **FBA Fee**: `FeeDetailList[]` where `FeeType == "FBAFees"`

**Fallback (if API fails):**
- Referral Fee = Sell Price × 0.15
- FBA Fee = $4.00
- Total Fees = Referral Fee + FBA Fee

**Implementation:**
```python
def batch_get_fees(asin_price_pairs: List[tuple]) -> Dict[str, Dict]:
    """Get fee estimates in batches of 20."""
    results = {}
    
    for i in range(0, len(asin_price_pairs), 20):
        batch = asin_price_pairs[i:i+20]
        fees_data = sp_api.get_fees_estimate_batch(batch)
        results.update(fees_data)
        time.sleep(2)  # Rate limiting
    
    return results
```

**Output:** `{ASIN: {total_fees, referral_fee, fba_fee}}`

---

### Step 1.4: Calculate Stage 1 Profitability Score

**Formulas:**
```python
net_profit = sell_price - buy_cost - total_fees
roi = (net_profit / buy_cost) * 100 if buy_cost > 0 else 0
```

**Stage 1 Scoring (100 points max):**

| Component | Points | Criteria |
|-----------|--------|----------|
| **ROI** | 0-40 | 100%+ = 40, 50%+ = 30, 30%+ = 20, 15%+ = 10 |
| **Seller Count** | 0-20 | 1 seller = 20, ≤3 = 15, ≤5 = 10, ≤10 = 5 |
| **Amazon Competition** | 0-20 | No Amazon = 20, Amazon qty 0 = 10 |
| **Net Profit** | 0-20 | $20+ = 20, $10+ = 15, $5+ = 10, $2+ = 5 |

**Implementation:**
```python
def calculate_stage1_score(roi, seller_count, amazon_is_seller, amazon_qty, net_profit):
    """Calculate Stage 1 profitability score (100 points max)."""
    score = 0
    
    # ROI component (0-40)
    if roi >= 100:
        score += 40
    elif roi >= 50:
        score += 30
    elif roi >= 30:
        score += 20
    elif roi >= 15:
        score += 10
    
    # Seller count component (0-20)
    if seller_count == 1:
        score += 20
    elif seller_count <= 3:
        score += 15
    elif seller_count <= 5:
        score += 10
    elif seller_count <= 10:
        score += 5
    
    # Amazon competition component (0-20)
    if not amazon_is_seller:
        score += 20
    elif amazon_qty == 0:
        score += 10
    
    # Net profit component (0-20)
    if net_profit >= 20:
        score += 20
    elif net_profit >= 10:
        score += 15
    elif net_profit >= 5:
        score += 10
    elif net_profit >= 2:
        score += 5
    
    return score
```

**Threshold:**
```
IF stage1_score >= 50:
    → Proceed to Stage 2 (Deep Analysis)
ELSE:
    → Mark as "Not Profitable" and skip Stage 2
```

**Alternative Simple Threshold:**
```
IF (ROI >= 30% AND Net Profit >= $5) AND 
   (Seller Count <= 5) AND 
   (NOT Amazon is Seller):
    → Proceed to Stage 2
```

**Output:** Products with Stage 1 score and pass/fail status

---

## Stage 2: Deep Analysis (Profitable Products Only)

**Purpose:** Get detailed data for products that passed Stage 1  
**Input:** ASINs of profitable products  
**Output:** Complete profitability data with all 9 fields

### Step 2.1: Keepa Product Data

**API:** Keepa API  
**Endpoint:** `GET /product`  
**Batch Size:** 100 ASINs per request  
**Rate Limit:** Token-based (1 second delay recommended)

**Request:**
```
GET /product
  ?key={KEEPA_API_KEY}
  &domain=1
  &asin=ASIN1,ASIN2,...,ASIN100
  &stats=365
  &history=1
  &rating=1
  &offers=1
```

**Response:**
```json
{
  "products": [
    {
      "asin": "B005HNOCHW",
      "title": "Product Title",
      "brand": "Brand Name",
      "categoryName": "Grocery & Gourmet Food",
      "salesRank": 250,
      "currentPrice": 69.14,
      "csv": [1234567890, 6914, 6914, ...],
      "salesRankDrops30": 2,
      "salesRankDrops90": 5,
      "salesRankDrops180": 8
    }
  ]
}
```

**Data Extracted:**

1. **BSR**: `salesRank`
2. **Current Price**: `currentPrice`
3. **Lowest Price (365 days)**: Parse from `csv` array
4. **Sales Rank Drops**: `salesRankDrops30/90/180`
5. **Category**: `categoryName`
6. **Title, Brand**: Verify against catalog data

**Calculations:**

**Lowest Price (365 days):**
```python
def parse_lowest_price_365d(csv_data):
    """Parse Keepa CSV to find lowest price in last 365 days."""
    prices = []
    # CSV format: [time, Amazon price, marketplace price, ...]
    # Price is in cents, time is minutes since 2008-01-01
    for i in range(1, min(len(csv_data), 730), 2):
        if csv_data[i] and csv_data[i] > 0:
            prices.append(csv_data[i] / 100.0)  # Convert cents to dollars
    return min(prices) if prices else None
```

**Sold Last Month (Estimated):**
```python
def estimate_monthly_sales(bsr, category):
    """
    Estimate monthly sales from BSR and category.
    Formula: (1,000,000 / BSR) × Category Multiplier
    """
    multipliers = {
        'Electronics': 0.8,
        'Home & Kitchen': 0.6,
        'Grocery & Gourmet Food': 1.2,
        'Sports & Outdoors': 0.4,
        'Health & Personal Care': 0.7,
        'Toys & Games': 0.5,
        'default': 0.5
    }
    
    multiplier = multipliers.get(category, multipliers['default'])
    
    if bsr and bsr > 0:
        estimated_sales = (1000000 / bsr) * multiplier
        return max(1, int(estimated_sales))
    return None
```

**% of BSR:**
```python
def calculate_bsr_percentage(bsr, category):
    """
    Calculate what % of category the BSR represents.
    Lower % = closer to #1 = better
    """
    category_sizes = {
        'Electronics': 1000000,
        'Home & Kitchen': 500000,
        'Grocery & Gourmet Food': 200000,
        'Sports & Outdoors': 300000,
        'Health & Personal Care': 400000,
        'Toys & Games': 250000,
        'default': 100000
    }
    
    category_size = category_sizes.get(category, category_sizes['default'])
    
    if bsr and category_size:
        return (bsr / category_size) * 100
    return None
```

**Implementation:**
```python
def batch_get_keepa_data(asins: List[str]) -> Dict[str, Dict]:
    """Get Keepa data in batches of 100."""
    results = {}
    
    for i in range(0, len(asins), 100):
        batch_asins = asins[i:i+100]
        keepa_data = keepa_api.batch_lookup_by_asin(batch_asins, stats=365, history=1)
        results.update(keepa_data)
        time.sleep(1)  # Rate limiting
    
    return results
```

**Output:** `{ASIN: {bsr, lowest_price_365d, current_price, sales_rank_drops_30/90/180, category, sold_last_month, bsr_percentage}}`

---

### Step 2.2: SP-API Catalog Item Details

**API:** Amazon SP-API Catalog  
**Endpoint:** `GET /catalog/2022-04-01/items/{asin}`  
**Purpose:** Get manufacturer info to check if manufacturer is seller

**Request:**
```
GET /catalog/2022-04-01/items/{asin}
  ?marketplaceIds=ATVPDKIKX0DER
  &includedData=attributes,identifiers
```

**Response:**
```json
{
  "attributes": {
    "manufacturer": [{"value": "Brand Name"}],
    "item_dimensions": {...},
    "item_weight": {...}
  }
}
```

**Manufacturer is Seller Check:**
```python
def check_manufacturer_is_seller(asin, pricing_data):
    """
    Check if manufacturer is in seller list.
    1. Get manufacturer from catalog
    2. Get seller list from pricing data (Step 1.2)
    3. Compare
    """
    catalog_item = sp_api.get_catalog_item(asin)
    manufacturer = catalog_item.get('attributes', {}).get('manufacturer', [{}])[0].get('value')
    
    sellers = extract_seller_list(pricing_data)
    
    return manufacturer.lower() in [s.lower() for s in sellers]
```

**Output:** Manufacturer name and `manufacturer_is_seller` boolean

---

### Step 2.3: SP-API Product Eligibility (Hazmat)

**API:** Amazon SP-API Product Eligibility  
**Endpoint:** `GET /fba/inbound/v0/eligibility`  
**Purpose:** Check if product is hazmat

**Request:**
```
GET /fba/inbound/v0/eligibility
  ?MarketplaceIds=ATVPDKIKX0DER
  &ASINList=ASIN1,ASIN2,...,ASIN20
```

**Response:**
```json
{
  "eligibility": [
    {
      "asin": "B005HNOCHW",
      "isHazmat": false
    }
  ]
}
```

**Output:** `hazmat` boolean

---

### Step 2.4: Calculate Final Profitability Score

**Complete Scoring System (100 points max):**

| Field | Points | Scoring Criteria |
|-------|--------|------------------|
| **ROI** | 0-25 | 100%+ = 25, 50%+ = 20, 30%+ = 15, 15%+ = 10, 5%+ = 5 |
| **BSR** | 0-20 | ≤100 = 20, ≤500 = 15, ≤1000 = 10, ≤5000 = 5 |
| **% of BSR** | 0-15 | ≤1% = 15, ≤5% = 12, ≤10% = 8, ≤25% = 5 |
| **Sold Last Month** | 0-15 | 100+ = 15, 50+ = 12, 20+ = 8, 10+ = 5 |
| **Seller Count** | 0-10 | 1 = 10, ≤3 = 8, ≤5 = 5, ≤10 = 2 |
| **Hazmat** | 0-5 | Not Hazmat = 5 |
| **Amazon is Seller** | 0-5 | Not Amazon = 5 |
| **Amazon Qty** | 0-3 | 0 or no Amazon = 3 |
| **Manufacturer is Seller** | 0-2 | Not Manufacturer = 2 |

**Implementation:**
```python
def calculate_final_score(data):
    """Calculate final profitability score from all 9 fields (100 points max)."""
    score = 0
    
    # 1. ROI (0-25)
    roi = data['roi']
    if roi >= 100:
        score += 25
    elif roi >= 50:
        score += 20
    elif roi >= 30:
        score += 15
    elif roi >= 15:
        score += 10
    elif roi >= 5:
        score += 5
    
    # 2. BSR (0-20)
    bsr = data['bsr']
    if bsr and bsr <= 100:
        score += 20
    elif bsr <= 500:
        score += 15
    elif bsr <= 1000:
        score += 10
    elif bsr <= 5000:
        score += 5
    
    # 3. % of BSR (0-15)
    bsr_pct = data['bsr_percentage']
    if bsr_pct and bsr_pct <= 1:
        score += 15
    elif bsr_pct <= 5:
        score += 12
    elif bsr_pct <= 10:
        score += 8
    elif bsr_pct <= 25:
        score += 5
    
    # 4. Sold Last Month (0-15)
    sales = data['sold_last_month']
    if sales and sales >= 100:
        score += 15
    elif sales >= 50:
        score += 12
    elif sales >= 20:
        score += 8
    elif sales >= 10:
        score += 5
    
    # 5. Seller Count (0-10)
    sellers = data['seller_count']
    if sellers == 1:
        score += 10
    elif sellers <= 3:
        score += 8
    elif sellers <= 5:
        score += 5
    elif sellers <= 10:
        score += 2
    
    # 6. Hazmat (0-5)
    if not data['hazmat']:
        score += 5
    
    # 7. Amazon is Seller (0-5)
    if not data['amazon_is_seller']:
        score += 5
    
    # 8. Amazon Qty (0-3)
    if data['amazon_qty'] == 0 or not data['amazon_is_seller']:
        score += 3
    
    # 9. Manufacturer is Seller (0-2)
    if not data['manufacturer_is_seller']:
        score += 2
    
    return score
```

**Final Classification:**
```
Score >= 70:  "Highly Profitable" (Top Priority)
Score >= 50:  "Profitable" (Good Opportunity)
Score >= 30:  "Marginally Profitable" (Consider if inventory allows)
Score < 30:   "Not Profitable" (Skip)
```

---

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│              INPUT: List of UPCs or ASINs                   │
│              (with Buy Costs from Excel)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  INPUT TYPE? │
                    └──────┬───────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
        ▼ UPCs                                 ▼ ASINs
┌───────────────────────┐          ┌───────────────────────┐
│  Step 1.1: UPC → ASIN  │          │  Skip Step 1.1        │
│  (20 per request)     │          │  Use ASINs directly   │
└───────────┬─────────────┘          └───────────┬───────────┘
            │                                    │
            └──────────────┬─────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 1: QUICK PROFITABILITY FILTER            │
│                                                              │
│  Step 1.2: Batch Competitive Pricing (20 per request)      │
│            API: POST /batches/products/pricing/v0/itemOffers│
│            Rate: 0.1 req/sec, Delay: 10s                   │
│            └─→ Extract: Sell Price, Seller Count,          │
│                Amazon is Seller, Amazon Qty                 │
│                                                              │
│  Step 1.2: Batch Competitive Pricing (20 per request)      │
│            API: POST /batches/products/pricing/v0/itemOffers│
│            Rate: 0.1 req/sec, Delay: 10s                   │
│            └─→ Extract: Sell Price, Seller Count,          │
│                Amazon is Seller, Amazon Qty                 │
│                                                              │
│  Step 1.3: Batch Fee Estimates (20 per request)            │
│            API: POST /products/fees/v0/feesEstimate        │
│            Rate: 0.5 req/sec, Delay: 2s                    │
│            └─→ Extract: FBA Fee, Referral Fee, Total Fees  │
│                                                              │
│  Step 1.4: Calculate Stage 1 Score (100 points max)         │
│            └─→ Filter: Score >= 50 → Stage 2                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  PROFITABLE? │
                    └──────┬───────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
        ▼ NO                                   ▼ YES
┌───────────────┐                    ┌─────────────────────────────┐
│ Mark as      │                    │  STAGE 2: DEEP ANALYSIS     │
│ "Not         │                    │                              │
│ Profitable"  │                    │  Step 2.1: Keepa Data        │
│              │                    │    API: GET /product          │
│ Skip Stage 2 │                    │    Batch: 100 ASINs          │
└──────────────┘                    │    └─→ BSR, Price History,   │
                                    │        Sales Rank Drops,     │
                                    │        Sold Last Month,      │
                                    │        % of BSR               │
                                    │                              │
                                    │  Step 2.2: Catalog Details  │
                                    │    API: GET /catalog/.../items│
                                    │    └─→ Manufacturer          │
                                    │                              │
                                    │  Step 2.3: Product Eligibility│
                                    │    API: GET /fba/inbound/... │
                                    │    └─→ Hazmat                │
                                    │                              │
                                    │  Step 2.4: Calculate Final   │
                                    │    Score (100 points)        │
                                    └──────────────────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  FINAL RESULTS   │
                                    │  (All 9 Fields)  │
                                    └──────────────────┘
```

---

## API Call Summary

### Stage 1 (Per 100 Products)

| Step | API | Batch Size | Calls | Rate Limit | Delay | Total Time |
|------|-----|------------|-------|------------|-------|------------|
| 1.1 | Catalog | 20 | 5 | 2/sec | 0.5s | ~2.5s |
| 1.2 | Pricing | 20 | 5 | 0.1/sec | 10s | ~50s |
| 1.3 | Fees | 20 | 5 | 0.5/sec | 2s | ~10s |
| **Total** | | | **15 calls** | | | **~63s** |

### Stage 2 (Per 100 Profitable Products)

| Step | API | Batch Size | Calls | Rate Limit | Delay | Total Time |
|------|-----|------------|-------|------------|-------|------------|
| 2.1 | Keepa | 100 | 1 | Token-based | 1s | ~1s |
| 2.2 | Catalog | 1 | 100 | 2/sec | 0.5s | ~50s |
| 2.3 | Eligibility | 20 | 5 | Varies | 2s | ~10s |
| **Total** | | | **~106 calls** | | | **~61s** |

**Total for 100 products (if all pass Stage 1):** ~124 seconds (~2 minutes)

---

## Data Points Collected

### Stage 1 (All Products)
- ✅ Identifier (UPC or ASIN - original input)
- ✅ ASIN (normalized - all products have ASIN after Step 1.1 or if input was ASINs)
- ✅ Buy Cost
- ✅ Sell Price
- ✅ Total Fees (FBA + Referral)
- ✅ Net Profit
- ✅ ROI %
- ✅ Seller Count
- ✅ Amazon is Seller
- ✅ Amazon Qty
- ✅ Stage 1 Score

### Stage 2 (Profitable Products Only)
- ✅ BSR
- ✅ Lowest Price (365 days)
- ✅ Current Price
- ✅ Sales Rank Drops (30/90/180 days)
- ✅ Sold Last Month (estimated)
- ✅ % of BSR
- ✅ Category
- ✅ Hazmat
- ✅ Manufacturer is Seller
- ✅ Final Score

---

## 9 Core Profitability Fields

These are the fields that determine profitability:

1. **BSR** (Best Seller Rank) - Lower is better
2. **ROI** (%) - Return on Investment
3. **Sold in Last Month** - Estimated units sold
4. **% of BSR** - How close to #1 (BSR / Category Size × 100)
5. **Seller Count** - Number of sellers (fewer = better)
6. **Hazmat** - Hazardous material status (False = better)
7. **Amazon is Seller** - Amazon competing (False = better)
8. **Amazon Qty** - Amazon's inventory (0 = better)
9. **Manufacturer is Seller** - Brand competing (False = better)

---

## Implementation Example

```python
async def analyze_products_pipeline(identifiers: List[str], buy_costs: List[float]):
    """
    Complete two-stage pipeline for product profitability analysis.
    
    Args:
        identifiers: List of UPCs or ASINs
        buy_costs: List of buy costs corresponding to identifiers
    """
    
    # ============================================
    # STAGE 1: QUICK PROFITABILITY FILTER
    # ============================================
    
    # Step 1.1: Normalize input (UPC → ASIN if needed)
    identifier_to_asin = normalize_input(identifiers)
    
    # Step 1.2: Batch Pricing (using ASINs)
    asins = list(identifier_to_asin.values())
    pricing_data = batch_get_pricing(asins)
    
    # Step 1.3: Batch Fees
    asin_price_pairs = [
        (asin, pricing_data[asin]['sell_price'])
        for asin in asins
        if asin in pricing_data and pricing_data[asin].get('sell_price')
    ]
    fees_data = batch_get_fees(asin_price_pairs)
    
    # Step 1.4: Calculate Stage 1 scores
    stage1_results = []
    profitable_asins = []
    
    for identifier, buy_cost in zip(identifiers, buy_costs):
        asin = identifier_to_asin.get(identifier)
        if not asin:
            continue
        
        pricing = pricing_data.get(asin, {})
        fees = fees_data.get(asin, {})
        
        sell_price = pricing.get('sell_price')
        total_fees = fees.get('total_fees') or (sell_price * 0.15 + 4.0)  # Estimate if needed
        
        if sell_price and total_fees:
            net_profit = sell_price - buy_cost - total_fees
            roi = (net_profit / buy_cost * 100) if buy_cost > 0 else 0
            
            stage1_score = calculate_stage1_score(
                roi=roi,
                seller_count=pricing.get('seller_count', 0),
                amazon_is_seller=pricing.get('amazon_is_seller', False),
                amazon_qty=pricing.get('amazon_qty', 0),
                net_profit=net_profit
            )
            
            result = {
                'identifier': identifier,  # Original UPC or ASIN
                'asin': asin,
                'buy_cost': buy_cost,
                'sell_price': sell_price,
                'total_fees': total_fees,
                'net_profit': net_profit,
                'roi': roi,
                'stage1_score': stage1_score,
                'passed_stage1': stage1_score >= 50
            }
            
            stage1_results.append(result)
            
            if result['passed_stage1']:
                profitable_asins.append(asin)
    
    # ============================================
    # STAGE 2: DEEP ANALYSIS (Profitable Only)
    # ============================================
    
    stage2_results = {}
    
    if profitable_asins:
        # Step 2.1: Keepa Data
        keepa_data = batch_get_keepa_data(profitable_asins)
        
        # Step 2.2: Catalog Details (manufacturer)
        for asin in profitable_asins:
            catalog_item = sp_api.get_catalog_item(asin)
            manufacturer = catalog_item.get('attributes', {}).get('manufacturer', [{}])[0].get('value')
            
            # Check if manufacturer is seller
            pricing = pricing_data.get(asin, {})
            sellers = extract_seller_list(pricing)
            manufacturer_is_seller = manufacturer.lower() in [s.lower() for s in sellers] if manufacturer else False
            
            # Step 2.3: Hazmat check
            eligibility = sp_api.get_product_eligibility([asin])
            hazmat = eligibility.get(asin, {}).get('isHazmat', False)
            
            # Combine all data
            keepa = keepa_data.get(asin, {})
            
            stage2_data = {
                'bsr': keepa.get('salesRank'),
                'lowest_price_365d': parse_lowest_price_365d(keepa.get('csv')),
                'current_price': keepa.get('currentPrice'),
                'sales_rank_drops_30d': keepa.get('salesRankDrops30', 0),
                'sales_rank_drops_90d': keepa.get('salesRankDrops90', 0),
                'sales_rank_drops_180d': keepa.get('salesRankDrops180', 0),
                'category': keepa.get('categoryName'),
                'sold_last_month': estimate_monthly_sales(
                    keepa.get('salesRank'),
                    keepa.get('categoryName')
                ),
                'bsr_percentage': calculate_bsr_percentage(
                    keepa.get('salesRank'),
                    keepa.get('categoryName')
                ),
                'hazmat': hazmat,
                'manufacturer_is_seller': manufacturer_is_seller,
            }
            
            stage2_results[asin] = stage2_data
    
    # ============================================
    # COMBINE RESULTS & CALCULATE FINAL SCORES
    # ============================================
    
    final_results = []
    
    for stage1_result in stage1_results:
        result = stage1_result.copy()
        
        if result['passed_stage1'] and result['asin'] in stage2_results:
            result.update(stage2_results[result['asin']])
            
            # Calculate final score
            final_score = calculate_final_score({
                'roi': result['roi'],
                'bsr': result.get('bsr'),
                'bsr_percentage': result.get('bsr_percentage'),
                'sold_last_month': result.get('sold_last_month'),
                'seller_count': result.get('seller_count', 0),
                'hazmat': result.get('hazmat', False),
                'amazon_is_seller': result.get('amazon_is_seller', False),
                'amazon_qty': result.get('amazon_qty', 0),
                'manufacturer_is_seller': result.get('manufacturer_is_seller', False),
            })
            
            result['final_score'] = final_score
            
            # Classify
            if final_score >= 70:
                result['classification'] = 'Highly Profitable'
            elif final_score >= 50:
                result['classification'] = 'Profitable'
            elif final_score >= 30:
                result['classification'] = 'Marginally Profitable'
            else:
                result['classification'] = 'Not Profitable'
        
        final_results.append(result)
    
    return final_results
```

---

## Key Points

1. **UPC → ASIN first** - All subsequent calls use ASINs
2. **Batch everything** - 20 items per request for SP-API, 100 for Keepa
3. **Stage 1 filters** - Only profitable products go to Stage 2
4. **All 9 fields** - Complete profitability data in Stage 2
5. **Scoring system** - Clear thresholds for decision making

---

## Related Documents

- `API_ENDPOINTS_REFERENCE.md` - Detailed API endpoint reference
- `PROFITABILITY_THRESHOLDS.md` - Quick reference for scoring
- `api_clients.py` - Implementation of all batch methods

