"""
Celery tasks for CSV/Excel file processing.
"""
import csv
import io
import re
import base64
from typing import Optional, List, Dict
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase
from app.tasks.base import JobManager
import logging

logger = logging.getLogger(__name__)

try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

BATCH_SIZE = 100


def parse_csv(contents: bytes) -> List[Dict]:
    """Parse CSV with BOM handling."""
    decoded = contents.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    rows = []
    for row in reader:
        normalized = {k.strip().lower(): v for k, v in row.items() if k}
        rows.append(normalized)
    return rows


def parse_excel(contents: bytes) -> List[Dict]:
    """Parse Excel file."""
    if not EXCEL_SUPPORT:
        raise ValueError("Excel not supported. Install openpyxl.")
    
    wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
    ws = wb.active
    
    rows = []
    headers = None
    
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(h).strip().lower() if h else f"col_{j}" for j, h in enumerate(row)]
            continue
        if not any(row):
            continue
        row_dict = {headers[j]: v for j, v in enumerate(row) if j < len(headers)}
        rows.append(row_dict)
    
    wb.close()
    return rows


def parse_asin(row: dict) -> Optional[str]:
    """Extract ASIN from row. Prioritizes ASIN over UPC."""
    # First, try to find ASIN directly
    asin = str(row.get("asin") or row.get("amazon asin") or row.get("product asin") or "").strip().upper()
    
    if len(asin) == 10 and re.match(r'^[A-Z0-9]{10}$', asin):
        return asin
    
    # Search all columns for ASIN pattern
    for value in row.values():
        if value:
            val = str(value).strip().upper()
            if len(val) == 10 and re.match(r'^[A-Z0-9]{10}$', val):
                return val
    return None


def parse_upc(row: dict) -> Optional[str]:
    """Extract UPC/EAN/GTIN from row."""
    from app.services.upc_converter import upc_converter
    
    # Try common UPC column names
    upc = str(row.get("upc") or row.get("ean") or row.get("gtin") or 
              row.get("barcode") or row.get("product upc") or "").strip()
    
    # Normalize and validate
    if upc:
        normalized = upc_converter.normalize_upc(upc)
        if normalized:
            return normalized
    
    # Search all columns for UPC pattern (12-14 digits)
    for value in row.values():
        if value:
            val = str(value).strip().replace("-", "").replace(" ", "")
            if upc_converter.is_valid_upc(val):
                return upc_converter.normalize_upc(val)
    
    return None


def parse_cost(row: dict) -> Optional[float]:
    """Extract cost from row."""
    cost_str = str(row.get("buy_cost") or row.get("buy cost") or row.get("cost") or row.get("price") or row.get("unit cost") or row.get("unit_cost") or "").strip()
    if not cost_str:
        return None
    try:
        return float(cost_str.replace("$", "").replace(",", ""))
    except:
        return None


def parse_moq(row: dict) -> int:
    """Extract MOQ from row with fuzzy column matching."""
    # Try exact matches first
    moq_str = None
    for key in ["moq", "qty", "quantity", "min qty", "min order qty", "minimum order", 
                "min order", "order qty", "order quantity", "min qty", "qty min"]:
        if key in row:
            moq_str = str(row[key] or "").strip()
            if moq_str:
                break
    
    # If not found, search all keys for MOQ-related patterns
    if not moq_str:
        for key, value in row.items():
            key_lower = key.lower()
            if any(term in key_lower for term in ["moq", "min", "qty", "quantity", "order"]):
                moq_str = str(value or "").strip()
                if moq_str and moq_str.lower() not in ["", "n/a", "na", "none", "null"]:
                    break
    
    if not moq_str:
        return 1
    
    try:
        # Remove common prefixes/suffixes
        moq_str = moq_str.replace("$", "").replace(",", "").replace(" ", "")
        # Extract first number found
        numbers = re.findall(r'\d+', moq_str)
        if numbers:
            return max(1, int(float(numbers[0])))
        return 1
    except:
        return 1


def parse_notes(row: dict) -> Optional[str]:
    """Extract notes from row."""
    notes = str(row.get("notes") or row.get("note") or row.get("comments") or "").strip()
    return notes if notes else None


