"""
Celery tasks for CSV/Excel file processing.
Supports hardcoded KEHE supplier format with UPC → ASIN conversion.
"""
import csv
import io
import re
import base64
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Tuple
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

# Valid columns in products table - ONLY use these when inserting
VALID_PRODUCT_COLUMNS = {
    'user_id', 'asin', 'title', 'image_url', 'category', 'brand_id', 
    'brand_name', 'sell_price', 'fees_total', 'bsr', 'seller_count',
    'fba_seller_count', 'amazon_sells', 'analysis_id', 'status',
    'upc', 'asin_status', 'brand', 'potential_asins', 'parent_asin',
    'is_variation', 'variation_count', 'variation_theme', 'supplier_title',
    'is_favorite', 'lookup_status', 'lookup_attempts', 'asin_found_at'
}

def clean_product_for_insert(product_dict):
    """
    Remove any keys not in the products table schema.
    This prevents PGRST204 'column not found' errors.
    """
    return {k: v for k, v in product_dict.items() if k in VALID_PRODUCT_COLUMNS}

def normalize_product_batch(products):
    """
    Ensure all products in a batch have exactly the same keys.
    This prevents PGRST102 'All object keys must match' errors.
    """
    if not products:
        return []
    
    # Get union of all keys across all products
    all_keys = set()
    for p in products:
        all_keys.update(p.keys())
    
    # Normalize each product to have all keys (with None for missing)
    normalized = []
    for p in products:
        normalized_product = {key: p.get(key) for key in all_keys}
        normalized.append(normalized_product)
    
    return normalized


def parse_csv(contents: bytes) -> Tuple[List[Dict], List[str]]:
    """Parse CSV with BOM handling. Returns (rows, headers)."""
    decoded = contents.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    original_headers = reader.fieldnames or []
    rows = []
    for row in reader:
        # Store both original and normalized versions
        row_dict = {}
        for key in original_headers:
            value = row.get(key, "")
            row_dict[key] = value  # Original case
            row_dict[key.strip().lower()] = value  # Lowercase for compatibility
        rows.append(row_dict)
    return rows, list(original_headers)


def parse_excel(contents: bytes) -> Tuple[List[Dict], List[str]]:
    """Parse Excel file. Preserves original column names for hardcoded mapping."""
    if not EXCEL_SUPPORT:
        raise ValueError("Excel not supported. Install openpyxl.")
    
    wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
    ws = wb.active
    
    rows = []
    headers = None
    original_headers = None
    
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            original_headers = [str(h).strip() if h else f"col_{j}" for j, h in enumerate(row)]
            headers = [str(h).strip().lower() if h else f"col_{j}" for j, h in enumerate(row)]
            continue
        if not any(row):
            continue
        # Store both original and lowercase versions
        row_dict = {}
        for j, v in enumerate(row):
            if j < len(headers):
                if original_headers[j]:
                    row_dict[original_headers[j]] = v  # Original case
                row_dict[headers[j]] = v  # Lowercase for compatibility
        rows.append(row_dict)
    
    wb.close()
    return rows, original_headers


def is_kehe_format(headers: List[str]) -> bool:
    """Check if this is the KEHE supplier format with hardcoded columns."""
    if not headers:
        return False
    header_set = {h.upper() for h in headers if h}
    # Check for KEHE-specific columns (UPC, WHOLESALE, PACK are key indicators)
    kehe_key_columns = {"UPC", "WHOLESALE", "PACK"}
    return len(kehe_key_columns.intersection(header_set)) >= 2


def parse_supplier_row(row: dict) -> Optional[Dict]:
    """
    Parse a supplier row with UPC and pack size support.
    
    CRITICAL: wholesale_cost is for entire case, buy_cost is per unit.
    buy_cost = wholesale_cost / pack_size
    """
    try:
        # Get UPC
        upc = row.get("UPC") or row.get("upc")
        if not upc:
            return None
        
        # Convert UPC to string and clean
        upc_str = str(upc).strip().replace("-", "").replace(" ", "").replace(".0", "")
        if len(upc_str) < 8:
            return None
        
        # Extract supplier_sku (ITEM column)
        supplier_sku = row.get("ITEM") or row.get("item")
        if supplier_sku:
            supplier_sku = str(supplier_sku).strip()
        else:
            supplier_sku = None
        
        # Extract pack_size (PACK column) - units per case
        pack_size = 1
        pack = row.get("PACK") or row.get("pack")
        if pack is not None:
            try:
                pack_val = str(pack).replace(",", "").strip().replace(".0", "")
                pack_size = max(1, int(float(pack_val)))
            except (ValueError, TypeError):
                pack_size = 1
        
        # Extract wholesale_cost (WHOLESALE column) - cost for ENTIRE case
        wholesale_cost = None
        wholesale = row.get("WHOLESALE") or row.get("wholesale")
        if wholesale is not None:
            try:
                wholesale_cost = float(str(wholesale).replace("$", "").replace(",", "").strip())
            except (ValueError, TypeError):
                pass
        
        # CRITICAL: Calculate buy_cost (per unit)
        buy_cost = None
        if wholesale_cost is not None and pack_size > 0:
            buy_cost = round(wholesale_cost / pack_size, 4)
        
        # Extract PROMO QTY (Column N) - min cases for discount (can be 0 or None)
        promo_qty = None
        promo_raw = row.get("PROMO QTY") or row.get("PROMO_QTY") or row.get("promo_qty")
        if promo_raw is not None:
            try:
                promo_qty = int(float(str(promo_raw).replace(",", "").strip()))
                if promo_qty < 0:
                    promo_qty = None
            except (ValueError, TypeError):
                pass
        
        # Extract TOTAL PROMO % (Column R) - discount percent
        promo_percent = None
        promo_pct_raw = row.get("TOTAL PROMO %") or row.get("TOTAL_PROMO_%") or row.get("TOTAL PROMO") or row.get("total_promo_%") or row.get("PROMO %") or row.get("PROMO_%")
        if promo_pct_raw is not None:
            try:
                pct_str = str(promo_pct_raw).replace("%", "").strip()
                promo_percent = float(pct_str)
                # Handle decimal format (0.65 -> 65)
                if 0 < promo_percent < 1:
                    promo_percent = promo_percent * 100
            except (ValueError, TypeError):
                pass
        
        # Calculate promo pricing
        # has_promo = TRUE if promo_percent exists (even if promo_qty is 0 or None)
        promo_wholesale_cost = None
        promo_buy_cost = None
        has_promo = False
        
        if promo_percent and promo_percent > 0 and wholesale_cost:
            has_promo = True
            # Promo wholesale = wholesale × (1 - discount)
            promo_wholesale_cost = round(wholesale_cost * (1 - promo_percent / 100), 2)
            if pack_size > 0:
                promo_buy_cost = round(promo_wholesale_cost / pack_size, 4)
        
        # Extract brand
        brand = row.get("BRAND") or row.get("brand") or ""
        if brand:
            brand = str(brand).strip()
        else:
            brand = None
        
        # Extract title/description
        title = row.get("DESCRIPTION") or row.get("description") or ""
        if title:
            title = str(title).strip()
        else:
            title = None
        
        # Build notes from description and brand
        notes_parts = []
        if title:
            notes_parts.append(title)
        if brand:
            notes_parts.append(f"Brand: {brand}")
        notes = " | ".join(notes_parts) if notes_parts else None
        
        return {
            "upc": upc_str,
            "supplier_sku": supplier_sku,
            "pack_size": pack_size,
            "wholesale_cost": wholesale_cost,
            "buy_cost": buy_cost,  # Per-unit cost for analysis
            "promo_qty": promo_qty,
            "promo_percent": promo_percent,
            "promo_wholesale_cost": promo_wholesale_cost,
            "promo_buy_cost": promo_buy_cost,
            "has_promo": has_promo,
            "original_row": row,  # Store entire original row for later storage
            "brand": brand,
            "title": title,
            "description": title,  # Alias for compatibility
            "notes": notes,
            "moq": 1,  # Actual MOQ (cases) - separate from pack_size
        }
    except Exception as e:
        logger.warning(f"Error parsing supplier row: {e}")
        return None


