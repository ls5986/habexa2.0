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
        
        # Get BSR from stats
        bsr = None
        if len(current_stats) > 3 and current_stats[3] and current_stats[3] > 0:
            bsr = current_stats[3]
        
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
        
        return {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "brand": product.get("brand"),
            "image_url": image_url,
            "bsr": bsr,
            "category": category,
            "sales_drops_30": stats.get("salesRankDrops30"),
            "sales_drops_90": stats.get("salesRankDrops90"),
            "sales_drops_180": stats.get("salesRankDrops180"),
            "variation_count": len(product.get("variations", [])) if product.get("variations") else 0,
            "amazon_in_stock": product.get("availabilityAmazon", -1) == 0,
            "rating": rating,
            "review_count": review_count,
        }


# Singleton instance
keepa_client = KeepaClient()
