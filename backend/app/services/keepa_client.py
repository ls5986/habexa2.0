"""
Keepa API client with BATCH cache lookups and BATCH API calls.
"""
import asyncio
import httpx
import logging
import os
from typing import Optional, List, Dict, Any
from app.services.supabase_client import supabase
from app.core.config import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")
KEEPA_API_URL = "https://api.keepa.com"


class KeepaError(Exception):
    """Custom exception for Keepa API errors."""
    pass


class KeepaClient:
    """
    Keepa client with BATCH cache lookups and BATCH API calls.
    """
    
    def __init__(self):
        self.api_key = KEEPA_API_KEY
        self.base_url = KEEPA_API_URL
        self.cache_hours = settings.KEEPA_CACHE_HOURS
    
    # ==========================================
    # BATCH CACHE LOOKUP - One query for all ASINs
    # ==========================================
    
    async def _get_cached_batch(self, asins: List[str]) -> Dict[str, dict]:
        """Get cached products in ONE query."""
        if not asins:
            return {}
        
        try:
            expires_after = datetime.utcnow().isoformat()
            
            # BATCH query - all ASINs at once
            result = supabase.table("keepa_cache")\
                .select("asin, data")\
                .in_("asin", asins)\
                .gt("expires_at", expires_after)\
                .execute()
            
            cached = {}
            for row in result.data or []:
                asin = row.get("asin")
                data = row.get("data")
                if asin and data:
                    cached[asin] = data
            
            if cached:
                logger.info(f"📦 Keepa cache hit: {len(cached)}/{len(asins)} ASINs")
            
            return cached
            
        except Exception as e:
            logger.warning(f"Cache batch read error: {e}")
            return {}
    
    async def _set_cached_batch(self, products: Dict[str, dict]):
        """Cache multiple products in ONE upsert."""
        if not products:
            return
        
        try:
            expires_at = (datetime.utcnow() + timedelta(hours=self.cache_hours)).isoformat()
            
            rows = [
                {
                    "asin": asin,
                    "marketplace_id": "ATVPDKIKX0DER",
                    "data": data,
                    "expires_at": expires_at
                }
                for asin, data in products.items()
            ]
            
            supabase.table("keepa_cache")\
                .upsert(rows, on_conflict="asin,marketplace_id")\
                .execute()
            
            logger.info(f"💾 Cached {len(rows)} products to Keepa cache")
                
        except Exception as e:
            logger.warning(f"Cache batch write error: {e}")
    
    # ==========================================
    # BATCH API CALL - Up to 100 ASINs per request
    # ==========================================
    
    async def get_products_batch(
        self,
        asins: List[str],
        domain: int = 1,
        history: bool = False,
        days: int = 90
    ) -> Dict[str, dict]:
        """
        Get product data for up to 100 ASINs.
        
        1. Check cache for all ASINs (ONE query)
        2. Fetch uncached ASINs from Keepa API (ONE call per 100)
        3. Cache new results
        
        Returns: Dict[asin, product_data]
        """
        if not asins or not self.api_key:
            return {}
        
        # Deduplicate
        asins = list(set(asins))
        
        # STEP 1: Batch cache lookup (ONE query)
        cached = await self._get_cached_batch(asins)
        uncached_asins = [a for a in asins if a not in cached]
        
        if not uncached_asins:
            logger.info(f"✅ All {len(asins)} ASINs found in cache")
            return cached
        
        logger.info(f"🔍 {len(cached)} cached, {len(uncached_asins)} need Keepa API")
        
        # STEP 2: Fetch from Keepa API in batches of 100
        fetched = {}
        
        for i in range(0, len(uncached_asins), 100):
            batch = uncached_asins[i:i + 100]
            
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.get(
                        f"{self.base_url}/product",
                        params={
                            "key": self.api_key,
                            "domain": domain,
                            "asin": ",".join(batch),
                            "stats": days,
                            "history": 1 if history else 0,
                            "rating": 1,
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Keepa API error: {response.status_code} - {response.text[:200]}")
                        continue
                    
                    data = response.json()
                    
                    # Check tokens remaining
                    tokens_left = data.get("tokensLeft", 0)
                    logger.info(f"🎟️ Keepa tokens remaining: {tokens_left}")
                    
                    # If low on tokens, wait
                    if tokens_left < 10:
                        logger.warning(f"⚠️ Low Keepa tokens: {tokens_left}, waiting 60s")
                        await asyncio.sleep(60)
                    
                    if "error" in data:
                        logger.error(f"Keepa error: {data['error']}")
                        continue
                    
                    # Parse products
                    for product in data.get("products", []):
                        asin = product.get("asin")
                        if not asin:
                            continue
                        
                        parsed = self._parse_product(product)
                        fetched[asin] = parsed
                    
                    logger.info(f"✅ Keepa API: {len(fetched)}/{len(batch)} products")
                    
            except Exception as e:
                logger.error(f"Keepa API request error: {e}")
        
        # STEP 3: Cache new results
        if fetched:
            await self._set_cached_batch(fetched)
        
        # Merge cached + fetched
        results = {**cached, **fetched}
        
        logger.info(f"✅ Keepa total: {len(results)}/{len(asins)} products")
        return results
    
    async def get_products_raw(
        self,
        asins: List[str],
        domain: int = 1,
        days: int = 365
    ) -> Dict[str, dict]:
        """
        Get raw Keepa product data without parsing.
        Used for 365-day stats extraction (stats.365, offers array).
        
        Unlike get_products_batch, this returns the raw Keepa API response
        so we can extract fba_lowest_365d, fbm_lowest_365d, FBA/FBM seller counts, etc.
        
        Args:
            asins: List of ASINs to fetch
            domain: Keepa domain (1 = US)
            days: Stats period (365 for yearly analysis)
        
        Returns:
            Dict mapping ASIN to raw Keepa product data
        """
        if not asins:
            return {}
        
        if not self.api_key:
            logger.warning("Keepa API key not configured")
            return {}
        
        results = {}
        batch_size = 100  # Keepa allows up to 100 ASINs per request
        
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.get(
                        f"{self.base_url}/product",
                        params={
                            "key": self.api_key,
                            "domain": domain,
                            "asin": ",".join(batch),
                            "stats": days,    # Get stats for X days (includes stats.365)
                            "history": 0,     # Don't need full CSV history (saves tokens)
                            "offers": 20,     # Get offers for FBA/FBM seller counts
                            "rating": 1,      # Include rating/reviews
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check for errors
                    if "error" in data:
                        logger.error(f"Keepa API error: {data['error']}")
                        continue
                    
                    # Check tokens remaining
                    tokens_left = data.get("tokensLeft", 0)
                    logger.info(f"🎟️ Keepa tokens remaining: {tokens_left}")
                    
                    # If low on tokens, wait
                    if tokens_left < 10:
                        logger.warning(f"⚠️ Low Keepa tokens: {tokens_left}, waiting 60s")
                        await asyncio.sleep(60)
                    
                    # Store raw product data
                    for product in data.get("products", []):
                        asin = product.get("asin")
                        if asin:
                            results[asin] = product  # Raw, unparsed data
                    
                    logger.info(f"✅ Keepa raw: fetched {len(batch)} products, got {len(data.get('products', []))} results")
                        
            except httpx.TimeoutException:
                logger.error(f"Keepa timeout for batch starting at {i}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Keepa HTTP error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Keepa raw fetch error: {e}")
            
            # Rate limiting - Keepa allows ~1 request per second
            if i + batch_size < len(asins):
                await asyncio.sleep(1)
        
        return results
    
    async def get_product(
        self,
        asin: str,
        domain: int = 1,
        days: int = 90,
        history: bool = False
    ) -> Optional[dict]:
        """
        Get product data for a single ASIN.
        Wrapper around get_products_batch for convenience.
        
        Args:
            asin: Amazon ASIN
            domain: Keepa domain (1 = US)
            days: Days of history/stats
            history: Whether to include full price history (CSV)
            
        Returns:
            Product data dict or None if not found
        """
        if not self.api_key:
            logger.warning("Keepa API key not configured")
            return None
        
        results = await self.get_products_batch(
            asins=[asin],
            domain=domain,
            days=days,
            history=history
        )
        
        return results.get(asin)
    
    async def get_token_status(self) -> dict:
        """Get current Keepa API token balance."""
        if not self.api_key:
            return {"tokens_left": 0, "error": "API key not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/token",
                    params={"key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "tokens_left": data.get("tokensLeft", 0),
                        "refill_rate": data.get("refillRate", 0),
                        "refill_in": data.get("refillIn", 0)
                    }
                else:
                    return {"tokens_left": 0, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting Keepa token status: {e}")
            return {"tokens_left": 0, "error": str(e)}
    
    def _parse_product(self, product: dict) -> dict:
        """Parse Keepa product response into our format."""
        stats = product.get("stats", {})
        current_stats = stats.get("current", [])
        
        # Get image URL
        images_csv = product.get("imagesCSV", "")
        image_url = None
        if images_csv:
            first_image = images_csv.split(",")[0]
            if first_image:
                image_url = f"https://images-na.ssl-images-amazon.com/images/I/{first_image}"
        
        # Get category
        category_tree = product.get("categoryTree", [])
        category = category_tree[-1].get("name") if category_tree else None
        
        # Get BSR from stats (index 3 in current array)
        bsr = None
        if len(current_stats) > 3 and current_stats[3] and current_stats[3] > 0:
            bsr = current_stats[3]
        
        # Get current price from stats (index 1 in current array = Amazon price)
        # Keepa stats array format: [timestamp, Amazon, New, Used, SalesRank, ...]
        current_price = None
        if len(current_stats) > 1 and current_stats[1] and current_stats[1] > 0:
            # Price is in cents, convert to dollars
            current_price = current_stats[1] / 100.0
        
        # Get rating
        rating = product.get("rating")
        if isinstance(rating, list):
            rating = (rating[0] / 10) if rating and rating[0] else None
        elif rating:
            rating = rating / 10
        
        # Get review count
        review_count = product.get("reviewCount")
        if isinstance(review_count, list):
            review_count = review_count[0] if review_count else None
        
        # Parse price history if available
        price_history = []
        rank_history = []
        
        # Keepa CSV format: [timestamp, Amazon, New, Used, SalesRank, ...]
        csv = product.get("csv", [])
        if csv and len(csv) > 0:
            for entry in csv:
                if len(entry) >= 5:
                    timestamp = entry[0]
                    amazon_price = entry[1] if entry[1] > 0 else None
                    sales_rank = entry[4] if entry[4] > 0 else None
                    
                    if amazon_price:
                        price_history.append({
                            "date": timestamp,
                            "price": amazon_price / 100.0  # Convert cents to dollars
                        })
                    
                    if sales_rank:
                        rank_history.append({
                            "date": timestamp,
                            "rank": sales_rank
                        })
        
        # Get averages from stats
        averages = {
            "price_30d": None,
            "price_90d": None,
            "rank_30d": None,
            "rank_90d": None
        }
        
        # Keepa stats format: stats.min[10] = FBA lowest 365d, stats.min[11] = FBM lowest 365d
        # stats.avg[1] = average Amazon price
        if stats:
            avg_prices = stats.get("avg", [])
            if len(avg_prices) > 1:
                averages["price_30d"] = avg_prices[1] / 100.0 if avg_prices[1] > 0 else None
            if len(avg_prices) > 1:
                averages["price_90d"] = avg_prices[1] / 100.0 if avg_prices[1] > 0 else None
            
            avg_ranks = stats.get("avg", [])
            if len(avg_ranks) > 4:
                averages["rank_30d"] = avg_ranks[4] if avg_ranks[4] > 0 else None
                averages["rank_90d"] = avg_ranks[4] if avg_ranks[4] > 0 else None
        
        return {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "brand": product.get("brand"),
            "image_url": image_url,
            "bsr": bsr,
            "category": category,
            "current_price": current_price,
            "buy_box_price": current_price,
            "sales_drops_30": stats.get("salesRankDrops30"),
            "sales_drops_90": stats.get("salesRankDrops90"),
            "sales_drops_180": stats.get("salesRankDrops180"),
            "variation_count": len(product.get("variations", [])) if product.get("variations") else 0,
            "amazon_in_stock": product.get("availabilityAmazon", -1) == 0,
            "rating": rating,
            "review_count": review_count,
            "price_history": price_history,
            "rank_history": rank_history,
            "averages": averages,
            "current": {
                "price": current_price,
                "bsr": bsr,
                "rating": rating,
                "review_count": review_count
            }
        }


# Singleton instance
keepa_client = KeepaClient()