def parse_asin(row: dict) -> Optional[str]:
    """Extract ASIN from row. Prioritizes ASIN over UPC."""
    # First, try to find ASIN directly
    asin = str(row.get("asin") or row.get("ASIN") or row.get("amazon asin") or row.get("product asin") or "").strip().upper()
    
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
    
    # Try common UPC column names (both original case and lowercase)
    upc = row.get("UPC") or row.get("upc") or row.get("ean") or row.get("gtin") or row.get("barcode") or row.get("product upc") or row.get("product_upc") or ""
    
    upc = str(upc).strip() if upc else ""
    
    # Normalize and validate
    if upc:
        # Clean UPC (remove .0 suffix from Excel numeric conversion)
        upc = upc.replace(".0", "").replace("-", "").replace(" ", "")
        normalized = upc_converter.normalize_upc(upc)
        if normalized:
            return normalized
    
    # Search all columns for UPC pattern (12-14 digits)
    for value in row.values():
        if value:
            val = str(value).strip().replace("-", "").replace(" ", "").replace(".0", "")
            if upc_converter.is_valid_upc(val):
                return upc_converter.normalize_upc(val)
    
    return None


def parse_cost(row: dict) -> Optional[float]:
    """Extract cost from row."""
    cost_str = str(row.get("buy_cost") or row.get("buy cost") or row.get("cost") or row.get("price") or row.get("unit cost") or row.get("unit_cost") or row.get("WHOLESALE") or row.get("wholesale") or "").strip()
    if not cost_str or cost_str.lower() in ["", "n/a", "na", "none", "null"]:
        return None
    try:
        return float(cost_str.replace("$", "").replace(",", ""))
    except:
        return None


def parse_moq(row: dict) -> int:
    """Extract MOQ from row with fuzzy column matching."""
    # Try exact matches first (including KEHE format)
    moq_str = None
    for key in ["PACK", "pack", "moq", "qty", "quantity", "min qty", "min order qty", "minimum order", 
                "min order", "order qty", "order quantity", "min qty", "qty min"]:
        if key in row:
            moq_str = str(row[key] or "").strip()
            if moq_str and moq_str.lower() not in ["", "n/a", "na", "none", "null"]:
                break
    
    # If not found, search all keys for MOQ-related patterns
    if not moq_str:
        for key, value in row.items():
            key_lower = key.lower()
            if any(term in key_lower for term in ["moq", "min", "qty", "quantity", "order", "pack"]):
                moq_str = str(value or "").strip()
                if moq_str and moq_str.lower() not in ["", "n/a", "na", "none", "null"]:
                    break
    
    if not moq_str:
        return 1
    
    try:
        # Remove common prefixes/suffixes and Excel numeric artifacts
        moq_str = moq_str.replace("$", "").replace(",", "").replace(" ", "").replace(".0", "")
        # Extract first number found
        numbers = re.findall(r'\d+', moq_str)
        if numbers:
            return max(1, int(float(numbers[0])))
        return 1
    except:
        return 1


def parse_notes(row: dict) -> Optional[str]:
    """Extract notes from row."""
    notes = str(row.get("notes") or row.get("note") or row.get("comments") or row.get("DESCRIPTION") or row.get("description") or "").strip()
    return notes if notes else None