@celery_app.task(bind=True, max_retries=2)
def process_file_upload(self, job_id: str, user_id: str, supplier_id: str, file_contents_b64: str, filename: str):
    """
    Process CSV/Excel file upload.
    file_contents_b64: Base64 encoded file contents (for serialization)
    """
    job = JobManager(job_id)
    
    try:
        # Decode file contents
        contents = base64.b64decode(file_contents_b64)
        
        # Parse file
        job.start()
        
        if filename.lower().endswith('.csv'):
            rows = parse_csv(contents)
        elif filename.lower().endswith(('.xlsx', '.xls')):
            rows = parse_excel(contents)
        else:
            job.fail(f"Unsupported file type: {filename}")
            return
        
        total = len(rows)
        if total == 0:
            job.complete({"message": "No valid rows found"}, success=0, errors=0)
            return
        
        job.update_progress(0, total)
        
        # Caches
        product_cache = {}  # asin -> product_id
        
        results = {
            "products_created": 0,
            "deals_processed": 0,
            "total_rows": total
        }
        error_list = []
        processed = 0
        
        # Process in batches
        for batch_start in range(0, total, BATCH_SIZE):
            # Check for cancellation
            if job.is_cancelled():
                job.complete(results, results["deals_processed"], len(error_list), error_list)
                return
            
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = rows[batch_start:batch_end]
            
            # Parse rows
            parsed_rows = []
            asins = []
            
            for idx, row in enumerate(batch):
                row_num = batch_start + idx + 2
                asin = parse_asin(row)
                
                if not asin:
                    error_list.append(f"Row {row_num}: Invalid ASIN")
                    continue
                
                parsed_rows.append({
                    "asin": asin,
                    "buy_cost": parse_cost(row),
                    "moq": parse_moq(row),
                    "notes": parse_notes(row)
                })
                asins.append(asin)
            
            # Batch get/create products
            unique_asins = list(set([a for a in asins if a and a not in product_cache]))
            
            if unique_asins:
                # Get existing
                existing = supabase.table("products")\
                    .select("id, asin")\
                    .eq("user_id", user_id)\
                    .in_("asin", unique_asins)\
                    .execute()
                
                for p in (existing.data or []):
                    product_cache[p["asin"]] = p["id"]
                
                # Create missing
                missing_asins = [a for a in unique_asins if a not in product_cache]
                if missing_asins:
                    new_products = [{"user_id": user_id, "asin": a, "status": "pending"} for a in missing_asins]
                    created = supabase.table("products").insert(new_products).execute()
                    for p in (created.data or []):
                        product_cache[p["asin"]] = p["id"]
                        results["products_created"] += 1
            
            # Build deals for upsert
            # Use dict to deduplicate by (product_id, supplier_id) - keep last occurrence
            deals_dict = {}
            for parsed in parsed_rows:
                product_id = product_cache.get(parsed["asin"])
                if not product_id:
                    continue
                
                # Use (product_id, supplier_id) as key to deduplicate
                key = (product_id, supplier_id)
                deals_dict[key] = {
                    "product_id": product_id,
                    "supplier_id": supplier_id,
                    "buy_cost": parsed["buy_cost"],
                    "moq": parsed["moq"],
                    "source": "excel" if filename.lower().endswith(('.xlsx', '.xls')) else "csv",
                    "source_detail": filename,
                    "notes": parsed["notes"],
                    "stage": "new",
                    "is_active": True
                }
            
            # Convert dict values to list for upsert (deduplicated)
            deals = list(deals_dict.values())
            
            # Batch upsert deals
            if deals:
                result = supabase.table("product_sources")\
                    .upsert(deals, on_conflict="product_id,supplier_id")\
                    .execute()
                results["deals_processed"] += len(result.data or [])
            
            processed = batch_end
            job.update_progress(processed, total, results["deals_processed"], len(error_list), error_list)
        
        # Complete
        job.complete(results, results["deals_processed"], len(error_list), error_list)
        
        # Auto-analyze uploaded products if requested (optional - can be enabled via metadata)
        # Get product IDs from the uploaded deals
        if results["deals_processed"] > 0:
            try:
                # Get product IDs from product_sources that were just created/updated
                # Query by source_detail (filename) to get the products we just uploaded
                uploaded_products = supabase.table("product_sources")\
                    .select("product_id")\
                    .eq("source_detail", filename)\
                    .eq("supplier_id", supplier_id)\
                    .execute()
                
                if uploaded_products.data:
                    product_ids = list(set([p["product_id"] for p in uploaded_products.data]))
                    
                    # Queue analysis job (optional - check metadata flag)
                    # For now, we'll always auto-analyze. Can be made configurable later.
                    from app.tasks.analysis import batch_analyze_products
                    from uuid import uuid4
                    
                    analysis_job_id = str(uuid4())
                    supabase.table("jobs").insert({
                        "id": analysis_job_id,
                        "user_id": user_id,
                        "type": "batch_analyze",
                        "status": "pending",
                        "total_items": len(product_ids),
                        "metadata": {
                            "triggered_by": "file_upload",
                            "upload_job_id": job_id,
                            "filename": filename
                        }
                    }).execute()
                    
                    # Queue analysis task
                    batch_analyze_products.delay(analysis_job_id, user_id, product_ids)
                    
                    logger.info(f"Auto-queued analysis for {len(product_ids)} products from upload {job_id}")
            except Exception as analysis_error:
                # Don't fail the upload job if auto-analysis fails
                logger.warning(f"Failed to auto-analyze uploaded products: {analysis_error}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job.fail(str(e))
        raise self.retry(exc=e, countdown=60)

