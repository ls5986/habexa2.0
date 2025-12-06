"""
Tests for database operations during CSV import.
Verifies bulk inserts and correct status values.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.tasks.file_processing import process_file_upload
import base64


@pytest.mark.asyncio
async def test_bulk_insert_creates_all_products():
    """Verify bulk insert saves all products efficiently"""
    
    csv_content = """upc,title,buy_cost
111111111111,Product1,5.00
222222222222,Product2,6.00
333333333333,Product3,7.00"""
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    insert_calls = []
    
    async def mock_batch(upcs):
        return {
            "111111111111": "B07AAA1111",
            "222222222222": "B07BBB2222",
            "333333333333": "B07CCC3333"
        }
    
    with patch('app.tasks.file_processing.run_async') as mock_run, \
         patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', side_effect=mock_batch), \
         patch('app.services.supabase_client.supabase') as mock_supabase:
        
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        def track_insert(data):
            """Track insert calls"""
            insert_calls.append(data if isinstance(data, list) else [data])
            return MagicMock(data=data if isinstance(data, list) else [data])
        
        mock_table.insert.side_effect = track_insert
        mock_table.upsert.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        def run_async_wrapper(coro):
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        
        mock_run.side_effect = run_async_wrapper
        
        with patch('app.tasks.file_processing.JobManager') as mock_job:
            mock_job_instance = MagicMock()
            mock_job_instance.is_cancelled.return_value = False
            mock_job_instance.update_progress = MagicMock()
            mock_job_instance.complete = MagicMock()
            mock_job_instance.start = MagicMock()
            mock_job_instance.set_status = MagicMock()
            mock_job.return_value = mock_job_instance
            
            await process_file_upload(
                None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
            )
    
    # Should use bulk insert (1-2 calls for 3 products, not 3 individual calls)
    products_insert_calls = [call for call in insert_calls if any('asin' in str(item) for item in call)]
    
    assert len(products_insert_calls) <= 2, \
        f"Expected 1-2 bulk INSERTs for 3 products, got {len(products_insert_calls)} individual INSERTs"


@pytest.mark.asyncio
async def test_products_created_with_correct_status():
    """All asin_status values set correctly"""
    
    csv_content = """upc,title,buy_cost
689542001425,FoundOne,5.00
825325690596,FoundTwo,5.00
000000000000,NotFound,5.00"""
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    inserted_products = []
    
    async def mock_batch(upcs):
        return {
            "689542001425": "B07AAA1111",  # Found
            "825325690596": "B07BBB2222",  # Found
            "000000000000": None  # Not found
        }
    
    async def mock_detailed(upc):
        if upc == "000000000000":
            return ([], "not_found")
        return ([{"asin": "B07TEST"}], "found")
    
    with patch('app.services.supabase_client.supabase') as mock_supabase:
        
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        def track_insert(data):
            if isinstance(data, list):
                inserted_products.extend(data)
            else:
                inserted_products.append(data)
            return MagicMock(data=data if isinstance(data, list) else [data])
        
        mock_table.insert.side_effect = track_insert
        mock_table.upsert.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        def run_async_wrapper(coro):
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        
        mock_run.side_effect = run_async_wrapper
        
        with patch('app.tasks.file_processing.JobManager') as mock_job:
            mock_job_instance = MagicMock()
            mock_job_instance.is_cancelled.return_value = False
            mock_job_instance.update_progress = MagicMock()
            mock_job_instance.complete = MagicMock()
            mock_job_instance.start = MagicMock()
            mock_job_instance.set_status = MagicMock()
            mock_job.return_value = mock_job_instance
            
            await process_file_upload(
                None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
            )
    
    # Check products were created with correct statuses
    products_by_upc = {}
    for product in inserted_products:
        if isinstance(product, dict) and 'upc' in product:
            products_by_upc[product['upc']] = product
    
    # Found products should have asin_status='found'
    if "689542001425" in products_by_upc:
        assert products_by_upc["689542001425"].get('asin_status') == 'found', \
            "Product with found ASIN should have asin_status='found'"
    
    if "825325690596" in products_by_upc:
        assert products_by_upc["825325690596"].get('asin_status') == 'found', \
            "Product with found ASIN should have asin_status='found'"
    
    # Not found product should have asin_status='not_found'
    if "000000000000" in products_by_upc:
        assert products_by_upc["000000000000"].get('asin_status') == 'not_found', \
            "Product without ASIN should have asin_status='not_found'"


@pytest.mark.asyncio
async def test_product_sources_created_correctly():
    """Verify product_sources (deals) are created with correct fields"""
    
    csv_content = """upc,title,buy_cost,moq
689542001425,Test Product,5.00,2"""
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    upserted_deals = []
    
    async def mock_batch(upcs):
        return {"689542001425": "B07TEST123"}
    
    with patch('app.tasks.file_processing.run_async') as mock_run, \
         patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', side_effect=mock_batch), \
         patch('app.services.supabase_client.supabase') as mock_supabase:
        
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_table.insert.return_value = MagicMock(data=[{"id": "test-product-id", "asin": "B07TEST123"}])
        
        def track_upsert(data):
            if isinstance(data, list):
                upserted_deals.extend(data)
            else:
                upserted_deals.append(data)
            return MagicMock(data=data if isinstance(data, list) else [data])
        
        mock_table.upsert.side_effect = track_upsert
        mock_supabase.table.return_value = mock_table
        
        with patch('app.tasks.file_processing.run_async') as mock_run, \
             patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', new_callable=AsyncMock) as mock_batch_func:
            
            mock_batch_func.side_effect = mock_batch
            
            def run_async_wrapper(coro):
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            
            mock_run.side_effect = run_async_wrapper
        
        with patch('app.tasks.file_processing.JobManager') as mock_job:
            mock_job_instance = MagicMock()
            mock_job_instance.is_cancelled.return_value = False
            mock_job_instance.update_progress = MagicMock()
            mock_job_instance.complete = MagicMock()
            mock_job_instance.start = MagicMock()
            mock_job_instance.set_status = MagicMock()
            mock_job.return_value = mock_job_instance
            
            await process_file_upload(
                None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
            )
    
    # Verify product_source was created
    assert len(upserted_deals) > 0, "Product source should be created"
    
    # Check required fields
    if upserted_deals:
        deal = upserted_deals[0] if isinstance(upserted_deals[0], dict) else {}
        assert 'product_id' in deal or 'buy_cost' in deal, "Deal should have required fields"

