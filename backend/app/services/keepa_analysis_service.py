"""
Keepa Analysis Service for TOP PRODUCTS stage.
Runs detailed Keepa API analysis when products reach TOP PRODUCTS stage.
"""
import asyncio
import httpx
import logging
import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")
KEEPA_API_URL = "https://api.keepa.com"

# Keepa epoch: January 1, 2011
KEEPA_EPOCH = datetime(2011, 1, 1)


class KeepaAnalysisService:
    """
    Service for detailed Keepa analysis when products reach TOP PRODUCTS stage.
    Makes two API calls:
    1. Basic product data with history
    2. Seller offers data for FBA/FBM breakdown
    """
    
    def __init__(self):
        self.api_key = KEEPA_API_KEY
        self.base_url = KEEPA_API_URL
    
    async def analyze_product(self, asin: str, domain: int = 1) -> Dict[str, Any]:
        """
        Run full Keepa analysis for a product.
        Returns both raw API responses and parsed metrics.
        """
        if not self.api_key:
            raise ValueError("KEEPA_API_KEY not set")
        
        logger.info(f"🔍 Starting Keepa analysis for {asin}")
        
        # Make both API calls in parallel
        basic_task = self._get_basic_product_data(asin, domain)
        offers_task = self._get_offers_data(asin, domain)
        
        basic_response, offers_response = await asyncio.gather(
            basic_task,
            offers_task,
            return_exceptions=True
        )
        
        # Handle errors
        if isinstance(basic_response, Exception):
            logger.error(f"Basic product data error: {basic_response}")
            basic_response = {}
        if isinstance(offers_response, Exception):
            logger.error(f"Offers data error: {offers_response}")
            offers_response = {}
        
        # Parse and extract metrics
        analysis = self._parse_analysis(asin, basic_response, offers_response)
        
        # Store raw responses in database
        await self._store_raw_responses(asin, basic_response, offers_response)
        
        logger.info(f"✅ Keepa analysis complete for {asin}")
        return analysis
    
    async def _get_basic_product_data(self, asin: str, domain: int = 1) -> Dict[str, Any]:
        """API Call 1: Basic product data with history."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(
                    f"{self.base_url}/product",
                    params={
                        "key": self.api_key,
                        "domain": domain,
                        "asin": asin,
                        "history": 1,
                        "stats": 365,  # 12 months
                        "rating": 1,
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Keepa API error: {response.status_code} - {response.text[:200]}")
                    return {}
                
                data = response.json()
                
                # Check tokens
                tokens_left = data.get("tokensLeft", 0)
                logger.info(f"🎟️ Keepa tokens remaining: {tokens_left}")
                
                if tokens_left < 10:
                    logger.warning(f"⚠️ Low Keepa tokens: {tokens_left}")
                
                if "error" in data:
                    logger.error(f"Keepa error: {data['error']}")
                    return {}
                
                products = data.get("products", [])
                if products:
                    return products[0]
                return {}
                
        except Exception as e:
            logger.error(f"Keepa basic product data error: {e}")
            return {}
    
    async def _get_offers_data(self, asin: str, domain: int = 1) -> Dict[str, Any]:
        """API Call 2: Seller offers data for FBA/FBM breakdown."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(
                    f"{self.base_url}/product",
                    params={
                        "key": self.api_key,
                        "domain": domain,
                        "asin": asin,
                        "history": 1,
                        "stats": 365,
                        "offers": 20,  # Get top 20 offers
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Keepa offers API error: {response.status_code}")
                    return {}
                
                data = response.json()
                
                if "error" in data:
                    logger.error(f"Keepa offers error: {data['error']}")
                    return {}
                
                products = data.get("products", [])
                if products:
                    return products[0]
                return {}
                
        except Exception as e:
            logger.error(f"Keepa offers data error: {e}")
            return {}
    
    def _parse_analysis(self, asin: str, basic_data: Dict, offers_data: Dict) -> Dict[str, Any]:
        """Parse Keepa responses and extract metrics."""
        analysis = {
            "asin": asin,
            "raw_basic_response": basic_data,
            "raw_offers_response": offers_data,
            "lowest_fba_price_12m": None,
            "lowest_fba_date": None,
            "lowest_fba_seller": None,
            "current_fba_price": None,
            "current_fbm_price": None,
            "fba_seller_count": 0,
            "fbm_seller_count": 0,
            "current_sales_rank": None,
            "avg_sales_rank_90d": None,
            "price_range_12m": None,
            "price_volatility": None,
        }
        
        # Parse basic product data
        if basic_data:
            stats = basic_data.get("stats", {})
            current = stats.get("current", [])
            
            # Sales rank
            if len(current) > 3 and current[3] and current[3] > 0:
                analysis["current_sales_rank"] = current[3]
            
            # 90-day average sales rank
            avg_rank_90 = stats.get("avg90", [])
            if len(avg_rank_90) > 3 and avg_rank_90[3] and avg_rank_90[3] > 0:
                analysis["avg_sales_rank_90d"] = avg_rank_90[3]
        
        # Parse offers data for FBA/FBM prices and seller counts
        if offers_data:
            offers = offers_data.get("offers", [])
            
            fba_prices = []
            fbm_prices = []
            
            for offer in offers:
                is_fba = offer.get("isFBA", False)
                offer_csv = offer.get("offerCSV", [])
                
                # Parse offerCSV: [timestamp, price, shipping, timestamp, price, shipping, ...]
                # Group by 3s
                for i in range(0, len(offer_csv), 3):
                    if i + 1 < len(offer_csv):
                        price = offer_csv[i + 1]
                        # Skip -1 (out of stock) and -2 (N/A)
                        if price > 0:
                            price_dollars = price / 100.0
                            
                            if is_fba:
                                fba_prices.append(price_dollars)
                            else:
                                fbm_prices.append(price_dollars)
            
            # Current prices (most recent)
            if fba_prices:
                analysis["current_fba_price"] = min(fba_prices)
            if fbm_prices:
                analysis["current_fbm_price"] = min(fbm_prices)
            
            # Count sellers
            fba_sellers = set()
            fbm_sellers = set()
            for offer in offers:
                seller_id = offer.get("sellerId")
                if seller_id:
                    if offer.get("isFBA", False):
                        fba_sellers.add(seller_id)
                    else:
                        fbm_sellers.add(seller_id)
            
            analysis["fba_seller_count"] = len(fba_sellers)
            analysis["fbm_seller_count"] = len(fbm_sellers)
            
            # Find lowest FBA price in last 12 months
            lowest_fba = None
            lowest_fba_timestamp = None
            lowest_fba_seller = None
            
            for offer in offers:
                if not offer.get("isFBA", False):
                    continue
                
                seller_id = offer.get("sellerId")
                offer_csv = offer.get("offerCSV", [])
                
                # Parse in groups of 3: [timestamp, price, shipping]
                for i in range(0, len(offer_csv), 3):
                    if i + 1 < len(offer_csv):
                        timestamp = offer_csv[i]
                        price = offer_csv[i + 1]
                        
                        # Only consider valid prices
                        if price > 0:
                            price_dollars = price / 100.0
                            
                            # Check if within last 12 months
                            if timestamp > 0:
                                offer_date = KEEPA_EPOCH + timedelta(minutes=timestamp)
                                twelve_months_ago = datetime.utcnow() - timedelta(days=365)
                                
                                if offer_date >= twelve_months_ago:
                                    if lowest_fba is None or price_dollars < lowest_fba:
                                        lowest_fba = price_dollars
                                        lowest_fba_timestamp = timestamp
                                        lowest_fba_seller = seller_id
            
            if lowest_fba is not None:
                analysis["lowest_fba_price_12m"] = lowest_fba
                if lowest_fba_timestamp:
                    analysis["lowest_fba_date"] = (KEEPA_EPOCH + timedelta(minutes=lowest_fba_timestamp)).isoformat()
                analysis["lowest_fba_seller"] = lowest_fba_seller
            
            # Price range and volatility
            if fba_prices:
                analysis["price_range_12m"] = {
                    "min": min(fba_prices),
                    "max": max(fba_prices),
                    "range": max(fba_prices) - min(fba_prices)
                }
                
                # Simple volatility: standard deviation / mean
                if len(fba_prices) > 1:
                    mean = sum(fba_prices) / len(fba_prices)
                    variance = sum((p - mean) ** 2 for p in fba_prices) / len(fba_prices)
                    std_dev = variance ** 0.5
                    analysis["price_volatility"] = {
                        "coefficient": (std_dev / mean) * 100 if mean > 0 else 0,
                        "std_dev": std_dev,
                        "mean": mean
                    }
        
        return analysis
    
    async def _store_raw_responses(self, asin: str, basic_response: Dict, offers_response: Dict):
        """Store raw API responses in database for reference."""
        try:
            supabase.table("keepa_analysis").upsert({
                "asin": asin,
                "raw_basic_response": basic_response,
                "raw_offers_response": offers_response,
                "analyzed_at": datetime.utcnow().isoformat(),
            }, on_conflict="asin").execute()
            
            logger.info(f"💾 Stored raw Keepa responses for {asin}")
        except Exception as e:
            logger.warning(f"Failed to store raw responses: {e}")
    
    def calculate_worst_case_profit(
        self,
        lowest_fba_price: float,
        supplier_cost: float,
        fba_fees: float,
        shipping_estimate: float = 0.50
    ) -> Dict[str, Any]:
        """
        Calculate worst-case profit if price drops to historical low.
        
        Returns:
        {
            "worst_case_profit": float,
            "worst_case_margin": float,
            "still_profitable": bool,
            "revenue": float,
            "total_costs": float
        }
        """
        if not lowest_fba_price or lowest_fba_price <= 0:
            return {
                "worst_case_profit": None,
                "worst_case_margin": None,
                "still_profitable": False,
                "revenue": None,
                "total_costs": None
            }
        
        revenue = lowest_fba_price
        total_costs = supplier_cost + fba_fees + shipping_estimate
        worst_case_profit = revenue - total_costs
        worst_case_margin = (worst_case_profit / revenue) * 100 if revenue > 0 else 0
        
        return {
            "worst_case_profit": round(worst_case_profit, 2),
            "worst_case_margin": round(worst_case_margin, 2),
            "still_profitable": worst_case_profit > 0,
            "revenue": round(revenue, 2),
            "total_costs": round(total_costs, 2),
            "breakdown": {
                "revenue": round(revenue, 2),
                "supplier_cost": round(supplier_cost, 2),
                "fba_fees": round(fba_fees, 2),
                "shipping_estimate": round(shipping_estimate, 2),
            }
        }


# Singleton instance
keepa_analysis_service = KeepaAnalysisService()

