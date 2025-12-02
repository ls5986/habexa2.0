import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

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
        
        # ============================================
        # STEP 1: GET SP-API DATA FIRST (PRIMARY SOURCE)
        # Uses APP CREDENTIALS - works for ALL users!
        # ============================================
        logger.info(f"🔍 Analyzing {asin} - Fetching SP-API data (app credentials)...")
        
        # Get user's marketplace preference (defaults to US)
        # Note: marketplace_id is stored in amazon_connections or user_settings (if added)
        marketplace_id = "ATVPDKIKX0DER"  # Default to US
        try:
            # Try to get from amazon_connections first
            connection_result = supabase.table("amazon_connections")\
                .select("marketplace_id")\
                .eq("user_id", self.user_id)\
                .eq("is_connected", True)\
                .limit(1)\
                .execute()
            if connection_result.data and connection_result.data[0].get("marketplace_id"):
                marketplace_id = connection_result.data[0]["marketplace_id"]
        except Exception as e:
            logger.debug(f"Could not get marketplace_id: {e}")
            pass
        
        # Fetch SP-API pricing FIRST (app credentials - no user auth needed!)
        sp_api_pricing = None
        sp_api_fees = None
        sp_api_eligibility = None
        sp_api_catalog = None
        sp_api_offers = None
        price_source = "unknown"
        sell_price = 0
        
        # Try SP-API with APP credentials (works for everyone)
        if sp_api_client.app_configured:
            try:
                # Get competitive pricing (PUBLIC DATA - app credentials)
                sp_api_pricing = await sp_api_client.get_competitive_pricing(asin, marketplace_id)
                if sp_api_pricing and sp_api_pricing.get("buy_box_price"):
                    sell_price = float(sp_api_pricing["buy_box_price"])
                    price_source = "sp_api_buy_box"
                    logger.info(f"✅ SP-API Buy Box Price: ${sell_price}")
            except Exception as e:
                logger.debug(f"SP-API pricing failed: {e}")
            
            # Get SP-API fees if we have a sell price
            if sell_price and sell_price > 0:
                try:
                    sp_api_fees = await sp_api_client.get_fee_estimate(asin, sell_price, marketplace_id)
                    if sp_api_fees:
                        logger.info(f"💰 SP-API Fees: Referral ${sp_api_fees.get('referral_fee')}, FBA ${sp_api_fees.get('fba_fulfillment_fee')}")
                except Exception as e:
                    logger.debug(f"SP-API fees error: {e}")
            
            # Get catalog info (PUBLIC DATA - app credentials)
            try:
                sp_api_catalog = await sp_api_client.get_catalog_item(asin, marketplace_id)
            except Exception as e:
                logger.debug(f"SP-API catalog failed: {e}")
            
            # Get offers data (PUBLIC DATA - app credentials)
            try:
                sp_api_offers = await sp_api_client.get_item_offers(asin, marketplace_id)
            except Exception as e:
                logger.debug(f"SP-API offers failed: {e}")
            
            # Get SP-API eligibility - SKIP if user not connected (requires seller account)
            # Note: Eligibility check requires seller connection, so we skip it during analysis
            # Users can check eligibility separately via the frontend if they're connected
            sp_api_eligibility = None
        else:
            logger.warning("SP-API app credentials not configured, skipping SP-API calls")
        
        # ============================================
        # STEP 2: DETERMINE SUCCESS (SP-API PRICE REQUIRED)
        # ============================================
        # SP-API is PRIMARY - if no price from SP-API, mark as failed
        if not sell_price or sell_price <= 0:
            logger.error(f"❌ {asin} FAILED: No SP-API price - marking as ERROR")
            # Return early with error status - no Keepa fallback for price
            return await self._build_error_response(asin, buy_cost, supplier_id, "No SP-API price available")
        
        # ============================================
        # STEP 3: GET KEEPA DATA (SUPPLEMENTAL ONLY - NOT FOR PRICE)
        # ============================================
        keepa_data = None
        try:
            keepa_data = await keepa_client.get_product(asin, days=90, history=False)
        except KeepaError as e:
            logger.debug(f"Keepa not configured or failed: {e}")
        
        # Keepa is ONLY for supplemental fields - NOT for price
        keepa_supplemental = {}
        if keepa_data:
            # ONLY supplemental fields - NOT price
            current = keepa_data.get("current", {})
            averages = keepa_data.get("averages", {})
            drops = keepa_data.get("drops", {})
            
            keepa_supplemental = {
                "sales_drops_30": drops.get("drops_30"),
                "sales_drops_90": drops.get("drops_90"),
                "sales_drops_180": drops.get("drops_180"),
                "price_history": keepa_data.get("price_history"),
                "rank_history": keepa_data.get("rank_history"),
                "buy_box_history": keepa_data.get("buy_box_history"),
                "variation_count": keepa_data.get("variation_count"),
                "buy_box_seller_id": current.get("buy_box_seller_id"),
            }
            
            logger.info(f"✅ Keepa supplemental for {asin}: drops_30={keepa_supplemental.get('sales_drops_30')}")
        
        # ============================================
        # STEP 4: GET FEES (SP-API FIRST, THEN ESTIMATE)
        # ============================================
        fba_fee = None
        referral_fee = None
        
        if sp_api_fees:
            fba_fee = sp_api_fees.get("fba_fulfillment_fee")
            referral_fee = sp_api_fees.get("referral_fee")
        
        # Extract seller counts from SP-API offers (already fetched above)
        num_fba_sellers = 0
        num_fbm_sellers = 0
        amazon_is_seller = False
        
        if sp_api_offers:
            num_fba_sellers = sp_api_offers.get("num_fba_sellers", 0)
            num_fbm_sellers = sp_api_offers.get("num_fbm_sellers", 0)
            amazon_is_seller = sp_api_offers.get("amazon_is_seller", False)
            logger.info(f"✅ SP-API Offers: {num_fba_sellers} FBA, {num_fbm_sellers} FBM sellers")
        
        # Get user settings
        user_settings = await self._get_user_settings()
        
        # Get user's cost settings
        prep_cost = user_settings.get("default_prep_cost", 0.50)
        inbound_shipping = user_settings.get("default_inbound_shipping", 0.50)
        
        # Get category from SP-API catalog or Keepa
        category = None
        if sp_api_catalog:
            category = sp_api_catalog.get("sales_rank_category")
        if not category and keepa_data:
            category = keepa_data.get("category") or keepa_data.get("product_group")
        
        profit_data = calculate_profit(
            buy_cost=buy_cost,
            sell_price=sell_price,
            category=category,
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
            # Fallback to estimation from category
            gating_status = self._estimate_gating(category)
        
        # Use SP-API sales rank if available, otherwise Keepa (supplemental only)
        final_sales_rank = None
        if sp_api_pricing:
            final_sales_rank = sp_api_pricing.get("sales_rank")
        if not final_sales_rank and sp_api_catalog:
            final_sales_rank = sp_api_catalog.get("sales_rank")
        # Keepa sales rank only as last resort for supplemental data
        if not final_sales_rank and keepa_data:
            final_sales_rank = keepa_data.get("sales_rank")
        
        # Calculate deal score
        deal_score = calculate_deal_score(
            roi=profit_data["roi"],
            sales_rank=final_sales_rank,
            gating_status=gating_status,
            amazon_is_seller=amazon_is_seller,
            num_fba_sellers=num_fba_sellers
        )
        
        # Check if meets user thresholds
        min_roi = user_settings.get("min_roi", 20)
        min_profit = user_settings.get("min_profit", 3)
        max_rank = user_settings.get("max_rank", 100000)
        
        meets_threshold = (
            profit_data["roi"] >= min_roi and
            profit_data["net_profit"] >= min_profit and
            (final_sales_rank or 999999) <= max_rank
        )
        
        # Extract Keepa supplemental data (NOT for price)
        keepa_title = None
        keepa_brand = None
        keepa_category = None
        keepa_image_url = None
        keepa_review_count = None
        keepa_rating = None
        
        if keepa_data:
            # Keepa ONLY for supplemental fields - NOT price
            keepa_title = keepa_data.get("title")
            keepa_brand = keepa_data.get("brand")
            keepa_category = keepa_data.get("category")
            keepa_image_url = keepa_data.get("image_url")
            keepa_review_count = keepa_data.get("review_count")
            keepa_rating = keepa_data.get("rating")
        
        # Final sell price is already determined (SP-API priority)
        final_sell_price = sell_price
        
        # Build complete analysis result - use Keepa data when available
        analysis = {
            "id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "message_id": message_id,
            "supplier_id": supplier_id,
            
            # Product info - prefer SP-API catalog, fallback to Keepa
            "asin": asin,
            "title": (sp_api_catalog.get("title") if sp_api_catalog else None) or keepa_title,
            "product_title": (sp_api_catalog.get("title") if sp_api_catalog else None) or keepa_title,  # For column
            "brand": (sp_api_catalog.get("brand") if sp_api_catalog else None) or keepa_brand,
            "category": (sp_api_catalog.get("sales_rank_category") if sp_api_catalog else None) or keepa_category,
            "image_url": (sp_api_catalog.get("image_url") if sp_api_catalog else None) or keepa_image_url,
            
            # Pricing
            "buy_cost": buy_cost,
            "sell_price": final_sell_price,
            "lowest_fba_price": sp_api_offers.get("lowest_fba_price") if sp_api_offers else None,
            "lowest_fbm_price": sp_api_offers.get("lowest_fbm_price") if sp_api_offers else None,
            
            # Fees
            "fba_fee": profit_data["fba_fee"],
            "referral_fee": profit_data["referral_fee"],
            "total_fees": profit_data.get("total_fees") or (profit_data["fba_fee"] + profit_data["referral_fee"]),
            "prep_cost": prep_cost,
            "inbound_shipping": inbound_shipping,
            
            # Profitability
            "net_profit": profit_data["net_profit"],
            "profit": profit_data["net_profit"],  # For column
            "roi": profit_data["roi"],
            "margin": profit_data["margin"],
            "profit_margin": profit_data["margin"],
            
            # Competition (from SP-API offers if available)
            "num_fba_sellers": num_fba_sellers,
            "num_fbm_sellers": num_fbm_sellers,
            "amazon_is_seller": amazon_is_seller,
            "buy_box_winner": None,  # Can be extracted from SP-API if needed
            
            # SP-API specific data
            "price_source": price_source,
            "seller_count": num_fba_sellers + num_fbm_sellers,
            "fba_seller_count": num_fba_sellers,
            "amazon_sells": amazon_is_seller,
            
            # Sales data - SP-API primary, Keepa supplemental
            "sales_rank": final_sales_rank,
            "sales_rank_category": (sp_api_catalog.get("sales_rank_category") if sp_api_catalog else None) or (keepa_category if keepa_data else None),
            "review_count": keepa_review_count,  # Keepa only
            "rating": keepa_rating,  # Keepa only
            
            # Keepa supplemental fields (sales drops, historical)
            "drops_30": keepa_supplemental.get("sales_drops_30"),
            "drops_90": keepa_supplemental.get("sales_drops_90"),
            "drops_180": keepa_supplemental.get("sales_drops_180"),
            "estimated_monthly_sales": keepa_supplemental.get("sales_drops_30"),
            "variation_count": keepa_supplemental.get("variation_count"),
            "buy_box_seller_id": keepa_supplemental.get("buy_box_seller_id"),
            
            # Historical (from Keepa if available)
            "price_history": keepa_supplemental.get("price_history"),
            "rank_history": keepa_supplemental.get("rank_history"),
            "buy_box_history": keepa_supplemental.get("buy_box_history"),
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
            "status": "complete",  # Use "complete" for column
            
            # Success indicator (SP-API price was found)
            "success": True,
            "price_source": price_source,
            
            "analyzed_at": datetime.utcnow().isoformat(),
            
            # Keepa data (if available) - keep for reference
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
        
        try:
            result = supabase.table("user_settings")\
                .select("*")\
                .eq("user_id", self.user_id)\
                .maybe_single()\
                .execute()
            
            if result.data:
                return result.data
            return {}
        except Exception as e:
            logger.debug(f"Could not fetch user settings: {e}")
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
    
    async def _build_error_response(self, asin: str, buy_cost: float, supplier_id: Optional[str], error_message: str) -> Dict[str, Any]:
        """Build error response when SP-API fails to get price."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "supplier_id": supplier_id,
            "asin": asin,
            "buy_cost": buy_cost,
            "sell_price": None,
            "fees_total": None,
            "title": None,
            "brand": None,
            "image_url": None,
            "bsr": None,
            "seller_count": None,
            "fba_seller_count": None,
            "amazon_sells": False,
            "sales_drops_30": None,
            "sales_drops_90": None,
            "sales_drops_180": None,
            "price_source": "error",
            "status": "error",
            "error_message": error_message,
            "success": False,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _to_scalar(self, val):
        """Convert arrays to single scalar values. Ensure we only save scalars to DB columns."""
        if val is None:
            return None
        # If it's an array, get first non-negative value
        if isinstance(val, list):
            for v in val:
                if v is not None and (not isinstance(v, (int, float)) or v >= 0):
                    return v
            return None
        # If it's a dict, return None (should be stored in JSONB only)
        if isinstance(val, dict):
            return None
        # If negative, treat as no data
        if isinstance(val, (int, float)) and val < 0:
            return None
        return val

    async def _save_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save analysis to database. Returns saved record with ID.
        Upserts on user_id + supplier_id + asin (unique constraint).
        Ensures all values are scalars (not arrays) when saving to individual columns.
        """
        from datetime import datetime
        
        # Clean analysis data - ensure arrays are converted to scalars for any direct column saves
        # Note: We store the full analysis in analysis_data JSONB, but if we ever save to individual
        # columns, we need to ensure they're scalars
        clean_analysis = {}
        for k, v in analysis.items():
            # Keep arrays/dicts in JSONB, but ensure any direct column values are scalars
            if k in ["gating_reasons"] and isinstance(v, list):
                # gating_reasons can be an array - that's fine for JSONB
                clean_analysis[k] = v
            elif isinstance(v, (dict, list)):
                # Complex types go in JSONB only
                clean_analysis[k] = v
            else:
                # Scalar values
                clean_analysis[k] = self._to_scalar(v)
        
        # Build analysis record - save to both columns AND JSONB for compatibility
        analysis_record = {
            "user_id": self.user_id,
            "supplier_id": analysis.get("supplier_id"),  # Can be None
            "asin": analysis.get("asin"),
            "deal_id": analysis.get("deal_id"),  # Can be None for telegram deals
            # Save to individual columns (for fast queries)
            "product_title": analysis.get("product_title") or analysis.get("title"),
            "brand": analysis.get("brand"),
            "category": analysis.get("category"),
            "image_url": analysis.get("image_url"),
            "buy_cost": self._to_scalar(analysis.get("buy_cost")),
            "sell_price": self._to_scalar(analysis.get("sell_price")),
            "profit": self._to_scalar(analysis.get("profit") or analysis.get("net_profit")),
            "roi": self._to_scalar(analysis.get("roi")),
            "margin": self._to_scalar(analysis.get("margin") or analysis.get("profit_margin")),
            "referral_fee": self._to_scalar(analysis.get("referral_fee")),
            "fba_fee": self._to_scalar(analysis.get("fba_fee")),
            "total_fees": self._to_scalar(analysis.get("total_fees")),
            "sales_rank": self._to_scalar(analysis.get("sales_rank")),
            "gating_status": analysis.get("gating_status"),
            "gating_reasons": analysis.get("gating_reasons") if isinstance(analysis.get("gating_reasons"), list) else None,
            "review_count": self._to_scalar(analysis.get("review_count")),
            "rating": self._to_scalar(analysis.get("rating")),
            "drops_30": self._to_scalar(analysis.get("drops_30")),
            "drops_90": self._to_scalar(analysis.get("drops_90")),
            "status": analysis.get("status", "complete"),
            # Also keep full analysis in JSONB for backward compatibility
            "analysis_data": clean_analysis,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Remove None values (but keep supplier_id even if None)
        analysis_record = {k: v for k, v in analysis_record.items() if v is not None or k == "supplier_id"}
        
        try:
            # Upsert on user_id + supplier_id + asin (the unique constraint)
            # Note: Supabase/PostgREST handles NULL in unique constraints correctly
            result = supabase.table("analyses").upsert(
                analysis_record,
                on_conflict="user_id,supplier_id,asin"
            ).execute()
            
            if result.data and len(result.data) > 0:
                # Return the saved record with ID
                saved = result.data[0]
                # Also set the ID in the analysis dict for caller
                analysis["id"] = saved["id"]
                return saved
            
            # Fallback: fetch the record we just created/updated
            fetch_query = supabase.table("analyses")\
                .select("*")\
                .eq("user_id", self.user_id)\
                .eq("asin", analysis.get("asin"))
            
            if analysis.get("supplier_id"):
                fetch_query = fetch_query.eq("supplier_id", analysis.get("supplier_id"))
            else:
                fetch_query = fetch_query.is_("supplier_id", "null")
            
            fetch_result = fetch_query\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if fetch_result.data and len(fetch_result.data) > 0:
                saved = fetch_result.data[0]
                analysis["id"] = saved["id"]
                return saved
            
            # Return record without ID if fetch fails
            return analysis_record
            
        except Exception as e:
            logger.error(f"Save analysis error: {e}")
            import traceback
            traceback.print_exc()
            # Return the record without ID - caller will handle
            return analysis_record
    
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

