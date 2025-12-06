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
        buy_costs: Dict[str, float] = None,
        promo_costs: Dict[str, float] = None,
        source_data: Dict[str, dict] = None,  # For shipping overrides
        user_settings: dict = None,           # User's default rates
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Dict[str, dict]:
        """Analyze products using batch API calls."""
        if not asins:
            return {}
        
        # Deduplicate and clean
        asins = list(set(a.strip().upper() for a in asins if a))
        
        results = {asin: {"asin": asin, "success": False} for asin in asins}
        
        logger.info(f"🚀 Analyzing {len(asins)} products...")
        import time
        start_time = time.time()
        
        # ==========================================
        # STEP 1 & 2: PARALLEL API CALLS
        # Keepa and SP-API can run in parallel - they're independent!
        # ==========================================
        logger.info("📚 Fetching data from Keepa and SP-API in parallel...")
        
        # Run Keepa, SP-API pricing, and SP-API catalog calls in parallel
        keepa_task = keepa_client.get_products_batch(asins, domain=1, history=False, days=90)
        
        # Prepare SP-API pricing calls
        sp_api_pricing_tasks = []
        for i in range(0, len(asins), SP_API_BATCH_SIZE):
            batch = asins[i:i + SP_API_BATCH_SIZE]
            sp_api_pricing_tasks.append(sp_api_client.get_competitive_pricing_batch(batch, marketplace_id))
        
        # Prepare SP-API catalog calls for images/details (parallel with pricing)
        sp_api_catalog_task = sp_api_client.get_catalog_items_batch(asins, marketplace_id)
        
        # Execute all API calls in parallel
        keepa_data, catalog_data, *sp_api_results = await asyncio.gather(
            keepa_task,
            sp_api_catalog_task,
            *sp_api_pricing_tasks,
            return_exceptions=True
        )
        
        # Handle Keepa results
        if isinstance(keepa_data, Exception):
            logger.error(f"Keepa API error: {keepa_data}")
            keepa_data = {}
        else:
            for asin, data in keepa_data.items():
                if asin in results:
                    results[asin].update({
                        "title": data.get("title"),
                        "brand": data.get("brand"),
                        "image_url": data.get("image_url"),  # Keepa image (fallback)
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
        
        # Handle SP-API catalog results (images, titles, brands - higher quality than Keepa)
        if isinstance(catalog_data, Exception):
            logger.warning(f"SP-API catalog error: {catalog_data}")
            catalog_data = {}
        else:
            logger.info(f"📸 SP-API catalog: Got data for {len(catalog_data)} products")
            for asin, catalog in catalog_data.items():
                if asin in results and catalog:
                    # SP-API catalog has higher quality images/details - use it if available
                    if catalog.get("image_url"):
                        results[asin]["image_url"] = catalog.get("image_url")
                        logger.debug(f"✅ {asin}: Using SP-API image")
                    
                    # SP-API title/brand are more reliable
                    if catalog.get("title"):
                        results[asin]["title"] = catalog.get("title")
                    if catalog.get("brand"):
                        results[asin]["brand"] = catalog.get("brand")
                    if catalog.get("sales_rank_category"):
                        results[asin]["category"] = catalog.get("sales_rank_category")
                    if catalog.get("sales_rank"):
                        results[asin]["bsr"] = catalog.get("sales_rank")
        
        # Handle SP-API pricing results
        all_pricing_data = {}
        sp_api_success = False
        for idx, pricing_result in enumerate(sp_api_results):
            if isinstance(pricing_result, Exception):
                logger.warning(f"SP-API pricing batch {idx + 1} failed: {pricing_result}")
                continue
            
            all_pricing_data.update(pricing_result)
            for asin, data in pricing_result.items():
                if data.get("buy_box_price") and asin in results:
                    results[asin]["sell_price"] = data["buy_box_price"]
                    results[asin]["seller_count"] = data.get("offer_count", 0)
                    results[asin]["price_source"] = "sp-api"
                    sp_api_success = True
        
        api_time = time.time() - start_time
        logger.info(f"⚡ API calls completed in {api_time:.2f}s (parallel)")
        
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
        # STEP 2C: FLAG PRODUCTS WITHOUT PRICING
        # ==========================================
        # After both SP-API and Keepa attempts, flag products still without pricing
        asins_still_no_price = [asin for asin in asins if not results[asin].get("sell_price") or results[asin].get("sell_price") <= 0]
        if asins_still_no_price:
            logger.warning(f"⚠️ {len(asins_still_no_price)} products have no pricing data available")
            
            for asin in asins_still_no_price:
                # Determine reason for missing pricing
                pricing_reason = self._determine_pricing_reason(asin, all_pricing_data.get(asin, {}))
                
                # Set pricing status flags
                results[asin].update({
                    "pricing_status": "no_pricing",
                    "pricing_status_reason": pricing_reason,
                    "needs_review": True,
                    "sell_price": None,
                    "fees_total": None,
                    "net_profit": None,
                    "roi": None,
                    "analysis_stage": "needs_review",
                    "passed_stage2": False,  # Can't pass without pricing
                })
                
                # Still include Keepa catalog data if available (helps user understand the product)
                if asin in keepa_data:
                    keepa_product = keepa_data[asin]
                    from app.services.keepa_data_extractor import extract_all_keepa_data
                    keepa_info = extract_all_keepa_data(keepa_product)
                    
                    results[asin].update({
                        "title": keepa_info.get("title") or keepa_product.get("title"),
                        "brand": keepa_info.get("brand") or keepa_product.get("brand"),
                        "category": keepa_info.get("category") or keepa_product.get("category"),
                        "bsr": keepa_info.get("bsr") or keepa_product.get("bsr"),
                        "fba_seller_count": keepa_info.get("fba_seller_count"),
                        "fbm_seller_count": keepa_info.get("fbm_seller_count"),
                        "review_count": keepa_info.get("review_count"),
                        "rating": keepa_info.get("rating"),
                        # 365-day data (might help understand why no pricing)
                        "fba_lowest_365d": keepa_info.get("fba_lowest_365d"),
                        "fbm_lowest_365d": keepa_info.get("fbm_lowest_365d"),
                        "amazon_was_seller": keepa_info.get("amazon_was_seller"),
                    })
                    
                    logger.info(f"⚠️ {asin}: Catalog data available but no pricing - reason: {pricing_reason}")
                else:
                    logger.warning(f"⚠️ {asin}: No pricing AND no catalog data")
        
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
                        # Store as both names for compatibility
                        referral_fee = data.get("referral_fee") or 0
                        results[asin]["referral_fee"] = referral_fee  # Standard name
                        results[asin]["fees_referral"] = referral_fee  # Legacy name
                        fba_fee = data.get("fba_fulfillment_fee") or 0
                        results[asin]["fba_fee"] = fba_fee  # Standard name
                        results[asin]["fees_fba"] = fba_fee  # Legacy name
                        logger.debug(f"✅ {asin}: Fees - Referral: ${referral_fee}, FBA: ${fba_fee}, Total: ${data.get('total')}")
            except Exception as e:
                logger.warning(f"SP-API fees batch failed for batch {i//SP_API_BATCH_SIZE + 1}: {e}")
        
        # FALLBACK: Calculate referral fees for products that didn't get them from SP-API
        from app.services.profit_calculator import get_referral_rate
        for asin in asins:
            if asin in results and results[asin].get("sell_price") and not results[asin].get("referral_fee"):
                category = results[asin].get("category")
                sell_price = results[asin].get("sell_price")
                referral_rate = get_referral_rate(category)
                referral_fee = sell_price * referral_rate
                results[asin]["referral_fee"] = referral_fee
                results[asin]["fees_referral"] = referral_fee
                results[asin]["referral_fee_percent"] = round(referral_rate * 100, 2)
                
                # Recalculate fees_total if missing
                if not results[asin].get("fees_total"):
                    fba_fee = results[asin].get("fba_fee") or results[asin].get("fees_fba") or 0
                    results[asin]["fees_total"] = referral_fee + fba_fee
                
                logger.info(f"📊 {asin}: Calculated referral fee from category: ${referral_fee:.2f} ({referral_rate*100}%)")
        
        # ========== STAGE 2: PROFIT CALCULATION & FILTERING (WITH SHIPPING) ==========
        if buy_costs:
            from app.services.cost_calculator import (
                calculate_inbound_shipping,
                calculate_prep_cost,
                calculate_landed_cost,
                calculate_net_profit,
                calculate_roi
            )
            
            # Get user's default rates
            inbound_rate = (user_settings or {}).get("inbound_rate_per_lb", 0.35)
            default_prep = (user_settings or {}).get("default_prep_cost", 0.10)
            
            logger.info(f"Stage 2: Calculating profitability for {len(asins)} products (with shipping)")
            
            for asin in asins:
                buy_cost = buy_costs.get(asin, 0)
                sell_price = results[asin].get("sell_price") or results[asin].get("current_price") or 0
                fees_total = results[asin].get("fees_total") or 0
                weight_lb = results[asin].get("item_weight_lb")  # From Keepa (Stage 1)
                
                if buy_cost > 0 and sell_price > 0:
                    # Get per-product overrides
                    source = (source_data or {}).get(asin, {})
                    supplier_ships_direct = source.get("supplier_ships_direct", False)
                    rate_override = source.get("inbound_rate_override")
                    prep_override = source.get("prep_cost_override")
                    
                    # Calculate shipping
                    inbound_shipping = calculate_inbound_shipping(
                        weight_lb=weight_lb,
                        user_rate=inbound_rate,
                        supplier_ships_direct=supplier_ships_direct,
                        rate_override=rate_override
                    )
                    
                    prep_cost = calculate_prep_cost(
                        user_default=default_prep,
                        override=prep_override
                    )
                    
                    # Calculate landed cost (buy + shipping + prep)
                    landed_cost = calculate_landed_cost(buy_cost, inbound_shipping, prep_cost)
                    
                    # Calculate profit WITH shipping
                    net_profit = calculate_net_profit(sell_price, fees_total, landed_cost)
                    roi = calculate_roi(net_profit, landed_cost)
                    profit_margin = round((net_profit / sell_price) * 100, 2) if sell_price > 0 else 0
                    
                    # Update results
                    results[asin].update({
                        "buy_cost": buy_cost,
                        "inbound_shipping": inbound_shipping,
                        "prep_cost": prep_cost,
                        "total_landed_cost": landed_cost,
                        "net_profit": net_profit,
                        "roi": roi,
                        "profit_margin": profit_margin,
                        "stage2_roi": roi,
                        "passed_stage2": roi >= 30 and net_profit >= 3,
                        "analysis_stage": "stage2_complete",
                    })
                    
                    # PROMO calculation (also with shipping)
                    promo_buy_cost = (promo_costs or {}).get(asin)
                    if promo_buy_cost and promo_buy_cost > 0:
                        promo_landed = calculate_landed_cost(promo_buy_cost, inbound_shipping, prep_cost)
                        promo_profit = calculate_net_profit(sell_price, fees_total, promo_landed)
                        promo_roi = calculate_roi(promo_profit, promo_landed)
                        
                        results[asin].update({
                            "promo_buy_cost": promo_buy_cost,
                            "promo_landed_cost": promo_landed,
                            "promo_net_profit": promo_profit,
                            "promo_roi": promo_roi,
                        })
                elif sell_price <= 0 or not sell_price:
                    # No valid pricing - already handled in STEP 2C
                    pass
                else:
                    # Has pricing but buy_cost missing or invalid
                    results[asin]["passed_stage2"] = False
                    results[asin]["analysis_stage"] = "stage2_no_data"
            
            passed_count = sum(1 for a in asins if results[a].get("passed_stage2"))
            logger.info(f"Stage 2: {passed_count}/{len(asins)} passed ROI filter (ROI >= 30%, profit >= $3)")
        # ========== END STAGE 2 ==========
        
        # ========== STAGE 3: KEEPA DEEP ANALYSIS (only for Stage 2 winners) ==========
        passed_stage2_asins = [a for a in asins if results[a].get("passed_stage2")]
        
        if passed_stage2_asins and buy_costs:
            logger.info(f"Stage 3: Fetching Keepa data for {len(passed_stage2_asins)} products")
            
            try:
                # Fetch raw Keepa data with stats for 365-day data
                keepa_deep = await keepa_client.get_products_raw(
                    passed_stage2_asins,
                    domain=1,
                    days=365  # Get 365-day stats
                )
                
                from app.services.keepa_data_extractor import extract_all_keepa_data, calculate_worst_case_profit
                
                for asin in passed_stage2_asins:
                    if asin in keepa_deep:
                        keepa_product_raw = keepa_deep[asin]
                        # TODO: keepa_client.get_products_batch returns parsed data, but extract_all_keepa_data
                        # needs raw Keepa API response with stats.365, offers array, etc.
                        # For now, extract_all_keepa_data will return empty dict if data format doesn't match.
                        # Future: Modify keepa_client to also return raw data, or make direct Keepa API call here.
                        keepa_data = extract_all_keepa_data(keepa_product_raw)
                        
                        # Update results with Keepa data
                        results[asin].update({
                            "fba_lowest_365d": keepa_data.get("fba_lowest_365d"),
                            "fba_lowest_date": keepa_data.get("fba_lowest_date"),
                            "fbm_lowest_365d": keepa_data.get("fbm_lowest_365d"),
                            "fbm_lowest_date": keepa_data.get("fbm_lowest_date"),
                            "lowest_was_fba": keepa_data.get("lowest_was_fba"),
                            "amazon_was_seller": keepa_data.get("amazon_was_seller"),
                            "fba_seller_count": keepa_data.get("fba_seller_count"),
                            "fbm_seller_count": keepa_data.get("fbm_seller_count"),
                            "sales_drops_30": keepa_data.get("sales_drops_30"),
                            "sales_drops_90": keepa_data.get("sales_drops_90"),
                            "sales_drops_180": keepa_data.get("sales_drops_180"),
                            "analysis_stage": "stage3_complete",
                        })
                        
                        # Calculate worst case profit (with shipping)
                        buy_cost = buy_costs.get(asin, 0)
                        landed_cost = results[asin].get("total_landed_cost", buy_cost)
                        fba_lowest = keepa_data.get("fba_lowest_365d")
                        
                        if fba_lowest and fba_lowest > 0:
                            # Estimate fees at worst price
                            sell_price = results[asin].get("sell_price", 0)
                            fees_total = results[asin].get("fees_total", 0)
                            fee_ratio = fees_total / sell_price if sell_price > 0 else 0.30
                            worst_fees = fba_lowest * fee_ratio
                            worst_profit = fba_lowest - worst_fees - landed_cost
                            
                            results[asin].update({
                                "worst_case_price": round(fba_lowest, 2),
                                "worst_case_fees": round(worst_fees, 2),
                                "worst_case_profit": round(worst_profit, 2),
                                "still_profitable_at_worst": worst_profit > 0,
                            })
                        
                        # Also update with weight/dimensions from Keepa
                        results[asin].update({
                            "item_weight_lb": keepa_data.get("item_weight_lb"),
                            "item_length_in": keepa_data.get("item_length_in"),
                            "item_width_in": keepa_data.get("item_width_in"),
                            "item_height_in": keepa_data.get("item_height_in"),
                            "size_tier": keepa_data.get("size_tier"),
                        })
                
                logger.info(f"Stage 3: Keepa data extracted for {len(passed_stage2_asins)} products")
                
            except Exception as e:
                logger.error(f"Stage 3 Keepa error: {e}", exc_info=True)
                for asin in passed_stage2_asins:
                    results[asin]["stage3_error"] = str(e)
        # ========== END STAGE 3 ==========
        
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
    
    def _determine_pricing_reason(self, asin: str, pricing_response: dict) -> str:
        """Determine why pricing is missing."""
        if not pricing_response:
            return "no_response"
        
        # Check for specific error codes or indicators
        errors = pricing_response.get("errors", [])
        if errors:
            error_code = errors[0].get("code", "")
            if "InvalidASIN" in error_code:
                return "invalid_asin"
            if "Restricted" in error_code or "Gated" in error_code:
                return "gated"
            return f"error_{error_code}"
        
        # Check offer counts
        offer_count = pricing_response.get("offer_count", 0)
        if offer_count == 0:
            return "no_active_offers"
        
        # Check if buy_box_price is None but offers exist
        if pricing_response.get("buy_box_price") is None and offer_count > 0:
            return "no_buy_box"
        
        return "unknown"


batch_analyzer = BatchAnalyzer()
