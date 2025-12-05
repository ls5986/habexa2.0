# Master Workflow Summary - Structured Reference

## 1. Two Stages and Their Purpose

### Stage 1: Quick Profitability Filter
- **Purpose:** Quickly identify profitable products using batch APIs
- **Goal:** Filter out unprofitable products before expensive API calls
- **Output:** Stage 1 Score (0-100 points)

### Stage 2: Deep Analysis
- **Purpose:** Get detailed data for products that passed Stage 1
- **Input:** ASINs of profitable products (Stage 1 Score >= 50)
- **Output:** Complete profitability data with all 9 fields + Final Score

---

## 2. Batch Size for Each API

| API Endpoint | Batch Size |
|--------------|------------|
| UPC → ASIN (Catalog Items) | 20 UPCs per request |
| Batch Competitive Pricing | 20 ASINs per request |
| Batch Fee Estimates | 20 items per request |
| Keepa Product Data | 100 ASINs per request |
| SP-API Catalog Item Details | 1 per request (individual) |
| SP-API Product Eligibility | 20 ASINs per request |

---

## 3. Stage 1 APIs Called

| Step | API Endpoint | Batch Size | Rate Limit | Delay Between Batches |
|------|--------------|------------|------------|----------------------|
| **1.1** (if UPCs) | `GET /catalog/2022-04-01/items` | 20 UPCs | 2 requests/second, burst of 2 | 0.5 seconds |
| **1.2** | `POST /batches/products/pricing/v0/itemOffers` | 20 ASINs | 0.1 requests/second, burst of 1 | 10 seconds |
| **1.3** | `POST /products/fees/v0/feesEstimate` | 20 items | 0.5 requests/second, burst of 1 | 2 seconds |

**Note:** Step 1.1 is skipped if input is already ASINs.

---

## 4. Stage 2 APIs Called

| Step | API Endpoint | Batch Size | Rate Limit | Delay Between Batches |
|------|--------------|------------|------------|----------------------|
| **2.1** | Keepa API `GET /product` | 100 ASINs | Token-based | 1 second |
| **2.2** | `GET /catalog/2022-04-01/items/{asin}` | 1 per request | 2 requests/second | 0.5 seconds |
| **2.3** | `GET /fba/inbound/v0/eligibility` | 20 ASINs | Varies | 2 seconds |

---

## 5. The 9 Core Profitability Fields

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

## 6. Stage 1 Score Threshold to Proceed to Stage 2

**Threshold:** `Stage 1 Score >= 50` → Proceed to Stage 2

**Alternative Simple Threshold:**
```
IF (ROI >= 30% AND Net Profit >= $5) AND 
   (Seller Count <= 5) AND 
   (NOT Amazon is Seller):
    → Proceed to Stage 2
```

---

## 7. Final Score Classification

| Score Range | Classification |
|-------------|----------------|
| **Score >= 70** | "Highly Profitable" (Top Priority) |
| **Score >= 50** | "Profitable" (Good Opportunity) |
| **Score >= 30** | "Marginally Profitable" (Consider if inventory allows) |
| **Score < 30** | "Not Profitable" (Skip) |

---

## 8. Processing Time for 100 Products

### Stage 1 (All 100 Products)
- **Step 1.1** (if UPCs): 5 calls × 0.5s = ~2.5s
- **Step 1.2** (Pricing): 5 calls × 10s = ~50s
- **Step 1.3** (Fees): 5 calls × 2s = ~10s
- **Total Stage 1:** ~63 seconds

### Stage 2 (Assumes all 100 pass Stage 1)
- **Step 2.1** (Keepa): 1 call × 1s = ~1s
- **Step 2.2** (Catalog): 100 calls × 0.5s = ~50s
- **Step 2.3** (Eligibility): 5 calls × 2s = ~10s
- **Total Stage 2:** ~61 seconds

### Total for 100 Products
- **If all pass Stage 1:** ~124 seconds (**~2 minutes**)
- **If only 50% pass Stage 1:** ~63s (Stage 1) + ~30.5s (Stage 2) = **~94 seconds (~1.5 minutes)**

---

## Quick Reference: Stage 1 Scoring (100 points max)

| Component | Points | Criteria |
|-----------|--------|----------|
| **ROI** | 0-40 | 100%+ = 40, 50%+ = 30, 30%+ = 20, 15%+ = 10 |
| **Seller Count** | 0-20 | 1 seller = 20, ≤3 = 15, ≤5 = 10, ≤10 = 5 |
| **Amazon Competition** | 0-20 | No Amazon = 20, Amazon qty 0 = 10 |
| **Net Profit** | 0-20 | $20+ = 20, $10+ = 15, $5+ = 10, $2+ = 5 |

---

## Quick Reference: Final Scoring (100 points max)

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

