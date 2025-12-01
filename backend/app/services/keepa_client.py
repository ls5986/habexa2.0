"""
Keepa API client for fetching price history and product data.
"""
import os
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.supabase_client import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Keepa API endpoint
KEEPA_API_URL = "https://api.keepa.com"

# Keepa time epoch: minutes since 2011-01-01 00:00:00 UTC
KEEPA_EPOCH = datetime(2011, 1, 1, 0, 0, 0)

# Price type indices in Keepa csv array
PRICE_TYPES = {
    0: "amazon",
    1: "new",
    2: "used",
    3: "sales_rank",
    4: "list_price",
    5: "collectible",
    7: "new_fba",
    10: "buy_box",
    11: "used_like_new",
    16: "buy_box_used",
    17: "new_offer_count",
    18: "used_offer_count"
}

# Domain IDs
DOMAINS = {
    "US": 1,
    "UK": 2,
    "DE": 3,
    "FR": 4,
    "JP": 5,
    "CA": 6,
    "IT": 8,
    "ES": 9,
    "IN": 10,
    "MX": 11,
}


class KeepaError(Exception):
    """Custom exception for Keepa API errors."""
    pass


class KeepaClient:
    """
    Keepa API client for fetching price history and product data.
    """
    
    def __init__(self):
        self.api_key = settings.KEEPA_API_KEY
        if not self.api_key:
            logger.warning("KEEPA_API_KEY not configured")
    
    # ==========================================
    # MAIN API METHODS
    # ==========================================
    
    async def get_product(
        self,
        asin: str,
        domain: int = 1,  # 1 = US
        history: bool = True,
        days: int = 90,
        offers: int = 0,
        stats: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        Get product data and price history from Keepa.
        """
        
        if not self.api_key:
            raise KeepaError("Keepa API key not configured")
        
        # Check cache first
        cached = await self._get_cached(asin)
        if cached:
            logger.debug(f"Returning cached Keepa data for {asin}")
            return cached
        
        # Build request
        params = {
            "key": self.api_key,
            "domain": domain,
            "asin": asin,
            "history": 1 if history else 0,
            "days": days,
            "offers": offers,
            "stats": stats,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{KEEPA_API_URL}/product",
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Keepa API error: {response.status_code} - {response.text}")
                    raise KeepaError(f"Keepa API error: {response.status_code}")
                
                data = response.json()
                
                # Check for errors
                if "error" in data:
                    raise KeepaError(data["error"].get("message", "Unknown error"))
                
                # Track token usage
                tokens_used = data.get("tokensConsumed", 1)
                await self._track_usage(tokens_used)
                
                # Parse products
                products = data.get("products", [])
                if not products:
                    return None
                
                # Parse the first product
                parsed = await self._parse_product(products[0], days)
                
                # Cache the result
                await self._cache_product(asin, parsed)
                
                return parsed
                
        except httpx.TimeoutException:
            raise KeepaError("Keepa API timeout")
        except Exception as e:
            logger.error(f"Keepa API error for {asin}: {e}")
            raise KeepaError(str(e))
    
    async def get_products_batch(
        self,
        asins: List[str],
        domain: int = 1,
        history: bool = True,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get data for multiple ASINs in one request.
        Keepa supports up to 100 ASINs per request.
        """
        
        if not self.api_key:
            raise KeepaError("Keepa API key not configured")
        
        if len(asins) > 100:
            raise KeepaError("Maximum 100 ASINs per batch request")
        
        # Check cache for each ASIN
        results = []
        uncached_asins = []
        
        for asin in asins:
            cached = await self._get_cached(asin)
            if cached:
                results.append(cached)
            else:
                uncached_asins.append(asin)
        
        # Fetch uncached ASINs
        if uncached_asins:
            params = {
                "key": self.api_key,
                "domain": domain,
                "asin": ",".join(uncached_asins),
                "history": 1 if history else 0,
                "days": days,
                "stats": 90,
            }
            
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.get(
                        f"{KEEPA_API_URL}/product",
                        params=params
                    )
                    
                    if response.status_code != 200:
                        raise KeepaError(f"Keepa API error: {response.status_code}")
                    
                    data = response.json()
                    
                    # Track usage
                    tokens_used = data.get("tokensConsumed", len(uncached_asins))
                    await self._track_usage(tokens_used)
                    
                    # Parse and cache each product
                    for product in data.get("products", []):
                        parsed = await self._parse_product(product, days)
                        await self._cache_product(parsed["asin"], parsed)
                        results.append(parsed)
                        
            except Exception as e:
                logger.error(f"Keepa batch error: {e}")
                raise KeepaError(str(e))
        
        return results
    
    async def get_token_status(self) -> Dict[str, Any]:
        """Get current API token balance."""
        
        if not self.api_key:
            return {"error": "API key not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{KEEPA_API_URL}/token",
                    params={"key": self.api_key}
                )
                
                data = response.json()
                
                return {
                    "tokens_left": data.get("tokensLeft", 0),
                    "refill_in": data.get("refillIn", 0),  # milliseconds
                    "refill_rate": data.get("refillRate", 0),  # tokens per minute
                }
        except Exception as e:
            return {"error": str(e)}
    
    # ==========================================
    # PARSING METHODS
    # ==========================================
    
    async def _parse_product(
        self,
        product: Dict[str, Any],
        days: int = 90
    ) -> Dict[str, Any]:
        """Parse Keepa product response into usable format."""
        
        asin = product.get("asin", "")
        
        # Parse CSV price arrays
        csv = product.get("csv", [])
        
        # Current prices (last value in each array)
        current = {
            "amazon_price": self._get_current_price(csv, 0),
            "new_price": self._get_current_price(csv, 1),
            "used_price": self._get_current_price(csv, 2),
            "sales_rank": self._get_current_value(csv, 3),
            "new_fba_price": self._get_current_price(csv, 7),
            "buy_box_price": self._get_current_price(csv, 10),
            "offer_count_new": self._get_current_value(csv, 17),
            "offer_count_used": self._get_current_value(csv, 18),
        }
        
        # Statistics
        stats = product.get("stats", {})
        
        # Parse averages
        avg = stats.get("avg", [[-1] * 4] * 20) or [[-1] * 4] * 20
        avg90 = stats.get("avg90", [[-1] * 4] * 20) or [[-1] * 4] * 20
        
        averages = {
            "avg_30": {
                "amazon": self._parse_stat_price(avg, 0),
                "new": self._parse_stat_price(avg, 1),
                "buy_box": self._parse_stat_price(avg, 10),
                "rank": self._parse_stat_value(avg, 3),
            },
            "avg_90": {
                "amazon": self._parse_stat_price(avg90, 0),
                "new": self._parse_stat_price(avg90, 1),
                "buy_box": self._parse_stat_price(avg90, 10),
                "rank": self._parse_stat_value(avg90, 3),
            }
        }
        
        # Sales rank drops (estimate of sales)
        drops = {
            "drops_30": stats.get("salesRankDrops30", 0),
            "drops_90": stats.get("salesRankDrops90", 0),
            "drops_180": stats.get("salesRankDrops180", 0),
        }
        
        # Out of stock percentage
        oos = {
            "oos_30": stats.get("outOfStockPercentage30", 0),
            "oos_90": stats.get("outOfStockPercentage90", 0),
        }
        
        # Parse price history for charts
        price_history = self._parse_history(csv, [0, 1, 7, 10], days)
        rank_history = self._parse_history(csv, [3], days)
        
        # Product info
        info = {
            "asin": asin,
            "title": product.get("title", ""),
            "brand": product.get("brand", ""),
            "product_group": product.get("productGroup", ""),
            "category_tree": product.get("categoryTree", []),
            "image_url": self._get_image_url(product),
            "rating": (product.get("rating", 0) or 0) / 10,  # Keepa stores as int * 10
            "review_count": product.get("reviewCount", 0),
            "sales_rank_category": product.get("categoryName", ""),
        }
        
        return {
            **info,
            "current": current,
            "averages": averages,
            "drops": drops,
            "oos": oos,
            "price_history": price_history,
            "rank_history": rank_history,
            "raw_stats": stats,
        }
    
    def _get_current_price(self, csv: List, index: int) -> Optional[float]:
        """Get current price from CSV array (converts cents to dollars)."""
        
        if not csv or index >= len(csv) or not csv[index]:
            return None
        
        arr = csv[index]
        if not arr or len(arr) < 2:
            return None
        
        # Last value (skip timestamp)
        value = arr[-1]
        if value < 0:  # -1 means out of stock/unavailable
            return None
        
        return value / 100  # Convert cents to dollars
    
    def _get_current_value(self, csv: List, index: int) -> Optional[int]:
        """Get current value from CSV array (no conversion)."""
        
        if not csv or index >= len(csv) or not csv[index]:
            return None
        
        arr = csv[index]
        if not arr or len(arr) < 2:
            return None
        
        value = arr[-1]
        if value < 0:
            return None
        
        return value
    
    def _parse_stat_price(self, stats: List, index: int) -> Optional[float]:
        """Parse price from stats array."""
        
        try:
            if not stats or index >= len(stats):
                return None
            
            value = stats[index]
            if isinstance(value, list):
                value = value[0] if value else -1
            
            if value < 0:
                return None
            
            return value / 100
        except:
            return None
    
    def _parse_stat_value(self, stats: List, index: int) -> Optional[int]:
        """Parse integer value from stats array."""
        
        try:
            if not stats or index >= len(stats):
                return None
            
            value = stats[index]
            if isinstance(value, list):
                value = value[0] if value else -1
            
            if value < 0:
                return None
            
            return value
        except:
            return None
    
    def _parse_history(
        self,
        csv: List,
        indices: List[int],
        days: int
    ) -> Dict[str, List[Dict]]:
        """
        Parse price/rank history from CSV arrays into chart-friendly format.
        """
        
        history = {}
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        type_names = {
            0: "amazon",
            1: "new",
            7: "new_fba",
            10: "buy_box",
            3: "sales_rank",
        }
        
        for idx in indices:
            if not csv or idx >= len(csv) or not csv[idx]:
                continue
            
            arr = csv[idx]
            type_name = type_names.get(idx, f"type_{idx}")
            points = []
            
            # CSV format: [time1, value1, time2, value2, ...]
            for i in range(0, len(arr) - 1, 2):
                keepa_time = arr[i]
                value = arr[i + 1]
                
                # Convert Keepa time to datetime
                dt = self._keepa_time_to_datetime(keepa_time)
                
                # Skip if before cutoff
                if dt < cutoff:
                    continue
                
                # Skip invalid values
                if value < 0:
                    continue
                
                # Convert price to dollars if not rank
                if idx != 3:  # Not sales rank
                    value = value / 100
                
                points.append({
                    "timestamp": dt.isoformat(),
                    "value": value
                })
            
            history[type_name] = points
        
        return history
    
    def _keepa_time_to_datetime(self, keepa_minutes: int) -> datetime:
        """Convert Keepa time (minutes since 2011-01-01) to datetime."""
        return KEEPA_EPOCH + timedelta(minutes=keepa_minutes)
    
    def _get_image_url(self, product: Dict) -> Optional[str]:
        """Get product image URL."""
        
        images = product.get("imagesCSV", "")
        if images:
            first_image = images.split(",")[0]
            return f"https://images-na.ssl-images-amazon.com/images/I/{first_image}"
        return None
    
    # ==========================================
    # CACHING
    # ==========================================
    
    async def _get_cached(self, asin: str) -> Optional[Dict[str, Any]]:
        """Get cached Keepa data if still valid."""
        
        result = supabase.table("keepa_cache")\
            .select("*")\
            .eq("asin", asin)\
            .gt("expires_at", datetime.utcnow().isoformat())\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return None
        
        data = result.data[0]
        
        # Reconstruct the parsed format from cache
        return {
            "asin": data["asin"],
            "title": data.get("title"),
            "brand": data.get("brand"),
            "product_group": data.get("product_group"),
            "category_tree": data.get("category_tree"),
            "image_url": data.get("image_url"),
            "rating": float(data["rating"]) if data.get("rating") else None,
            "review_count": data.get("review_count"),
            "sales_rank_category": data.get("sales_rank_category"),
            "current": {
                "amazon_price": data["amazon_price"] / 100 if data.get("amazon_price") else None,
                "new_price": data["new_price"] / 100 if data.get("new_price") else None,
                "new_fba_price": data["new_fba_price"] / 100 if data.get("new_fba_price") else None,
                "buy_box_price": data["buy_box_price"] / 100 if data.get("buy_box_price") else None,
                "sales_rank": data.get("sales_rank"),
                "offer_count_new": data.get("offer_count_new"),
            },
            "averages": {
                "avg_30": {
                    "amazon": data["avg_amazon_30"] / 100 if data.get("avg_amazon_30") else None,
                    "new": data["avg_new_30"] / 100 if data.get("avg_new_30") else None,
                    "buy_box": data["avg_buy_box_30"] / 100 if data.get("avg_buy_box_30") else None,
                    "rank": data.get("avg_rank_30"),
                },
                "avg_90": {
                    "amazon": data["avg_amazon_90"] / 100 if data.get("avg_amazon_90") else None,
                    "new": data["avg_new_90"] / 100 if data.get("avg_new_90") else None,
                    "buy_box": data["avg_buy_box_90"] / 100 if data.get("avg_buy_box_90") else None,
                    "rank": data.get("avg_rank_90"),
                },
            },
            "drops": {
                "drops_30": data.get("drops_30"),
                "drops_90": data.get("drops_90"),
                "drops_180": data.get("drops_180"),
            },
            "oos": {
                "oos_30": data.get("oos_percentage_30"),
                "oos_90": data.get("oos_percentage_90"),
            },
            "price_history": data.get("price_history", {}),
            "rank_history": data.get("rank_history", {}),
            "cached": True,
            "cached_at": data["fetched_at"],
        }
    
    async def _cache_product(self, asin: str, data: Dict[str, Any]):
        """Cache parsed Keepa data."""
        
        current = data.get("current", {})
        avg_30 = data.get("averages", {}).get("avg_30", {})
        avg_90 = data.get("averages", {}).get("avg_90", {})
        drops = data.get("drops", {})
        oos = data.get("oos", {})
        
        cache_data = {
            "asin": asin,
            "title": data.get("title"),
            "brand": data.get("brand"),
            "product_group": data.get("product_group"),
            "category_tree": data.get("category_tree"),
            "image_url": data.get("image_url"),
            "sales_rank_category": data.get("sales_rank_category"),
            "rating": data.get("rating"),
            "review_count": data.get("review_count"),
            
            # Current prices (stored as cents)
            "amazon_price": int(current.get("amazon_price", 0) * 100) if current.get("amazon_price") else None,
            "new_price": int(current.get("new_price", 0) * 100) if current.get("new_price") else None,
            "new_fba_price": int(current.get("new_fba_price", 0) * 100) if current.get("new_fba_price") else None,
            "buy_box_price": int(current.get("buy_box_price", 0) * 100) if current.get("buy_box_price") else None,
            "sales_rank": current.get("sales_rank"),
            "offer_count_new": current.get("offer_count_new"),
            
            # 30-day averages
            "avg_amazon_30": int(avg_30.get("amazon", 0) * 100) if avg_30.get("amazon") else None,
            "avg_new_30": int(avg_30.get("new", 0) * 100) if avg_30.get("new") else None,
            "avg_buy_box_30": int(avg_30.get("buy_box", 0) * 100) if avg_30.get("buy_box") else None,
            "avg_rank_30": avg_30.get("rank"),
            
            # 90-day averages
            "avg_amazon_90": int(avg_90.get("amazon", 0) * 100) if avg_90.get("amazon") else None,
            "avg_new_90": int(avg_90.get("new", 0) * 100) if avg_90.get("new") else None,
            "avg_buy_box_90": int(avg_90.get("buy_box", 0) * 100) if avg_90.get("buy_box") else None,
            "avg_rank_90": avg_90.get("rank"),
            
            # Drops
            "drops_30": drops.get("drops_30"),
            "drops_90": drops.get("drops_90"),
            "drops_180": drops.get("drops_180"),
            
            # OOS
            "oos_percentage_30": oos.get("oos_30"),
            "oos_percentage_90": oos.get("oos_90"),
            
            # History JSON
            "price_history": data.get("price_history"),
            "rank_history": data.get("rank_history"),
            
            # Cache expiry
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        supabase.table("keepa_cache")\
            .upsert(cache_data, on_conflict="asin,marketplace_id")\
            .execute()
    
    async def _track_usage(self, tokens: int):
        """Track API token usage."""
        
        try:
            supabase.rpc("track_keepa_usage", {"p_tokens": tokens}).execute()
        except:
            pass  # Don't fail if tracking fails


# Singleton instance
keepa_client = KeepaClient()

