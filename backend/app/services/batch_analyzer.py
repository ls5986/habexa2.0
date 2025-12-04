"""
Optimized batch analyzer using SP-API for pricing/fees and Keepa for catalog data.
Implements optimal API strategy: Keepa first (100 ASINs), then SP-API (20 ASINs).
"""
import asyncio
import logging
from typing import List, Dict
from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import keepa_client

logger = logging.getLogger(__name__)

SP_API_BATCH_SIZE = 20
KEEPA_BATCH_SIZE = 100


class BatchAnalyzer:
    """
    Optimized analyzer using batch API calls.
    - Keepa: 100 ASINs per API call, batch cache lookups
    - SP-API: 20 ASINs per batch call
    """
    
    async def analyze_products(
        self,
        asins: List[str],
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Dict[str, dict]:
        """Analyze products using batch API calls."""
        if not asins:
            return {}
        
        # Deduplicate and clean
        asins = list(set(a.strip().upper() for a in asins if a))
        
        results = {asin: {"asin": asin, "success": False} for asin in asins}
        
        logger.info(f"🚀 Analyzing {len(asins)} products...")
        
        # ==========================================
        # STEP 1: KEEPA - Batch of 100
        # ==========================================
        logger.info("📚 Fetching catalog data from Keepa...")
        
        # Process all ASINs in one batch call (handles internal batching)
        keepa_data = await keepa_client.get_products_batch(asins, domain=1, history=False, days=90)
        
        for asin, data in keepa_data.items():
            if asin in results:
                results[asin].update({
                    "title": data.get("title"),
                    "brand": data.get("brand"),
                    "image_url": data.get("image_url"),
                    "bsr": data.get("bsr"),
                    "category": data.get("category"),
                    "sales_drops_30": data.get("sales_drops_30"),
                    "sales_drops_90": data.get("sales_drops_90"),
                    "sales_drops_180": data.get("sales_drops_180"),
                    "variation_count": data.get("variation_count"),
                    "amazon_in_stock": data.get("amazon_in_stock"),
                    "rating": data.get("rating"),
                    "review_count": data.get("review_count"),
                })
        
        # ==========================================
        # STEP 2: SP-API PRICING - Batch of 20
        # ==========================================
        logger.info("💰 Fetching pricing from SP-API...")
        
        sp_api_success = False
        for i in range(0, len(asins), SP_API_BATCH_SIZE):
            batch = asins[i:i + SP_API_BATCH_SIZE]
            
            try:
                pricing_data = await sp_api_client.get_competitive_pricing_batch(batch, marketplace_id)
                
                for asin, data in pricing_data.items():
                    if data.get("buy_box_price") and asin in results:
                        results[asin]["sell_price"] = data["buy_box_price"]
                        results[asin]["seller_count"] = data.get("offer_count", 0)
                        results[asin]["price_source"] = "sp-api"
                        sp_api_success = True
            except Exception as e:
                logger.warning(f"SP-API pricing batch failed for batch {i//SP_API_BATCH_SIZE + 1}: {e}")
        
        # ==========================================
        # STEP 2B: KEEPA PRICING FALLBACK - If SP-API failed
        # ==========================================
        # If SP-API didn't provide pricing, use Keepa pricing if available
        asins_without_price = [asin for asin in asins if not results[asin].get("sell_price")]
        if asins_without_price:
            logger.info(f"📚 Using Keepa pricing for {len(asins_without_price)} products (SP-API fallback)...")
            keepa_fallback_count = 0
            for asin in asins_without_price:
                if asin in keepa_data:
                    keepa_product = keepa_data[asin]
                    # Try to get current price from Keepa (already parsed in _parse_product)
                    current_price = keepa_product.get("current_price") or keepa_product.get("buy_box_price")
                    if current_price and current_price > 0:
                        results[asin]["sell_price"] = current_price
                        results[asin]["price_source"] = "keepa"
                        keepa_fallback_count += 1
                        logger.debug(f"✅ Keepa price for {asin}: ${current_price}")
            if keepa_fallback_count > 0:
                logger.info(f"✅ Keepa pricing fallback: {keepa_fallback_count} products got pricing")
        
        # ==========================================
        # STEP 3: SP-API FEES - Batch of 20
        # ==========================================
        logger.info("📊 Fetching fees from SP-API...")
        
        items_with_prices = [
            {"asin": asin, "price": results[asin]["sell_price"]}
            for asin in asins
            if results[asin].get("sell_price")
        ]
        
        for i in range(0, len(items_with_prices), SP_API_BATCH_SIZE):
            batch = items_with_prices[i:i + SP_API_BATCH_SIZE]
            
            try:
                fees_data = await sp_api_client.get_fees_estimate_batch(batch, marketplace_id)
                
                for asin, data in fees_data.items():
                    if asin in results:
                        results[asin]["fees_total"] = data.get("total")
                        results[asin]["fees_referral"] = data.get("referral_fee")
                        results[asin]["fees_fba"] = data.get("fba_fulfillment_fee")
            except Exception as e:
                logger.warning(f"SP-API fees batch failed for batch {i//SP_API_BATCH_SIZE + 1}: {e}")
        
        # ==========================================
        # STEP 4: Mark success - More lenient criteria
        # ==========================================
        for asin in asins:
            result = results[asin]
            # Mark success if we have:
            # 1. Sell price (required for profit calculation), OR
            # 2. Title + other catalog data (at least we got product info)
            has_price = bool(result.get("sell_price"))
            has_catalog_data = bool(result.get("title") or result.get("brand") or result.get("image_url"))
            
            if has_price:
                # Full success - we have pricing data
                result["success"] = True
            elif has_catalog_data:
                # Partial success - we have catalog data but no pricing
                # Still mark as success so product doesn't get stuck in error state
                # Frontend can show "Price unavailable" instead of "Pending analysis"
                result["success"] = True
                result["price_unavailable"] = True
                logger.warning(f"⚠️ {asin}: Catalog data available but no pricing")
            else:
                # Complete failure - no data at all
                result["success"] = False
                logger.error(f"❌ {asin}: No data available from any source")
        
        success_count = sum(1 for r in results.values() if r["success"])
        logger.info(f"✅ Analysis complete: {success_count}/{len(asins)} successful")
        
        return results


batch_analyzer = BatchAnalyzer()
