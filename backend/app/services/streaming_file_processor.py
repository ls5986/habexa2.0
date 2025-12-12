"""
Enterprise streaming file processor.
Handles 50,000+ products efficiently.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from collections import defaultdict
import os
from app.services.supabase_client import supabase
from app.services.parallel_upc_converter import ParallelUPCConverter
from app.services.api_batch_fetcher import APIBatchFetcher

logger = logging.getLogger(__name__)


class StreamingFileProcessor:
    """
    Process large files (50k+ rows) with streaming and parallelization.
    
    Performance targets:
    - 50,000 products: <5 minutes
    - 10,000 products: <1 minute
    - 1,000 products: <20 seconds
    """
    
    CHUNK_SIZE = 1000  # Process 1000 rows at a time
    DB_BATCH_SIZE = 1000  # Insert 1000 products per query
    API_BATCH_SIZE = 100  # Fetch API data for 100 ASINs at once
    MAX_API_WORKERS = 10  # 10 parallel API fetch workers
    
    def __init__(self, user_id: str, job_id: str):
        self.user_id = user_id
        self.job_id = job_id
        self.stats = {
            'total_rows': 0,
            'successful': 0,
            'failed': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'duration_seconds': 0
        }
    
    async def process_file(
        self,
        file_path: str,
        column_mapping: Dict[str, str],
        supplier_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for file processing.
        
        Args:
            file_path: Path to uploaded CSV/Excel file
            column_mapping: {csv_column: db_field} mapping
            supplier_id: Optional supplier ID
            
        Returns:
            Processing statistics
        """
        start_time = datetime.utcnow()
        logger.warning(f"🚀 ENTERPRISE FILE PROCESSOR STARTED: {file_path}")
        
        await self._update_job('parsing', 0)
        
        try:
            # ========================================
            # PHASE 1: STREAMING PARSE + DEDUPE
            # ========================================
            logger.info("📖 PHASE 1/5: Streaming file parse")
            
            all_products, unique_upcs = await self._stream_parse_file(
                file_path,
                column_mapping
            )
            
            self.stats['total_rows'] = len(all_products)
            
            logger.info(
                f"  ✅ Parsed {len(all_products)} products\n"
                f"  📊 Unique UPCs: {len(unique_upcs)}"
            )
            
            # ========================================
            # PHASE 2: PARALLEL UPC CONVERSION
            # ========================================
            logger.info("🔄 PHASE 2/5: UPC→ASIN conversion")
            
            await self._update_job('converting_upcs', len(all_products))
            
            upc_to_asin = await ParallelUPCConverter.convert(list(unique_upcs))
            
            # Apply ASINs to products
            for product in all_products:
                upc = product.get('upc')
                if upc and upc in upc_to_asin:
                    asin_data = upc_to_asin[upc]
                    product['asin'] = asin_data.get('asin')
                    product['asin_status'] = asin_data.get('status', 'found')
                    product['potential_asins'] = asin_data.get('potential_asins')
            
            # Track stats
            self.stats['cache_hits'] = sum(
                1 for v in upc_to_asin.values()
                if v.get('cache_age_days') is not None
            )
            self.stats['api_calls'] = len(unique_upcs) - self.stats['cache_hits']
            
            # ========================================
            # PHASE 3: BATCH DATABASE INSERT
            # ========================================
            logger.info("💾 PHASE 3/5: Batch database insert")
            
            await self._update_job('inserting', len(all_products))
            
            inserted_products = await self._batch_insert_products(all_products)
            
            self.stats['successful'] = len(inserted_products)
            
            logger.info(f"  ✅ Inserted {len(inserted_products)} products")
            
            # ========================================
            # PHASE 4: CREATE PRODUCT SOURCES
            # ========================================
            if supplier_id:
                logger.info("🔗 PHASE 4/5: Creating product-supplier links")
                
                await self._create_product_sources(
                    all_products,
                    inserted_products,
                    supplier_id
                )
            
            # ========================================
            # PHASE 5: PARALLEL API DATA FETCH
            # ========================================
            logger.info("🌐 PHASE 5/5: Fetching API data")
            
            await self._update_job('fetching_api', len(inserted_products))
            
            # Get unique ASINs
            unique_asins = list(set([
                p.get('asin')
                for p in inserted_products
                if p.get('asin') and not str(p.get('asin', '')).startswith('PENDING_')
            ]))
            
            logger.info(f"  Fetching API data for {len(unique_asins)} unique ASINs")
            
            if unique_asins:
                api_results = await self._parallel_api_fetch(unique_asins)
                logger.info(f"  ✅ API fetch complete: {api_results}")
            
            # ========================================
            # COMPLETE
            # ========================================
            self.stats['duration_seconds'] = (
                datetime.utcnow() - start_time
            ).total_seconds()
            
            await self._update_job('complete', self.stats['successful'])
            
            logger.warning(
                f"🎉 FILE PROCESSING COMPLETE:\n"
                f"  Total rows: {self.stats['total_rows']}\n"
                f"  Successful: {self.stats['successful']}\n"
                f"  Failed: {self.stats['failed']}\n"
                f"  Cache hits: {self.stats['cache_hits']}\n"
                f"  API calls: {self.stats['api_calls']}\n"
                f"  Duration: {self.stats['duration_seconds']:.1f}s\n"
                f"  Speed: {self.stats['total_rows'] / self.stats['duration_seconds']:.0f} rows/sec" if self.stats['duration_seconds'] > 0 else "  Speed: N/A"
            )
            
            return self.stats
            
        except Exception as e:
            logger.error(f"❌ File processing failed: {e}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            
            await self._update_job('failed', 0, error=str(e))
            raise
    
    async def _stream_parse_file(
        self,
        file_path: str,
        column_mapping: Dict[str, str]
    ) -> tuple[List[Dict[str, Any]], set]:
        """
        Stream parse file in chunks, deduplicate UPCs.
        
        Returns:
            (all_products, unique_upcs)
        """
        all_products = []
        unique_upcs = set()
        chunk_num = 0
        
        # Determine file type
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            # Stream read file
            if file_ext == '.csv':
                chunks = pd.read_csv(file_path, chunksize=self.CHUNK_SIZE, dtype=str, keep_default_na=False)
            else:  # Excel
                chunks = pd.read_excel(file_path, chunksize=self.CHUNK_SIZE, dtype=str, keep_default_na=False)
            
            for chunk_df in chunks:
                chunk_num += 1
                
                # Map columns
                chunk_products = self._map_columns(chunk_df, column_mapping)
                all_products.extend(chunk_products)
                
                # Collect unique UPCs
                for product in chunk_products:
                    upc = product.get('upc')
                    if upc and str(upc).strip():
                        unique_upcs.add(str(upc).strip())
                
                # Update progress
                await self._update_job('parsing', len(all_products))
                
                if chunk_num % 10 == 0:
                    logger.info(f"  Parsed {len(all_products)} rows...")
        
        except Exception as e:
            logger.error(f"Error parsing file: {e}", exc_info=True)
            raise
        
        return all_products, unique_upcs
    
    def _map_columns(
        self,
        df: pd.DataFrame,
        column_mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Map CSV columns to database fields."""
        products = []
        
        for _, row in df.iterrows():
            product = {'user_id': self.user_id}
            
            for csv_col, db_field in column_mapping.items():
                if csv_col in row:
                    value = row[csv_col]
                    
                    # Handle NaN/None
                    if pd.isna(value) or value == '' or value == 'nan':
                        value = None
                    else:
                        value = str(value).strip()
                    
                    product[db_field] = value
            
            products.append(product)
        
        return products
    
    async def _batch_insert_products(
        self,
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Insert products in batches of 1000.
        """
        inserted = []
        
        for i in range(0, len(products), self.DB_BATCH_SIZE):
            batch = products[i:i + self.DB_BATCH_SIZE]
            
            # Clean batch for insert
            cleaned_batch = []
            for p in batch:
                cleaned = {
                    'user_id': p.get('user_id'),
                    'upc': p.get('upc'),
                    'asin': p.get('asin'),
                    'asin_status': p.get('asin_status', 'found'),
                    'potential_asins': p.get('potential_asins'),
                    'title': p.get('title') or p.get('supplier_title'),
                    'supplier_title': p.get('supplier_title'),
                    'brand': p.get('brand'),
                    'category': p.get('category'),
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                # Remove None values
                cleaned = {k: v for k, v in cleaned.items() if v is not None}
                cleaned_batch.append(cleaned)
            
            try:
                response = supabase.table('products').insert(cleaned_batch).execute()
                
                if response.data:
                    inserted.extend(response.data)
                
                await self._update_job('inserting', len(inserted))
                
                if (i // self.DB_BATCH_SIZE) % 5 == 0:
                    logger.info(f"  Inserted {len(inserted)}/{len(products)} products...")
                
            except Exception as e:
                logger.error(f"Batch insert failed at {i}: {e}")
                self.stats['failed'] += len(batch)
        
        return inserted
    
    async def _create_product_sources(
        self,
        original_products: List[Dict[str, Any]],
        inserted_products: List[Dict[str, Any]],
        supplier_id: str
    ) -> None:
        """Create product_sources for pricing data."""
        sources = []
        
        # Create mapping by UPC for faster lookup
        inserted_by_upc = {}
        for p in inserted_products:
            upc = p.get('upc')
            if upc:
                inserted_by_upc[upc] = p
        
        for product in original_products:
            upc = product.get('upc')
            if upc and upc in inserted_by_upc:
                inserted = inserted_by_upc[upc]
                
                if inserted.get('id'):
                    # Parse wholesale_cost
                    wholesale_cost = None
                    cost_str = product.get('wholesale_cost') or product.get('buy_cost')
                    if cost_str:
                        try:
                            # Remove $ and commas
                            cost_str = str(cost_str).replace('$', '').replace(',', '').strip()
                            wholesale_cost = float(cost_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # Parse pack_size
                    pack_size = 1
                    pack_str = product.get('pack_size') or product.get('package_quantity')
                    if pack_str:
                        try:
                            pack_size = int(float(str(pack_str)))
                        except (ValueError, TypeError):
                            pass
                    
                    sources.append({
                        'product_id': inserted['id'],
                        'supplier_id': supplier_id,
                        'user_id': self.user_id,
                        'wholesale_cost': wholesale_cost,
                        'buy_cost': wholesale_cost,  # Same as wholesale for now
                        'pack_size': pack_size,
                        'upc': upc,
                        'supplier_sku': product.get('supplier_sku'),
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    })
        
        # Insert in batches
        for i in range(0, len(sources), self.DB_BATCH_SIZE):
            batch = sources[i:i + self.DB_BATCH_SIZE]
            
            try:
                supabase.table('product_sources').insert(batch).execute()
            except Exception as e:
                logger.error(f"Source batch insert failed: {e}")
        
        logger.info(f"  ✅ Created {len(sources)} product sources")
    
    async def _parallel_api_fetch(
        self,
        asins: List[str]
    ) -> Dict[str, Any]:
        """
        Fetch API data with parallel workers.
        """
        results = {
            'sp_api_success': 0,
            'keepa_success': 0,
            'updated': 0
        }
        
        # Split into parallel groups
        parallel_size = self.MAX_API_WORKERS * self.API_BATCH_SIZE
        
        for i in range(0, len(asins), parallel_size):
            batch_asins = asins[i:i + parallel_size]
            
            try:
                batch_results = await APIBatchFetcher.fetch_and_store(
                    asins=batch_asins,
                    user_id=self.user_id
                )
                
                results['sp_api_success'] += batch_results.get('sp_api_success', 0)
                results['keepa_success'] += batch_results.get('keepa_success', 0)
                results['updated'] += batch_results.get('updated', 0)
                
                await self._update_job('fetching_api', results['updated'])
                
                logger.info(
                    f"  API Progress: {min(i + parallel_size, len(asins))}/{len(asins)} ASINs"
                )
            except Exception as e:
                logger.error(f"API fetch batch failed: {e}")
        
        return results
    
    async def _update_job(
        self,
        status: str,
        processed: int,
        error: Optional[str] = None
    ) -> None:
        """Update job progress in database."""
        try:
            update_data = {
                'status': status,
                'current_phase': status,
                'processed_rows': processed,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if status == 'complete':
                update_data['completed_at'] = datetime.utcnow().isoformat()
                update_data['duration_seconds'] = int(self.stats['duration_seconds'])
                update_data['products_created'] = self.stats['successful']
                update_data['cache_hits'] = self.stats['cache_hits']
                update_data['api_calls_made'] = self.stats['api_calls']
                update_data['successful_rows'] = self.stats['successful']
                update_data['failed_rows'] = self.stats['failed']
            
            if error:
                update_data['error_summary'] = {'error': error}
            
            supabase.table('upload_jobs').update(update_data).eq(
                'id', self.job_id
            ).execute()
            
        except Exception as e:
            logger.debug(f"Job update failed (non-critical): {e}")

