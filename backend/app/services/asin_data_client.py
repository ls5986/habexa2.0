import httpx
from typing import Dict, Any
import os
from app.core.config import settings


class ASINDataClient:
    """Client for ASIN Data API."""
    
    BASE_URL = "https://api.asindataapi.com/request"
    
    def __init__(self):
        self.api_key = settings.ASIN_DATA_API_KEY
    
    async def get_product(self, asin: str, marketplace: str = "US") -> Dict[str, Any]:
        """
        Fetch product data from ASIN Data API.
        
        Returns:
            title, brand, category, price, sales_rank, rating,
            reviews_count, image_url, buy_box_price, fba_sellers, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                params={
                    "api_key": self.api_key,
                    "type": "product",
                    "asin": asin,
                    "amazon_domain": f"amazon.com" if marketplace == "US" else f"amazon.{marketplace.lower()}",
                    "output": "json"
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"ASIN API error: {response.text}")
            
            data = response.json()
            product = data.get("product", {})
            
            return {
                "asin": asin,
                "title": product.get("title"),
                "brand": product.get("brand"),
                "category": product.get("categories", [{}])[0].get("name") if product.get("categories") else None,
                "image_url": product.get("main_image", {}).get("link"),
                "sell_price": product.get("buybox_winner", {}).get("price", {}).get("value"),
                "sales_rank": product.get("bestsellers_rank", [{}])[0].get("rank") if product.get("bestsellers_rank") else None,
                "sales_rank_category": product.get("bestsellers_rank", [{}])[0].get("category") if product.get("bestsellers_rank") else None,
                "rating": product.get("rating"),
                "reviews_count": product.get("ratings_total"),
                "buy_box_winner": product.get("buybox_winner", {}).get("seller", {}).get("name"),
                "amazon_is_seller": product.get("buybox_winner", {}).get("is_amazon", False),
                "num_sellers": len(product.get("offers", [])),
            }
    
    async def get_offers(self, asin: str) -> Dict[str, Any]:
        """Get all offers/sellers for an ASIN."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                params={
                    "api_key": self.api_key,
                    "type": "offers",
                    "asin": asin,
                    "amazon_domain": "amazon.com",
                    "output": "json"
                },
                timeout=30.0
            )
            
            data = response.json()
            offers = data.get("offers", [])
            
            fba_sellers = [o for o in offers if o.get("delivery", {}).get("fulfilled_by_amazon")]
            fbm_sellers = [o for o in offers if not o.get("delivery", {}).get("fulfilled_by_amazon")]
            
            return {
                "num_fba_sellers": len(fba_sellers),
                "num_fbm_sellers": len(fbm_sellers),
                "lowest_fba_price": min([o.get("price", {}).get("value", 9999) for o in fba_sellers]) if fba_sellers else None,
                "lowest_fbm_price": min([o.get("price", {}).get("value", 9999) for o in fbm_sellers]) if fbm_sellers else None,
            }

