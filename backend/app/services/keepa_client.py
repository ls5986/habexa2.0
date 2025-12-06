"""Minimal Keepa client."""
import os
import httpx
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KeepaClient:
    def __init__(self):
        self.api_key = os.getenv("KEEPA_API_KEY")
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def get_product(self, asin: str, days: int = 90) -> Optional[Dict]:
        if not self.api_key:
            return None
        
        try:
            params = {
                "key": self.api_key,
                "domain": 1,
                "asin": asin,
                "stats": days,
                "offers": 20,
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get("https://api.keepa.com/product", params=params)
                
                if resp.status_code != 200:
                    logger.error(f"Keepa error: {resp.status_code}")
                    return None
                
                data = resp.json()
                products = data.get("products", [])
                
                if not products:
                    return None
                
                p = products[0]
                stats = p.get("stats") or {}
                current = stats.get("current") or []
                
                # Safe value extraction
                def get_price(idx):
                    if current and len(current) > idx:
                        v = current[idx]
                        if v is not None and v >= 0:
                            return v / 100.0
                    return None
                
                def get_int(idx):
                    if current and len(current) > idx:
                        v = current[idx]
                        if v is not None and v >= 0:
                            return int(v)
                    return None
                
                return {
                    "asin": asin,
                    "title": p.get("title"),
                    "brand": p.get("brand"),
                    "current": {
                        "amazon_price": get_price(0),
                        "new_price": get_price(1),
                        "buy_box_price": get_price(18),
                        "sales_rank": get_int(3),
                        "fba_sellers": stats.get("offerCountFBA") or 0,
                        "fbm_sellers": stats.get("offerCountFBM") or 0,
                    },
                    "stats": {
                        "drops_30": stats.get("salesRankDrops30") or 0,
                        "drops_90": stats.get("salesRankDrops90") or 0,
                    },
                    "averages": {},
                    "price_history": [],
                    "rank_history": [],
                    "offers": [],
                }
                
        except Exception as e:
            logger.error(f"Keepa error: {e}")
            return None
    
    async def get_products_batch(self, asins: List[str], days: int = 90) -> Dict:
        return {}
    
    async def get_tokens_left(self) -> Dict:
        return {"configured": self.is_configured()}


_client = None

def get_keepa_client() -> KeepaClient:
    global _client
    if _client is None:
        _client = KeepaClient()
    return _client

# Backward compatibility
keepa_client = None
def _init():
    global keepa_client
    keepa_client = get_keepa_client()
_init()
