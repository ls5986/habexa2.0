import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from .asin_data_client import ASINDataClient
from .profit_calculator import calculate_profit, calculate_deal_score
from .supabase_client import supabase
from .sp_api_client import sp_api_client, SPAPIError
from .keepa_client import keepa_client, KeepaError
import logging

logger = logging.getLogger(__name__)


class ASINAnalyzer:
    """Complete ASIN analysis service."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.asin_client = ASINDataClient()
    
    async def analyze(
        self,
        asin: str,
        buy_cost: float,
        moq: int = 1,
        supplier_id: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform complete profitability analysis on an ASIN.
        """
        
        # Fetch data from multiple sources in parallel
        product_task = self.asin_client.get_product(asin)
        offers_task = self.asin_client.get_offers(asin)
        settings_task = self._get_user_settings()
        
        # SP-API tasks (use per-user credentials)
        sp_api_eligibility_task = None
        try:
            # Check eligibility using user's connected account
            sp_api_eligibility_task = sp_api_client.check_eligibility(self.user_id, asin)
        except Exception as e:
            logger.debug(f"SP-API eligibility check failed: {e}")
        
        # Keepa task
        keepa_task = None
        try:
            keepa_task = keepa_client.get_product(asin, days=90, history=False)
        except KeepaError as e:
            logger.debug(f"Keepa not configured: {e}")
        
        results = await asyncio.gather(
            product_task,
            offers_task,
            settings_task,
            sp_api_eligibility_task,
            keepa_task,
            return_exceptions=True
        )
        
        product_data = results[0] if not isinstance(results[0], Exception) else {}
        offers_data = results[1] if not isinstance(results[1], Exception) else {}
        user_settings = results[2] if not isinstance(results[2], Exception) else {}
        sp_api_eligibility = results[3] if not isinstance(results[3], Exception) else None
        keepa_data = results[4] if not isinstance(results[4], Exception) else None
        
        # Get user's cost settings
        prep_cost = user_settings.get("default_prep_cost", 0.50)
        inbound_shipping = user_settings.get("default_inbound_shipping", 0.50)
        
        # Determine sell price (use SP-API buy box if available, else ASIN Data API)
        sell_price = product_data.get("sell_price", 0) or 0
        
        # Get SP-API fees if we have a sell price (use per-user credentials)
        sp_api_fees = None
        if sell_price:
            try:
                sp_api_fees = await sp_api_client.get_fee_estimate(self.user_id, asin, sell_price)
            except Exception as e:
                logger.debug(f"SP-API fees error: {e}")
        
        # Use SP-API fees if available, otherwise estimate
        fba_fee = None
        referral_fee = None
        if sp_api_fees:
            fba_fee = sp_api_fees.get("fba_fulfillment_fee")
            referral_fee = sp_api_fees.get("referral_fee")
        
        profit_data = calculate_profit(
            buy_cost=buy_cost,
            sell_price=sell_price,
            category=product_data.get("category"),
            prep_cost=prep_cost,
            inbound_shipping=inbound_shipping,
            fba_fee=fba_fee,
            referral_fee=referral_fee
        )
        
        # Determine gating status - use SP-API if available
        gating_status_source = "estimated"
        gating_reasons = []
        
        if sp_api_eligibility:
            status = sp_api_eligibility.get("status", "UNKNOWN")
            gating_status_source = "sp_api"
            gating_reasons = sp_api_eligibility.get("reasons", [])
            
            if status == "ELIGIBLE":
                gating_status = "ungated"
            elif status == "APPROVAL_REQUIRED":
                gating_status = "approval_required"
            elif status == "NOT_ELIGIBLE":
                gating_status = "gated"
            elif status == "NOT_CONNECTED":
                gating_status = "unknown"
                gating_status_source = "not_connected"
            else:
                gating_status = "unknown"
        else:
            # Fallback to estimation
            gating_status = self._estimate_gating(product_data.get("category"))
        
        # Calculate deal score
        deal_score = calculate_deal_score(
            roi=profit_data["roi"],
            sales_rank=product_data.get("sales_rank"),
            gating_status=gating_status,
            amazon_is_seller=product_data.get("amazon_is_seller", False),
            num_fba_sellers=offers_data.get("num_fba_sellers", 0)
        )
        
        # Check if meets user thresholds
        min_roi = user_settings.get("min_roi", 20)
        min_profit = user_settings.get("min_profit", 3)
        max_rank = user_settings.get("max_rank", 100000)
        
        meets_threshold = (
            profit_data["roi"] >= min_roi and
            profit_data["net_profit"] >= min_profit and
            (product_data.get("sales_rank") or 999999) <= max_rank
        )
        
        # Build complete analysis result
        analysis = {
            "id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "message_id": message_id,
            "supplier_id": supplier_id,
            
            # Product info
            "asin": asin,
            "title": product_data.get("title"),
            "brand": product_data.get("brand"),
            "category": product_data.get("category"),
            "image_url": product_data.get("image_url"),
            
            # Pricing
            "buy_cost": buy_cost,
            "sell_price": sell_price,
            "lowest_fba_price": offers_data.get("lowest_fba_price"),
            "lowest_fbm_price": offers_data.get("lowest_fbm_price"),
            
            # Fees
            "fba_fee": profit_data["fba_fee"],
            "referral_fee": profit_data["referral_fee"],
            "prep_cost": prep_cost,
            "inbound_shipping": inbound_shipping,
            
            # Profitability
            "net_profit": profit_data["net_profit"],
            "roi": profit_data["roi"],
            "profit_margin": profit_data["margin"],
            
            # Competition
            "num_fba_sellers": offers_data.get("num_fba_sellers", 0),
            "num_fbm_sellers": offers_data.get("num_fbm_sellers", 0),
            "amazon_is_seller": product_data.get("amazon_is_seller", False),
            "buy_box_winner": product_data.get("buy_box_winner"),
            
            # Sales data
            "sales_rank": product_data.get("sales_rank"),
            "sales_rank_category": product_data.get("sales_rank_category"),
            "estimated_monthly_sales": keepa_data.get("drops", {}).get("drops_30") if keepa_data else None,
            
            # Historical (from Keepa if available)
            "avg_price_90d": keepa_data.get("averages", {}).get("avg_90", {}).get("buy_box") if keepa_data else None,
            "avg_rank_90d": keepa_data.get("averages", {}).get("avg_90", {}).get("rank") if keepa_data else None,
            "price_trend": "stable",
            
            # Assessment
            "gating_status": gating_status,
            "gating_status_source": gating_status_source,
            "gating_reasons": gating_reasons,
            "can_list": sp_api_eligibility.get("can_list") if sp_api_eligibility else None,
            "moq": moq,
            "deal_score": deal_score,
            "is_profitable": profit_data["is_profitable"],
            "meets_threshold": meets_threshold,
            "status": "analyzed",
            
            "analyzed_at": datetime.utcnow().isoformat(),
            
            # Keepa data (if available)
            "keepa_data": keepa_data if keepa_data else None,
        }
        
        # Save to database
        await self._save_analysis(analysis)
        
        # Send notification if profitable
        if meets_threshold and gating_status != "gated":
            await self._send_alert(analysis)
        
        return analysis
    
    async def analyze_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze multiple ASINs."""
        
        tasks = [
            self.analyze(
                asin=item["asin"],
                buy_cost=item["buy_cost"],
                moq=item.get("moq", 1),
                supplier_id=item.get("supplier_id")
            )
            for item in items
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def _get_user_settings(self) -> Dict[str, Any]:
        """Get user's profit settings."""
        
        result = supabase.table("user_settings").select("*").eq("user_id", self.user_id).single().execute()
        
        if result.data:
            return result.data
        return {}
    
    def _estimate_gating(self, category: Optional[str]) -> str:
        """Estimate gating status based on category."""
        
        GATED_CATEGORIES = [
            "Grocery", "Topical", "Beauty", "Health", "Watches",
            "Jewelry", "Clothing", "Shoes", "Fine Art", "Collectibles"
        ]
        
        if not category:
            return "unknown"
        
        for gated in GATED_CATEGORIES:
            if gated.lower() in category.lower():
                return "gated"
        
        return "ungated"
    
    async def _save_analysis(self, analysis: Dict[str, Any]):
        """Save analysis to database."""
        
        supabase.table("deals").upsert(analysis).execute()
    
    async def _send_alert(self, analysis: Dict[str, Any]):
        """Send notification for profitable deal."""
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "deal_id": analysis["id"],
            "type": "profitable_deal",
            "title": f"🔥 Hot Deal: {analysis['deal_score']} Score!",
            "message": f"{analysis['title'][:50] if analysis.get('title') else 'Product'}... - ROI: {analysis['roi']}%, Profit: ${analysis['net_profit']}",
            "data": {
                "asin": analysis["asin"],
                "roi": analysis["roi"],
                "profit": analysis["net_profit"]
            },
            "is_read": False
        }
        
        supabase.table("notifications").insert(notification).execute()