@celery_app.task(bind=True, max_retries=2)
def process_file_upload(self, job_id: str, user_id: str, supplier_id: str, file_contents_b64: str, filename: str):
    """
    Process CSV/Excel file upload.
    Supports hardcoded KEHE supplier format with UPC → ASIN conversion.
    file_contents_b64: Base64 encoded file contents (for serialization)
    
    Can be called with self=None for synchronous execution (BackgroundTasks fallback).
    """
    # ============================================================
    # CRITICAL LOGGING - TASK START
    # ============================================================
    print("=" * 60)
    print("BACKGROUND TASK EXECUTING")
    print(f"Job ID: {job_id}")
    print(f"User ID: {user_id}")
    print(f"Supplier ID: {supplier_id}")
    print(f"Filename: {filename}")
    print(f"Content length (b64): {len(file_contents_b64) if file_contents_b64 else 'None'}")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info("BACKGROUND TASK EXECUTING - process_file_upload")
    logger.info(f"Job ID: {job_id}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Supplier ID: {supplier_id}")
    logger.info(f"Filename: {filename}")
    logger.info(f"Content length (b64): {len(file_contents_b64) if file_contents_b64 else 'None'}")
    logger.info(f"Celery mode: {self is not None}")
    logger.info("=" * 60)
    
    job = JobManager(job_id)
    
    try:
        # ============================================================
        # STEP 1: DECODE FILE
        # ============================================================
        logger.info("=" * 80)
        logger.info("📥 STEP 1: DECODING FILE")
        logger.info("=" * 80)
        logger.info(f"Job ID: {job_id}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Supplier ID: {supplier_id}")
        logger.info(f"Filename: {filename}")
        logger.info(f"Base64 content length: {len(file_contents_b64) if file_contents_b64 else 'None'}")
        
        try:
            contents = base64.b64decode(file_contents_b64)
            logger.info(f"✅ Decoded successfully: {len(contents)} bytes")
        except Exception as decode_error:
            error_msg = f"Failed to decode base64 file: {str(decode_error)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            job.fail(error_msg)
            return
        
        # ============================================================
        # STEP 2: PARSE FILE
        # ============================================================
        logger.info("=" * 80)
        logger.info("📖 STEP 2: PARSING FILE")
        logger.info("=" * 80)
        
        job.start()
        job.set_status("parsing")
        job.update_progress(0, 0, success=0, errors=0, error_list=None)
        
        try:
            if filename.lower().endswith('.csv'):
                logger.info("📄 Detected CSV format")
                rows, headers = parse_csv(contents)
            elif filename.lower().endswith(('.xlsx', '.xls')):
                logger.info("📊 Detected Excel format")
                rows, headers = parse_excel(contents)
            else:
                error_msg = f"Unsupported file type: {filename}"
                logger.error(f"❌ {error_msg}")
                job.fail(error_msg)
                return
            
            logger.info(f"✅ Parsed successfully: {len(rows)} rows, {len(headers)} columns")
            logger.info(f"📋 Headers: {headers[:10]}{'...' if len(headers) > 10 else ''}")
        except Exception as parse_error:
            error_msg = f"Failed to parse file: {str(parse_error)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            logger.error(f"Traceback: {traceback.format_exc()}")
            job.fail(error_msg)
            return
        
        total = len(rows)
        if total == 0:
            logger.warning("⚠️ No rows found in file")
            job.complete({"message": "No valid rows found"}, success=0, errors=0)
            return
        
        # ============================================================
        # STEP 3: DETECT FORMAT
        # ============================================================
        logger.info("=" * 80)
        logger.info("🔍 STEP 3: DETECTING FORMAT")
        logger.info("=" * 80)
        
        is_kehe = is_kehe_format(headers)
        if is_kehe:
            logger.info(f"✅ Detected KEHE supplier format")
        else:
            logger.info(f"📋 Standard format detected")
        
        job.set_status("processing")
        job.update_progress(0, total, success=0, errors=0, error_list=None)
        
        # Caches
        product_cache = {}  # asin -> product_id
        upc_to_asin_cache = {}  # upc -> asin (for KEHE format)
        
        # Import UPC converter for KEHE format
        from app.services.upc_converter import upc_converter
        
        results = {
            "products_created": 0,
            "deals_processed": 0,
            "total_rows": total,
            "format": "kehe" if is_kehe else "standard",
            "analyzed": 0,
            "needs_asin_selection": 0,
            "needs_manual_asin": 0,
            "errors": 0
        }
        error_list = []
        processed = 0
        
            # Process in batches
        logger.info("=" * 80)
        logger.info("🔄 STEP 4: PROCESSING IN BATCHES")
        logger.info("=" * 80)
        logger.info(f"   Total rows to process: {total}")
        logger.info(f"   Batch size: {BATCH_SIZE}")
        logger.info(f"   Number of batches: {(total + BATCH_SIZE - 1) // BATCH_SIZE}")
        
        for batch_start in range(0, total, BATCH_SIZE):
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
            
            # Check for cancellation
            if job.is_cancelled():
                logger.warning("⚠️ Job was cancelled by user")
                job.complete(results, results["deals_processed"], len(error_list), error_list)
                return
            
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = rows[batch_start:batch_end]
            logger.info("=" * 80)
            logger.info(f"📦 BATCH {batch_num}/{total_batches}: Processing rows {batch_start + 1}-{batch_end} ({len(batch)} rows)")
            logger.info("=" * 80)
            
            # Parse rows
            parsed_rows = []
            asins = []
            upcs_to_convert = []
            
            logger.info(f"🔍 Parsing {len(batch)} rows in batch...")
            for idx, row in enumerate(batch):
                row_num = batch_start + idx + 2
                if (idx + 1) % 10 == 0:
                    logger.info(f"   Parsed {idx + 1}/{len(batch)} rows...")
                
                # Use KEHE format parsing if detected
                if is_kehe:
                    supplier_data = parse_supplier_row(row)
                    if not supplier_data or not supplier_data.get("upc"):
                        error_list.append(f"Row {row_num}: Missing UPC in supplier format")
                        continue
                    
                    upc = supplier_data["upc"]
                    
                    # Check cache for UPC → ASIN conversion
                    if upc in upc_to_asin_cache:
                        asin = upc_to_asin_cache[upc]
                    else:
                        # Convert UPC to ASIN
                        upcs_to_convert.append((upc, supplier_data, row_num))
                        continue  # Will process after batch conversion
                    
                    parsed_rows.append({
                        "asin": asin,
                        "upc": supplier_data.get("upc"),
                        "buy_cost": supplier_data.get("buy_cost"),
                        "pack_size": supplier_data.get("pack_size", 1),
                        "wholesale_cost": supplier_data.get("wholesale_cost"),
                        "supplier_sku": supplier_data.get("supplier_sku"),
                        "promo_qty": supplier_data.get("promo_qty"),
                        "moq": supplier_data.get("moq", 1),
                        "notes": supplier_data.get("notes"),
                        "brand": supplier_data.get("brand"),
                        "title": supplier_data.get("title"),
                        "original_row": supplier_data.get("original_row", row)  # Store original row
                    })
                    asins.append(asin)
                else:
                    # Standard format - try ASIN first, then UPC
                    asin = parse_asin(row)
                    
                    if not asin:
                        # Try UPC conversion
                        upc = parse_upc(row)
                        if upc:
                            if upc in upc_to_asin_cache:
                                asin = upc_to_asin_cache[upc]
                            else:
                                upcs_to_convert.append((upc, None, row_num))
                                continue
                        else:
                            error_list.append(f"Row {row_num}: Invalid ASIN/UPC")
                            continue
                    
                    parsed_rows.append({
                        "asin": asin,
                        "upc": parse_upc(row),
                        "buy_cost": parse_cost(row),
                        "moq": parse_moq(row),
                        "notes": parse_notes(row),
                        "original_row": row  # Store entire original row
                    })
                    asins.append(asin)
            
            # Batch convert UPCs to ASINs (async) - Process in batches of 20
            if upcs_to_convert:
                from app.tasks.base import run_async
                import time
                
                # Group UPCs into batches of 20 (SP-API limit)
                UPC_BATCH_SIZE = 20
                
                # Store mapping of UPC -> (supplier_data, row_num) for later processing
                upc_info_map = {}
                for upc, supplier_data, row_num in upcs_to_convert:
                    upc_info_map[upc] = (supplier_data, row_num)
                
                # Process UPCs in batches
                all_upcs = [upc for upc, _, _ in upcs_to_convert]
                
                logger.info(f"🔄 Starting batch UPC conversion for {len(all_upcs)} UPCs in {(len(all_upcs) + UPC_BATCH_SIZE - 1) // UPC_BATCH_SIZE} batches...")
                logger.info(f"   First 10 UPCs: {all_upcs[:10]}")
                
                for batch_start in range(0, len(all_upcs), UPC_BATCH_SIZE):
                    batch_upcs = all_upcs[batch_start:batch_start + UPC_BATCH_SIZE]
                    batch_num = batch_start // UPC_BATCH_SIZE + 1
                    
                    try:
                        # Batch convert up to 20 UPCs at once
                        logger.info(f"🔄 Batch {batch_num}: Converting {len(batch_upcs)} UPCs...")
                        logger.info(f"   UPCs: {batch_upcs}")
                        
                        upc_to_asin_results = run_async(
                            upc_converter.upcs_to_asins_batch(batch_upcs)
                        )
                        
                        logger.info(f"📦 Batch {batch_num} conversion result:")
                        logger.info(f"   Result type: {type(upc_to_asin_results)}")
                        if isinstance(upc_to_asin_results, dict):
                            logger.info(f"   Result keys: {list(upc_to_asin_results.keys())[:5]}...")
                            logger.info(f"   Result values: {list(upc_to_asin_results.values())[:5]}...")
                            found = sum(1 for v in upc_to_asin_results.values() if v)
                            logger.info(f"   Found: {found}/{len(batch_upcs)}")
                        
                        # Process results - check for multiple ASINs if batch returned single ASIN
                        for upc in batch_upcs:
                            asin_result = upc_to_asin_results.get(upc)
                            supplier_data, row_num = upc_info_map.get(upc, (None, None))
                            
                            if asin_result:
                                # Batch conversion found an ASIN - use it directly (no redundant API call)
                                logger.info(f"   ✅ UPC {upc} → ASIN {asin_result} (from batch)")
                                
                                # Use the ASIN from batch directly - no need for detailed lookup
                                # Variation checking can be done later if needed (e.g., during analysis)
                                upc_to_asin_cache[upc] = asin_result
                                
                                # Create parsed row with single ASIN
                                if is_kehe and supplier_data:
                                    parsed_rows.append({
                                        "asin": asin_result,
                                        "upc": upc,
                                        "buy_cost": supplier_data.get("buy_cost"),
                                        "pack_size": supplier_data.get("pack_size", 1),
                                        "wholesale_cost": supplier_data.get("wholesale_cost"),
                                        "supplier_sku": supplier_data.get("supplier_sku"),
                                        "supplier_title": supplier_data.get("title"),
                                        "promo_qty": supplier_data.get("promo_qty"),
                                        "moq": supplier_data.get("moq", 1),
                                        "notes": supplier_data.get("notes"),
                                        "brand": supplier_data.get("brand"),
                                        "original_row": supplier_data.get("original_row", row)
                                    })
                                else:
                                    # For standard format, use stored row data
                                    if supplier_data:
                                        parsed_rows.append({
                                            "asin": asin_result,
                                            "upc": upc,
                                            "buy_cost": supplier_data.get("buy_cost"),
                                            "moq": supplier_data.get("moq", 1),
                                            "notes": supplier_data.get("notes"),
                                            "original_row": supplier_data.get("original_row", row)
                                        })
                                    else:
                                        # Fallback: try to find original row
                                        original_row = None
                                        for orig_row in batch:
                                            if parse_upc(orig_row) == upc:
                                                original_row = orig_row
                                                break
                                        
                                        if original_row:
                                            parsed_rows.append({
                                                "asin": asin_result,
                                                "upc": upc,
                                                "buy_cost": parse_cost(original_row),
                                                "moq": parse_moq(original_row),
                                                "notes": parse_notes(original_row),
                                                "original_row": original_row
                                            })
                                asins.append(asin_result)
                            else:
                                # Batch conversion returned None - try detailed lookup to confirm
                                logger.warning(f"   ❌ UPC {upc} → No ASIN found in batch, checking detailed lookup...")
                                
                                detailed_result = run_async(
                                    upc_converter.upc_to_asins(upc)
                                )
                                detailed_asins, lookup_status = detailed_result if isinstance(detailed_result, tuple) else ([], "error")
                                
                                if lookup_status == "multiple" and len(detailed_asins) > 1:
                                    # Multiple ASINs found - same handling as above
                                    logger.warning(f"   ⚠️ UPC {upc} has {len(detailed_asins)} ASINs - user must choose")
                                    
                                    if is_kehe and supplier_data:
                                        parsed_rows.append({
                                            "asin": None,
                                            "upc": upc,
                                            "potential_asins": detailed_asins,
                                            "asin_status": "multiple_found",
                                            "buy_cost": supplier_data.get("buy_cost"),
                                            "pack_size": supplier_data.get("pack_size", 1),
                                            "wholesale_cost": supplier_data.get("wholesale_cost"),
                                            "supplier_sku": supplier_data.get("supplier_sku"),
                                            "supplier_title": supplier_data.get("title"),
                                            "promo_qty": supplier_data.get("promo_qty"),
                                            "moq": supplier_data.get("moq", 1),
                                            "notes": supplier_data.get("notes"),
                                            "brand": supplier_data.get("brand"),
                                            "original_row": supplier_data.get("original_row", row)
                                        })
                                    else:
                                        original_row = None
                                        for orig_row in batch:
                                            if parse_upc(orig_row) == upc:
                                                original_row = orig_row
                                                break
                                        
                                        parsed_rows.append({
                                            "asin": None,
                                            "upc": upc,
                                            "potential_asins": detailed_asins,
                                            "asin_status": "multiple_found",
                                            "supplier_title": original_row.get("title") if original_row else None,
                                            "buy_cost": supplier_data.get("buy_cost") if supplier_data else parse_cost(original_row) if original_row else None,
                                            "moq": supplier_data.get("moq", 1) if supplier_data else parse_moq(original_row) if original_row else 1,
                                            "notes": supplier_data.get("notes") if supplier_data else parse_notes(original_row) if original_row else None,
                                            "original_row": original_row if original_row else (supplier_data.get("original_row") if supplier_data else row)
                                        })
                                    
                                    if row_num:
                                        error_list.append(f"Row {row_num}: Found {len(detailed_asins)} ASINs for UPC {upc} - user must choose")
                                elif lookup_status == "found" and len(detailed_asins) == 1:
                                    # Single ASIN found in detailed lookup (batch may have missed it)
                                    asin_result = detailed_asins[0].get("asin")
                                    if asin_result:
                                        logger.info(f"   ✅ UPC {upc} → ASIN {asin_result} (from detailed lookup)")
                                        upc_to_asin_cache[upc] = asin_result
                                        
                                        if is_kehe and supplier_data:
                                            parsed_rows.append({
                                                "asin": asin_result,
                                                "upc": upc,
                                                "buy_cost": supplier_data.get("buy_cost"),
                                                "pack_size": supplier_data.get("pack_size", 1),
                                                "wholesale_cost": supplier_data.get("wholesale_cost"),
                                                "supplier_sku": supplier_data.get("supplier_sku"),
                                                "supplier_title": supplier_data.get("title"),
                                                "promo_qty": supplier_data.get("promo_qty"),
                                                "moq": supplier_data.get("moq", 1),
                                                "notes": supplier_data.get("notes"),
                                                "brand": supplier_data.get("brand"),
                                                "original_row": supplier_data.get("original_row", row)
                                            })
                                        else:
                                            original_row = None
                                            for orig_row in batch:
                                                if parse_upc(orig_row) == upc:
                                                    original_row = orig_row
                                                    break
                                            
                                            if original_row:
                                                parsed_rows.append({
                                                    "asin": asin_result,
                                                    "upc": upc,
                                                    "buy_cost": parse_cost(original_row),
                                                    "moq": parse_moq(original_row),
                                                    "notes": parse_notes(original_row),
                                                    "original_row": original_row
                                                })
                                        asins.append(asin_result)
                                else:
                                    # NO ASIN FOUND - save product anyway for manual entry
                                    logger.info(f"   ❌ UPC {upc} → No ASIN found - product will be saved for manual entry")
                                    
                                    if supplier_data:
                                        parsed_rows.append({
                                            "asin": None,  # No ASIN yet
                                            "upc": upc,  # Keep UPC for manual lookup
                                            "asin_status": "not_found",
                                            "buy_cost": supplier_data.get("buy_cost"),
                                            "pack_size": supplier_data.get("pack_size", 1),
                                            "wholesale_cost": supplier_data.get("wholesale_cost"),
                                            "supplier_sku": supplier_data.get("supplier_sku"),
                                            "supplier_title": supplier_data.get("title"),
                                            "promo_qty": supplier_data.get("promo_qty"),
                                            "moq": supplier_data.get("moq", 1),
                                            "original_row": supplier_data.get("original_row", row),
                                            "notes": supplier_data.get("notes"),
                                            "brand": supplier_data.get("brand")
                                        })
                                        logger.info(f"✅ Row {row_num}: UPC {upc} conversion failed, but product will be saved with asin_status='not_found'")
                                    else:
                                        # No supplier_data - this shouldn't happen for KEHE format, but handle it
                                        logger.warning(f"⚠️ Row {row_num}: UPC {upc} conversion failed but no supplier_data available")
                                    
                                    if row_num:
                                        error_list.append(f"Row {row_num}: Could not convert UPC {upc} to ASIN - product saved for manual entry")
                        
                        # Rate limiting - wait 0.5 seconds between batches (2 requests/sec max)
                        if batch_start + UPC_BATCH_SIZE < len(all_upcs):
                            time.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Error in batch UPC conversion (batch {batch_start // UPC_BATCH_SIZE + 1}): {e}", exc_info=True)
                        # Mark all UPCs in this batch as failed
                        for upc in batch_upcs:
                            _, row_num = upc_info_map.get(upc, (None, None))
                            if row_num:
                                error_list.append(f"Row {row_num}: Error converting UPC {upc}: {str(e)}")
            
            # Batch get/create products
            logger.info("=" * 80)
            logger.info(f"💾 STEP 5: CREATING PRODUCTS (Batch {batch_num}/{total_batches})")
            logger.info("=" * 80)
            logger.info(f"   Total parsed rows in this batch: {len(parsed_rows)}")
            
            # Separate products with ASINs and products without ASINs
            products_with_asin = [p for p in parsed_rows if p.get("asin")]
            products_without_asin = [p for p in parsed_rows if not p.get("asin")]
            
            logger.info(f"   Products WITH ASIN: {len(products_with_asin)}")
            logger.info(f"   Products WITHOUT ASIN: {len(products_without_asin)}")
            
            # Process products WITH ASINs (existing logic)
            unique_asins = list(set([p["asin"] for p in products_with_asin if p.get("asin") and p["asin"] not in product_cache]))
            
            if unique_asins:
                logger.info(f"🔍 Checking for existing products with {len(unique_asins)} unique ASINs...")
                logger.info(f"   Sample ASINs: {unique_asins[:5]}{'...' if len(unique_asins) > 5 else ''}")
                try:
                    # Get existing
                    existing = supabase.table("products")\
                        .select("id, asin")\
                        .eq("user_id", user_id)\
                        .in_("asin", unique_asins)\
                        .execute()
                    
                    existing_count = len(existing.data or [])
                    logger.info(f"✅ Found {existing_count} existing products in database")
                    if existing_count > 0:
                        logger.info(f"   Sample existing product IDs: {[p['id'][:8] + '...' for p in (existing.data or [])[:3]]}")
                    
                    for p in (existing.data or []):
                        product_cache[p["asin"]] = p["id"]
                except Exception as check_error:
                    logger.error(f"❌ Failed to check existing products: {check_error}", exc_info=True)
                    logger.error(f"   Error type: {type(check_error).__name__}")
                    logger.error(f"   Full traceback:\n{traceback.format_exc()}")
                    error_list.append(f"Failed to check existing products: {str(check_error)}")
                
                # Create missing
                missing_asins = [a for a in unique_asins if a not in product_cache]
                logger.info(f"   Products to create: {len(missing_asins)} (missing from database)")
                if missing_asins:
                    logger.info(f"   Sample missing ASINs: {missing_asins[:5]}{'...' if len(missing_asins) > 5 else ''}")
                    # Create products with brand if available (for KEHE format)
                    new_products = []
                    for parsed in products_with_asin:
                        if parsed["asin"] in missing_asins:
                            # Get Amazon title from first potential ASIN if available
                            amazon_title = None
                            if parsed.get("potential_asins") and len(parsed["potential_asins"]) > 0:
                                # Use the selected ASIN's title from potential_asins
                                selected_asin_data = next(
                                    (a for a in parsed["potential_asins"] if a.get("asin") == parsed["asin"]),
                                    None
                                )
                                if selected_asin_data:
                                    amazon_title = selected_asin_data.get("title")
                            
                            # Extract all CSV columns from original row
                            original_row = parsed.get("original_row", {})
                            
                            product_data = {
                                "user_id": user_id,
                                "asin": parsed["asin"],
                                "upc": parsed.get("upc"),
                                "title": amazon_title,  # Amazon title (from SP-API)
                                "supplier_title": original_row.get("title") or original_row.get("product_name") or original_row.get("name") or original_row.get("DESCRIPTION") or original_row.get("description") or parsed.get("supplier_title") or parsed.get("title"),
                                "brand": original_row.get("brand") or original_row.get("BRAND") or parsed.get("brand"),
                                "category": original_row.get("category") or original_row.get("CATEGORY"),
                                "status": "pending",
                                "asin_status": "found",  # ASIN was found via UPC conversion
                                "lookup_status": "found"
                            }
                            new_products.append(product_data)
                    
                    # Deduplicate by ASIN
                    seen_asins = set()
                    unique_products = []
                    for p in new_products:
                        if p["asin"] not in seen_asins:
                            unique_products.append(p)
                            seen_asins.add(p["asin"])
                    
                    if unique_products:
                        logger.info(f"💾 Inserting {len(unique_products)} new products WITH ASINs...")
                        logger.info(f"   Sample product data keys: {list(unique_products[0].keys()) if unique_products else []}")
                        try:
                            # Clean and normalize products before insert
                            cleaned_products = [clean_product_for_insert(p) for p in unique_products]
                            normalized_products = normalize_product_batch(cleaned_products)
                            created = supabase.table("products").insert(normalized_products).execute()
                            created_count = len(created.data or [])
                            logger.info(f"✅ Successfully created {created_count} products with ASINs")
                            
                            for p in (created.data or []):
                                product_cache[p["asin"]] = p["id"]
                                results["products_created"] += 1
                            
                            logger.info(f"   Product cache now contains {len(product_cache)} entries")
                            
                            # 🔥 CRITICAL: Fetch and store COMPLETE API data for all new products
                            logger.info(f"📡 Fetching complete API data for {len(created.data)} new products...")
                            from app.services.api_storage_service import fetch_and_store_all_api_data
                            from app.tasks.base import run_async
                            
                            for p in created.data:
                                asin = p.get("asin")
                                if asin and asin not in ["PENDING_", "Unknown"] and not asin.startswith("PENDING_"):
                                    try:
                                        # Fetch and store ALL API data (SP-API + Keepa)
                                        # Use run_async since this is a sync Celery task
                                        run_async(fetch_and_store_all_api_data(asin, force_refresh=False))
                                        logger.info(f"✅ Stored complete API data for {asin}")
                                    except Exception as api_error:
                                        logger.error(f"❌ Failed to fetch API data for {asin}: {api_error}")
                                        # Continue - at least we have the ASIN
                            
                            results.setdefault("analyzed", 0)
                            # Note: Will be analyzed later by the auto-analysis job
                        except Exception as insert_error:
                            logger.error(f"❌ Failed to insert products with ASINs: {insert_error}", exc_info=True)
                            logger.error(f"   Error type: {type(insert_error).__name__}")
                            logger.error(f"   Attempting to insert {len(unique_products)} products")
                            logger.error(f"   First product sample: {unique_products[0] if unique_products else 'N/A'}")
                            logger.error(f"   Full traceback:\n{traceback.format_exc()}")
                            error_list.append(f"Failed to insert products: {str(insert_error)}")
                            
                            # Try one-by-one to identify problematic records
                            logger.info("🔄 Attempting one-by-one insert to identify problematic records...")
                            for idx, prod in enumerate(unique_products):
                                try:
                                    cleaned_prod = clean_product_for_insert(prod)
                                    single_result = supabase.table("products").insert([cleaned_prod]).execute()
                                    if single_result.data:
                                        product_cache[prod["asin"]] = single_result.data[0]["id"]
                                        results["products_created"] += 1
                                        logger.info(f"   ✅ Product {idx + 1}/{len(unique_products)} inserted: {prod.get('asin')}")
                                except Exception as single_error:
                                    logger.error(f"   ❌ Product {idx + 1}/{len(unique_products)} failed: {prod.get('asin')} - {single_error}")
                                    error_list.append(f"Row {batch_start + idx + 1}: Failed to create product {prod.get('asin')}: {str(single_error)}")
            
            # Process products WITHOUT ASINs (new logic)
            if products_without_asin:
                logger.info("=" * 80)
                logger.info(f"💾 STEP 6: CREATING PRODUCTS WITHOUT ASINs (Batch {batch_num}/{total_batches})")
                logger.info("=" * 80)
                logger.info(f"   Products without ASIN: {len(products_without_asin)}")
                
                new_products_no_asin = []
                for parsed in products_without_asin:
                    # Check if product with this UPC already exists
                    upc = parsed.get("upc")
                    if not upc:
                        continue
                    
                    asin_status = parsed.get("asin_status", "not_found")
                    potential_asins = parsed.get("potential_asins")
                    
                    # Use placeholder ASIN since column is NOT NULL (unless DB allows NULL after migration)
                    # Format: PENDING_{UPC} - will be updated when ASIN is found
                    placeholder_asin = f"PENDING_{upc}"
                    
                    # Extract all CSV columns from original row
                    original_row = parsed.get("original_row", {})
                    
                    # Build product data with all new fields
                    product_data = {
                        "user_id": user_id,
                        "asin": None if asin_status == "multiple_found" else placeholder_asin,  # NULL if multiple ASINs (user must choose), placeholder otherwise
                        "upc": upc,  # Store UPC for manual lookup
                        "title": None,  # Will be filled from Amazon once ASIN is set
                        "supplier_title": original_row.get("title") or original_row.get("product_name") or original_row.get("name") or original_row.get("DESCRIPTION") or original_row.get("description") or parsed.get("supplier_title") or parsed.get("title"),
                        "brand": original_row.get("brand") or original_row.get("BRAND") or parsed.get("brand"),
                        "category": original_row.get("category") or original_row.get("CATEGORY"),
                        "status": "pending",
                        "asin_status": asin_status,  # 'not_found' or 'multiple_found'
                        "potential_asins": potential_asins if potential_asins else None,  # JSONB array of ASIN options
                        "lookup_status": "not_found" if asin_status == "not_found" else "pending_selection" if asin_status == "multiple_found" else "pending"
                    }
                    new_products_no_asin.append(product_data)
                
                if new_products_no_asin:
                    logger.info(f"💾 Preparing to insert {len(new_products_no_asin)} products without ASINs...")
                    logger.info(f"   Sample UPCs: {[p.get('upc') for p in new_products_no_asin[:5]]}")
                    
                    # Insert products without ASINs
                    try:
                        # Clean product data - remove None values and ensure proper types
                        logger.info("🧹 Cleaning product data (removing None values, ensuring proper types)...")
                        cleaned_products = []
                        for p in new_products_no_asin:
                            cleaned = {}
                            for key, value in p.items():
                                # Skip None values for optional fields (except where NULL is meaningful)
                                if value is None and key not in ['asin', 'title', 'brand']:
                                    continue
                                # Ensure proper types for JSONB fields
                                if key == 'potential_asins' and value:
                                    # Ensure it's a list, not a dict
                                    if isinstance(value, dict):
                                        cleaned[key] = [value]
                                    elif isinstance(value, list):
                                        cleaned[key] = value
                                    else:
                                        cleaned[key] = [value] if value else None
                                else:
                                    cleaned[key] = value
                            cleaned_products.append(cleaned)
                        
                        logger.info(f"📤 Executing batch insert of {len(cleaned_products)} products without ASINs...")
                        # Clean and normalize products before insert
                        final_cleaned = [clean_product_for_insert(p) for p in cleaned_products]
                        normalized_products = normalize_product_batch(final_cleaned)
                        created_no_asin = supabase.table("products").insert(normalized_products).execute()
                        created_count = len(created_no_asin.data or [])
                        logger.info(f"✅ Successfully inserted {created_count} products without ASINs")
                        
                        for p in (created_no_asin.data or []):
                            # Use a special key format for products without ASIN: "upc:{upc}"
                            upc_key = f"upc:{p.get('upc')}"
                            product_cache[upc_key] = p["id"]
                            results["products_created"] += 1
                            
                            # Track different result types
                            if p.get("asin_status") == "multiple_found":
                                results.setdefault("needs_asin_selection", 0)
                                results["needs_asin_selection"] += 1
                            elif p.get("asin_status") == "not_found":
                                results.setdefault("needs_manual_asin", 0)
                                results["needs_manual_asin"] += 1
                    except Exception as insert_error:
                        error_msg = f"Failed to insert products without ASINs: {str(insert_error)}"
                        logger.error(f"❌ {error_msg}", exc_info=True)
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        error_list.append(error_msg)
                        # Try to insert one by one to identify problematic records
                        logger.info(f"🔄 Retrying one-by-one insert for {len(new_products_no_asin)} products...")
                        success_count = 0
                        for idx, p in enumerate(new_products_no_asin):
                            try:
                                cleaned = {k: v for k, v in p.items() if v is not None or k in ['asin', 'title', 'brand']}
                                if 'potential_asins' in cleaned and cleaned['potential_asins']:
                                    if isinstance(cleaned['potential_asins'], dict):
                                        cleaned['potential_asins'] = [cleaned['potential_asins']]
                                logger.debug(f"   Inserting product {idx + 1}/{len(new_products_no_asin)}: UPC {p.get('upc')}")
                                cleaned_product = clean_product_for_insert(cleaned)
                                result = supabase.table("products").insert([cleaned_product]).execute()
                                if result.data:
                                    product = result.data[0]
                                    upc_key = f"upc:{product.get('upc')}"
                                    product_cache[upc_key] = product["id"]
                                    results["products_created"] += 1
                                    success_count += 1
                            except Exception as single_error:
                                logger.error(f"❌ Failed to insert product {idx + 1} (UPC {p.get('upc')}): {single_error}")
                                error_list.append(f"Row {batch_start + idx + 2}: Failed to create product: {str(single_error)}")
                        logger.info(f"✅ One-by-one insert complete: {success_count}/{len(new_products_no_asin)} succeeded")
            
            # Build deals for upsert
            # Use dict to deduplicate by (product_id, supplier_id) - keep last occurrence
            deals_dict = {}
            missing_product_count = 0  # Track rows that couldn't be matched to products
            for parsed in parsed_rows:
                # Get product_id - either by ASIN or by UPC
                product_id = None
                if parsed.get("asin"):
                    product_id = product_cache.get(parsed["asin"])
                elif parsed.get("upc"):
                    # For products without ASIN, use UPC key
                    upc_key = f"upc:{parsed['upc']}"
                    product_id = product_cache.get(upc_key)
                
                if not product_id:
                    missing_product_count += 1
                    continue
                
                # Use (product_id, supplier_id) as key to deduplicate
                key = (product_id, supplier_id)
                deals_dict[key] = {
                    "product_id": product_id,
                    "supplier_id": supplier_id,
                    "buy_cost": parsed.get("buy_cost"),  # Now correctly per-unit
                    "pack_size": parsed.get("pack_size", 1),  # NEW
                    "wholesale_cost": parsed.get("wholesale_cost"),  # NEW
                    "supplier_sku": parsed.get("supplier_sku"),  # NEW
                    "promo_qty": parsed.get("promo_qty"),  # NEW
                    "promo_percent": parsed.get("promo_percent"),  # NEW
                    "promo_wholesale_cost": parsed.get("promo_wholesale_cost"),  # NEW
                    "promo_buy_cost": parsed.get("promo_buy_cost"),  # NEW
                    "has_promo": parsed.get("has_promo", False),  # NEW
                    "moq": parsed.get("moq", 1),
                    "source": "excel" if filename.lower().endswith(('.xlsx', '.xls')) else "csv",
                    "source_detail": filename,
                    "notes": parsed.get("notes"),
                    "stage": "pending_asin_selection" if parsed.get("asin_status") == "multiple_found" else ("pending_asin" if not parsed.get("asin") else "new"),  # Can't analyze without ASIN
                    "is_active": True
                }
            
            # Convert dict values to list for upsert (deduplicated)
            deals = list(deals_dict.values())
            
            # Batch upsert deals
            if deals:
                logger.info(f"💼 Upserting {len(deals)} deals...")
                try:
                    result = supabase.table("product_sources")\
                        .upsert(deals, on_conflict="product_id,supplier_id")\
                        .execute()
                    deals_count = len(result.data or [])
                    logger.info(f"✅ Successfully upserted {deals_count} deals")
                    results["deals_processed"] += deals_count
                except Exception as deals_error:
                    error_msg = f"Failed to upsert deals: {str(deals_error)}"
                    logger.error(f"❌ {error_msg}", exc_info=True)
                    error_list.append(error_msg)
            else:
                logger.warning(f"⚠️ No deals to upsert for this batch")
            
            if missing_product_count > 0:
                logger.warning(f"⚠️ {missing_product_count} rows skipped due to missing product_id")
            
            processed = batch_end
            logger.info(f"📊 Batch {batch_num} complete: {processed}/{total} rows processed")
            logger.info(f"   Products created: {results['products_created']}")
            logger.info(f"   Deals processed: {results['deals_processed']}")
            logger.info(f"   Errors: {len(error_list)}")
            job.update_progress(processed, total, results["deals_processed"], len(error_list), error_list)
        
        # Complete
        job.complete(results, results["deals_processed"], len(error_list), error_list)
        
        # Auto-analyze uploaded products WITH REAL ASINs (not PENDING_ placeholders)
        # Get product IDs from the uploaded deals that have real ASINs
        if results["deals_processed"] > 0:
            try:
                # Get product IDs with their ASINs - only analyze products with real ASINs
                # Join with products table to filter out PENDING_ ASINs
                uploaded_products = supabase.table("product_sources")\
                    .select("product_id, products!inner(asin)")\
                    .eq("source_detail", filename)\
                    .eq("supplier_id", supplier_id)\
                    .execute()
                
                if uploaded_products.data:
                    # Filter to only products with real ASINs (not PENDING_ or NULL)
                    product_ids_to_analyze = []
                    for p in uploaded_products.data:
                        product = p.get("products")
                        if product:
                            asin = product.get("asin")
                            # Only include products with real ASINs
                            if asin and asin != "" and not asin.startswith("PENDING_") and not asin.startswith("Unknown"):
                                product_ids_to_analyze.append(p["product_id"])
                    
                    if product_ids_to_analyze:
                        # Queue analysis job in chunks for better performance
                        from app.tasks.analysis import batch_analyze_products
                        from uuid import uuid4
                        
                        # Process in chunks of 50 products at a time
                        CHUNK_SIZE = 50
                        total_chunks = (len(product_ids_to_analyze) + CHUNK_SIZE - 1) // CHUNK_SIZE
                        
                        logger.info(f"📊 Queuing analysis for {len(product_ids_to_analyze)} products in {total_chunks} chunks...")
                        
                        for chunk_idx in range(0, len(product_ids_to_analyze), CHUNK_SIZE):
                            chunk = product_ids_to_analyze[chunk_idx:chunk_idx + CHUNK_SIZE]
                            chunk_num = chunk_idx // CHUNK_SIZE + 1
                            
                            analysis_job_id = str(uuid4())
                            supabase.table("jobs").insert({
                                "id": analysis_job_id,
                                "user_id": user_id,
                                "type": "batch_analyze",
                                "status": "pending",
                                "total_items": len(chunk),
                                "metadata": {
                                    "triggered_by": "file_upload",
                                    "upload_job_id": job_id,
                                    "filename": filename,
                                    "chunk": f"{chunk_num}/{total_chunks}",
                                    "total_products": len(product_ids_to_analyze)
                                }
                            }).execute()
                            
                            # Queue analysis task for this chunk
                            batch_analyze_products.delay(analysis_job_id, user_id, chunk)
                            
                            logger.info(f"✅ Queued analysis chunk {chunk_num}/{total_chunks} ({len(chunk)} products)")
                        
                        results["analyzed"] = len(product_ids_to_analyze)
                        logger.info(f"🎉 Auto-queued analysis for {len(product_ids_to_analyze)} products with real ASINs from upload {job_id}")
                    else:
                        logger.warning(f"⚠️ No products with real ASINs to analyze (all have PENDING_ or no ASIN)")
            except Exception as analysis_error:
                # Don't fail the upload job if auto-analysis fails
                logger.error(f"❌ Failed to auto-analyze uploaded products: {analysis_error}", exc_info=True)
        
    except Exception as e:
        logger.error(f"❌ BACKGROUND TASK CRASHED for job {job_id}: {e}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            job.fail(f"Task execution failed: {str(e)}")
        except:
            # If job update fails, try direct Supabase update
            try:
                supabase.table("jobs").update({
                    "status": "failed",
                    "errors": [f"Task execution failed: {str(e)}"]
                }).eq("id", job_id).execute()
            except:
                pass
        # Only retry if this is a Celery task (has self)
        if self is not None and hasattr(self, 'retry'):
            raise self.retry(exc=e, countdown=60)
        else:
            raise  # Re-raise for sync version


