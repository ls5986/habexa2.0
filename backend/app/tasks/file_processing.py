"""
Celery tasks for CSV/Excel file processing.
Supports hardcoded KEHE supplier format with UPC → ASIN conversion.
"""
import csv
import io
import re
import base64
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
    """
    job = JobManager(job_id)
    
    try:
        # Decode file contents
        contents = base64.b64decode(file_contents_b64)
        
        # Parse file
        job.start()
        job.set_status("parsing")
        job.update_progress(0, 0, success=0, errors=0, error_list=None)
        
        if filename.lower().endswith('.csv'):
            rows, headers = parse_csv(contents)
        elif filename.lower().endswith(('.xlsx', '.xls')):
            rows, headers = parse_excel(contents)
        else:
            job.fail(f"Unsupported file type: {filename}")
            return
        
        total = len(rows)
        if total == 0:
            job.complete({"message": "No valid rows found"}, success=0, errors=0)
            return
        
        # Detect KEHE format
        is_kehe = is_kehe_format(headers)
        if is_kehe:
            logger.info(f"Detected KEHE supplier format for file {filename}")
        
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
            "format": "kehe" if is_kehe else "standard"
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
            upcs_to_convert = []
            
            for idx, row in enumerate(batch):
                row_num = batch_start + idx + 2
                
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
                        "buy_cost": supplier_data.get("buy_cost"),
                        "pack_size": supplier_data.get("pack_size", 1),
                        "wholesale_cost": supplier_data.get("wholesale_cost"),
                        "supplier_sku": supplier_data.get("supplier_sku"),
                        "promo_qty": supplier_data.get("promo_qty"),
                        "moq": supplier_data.get("moq", 1),
                        "notes": supplier_data.get("notes"),
                        "brand": supplier_data.get("brand")
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
                        "buy_cost": parse_cost(row),
                        "moq": parse_moq(row),
                        "notes": parse_notes(row)
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
                
                for batch_start in range(0, len(all_upcs), BATCH_SIZE):
                    batch_upcs = all_upcs[batch_start:batch_start + BATCH_SIZE]
                    
                    try:
                        # Batch convert up to 20 UPCs at once
                        logger.info(f"🔄 Batch converting {len(batch_upcs)} UPCs (batch {batch_start // BATCH_SIZE + 1})...")
                        upc_to_asin_results = run_async(
                            upc_converter.upcs_to_asins_batch(batch_upcs)
                        )
                        
                        # Process results
                        for upc in batch_upcs:
                            asin_result = upc_to_asin_results.get(upc)
                            
                            if asin_result:
                                upc_to_asin_cache[upc] = asin_result
                                supplier_data, row_num = upc_info_map.get(upc, (None, None))
                                
                                # Create parsed row
                                if is_kehe and supplier_data:
                                    parsed_rows.append({
                                        "asin": asin_result,
                                        "buy_cost": supplier_data.get("buy_cost"),
                                        "pack_size": supplier_data.get("pack_size", 1),
                                        "wholesale_cost": supplier_data.get("wholesale_cost"),
                                        "supplier_sku": supplier_data.get("supplier_sku"),
                                        "promo_qty": supplier_data.get("promo_qty"),
                                        "moq": supplier_data.get("moq", 1),
                                        "notes": supplier_data.get("notes"),
                                        "brand": supplier_data.get("brand")
                                    })
                                else:
                                    # For standard format, use stored row data
                                    if supplier_data:
                                        parsed_rows.append({
                                            "asin": asin_result,
                                            "buy_cost": supplier_data.get("buy_cost"),
                                            "moq": supplier_data.get("moq", 1),
                                            "notes": supplier_data.get("notes")
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
                                                "buy_cost": parse_cost(original_row),
                                                "moq": parse_moq(original_row),
                                                "notes": parse_notes(original_row)
                                            })
                                asins.append(asin_result)
                            else:
                                # UPC conversion failed - but we still want to save the product
                                supplier_data, row_num = upc_info_map.get(upc, (None, None))
                                
                                if supplier_data:
                                    # Create parsed row without ASIN - will be saved with asin_status = 'not_found'
                                    parsed_rows.append({
                                        "asin": None,  # No ASIN yet
                                        "upc": upc,  # Keep UPC for manual lookup
                                        "buy_cost": supplier_data.get("buy_cost"),
                                        "pack_size": supplier_data.get("pack_size", 1),
                                        "wholesale_cost": supplier_data.get("wholesale_cost"),
                                        "supplier_sku": supplier_data.get("supplier_sku"),
                                        "promo_qty": supplier_data.get("promo_qty"),
                                        "moq": supplier_data.get("moq", 1),
                                        "notes": supplier_data.get("notes"),
                                        "brand": supplier_data.get("brand"),
                                        "title": supplier_data.get("title"),
                                        "asin_status": "not_found"  # Mark for manual entry
                                    })
                                    logger.info(f"✅ Row {row_num}: UPC {upc} conversion failed, but product will be saved with asin_status='not_found'")
                                else:
                                    # No supplier_data - this shouldn't happen for KEHE format, but handle it
                                    logger.warning(f"⚠️ Row {row_num}: UPC {upc} conversion failed but no supplier_data available")
                                
                                if row_num:
                                    error_list.append(f"Row {row_num}: Could not convert UPC {upc} to ASIN - product saved for manual entry")
                        
                        # Rate limiting - wait 0.5 seconds between batches (2 requests/sec max)
                        if batch_start + BATCH_SIZE < len(all_upcs):
                            time.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Error in batch UPC conversion (batch {batch_start // BATCH_SIZE + 1}): {e}", exc_info=True)
                        # Mark all UPCs in this batch as failed
                        for upc in batch_upcs:
                            _, row_num = upc_info_map.get(upc, (None, None))
                            if row_num:
                                error_list.append(f"Row {row_num}: Error converting UPC {upc}: {str(e)}")
            
            # Batch get/create products
            # Separate products with ASINs and products without ASINs
            products_with_asin = [p for p in parsed_rows if p.get("asin")]
            products_without_asin = [p for p in parsed_rows if not p.get("asin")]
            
            # Process products WITH ASINs (existing logic)
            unique_asins = list(set([p["asin"] for p in products_with_asin if p.get("asin") and p["asin"] not in product_cache]))
            
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
                    # Create products with brand if available (for KEHE format)
                    new_products = []
                    for parsed in products_with_asin:
                        if parsed["asin"] in missing_asins:
                            product_data = {
                                "user_id": user_id,
                                "asin": parsed["asin"],
                                "upc": parsed.get("upc"),
                                "title": parsed.get("title"),
                                "brand": parsed.get("brand"),
                                "status": "pending",
                                "asin_status": "found"  # ASIN was found via UPC conversion
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
                        created = supabase.table("products").insert(unique_products).execute()
                        for p in (created.data or []):
                            product_cache[p["asin"]] = p["id"]
                            results["products_created"] += 1
            
            # Process products WITHOUT ASINs (new logic)
            if products_without_asin:
                new_products_no_asin = []
                for parsed in products_without_asin:
                    # Check if product with this UPC already exists
                    upc = parsed.get("upc")
                    if not upc:
                        continue
                    
                    # Check cache by UPC (we'll need to query by UPC)
                    # For now, create new product - deduplication can happen later
                    product_data = {
                        "user_id": user_id,
                        "asin": None,  # No ASIN yet
                        "upc": upc,  # Store UPC for manual lookup
                        "title": parsed.get("title"),
                        "brand": parsed.get("brand"),
                        "status": "pending",
                        "asin_status": "not_found"  # Mark for manual entry
                    }
                    new_products_no_asin.append(product_data)
                
                if new_products_no_asin:
                    # Insert products without ASINs
                    created_no_asin = supabase.table("products").insert(new_products_no_asin).execute()
                    for p in (created_no_asin.data or []):
                        # Use a special key format for products without ASIN: "upc:{upc}"
                        upc_key = f"upc:{p.get('upc')}"
                        product_cache[upc_key] = p["id"]
                        results["products_created"] += 1
            
            # Build deals for upsert
            # Use dict to deduplicate by (product_id, supplier_id) - keep last occurrence
            deals_dict = {}
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
                    "stage": "pending_asin" if not parsed.get("asin") else "new",  # Can't analyze without ASIN
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
