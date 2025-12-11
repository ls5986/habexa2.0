"""
Hybrid SP-API Client:
- App credentials for public data (pricing, fees, catalog)
- User credentials for seller-specific data (inventory, orders)
"""
import os
import logging
import httpx
import asyncio
import random
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.services.supabase_client import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Import token bucket rate limiter
try:
    from app.services.rate_limiter import get_limiter, sp_api_pricing_limiter, sp_api_fees_limiter
    USE_TOKEN_BUCKET = True
except ImportError:
    USE_TOKEN_BUCKET = False
    get_limiter = None
    sp_api_pricing_limiter = None
    sp_api_fees_limiter = None

# Import distributed rate limiter if available (legacy)
try:
    from app.tasks.rate_limiter import sp_api_limiter
    USE_DISTRIBUTED_LIMITER = True
except ImportError:
    USE_DISTRIBUTED_LIMITER = False
    sp_api_limiter = None

# Simple rate limiter for local use
_last_request = 0
_min_interval = 0.4  # ~2.5 requests/sec

def _rate_limit():
    """Simple rate limiter to avoid hitting limits."""
    global _last_request
    now = time.time()
    wait = _min_interval - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()


class SPAPIError(Exception):
    """Custom exception for SP-API errors."""
    pass


class SPAPIClient:
    """
    SP-API client with hybrid authentication:
    - Public data: Uses app credentials (everyone can use)
    - Seller data: Uses user credentials (only if connected)
    """
    
    def __init__(self):
        # App credentials (from .env) - try new names first, fallback to legacy
        self.app_lwa_id = os.getenv("SP_API_LWA_APP_ID") or settings.SP_API_LWA_APP_ID or settings.SPAPI_LWA_CLIENT_ID
        self.app_lwa_secret = os.getenv("SP_API_LWA_CLIENT_SECRET") or settings.SP_API_LWA_CLIENT_SECRET or settings.SPAPI_LWA_CLIENT_SECRET
        self.app_refresh_token = os.getenv("SP_API_REFRESH_TOKEN") or settings.SP_API_REFRESH_TOKEN or settings.SPAPI_REFRESH_TOKEN
        
        # Cached app token
        self._app_access_token = None
        self._app_token_expires = None
        
        # Check if app credentials configured
        self.app_configured = all([
            self.app_lwa_id,
            self.app_lwa_secret,
            self.app_refresh_token
        ])
        
        if not self.app_configured:
            logger.warning("⚠️ SP-API app credentials not configured")
        else:
            logger.info("✅ SP-API app credentials loaded")
        
        # Regional endpoints
        self.endpoints = {
            "NA": "https://sellingpartnerapi-na.amazon.com",
            "EU": "https://sellingpartnerapi-eu.amazon.com",
            "FE": "https://sellingpartnerapi-fe.amazon.com"
        }
        
        # Marketplace to region mapping
        self.marketplace_regions = {
            "ATVPDKIKX0DER": "NA",   # US
            "A2EUQ1WTGCTBG2": "NA",  # CA
            "A1AM78C64UM0Y8": "NA",  # MX
            "A1F83G8C2ARO7P": "EU",  # UK
            "A13V1IB3VIYBER": "EU",  # FR
            "A1PA6795UKMFR9": "EU",  # DE
            "APJ6JRA9NG5V4": "EU",   # IT
            "A1RKKUPIHCS9HS": "EU",  # ES
            "A1VC38T7YXB528": "FE",  # JP
            "A39IBJ37TRP1C6": "FE",  # AU
        }
    
    def _get_endpoint(self, marketplace_id: str) -> str:
        """Get API endpoint for marketplace."""
        region = self.marketplace_regions.get(marketplace_id, "NA")
        return self.endpoints[region]
    
    # ==========================================
    # TOKEN MANAGEMENT
    # ==========================================
    
    async def _get_app_access_token(self) -> Optional[str]:
        """Get access token using APP credentials."""
        if not self.app_configured:
            return None
        
        # Return cached if valid
        if self._app_access_token and self._app_token_expires:
            if datetime.utcnow() < self._app_token_expires - timedelta(minutes=5):
                return self._app_access_token
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.amazon.com/auth/o2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.app_refresh_token,
                        "client_id": self.app_lwa_id,
                        "client_secret": self.app_lwa_secret
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"App LWA token error: {response.status_code} - {response.text[:200]}")
                    return None
                
                data = response.json()
                self._app_access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self._app_token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info("✅ SP-API app token refreshed")
                return self._app_access_token
                
        except Exception as e:
            logger.error(f"Error getting app token: {e}")
            return None
    
    async def _get_user_access_token(self, user_id: str, marketplace_id: str) -> Optional[str]:
        """Get access token using USER credentials (if connected)."""
        try:
            # Get user's connection
            result = supabase.table("amazon_connections")\
                .select("refresh_token_encrypted, is_connected")\
                .eq("user_id", user_id)\
                .eq("marketplace_id", marketplace_id)\
                .eq("is_connected", True)\
                .limit(1)\
                .execute()
            
            if not result.data:
                return None
            
            encrypted_token = result.data[0].get("refresh_token_encrypted")
            if not encrypted_token:
                return None
            
            # Decrypt token (if encryption is used)
            # For now, assume it's stored plain (should be encrypted in production)
            refresh_token = encrypted_token
            
            # Get access token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.amazon.com/auth/o2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.app_lwa_id,
                        "client_secret": self.app_lwa_secret
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"User LWA token error: {response.status_code}")
                    return None
                
                return response.json().get("access_token")
                
        except Exception as e:
            logger.error(f"Error getting user token: {e}")
            return None
    
    async def _request(
        self, 
        method: str, 
        path: str, 
        marketplace_id: str,
        params: dict = None, 
        json_data: dict = None,
        use_user_token: bool = False,
        user_id: str = None,
        max_retries: int = 5,
        limiter_name: str = "competitive_pricing"
    ) -> Optional[dict]:
        """SP-API request with token bucket rate limiting + 429 retry + exponential backoff."""
        
        # Get token based on request type
        if use_user_token and user_id:
            token = await self._get_user_access_token(user_id, marketplace_id)
            if not token:
                logger.warning(f"User {user_id} not connected, cannot make seller request")
                return None
        else:
            token = await self._get_app_access_token()
        
        if not token:
            logger.error("No access token available")
            return None
        
        endpoint = self._get_endpoint(marketplace_id)
        url = f"{endpoint}{path}"
        
        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Get rate limiter for this endpoint
        limiter = None
        if USE_TOKEN_BUCKET:
            # Use specific limiters for pricing and fees
            if limiter_name == "competitive_pricing" and sp_api_pricing_limiter:
                limiter = sp_api_pricing_limiter
            elif limiter_name == "fees_estimate" and sp_api_fees_limiter:
                limiter = sp_api_fees_limiter
            elif get_limiter:
                limiter = get_limiter(limiter_name)
        
        for attempt in range(max_retries):
            # Apply token bucket rate limiting (blocks until token available)
            if limiter:
                if not limiter.acquire(tokens=1, timeout=120):
                    logger.error(f"Rate limit timeout for {path}")
                    return None
            elif USE_DISTRIBUTED_LIMITER and sp_api_limiter:
                sp_api_limiter.wait()
            else:
                _rate_limit()
            
            try:
                # Log SP-API request for debugging
                logger.info(f"📡 SP-API REQUEST: {method} {path} | Marketplace: {marketplace_id} | User: {user_id or 'APP'}")
                if json_data and len(str(json_data)) < 500:
                    logger.debug(f"SP-API {method} {path} body: {json_data}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_data,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ SP-API SUCCESS: {method} {path} | Status: 200")
                        return result
                    
                    elif response.status_code == 429:
                        # Exponential backoff: 2, 4, 8, 16, 32 sec
                        wait = min(2 ** (attempt + 1), 32) * random.uniform(0.8, 1.2)
                        logger.warning(f"⏳ 429 on {path} - waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait)
                        continue
                    
                    elif response.status_code == 503:
                        wait = 2 ** attempt
                        logger.warning(f"⏳ 503 on {path} - waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait)
                        continue
                    
                    else:
                        logger.error(f"SP-API {path}: {response.status_code} - {response.text[:500]}")
                        if attempt == max_retries - 1:
                            return None
                        # Retry on other errors with shorter backoff
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout on {path}, retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                logger.error(f"SP-API error on {path}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
        
        logger.error(f"❌ SP-API {path}: All {max_retries} retries exhausted")
        
        # Log all SP-API calls for debugging
        logger.info(f"📡 SP-API CALL: {method} {path} | Status: {response.status_code if 'response' in locals() else 'FAILED'} | ASINs: {asin_list if 'asin_list' in locals() else 'N/A'}")
        return None
    
    # ==========================================
    # PUBLIC DATA METHODS (App Credentials)
    # No user_id needed - works for everyone
    # ==========================================
    
    async def get_competitive_pricing(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[dict]:
        """Get competitive pricing - PUBLIC DATA."""
        if not self.app_configured:
            logger.warning("SP-API not configured, cannot get pricing")
            return None
        
        data = await self._request(
            "GET",
            "/products/pricing/v0/competitivePrice",
            marketplace_id,
            limiter_name="competitive_pricing",
            params={
                "MarketplaceId": marketplace_id,
                "Asins": asin,
                "ItemType": "Asin"
            }
        )
        
        if not data or "payload" not in data:
            return None
        
        payload = data.get("payload", [])
        if not payload:
            return None
        
        product = payload[0].get("Product", {})
        competitive_pricing = product.get("CompetitivePricing", {})
        competitive_prices = competitive_pricing.get("CompetitivePrices", [])
        number_of_offers = competitive_pricing.get("NumberOfOfferListings", [])
        
        result = {
            "asin": asin,
            "buy_box_price": None,
            "lowest_price": None,
            "offer_count": 0,
            "amazon_sells": False
        }
        
        # Parse prices
        for price in competitive_prices:
            condition = price.get("condition", "")
            price_id = price.get("CompetitivePriceId", "")
            
            if condition == "New":
                amount = price.get("Price", {}).get("ListingPrice", {}).get("Amount")
                if amount:
                    if price_id == "1":  # Buy Box
                        result["buy_box_price"] = float(amount)
                    else:
                        if result["lowest_price"] is None or float(amount) < result["lowest_price"]:
                            result["lowest_price"] = float(amount)
        
        # Parse offer count
        for offer in number_of_offers:
            if offer.get("condition") == "New":
                result["offer_count"] = offer.get("Count", 0)
        
        logger.info(f"✅ SP-API pricing for {asin}: ${result['buy_box_price']}")
        return result
    
    async def get_fee_estimate(self, asin: str, price: float, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[dict]:
        """Get FBA fees estimate with correct response parsing."""
        if not self.app_configured:
            return None
        
        # Validate price
        if not price or price <= 0:
            logger.warning(f"Invalid price for fees estimate: {price}")
            return None
        
        # Ensure price is a float
        price = float(price)
        
        # CORRECT PATH: /products/fees/v0/items/{asin}/feesEstimate
        path = f"/products/fees/v0/items/{asin}/feesEstimate"
        
        # CORRECT BODY STRUCTURE
        body = {
            "FeesEstimateRequest": {
                "MarketplaceId": marketplace_id,
                "IsAmazonFulfilled": True,
                "Identifier": asin,
                "PriceToEstimateFees": {
                    "ListingPrice": {
                        "CurrencyCode": "USD",
                        "Amount": price
                    }
                }
            }
        }
        
        logger.debug(f"SP-API fees estimate POST {path} body: {body}")
        
        data = await self._request(
            "POST",
            path,
            marketplace_id,
            limiter_name="fees_estimate",
            json_data=body
        )
        
        if not data:
            logger.warning(f"No fees data returned for {asin}")
            return None
        
        # DEBUG: Log the actual response structure
        import json
        logger.debug(f"📦 FEES RAW RESPONSE for {asin}: {json.dumps(data, indent=2)}")
        
        # The response structure can be:
        # {
        #   "payload": {
        #     "FeesEstimateResult": {
        #       "FeesEstimate": {
        #         "TotalFeesEstimate": {"Amount": 12.34, "CurrencyCode": "USD"},
        #         "FeeDetailList": [...]
        #       },
        #       "FeesEstimateIdentifier": {...}
        #     }
        #   }
        # }
        # OR the response might be directly in payload
        
        # Try multiple possible response structures
        payload = data.get("payload") or data
        fees_result = payload.get("FeesEstimateResult") or payload
        fees_estimate = fees_result.get("FeesEstimate") or fees_result
        
        # Check if we got fees data - don't check for "Status" field
        if not fees_estimate:
            # Log the actual response to debug
            logger.warning(f"No FeesEstimate in response for {asin}. Response keys: {list(data.keys()) if data else 'None'}")
            if payload:
                logger.warning(f"Payload keys: {list(payload.keys())}")
            return None
        
        total_fees = fees_estimate.get("TotalFeesEstimate", {})
        fee_details = fees_estimate.get("FeeDetailList", [])
        
        # If no total fees and no details, response might be in different format
        if not total_fees and not fee_details:
            logger.warning(f"Empty fees response for {asin}. FeesEstimate keys: {list(fees_estimate.keys())}")
            return None
        
        result = {
            "total": float(total_fees.get("Amount", 0)) if total_fees else 0,
            "currency": total_fees.get("CurrencyCode", "USD") if total_fees else "USD",
            "referral_fee": 0,
            "fba_fulfillment_fee": 0,
            "variable_closing": 0,
            "per_item": 0
        }
        
        # Parse individual fees
        for fee in fee_details:
            fee_type = fee.get("FeeType", "")
            final_fee = fee.get("FinalFee", {})
            amount = float(final_fee.get("Amount", 0)) if final_fee else 0
            
            if "Referral" in fee_type:
                result["referral_fee"] = amount
            elif "FBA" in fee_type or "Fulfillment" in fee_type:
                result["fba_fulfillment_fee"] = amount
            elif "VariableClosing" in fee_type or "Closing" in fee_type:
                result["variable_closing"] = amount
            elif "PerItem" in fee_type:
                result["per_item"] = amount
        
        # If total wasn't in response, calculate from details
        if result["total"] == 0 and fee_details:
            result["total"] = result["referral_fee"] + result["fba_fulfillment_fee"] + result["variable_closing"] + result["per_item"]
        
        # Only return if we have valid fees
        if result["total"] > 0:
            logger.info(f"✅ SP-API fees for {asin}: ${result['total']:.2f} (Referral: ${result['referral_fee']:.2f}, FBA: ${result['fba_fulfillment_fee']:.2f})")
            return result
        else:
            logger.warning(f"⚠️ Zero fees calculated for {asin} - response may be incomplete")
            return None
    
    async def search_catalog_items(
        self,
        identifiers: List[str],
        identifiers_type: str = "UPC",
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Optional[dict]:
        """
        Search catalog items by UPC/EAN/GTIN identifiers.
        
        Args:
            identifiers: List of UPC/EAN/GTIN codes
            identifiers_type: Type of identifier (UPC, EAN, GTIN)
            marketplace_id: Amazon marketplace ID
            
        Returns:
            Catalog search results with items containing ASINs
        """
        if not self.app_configured:
            return None
        
        if not identifiers:
            return None
        
        # SP-API catalog search endpoint
        data = await self._request(
            "GET",
            "/catalog/2022-04-01/items",
            marketplace_id,
            limiter_name="catalog",
            params={
                "marketplaceIds": marketplace_id,
                "identifiers": ",".join(identifiers),
                "identifiersType": identifiers_type,
                "includedData": "summaries"
            }
        )
        
        if not data:
            return None
        
        return data
    
    async def get_catalog_item(
        self, 
        asin: str, 
        marketplace_id: str = "ATVPDKIKX0DER",
        included_data: List[str] = None
    ) -> Optional[dict]:
        """
        Get catalog item details - PUBLIC DATA with caching.
        Returns BOTH processed dict AND raw response for storage.
        """
        if not self.app_configured:
            return None
        
        included_data = included_data or ['summaries', 'images', 'attributes', 'salesRanks']
        
        # IMPROVEMENT 4: Check cache first
        try:
            from app.cache import cache
            cache_key = f"catalog:{asin}:{marketplace_id}"
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache hit for catalog:{asin}")
                # If cached data is old format, return it as processed
                if 'processed' in cached_data:
                    return cached_data
                # Legacy format - wrap it
                return {'processed': cached_data, 'raw': cached_data}
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
        
        logger.info(f"📡 Cache miss, fetching from SP-API: {asin}")
        
        # Make the API call - this returns the RAW response
        raw_data = await self._request(
            "GET",
            f"/catalog/2022-04-01/items/{asin}",
            marketplace_id,
            limiter_name="catalog",
            params={
                "marketplaceIds": marketplace_id,
                "includedData": ",".join(included_data)
            }
        )
        
        if not raw_data:
            return None
        
        # Extract processed data from raw response
        summaries = raw_data.get("summaries", [])
        summary = summaries[0] if summaries else {}
        
        images = raw_data.get("images", [])
        main_image = None
        if images:
            for img_set in images:
                for img in img_set.get("images", []):
                    if img.get("variant") == "MAIN":
                        main_image = img.get("link")
                        break
        
        sales_ranks = raw_data.get("salesRanks", [])
        bsr = None
        if sales_ranks:
            for rank in sales_ranks:
                display_ranks = rank.get("displayGroupRanks", [])
                if display_ranks:
                    bsr = display_ranks[0].get("rank")
                    break
        
        processed = {
            "asin": asin,
            "title": summary.get("itemName"),
            "brand": summary.get("brandName") or summary.get("brand"),
            "image_url": main_image,
            "sales_rank": bsr,
            "sales_rank_category": summary.get("websiteDisplayGroup"),
            "parentAsin": summary.get("parentAsin"),  # For variation detection
            "isPrimeEligible": summary.get("isPrimeEligible", False)
        }
        
        # Return BOTH processed and raw
        result = {
            "processed": processed,
            "raw": raw_data  # Store the raw response for extraction
        }
        
        # Cache for 24 hours
        try:
            from app.cache import cache
            cache.set(cache_key, result, ttl=86400)
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")
        
        return result
    
    async def get_parent_asin(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[str]:
        """
        Get parent ASIN for a variation.
        Returns None if ASIN is already parent or has no parent.
        """
        try:
            # Use catalog API to get variation info
            response = await self.get_catalog_item(asin, marketplace_id)
            
            if response and response.get('parentAsin'):
                return response['parentAsin']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get parent ASIN for {asin}: {e}")
            return None
    
    async def get_asin_quality_indicators(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> Dict:
        """
        Get quality indicators for ASIN selection.
        """
        indicators = {
            'bsr': None,
            'review_count': None,
            'rating': None,
            'has_prime': False,
            'is_buybox_winner': False,
            'condition': 'new'
        }
        
        try:
            # Get catalog data
            catalog = await self.get_catalog_item(asin, marketplace_id)
            if catalog:
                indicators['bsr'] = catalog.get('sales_rank')
                indicators['has_prime'] = catalog.get('isPrimeEligible', False)
            
            # Get pricing (check buybox)
            try:
                pricing = await self.get_competitive_pricing([asin], marketplace_id)
                if pricing and pricing.get(asin):
                    price_data = pricing[asin]
                    indicators['is_buybox_winner'] = price_data.get('isBuyBoxWinner', False)
            except Exception as e:
                logger.debug(f"Could not get pricing for quality indicators: {e}")
            
            # Note: Review count and rating would require additional API calls
            # For now, we'll leave them as None and can be filled by Keepa if available
            
        except Exception as e:
            logger.error(f"Failed to get quality indicators for {asin}: {e}")
        
        return indicators
    
    async def get_item_offers(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[dict]:
        """Get all offers for a product - PUBLIC DATA."""
        if not self.app_configured:
            return None
        
        data = await self._request(
            "GET",
            f"/products/pricing/v0/items/{asin}/offers",
            marketplace_id,
            limiter_name="item_offers",
            params={
                "MarketplaceId": marketplace_id,
                "ItemCondition": "New"
            }
        )
        
        if not data:
            return None
        
        payload = data.get("payload", {})
        offers = payload.get("Offers", [])
        
        result = {
            "asin": asin,
            "total_offers": len(offers),
            "num_fba_sellers": 0,
            "num_fbm_sellers": 0,
            "amazon_is_seller": False,
            "buy_box_price": None,
            "lowest_fba_price": None,
            "lowest_fbm_price": None
        }
        
        for offer in offers:
            is_fba = offer.get("IsFulfilledByAmazon", False)
            is_buy_box = offer.get("IsBuyBoxWinner", False)
            seller_id = offer.get("SellerId", "")
            
            price = offer.get("ListingPrice", {}).get("Amount")
            
            if seller_id == "ATVPDKIKX0DER":  # Amazon
                result["amazon_is_seller"] = True
            
            if is_fba:
                result["num_fba_sellers"] += 1
                if price and (result["lowest_fba_price"] is None or price < result["lowest_fba_price"]):
                    result["lowest_fba_price"] = float(price)
            else:
                result["num_fbm_sellers"] += 1
                if price and (result["lowest_fbm_price"] is None or price < result["lowest_fbm_price"]):
                    result["lowest_fbm_price"] = float(price)
            
            if is_buy_box and price:
                result["buy_box_price"] = float(price)
        
        return result
    
    async def check_eligibility(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[dict]:
        """Check listing restrictions - PUBLIC DATA."""
        if not self.app_configured:
            return None
        
        data = await self._request(
            "GET",
            "/listings/2021-08-01/restrictions",
            marketplace_id,
            limiter_name="competitive_pricing",  # Use default limiter
            params={
                "asin": asin,
                "sellerId": settings.SELLER_ID or "ATVPDKIKX0DER",  # Use app seller ID
                "marketplaceIds": marketplace_id
            }
        )
        
        if not data:
            return None
        
        restrictions = data.get("restrictions", [])
        if not restrictions:
            return {"status": "ELIGIBLE", "can_list": True, "reasons": []}
        
        restriction = restrictions[0]
        reasons = restriction.get("reasons", [])
        
        return {
            "status": restriction.get("status", "UNKNOWN"),
            "can_list": restriction.get("status") == "ELIGIBLE",
            "reasons": [r.get("message") for r in reasons]
        }
    
    # ==========================================
    # USER-SPECIFIC METHODS (User Credentials)
    # Requires user to connect their Seller account
    # ==========================================
    
    async def is_user_connected(self, user_id: str, marketplace_id: str = "ATVPDKIKX0DER") -> bool:
        """Check if user has connected their seller account."""
        try:
            result = supabase.table("amazon_connections")\
                .select("is_connected")\
                .eq("user_id", user_id)\
                .eq("marketplace_id", marketplace_id)\
                .limit(1)\
                .execute()
            
            return result.data and result.data[0].get("is_connected", False)
        except:
            return False
    
    async def get_my_inventory(self, user_id: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[list]:
        """Get user's FBA inventory - REQUIRES USER CONNECTION."""
        if not await self.is_user_connected(user_id, marketplace_id):
            logger.warning(f"User {user_id} not connected, cannot get inventory")
            return None
        
        data = await self._request(
            "GET",
            "/fba/inventory/v1/summaries",
            marketplace_id,
            params={
                "marketplaceIds": marketplace_id,
                "granularityType": "Marketplace",
                "granularityId": marketplace_id
            },
            use_user_token=True,
            user_id=user_id
        )
        
        if not data:
            return None
        
        return data.get("payload", {}).get("inventorySummaries", [])
    
    async def get_my_orders(self, user_id: str, marketplace_id: str = "ATVPDKIKX0DER", days: int = 30) -> Optional[list]:
        """Get user's orders - REQUIRES USER CONNECTION."""
        if not await self.is_user_connected(user_id, marketplace_id):
            return None
        
        created_after = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        data = await self._request(
            "GET",
            "/orders/v0/orders",
            marketplace_id,
            limiter_name="competitive_pricing",  # Use default limiter for seller endpoints
            params={
                "MarketplaceIds": marketplace_id,
                "CreatedAfter": created_after
            },
            use_user_token=True,
            user_id=user_id
        )
        
        if not data:
            return None
        
        return data.get("payload", {}).get("Orders", [])
    
    # ==========================================
    # BATCH ENDPOINTS - Key to performance!
    # ==========================================
    
    async def get_competitive_pricing_batch(
        self, 
        asins: List[str], 
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Dict[str, dict]:
        """
        Get competitive pricing for UP TO 20 ASINs in ONE call.
        Returns dict mapping ASIN -> pricing data.
        """
        if not self.app_configured or not asins:
            return {}
        
        # SP-API accepts comma-separated ASINs (max 20)
        asin_list = asins[:20]
        
        data = await self._request(
            "GET",
            "/products/pricing/v0/competitivePrice",
            marketplace_id,
            limiter_name="competitive_pricing",
            params={
                "MarketplaceId": marketplace_id,
                "Asins": ",".join(asin_list),
                "ItemType": "Asin"
            }
        )
        
        if not data or "payload" not in data:
            return {}
        
        results = {}
        payload = data.get("payload", [])
        
        for item in payload:
            asin = item.get("ASIN")
            if not asin:
                continue
            
            product = item.get("Product", {})
            pricing = product.get("CompetitivePricing", {})
            prices = pricing.get("CompetitivePrices", [])
            offers = pricing.get("NumberOfOfferListings", [])
            
            result = {"asin": asin, "buy_box_price": None, "offer_count": 0}
            
            # Parse buy box price
            for price in prices:
                if price.get("CompetitivePriceId") == "1":  # Buy Box
                    amount = price.get("Price", {}).get("ListingPrice", {}).get("Amount")
                    if amount:
                        result["buy_box_price"] = float(amount)
                        break
            
            # Parse offer count
            for offer in offers:
                if offer.get("condition") == "New":
                    result["offer_count"] = offer.get("Count", 0)
                    break
            
            results[asin] = result
        
        logger.info(f"✅ Batch pricing: {len(results)}/{len(asin_list)} ASINs")
        return results
    
    async def get_fees_estimate_batch(
        self,
        items: List[dict],  # [{"asin": "B00...", "price": 29.99}, ...]
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Dict[str, dict]:
        """
        Get fees for up to 20 items in ONE call using batch endpoint.
        
        Endpoint: POST /products/fees/v0/feesEstimate
        
        Request body format:
        [
            {
                "IdType": "ASIN",           # REQUIRED at top level!
                "IdValue": "B00...",        # REQUIRED at top level!
                "FeesEstimateRequest": {
                    "MarketplaceId": "...",
                    "Identifier": "B00...",
                    "IsAmazonFulfilled": true,
                    "PriceToEstimateFees": {...}
                }
            },
            ...
        ]
        """
        if not self.app_configured or not items:
            return {}
        
        results = {}
        
        # Process in batches of 20
        for i in range(0, len(items), 20):
            batch = items[i:i + 20]
            
            # Build batch request body - CORRECT FORMAT
            # IdType and IdValue must be at TOP LEVEL, not inside FeesEstimateRequest
            body = []
            for item in batch:
                body.append({
                    "IdType": "ASIN",  # REQUIRED - at top level!
                    "IdValue": item["asin"],  # REQUIRED - at top level!
                    "FeesEstimateRequest": {
                        "MarketplaceId": marketplace_id,
                        "Identifier": item["asin"],
                        "IsAmazonFulfilled": True,
                        "PriceToEstimateFees": {
                            "ListingPrice": {
                                "CurrencyCode": "USD",
                                "Amount": float(item["price"])
                            }
                        }
                    }
                })
            
            # Debug: log first request body
            if i == 0 and body:
                import json
                logger.info(f"📤 Fees request body sample: {json.dumps(body[0], indent=2)}")
            
            # Call BATCH endpoint (not single-item endpoint!)
            data = await self._request(
                "POST",
                "/products/fees/v0/feesEstimate",  # BATCH endpoint
                marketplace_id,
                json_data=body,
                limiter_name="fees_estimate"
            )
            
            if not data:
                logger.warning(f"Fees batch returned no data")
                continue
            
            # DEBUG: Log the actual response structure
            logger.info(f"🔍 Fees batch response type: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'N/A (list)'}")
            if isinstance(data, dict):
                logger.debug(f"🔍 Fees batch response sample: {str(data)[:500]}")
            elif isinstance(data, list) and len(data) > 0:
                logger.debug(f"🔍 Fees batch response sample (first item): {str(data[0])[:500]}")
            
            # Parse batch response
            # Response can be either:
            # 1. List directly: [{"Status": "Success", ...}, ...]
            # 2. Dict with payload: {"payload": [{"Status": "Success", ...}, ...]}
            # 3. Dict with "FeesEstimateResult" key containing a list
            payload = None
            if isinstance(data, list):
                payload = data
            elif isinstance(data, dict):
                # Try different possible keys
                payload = data.get("payload") or data.get("FeesEstimateResult") or data.get("results")
                if not isinstance(payload, list):
                    # Maybe it's a dict with ASIN keys?
                    if all(isinstance(k, str) and len(k) == 10 for k in data.keys()):
                        # Convert dict to list
                        payload = list(data.values())
                    else:
                        logger.warning(f"Fees batch response payload is not a list: {type(payload)}, keys: {list(data.keys())[:10]}")
                        continue
            else:
                logger.warning(f"Fees batch response is unexpected type: {type(data)}")
                continue
            
            logger.info(f"🔍 Parsing {len(payload)} fee responses from batch")
            
            parsed_count = 0
            for idx, resp in enumerate(payload):
                try:
                    # Log first response structure for debugging
                    if idx == 0:
                        logger.info(f"🔍 First fee response keys: {list(resp.keys()) if isinstance(resp, dict) else 'not a dict'}")
                        logger.info(f"🔍 First fee response full: {resp}")
                    
                    # Check if this is an error response FIRST
                    if "Error" in resp:
                        error_info = resp.get("Error", {})
                        error_code = error_info.get("Code", "Unknown")
                        error_msg = error_info.get("Message", "Unknown error")
                        # Extract ASIN for logging
                        identifier = resp.get("FeesEstimateIdentifier", {})
                        asin = None
                        if isinstance(identifier, dict):
                            asin = identifier.get("IdValue") or identifier.get("Identifier")
                        logger.warning(f"❌ Fees estimate ERROR for ASIN {asin or 'unknown'}: {error_code} - {error_msg}")
                        continue
                    
                    # Try different possible status fields
                    status = resp.get("Status") or resp.get("status") or resp.get("FeesEstimateResult", {}).get("Status")
                    if status and status != "Success":
                        logger.warning(f"⚠️ Fees estimate status: {status} for response {idx} (not Success)")
                        # Still try to parse if Status is missing but FeesEstimate exists
                        if not resp.get("FeesEstimate"):
                            continue
                    
                    # Extract ASIN from FeesEstimateIdentifier
                    identifier = resp.get("FeesEstimateIdentifier", {})
                    asin = identifier.get("IdValue") or identifier.get("SellerInputIdentifier") or identifier.get("Identifier")
                    
                    if not asin:
                        logger.warning(f"Could not extract ASIN from fee response {idx}: identifier={identifier}")
                        continue
                    
                    # Try different ways to get fees estimate
                    estimate = resp.get("FeesEstimate") or resp.get("feesEstimate") or resp.get("FeesEstimateResult", {}).get("FeesEstimate")
                    if not estimate and isinstance(resp, dict):
                        # Maybe the whole response IS the estimate?
                        if "TotalFeesEstimate" in resp or "totalFeesEstimate" in resp:
                            estimate = resp
                    
                    if not estimate:
                        logger.warning(f"No FeesEstimate found for {asin} in response {idx}")
                        continue
                    
                    if isinstance(estimate, dict):
                        total_estimate = estimate.get("TotalFeesEstimate") or estimate.get("totalFeesEstimate") or {}
                        fee_details = estimate.get("FeeDetailList") or estimate.get("feeDetailList") or []
                    else:
                        total_estimate = {}
                        fee_details = []
                    
                    result = {
                        "asin": asin,
                        "total": float(total_estimate.get("Amount", 0)) if isinstance(total_estimate, dict) and total_estimate else 0,
                        "referral_fee": 0,
                        "fba_fulfillment_fee": 0
                    }
                    
                    for fee in fee_details:
                        if not isinstance(fee, dict):
                            continue
                        fee_type = fee.get("FeeType") or fee.get("feeType") or ""
                        final_fee = fee.get("FinalFee") or fee.get("finalFee") or {}
                        amount = float(final_fee.get("Amount", 0)) if isinstance(final_fee, dict) and final_fee else 0
                        
                        if "Referral" in fee_type or "referral" in fee_type.lower():
                            result["referral_fee"] = amount
                        elif "FBA" in fee_type or "Fulfillment" in fee_type or "fba" in fee_type.lower() or "fulfillment" in fee_type.lower():
                            result["fba_fulfillment_fee"] += amount
                    
                    results[asin] = result
                    parsed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error parsing fee response {idx}: {e}, response keys: {list(resp.keys())[:10] if isinstance(resp, dict) else 'not a dict'}")
            
            logger.info(f"✅ Batch fees: {parsed_count}/{len(batch)} items parsed, {len(results)} total results")
        
        return results
    
    async def get_catalog_items(
        self,
        asins: List[str],
        marketplace_id: str = "ATVPDKIKX0DER",
        included_data: List[str] = None,
        rate_limit: int = 5  # SP-API limit: 5 req/sec
    ) -> Dict[str, dict]:
        """
        Get catalog items for multiple ASINs with rate limiting.
        Returns dict mapping ASIN -> {processed, raw}
        Note: SP-API catalog doesn't support batching, so we parallelize with semaphore.
        """
        if not self.app_configured or not asins:
            return {}
        
        included_data = included_data or ['summaries', 'images', 'attributes', 'salesRanks']
        asin_list = asins[:20]  # Limit to 20 for reasonable parallelization
        results = {}
        
        # IMPROVEMENT 6: Use semaphore to respect rate limits (5 req/sec for SP-API)
        sem = asyncio.Semaphore(rate_limit)
        
        async def get_catalog_with_semaphore(asin: str):
            async with sem:
                # 200ms delay between requests (5 req/sec)
                await asyncio.sleep(0.2)
                try:
                    catalog = await self.get_catalog_item(asin, marketplace_id, included_data)
                    return asin, catalog
                except Exception as e:
                    logger.error(f"Failed to fetch catalog for {asin}: {e}")
                    return asin, None
        
        tasks = [get_catalog_with_semaphore(asin) for asin in asin_list]
        catalog_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in catalog_results:
            if isinstance(result, Exception):
                continue
            asin, catalog = result
            if catalog:
                results[asin] = catalog
        
        logger.info(f"✅ Fetched {len(results)} catalog items (rate-limited)")
        
        logger.info(f"✅ Batch catalog: {len(results)}/{len(asin_list)} ASINs")
        return results
    
    async def get_catalog_items_batch(
        self,
        asins: List[str],
        marketplace_id: str = "ATVPDKIKX0DER",
        rate_limit: int = 5  # SP-API limit: 5 req/sec
    ) -> Dict[str, dict]:
        """
        DEPRECATED: Use get_catalog_items instead.
        Kept for backward compatibility.
        """
        return await self.get_catalog_items(asins, marketplace_id, None, rate_limit)
    


# Global instance
sp_api_client = SPAPIClient()
