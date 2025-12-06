"""Keepa client - FIXED with working batch method."""
import os
import httpx
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class KeepaClient:
    def __init__(self):
        self.api_key = os.getenv("KEEPA_API_KEY")
        if self.api_key:
            logger.info(f"✅ Keepa configured (key length: {len(self.api_key)})")
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def get_product(self, asin: str, days: int = 90) -> Optional[Dict]:
        """Get single product - calls batch with one ASIN."""
        results = await self.get_products_batch([asin], days)
        return results.get(asin)
    
    async def get_products_batch(self, asins: List[str], days: int = 90) -> Dict[str, Dict]:
        """
        Batch fetch multiple ASINs in one API call.
        Keepa allows up to 100 ASINs per request.
        """
        if not self.api_key or not asins:
            return {}
        
        results = {}
        
        try:
            # Keepa accepts comma-separated ASINs
            asin_str = ",".join(asins[:100])
            
            params = {
                "key": self.api_key,
                "domain": 1,
                "asin": asin_str,
                "stats": days,
                "offers": 20,
            }
            
            logger.info(f"🔍 Keepa batch request: {len(asins)} ASINs")
            
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get("https://api.keepa.com/product", params=params)
                
                if resp.status_code != 200:
                    logger.error(f"❌ Keepa error: {resp.status_code}")
                    return {}
                
                data = resp.json()
                products = data.get("products")
                
                # Handle None or empty list
                if products is None:
                    logger.warning(f"⚠️ Keepa returned products=None (might be null in JSON)")
                    products = []
                elif not isinstance(products, list):
                    logger.warning(f"⚠️ Keepa returned products as {type(products)}, expected list")
                    products = []
                
                logger.info(f"📦 Keepa returned {len(products)} products, tokens left: {data.get('tokensLeft')}")
                
                if not products:
                    logger.warning(f"⚠️ No products in response. Response keys: {list(data.keys())}")
                    return {}
                
                for p in products:
                    if not p:
                        continue
                    
                    asin = p.get("asin")
                    if not asin:
                        continue
                    
                    stats = p.get("stats") or {}
                    current = stats.get("current") or []
                    
                    # Safe value extraction
                    def get_price(idx):
                        if current and len(current) > idx:
                            v = current[idx]
                            if v is not None and v >= 0:
                                return round(v / 100.0, 2)
                        return None
                    
                    def get_int(idx):
                        if current and len(current) > idx:
                            v = current[idx]
                            if v is not None and v >= 0:
                                return int(v)
                        return None
                    
                    results[asin] = {
                        "asin": asin,
                        "title": p.get("title"),
                        "brand": p.get("brand"),
                        "manufacturer": p.get("manufacturer"),
                        "current": {
                            "amazon_price": get_price(0),
                            "new_price": get_price(1),
                            "used_price": get_price(2),
                            "buy_box_price": get_price(18),
                            "fba_price": get_price(10),
                            "sales_rank": get_int(3),
                            "fba_sellers": stats.get("offerCountFBA") or 0,
                            "fbm_sellers": stats.get("offerCountFBM") or 0,
                            "total_sellers": (stats.get("offerCountFBA") or 0) + (stats.get("offerCountFBM") or 0),
                        },
                        "stats": {
                            "drops_30": stats.get("salesRankDrops30") or 0,
                            "drops_90": stats.get("salesRankDrops90") or 0,
                            "drops_180": stats.get("salesRankDrops180") or 0,
                        },
                        "averages": {
                            "avg_price_90": get_price(0),
                            "avg_rank_90": get_int(3),
                            "drops_90": stats.get("salesRankDrops90") or 0,
                        },
                        "price_history": [],
                        "rank_history": [],
                        "offers": [],
                    }
                    
                    logger.info(f"✅ Parsed {asin}: rank={results[asin]['current']['sales_rank']}")
        
        except Exception as e:
            logger.error(f"❌ Keepa batch error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return results
    
    async def get_tokens_left(self) -> Dict:
        """Check remaining API tokens."""
        if not self.api_key:
            return {"configured": False, "tokens_left": 0}
        
        try:
            params = {
                "key": self.api_key,
                "domain": 1,
                "asin": "B000000000",
                "stats": 0,
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://api.keepa.com/product", params=params)
                data = resp.json()
                return {
                    "configured": True,
                    "tokens_left": data.get("tokensLeft", 0),
                }
        except Exception as e:
            return {"configured": True, "error": str(e)}


# Singleton
_client = None

def get_keepa_client() -> KeepaClient:
    global _client
    if _client is None:
        _client = KeepaClient()
    return _client
