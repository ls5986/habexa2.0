# Amazon SP-API & LWA Integration Guide
## Complete Technical Workflow for Habexa

---

# TABLE OF CONTENTS

1. [Authentication Flow (LWA)](#1-authentication-flow-lwa)
2. [SP-API Endpoints You Need](#2-sp-api-endpoints-you-need)
3. [Data Flow Architecture](#3-data-flow-architecture)
4. [API Call Sequences](#4-api-call-sequences)
5. [Rate Limiting & Best Practices](#5-rate-limiting--best-practices)
6. [Error Handling](#6-error-handling)
7. [Database Schema Recommendations](#7-database-schema-recommendations)

---

# 1. AUTHENTICATION FLOW (LWA)

## 1.1 Overview

Login with Amazon (LWA) is OAuth 2.0 based. For SP-API, you need TWO types of tokens:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LWA TOKEN TYPES                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. LWA ACCESS TOKEN (for API calls)                               │
│     • Short-lived (1 hour)                                          │
│     • Used in Authorization header                                  │
│     • Refreshed automatically with refresh_token                    │
│                                                                     │
│  2. RESTRICTED DATA TOKEN (RDT) - Optional                         │
│     • For PII data (buyer info, shipping addresses)                 │
│     • You probably don't need this for profitability analysis       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 1.2 Initial Authorization Flow (One-Time Setup)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    USER      │     │   HABEXA     │     │   AMAZON     │
│  (Seller)    │     │   BACKEND    │     │    LWA       │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ 1. Click "Connect  │                    │
       │    Amazon Account" │                    │
       │ ──────────────────>│                    │
       │                    │                    │
       │                    │ 2. Redirect to     │
       │                    │    Amazon OAuth    │
       │ <─────────────────────────────────────> │
       │                    │                    │
       │ 3. User logs in &  │                    │
       │    grants permission                    │
       │ ──────────────────────────────────────> │
       │                    │                    │
       │                    │ 4. Amazon redirects│
       │                    │    with auth_code  │
       │ <─────────────────────────────────────  │
       │                    │                    │
       │                    │ 5. Exchange code   │
       │                    │    for tokens      │
       │                    │ ──────────────────>│
       │                    │                    │
       │                    │ 6. Receive:        │
       │                    │    - access_token  │
       │                    │    - refresh_token │
       │                    │ <──────────────────│
       │                    │                    │
       │ 7. Store tokens    │                    │
       │    securely        │                    │
       │ <──────────────────│                    │
       │                    │                    │
```

## 1.3 Token Refresh Flow (Ongoing)

```python
# FastAPI endpoint for token refresh
# File: app/services/amazon_auth.py

import httpx
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.amazon_credentials import AmazonCredentials

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

async def refresh_access_token(user_id: int, db: Session) -> str:
    """
    Refresh the LWA access token using the stored refresh token.
    Called automatically when access_token expires.
    """
    
    # Get stored credentials
    creds = db.query(AmazonCredentials).filter(
        AmazonCredentials.user_id == user_id
    ).first()
    
    if not creds:
        raise ValueError("No Amazon credentials found for user")
    
    # Check if token is still valid (with 5 min buffer)
    if creds.token_expires_at > datetime.utcnow() + timedelta(minutes=5):
        return creds.access_token
    
    # Refresh the token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": creds.refresh_token,
                "client_id": settings.LWA_CLIENT_ID,
                "client_secret": settings.LWA_CLIENT_SECRET,
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.text}")
        
        token_data = response.json()
        
        # Update stored credentials
        creds.access_token = token_data["access_token"]
        creds.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data["expires_in"]
        )
        db.commit()
        
        return creds.access_token
```

## 1.4 Environment Variables Required

```bash
# .env file
LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxxxxxxx
LWA_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SP_API_REFRESH_TOKEN=Atzr|xxxxxxxxxxxxxxxxxxxxxxxxxx  # From initial auth
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SP_API_ROLE_ARN=arn:aws:iam::123456789012:role/SellingPartnerAPIRole
MARKETPLACE_ID=ATVPDKIKX0DER  # US marketplace
SELLER_ID=A1BCDEFGHIJK2L  # Your seller ID
```

---

# 2. SP-API ENDPOINTS YOU NEED

## 2.1 Core Endpoints for Profitability Analysis

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REQUIRED SP-API ENDPOINTS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📦 CATALOG ITEMS API                                               │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Get product details (title, category, images, etc.)       │
│  Endpoint: GET /catalog/2022-04-01/items/{asin}                     │
│  Rate Limit: 2 requests/second                                      │
│                                                                     │
│  💰 PRODUCT PRICING API                                             │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Get current Buy Box price, competitive pricing            │
│  Endpoint: GET /products/pricing/v0/price                           │
│  Rate Limit: 10 items per request, 0.5 requests/second              │
│                                                                     │
│  📊 PRODUCT FEES API                                                │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Calculate FBA fees, referral fees                         │
│  Endpoint: POST /products/fees/v0/feesEstimate                      │
│  Rate Limit: 1 request/second                                       │
│                                                                     │
│  📈 SALES API (Reports)                                             │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Historical sales data, BSR trends                         │
│  Endpoint: POST /reports/2021-06-30/reports                         │
│  Rate Limit: 0.0167 requests/second (1 per minute)                  │
│                                                                     │
│  🔒 LISTINGS API                                                    │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Check if you can sell (gating/eligibility)                │
│  Endpoint: GET /listings/2021-08-01/items/{sellerId}/{sku}          │
│  Rate Limit: 5 requests/second                                      │
│                                                                     │
│  📦 FBA INVENTORY API                                               │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Check your current FBA inventory                          │
│  Endpoint: GET /fba/inventory/v1/summaries                          │
│  Rate Limit: 2 requests/second                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2.2 Supplementary APIs (External - Not SP-API)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL APIs TO INTEGRATE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📊 KEEPA API (Recommended)                                         │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Historical price/rank data, sales estimates               │
│  Why: SP-API doesn't give good historical data                      │
│  Pricing: ~$0.01 per ASIN lookup                                    │
│  Docs: https://keepa.com/#!discuss/t/using-the-keepa-api            │
│                                                                     │
│  📈 JUNGLE SCOUT API (Alternative)                                  │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Sales estimates, competition analysis                     │
│  Pricing: Enterprise pricing                                        │
│                                                                     │
│  🔍 ASIN DATA API / RAINFOREST API (Alternative)                   │
│  ──────────────────────────────────────────────────────────────     │
│  Purpose: Product data if SP-API is rate limited                    │
│  Pricing: Pay per request                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 3. DATA FLOW ARCHITECTURE

## 3.1 Complete ASIN Analysis Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ASIN ANALYSIS PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐                                                            │
│  │  TELEGRAM   │──┐                                                         │
│  │  MESSAGE    │  │     ┌──────────────┐     ┌──────────────────────┐      │
│  └─────────────┘  │     │              │     │                      │      │
│                   ├────▶│  OPENAI API  │────▶│  EXTRACTED DATA      │      │
│  ┌─────────────┐  │     │  (GPT-4)     │     │  • ASIN: B08XYZ1234  │      │
│  │   EMAIL     │  │     │              │     │  • Price: $45        │      │
│  │  (IMAP)     │──┘     │  Extract:    │     │  • MOQ: 24           │      │
│  └─────────────┘        │  ASIN, Price │     │  • Supplier: WK      │      │
│                         │  MOQ, etc.   │     │                      │      │
│                         └──────────────┘     └──────────┬───────────┘      │
│                                                         │                   │
│                                                         ▼                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        PARALLEL API CALLS                            │  │
│  │                                                                      │  │
│  │   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐ │  │
│  │   │ CATALOG    │   │ PRICING    │   │ FEES       │   │ KEEPA      │ │  │
│  │   │ ITEMS API  │   │ API        │   │ API        │   │ API        │ │  │
│  │   │            │   │            │   │            │   │            │ │  │
│  │   │ • Title    │   │ • Buy Box  │   │ • FBA Fee  │   │ • History  │ │  │
│  │   │ • Category │   │ • Lowest   │   │ • Referral │   │ • Sales    │ │  │
│  │   │ • Images   │   │ • Offers   │   │ • Prep Est │   │ • Rank     │ │  │
│  │   │ • Brand    │   │            │   │            │   │ • Trend    │ │  │
│  │   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘ │  │
│  │         │                │                │                │        │  │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────┘  │
│            │                │                │                │           │
│            └────────────────┴────────────────┴────────────────┘           │
│                                      │                                     │
│                                      ▼                                     │
│                         ┌──────────────────────┐                          │
│                         │   PROFIT CALCULATOR  │                          │
│                         │                      │                          │
│                         │ sell_price           │                          │
│                         │ - buy_cost           │                          │
│                         │ - fba_fee            │                          │
│                         │ - referral_fee       │                          │
│                         │ - prep_cost          │                          │
│                         │ - inbound_shipping   │                          │
│                         │ ─────────────────    │                          │
│                         │ = NET PROFIT         │                          │
│                         │ = ROI %              │                          │
│                         └──────────┬───────────┘                          │
│                                    │                                       │
│                                    ▼                                       │
│                         ┌──────────────────────┐                          │
│                         │   DECISION ENGINE    │                          │
│                         │                      │                          │
│                         │ IF roi > threshold   │                          │
│                         │ AND rank < max_rank  │                          │
│                         │ AND not gated        │                          │
│                         │ AND no IP issues     │                          │
│                         │ ─────────────────    │                          │
│                         │ → ALERT USER! 🔔     │                          │
│                         └──────────────────────┘                          │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Gating Check Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GATING/ELIGIBILITY CHECK                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  METHOD 1: Product Type Definitions API (Recommended)               │
│  ──────────────────────────────────────────────────────────────     │
│                                                                     │
│  1. Get product type from Catalog Items API                         │
│  2. Check Product Type Definitions for requirements                 │
│  3. Compare against seller's approved categories                    │
│                                                                     │
│  METHOD 2: Listings API (Try to create listing)                     │
│  ──────────────────────────────────────────────────────────────     │
│                                                                     │
│  1. Attempt to get listing requirements for ASIN                    │
│  2. If error = "UNAUTHORIZED" → Gated                               │
│  3. If success → Ungated (can sell)                                 │
│                                                                     │
│  METHOD 3: Manual Category Mapping (Fallback)                       │
│  ──────────────────────────────────────────────────────────────     │
│                                                                     │
│  1. Maintain database of known gated categories                     │
│  2. Check product category against list                             │
│  3. Less accurate but fast                                          │
│                                                                     │
│  KNOWN GATED CATEGORIES (US Marketplace):                           │
│  • Automotive & Powersports                                         │
│  • Collectibles & Fine Art                                          │
│  • Fashion (Watches, Jewelry, Clothing brands)                      │
│  • Grocery & Gourmet Food                                           │
│  • Health & Personal Care (some)                                    │
│  • Industrial & Scientific (some)                                   │
│  • Professional Services                                            │
│  • Sports Collectibles                                              │
│  • Toys & Games (Q4 restrictions)                                   │
│  • Certain brands (Nike, Apple, Disney, etc.)                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 4. API CALL SEQUENCES

## 4.1 Single ASIN Analysis (Python/FastAPI)

```python
# File: app/services/asin_analyzer.py

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

from app.services.amazon_auth import get_sp_api_client
from app.services.keepa_client import KeepaClient
from app.services.profit_calculator import calculate_profit
from app.models.analysis import AnalysisResult


class ASINAnalyzer:
    """
    Main service for analyzing a single ASIN's profitability.
    """
    
    def __init__(self, user_id: int, db_session):
        self.user_id = user_id
        self.db = db_session
        self.sp_client = None
        self.keepa_client = KeepaClient()
    
    async def analyze(
        self, 
        asin: str, 
        buy_cost: float, 
        moq: int = 1,
        supplier_id: Optional[int] = None
    ) -> AnalysisResult:
        """
        Perform complete profitability analysis on an ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            buy_cost: Your purchase cost per unit
            moq: Minimum order quantity
            supplier_id: Optional linked supplier
            
        Returns:
            AnalysisResult with all profitability metrics
        """
        
        # Initialize SP-API client with refreshed token
        self.sp_client = await get_sp_api_client(self.user_id, self.db)
        
        # Run all API calls in parallel for speed
        results = await asyncio.gather(
            self._get_catalog_item(asin),
            self._get_pricing(asin),
            self._get_fees_estimate(asin, buy_cost),
            self._get_keepa_data(asin),
            self._check_eligibility(asin),
            return_exceptions=True
        )
        
        catalog_data, pricing_data, fees_data, keepa_data, eligibility = results
        
        # Handle any failed API calls
        catalog_data = catalog_data if not isinstance(catalog_data, Exception) else {}
        pricing_data = pricing_data if not isinstance(pricing_data, Exception) else {}
        fees_data = fees_data if not isinstance(fees_data, Exception) else {}
        keepa_data = keepa_data if not isinstance(keepa_data, Exception) else {}
        eligibility = eligibility if not isinstance(eligibility, Exception) else "unknown"
        
        # Calculate profitability
        profit_data = calculate_profit(
            buy_cost=buy_cost,
            sell_price=pricing_data.get("buy_box_price", 0),
            fba_fee=fees_data.get("fba_fee", 0),
            referral_fee=fees_data.get("referral_fee", 0),
            user_id=self.user_id,  # For user-specific prep costs
            db=self.db
        )
        
        # Build result object
        result = AnalysisResult(
            asin=asin,
            title=catalog_data.get("title", "Unknown Product"),
            category=catalog_data.get("category", "Unknown"),
            brand=catalog_data.get("brand"),
            image_url=catalog_data.get("main_image"),
            
            # Pricing
            buy_cost=buy_cost,
            sell_price=pricing_data.get("buy_box_price", 0),
            lowest_fba_price=pricing_data.get("lowest_fba", 0),
            lowest_fbm_price=pricing_data.get("lowest_fbm", 0),
            
            # Fees
            fba_fee=fees_data.get("fba_fee", 0),
            referral_fee=fees_data.get("referral_fee", 0),
            variable_closing_fee=fees_data.get("variable_closing_fee", 0),
            
            # Profitability
            net_profit=profit_data["net_profit"],
            roi=profit_data["roi"],
            profit_margin=profit_data["margin"],
            
            # Competition
            num_fba_sellers=pricing_data.get("fba_seller_count", 0),
            num_fbm_sellers=pricing_data.get("fbm_seller_count", 0),
            amazon_is_seller=pricing_data.get("amazon_is_seller", False),
            buy_box_winner=pricing_data.get("buy_box_winner", "Unknown"),
            
            # Rank & Sales
            sales_rank=keepa_data.get("current_rank", 0),
            sales_rank_category=catalog_data.get("category", ""),
            estimated_monthly_sales=keepa_data.get("monthly_sales_estimate", 0),
            
            # Historical (from Keepa)
            avg_price_90d=keepa_data.get("avg_price_90d", 0),
            avg_rank_90d=keepa_data.get("avg_rank_90d", 0),
            price_trend=keepa_data.get("price_trend", "stable"),
            
            # Eligibility
            gating_status=eligibility,
            
            # Meta
            moq=moq,
            supplier_id=supplier_id,
            analyzed_at=datetime.utcnow(),
            
            # Computed fields
            is_profitable=profit_data["roi"] > 0,
            meets_threshold=self._check_user_thresholds(profit_data, keepa_data),
            deal_score=self._calculate_deal_score(profit_data, keepa_data, eligibility)
        )
        
        # Save to database
        self._save_analysis(result)
        
        return result
    
    async def _get_catalog_item(self, asin: str) -> Dict[str, Any]:
        """
        Fetch product details from Catalog Items API.
        
        Endpoint: GET /catalog/2022-04-01/items/{asin}
        """
        
        url = f"https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items/{asin}"
        
        params = {
            "marketplaceIds": "ATVPDKIKX0DER",  # US
            "includedData": "attributes,identifiers,images,productTypes,salesRanks,summaries"
        }
        
        response = await self.sp_client.get(url, params=params)
        data = response.json()
        
        # Parse response
        summaries = data.get("summaries", [{}])[0]
        images = data.get("images", [{}])[0].get("images", [])
        sales_ranks = data.get("salesRanks", [{}])[0].get("ranks", [])
        
        return {
            "title": summaries.get("itemName", "Unknown"),
            "brand": summaries.get("brand", "Unknown"),
            "category": sales_ranks[0].get("title", "Unknown") if sales_ranks else "Unknown",
            "main_image": images[0].get("link") if images else None,
            "product_type": data.get("productTypes", [{}])[0].get("productType"),
        }
    
    async def _get_pricing(self, asin: str) -> Dict[str, Any]:
        """
        Fetch competitive pricing data.
        
        Endpoint: GET /products/pricing/v0/price
        """
        
        url = "https://sellingpartnerapi-na.amazon.com/products/pricing/v0/price"
        
        params = {
            "MarketplaceId": "ATVPDKIKX0DER",
            "Asins": asin,
            "ItemType": "Asin"
        }
        
        response = await self.sp_client.get(url, params=params)
        data = response.json()
        
        # Parse pricing data
        payload = data.get("payload", [{}])[0]
        product = payload.get("Product", {})
        offers = product.get("Offers", [])
        competitive = product.get("CompetitivePricing", {})
        
        # Find Buy Box price
        buy_box_price = 0
        for offer in offers:
            if offer.get("IsBuyBoxWinner"):
                buy_box_price = float(offer.get("ListingPrice", {}).get("Amount", 0))
                break
        
        # Count sellers
        fba_count = len([o for o in offers if o.get("IsFulfilledByAmazon")])
        fbm_count = len([o for o in offers if not o.get("IsFulfilledByAmazon")])
        
        # Check if Amazon is selling
        amazon_selling = any(
            o.get("SellerId") == "ATVPDKIKX0DER" for o in offers
        )
        
        return {
            "buy_box_price": buy_box_price,
            "lowest_fba": self._find_lowest_price(offers, fba_only=True),
            "lowest_fbm": self._find_lowest_price(offers, fba_only=False),
            "fba_seller_count": fba_count,
            "fbm_seller_count": fbm_count,
            "amazon_is_seller": amazon_selling,
            "buy_box_winner": self._get_buy_box_winner(offers)
        }
    
    async def _get_fees_estimate(self, asin: str, price: float) -> Dict[str, Any]:
        """
        Calculate Amazon fees for the product.
        
        Endpoint: POST /products/fees/v0/feesEstimate
        """
        
        url = "https://sellingpartnerapi-na.amazon.com/products/fees/v0/feesEstimate"
        
        body = {
            "FeesEstimateRequest": {
                "MarketplaceId": "ATVPDKIKX0DER",
                "IdType": "ASIN",
                "IdValue": asin,
                "IsAmazonFulfilled": True,  # FBA
                "PriceToEstimateFees": {
                    "ListingPrice": {
                        "CurrencyCode": "USD",
                        "Amount": price
                    }
                }
            }
        }
        
        response = await self.sp_client.post(url, json=body)
        data = response.json()
        
        # Parse fees
        fees = data.get("payload", {}).get("FeesEstimateResult", {}).get("FeesEstimate", {})
        fee_details = fees.get("FeeDetailList", [])
        
        fba_fee = 0
        referral_fee = 0
        closing_fee = 0
        
        for fee in fee_details:
            fee_type = fee.get("FeeType")
            amount = float(fee.get("FinalFee", {}).get("Amount", 0))
            
            if fee_type == "FBAFees":
                fba_fee = amount
            elif fee_type == "ReferralFee":
                referral_fee = amount
            elif fee_type == "VariableClosingFee":
                closing_fee = amount
        
        return {
            "fba_fee": fba_fee,
            "referral_fee": referral_fee,
            "variable_closing_fee": closing_fee,
            "total_fees": fba_fee + referral_fee + closing_fee
        }
    
    async def _get_keepa_data(self, asin: str) -> Dict[str, Any]:
        """
        Fetch historical data from Keepa API.
        
        Note: This is an external API, not SP-API
        """
        
        return await self.keepa_client.get_product_data(asin)
    
    async def _check_eligibility(self, asin: str) -> str:
        """
        Check if seller is approved to sell this product.
        
        Returns: "ungated", "gated", "amazon_restricted", or "unknown"
        """
        
        try:
            # Try to get listing requirements
            url = f"https://sellingpartnerapi-na.amazon.com/listings/2021-08-01/items/{self.seller_id}"
            
            params = {
                "marketplaceIds": "ATVPDKIKX0DER",
                "issueLocale": "en_US"
            }
            
            response = await self.sp_client.get(url, params=params)
            
            if response.status_code == 200:
                return "ungated"
            elif response.status_code == 403:
                return "gated"
            else:
                return "unknown"
                
        except Exception:
            return "unknown"
    
    def _calculate_deal_score(
        self, 
        profit_data: Dict, 
        keepa_data: Dict, 
        eligibility: str
    ) -> str:
        """
        Calculate overall deal score (A, B, C, D, F).
        
        Factors:
        - ROI
        - Sales rank
        - Competition level
        - Gating status
        - Price stability
        """
        
        score = 0
        
        # ROI scoring (0-30 points)
        roi = profit_data.get("roi", 0)
        if roi >= 50:
            score += 30
        elif roi >= 30:
            score += 25
        elif roi >= 20:
            score += 20
        elif roi >= 10:
            score += 10
        
        # Rank scoring (0-25 points)
        rank = keepa_data.get("current_rank", 999999)
        if rank < 5000:
            score += 25
        elif rank < 20000:
            score += 20
        elif rank < 50000:
            score += 15
        elif rank < 100000:
            score += 10
        
        # Eligibility scoring (0-20 points)
        if eligibility == "ungated":
            score += 20
        elif eligibility == "unknown":
            score += 10
        
        # Competition scoring (0-15 points)
        # Lower competition = higher score
        # ... implement based on seller count
        score += 10  # Placeholder
        
        # Price stability (0-10 points)
        # ... implement based on Keepa trends
        score += 5  # Placeholder
        
        # Convert to letter grade
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
```

## 4.2 Batch Analysis Endpoint

```python
# File: app/api/v1/analysis.py

from fastapi import APIRouter, Depends, BackgroundTasks
from typing import List
from pydantic import BaseModel

from app.services.asin_analyzer import ASINAnalyzer
from app.api.deps import get_current_user, get_db


router = APIRouter()


class ASINInput(BaseModel):
    asin: str
    buy_cost: float
    moq: int = 1
    supplier_id: Optional[int] = None


class BatchAnalysisRequest(BaseModel):
    items: List[ASINInput]


@router.post("/analyze/single")
async def analyze_single_asin(
    asin: str,
    buy_cost: float,
    moq: int = 1,
    supplier_id: Optional[int] = None,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Analyze a single ASIN for profitability.
    """
    analyzer = ASINAnalyzer(current_user.id, db)
    result = await analyzer.analyze(asin, buy_cost, moq, supplier_id)
    
    return {
        "success": True,
        "data": result.dict()
    }


@router.post("/analyze/batch")
async def analyze_batch_asins(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Analyze multiple ASINs. 
    Processes in background for large batches.
    """
    
    if len(request.items) <= 5:
        # Small batch - process immediately
        analyzer = ASINAnalyzer(current_user.id, db)
        results = []
        
        for item in request.items:
            result = await analyzer.analyze(
                item.asin, 
                item.buy_cost, 
                item.moq, 
                item.supplier_id
            )
            results.append(result.dict())
        
        return {
            "success": True,
            "data": results
        }
    else:
        # Large batch - process in background
        batch_id = generate_batch_id()
        
        background_tasks.add_task(
            process_batch_analysis,
            batch_id,
            request.items,
            current_user.id
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "message": f"Processing {len(request.items)} ASINs in background",
            "status_url": f"/api/v1/analysis/batch/{batch_id}/status"
        }
```

---

# 5. RATE LIMITING & BEST PRACTICES

## 5.1 SP-API Rate Limits

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SP-API RATE LIMITS                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  API                          │ Rate Limit    │ Burst               │
│  ─────────────────────────────┼───────────────┼─────────────────    │
│  Catalog Items                │ 2/sec         │ 2                   │
│  Product Pricing              │ 0.5/sec       │ 1                   │
│  Product Fees                 │ 1/sec         │ 1                   │
│  Listings                     │ 5/sec         │ 10                  │
│  Reports                      │ 0.0167/sec    │ 15                  │
│  Notifications                │ 1/sec         │ 5                   │
│                                                                     │
│  HANDLING RATE LIMITS:                                              │
│  ──────────────────────────────────────────────────────────────     │
│                                                                     │
│  • Implement exponential backoff                                    │
│  • Queue requests with delays                                       │
│  • Cache responses (especially catalog data)                        │
│  • Use batch endpoints where available                              │
│  • Monitor x-amzn-RateLimit-Limit headers                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 5.2 Rate Limiter Implementation

```python
# File: app/core/rate_limiter.py

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import time


class SPAPIRateLimiter:
    """
    Token bucket rate limiter for SP-API calls.
    """
    
    # Rate limits by endpoint type
    LIMITS = {
        "catalog": {"rate": 2, "burst": 2},
        "pricing": {"rate": 0.5, "burst": 1},
        "fees": {"rate": 1, "burst": 1},
        "listings": {"rate": 5, "burst": 10},
        "reports": {"rate": 0.0167, "burst": 15},
    }
    
    def __init__(self):
        self.tokens = defaultdict(lambda: {"tokens": 0, "last_update": time.time()})
        self._lock = asyncio.Lock()
    
    async def acquire(self, endpoint_type: str):
        """
        Acquire a token for making an API call.
        Blocks if rate limit would be exceeded.
        """
        
        async with self._lock:
            limit = self.LIMITS.get(endpoint_type, {"rate": 1, "burst": 1})
            bucket = self.tokens[endpoint_type]
            
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - bucket["last_update"]
            bucket["tokens"] = min(
                limit["burst"],
                bucket["tokens"] + elapsed * limit["rate"]
            )
            bucket["last_update"] = now
            
            # Wait if no tokens available
            if bucket["tokens"] < 1:
                wait_time = (1 - bucket["tokens"]) / limit["rate"]
                await asyncio.sleep(wait_time)
                bucket["tokens"] = 0
            else:
                bucket["tokens"] -= 1


# Global instance
rate_limiter = SPAPIRateLimiter()


# Usage in API client
class SPAPIClient:
    async def get_catalog_item(self, asin: str):
        await rate_limiter.acquire("catalog")
        # ... make API call
```

## 5.3 Caching Strategy

```python
# File: app/core/cache.py

from functools import wraps
import hashlib
import json
from typing import Optional
from datetime import timedelta

import redis.asyncio as redis


class SPAPICache:
    """
    Redis-based cache for SP-API responses.
    """
    
    # Cache TTLs by data type
    TTL = {
        "catalog": timedelta(hours=24),      # Product info rarely changes
        "pricing": timedelta(minutes=15),    # Prices change frequently
        "fees": timedelta(hours=6),          # Fees change occasionally
        "keepa": timedelta(hours=1),         # Historical data
        "eligibility": timedelta(hours=12),  # Gating status
    }
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments."""
        data = json.dumps(args, sort_keys=True)
        hash_val = hashlib.md5(data.encode()).hexdigest()[:12]
        return f"spapi:{prefix}:{hash_val}"
    
    async def get(self, prefix: str, *args) -> Optional[dict]:
        """Get cached data."""
        key = self._make_key(prefix, *args)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(self, prefix: str, data: dict, *args):
        """Cache data with appropriate TTL."""
        key = self._make_key(prefix, *args)
        ttl = self.TTL.get(prefix, timedelta(hours=1))
        await self.redis.setex(
            key, 
            int(ttl.total_seconds()), 
            json.dumps(data)
        )
    
    async def invalidate(self, prefix: str, *args):
        """Invalidate cached data."""
        key = self._make_key(prefix, *args)
        await self.redis.delete(key)


# Decorator for cached API calls
def cached(prefix: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Check cache first
            cached_data = await self.cache.get(prefix, *args)
            if cached_data:
                return cached_data
            
            # Call API
            result = await func(self, *args, **kwargs)
            
            # Cache result
            await self.cache.set(prefix, result, *args)
            
            return result
        return wrapper
    return decorator
```

---

# 6. ERROR HANDLING

## 6.1 Common SP-API Errors

```python
# File: app/core/exceptions.py

class SPAPIError(Exception):
    """Base exception for SP-API errors."""
    pass


class RateLimitError(SPAPIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


class QuotaExceededError(SPAPIError):
    """Raised when daily quota is exceeded."""
    pass


class InvalidASINError(SPAPIError):
    """Raised when ASIN is invalid or not found."""
    pass


class AuthenticationError(SPAPIError):
    """Raised when LWA token is invalid or expired."""
    pass


class GatedProductError(SPAPIError):
    """Raised when seller is not approved for product."""
    pass


# Error handler middleware
async def sp_api_error_handler(request, call_next):
    try:
        response = await call_next(request)
        return response
    except RateLimitError as e:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": str(e),
                "retry_after": e.retry_after
            },
            headers={"Retry-After": str(e.retry_after)}
        )
    except AuthenticationError:
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_failed",
                "message": "Please reconnect your Amazon account"
            }
        )
    except SPAPIError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "sp_api_error",
                "message": str(e)
            }
        )
```

## 6.2 Retry Logic

```python
# File: app/core/retry.py

import asyncio
from functools import wraps
from typing import Tuple, Type
import random


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2,
    retryable_exceptions: Tuple[Type[Exception], ...] = (RateLimitError,)
):
    """
    Decorator for automatic retry with exponential backoff.
    """
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        raise
                    
                    # Calculate delay with jitter
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    delay *= (0.5 + random.random())  # Add jitter
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# Usage
class SPAPIClient:
    @with_retry(max_attempts=3, base_delay=2.0)
    async def get_pricing(self, asin: str):
        # ... API call that might fail
        pass
```

---

# 7. DATABASE SCHEMA RECOMMENDATIONS

## 7.1 Core Tables

```sql
-- Users and Authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Amazon Credentials (encrypted)
CREATE TABLE amazon_credentials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    seller_id VARCHAR(50) NOT NULL,
    marketplace_id VARCHAR(20) NOT NULL,
    access_token TEXT,  -- Encrypted
    refresh_token TEXT NOT NULL,  -- Encrypted
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, marketplace_id)
);

-- Suppliers
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    telegram_username VARCHAR(100),
    telegram_channel_id VARCHAR(100),
    whatsapp_number VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(500),
    notes TEXT,
    rating DECIMAL(2,1) DEFAULT 0,
    avg_lead_time_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw Messages (from Telegram/Email)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    supplier_id INTEGER REFERENCES suppliers(id),
    source VARCHAR(20) NOT NULL,  -- 'telegram', 'email'
    source_id VARCHAR(255),  -- Message ID from source
    channel_name VARCHAR(255),
    raw_content TEXT NOT NULL,
    extracted_data JSONB,  -- Parsed ASINs, prices, MOQs
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_id)
);

-- Analyzed Products
CREATE TABLE product_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES messages(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    
    -- Product Info
    asin VARCHAR(20) NOT NULL,
    title VARCHAR(500),
    brand VARCHAR(255),
    category VARCHAR(255),
    image_url VARCHAR(1000),
    
    -- Pricing
    buy_cost DECIMAL(10,2) NOT NULL,
    sell_price DECIMAL(10,2),
    lowest_fba_price DECIMAL(10,2),
    lowest_fbm_price DECIMAL(10,2),
    
    -- Fees
    fba_fee DECIMAL(10,2),
    referral_fee DECIMAL(10,2),
    prep_cost DECIMAL(10,2),
    inbound_shipping DECIMAL(10,2),
    
    -- Profitability
    net_profit DECIMAL(10,2),
    roi DECIMAL(5,2),
    profit_margin DECIMAL(5,2),
    
    -- Competition
    num_fba_sellers INTEGER,
    num_fbm_sellers INTEGER,
    amazon_is_seller BOOLEAN DEFAULT FALSE,
    buy_box_winner VARCHAR(100),
    
    -- Sales Data
    sales_rank INTEGER,
    sales_rank_category VARCHAR(255),
    estimated_monthly_sales INTEGER,
    
    -- Historical
    avg_price_90d DECIMAL(10,2),
    avg_rank_90d INTEGER,
    price_trend VARCHAR(20),  -- 'up', 'down', 'stable'
    
    -- Eligibility
    gating_status VARCHAR(20),  -- 'ungated', 'gated', 'amazon_restricted'
    
    -- Deal Assessment
    moq INTEGER DEFAULT 1,
    deal_score CHAR(1),  -- A, B, C, D, F
    is_profitable BOOLEAN,
    meets_threshold BOOLEAN,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'analyzed', 'saved', 'ordered', 'dismissed'
    notes TEXT,
    
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_asin (asin),
    INDEX idx_user_status (user_id, status),
    INDEX idx_analyzed_at (analyzed_at)
);

-- User Watchlist
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    asin VARCHAR(20) NOT NULL,
    target_price DECIMAL(10,2),
    notes TEXT,
    notify_on_price_drop BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, asin)
);

-- Orders/Purchases
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    supplier_id INTEGER REFERENCES suppliers(id),
    analysis_id INTEGER REFERENCES product_analyses(id),
    
    asin VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    total_cost DECIMAL(10,2) NOT NULL,
    
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'confirmed', 'shipped', 'received', 'cancelled'
    expected_delivery DATE,
    actual_delivery DATE,
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Profit Settings
CREATE TABLE profit_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    
    min_roi DECIMAL(5,2) DEFAULT 20.00,
    min_profit DECIMAL(10,2) DEFAULT 3.00,
    max_rank INTEGER DEFAULT 100000,
    
    default_prep_cost DECIMAL(10,2) DEFAULT 0.50,
    default_inbound_shipping DECIMAL(10,2) DEFAULT 0.50,
    
    -- Alert preferences
    alert_on_profitable BOOLEAN DEFAULT TRUE,
    alert_min_roi DECIMAL(5,2) DEFAULT 30.00,
    alert_channels JSONB DEFAULT '["push", "email"]',
    
    -- Category preferences
    preferred_categories JSONB DEFAULT '[]',
    excluded_categories JSONB DEFAULT '[]',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts/Notifications
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    analysis_id INTEGER REFERENCES product_analyses(id),
    
    type VARCHAR(50) NOT NULL,  -- 'profitable_deal', 'price_drop', 'restock', etc.
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB,
    
    is_read BOOLEAN DEFAULT FALSE,
    sent_push BOOLEAN DEFAULT FALSE,
    sent_email BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);
```

---

# APPENDIX: Quick Reference

## API Endpoints Summary

| Action | SP-API Endpoint | Method | Rate |
|--------|----------------|--------|------|
| Get product info | `/catalog/2022-04-01/items/{asin}` | GET | 2/s |
| Get pricing | `/products/pricing/v0/price` | GET | 0.5/s |
| Calculate fees | `/products/fees/v0/feesEstimate` | POST | 1/s |
| Check eligibility | `/listings/2021-08-01/items/{sellerId}/{sku}` | GET | 5/s |
| Get inventory | `/fba/inventory/v1/summaries` | GET | 2/s |
| Create report | `/reports/2021-06-30/reports` | POST | 0.017/s |

## Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad request | Check parameters |
| 401 | Unauthorized | Refresh token |
| 403 | Forbidden | Check permissions/gating |
| 404 | Not found | Invalid ASIN |
| 429 | Rate limited | Wait & retry |
| 500 | Server error | Retry with backoff |

## Useful Links

- [SP-API Documentation](https://developer-docs.amazon.com/sp-api/)
- [SP-API Models](https://github.com/amzn/selling-partner-api-models)
- [LWA Developer Portal](https://developer.amazon.com/)
- [Keepa API Docs](https://keepa.com/#!discuss/t/using-the-keepa-api)
