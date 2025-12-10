"""
Products API - Parent-Child Model (products + product_sources)
Optimized with Redis caching and query batching.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from app.tasks.file_processing import process_file_upload
import base64
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.redis_client import cached
from app.core.redis import get_cached, set_cached, delete_cached, get_cache_info
import uuid
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
import csv
import io
import logging
import os
import json
import openai
import pandas as pd
from pathlib import Path
from datetime import datetime
from app.core.config import settings
from app.services.column_mapper import column_mapper

logger = logging.getLogger(__name__)
SYNC_PROCESSING_THRESHOLD = settings.SYNC_PROCESSING_THRESHOLD

router = APIRouter(prefix="/products", tags=["products"])


def _calculate_buy_cost_from_wholesale_pack(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Calculate Buy Cost per unit from available columns.
    
    Priority:
    1. If "Wholesale Cost" exists → use it directly as Buy Cost
    2. If "Wholesale" + "Pack" exist → calculate Buy Cost = Wholesale / Pack (only for rows with both)
    3. If "Buy Cost" already exists → use it (skip calculation)
    
    Handles mixed cases where some rows have packs and some don't.
    
    Args:
        df: DataFrame with potential Wholesale Cost, Wholesale, and Pack columns
        
    Returns:
        Tuple of (DataFrame with 'Buy Cost' column added if calculation was performed, status dict)
        Status dict contains: success (bool), calculated_count (int), errors (list), method (str)
    """
    status = {
        'success': False,
        'calculated_count': 0,
        'errors': [],
        'wholesale_col': None,
        'pack_col': None,
        'method': None
    }
    
    # Check if Buy Cost column already exists (case-insensitive)
    df_columns_lower = [c.lower().strip() for c in df.columns]
    if 'buy cost' in df_columns_lower or 'buy_cost' in df_columns_lower:
        logger.debug("Buy Cost column already exists, skipping calculation")
        status['success'] = True
        status['method'] = 'existing_column'
        return df, status
    
    # Find columns (case-insensitive)
    wholesale_cost_col = None  # "Wholesale Cost" - use directly
    wholesale_col = None        # "Wholesale" - needs Pack to calculate
    pack_col = None
    
    for col in df.columns:
        col_lower = col.lower().strip()
        # Check for "Wholesale Cost" (exact match or contains both words)
        if ('wholesale' in col_lower and 'cost' in col_lower) and wholesale_cost_col is None:
            wholesale_cost_col = col
        # Check for just "Wholesale" (without "cost")
        elif 'wholesale' in col_lower and 'cost' not in col_lower and wholesale_col is None:
            wholesale_col = col
        # Check for Pack
        if ('pack' in col_lower or 'case_pack' in col_lower or 'case pack' in col_lower) and pack_col is None:
            pack_col = col
    
    # Priority 1: Use "Wholesale Cost" directly if it exists
    if wholesale_cost_col:
        logger.info(f"✅ Using '{wholesale_cost_col}' directly as Buy Cost")
        try:
            buy_cost_series = pd.to_numeric(df[wholesale_cost_col], errors='coerce')
            buy_cost_series = buy_cost_series.round(2)
            buy_cost_series = buy_cost_series.where(pd.notnull(buy_cost_series), None)
            
            df['Buy Cost'] = buy_cost_series
            calculated_count = buy_cost_series.notna().sum()
            
            status['success'] = True
            status['calculated_count'] = int(calculated_count)
            status['method'] = 'wholesale_cost_direct'
            status['wholesale_col'] = wholesale_cost_col
            
            logger.info(f"✅ Used Wholesale Cost for {calculated_count}/{len(df)} rows")
            return df, status
        except Exception as e:
            error_msg = f"Failed to use Wholesale Cost column: {str(e)}"
            status['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
            # Fall through to try calculation method
    
    # Priority 2: Calculate from Wholesale / Pack (if both exist)
    if wholesale_col and pack_col:
        logger.info(f"✅ Calculating Buy Cost from {wholesale_col} / {pack_col}")
        status['wholesale_col'] = wholesale_col
        status['pack_col'] = pack_col
        
        try:
            # Convert to numeric
            wholesale_series = pd.to_numeric(df[wholesale_col], errors='coerce')
            pack_series = pd.to_numeric(df[pack_col], errors='coerce')
            
            # Initialize Buy Cost series (start with None for all rows)
            buy_cost_series = pd.Series([None] * len(df), dtype=object)
            
            # Calculate only for rows that have both wholesale AND pack values
            # Rows without pack will keep None (which is correct - they don't have per-unit cost)
            mask = wholesale_series.notna() & pack_series.notna() & (pack_series > 0)
            
            if mask.any():
                # Calculate for rows with both values
                calculated = wholesale_series[mask] / pack_series[mask]
                calculated = calculated.round(2)
                buy_cost_series[mask] = calculated
                
                # Count successful calculations
                calculated_count = mask.sum()
                status['calculated_count'] = int(calculated_count)
                status['success'] = True
                status['method'] = 'wholesale_divided_by_pack'
                
                # Count rows without pack (not an error, just info)
                no_pack_count = (wholesale_series.notna() & (pack_series.isna() | (pack_series == 0))).sum()
                if no_pack_count > 0:
                    logger.info(f"ℹ️ {no_pack_count} rows don't have Pack - Buy Cost will be None for those rows")
                
                # Count division by zero
                zero_division_count = (pack_series == 0).sum()
                if zero_division_count > 0:
                    status['errors'].append(f"{zero_division_count} rows have Pack = 0 (division by zero)")
                
                logger.info(f"✅ Calculated Buy Cost for {calculated_count}/{len(df)} rows (rows with both Wholesale and Pack)")
            else:
                status['errors'].append("No rows have both Wholesale and Pack values")
                logger.warning("⚠️ No rows have both Wholesale and Pack values for calculation")
            
            # Add Buy Cost column
            df['Buy Cost'] = buy_cost_series
            
        except Exception as e:
            error_msg = f"Failed to calculate Buy Cost: {str(e)}"
            status['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        return df, status
    
    # No suitable columns found
    if not wholesale_cost_col and not wholesale_col:
        status['errors'].append("Could not find 'Wholesale Cost' or 'Wholesale' column in CSV")
        logger.warning("⚠️ Could not find Wholesale Cost or Wholesale column")
    elif wholesale_col and not pack_col:
        status['errors'].append("Found 'Wholesale' but no 'Pack' column. Need both to calculate per-unit cost, or use 'Wholesale Cost' column directly.")
        logger.warning("⚠️ Found Wholesale but no Pack column")
    
    return df, status


# ============================================
# SCHEMAS
# ============================================

class AddProductRequest(BaseModel):
    asin: str
    brand_name: Optional[str] = None  # Product brand (Nike, Sony) - for ungating
    buy_cost: Optional[float] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None  # Who you buy FROM (Costco, Target)
    moq: Optional[int] = 1
    notes: Optional[str] = None
    source: Optional[str] = "manual"
    source_detail: Optional[str] = None

class CreateProductRequest(BaseModel):
    """Request model for creating a product from analysis results."""
    # Identifiers
    asin: str
    upc: Optional[str] = None
    sku: Optional[str] = None
    
    # Product info
    title: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    
    # Pricing (required for analysis)
    buy_cost: float
    sell_price: Optional[float] = None
    fees: Optional[float] = None
    profit: Optional[float] = None
    roi: Optional[float] = None
    
    # Other
    moq: Optional[int] = 1
    supplier_id: Optional[str] = None
    
    # Keepa data
    bsr: Optional[int] = None
    sales_estimate: Optional[int] = None
    parent_asin: Optional[str] = None

class UpdateDealRequest(BaseModel):
    buy_cost: Optional[float] = None
    moq: Optional[int] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
    supplier_id: Optional[str] = None

class AnalyzeBatchRequest(BaseModel):
    deal_ids: List[str]

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_or_create_brand(user_id: str, brand_name: str) -> Optional[str]:
    """Get or create a brand for ungating tracking. Returns brand_id."""
    if not brand_name:
        return None
    
    brand_name = brand_name.strip()
    if not brand_name:
        return None
    
    # Check existing (case-insensitive)
    existing = supabase.table("brands")\
        .select("id")\
        .eq("user_id", user_id)\
        .ilike("name", brand_name)\
        .limit(1)\
        .execute()
    
    if existing.data:
        return existing.data[0]["id"]
    
    # Create new brand
    try:
        new_brand = supabase.table("brands").insert({
            "user_id": user_id,
            "name": brand_name,
            "is_ungated": False
        }).execute()
        
        return new_brand.data[0]["id"] if new_brand.data else None
    except Exception as e:
        logger.warning(f"Failed to create brand '{brand_name}': {e}")
        return None

def get_or_create_supplier(user_id: str, supplier_name: str, source: str = "manual") -> Optional[str]:
    """Get existing supplier or create new one. Returns supplier_id."""
    if not supplier_name:
        return None
    
    supplier_name = supplier_name.strip()
    if not supplier_name:
        return None
    
    # Check existing (case-insensitive)
    existing = supabase.table("suppliers")\
        .select("id")\
        .eq("user_id", user_id)\
        .ilike("name", supplier_name)\
        .limit(1)\
        .execute()
    
    if existing.data:
        return existing.data[0]["id"]
    
    # Create new
    try:
        new_sup = supabase.table("suppliers").insert({
            "user_id": user_id,
            "name": supplier_name,
            "source": source,
            "is_active": True
        }).execute()
        
        return new_sup.data[0]["id"] if new_sup.data else None
    except Exception as e:
        logger.warning(f"Failed to create supplier '{supplier_name}': {e}")
        return None

def get_or_create_product(user_id: str, asin: str, brand_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get existing product or create new one. Returns product dict.
    Optionally sets brand if provided.
    """
    asin = asin.strip().upper()
    
    if len(asin) != 10:
        raise ValueError("ASIN must be 10 characters")
    
    existing = supabase.table("products")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("asin", asin)\
        .limit(1)\
        .execute()
    
    if existing.data:
        # Update brand if provided and not already set
        product = existing.data[0]
        if brand_name and not product.get("brand_id"):
            brand_id = get_or_create_brand(user_id, brand_name)
            if brand_id:
                supabase.table("products")\
                    .update({"brand_id": brand_id, "brand": brand_name})\
                    .eq("id", product["id"])\
                    .execute()
                product["brand_id"] = brand_id
                product["brand"] = brand_name
        return {"product": product, "created": False}
    
    # Create new product with brand if provided
    product_data = {
        "user_id": user_id,
        "asin": asin,
        "status": "pending"
    }
    
    if brand_name:
        brand_id = get_or_create_brand(user_id, brand_name)
        if brand_id:
            product_data["brand_id"] = brand_id
            product_data["brand"] = brand_name
    
    new_product = supabase.table("products").insert(product_data).execute()
    
    return {"product": new_product.data[0] if new_product.data else None, "created": True}

def upsert_deal(product_id: str, supplier_id: Optional[str], data: dict) -> Dict[str, Any]:
    """
    Insert or update a deal (product_source).
    Unique key: product_id + supplier_id (with NULL handling)
    """
    # Check if deal exists
    query = supabase.table("product_sources")\
        .select("id, stage")\
        .eq("product_id", product_id)
    
    if supplier_id:
        query = query.eq("supplier_id", supplier_id)
    else:
        query = query.is_("supplier_id", "null")
    
    existing = query.limit(1).execute()
    
    if existing.data:
        # UPDATE existing deal
        deal_id = existing.data[0]["id"]
        current_stage = existing.data[0].get("stage", "new")
        
        update_data = {
            "buy_cost": data.get("buy_cost"),
            "moq": data.get("moq", 1),
            "source": data.get("source", "manual"),
            "source_detail": data.get("source_detail"),
            "notes": data.get("notes"),
            "is_active": True,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Only update stage if explicitly provided or if still 'new'
        if data.get("stage"):
            update_data["stage"] = data["stage"]
        
        result = supabase.table("product_sources")\
            .update(update_data)\
            .eq("id", deal_id)\
            .execute()
        
        return {"action": "updated", "deal": result.data[0] if result.data else None}
    
    else:
        # INSERT new deal
        insert_data = {
            "product_id": product_id,
            "supplier_id": supplier_id,
            "buy_cost": data.get("buy_cost"),
            "moq": data.get("moq", 1),
            "source": data.get("source", "manual"),
            "source_detail": data.get("source_detail"),
            "stage": data.get("stage", "new"),
            "notes": data.get("notes"),
            "is_active": True
        }
        
        result = supabase.table("product_sources").insert(insert_data).execute()
        
        return {"action": "created", "deal": result.data[0] if result.data else None}

# ============================================
# ENDPOINTS
# ============================================

@router.get("")
@router.get("/")
@router.get("/deals")  # Alias for frontend compatibility
@cached(ttl=10)  # Cache for 10 seconds (reduced from 30 for faster updates)
async def get_deals(
    stage: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    min_roi: Optional[float] = Query(None),
    min_profit: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    asin_status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user = Depends(get_current_user)
):
    """
    Get all deals (product + source combinations) using PostgreSQL RPC function.
    100% database-side filtering - highly scalable and accurate.
    
    Supports filtering by asin_status:
    - 'asin_found': Has real ASIN (not PENDING_*, not Unknown)
    - 'needs_selection': Needs ASIN selection from multiple options
    - 'needs_asin': Has UPC but no real ASIN (includes PENDING_*)
    - 'manual_entry': No UPC and no real ASIN
    """
    user_id = str(current_user.id)
    
    logger.info(f"🔍 get_deals called - asin_status={asin_status}, stage={stage}, user_id={user_id}")
    
    try:
        # Use PostgreSQL RPC function for 100% database-side filtering
        # This ensures filtering is accurate and scalable
        rpc_params = {
            'p_user_id': user_id,
            'p_asin_status': asin_status if asin_status and asin_status != 'all' else None,
            'p_stage': stage,
            'p_source': source,
            'p_supplier_id': supplier_id,
            'p_min_roi': min_roi,
            'p_min_profit': min_profit,
            'p_search': search,
            'p_limit': limit,
            'p_offset': offset
        }
        
        # Remove None values to avoid passing NULL unnecessarily
        rpc_params = {k: v for k, v in rpc_params.items() if v is not None}
        
        result = supabase.rpc('filter_product_deals', rpc_params).execute()
        deals = result.data or []
        
        # Log filter application for debugging
        if asin_status:
            logger.info(f"✅ ASIN status filter applied (RPC): {asin_status}, returned {len(deals)} deals")
            if deals:
                sample_asins = [d.get('asin', 'NO_ASIN')[:20] for d in deals[:5]]
                logger.info(f"📦 Sample ASINs: {sample_asins}")
            else:
                logger.warning(f"⚠️ No deals returned for filter: {asin_status}")
        else:
            logger.info(f"📋 No ASIN filter - returned {len(deals)} deals")
        
        # Get counts for each status (for UI filters) - only if no filters applied
        counts = {}
        if not stage and not source and not supplier_id and not asin_status and not search:
            try:
                # Use the existing RPC function for counts (already optimized)
                stats_result = supabase.rpc('get_asin_stats', {'p_user_id': user_id}).execute()
                if stats_result.data:
                    stats = stats_result.data
                    counts = {
                        "all": stats.get("all", 0),
                        "asin_found": stats.get("asin_found", 0),
                        "needs_selection": stats.get("needs_selection", 0),
                        "needs_asin": stats.get("needs_asin", 0),
                        "manual_entry": stats.get("manual_entry", 0)
                    }
                else:
                    counts = {"all": len(deals)}
            except Exception as count_error:
                logger.warning(f"Failed to get status counts: {count_error}")
                counts = {"all": len(deals)}
        
        response = {
            "deals": deals,
            "total": len(deals),
            "counts": counts if counts else None
        }
        logger.info(f"📤 Returning {len(deals)} deals (filter: {asin_status})")
        return response
        
    except Exception as e:
        logger.error(f"Failed to fetch deals: {e}", exc_info=True)
        # Check if RPC function doesn't exist
        if "function" in str(e).lower() and "filter_product_deals" in str(e).lower():
            logger.error("filter_product_deals RPC function does not exist! Please run the migration.")
            raise HTTPException(500, "Database function missing. Please contact support.")
        # Fallback to view-based query if RPC fails (graceful degradation)
        logger.warning("RPC call failed, falling back to view-based query")
        try:
            query = supabase.table("product_deals")\
                .select("*")\
                .eq("user_id", user_id)
            
            if stage:
                query = query.eq("stage", stage)
            if source:
                query = query.eq("source", source)
            if supplier_id:
                query = query.eq("supplier_id", supplier_id)
            if search:
                query = query.ilike("asin", f"%{search}%")
            if min_roi is not None:
                query = query.gte("roi", min_roi)
            if min_profit is not None:
                query = query.gte("profit", min_profit)
            
            query = query.order("deal_created_at", desc=True)
            query = query.range(offset, offset + limit - 1)
            
            result = query.execute()
            deals = result.data or []
            
            # Note: Fallback doesn't support ASIN status filtering - will return all
            if asin_status:
                logger.warning(f"⚠️ ASIN status filter not applied in fallback mode: {asin_status}")
            
            return {
                "deals": deals,
                "total": len(deals),
                "counts": None
            }
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {fallback_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(500, str(e))

@router.get("/stats/asin-status")
async def get_asin_status_stats(current_user = Depends(get_current_user)):
    """
    Get ASIN status stats using PostgreSQL RPC function with Redis caching.
    100% database-side counting, cached for 10 seconds for sub-10ms response times.
    """
    user_id = str(current_user.id)
    cache_key = f"asin_stats:{user_id}"
    
    # Check cache first
    cached_stats = get_cached(cache_key)
    if cached_stats is not None:
        logger.debug(f"✅ Cache HIT for {cache_key}")
        return cached_stats
    
    # Cache miss - query database
    logger.debug(f"❌ Cache MISS for {cache_key} - querying database")
    
    try:
        # Call PostgreSQL RPC function - single query, single round-trip
        # This uses FILTER clauses for efficient counting
        result = supabase.rpc('get_asin_stats', {'p_user_id': user_id}).execute()
        
        if result.data:
            stats = result.data
            logger.info(f"✅ ASIN Stats (DB-side) for user {user_id}: {stats}")
            
            # Store in cache for 10 seconds
            set_cached(cache_key, stats, ttl_seconds=10)
            
            return stats
        else:
            # Fallback if RPC returns null
            logger.warning(f"RPC returned null for user {user_id}, using fallback")
            fallback_stats = {
                "all": 0,
                "asin_found": 0,
                "needs_selection": 0,
                "needs_asin": 0,
                "manual_entry": 0
            }
            # Cache fallback too (shorter TTL)
            set_cached(cache_key, fallback_stats, ttl_seconds=5)
            return fallback_stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get ASIN stats via RPC: {e}", exc_info=True)
        # Fallback to safe defaults
        fallback_stats = {
            "all": 0,
            "asin_found": 0,
            "needs_selection": 0,
            "needs_asin": 0,
            "manual_entry": 0
        }
        # Don't cache errors
        return fallback_stats


@router.get("/cache-status")
async def get_cache_status(current_user = Depends(get_current_user)):
    """
    Get Redis cache status and diagnostics.
    Useful for debugging cache performance.
    
    Full path: /api/v1/products/cache-status
    """
    try:
        user_id = str(current_user.id)
        cache_info = get_cache_info(user_id=user_id)
        
        response = {
            "redis": {
                "enabled": cache_info.get("enabled", False),
                "connected": cache_info.get("connected", False),
                "hit_rate": cache_info.get("hit_rate"),
                "memory_usage": cache_info.get("memory_usage"),
            },
            "user_cache": {
                "user_id": user_id,
                "cache_key": cache_info.get("cache_key"),
                "is_cached": cache_info.get("user_cached", False),
                "ttl_seconds": cache_info.get("ttl_seconds", 0)
            },
            "stats": {
                "keyspace_hits": cache_info.get("keyspace_hits", 0),
                "keyspace_misses": cache_info.get("keyspace_misses", 0)
            }
        }
        logger.info(f"Cache status requested by user {user_id}")
        return response
    except Exception as e:
        logger.error(f"Error getting cache status: {e}", exc_info=True)
        return {
            "redis": {
                "enabled": False,
                "connected": False,
                "error": str(e)
            },
            "user_cache": {
                "user_id": str(current_user.id) if current_user else None,
                "error": str(e)
            },
            "stats": {}
        }

@router.get("/stats")
@cached(ttl=10)  # Cache stats for 10 seconds (reduced from 60 for faster updates)
async def get_stats(current_user = Depends(get_current_user)):
    """Get counts by stage and source. Cached for performance."""
    user_id = str(current_user.id)
    
    try:
        # Get all product_deals with stage and status
        result = supabase.table("product_deals")\
            .select("stage, source, product_status")\
            .eq("user_id", user_id)\
            .execute()
        
        deals = result.data or []
        
        stats = {
            "stages": {"new": 0, "analyzing": 0, "reviewed": 0, "top_products": 0, "buy_list": 0, "ordered": 0},
            "sources": {"telegram": 0, "csv": 0, "manual": 0, "quick_analyze": 0},
            "total": len(deals)
        }
        
        for d in deals:
            # Stage from product_sources
            stage = d.get("stage") or "new"
            
            # Map product status to stage if stage is missing
            product_status = d.get("product_status") or "pending"
            if not stage or stage == "new":
                # Map product status to stage
                if product_status == "analyzing":
                    stage = "analyzing"
                elif product_status == "analyzed":
                    stage = "reviewed"  # Analyzed products go to reviewed stage
                elif product_status == "error":
                    stage = "new"  # Errors stay in new
                else:
                    stage = "new"
            
            source = d.get("source") or "manual"
            
            if stage in stats["stages"]:
                stats["stages"][stage] += 1
            if source in stats["sources"]:
                stats["sources"][source] += 1
        
        # Log stats for debugging
        logger.debug(f"Stats for user {user_id}: {stats}")
        
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        # Check if it's a view missing error
        if "relation" in str(e).lower() and "product_deals" in str(e).lower():
            logger.error("product_deals view does not exist! Please create it in the database.")
            # Return empty stats instead of crashing
            return {
                "stages": {"new": 0, "analyzing": 0, "reviewed": 0, "top_products": 0, "buy_list": 0, "ordered": 0},
                "sources": {"telegram": 0, "csv": 0, "manual": 0, "quick_analyze": 0},
                "total": 0
            }
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))

@router.get("/by-asin/{asin}")
@cached(ttl=60)
async def get_deals_for_asin(asin: str, current_user = Depends(get_current_user)):
    """
    Get all deals for a specific ASIN (compare suppliers).
    Useful for comparing multiple supplier offers for the same product.
    """
    user_id = str(current_user.id)
    asin = asin.strip().upper()
    
    try:
        result = supabase.table("product_deals")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("asin", asin)\
            .order("buy_cost", desc=False)\
            .execute()
        
        return {"asin": asin, "deals": result.data or []}
    except Exception as e:
        logger.error(f"Failed to fetch deals for ASIN {asin}: {e}")
        raise HTTPException(500, str(e))

@router.post("")
async def create_product(
    request: CreateProductRequest,
    current_user = Depends(get_current_user)
):
    """
    Create a new product from analysis results.
    This endpoint is called when user clicks "Add to Products" after analysis.
    """
    user_id = str(current_user.id)
    
    logger.info(f"📝 Creating product for user {user_id}: ASIN={request.asin}")
    
    try:
        asin = request.asin.strip().upper()
        if len(asin) != 10:
            raise HTTPException(400, "ASIN must be 10 characters")
        
        # Get or create product
        product_result = get_or_create_product(user_id, asin, request.brand)
        product = product_result["product"]
        
        if not product:
            raise HTTPException(500, "Failed to create product")
        
        # Update product with analysis data
        update_data = {
            "title": request.title or product.get("title"),
            "brand": request.brand or product.get("brand"),
            "image_url": request.image_url or product.get("image_url"),
            "category": request.category or product.get("category"),
            "upc": request.upc or product.get("upc"),
            "sku": request.sku or product.get("sku"),
            "bsr": request.bsr or product.get("bsr"),
            "sales_estimate": request.sales_estimate or product.get("sales_estimate"),
            "parent_asin": request.parent_asin or product.get("parent_asin"),
            "status": "analyzed",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if update_data:
            updated_product = supabase.table("products")\
                .update(update_data)\
                .eq("id", product["id"])\
                .execute()
            
            if updated_product.data:
                product = updated_product.data[0]
        
        # Create or update product_source (deal)
        deal_result = upsert_deal(product["id"], request.supplier_id, {
            "buy_cost": request.buy_cost,
            "moq": request.moq or 1,
            "source": "quick_analyze",
            "source_detail": "Added from analysis",
            "stage": "reviewed"  # Already analyzed, so mark as reviewed
        })
        
        # If we have analysis data (profit, ROI, etc.), we should also create/update an analysis record
        # But for now, the product_source contains the key data
        
        logger.info(f"✅ Product created: {product['id']}, Deal: {deal_result.get('deal', {}).get('id')}")
        
        # Invalidate stats cache (product count changed)
        cache_key = f"asin_stats:{user_id}"
        delete_cached(cache_key)
        logger.debug(f"🗑️  Cache invalidated: {cache_key}")
        
        return {
            "success": True,
            "product": product,
            "deal": deal_result.get("deal"),
            "message": "Product added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create product: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create product: {str(e)}")

@router.post("/add-deal")
async def add_deal(req: AddProductRequest, current_user = Depends(get_current_user)):
    """
    Add a deal (creates product if needed, then creates/updates deal).
    This is the main entry point for adding products manually.
    """
    user_id = str(current_user.id)
    
    try:
        asin = req.asin.strip().upper()
        if len(asin) != 10:
            raise HTTPException(400, "ASIN must be 10 characters")
        
        # Get or create product (with brand if provided)
        product_result = get_or_create_product(user_id, asin, req.brand_name)
        product = product_result["product"]
        
        if not product:
            raise HTTPException(500, "Failed to create product")
        
        # Get or create supplier (who you buy FROM)
        supplier_id = req.supplier_id
        if not supplier_id and req.supplier_name:
            supplier_id = get_or_create_supplier(user_id, req.supplier_name, "manual")
        
        # Upsert deal
        deal_result = upsert_deal(product["id"], supplier_id, {
            "buy_cost": req.buy_cost,
            "moq": req.moq,
            "source": req.source or "manual",
            "source_detail": req.source_detail,
            "notes": req.notes
        })
        
        return {
            "product_created": product_result["created"],
            "deal_action": deal_result["action"],
            "product_id": product["id"],
            "deal": deal_result["deal"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add deal: {e}")
        raise HTTPException(500, str(e))

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    supplier_id: str = Form(...),  # REQUIRED - which supplier is this from
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(get_current_user)
):
    """
    Upload CSV or Excel file for background processing via Celery.
    ALL products in file will be tied to the selected supplier.
    Returns job_id immediately, processes in background.
    """
    logger.info("=" * 80)
    logger.info("📤 UPLOAD ENDPOINT HIT")
    logger.info("=" * 80)
    
    try:
        user_id = str(current_user.id)
        filename = file.filename or "unknown"
        
        logger.info(f"📋 Upload Parameters:")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Supplier ID: {supplier_id}")
        logger.info(f"   Filename: {filename}")
        
        # Validate file type
        if not filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            logger.error(f"❌ Invalid file type: {filename}")
            raise HTTPException(400, "File must be .csv, .xlsx, or .xls")
        
        # Validate supplier belongs to user
        logger.info(f"🔍 Validating supplier {supplier_id} for user {user_id}...")
        supplier = supabase.table("suppliers")\
            .select("id, name")\
            .eq("id", supplier_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not supplier.data:
            logger.error(f"❌ Invalid supplier: {supplier_id} not found for user {user_id}")
            raise HTTPException(400, "Invalid supplier")
        
        logger.info(f"✅ Supplier validated: {supplier.data[0]['name']}")
        
        # Read and encode file contents
        logger.info(f"📖 Reading file content...")
        contents = await file.read()
        logger.info(f"   File size: {len(contents)} bytes")
        
        contents_b64 = base64.b64encode(contents).decode()
        logger.info(f"   Base64 encoded size: {len(contents_b64)} characters")
        
        # Create job record
        job_id = str(uuid.uuid4())
        job_type = "file_upload"
        
        logger.info(f"💾 Creating job record: {job_id}")
        try:
            supabase.table("jobs").insert({
                "id": job_id,
                "user_id": user_id,
                "type": job_type,
                "status": "pending",
                "metadata": {
                    "filename": filename,
                    "supplier_id": supplier_id,
                    "supplier_name": supplier.data[0]["name"]
                }
            }).execute()
            logger.info(f"✅ Job record created: {job_id}")
        except Exception as db_error:
            logger.error(f"❌ Failed to create job record: {db_error}")
            # Check if jobs table exists
            error_str = str(db_error)
            if "could not find the table" in error_str.lower() or "PGRST205" in error_str:
                raise HTTPException(500, "jobs table not found. Please run the SQL migration: database/CREATE_UNIFIED_JOBS_TABLE.sql")
            raise HTTPException(500, f"Database error: {error_str}")
        
        # Queue Celery task with fallback to BackgroundTasks
        from fastapi import BackgroundTasks
        from app.tasks.file_processing import process_file_upload_sync
        
        # Create background task function
        def run_file_processing():
            logger.info(f"🚀 BACKGROUND TASK STARTING for job {job_id}")
            logger.info(f"   User: {user_id}, Supplier: {supplier_id}, File: {filename}")
            try:
                process_file_upload_sync(job_id, user_id, supplier_id, contents_b64, filename)
                logger.info(f"✅ BACKGROUND TASK COMPLETED for job {job_id}")
            except Exception as e:
                logger.error(f"❌ BACKGROUND TASK FAILED for job {job_id}: {e}", exc_info=True)
                # Update job status
                try:
                    supabase.table("jobs").update({
                        "status": "failed",
                        "errors": [f"Task execution failed: {str(e)}"]
                    }).eq("id", job_id).execute()
                except:
                    pass
        
        # CRITICAL: Try Celery first, fallback to BackgroundTasks
        logger.info("=" * 80)
        logger.info("📤 QUEUING CELERY TASK")
        logger.info("=" * 80)
        logger.info(f"   Job ID: {job_id}")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Supplier ID: {supplier_id}")
        logger.info(f"   Filename: {filename}")
        logger.info(f"   Content length (base64): {len(contents_b64)}")
        
        try:
            # Import the task
            from app.tasks.file_processing import process_file_upload
            
            logger.info(f"🔍 Checking Celery task signature...")
            logger.info(f"   Task: {process_file_upload}")
            logger.info(f"   Task name: {process_file_upload.name}")
            
            # Call .delay() with correct parameters
            logger.info(f"🚀 Calling process_file_upload.delay()...")
            logger.info(f"   Parameters: job_id={job_id}, user_id={user_id}, supplier_id={supplier_id}, filename={filename}")
            
            task_result = process_file_upload.delay(
                job_id=job_id,
                user_id=user_id,
                supplier_id=supplier_id,
                file_contents_b64=contents_b64,
                filename=filename
            )
            
            logger.info("=" * 80)
            logger.info(f"✅ CELERY TASK QUEUED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"   Task ID: {task_result.id}")
            logger.info(f"   Task State: {task_result.state}")
            logger.info(f"   Task Ready: {task_result.ready()}")
            
        except Exception as celery_error:
            logger.error("=" * 80)
            logger.error(f"❌ CELERY TASK FAILED TO QUEUE")
            logger.error("=" * 80)
            logger.error(f"   Error Type: {type(celery_error).__name__}")
            logger.error(f"   Error Message: {str(celery_error)}")
            logger.error(f"   Full Traceback:")
            import traceback
            logger.error(traceback.format_exc())
            
            logger.warning("⚠️ Falling back to FastAPI BackgroundTasks (Celery worker may not be running)...")
            
            # Fallback: Use FastAPI BackgroundTasks
            background_tasks.add_task(run_file_processing)
            logger.info(f"✅ Added to BackgroundTasks for job {job_id}")
        
        logger.info("=" * 80)
        logger.info(f"✅ UPLOAD ENDPOINT COMPLETE - Returning response")
        logger.info("=" * 80)
        
        return {
            "job_id": job_id,
            "message": f"Upload started - assigning to {supplier.data[0]['name']}",
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ UPLOAD ENDPOINT ERROR")
        logger.error("=" * 80)
        logger.error(f"   Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.post("/upload/preview")
async def preview_csv_upload(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    Preview CSV/Excel and suggest column mapping.
    Returns first 5 rows + suggested mapping.
    """
    user_id = str(current_user.id)
    
    # Validate file
    if not file.filename:
        raise HTTPException(400, "File name is required")
    
    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    try:
        # Read file
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(400, "File is empty")
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, f"File is too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")
        
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.csv', '.xlsx', '.xls']:
            raise HTTPException(400, f"Invalid file type. Only CSV and Excel files (.csv, .xlsx, .xls) are supported. Got: {file_ext}")
        
        # Parse file with error handling
        try:
            if file_ext in ['.xlsx', '.xls']:
                try:
                    df = pd.read_excel(io.BytesIO(content), engine='openpyxl' if file_ext == '.xlsx' else None)
                except Exception as e:
                    raise HTTPException(400, f"Failed to parse Excel file. Make sure it's a valid Excel file. Error: {str(e)}")
            else:
                try:
                    # Try different encodings
                    try:
                        df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
                    except UnicodeDecodeError:
                        try:
                            df = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig')  # Handle BOM
                        except UnicodeDecodeError:
                            df = pd.read_csv(io.BytesIO(content), encoding='latin-1')  # Fallback
                except Exception as e:
                    raise HTTPException(400, f"Failed to parse CSV file. Make sure it's a valid CSV file. Error: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Failed to parse file: {str(e)}")
        
        # Validate DataFrame
        if df.empty:
            raise HTTPException(400, "File contains no data rows")
        
        if len(df.columns) == 0:
            raise HTTPException(400, "File contains no columns")
        
        logger.info(f"📄 Uploaded file: {len(df)} rows, {len(df.columns)} columns")
        
        # CRITICAL FIX: Replace NaN values with None for JSON serialization
        # This prevents "Out of range float values are not JSON compliant: nan" errors
        df = df.replace({pd.NA: None, pd.NaT: None})
        df = df.where(pd.notnull(df), None)
        
        # Calculate Buy Cost from Wholesale/Pack if missing
        # Store original columns BEFORE calculation (so "Buy Cost" doesn't appear in mapping)
        original_columns = df.columns.tolist()
        df, buy_cost_status = _calculate_buy_cost_from_wholesale_pack(df)
        
        # Get column names - EXCLUDE calculated "Buy Cost" from mapping options
        # Users should map "Wholesale Cost" or "Wholesale" + "Pack", not the calculated "Buy Cost"
        columns = [col for col in df.columns.tolist() if col != 'Buy Cost']
        
        # Get sample data (first row) - exclude "Buy Cost" from sample so it doesn't confuse AI mapping
        sample_data = None
        if len(df) > 0:
            try:
                sample_dict = df.iloc[0].to_dict()
                # Remove "Buy Cost" from sample data so it doesn't confuse AI mapping
                if 'Buy Cost' in sample_dict:
                    del sample_dict['Buy Cost']
                sample_data = sample_dict
            except Exception as e:
                logger.warning(f"Failed to get sample data: {e}")
        
        # AI column mapping with error handling
        suggested_mapping = {}
        validation = {}
        try:
            suggested_mapping = await column_mapper.map_columns_ai(
                columns=columns,
                sample_data=sample_data
            )
            
            # Validate mapping
            validation = column_mapper.validate_mapping(suggested_mapping)
        except Exception as e:
            logger.warning(f"AI column mapping failed: {e}, using fallback")
            # Fallback: create basic mapping
            suggested_mapping = {}
            validation = {'valid': False, 'errors': [f"Column mapping failed: {str(e)}"]}
        
        # Get preview data (first 5 rows) - now safe from NaN values
        preview_data = []
        try:
            preview_data = df.head(5).to_dict('records')
        except Exception as e:
            logger.error(f"Failed to convert preview data: {e}", exc_info=True)
            raise HTTPException(500, f"Failed to generate preview: {str(e)}")
        
        return {
            'filename': file.filename,
            'total_rows': len(df),
            'columns': columns,  # Excludes calculated "Buy Cost" column
            'suggested_mapping': suggested_mapping,
            'validation': validation,
            'preview_data': preview_data,
            'buy_cost_calculation': buy_cost_status,
            'calculated_buy_cost_column': 'Buy Cost' if buy_cost_status.get('success') else None  # Inform frontend that Buy Cost was calculated
        }
        
    except HTTPException:
        raise
    except pd.errors.EmptyDataError:
        raise HTTPException(400, "File is empty or corrupted")
    except pd.errors.ParserError as e:
        raise HTTPException(400, f"File format is invalid. Please check that your CSV/Excel file is properly formatted. Error: {str(e)}")
    except UnicodeDecodeError as e:
        raise HTTPException(400, f"File encoding error. Please save your file as UTF-8 and try again. Error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to preview file: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to preview file: {str(e)}")

class ConfirmUploadRequest(BaseModel):
    filename: str
    file_data: str  # Base64 encoded
    column_mapping: Dict[str, str]  # {'title': 'DESCRIPTION', 'cost': 'WHOLESALE'}
    supplier_id: Optional[str] = None

@router.post("/upload/confirm")
async def confirm_csv_upload(
    request: ConfirmUploadRequest,
    current_user = Depends(get_current_user)
):
    """
    Process CSV/Excel with user-confirmed column mapping.
    """
    user_id = str(current_user.id)
    
    # Validate request
    if not request.filename:
        raise HTTPException(400, "Filename is required")
    
    if not request.file_data:
        raise HTTPException(400, "File data is required")
    
    if not request.column_mapping:
        raise HTTPException(400, "Column mapping is required")
    
    try:
        # Read file (from base64) with error handling
        try:
            file_bytes = base64.b64decode(request.file_data)
        except Exception as e:
            raise HTTPException(400, f"Invalid file data encoding: {str(e)}")
        
        if len(file_bytes) == 0:
            raise HTTPException(400, "File data is empty")
        
        # Parse file with comprehensive error handling
        try:
            file_ext = Path(request.filename).suffix.lower()
            if file_ext in ['.xlsx', '.xls']:
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl' if file_ext == '.xlsx' else None)
                except Exception as e:
                    raise HTTPException(400, f"Failed to parse Excel file: {str(e)}")
            else:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8-sig')
                    except UnicodeDecodeError:
                        df = pd.read_csv(io.BytesIO(file_bytes), encoding='latin-1')
                except Exception as e:
                    raise HTTPException(400, f"Failed to parse CSV file: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Failed to parse file: {str(e)}")
        
        # CRITICAL FIX: Replace NaN values with None for JSON serialization
        # This prevents "Out of range float values are not JSON compliant: nan" errors
        df = df.replace({pd.NA: None, pd.NaT: None})
        df = df.where(pd.notnull(df), None)
        
        # Validate DataFrame
        if df.empty:
            raise HTTPException(400, "File contains no data rows")
        
        if len(df.columns) == 0:
            raise HTTPException(400, "File contains no columns")
        
        # Calculate Buy Cost from Wholesale/Pack if missing
        df, buy_cost_status = _calculate_buy_cost_from_wholesale_pack(df)
        
        # Log buy cost calculation status
        if buy_cost_status['success']:
            logger.info(f"✅ Buy Cost calculated: {buy_cost_status['calculated_count']}/{len(df)} rows")
        elif buy_cost_status['errors']:
            logger.warning(f"⚠️ Buy Cost calculation issues: {', '.join(buy_cost_status['errors'])}")
        
        logger.info(f"📦 Processing {len(df)} products with mapping: {request.column_mapping}")
        
        # Get supplier mapping (if supplier_name column provided)
        supplier_map = {}
        if 'supplier_name' in request.column_mapping:
            suppliers_result = supabase.table('suppliers')\
                .select('id, name')\
                .eq('user_id', user_id)\
                .execute()
            
            supplier_map = {s['name']: s['id'] for s in (suppliers_result.data or [])}
        
        # Process each row
        created_products = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Map columns to product fields
                product_data = {
                    'user_id': user_id,
                    'upload_source': 'csv',
                    'source_filename': request.filename,
                    'status': 'pending',
                    'uploaded_at': datetime.utcnow().isoformat()
                }
                
                # Apply column mapping with error handling
                for our_field, csv_column in request.column_mapping.items():
                    if csv_column not in row:
                        continue
                    
                    value = row[csv_column]
                    
                    # Skip None/NaN values
                    if pd.isna(value) or value is None:
                        continue
                    
                    try:
                        # Map to correct field name with type validation
                        if our_field == 'title':
                            product_data['uploaded_title'] = str(value).strip() if value else None
                        elif our_field == 'brand':
                            product_data['uploaded_brand'] = str(value).strip() if value else None
                        elif our_field == 'category':
                            product_data['uploaded_category'] = str(value).strip() if value else None
                        elif our_field == 'cost' or our_field == 'buy_cost':
                            # Handle numeric conversion with error handling
                            try:
                                # Remove currency symbols and commas
                                if isinstance(value, str):
                                    value = value.replace('$', '').replace(',', '').strip()
                                buy_cost = float(value)
                                if buy_cost < 0:
                                    raise ValueError(f"Buy cost cannot be negative: {buy_cost}")
                                product_data['buy_cost'] = buy_cost
                            except (ValueError, TypeError) as e:
                                errors.append({
                                    'row': idx + 1,
                                    'error': f"Invalid buy cost value '{value}' in column '{csv_column}': {str(e)}",
                                    'data': {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                                })
                                continue
                        elif our_field == 'wholesale_cost_case':
                            # Store wholesale case cost - will calculate buy_cost later if pack is available
                            try:
                                if isinstance(value, str):
                                    value = value.replace('$', '').replace(',', '').strip()
                                wholesale_case = float(value)
                                if wholesale_case < 0:
                                    raise ValueError(f"Wholesale case cost cannot be negative: {wholesale_case}")
                                product_data['wholesale_cost_case'] = wholesale_case
                            except (ValueError, TypeError) as e:
                                errors.append({
                                    'row': idx + 1,
                                    'error': f"Invalid wholesale case cost value '{value}' in column '{csv_column}': {str(e)}",
                                    'data': {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                                })
                                continue
                        elif our_field == 'case_pack':
                            try:
                                case_pack = int(float(value))  # Allow float input, convert to int
                                if case_pack < 1:
                                    raise ValueError(f"Case pack must be at least 1: {case_pack}")
                                product_data['case_pack'] = case_pack
                            except (ValueError, TypeError) as e:
                                errors.append({
                                    'row': idx + 1,
                                    'error': f"Invalid case pack value '{value}' in column '{csv_column}': {str(e)}",
                                    'data': {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                                })
                                continue
                        elif our_field == 'moq':
                            try:
                                moq = int(float(value))  # Allow float input, convert to int
                                if moq < 1:
                                    raise ValueError(f"MOQ must be at least 1: {moq}")
                                product_data['moq'] = moq
                            except (ValueError, TypeError) as e:
                                errors.append({
                                    'row': idx + 1,
                                    'error': f"Invalid MOQ value '{value}' in column '{csv_column}': {str(e)}",
                                    'data': {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                                })
                                continue
                        elif our_field == 'supplier_name':
                            supplier_name = str(value).strip()
                            if supplier_name in supplier_map:
                                product_data['supplier_id'] = supplier_map[supplier_name]
                            else:
                                # Log warning but don't fail - supplier might be created later
                                logger.warning(f"Supplier '{supplier_name}' not found for row {idx + 1}")
                        else:
                            # Generic field mapping
                            product_data[our_field] = value
                    except Exception as e:
                        errors.append({
                            'row': idx + 1,
                            'error': f"Error processing field '{our_field}' from column '{csv_column}': {str(e)}",
                            'data': {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                        })
                        continue
                
                # Calculate buy_cost from wholesale_cost_case + case_pack if needed
                # Check both product_data (from mapping) and row data (direct from CSV)
                if 'buy_cost' not in product_data:
                    # Try from mapped fields first
                    if 'wholesale_cost_case' in product_data and 'case_pack' in product_data:
                        wholesale_case = product_data.get('wholesale_cost_case')
                        case_pack = product_data.get('case_pack')
                        if wholesale_case is not None and case_pack is not None and case_pack > 0:
                            try:
                                product_data['buy_cost'] = round(float(wholesale_case) / float(case_pack), 2)
                                logger.debug(f"Row {idx + 1}: Calculated buy_cost from mapped fields = {product_data['buy_cost']}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Row {idx + 1}: Could not calculate from mapped fields: {e}")
                    
                    # If still not calculated, try to get from row data directly (check if columns are mapped)
                    if 'buy_cost' not in product_data:
                        wholesale_col = request.column_mapping.get('wholesale_cost_case')
                        pack_col = request.column_mapping.get('case_pack')
                        
                        if wholesale_col and pack_col and wholesale_col in row.index and pack_col in row.index:
                            wholesale_val = row[wholesale_col]
                            pack_val = row[pack_col]
                            
                            if pd.notna(wholesale_val) and pd.notna(pack_val):
                                try:
                                    wholesale_case = float(wholesale_val) if not pd.isna(wholesale_val) else None
                                    case_pack = float(pack_val) if not pd.isna(pack_val) else None
                                    
                                    if wholesale_case is not None and case_pack is not None and case_pack > 0:
                                        product_data['buy_cost'] = round(wholesale_case / case_pack, 2)
                                        logger.debug(f"Row {idx + 1}: Calculated buy_cost from CSV columns = {product_data['buy_cost']}")
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Row {idx + 1}: Could not calculate from CSV columns: {e}")
                
                # If still no buy_cost, try to get from calculated "Buy Cost" column (created by _calculate_buy_cost_from_wholesale_pack)
                if 'buy_cost' not in product_data and 'Buy Cost' in df.columns:
                    buy_cost_val = row.get('Buy Cost')
                    if pd.notna(buy_cost_val) and buy_cost_val is not None:
                        try:
                            if isinstance(buy_cost_val, str):
                                buy_cost_val = buy_cost_val.replace('$', '').replace(',', '').strip()
                            product_data['buy_cost'] = float(buy_cost_val)
                            logger.debug(f"Row {idx + 1}: Using calculated Buy Cost column = {product_data['buy_cost']}")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Row {idx + 1}: Could not use calculated Buy Cost value: {e}")
                
                # Validate buy_cost is present
                if 'buy_cost' not in product_data or product_data.get('buy_cost') is None:
                    # Check what's mapped to provide helpful error
                    has_cost_mapping = 'cost' in request.column_mapping
                    has_wholesale_mapping = 'wholesale_cost_case' in request.column_mapping
                    has_pack_mapping = 'case_pack' in request.column_mapping
                    
                    error_msg = "Buy cost is required but could not be determined. "
                    if has_wholesale_mapping and not has_pack_mapping:
                        error_msg += "Map 'case_pack' to 'Pack' column to calculate buy cost from wholesale case cost."
                    elif has_pack_mapping and not has_wholesale_mapping:
                        error_msg += "Map 'wholesale_cost_case' to 'Wholesale' column, or map 'cost' to 'Wholesale Cost' column."
                    elif not has_cost_mapping and not (has_wholesale_mapping and has_pack_mapping):
                        error_msg += "Map 'cost' to 'Wholesale Cost' column, or map 'wholesale_cost_case' + 'case_pack' to calculate it."
                    else:
                        error_msg += "Values in mapped columns may be empty or invalid. Check your CSV data."
                    
                    errors.append({
                        'row': idx + 1,
                        'error': error_msg,
                        'data': {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                    })
                    continue
                
                # Store original row data (NaN already replaced with None above)
                # Convert any remaining NaN values to None for JSON serialization
                original_data = row.to_dict()
                product_data['original_upload_data'] = {k: (None if pd.isna(v) else v) for k, v in original_data.items()}
                
                # Add supplier_id if provided
                if request.supplier_id:
                    product_data['supplier_id'] = request.supplier_id
                
                # Determine ASIN status
                if product_data.get('asin'):
                    product_data['asin_status'] = 'found'
                elif product_data.get('upc'):
                    product_data['asin_status'] = 'pending_lookup'
                else:
                    product_data['asin_status'] = 'needs_input'
                
                # Create product
                result = supabase.table('products').insert(product_data).execute()
                if result.data:
                    product = result.data[0]
                    created_products.append(product)
                    
                    # Create product_source (deal) if supplier_id is provided
                    if request.supplier_id and product_data.get('buy_cost'):
                        upsert_deal(product['id'], request.supplier_id, {
                            'buy_cost': product_data.get('buy_cost'),
                            'moq': product_data.get('moq', 1),
                            'source': 'csv',
                            'source_detail': request.filename,
                            'stage': 'new'
                        })
                
            except Exception as e:
                logger.error(f"Failed to create product from row {idx}: {e}")
                # Convert row to dict, replacing any NaN values with None for JSON
                error_row_data = row.to_dict()
                error_row_data_clean = {k: (None if pd.isna(v) else v) for k, v in error_row_data.items()}
                errors.append({
                    'row': idx + 1,
                    'error': str(e),
                    'data': error_row_data_clean
                })
        
        logger.info(f"✅ Created {len(created_products)} products, {len(errors)} errors")
        
        return {
            'success': True,
            'total': len(df),
            'created': len(created_products),
            'failed': len(errors),
            'errors': errors[:10],  # Return first 10 errors
            'buy_cost_calculation': buy_cost_status
        }
        
    except Exception as e:
        logger.error(f"Failed to process upload: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to process upload: {str(e)}")

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    """
    DEPRECATED: Use /upload instead with supplier_id.
    Upload CSV/Excel - creates products and deals.
    Uses AI column detection for flexible file formats.
    Handles BOM, normalizes headers, and supports various delimiters.
    """
    user_id = str(current_user.id)
    
    # Read file
    contents = await file.read()
    file_extension = Path(file.filename or "").suffix.lower()
    
    # Parse based on file type
    if file_extension in ['.xlsx', '.xls']:
        try:
            engine = 'openpyxl' if file_extension == '.xlsx' else None
            df = pd.read_excel(io.BytesIO(contents), engine=engine, sheet_name=0)
            df = df.dropna(how='all')
            
            # Normalize column names (strip whitespace, lowercase)
            df.columns = [str(col).strip() for col in df.columns]
            
            all_rows = df.to_dict('records')
            headers = [str(col).strip().lower() for col in df.columns]  # Normalized headers
            
            for row in all_rows:
                for key, value in row.items():
                    if pd.isna(value):
                        row[key] = None
                    elif isinstance(value, (pd.Timestamp,)):
                        row[key] = value.isoformat()
                    else:
                        row[key] = str(value) if value is not None else None
        except Exception as e:
            logger.error(f"Excel parsing error: {e}")
            raise HTTPException(400, f"Failed to parse Excel file: {str(e)}")
    elif file_extension == '.csv':
        # Remove BOM if present (Excel adds this)
        try:
            decoded = contents.decode('utf-8-sig')  # utf-8-sig strips BOM
        except:
            decoded = contents.decode('utf-8')  # Fallback
        
        # Try different delimiters
        sniffer = csv.Sniffer()
        sample = decoded[:1024]  # Sample first 1KB
        try:
            dialect = sniffer.sniff(sample, delimiters=',;\t')
        except:
            dialect = csv.excel  # Default to comma
        
        reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
        
        # Normalize headers (strip whitespace, lowercase for matching)
        original_headers = reader.fieldnames or []
        normalized_headers = [h.strip().lower() if h else h for h in original_headers]
        reader.fieldnames = normalized_headers
        
        # Debug logging
        logger.info(f"CSV Headers (original): {original_headers}")
        logger.info(f"CSV Headers (normalized): {normalized_headers}")
        
        all_rows = list(reader)
        headers = normalized_headers
        
        # Debug: log first row
        if all_rows:
            logger.info(f"First row data: {dict(all_rows[0])}")
    else:
        raise HTTPException(400, f"Unsupported file type: {file_extension}")
    
    if not headers:
        raise HTTPException(400, "File has no headers")
    
    # Use improved column detection (case-insensitive, handles variations)
    # IMPORTANT: Brand and Supplier are DIFFERENT!
    # Brand = Product manufacturer (Nike, Sony) - for ungating
    # Supplier = Who you buy FROM (Costco, Target) - for deals
    column_mapping = {}
    for h in headers:
        h_clean = h.strip().lower()
        if not column_mapping.get("asin") and ("asin" in h_clean or h_clean == "asin"):
            column_mapping["asin"] = h
        elif not column_mapping.get("brand") and (h_clean == "brand" or h_clean == "manufacturer" or h_clean == "maker"):
            column_mapping["brand"] = h
        elif not column_mapping.get("supplier") and ("supplier" in h_clean or "vendor" in h_clean or "seller" in h_clean):
            column_mapping["supplier"] = h
        elif not column_mapping.get("buy_cost") and ("cost" in h_clean or "price" in h_clean or ("buy" in h_clean and "cost" in h_clean)):
            column_mapping["buy_cost"] = h
        elif not column_mapping.get("moq") and ("moq" in h_clean or "qty" in h_clean or "quantity" in h_clean or "min" in h_clean):
            column_mapping["moq"] = h
        elif not column_mapping.get("notes") and ("note" in h_clean or "comment" in h_clean or "description" in h_clean):
            column_mapping["notes"] = h
    
    logger.info(f"Detected column mapping: {column_mapping}")
    
    if not column_mapping.get("asin"):
        raise HTTPException(
            400, 
            f"Could not detect ASIN column. Found columns: {', '.join(headers)}. "
            "Please ensure your CSV has a column named 'ASIN' or 'asin'."
        )
    
    results = {
        "products_created": 0,
        "deals_created": 0,
        "deals_updated": 0,
        "errors": []
    }
    supplier_cache = {}
    
    # Get existing suppliers for matching
    existing_suppliers = supabase.table("suppliers")\
        .select("id, name")\
        .eq("user_id", user_id)\
        .execute()
    
    supplier_name_to_id = {s["name"].lower(): s["id"] for s in (existing_suppliers.data or [])}
    
    for row_idx, row in enumerate(all_rows, start=2):
        try:
            # Get ASIN - handle both normalized and original column names
            asin_col = column_mapping["asin"]
            # Try normalized first, then original
            asin_value = row.get(asin_col) or row.get(asin_col.strip().lower()) or ""
            asin = str(asin_value).strip().upper() if asin_value else ""
            
            if not asin or len(asin) != 10:
                results["errors"].append(f"Row {row_idx}: Invalid ASIN '{asin}'")
                continue
            
            # Get or create product
            product_result = get_or_create_product(user_id, asin)
            product = product_result["product"]
            
            if not product:
                results["errors"].append(f"Row {row_idx}: Failed to create product")
                continue
            
            if product_result["created"]:
                results["products_created"] += 1
            
            # Parse buy cost - handle normalized column names
            buy_cost = None
            buy_cost_col = column_mapping.get("buy_cost")
            if buy_cost_col:
                buy_cost_value = row.get(buy_cost_col) or row.get(buy_cost_col.strip().lower())
                if buy_cost_value:
                    try:
                        buy_cost_str = str(buy_cost_value).replace("$", "").replace(",", "").strip()
                        buy_cost = float(buy_cost_str) if buy_cost_str else None
                    except:
                        pass
            
            # Parse MOQ - handle normalized column names
            moq = 1
            moq_col = column_mapping.get("moq")
            if moq_col:
                moq_value = row.get(moq_col) or row.get(moq_col.strip().lower())
                if moq_value:
                    try:
                        moq_str = str(moq_value).replace(",", "").strip()
                        moq = int(moq_str) if moq_str else 1
                        if moq < 1:
                            moq = 1
                    except:
                        pass
            
            # Get or create supplier - handle normalized column names
            supplier_id = None
            supplier_col = column_mapping.get("supplier")
            supplier_name = ""
            
            if supplier_col:
                supplier_value = row.get(supplier_col) or row.get(supplier_col.strip().lower())
                if supplier_value:
                    supplier_name = str(supplier_value).strip()
                    
                    if supplier_name:
                        supplier_lower = supplier_name.lower()
                        if supplier_lower in supplier_name_to_id:
                            supplier_id = supplier_name_to_id[supplier_lower]
                        elif supplier_name in supplier_cache:
                            supplier_id = supplier_cache[supplier_name]
                        else:
                            # Create new supplier
                            supplier_id = get_or_create_supplier(user_id, supplier_name, "csv")
                            if supplier_id:
                                supplier_cache[supplier_name] = supplier_id
                                supplier_name_to_id[supplier_lower] = supplier_id
            
            # Get notes - handle normalized column names
            notes = ""
            notes_col = column_mapping.get("notes")
            if notes_col:
                notes_value = row.get(notes_col) or row.get(notes_col.strip().lower())
                if notes_value:
                    notes = str(notes_value).strip()
            
            # Upsert deal
            deal_result = upsert_deal(product["id"], supplier_id, {
                "buy_cost": buy_cost,
                "moq": moq,
                "source": file_extension.replace(".", "") if file_extension else "csv",
                "source_detail": file.filename,
                "notes": notes
            })
            
            if deal_result["action"] == "created":
                results["deals_created"] += 1
            else:
                results["deals_updated"] += 1
            
        except Exception as e:
            results["errors"].append(f"Row {row_idx}: {str(e)}")
            logger.error(f"Error processing row {row_idx}: {e}")
    
    return results

@router.patch("/deal/{deal_id}")
async def update_deal(deal_id: str, updates: UpdateDealRequest, current_user = Depends(get_current_user)):
    """Update a specific deal."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership via product
        deal = supabase.table("product_sources")\
            .select("*, products!inner(user_id)")\
            .eq("id", deal_id)\
            .limit(1)\
            .execute()
        
        if not deal.data:
            raise HTTPException(404, "Deal not found")
        
        # Check ownership (handle nested structure from join)
        deal_data = deal.data[0]
        product_user_id = deal_data.get("products", {}).get("user_id") if isinstance(deal_data.get("products"), dict) else None
        
        if not product_user_id or product_user_id != user_id:
            raise HTTPException(404, "Deal not found")
        
        update_data = {}
        if updates.buy_cost is not None:
            update_data["buy_cost"] = updates.buy_cost
        if updates.moq is not None:
            update_data["moq"] = updates.moq
        if updates.stage is not None:
            update_data["stage"] = updates.stage
        if updates.notes is not None:
            update_data["notes"] = updates.notes
        if updates.supplier_id is not None:
            update_data["supplier_id"] = updates.supplier_id
        
        if not update_data:
            raise HTTPException(400, "No valid fields to update")
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("product_sources")\
            .update(update_data)\
            .eq("id", deal_id)\
            .execute()
        
        return result.data[0] if result.data else {"error": "Update failed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update deal: {e}")
        raise HTTPException(500, str(e))

@router.post("/bulk-stage")
async def bulk_update_stage(deal_ids: List[str], stage: str, current_user = Depends(get_current_user)):
    """Move multiple deals to a stage."""
    user_id = str(current_user.id)
    
    valid_stages = ["new", "analyzing", "reviewed", "top_products", "buy_list", "ordered"]
    if stage not in valid_stages:
        raise HTTPException(400, f"Invalid stage. Must be one of: {', '.join(valid_stages)}")
    
    try:
        # Get deals that belong to user (batch query)
        deals = supabase.table("product_sources")\
            .select("id, products!inner(user_id)")\
            .in_("id", deal_ids)\
            .execute()
        
        owned_ids = []
        for d in (deals.data or []):
            products = d.get("products", {})
            if isinstance(products, dict) and products.get("user_id") == user_id:
                owned_ids.append(d["id"])
        
        if not owned_ids:
            raise HTTPException(404, "No deals found")
        
        result = supabase.table("product_sources")\
            .update({"stage": stage, "updated_at": datetime.utcnow().isoformat()})\
            .in_("id", owned_ids)\
            .execute()
        
        # If stage is "top_products", trigger Keepa analysis
        if stage == "top_products" and owned_ids:
            from app.tasks.keepa_analysis import batch_analyze_top_products
            
            # Use batch processing for efficiency (processes all products in one task)
            # This is more efficient than queuing individual tasks
            batch_analyze_top_products.delay(owned_ids, user_id)
            logger.info(f"Queued batch Keepa analysis for {len(owned_ids)} products")
        
        return {"updated": len(result.data or []), "stage": stage}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk update stage: {e}")
        raise HTTPException(500, str(e))

@router.post("/analyze")
async def analyze_product(
    request: dict,
    current_user = Depends(get_current_user)
):
    """
    Analyze a single product - forwards to /analyze/single endpoint.
    Accepts: {asin, cost, moq} or {asin, buy_cost, moq}
    """
    from app.api.v1.analysis import ASINInput, analyze_single
    from pydantic import ValidationError
    
    try:
        # Convert request format
        asin = request.get("asin") or request.get("ASIN")
        buy_cost = request.get("cost") or request.get("buy_cost") or request.get("buyCost")
        moq = request.get("moq") or request.get("MOQ") or 1
        
        if not asin or not buy_cost:
            raise HTTPException(400, "Missing required fields: asin and cost/buy_cost")
        
        # Create ASINInput object
        try:
            asin_input = ASINInput(
                asin=asin,
                buy_cost=float(buy_cost),
                moq=int(moq),
                identifier_type="asin"
            )
        except (ValueError, ValidationError) as e:
            raise HTTPException(400, f"Invalid input: {str(e)}")
        
        # Call the actual analysis endpoint
        return await analyze_single(asin_input, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /products/analyze: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to analyze product: {str(e)}")


@router.post("/bulk-analyze")
async def bulk_analyze(req: AnalyzeBatchRequest, current_user = Depends(get_current_user)):
    """
    Queue multiple products for analysis via the batch system.
    Checks suppliers on the SELECTED DEALS, not all deals for those products.
    Analysis runs once per product (ASIN), not per deal.
    """
    user_id = str(current_user.id)
    
    try:
        # Get the SELECTED deals and check if THEY have suppliers
        deals = supabase.table("product_sources")\
            .select("id, product_id, supplier_id, products!inner(id, asin, user_id, status, title)")\
            .in_("id", req.deal_ids)\
            .execute()
        
        if not deals.data:
            raise HTTPException(404, "No deals found")
        
        # Check which SELECTED deals don't have suppliers
        deals_without_suppliers = []
        product_ids = []
        
        for d in deals.data:
            products = d.get("products", {})
            if isinstance(products, dict) and products.get("user_id") == user_id:
                product_id = d["product_id"]
                if product_id not in product_ids:
                    product_ids.append(product_id)
                
                # Check if THIS SPECIFIC DEAL has a supplier
                if not d.get("supplier_id"):
                    deals_without_suppliers.append({
                        "deal_id": d["id"],
                        "product_id": product_id,
                        "asin": products.get("asin"),
                        "title": products.get("title")
                    })
        
        if deals_without_suppliers:
            # Get unique products without suppliers
            products_data = []
            asins = []
            for deal_info in deals_without_suppliers:
                if deal_info["asin"]:
                    products_data.append({
                        "id": deal_info["product_id"],
                        "asin": deal_info["asin"],
                        "title": deal_info.get("title")
                    })
                    asins.append(deal_info["asin"])
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "products_missing_suppliers",
                    "message": f"{len(deals_without_suppliers)} selected deal(s) have no supplier assigned. Please assign a supplier to these deals before analyzing.",
                    "count": len(deals_without_suppliers),
                    "products": products_data,
                    "asins": asins
                }
            )
        
        if not product_ids:
            raise HTTPException(404, "No products found")
        
        # Create job and queue analysis
        from app.tasks.analysis import batch_analyze_products
        from uuid import uuid4
        
        job_id = str(uuid4())
        supabase.table("jobs").insert({
            "id": job_id,
            "user_id": user_id,
            "type": "batch_analyze",
            "status": "pending",
            "total_items": len(product_ids),
            "metadata": {"source_deal_ids": req.deal_ids}
        }).execute()
        
        # Update deals to analyzing stage
        supabase.table("product_sources")\
            .update({"stage": "analyzing", "updated_at": datetime.utcnow().isoformat()})\
            .in_("id", req.deal_ids)\
            .execute()
        
        # Queue Celery task
        batch_analyze_products.delay(job_id, user_id, product_ids)
        
        return {
            "job_id": job_id,
            "queued": len(product_ids),
            "message": f"Started analyzing {len(product_ids)} products"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk analyze: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@router.delete("/deal/{deal_id}")
async def delete_deal(deal_id: str, current_user = Depends(get_current_user)):
    """Soft delete a deal."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        deal = supabase.table("product_sources")\
            .select("id, products!inner(user_id)")\
            .eq("id", deal_id)\
            .limit(1)\
            .execute()
        
        if not deal.data:
            raise HTTPException(404, "Deal not found")
        
        deal_data = deal.data[0]
        products = deal_data.get("products", {})
        if not isinstance(products, dict) or products.get("user_id") != user_id:
            raise HTTPException(404, "Deal not found")
        
        result = supabase.table("product_sources")\
            .update({"is_active": False, "updated_at": datetime.utcnow().isoformat()})\
            .eq("id", deal_id)\
            .execute()
        
        # Invalidate stats cache (product count changed)
        cache_key = f"asin_stats:{user_id}"
        delete_cached(cache_key)
        logger.debug(f"🗑️  Cache invalidated: {cache_key}")
        
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete deal: {e}")
        raise HTTPException(500, str(e))

@router.post("/assign-supplier")
async def assign_supplier_to_products(
    request: dict,
    current_user = Depends(get_current_user)
):
    """
    Bulk assign a supplier to multiple products.
    Creates or updates product_sources for each product.
    
    If assign_all_pending is True, assigns supplier to all products without suppliers.
    Otherwise, requires product_ids.
    """
    user_id = str(current_user.id)
    supplier_id = request.get("supplier_id")
    assign_all_pending = request.get("assign_all_pending", False)
    product_ids = request.get("product_ids", [])
    
    if not supplier_id:
        raise HTTPException(400, "supplier_id is required")
    
    # If assign_all_pending, find all products without suppliers
    if assign_all_pending:
        try:
            # Get all products for this user
            all_products = supabase.table("products")\
                .select("id")\
                .eq("user_id", user_id)\
                .execute()
            
            all_product_ids = [p["id"] for p in (all_products.data or [])]
            
            if not all_product_ids:
                return {
                    "message": "No products found",
                    "updated": 0,
                    "created": 0,
                    "total": 0
                }
            
            logger.info(f"Found {len(all_product_ids)} total products for user {user_id}")
            
            # Get all product_sources with suppliers
            # Fetch in batches to avoid URL length limits
            products_with_suppliers = set()
            BATCH_SIZE = 100
            
            for i in range(0, len(all_product_ids), BATCH_SIZE):
                batch_ids = all_product_ids[i:i + BATCH_SIZE]
                try:
                    sources_with_suppliers = supabase.table("product_sources")\
                        .select("product_id, supplier_id")\
                        .in_("product_id", batch_ids)\
                        .execute()
                    
                    if sources_with_suppliers.data:
                        for source in sources_with_suppliers.data:
                            if source.get("supplier_id"):  # Not null
                                products_with_suppliers.add(source["product_id"])
                except Exception as e:
                    logger.warning(f"Error fetching suppliers for batch {i//BATCH_SIZE + 1}: {e}")
                    # Continue with other batches
            
            logger.info(f"Found {len(products_with_suppliers)} products with suppliers")
            
            # Find products without suppliers
            product_ids = [pid for pid in all_product_ids if pid not in products_with_suppliers]
            
            logger.info(f"Found {len(product_ids)} products without suppliers")
            
            if not product_ids:
                return {
                    "message": "All products already have suppliers assigned",
                    "updated": 0,
                    "created": 0,
                    "total": 0
                }
        except Exception as e:
            logger.error(f"Error finding products without suppliers: {e}", exc_info=True)
            raise HTTPException(500, f"Error finding products: {str(e)}")
    
    if not product_ids:
        raise HTTPException(400, "product_ids is required or assign_all_pending must be true")
    
    # Verify supplier belongs to user
    supplier_check = supabase.table("suppliers")\
        .select("id")\
        .eq("id", supplier_id)\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()
    
    if not supplier_check.data:
        raise HTTPException(400, "Invalid supplier")
    
    # Get products to verify ownership - batch to avoid URL length limits
    verified_product_ids = []
    BATCH_SIZE = 100
    
    try:
        for i in range(0, len(product_ids), BATCH_SIZE):
            batch_ids = product_ids[i:i + BATCH_SIZE]
            products_result = supabase.table("products")\
                .select("id, asin")\
                .eq("user_id", user_id)\
                .in_("id", batch_ids)\
                .execute()
            
            if products_result.data:
                verified_product_ids.extend([p["id"] for p in products_result.data])
    except Exception as e:
        logger.error(f"Error verifying products: {e}", exc_info=True)
        raise HTTPException(500, f"Error verifying products: {str(e)}")
    
    if len(verified_product_ids) != len(product_ids):
        logger.warning(f"Only verified {len(verified_product_ids)} of {len(product_ids)} products")
        # Continue with verified products instead of failing
    
    if not verified_product_ids:
        raise HTTPException(400, "No valid products found")
    
    updated_count = 0
    created_count = 0
    errors = []
    
    # Process in batches to avoid overwhelming the database
    for i in range(0, len(verified_product_ids), BATCH_SIZE):
        batch_product_ids = verified_product_ids[i:i + BATCH_SIZE]
        
        for product_id in batch_product_ids:
            try:
                # Check if product_source exists without supplier
                existing_source = supabase.table("product_sources")\
                    .select("id")\
                    .eq("product_id", product_id)\
                    .is_("supplier_id", "null")\
                    .limit(1)\
                    .execute()
                
                if existing_source.data:
                    # Update existing source with supplier
                    supabase.table("product_sources")\
                        .update({
                            "supplier_id": supplier_id,
                            "updated_at": datetime.utcnow().isoformat()
                        })\
                        .eq("id", existing_source.data[0]["id"])\
                        .execute()
                    updated_count += 1
                else:
                    # Check if source with this supplier already exists
                    check_existing = supabase.table("product_sources")\
                        .select("id")\
                        .eq("product_id", product_id)\
                        .eq("supplier_id", supplier_id)\
                        .limit(1)\
                        .execute()
                    
                    if not check_existing.data:
                        # Create new product_source
                        supabase.table("product_sources").insert({
                            "product_id": product_id,
                            "supplier_id": supplier_id,
                            "buy_cost": None,
                            "moq": 1,
                            "source": "manual",
                            "source_detail": "Bulk assigned",
                            "stage": "new",
                            "is_active": True
                        }).execute()
                        created_count += 1
            except Exception as e:
                logger.error(f"Error assigning supplier to product {product_id}: {e}")
                errors.append(f"Product {product_id}: {str(e)}")
                # Continue with other products
    
    return {
        "message": f"Assigned supplier to {updated_count + created_count} products",
        "updated": updated_count,
        "created": created_count,
        "total": updated_count + created_count,
        "errors": errors if errors else None
    }

@router.get("/export")
async def export_deals(
    stage: Optional[str] = None,
    source: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Export deals as CSV data."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("product_deals")\
            .select("*")\
            .eq("user_id", user_id)
        
        if stage:
            query = query.eq("stage", stage)
        if source:
            query = query.eq("source", source)
        
        result = query.order("deal_created_at", desc=True).execute()
        deals = result.data or []
        
        export = []
        for d in deals:
            export.append({
                "asin": d.get("asin"),
                "title": d.get("title"),
                "supplier": d.get("supplier_name", "Unknown"),
                "buy_cost": d.get("buy_cost"),
                "moq": d.get("moq"),
                "sell_price": d.get("sell_price"),
                "fees": d.get("fees_total"),
                "profit": d.get("profit"),
                "roi": d.get("roi"),
                "total_investment": d.get("total_investment"),
                "stage": d.get("stage"),
                "source": d.get("source"),
                "source_detail": d.get("source_detail"),
                "notes": d.get("notes")
            })
        
        return {"rows": export}
    except Exception as e:
        logger.error(f"Failed to export deals: {e}")
        raise HTTPException(500, str(e))

@router.get("/keepa-analysis/{asin}")
async def get_keepa_analysis(asin: str, current_user = Depends(get_current_user)):
    """
    Get Keepa analysis results for a product.
    Returns detailed price history, worst-case profit, and market data.
    """
    user_id = str(current_user.id)
    asin = asin.strip().upper()
    
    try:
        # Verify product belongs to user
        product = supabase.table("products")\
            .select("id, asin, sell_price, fees_total")\
            .eq("asin", asin)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product.data:
            raise HTTPException(404, "Product not found")
        
        # Get Keepa analysis
        analysis_result = supabase.table("keepa_analysis")\
            .select("*")\
            .eq("asin", asin)\
            .single()\
            .execute()
        
        if not analysis_result.data:
            return {
                "asin": asin,
                "analyzed": False,
                "message": "Keepa analysis not yet available. Move product to TOP PRODUCTS stage to trigger analysis."
            }
        
        analysis = analysis_result.data
        product_data = product.data
        
        # Get product_source for profit calculation
        product_source = supabase.table("product_sources")\
            .select("buy_cost, moq")\
            .eq("product_id", product_data["id"])\
            .limit(1)\
            .execute()
        
        source_data = product_source.data[0] if product_source.data else {}
        
        # Calculate worst-case profit if we have the data
        worst_case = None
        if analysis.get("lowest_fba_price_12m"):
            from app.services.keepa_analysis_service import keepa_analysis_service
            
            worst_case = keepa_analysis_service.calculate_worst_case_profit(
                lowest_fba_price=float(analysis["lowest_fba_price_12m"]),
                supplier_cost=float(source_data.get("buy_cost", 0) or 0),
                fba_fees=float(product_data.get("fees_total", 0) or 0)
            )
        
        return {
            "asin": asin,
            "analyzed": True,
            "analyzed_at": analysis.get("analyzed_at"),
            "lowest_fba_price_12m": analysis.get("lowest_fba_price_12m"),
            "lowest_fba_date": analysis.get("lowest_fba_date"),
            "lowest_fba_seller": analysis.get("lowest_fba_seller"),
            "current_fba_price": analysis.get("current_fba_price"),
            "current_fbm_price": analysis.get("current_fbm_price"),
            "fba_seller_count": analysis.get("fba_seller_count", 0),
            "fbm_seller_count": analysis.get("fbm_seller_count", 0),
            "current_sales_rank": analysis.get("current_sales_rank"),
            "avg_sales_rank_90d": analysis.get("avg_sales_rank_90d"),
            "price_range_12m": analysis.get("price_range_12m"),
            "price_volatility": analysis.get("price_volatility"),
            "worst_case_analysis": worst_case or (analysis.get("worst_case_profit") and {
                "worst_case_profit": analysis.get("worst_case_profit"),
                "worst_case_margin": analysis.get("worst_case_margin"),
                "still_profitable": analysis.get("still_profitable")
            }),
            "raw_responses": {
                "basic": analysis.get("raw_basic_response"),
                "offers": analysis.get("raw_offers_response")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Keepa analysis: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.patch("/{product_id}/asin")
async def set_product_asin(
    product_id: str,
    request: dict,
    current_user = Depends(get_current_user)
):
    """
    Manually set ASIN for a product that doesn't have one.
    Updates product and changes product_sources stage to 'new' (ready for analysis).
    """
    user_id = str(current_user.id)
    asin = request.get("asin", "").strip().upper()
    
    if not asin:
        raise HTTPException(400, "ASIN is required")
    
    if len(asin) != 10:
        raise HTTPException(400, "ASIN must be 10 characters")
    
    try:
        # Verify product belongs to user
        product = supabase.table("products")\
            .select("id, asin, asin_status")\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not product.data:
            raise HTTPException(404, "Product not found")
        
        product_data = product.data[0]
        
        # Check if ASIN already exists for another product
        existing = supabase.table("products")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("asin", asin)\
            .neq("id", product_id)\
            .limit(1)\
            .execute()
        
        if existing.data:
            raise HTTPException(400, f"ASIN {asin} is already assigned to another product")
        
        # Update product
        update_data = {
            "asin": asin,
            "asin_status": "manual",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("products")\
            .update(update_data)\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to update product")
        
        # Update product_sources stage to 'new' (ready for analysis)
        supabase.table("product_sources")\
            .update({
                "stage": "new",
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("product_id", product_id)\
            .execute()
        
        return {
            "success": True,
            "asin": asin,
            "message": "ASIN set successfully. Product is now ready for analysis."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set ASIN for product {product_id}: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@router.get("/{asin}/variations")
async def get_product_variations(
    asin: str,
    current_user=Depends(get_current_user)
):
    """
    Get product variations (parent/child relationships) for an ASIN.
    
    Uses SP-API catalog to find variation relationships and returns
    variation ASINs with their titles and prices.
    
    Args:
        asin: Amazon ASIN to get variations for
        
    Returns:
        List of variation objects with asin, title, price, image_url
    """
    from app.services.sp_api_client import sp_api_client
    
    try:
        marketplace_id = "ATVPDKIKX0DER"  # Default to US
        
        # Get raw catalog item data to access relationships
        # We need the raw response, not the simplified version
        if not sp_api_client.app_configured:
            return {"variations": []}
        
        # Get raw catalog data with relationships included
        raw_catalog = await sp_api_client._request(
            "GET",
            f"/catalog/2022-04-01/items/{asin}",
            marketplace_id,
            limiter_name="catalog",
            params={
                "marketplaceIds": marketplace_id,
                "includedData": "summaries,images,relationships"
            }
        )
        
        if not raw_catalog:
            return {"variations": []}
        
        # Extract variation ASINs from relationships
        variation_asins = []
        items = raw_catalog.get("items", [])
        
        if items:
            item = items[0]
            relationships = item.get("relationships", [])
            
            for relationship in relationships:
                if relationship.get("type") == "VARIATION":
                    # Get child ASINs (if this is a parent)
                    child_asins = relationship.get("childAsins", [])
                    if child_asins:
                        variation_asins.extend(child_asins)
                    # Get parent ASIN (if this is a child)
                    parent_asin = relationship.get("parentAsin")
                    if parent_asin:
                        # Fetch parent to get all siblings
                        parent_raw = await sp_api_client._request(
                            "GET",
                            f"/catalog/2022-04-01/items/{parent_asin}",
                            marketplace_id,
                            limiter_name="catalog",
                            params={
                                "marketplaceIds": marketplace_id,
                                "includedData": "summaries,images,relationships"
                            }
                        )
                        if parent_raw and parent_raw.get("items"):
                            parent_item = parent_raw["items"][0]
                            for rel in parent_item.get("relationships", []):
                                if rel.get("type") == "VARIATION":
                                    sibling_asins = rel.get("childAsins", [])
                                    variation_asins.extend(sibling_asins)
        
        # Remove duplicates and the original ASIN
        variation_asins = list(set(variation_asins))
        if asin in variation_asins:
            variation_asins.remove(asin)
        
        if not variation_asins:
            return {"variations": []}
        
        # Limit to first 20 variations to avoid too many API calls
        variation_asins = variation_asins[:20]
        variations = []
        
        # Get catalog data for each variation ASIN
        for var_asin in variation_asins:
            try:
                var_catalog = await sp_api_client.get_catalog_item(var_asin, marketplace_id)
                if var_catalog:
                    # Get price from competitive pricing
                    price = None
                    try:
                        pricing = await sp_api_client.get_competitive_pricing(var_asin, marketplace_id)
                        if pricing and "buy_box_price" in pricing:
                            price = pricing["buy_box_price"]
                    except:
                        pass  # Price is optional
                    
                    variations.append({
                        "asin": var_asin,
                        "title": var_catalog.get("title") or f"Variation {var_asin}",
                        "price": price,
                        "image_url": var_catalog.get("image_url")
                    })
            except Exception as e:
                logger.warning(f"Failed to get catalog for variation {var_asin}: {e}")
                # Still add the variation with minimal data
                variations.append({
                    "asin": var_asin,
                    "title": f"Variation {var_asin}",
                    "price": None,
                    "image_url": None
                })
        
        return {"variations": variations}
        
    except Exception as e:
        logger.error(f"Failed to get variations for {asin}: {e}", exc_info=True)
        # Return empty list on error rather than failing
        return {"variations": []}


# ============================================
# ASIN SELECTION & MANUAL ENTRY ENDPOINTS
# ============================================

class SelectASINRequest(BaseModel):
    asin: str  # The chosen ASIN from potential_asins

@router.post("/{product_id}/select-asin")
async def select_asin(
    product_id: str,
    request: SelectASINRequest,
    current_user = Depends(get_current_user)
):
    """
    User selects one ASIN from multiple options.
    
    This endpoint is called when asin_status = 'multiple_found'
    and user clicks on one of the potential ASINs.
    """
    user_id = str(current_user.id)
    
    try:
        # Get product
        product_result = supabase.table("products")\
            .select("*")\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product_result.data:
            raise HTTPException(404, "Product not found")
        
        product = product_result.data
        
        if product.get('asin_status') != 'multiple_found':
            raise HTTPException(400, "Product does not need ASIN selection")
        
        # Validate selected ASIN is in potential_asins
        potential_asins = product.get('potential_asins') or []
        if not isinstance(potential_asins, list):
            potential_asins = []
        
        selected_asin_data = next(
            (a for a in potential_asins if isinstance(a, dict) and a.get('asin') == request.asin),
            None
        )
        
        if not selected_asin_data:
            raise HTTPException(400, "Selected ASIN not in potential ASINs")
        
        # Update product with selected ASIN
        update_data = {
            "asin": request.asin,
            "asin_status": "found",
            "title": selected_asin_data.get('title'),
            "brand": selected_asin_data.get('brand'),
            "image_url": selected_asin_data.get('image'),
            "potential_asins": None,  # Clear this now
            "updated_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("products")\
            .update(update_data)\
            .eq("id", product_id)\
            .execute()
        
        # Update product_source stage to trigger analysis
        supabase.table("product_sources")\
            .update({"stage": "new"})\
            .eq("product_id", product_id)\
            .execute()
        
        # Get parent ASIN from Keepa (optional but recommended)
        # Note: Keepa client may not return parent_asin yet - this is a placeholder
        # TODO: Update when Keepa client is enhanced to return variation data
        try:
            from app.services.keepa_client import get_keepa_client
            from app.tasks.base import run_async
            
            keepa_client = get_keepa_client()
            keepa_data = run_async(keepa_client.get_product(request.asin, days=90))
            
            # Keepa data structure may vary - check for parent_asin field
            # If Keepa client doesn't provide this yet, we'll skip it
            if keepa_data:
                parent_asin = keepa_data.get('parent_asin') or keepa_data.get('parentAsin')
                if parent_asin:
                    variation_count = keepa_data.get('variation_count') or len(keepa_data.get('variations', [])) or 1
                    supabase.table("products")\
                        .update({
                            "parent_asin": parent_asin,
                            "is_variation": True,
                            "variation_count": variation_count
                        })\
                        .eq("id", product_id)\
                        .execute()
        except Exception as e:
            logger.debug(f"Could not get Keepa variation data for {request.asin}: {e}")
        
        # Queue for analysis using batch_analyze_products with single product
        try:
            from app.tasks.analysis import batch_analyze_products
            from uuid import uuid4
            
            analysis_job_id = str(uuid4())
            supabase.table("jobs").insert({
                "id": analysis_job_id,
                "user_id": user_id,
                "type": "batch_analyze",
                "status": "pending",
                "total_items": 1,
                "metadata": {
                    "triggered_by": "asin_selection",
                    "product_id": product_id
                }
            }).execute()
            
            batch_analyze_products.delay(analysis_job_id, user_id, [product_id])
        except Exception as e:
            logger.warning(f"Could not queue analysis for {product_id}: {e}")
        
        return {
            "success": True,
            "message": "ASIN selected and queued for analysis",
            "asin": request.asin
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting ASIN for product {product_id}: {e}", exc_info=True)
        raise HTTPException(500, str(e))


class ManualASINRequest(BaseModel):
    asin: str  # User-entered ASIN

@router.patch("/{product_id}/manual-asin")
async def set_manual_asin(
    product_id: str,
    request: ManualASINRequest,
    current_user = Depends(get_current_user)
):
    """
    User manually enters ASIN for a product.
    
    Called when asin_status = 'not_found' and user types in ASIN.
    """
    user_id = str(current_user.id)
    
    try:
        # Get product
        product_result = supabase.table("products")\
            .select("*")\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product_result.data:
            raise HTTPException(404, "Product not found")
        
        product = product_result.data
        
        if product.get('asin_status') not in ['not_found', 'manual']:
            raise HTTPException(400, "Product already has ASIN")
        
        # Validate ASIN format
        asin = request.asin.strip().upper()
        if len(asin) != 10:
            raise HTTPException(400, "ASIN must be 10 characters")
        
        # Try to get product info from Amazon
        try:
            from app.services.keepa_client import get_keepa_client
            from app.services.sp_api_client import sp_api_client
            from app.tasks.base import run_async
            
            # Try Keepa first
            keepa_client = get_keepa_client()
            keepa_data = run_async(keepa_client.get_product(asin, days=90))
            
            update_data = {
                "asin": asin,
                "asin_status": "manual",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if keepa_data:
                parent_asin = keepa_data.get('parent_asin') or keepa_data.get('parentAsin')
                variation_count = keepa_data.get('variation_count') or len(keepa_data.get('variations', [])) or 1
                
                update_data.update({
                    "title": keepa_data.get('title'),
                    "brand": keepa_data.get('brand'),
                    "image_url": keepa_data.get('image_url') or keepa_data.get('image')
                })
                
                if parent_asin:
                    update_data.update({
                        "parent_asin": parent_asin,
                        "is_variation": True,
                        "variation_count": variation_count
                    })
            else:
                # Fallback to SP-API
                catalog_data = await sp_api_client.get_catalog_item(asin)
                if catalog_data:
                    update_data.update({
                        "title": catalog_data.get('title'),
                        "brand": catalog_data.get('brand'),
                        "image_url": catalog_data.get('image_url')
                    })
            
            supabase.table("products")\
                .update(update_data)\
                .eq("id", product_id)\
                .execute()
                
        except Exception as e:
            logger.warning(f"Could not verify ASIN {asin}: {e}")
            # Save anyway
            supabase.table("products")\
                .update({
                    "asin": asin,
                    "asin_status": "manual",
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", product_id)\
                .execute()
        
        # Update stage and queue for analysis
        supabase.table("product_sources")\
            .update({"stage": "new"})\
            .eq("product_id", product_id)\
            .execute()
        
        # Queue for analysis using batch_analyze_products with single product
        try:
            from app.tasks.analysis import batch_analyze_products
            from uuid import uuid4
            
            analysis_job_id = str(uuid4())
            supabase.table("jobs").insert({
                "id": analysis_job_id,
                "user_id": user_id,
                "type": "batch_analyze",
                "status": "pending",
                "total_items": 1,
                "metadata": {
                    "triggered_by": "asin_selection",
                    "product_id": product_id
                }
            }).execute()
            
            batch_analyze_products.delay(analysis_job_id, user_id, [product_id])
        except Exception as e:
            logger.warning(f"Could not queue analysis for {product_id}: {e}")
        
        return {
            "success": True,
            "message": "ASIN set and queued for analysis",
            "asin": asin
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting manual ASIN for product {product_id}: {e}", exc_info=True)
        raise HTTPException(500, str(e))


class MoveToOrdersRequest(BaseModel):
    quantity: Optional[int] = None  # If not provided, use MOQ


class BulkActionRequest(BaseModel):
    action: str  # 'favorite', 'unfavorite', 'move_to_orders', 'delete'
    product_ids: List[str]


@router.patch("/deal/{deal_id}/favorite")
async def toggle_favorite(
    deal_id: str,
    current_user=Depends(get_current_user)
):
    """
    Toggle product favorite status via deal_id.
    """
    user_id = str(current_user.id)
    
    # Get product_source (deal) to find product_id
    deal_result = supabase.table('product_sources') \
        .select('product_id') \
        .eq('id', deal_id) \
        .execute()
    
    if not deal_result.data:
        raise HTTPException(404, "Deal not found")
    
    product_id = deal_result.data[0]['product_id']
    
    # Get current product
    result = supabase.table('products') \
        .select('id, is_favorite') \
        .eq('id', product_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Product not found")
    
    current_favorite = result.data.get('is_favorite', False)
    
    # Toggle favorite
    supabase.table('products').update({
        'is_favorite': not current_favorite,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', product_id).execute()
    
    logger.info(f"{'⭐ Added to' if not current_favorite else '❌ Removed from'} favorites: {product_id}")
    
    return {
        'success': True,
        'is_favorite': not current_favorite
    }


@router.post("/deal/{deal_id}/move-to-orders")
async def move_to_orders(
    deal_id: str,
    request: MoveToOrdersRequest,
    current_user=Depends(get_current_user)
):
    """
    Move product to orders (ready to order from supplier).
    Creates an order item or updates existing order.
    """
    user_id = str(current_user.id)
    
    # Get deal (product_source) with product and supplier info
    deal_result = supabase.table('product_sources') \
        .select('*, product:products(*), supplier:suppliers(*)') \
        .eq('id', deal_id) \
        .execute()
    
    if not deal_result.data:
        raise HTTPException(404, "Deal not found")
    
    deal = deal_result.data[0]
    product = deal.get('product', {})
    supplier_id = deal.get('supplier_id')
    
    if not supplier_id:
        raise HTTPException(400, "Product must have a supplier to add to orders")
    
    # Check if there's an active order for this supplier
    active_order = None
    order_result = supabase.table('orders') \
        .select('*') \
        .eq('user_id', user_id) \
        .eq('supplier_id', supplier_id) \
        .eq('status', 'draft') \
        .execute()
    
    if order_result.data:
        active_order = order_result.data[0]
    
    # Create order if needed
    if not active_order:
        order_data = {
            'user_id': user_id,
            'supplier_id': supplier_id,
            'status': 'draft',
            'created_at': datetime.utcnow().isoformat()
        }
        
        order_result = supabase.table('orders').insert(order_data).execute()
        active_order = order_result.data[0]
        
        logger.info(f"📦 Created new order: {active_order['id']}")
    
    # Add product to order (or update quantity)
    order_item_result = supabase.table('order_items') \
        .select('*') \
        .eq('order_id', active_order['id']) \
        .eq('product_id', product['id']) \
        .execute()
    
    if order_item_result.data:
        # Update quantity
        current_qty = order_item_result.data[0]['quantity']
        new_qty = request.quantity if request.quantity else current_qty + (deal.get('moq', 1))
        
        supabase.table('order_items').update({
            'quantity': new_qty,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', order_item_result.data[0]['id']).execute()
        
        logger.info(f"✅ Updated order item quantity: {current_qty} → {new_qty}")
    else:
        # Create new order item
        order_item_data = {
            'order_id': active_order['id'],
            'product_id': product['id'],
            'quantity': request.quantity or deal.get('moq', 1),
            'unit_cost': deal.get('buy_cost', 0),
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('order_items').insert(order_item_data).execute()
        
        logger.info(f"✅ Added to order: {product['id']}")
    
    # Update deal stage
    supabase.table('product_sources').update({
        'stage': 'ordered',
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', deal_id).execute()
    
    supplier_name = deal.get('supplier', {}).get('name', 'supplier') if deal.get('supplier') else 'supplier'
    
    return {
        'success': True,
        'order_id': active_order['id'],
        'message': f'Added to order for {supplier_name}'
    }


@router.post("/bulk-action")
async def bulk_action(
    request: BulkActionRequest,
    current_user=Depends(get_current_user)
):
    """
    Perform bulk action on multiple products.
    Actions: favorite, unfavorite, move_to_orders, delete
    """
    user_id = str(current_user.id)
    
    action = request.action
    deal_ids = request.product_ids  # These are actually deal_ids (product_source.id)
    
    if not deal_ids:
        raise HTTPException(400, "No products selected")
    
    # Get all deals with products and suppliers
    deals_result = supabase.table('product_sources') \
        .select('*, product:products(*), supplier:suppliers(*)') \
        .in_('id', deal_ids) \
        .execute()
    
    if not deals_result.data or len(deals_result.data) != len(deal_ids):
        raise HTTPException(403, "Some products don't belong to you or not found")
    
    # Verify all products belong to user
    product_ids = [d.get('product', {}).get('id') for d in deals_result.data if d.get('product')]
    products_result = supabase.table('products') \
        .select('*') \
        .in_('id', product_ids) \
        .eq('user_id', user_id) \
        .execute()
    
    if len(products_result.data) != len(product_ids):
        raise HTTPException(403, "Some products don't belong to you")
    
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    if action == 'favorite':
        # Add to favorites
        supabase.table('products').update({
            'is_favorite': True,
            'updated_at': datetime.utcnow().isoformat()
        }).in_('id', product_ids).execute()
        
        results['success'] = len(product_ids)
        
    elif action == 'unfavorite':
        # Remove from favorites
        supabase.table('products').update({
            'is_favorite': False,
            'updated_at': datetime.utcnow().isoformat()
        }).in_('id', product_ids).execute()
        
        results['success'] = len(product_ids)
        
    elif action == 'move_to_orders':
        # Group by supplier
        by_supplier = {}
        for deal in deals_result.data:
            supplier_id = deal.get('supplier_id', 'no_supplier')
            if supplier_id not in by_supplier:
                by_supplier[supplier_id] = []
            by_supplier[supplier_id].append(deal)
        
        # Create/update orders for each supplier
        for supplier_id, supplier_deals in by_supplier.items():
            try:
                # Get or create order
                if supplier_id != 'no_supplier':
                    order_result = supabase.table('orders') \
                        .select('*') \
                        .eq('user_id', user_id) \
                        .eq('supplier_id', supplier_id) \
                        .eq('status', 'draft') \
                        .execute()
                    
                    if order_result.data:
                        order = order_result.data[0]
                    else:
                        order_data = {
                            'user_id': user_id,
                            'supplier_id': supplier_id,
                            'status': 'draft',
                            'created_at': datetime.utcnow().isoformat()
                        }
                        order_result = supabase.table('orders').insert(order_data).execute()
                        order = order_result.data[0]
                else:
                    # Create order without supplier
                    order_data = {
                        'user_id': user_id,
                        'status': 'draft',
                        'created_at': datetime.utcnow().isoformat()
                    }
                    order_result = supabase.table('orders').insert(order_data).execute()
                    order = order_result.data[0]
                
                # Add products to order
                for deal in supplier_deals:
                    product = deal.get('product', {})
                    if not product or not product.get('id'):
                        continue
                    
                    # Check if item already exists
                    existing_item = supabase.table('order_items') \
                        .select('*') \
                        .eq('order_id', order['id']) \
                        .eq('product_id', product['id']) \
                        .execute()
                    
                    if existing_item.data:
                        # Update quantity
                        current_qty = existing_item.data[0]['quantity']
                        new_qty = current_qty + deal.get('moq', 1)
                        supabase.table('order_items').update({
                            'quantity': new_qty,
                            'updated_at': datetime.utcnow().isoformat()
                        }).eq('id', existing_item.data[0]['id']).execute()
                    else:
                        # Create new order item
                        order_item_data = {
                            'order_id': order['id'],
                            'product_id': product['id'],
                            'quantity': deal.get('moq', 1),
                            'unit_cost': deal.get('buy_cost', 0),
                            'created_at': datetime.utcnow().isoformat()
                        }
                        supabase.table('order_items').insert(order_item_data).execute()
                    
                    # Update deal stage
                    supabase.table('product_sources').update({
                        'stage': 'ordered',
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', deal['id']).execute()
                
                results['success'] += len(supplier_deals)
                
            except Exception as e:
                logger.error(f"Failed to add products to order: {e}")
                results['failed'] += len(supplier_deals)
                results['errors'].append(str(e))
        
    elif action == 'delete':
        # Delete product_sources (deals) - products remain
        supabase.table('product_sources').delete().in_('id', deal_ids).execute()
        results['success'] = len(deal_ids)
    
    else:
        raise HTTPException(400, f"Invalid action: {action}")
    
    # Invalidate stats cache if products were modified
    if action in ['delete', 'move_to_orders']:
        cache_key = f"asin_stats:{user_id}"
        delete_cached(cache_key)
        logger.debug(f"🗑️  Cache invalidated after bulk action '{action}': {cache_key}")
    
    logger.info(f"✅ Bulk action '{action}': {results['success']} succeeded, {results['failed']} failed")
    
    return results
