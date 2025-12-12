"""Keepa client - FIXED with working batch method."""
import os
import httpx
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class KeepaError(Exception):
    """Keepa API error."""
    pass


class KeepaClient:
    def __init__(self):
        self.api_key = os.getenv("KEEPA_API_KEY")
        if self.api_key:
            logger.info(f"✅ Keepa configured (key length: {len(self.api_key)})")
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def get_product(self, asin: str, days: int = 90, domain: int = 1, history: bool = False) -> Optional[Dict]:
        """Get single product - calls batch with one ASIN.
        
        Args:
            asin: Product ASIN
            days: Number of days of history (default 90)
            domain: Keepa domain (1=US, ignored for backward compatibility)
            history: Whether to include history (ignored for backward compatibility)
        """
        results = await self.get_products_batch([asin], days)
        return results.get(asin)
    
    async def get_products_batch(self, asins: List[str], days: int = 90, domain: int = 1, history: bool = False, return_raw: bool = False) -> Dict[str, Any]:
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
                "offers": 20,  # Number of offers to return
                "history": 1,  # Include price/rank history
                "update": 0,   # Don't force update
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
                
                # If return_raw is True, return the full raw response
                if return_raw:
                    return {
                        'raw_response': data,
                        'products': products,
                        'tokens_left': data.get('tokensLeft')
                    }
                
                if not products:
                    logger.warning(f"⚠️ No products in response. Response keys: {list(data.keys())}")
                    logger.warning(f"⚠️ Full response sample: {str(data)[:500]}")
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
                    
                    # Parse price history (CSV format: [time, price, ...])
                    price_history = []
                    csv_data = p.get("csv", [])
                    if csv_data and len(csv_data) > 0:
                        # csv[0] is Amazon price history
                        # Format: [timestamp, price, ...] where price is in cents
                        amazon_price_csv = csv_data[0] if len(csv_data) > 0 else []
                        if amazon_price_csv and len(amazon_price_csv) > 1:
                            for i in range(0, len(amazon_price_csv) - 1, 2):
                                if i + 1 < len(amazon_price_csv):
                                    timestamp = amazon_price_csv[i]
                                    price = amazon_price_csv[i + 1]
                                    if price is not None and price >= 0:
                                        price_history.append({
                                            "timestamp": timestamp,
                                            "price": round(price / 100.0, 2),
                                            "date": timestamp  # Keepa timestamp is minutes since epoch
                                        })
                    
                    # Parse rank history (CSV format: [time, rank, ...])
                    rank_history = []
                    if csv_data and len(csv_data) > 3:
                        # csv[3] is sales rank history
                        sales_rank_csv = csv_data[3] if len(csv_data) > 3 else []
                        if sales_rank_csv and len(sales_rank_csv) > 1:
                            for i in range(0, len(sales_rank_csv) - 1, 2):
                                if i + 1 < len(sales_rank_csv):
                                    timestamp = sales_rank_csv[i]
                                    rank = sales_rank_csv[i + 1]
                                    if rank is not None and rank >= 0:
                                        rank_history.append({
                                            "timestamp": timestamp,
                                            "rank": rank,
                                            "date": timestamp
                                        })
                    
                    # Parse offers
                    offers = []
                    offers_data = p.get("offers", [])
                    if offers_data:
                        for offer in offers_data:
                            if offer:
                                offers.append({
                                    "seller_id": offer.get("sellerId"),
                                    "seller_name": offer.get("sellerName"),
                                    "is_amazon": offer.get("isAmazon", False),
                                    "is_fba": offer.get("isFBA", False),
                                    "is_buy_box": offer.get("isBuyBoxWinner", False),
                                    "price": round(offer.get("price", 0) / 100.0, 2) if offer.get("price") else None,
                                    "shipping": round(offer.get("shipping", 0) / 100.0, 2) if offer.get("shipping") else None,
                                    "condition": offer.get("condition"),
                                    "last_seen": offer.get("lastSeen"),
                                })
                    
                    # Parse variations
                    variations = []
                    variation_asins = p.get("variationASINs", [])
                    if variation_asins:
                        variations = variation_asins
                    
                    # Check if Amazon is seller
                    amazon_is_seller = False
                    if offers:
                        amazon_is_seller = any(offer.get("isAmazon", False) for offer in offers)
                    # Also check in stats
                    if not amazon_is_seller:
                        amazon_is_seller = stats.get("isAmazon", False) or False
                    
                    # Hazmat info
                    hazmat = p.get("isHazmat", False)
                    hazmat_reason = p.get("hazmatReason") if hazmat else None
                    
                    # Additional product info
                    product_group = p.get("productGroup")
                    category = p.get("category")
                    model = p.get("model")
                    part_number = p.get("partNumber")
                    ean_list = p.get("eanList", [])
                    upc_list = p.get("upcList", [])
                    images_csv = p.get("imagesCSV", [])
                    image_url = images_csv[0] if images_csv else None
                    
                    # Parent ASIN (if this is a variation)
                    parent_asin = p.get("parentAsin")
                    
                    # Dimensions and weight
                    package_dimensions = p.get("packageDimensions")
                    package_weight = p.get("packageWeight")
                    
                    # Review data
                    reviews_total = stats.get("reviewsTotal") or 0
                    rating = stats.get("rating") or None
                    if rating:
                        rating = round(rating / 10.0, 1)  # Keepa stores rating as 0-100, convert to 0-10
                    
                    results[asin] = {
                        "asin": asin,
                        "title": p.get("title"),
                        "brand": p.get("brand"),
                        "manufacturer": p.get("manufacturer"),
                        "model": model,
                        "part_number": part_number,
                        "product_group": product_group,
                        "category": category,
                        "image_url": image_url,
                        "ean_list": ean_list,
                        "upc_list": upc_list,
                        "parent_asin": parent_asin,
                        "is_variation": bool(parent_asin),
                        "variations": variations,
                        "hazmat": hazmat,
                        "hazmat_reason": hazmat_reason,
                        "package_dimensions": package_dimensions,
                        "package_weight": package_weight,
                        "current": {
                            "amazon_price": get_price(0),
                            "new_price": get_price(1),
                            "used_price": get_price(2),
                            "buy_box_price": get_price(18),
                            "fba_price": get_price(10),
                            "fbm_price": get_price(11),
                            "sales_rank": get_int(3),
                            "fba_sellers": stats.get("offerCountFBA") or 0,
                            "fbm_sellers": stats.get("offerCountFBM") or 0,
                            "total_sellers": (stats.get("offerCountFBA") or 0) + (stats.get("offerCountFBM") or 0),
                            "amazon_is_seller": amazon_is_seller,
                            "rating": rating,
                            "reviews_total": reviews_total,
                        },
                        "stats": {
                            "drops_30": stats.get("salesRankDrops30") or 0,
                            "drops_90": stats.get("salesRankDrops90") or 0,
                            "drops_180": stats.get("salesRankDrops180") or 0,
                            "avg_price_30": round(stats.get("avg30", 0) / 100.0, 2) if stats.get("avg30") else None,
                            "avg_price_90": round(stats.get("avg90", 0) / 100.0, 2) if stats.get("avg90") else None,
                            "avg_price_180": round(stats.get("avg180", 0) / 100.0, 2) if stats.get("avg180") else None,
                            "avg_price_365": round(stats.get("avg365", 0) / 100.0, 2) if stats.get("avg365") else None,
                            "min_price_30": round(stats.get("min30", 0) / 100.0, 2) if stats.get("min30") else None,
                            "min_price_90": round(stats.get("min90", 0) / 100.0, 2) if stats.get("min90") else None,
                            "max_price_30": round(stats.get("max30", 0) / 100.0, 2) if stats.get("max30") else None,
                            "max_price_90": round(stats.get("max90", 0) / 100.0, 2) if stats.get("max90") else None,
                        },
                        "averages": {
                            "avg_price_90": get_price(0),
                            "avg_rank_90": get_int(3),
                            "drops_90": stats.get("salesRankDrops90") or 0,
                        },
                        "price_history": price_history,
                        "rank_history": rank_history,
                        "offers": offers,
                    }
                    
                    logger.info(f"✅ Parsed {asin}: rank={results[asin]['current']['sales_rank']}")
        
        except Exception as e:
            logger.error(f"❌ Keepa batch error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return results
    
    async def get_products_raw(self, asins: List[str], days: int = 90) -> Dict:
        """Get raw Keepa product data (for deep analysis).
        
        This is a compatibility method - returns the same as get_products_batch
        but with a different name for backward compatibility.
        """
        return await self.get_products_batch(asins, days)
    
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

# Backward compatibility - export keepa_client instance
keepa_client = get_keepa_client()
