"""
Background file processor for CSV and Excel uploads with batch processing.
"""
import csv
import io
import re
import asyncio
from typing import Optional, List, Dict
from app.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False


class FileProcessor:
    """Background file processor for CSV and Excel with batch inserts."""
    
    BATCH_SIZE = 100
    
    def __init__(self, user_id: str, job_id: str, supplier_id: str):
        self.user_id = user_id
        self.job_id = job_id
        self.supplier_id = supplier_id  # ALL rows go to this supplier
        self.product_cache = {}
    
    # ==========================================
    # JOB STATUS UPDATES
    # ==========================================
    def update_progress(self, processed: int, total: int, status: str = "processing"):
        progress = int((processed / total) * 100) if total > 0 else 0
        supabase.table("jobs").update({
            "status": status,
            "progress": progress,
            "processed_items": processed,
            "total_items": total,
            "updated_at": "now()"
        }).eq("id", self.job_id).execute()
    
    def complete_job(self, result: dict):
        supabase.table("jobs").update({
            "status": "completed",
            "progress": 100,
            "result": result,
            "updated_at": "now()"
        }).eq("id", self.job_id).execute()
    
    def fail_job(self, error: str):
        supabase.table("jobs").update({
            "status": "failed",
            "error": error,
            "updated_at": "now()"
        }).eq("id", self.job_id).execute()
    
    # ==========================================
    # FILE PARSING
    # ==========================================
    def parse_file(self, contents: bytes, filename: str) -> List[Dict]:
        """Parse CSV or Excel file into list of row dicts."""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.csv'):
            return self.parse_csv(contents)
        elif filename_lower.endswith(('.xlsx', '.xls')):
            return self.parse_excel(contents)
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    
    def parse_csv(self, contents: bytes) -> List[Dict]:
        """Parse CSV file with BOM handling."""
        try:
            decoded = contents.decode('utf-8-sig')  # Strips BOM
        except:
            decoded = contents.decode('utf-8')
        
        reader = csv.DictReader(io.StringIO(decoded))
        
        rows = []
        for row in reader:
            normalized = {k.strip().lower(): v for k, v in row.items() if k}
            rows.append(normalized)
        
        return rows
    
    def parse_excel(self, contents: bytes) -> List[Dict]:
        """Parse Excel file."""
        if not EXCEL_SUPPORT:
            raise ValueError("Excel support not installed. Run: pip install pandas openpyxl")
        
        try:
            engine = 'openpyxl'
            df = pd.read_excel(io.BytesIO(contents), engine=engine, sheet_name=0)
            df = df.dropna(how='all')
            
            # Normalize column names
            df.columns = [str(col).strip().lower() for col in df.columns]
            
            rows = df.to_dict('records')
            
            # Convert pandas types to Python types
            normalized_rows = []
            for row in rows:
                normalized = {}
                for key, value in row.items():
                    if pd.isna(value):
                        normalized[key] = None
                    elif isinstance(value, (pd.Timestamp,)):
                        normalized[key] = value.isoformat()
                    else:
                        normalized[key] = str(value) if value is not None else None
                normalized_rows.append(normalized)
            
            return normalized_rows
        except Exception as e:
            logger.error(f"Excel parsing error: {e}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
    
    # ==========================================
    # ROW PARSING
    # ==========================================
    def parse_asin(self, row: dict) -> Optional[str]:
        """Extract ASIN from row."""
        asin = (
            row.get("asin") or 
            row.get("amazon asin") or
            row.get("product asin") or
            row.get("product_asin") or
            ""
        )
        asin = str(asin).strip().upper()
        
        if len(asin) == 10 and re.match(r'^[A-Z0-9]{10}$', asin):
            return asin
        
        # Try to find ASIN pattern in any column
        for value in row.values():
            val = str(value).strip().upper() if value else ""
            if len(val) == 10 and re.match(r'^[A-Z0-9]{10}$', val):
                return val
        
        return None
    
    def parse_cost(self, row: dict) -> Optional[float]:
        """Extract buy cost from row."""
        cost_str = (
            row.get("buy_cost") or
            row.get("buy cost") or
            row.get("cost") or
            row.get("price") or
            row.get("unit cost") or
            row.get("unit_cost") or
            row.get("unit price") or
            row.get("unit_price") or
            ""
        )
        if not cost_str:
            return None
        
        try:
            return float(str(cost_str).replace("$", "").replace(",", "").strip())
        except:
            return None
    
    def parse_moq(self, row: dict) -> int:
        """Extract MOQ from row."""
        moq_str = (
            row.get("moq") or
            row.get("qty") or
            row.get("quantity") or
            row.get("min qty") or
            row.get("min_qty") or
            row.get("min order") or
            row.get("min_order") or
            ""
        )
        if not moq_str:
            return 1
        
        try:
            return max(1, int(float(str(moq_str).replace(",", "").strip())))
        except:
            return 1
    
    def parse_notes(self, row: dict) -> Optional[str]:
        """Extract notes from row."""
        notes = row.get("notes") or row.get("note") or row.get("comments") or ""
        return str(notes).strip() if notes else None
    
    # ==========================================
    # BATCH DATABASE OPERATIONS
    # ==========================================
    def batch_get_or_create_products(self, asins: List[str]) -> Dict[str, str]:
        """Get or create products in batch. Returns {asin: product_id}."""
        unique_asins = list(set([a for a in asins if a]))
        if not unique_asins:
            return {}
        
        uncached = [a for a in unique_asins if a not in self.product_cache]
        
        if uncached:
            # Get existing
            existing = supabase.table("products")\
                .select("id, asin")\
                .eq("user_id", self.user_id)\
                .in_("asin", uncached)\
                .execute()
            
            for p in (existing.data or []):
                self.product_cache[p["asin"]] = p["id"]
            
            # Create missing
            still_missing = [a for a in uncached if a not in self.product_cache]
            if still_missing:
                new_products = [
                    {"user_id": self.user_id, "asin": asin, "status": "pending"}
                    for asin in still_missing
                ]
                
                created = supabase.table("products").insert(new_products).execute()
                for p in (created.data or []):
                    self.product_cache[p["asin"]] = p["id"]
        
        return {a: self.product_cache.get(a) for a in unique_asins}
    
    def batch_upsert_deals(self, deals: List[dict]) -> dict:
        """Batch upsert deals (product_sources)."""
        if not deals:
            return {"processed": 0}
        
        # Supabase upsert
        result = supabase.table("product_sources")\
            .upsert(deals, on_conflict="product_id,supplier_id")\
            .execute()
        
        return {"processed": len(result.data or [])}
    
    # ==========================================
    # MAIN PROCESSING
    # ==========================================
    async def process(self, contents: bytes, filename: str):
        """Main processing function - runs in background."""
        try:
            # Parse file
            self.update_progress(0, 1, "parsing")
            rows = self.parse_file(contents, filename)
            total = len(rows)
            
            if total == 0:
                self.complete_job({"error": "No valid rows found", "products_created": 0, "deals_processed": 0})
                return
            
            self.update_progress(0, total, "processing")
            
            results = {
                "products_created": 0,
                "deals_processed": 0,
                "errors": [],
                "total_rows": total
            }
            
            # Process in batches
            for batch_start in range(0, total, self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, total)
                batch = rows[batch_start:batch_end]
                
                # Parse all rows in batch
                parsed_rows = []
                asins = []
                
                for idx, row in enumerate(batch):
                    row_num = batch_start + idx + 2  # +2 for header and 0-index
                    
                    asin = self.parse_asin(row)
                    if not asin:
                        results["errors"].append(f"Row {row_num}: Invalid or missing ASIN")
                        continue
                    
                    parsed = {
                        "asin": asin,
                        "buy_cost": self.parse_cost(row),
                        "moq": self.parse_moq(row),
                        "notes": self.parse_notes(row)
                    }
                    
                    parsed_rows.append(parsed)
                    asins.append(asin)
                
                # Batch create products
                products_before = len(self.product_cache)
                product_map = self.batch_get_or_create_products(asins)
                products_after = len(self.product_cache)
                results["products_created"] += (products_after - products_before)
                
                # Build deals - ALL tied to the selected supplier
                deals_to_upsert = []
                for parsed in parsed_rows:
                    product_id = product_map.get(parsed["asin"])
                    if not product_id:
                        continue
                    
                    deal = {
                        "product_id": product_id,
                        "supplier_id": self.supplier_id,  # FROM UPLOAD SELECTION
                        "buy_cost": parsed["buy_cost"],
                        "moq": parsed["moq"],
                        "source": "excel" if filename.lower().endswith(('.xlsx', '.xls')) else "csv",
                        "source_detail": filename,
                        "notes": parsed["notes"],
                        "stage": "new",
                        "is_active": True
                    }
                    deals_to_upsert.append(deal)
                
                # Batch upsert deals
                if deals_to_upsert:
                    deal_result = self.batch_upsert_deals(deals_to_upsert)
                    results["deals_processed"] += deal_result.get("processed", 0)
                
                # Update progress
                self.update_progress(batch_end, total)
                
                # Small delay to prevent overwhelming the database
                await asyncio.sleep(0.05)
            
            # Trim errors if too many
            if len(results["errors"]) > 50:
                results["errors"] = results["errors"][:50] + [f"... and {len(results['errors']) - 50} more errors"]
            
            self.complete_job(results)
            
        except Exception as e:
            import traceback
            logger.error(f"File processing error: {e}\n{traceback.format_exc()}")
            self.fail_job(str(e))


async def process_file_background(user_id: str, job_id: str, supplier_id: str, contents: bytes, filename: str):
    """Run file processing in background."""
    processor = FileProcessor(user_id, job_id, supplier_id)
    await processor.process(contents, filename)

