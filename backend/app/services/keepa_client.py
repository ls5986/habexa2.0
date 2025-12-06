"""
Keepa API Client - Direct REST API
Matches working curl: curl "https://api.keepa.com/product?key=KEY&domain=1&asin=ASIN&stats=90&offers=20"
"""
import os
import httpx
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

KEEPA_API_URL = "https://api.keepa.com/product"

# Price indices - prices in CENTS, divide by 100
# Negative values: -1=no data, -2=out of stock, -3=too old, -4=never tracked
PRICE_INDEX = {
    "amazon": 0, "new": 1, "used": 2, "sales_rank": 3, "list_price": 4,
    "collectible": 5, "refurbished": 6, "new_fba": 10, "lightning_deal": 11,
    "warehouse": 12, "new_fbm": 13, "buy_box": 18,
}

DOMAINS = {"US": 1, "UK": 2, "DE": 3, "FR": 4, "JP": 5, "CA": 6}


class KeepaClient:
    def __init__(self):
        self.api_key = os.getenv("KEEPA_API_KEY")
        if self.api_key:
            logger.info(f"✅ Keepa configured (key length: {len(self.api_key)})")
        else:
            logger.warning("⚠️ KEEPA_API_KEY not set")
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def get_product(self, asin: str, days: int = 90, domain: str = "US") -> Optional[Dict]:
        """Fetch product from Keepa REST API."""
        if not self.is_configured():
            return None
        
        try:
            params = {
                "key": self.api_key,
                "domain": DOMAINS.get(domain, 1),
                "asin": asin,
                "stats": days,
                "offers": 20,
            }
            
            logger.info(f"🔍 Keepa API: {asin}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(KEEPA_API_URL, params=params)
                
                if resp.status_code == 403:
                    logger.error("❌ Keepa: Invalid API key")
                    return None
                if resp.status_code == 429:
                    logger.error("❌ Keepa: Rate limited")
                    return None
                if resp.status_code != 200:
                    logger.error(f"❌ Keepa: {resp.status_code}")
                    return None
                
                data = resp.json()
                logger.info(f"🎟️ Tokens left: {data.get('tokensLeft', '?')}")
                
                products = data.get("products", [])
                if not products:
                    logger.warning(f"⚠️ No Keepa data for {asin}")
                    return None
                
                return self._parse_product(products[0], asin, days)
                
        except Exception as e:
            logger.error(f"❌ Keepa error: {e}")
            return None
    
    async def get_products_batch(self, asins: List[str], days: int = 90) -> Dict[str, Any]:
        """Fetch multiple ASINs (max 100)."""
        if not self.is_configured() or not asins:
            return {}
        
        try:
            params = {
                "key": self.api_key,
                "domain": 1,
                "asin": ",".join(asins[:100]),
                "stats": days,
                "offers": 20,
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(KEEPA_API_URL, params=params)
                if resp.status_code != 200:
                    return {}
                
                data = resp.json()
                result = {}
                for p in data.get("products", []):
                    if p and p.get("asin"):
                        result[p["asin"]] = self._parse_product(p, p["asin"], days)
                return result
        except:
            return {}
    
    def _parse_product(self, p: dict, asin: str, days: int) -> Dict[str, Any]:
        """Parse Keepa product - ALL fields."""
        logger.info(f"🔧 Starting parse for {asin}")
        logger.info(f"🔧 Product keys: {list(p.keys())[:10]}")
        
        try:
            stats = p.get("stats") or {}
            logger.info(f"🔧 Stats keys: {list(stats.keys())[:10]}")
            
            current = stats.get("current") or []
            logger.info(f"🔧 Current array length: {len(current)}")
            logger.info(f"🔧 Current first 5: {current[:5] if current else 'empty'}")
            
            avg90 = stats.get("avg90") or stats.get("avg") or []
            avg30 = stats.get("avg30") or []
            min_v = stats.get("min") or []
            max_v = stats.get("max") or []
            
            # Current prices (cents -> dollars)
            cur_amazon = self._price(current, 0)
            cur_new = self._price(current, 1)
            cur_used = self._price(current, 2)
            cur_bsr = self._rank(current, 3)
            cur_fba = self._price(current, 10)
            cur_fbm = self._price(current, 13)
            cur_buybox = self._price(current, 18)
            
            # Averages
            avg_amazon = self._price(avg90, 0)
            avg_new = self._price(avg90, 1)
            avg_bsr = self._rank(avg90, 3)
            avg_buybox = self._price(avg90, 18)
            
            # Min/Max
            min_price = self._price(min_v, 0) or self._price(min_v, 1)
            max_price = self._price(max_v, 0) or self._price(max_v, 1)
            min_bsr = self._rank(min_v, 3)
            max_bsr = self._rank(max_v, 3)
            
            # Sellers & Drops
            fba = stats.get("offerCountFBA") or 0
            fbm = stats.get("offerCountFBM") or 0
            drops30 = stats.get("salesRankDrops30") or 0
            drops90 = stats.get("salesRankDrops90") or 0
            drops180 = stats.get("salesRankDrops180") or 0
            
            # Category
            cats = p.get("categoryTree") or []
            root_cat = cats[0].get("name") if cats else None
            
            # History for charts
            price_hist = self._history(p, 0, days) or self._history(p, 1, days) or self._history(p, 18, days)
            rank_hist = self._history(p, 3, days)
            
            # Images
            imgs = p.get("imagesCSV") or ""
            images = [f"https://images-na.ssl-images-amazon.com/images/I/{i}" for i in imgs.split(",") if i]
            
            # Offers
            offers = self._parse_offers(p.get("offers") or [])
            
            return {
                "asin": asin,
                "title": p.get("title"),
                "brand": p.get("brand"),
                "manufacturer": p.get("manufacturer"),
                "productGroup": p.get("productGroup"),
                "parentAsin": p.get("parentAsin"),
                "rootCategory": root_cat,
                "categoryTree": cats,
                "images": images,
                "hazmat": p.get("hazardousMaterials"),
                
                "current": {
                    "amazon_price": cur_amazon,
                    "new_price": cur_new,
                    "used_price": cur_used,
                    "fba_price": cur_fba,
                    "fbm_price": cur_fbm,
                    "buy_box_price": cur_buybox,
                    "sales_rank": cur_bsr,
                    "fba_sellers": fba,
                    "fbm_sellers": fbm,
                    "total_sellers": fba + fbm,
                },
                
                "stats": {
                    "avg_price": avg_amazon or avg_new or avg_buybox,
                    "avg_rank": avg_bsr,
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_rank": min_bsr,
                    "max_rank": max_bsr,
                    "drops_30": drops30,
                    "drops_90": drops90,
                    "drops_180": drops180,
                    "fba_sellers": fba,
                    "fbm_sellers": fbm,
                },
                
                "averages": {
                    "avg_price_90": avg_amazon or avg_new,
                    "avg_rank_90": avg_bsr,
                    "drops_90": drops90,
                },
                
                "price_history": price_hist,
                "rank_history": rank_hist,
                "offers": offers,
                "offerCount": len(offers),
            }
        except Exception as e:
            logger.error(f"Parse error {asin}: {e}")
            return {"asin": asin, "error": str(e)}
    
    def _price(self, arr, idx) -> Optional[float]:
        try:
            if arr and len(arr) > idx and arr[idx] is not None and arr[idx] >= 0:
                return arr[idx] / 100.0
        except:
            pass
        return None
    
    def _rank(self, arr, idx) -> Optional[int]:
        try:
            if arr and len(arr) > idx and arr[idx] is not None and arr[idx] >= 0:
                return int(arr[idx])
        except:
            pass
        return None
    
    def _parse_offers(self, offers) -> List[Dict]:
        result = []
        for o in (offers or [])[:20]:
            try:
                stock = None
                csv = o.get("stockCSV") or []
                if len(csv) >= 2 and csv[-1] >= 0:
                    stock = csv[-1]
                
                result.append({
                    "seller_id": o.get("sellerId"),
                    "seller_name": o.get("sellerName"),
                    "is_amazon": o.get("isAmazon", False),
                    "is_fba": o.get("isFBA", False),
                    "is_prime": o.get("isPrime", False),
                    "condition": o.get("condition", 1),
                    "stock": stock,
                })
            except:
                pass
        return result
    
    def _history(self, p, idx, days) -> List[Dict]:
        history = []
        try:
            csv = p.get("csv")
            if not csv or len(csv) <= idx or not csv[idx]:
                return history
            
            data = csv[idx]
            epoch = datetime(2011, 1, 1)
            cutoff = datetime.utcnow() - timedelta(days=days)
            div = 100.0 if idx != 3 else 1
            
            i = 0
            while i < len(data) - 1:
                ts, val = data[i], data[i+1]
                i += 2
                if ts is None or val is None or val < 0:
                    continue
                dt = epoch + timedelta(minutes=int(ts))
                if dt < cutoff:
                    continue
                history.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "timestamp": int(dt.timestamp() * 1000),
                    "value": val / div if div != 1 else val
                })
            history.sort(key=lambda x: x["timestamp"])
        except:
            pass
        return history
    
    async def get_tokens_left(self) -> Dict:
        if not self.is_configured():
            return {"configured": False}
        try:
            params = {"key": self.api_key, "domain": 1, "asin": "B000000000", "stats": 0}
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(KEEPA_API_URL, params=params)
                d = r.json()
                return {"configured": True, "tokens_left": d.get("tokensLeft", 0)}
        except Exception as e:
            return {"configured": True, "error": str(e)}


_client = None
def get_keepa_client() -> KeepaClient:
    global _client
    if _client is None:
        _client = KeepaClient()
    return _client

# Singleton instance for backward compatibility
keepa_client = get_keepa_client()
