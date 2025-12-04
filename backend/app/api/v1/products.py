"""
Products API - Parent-Child Model (products + product_sources)
Optimized with Redis caching and query batching.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from app.tasks.file_processing import process_file_upload
import base64
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.redis_client import cached
import uuid
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import csv
import io
import logging
import os
import json
import openai
import pandas as pd
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

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
@router.get("/deals")  # Alias for frontend compatibility
@cached(ttl=10)  # Cache for 10 seconds (reduced from 30 for faster updates)
async def get_deals(
    stage: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    min_roi: Optional[float] = Query(None),
    min_profit: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user = Depends(get_current_user)
):
    """
    Get all deals (product + source combinations) using the view.
    Optimized with Redis caching and single query.
    """
    user_id = str(current_user.id)
    
    try:
        # Use the product_deals view for optimized querying
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
        
        # Log if view returns empty but we expect data (for debugging)
        if len(deals) == 0 and offset == 0:
            logger.debug(f"No deals found for user {user_id} - view might be empty or missing data")
        
        return {"deals": deals, "total": len(deals)}
        
    except Exception as e:
        logger.error(f"Failed to fetch deals: {e}")
        # Check if it's a view missing error
        if "relation" in str(e).lower() and "product_deals" in str(e).lower():
            logger.error("product_deals view does not exist! Please create it in the database.")
            raise HTTPException(500, "Database view missing. Please contact support.")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))

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
async def add_deal(req: AddProductRequest, current_user = Depends(get_current_user)):
    """
    Add a deal (creates product if needed, then creates/updates deal).
    This is the main entry point for adding products.
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
    current_user = Depends(get_current_user)
):
    """
    Upload CSV or Excel file for background processing via Celery.
    ALL products in file will be tied to the selected supplier.
    Returns job_id immediately, processes in background.
    """
    try:
        user_id = str(current_user.id)
        filename = file.filename or "unknown"
        
        # Validate file type
        if not filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(400, "File must be .csv, .xlsx, or .xls")
        
        # Validate supplier belongs to user
        supplier = supabase.table("suppliers")\
            .select("id, name")\
            .eq("id", supplier_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not supplier.data:
            raise HTTPException(400, "Invalid supplier")
        
        # Read and encode file contents
        contents = await file.read()
        contents_b64 = base64.b64encode(contents).decode()
        
        # Create job record
        job_id = str(uuid.uuid4())
        job_type = "file_upload"
        
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
        except Exception as db_error:
            logger.error(f"Failed to create job record: {db_error}")
            # Check if jobs table exists
            error_str = str(db_error)
            if "could not find the table" in error_str.lower() or "PGRST205" in error_str:
                raise HTTPException(500, "jobs table not found. Please run the SQL migration: database/CREATE_UNIFIED_JOBS_TABLE.sql")
            raise HTTPException(500, f"Database error: {error_str}")
        
        # Queue Celery task
        try:
            process_file_upload.delay(job_id, user_id, supplier_id, contents_b64, filename)
        except Exception as celery_error:
            logger.error(f"Failed to queue Celery task: {celery_error}")
            # Update job status to failed
            try:
                supabase.table("jobs").update({
                    "status": "failed",
                    "errors": [f"Failed to queue task: {str(celery_error)}"]
                }).eq("id", job_id).execute()
            except:
                pass
            raise HTTPException(500, f"Failed to start background processing. Is Celery running? Error: {str(celery_error)}")
        
        return {
            "job_id": job_id,
            "message": f"Upload started - assigning to {supplier.data[0]['name']}",
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload endpoint error: {e}", exc_info=True)
        raise HTTPException(500, f"Upload failed: {str(e)}")

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
