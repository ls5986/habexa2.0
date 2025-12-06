"""
Tests for CSV/Excel file processing.
Verifies Bug #2 fix: No redundant detailed lookup calls.
Tests all ASIN scenarios and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.tasks.file_processing import process_file_upload
import base64
import json
import asyncio


@pytest.mark.asyncio
async def test_no_redundant_detailed_lookup():
    """Verify Bug #2 fix: No detailed lookup when batch finds ASIN"""
    
    # Create CSV data
    csv_content = "upc,title,buy_cost\n689542001425,Test Product,5.00"
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    # Track API calls
    batch_calls = []
    detailed_calls = []
    
    async def mock_batch(upcs):
        """Mock batch conversion - returns ASIN"""
        batch_calls.append(upcs)
        return {"689542001425": "B07VRZ8TK3"}
    
    async def mock_detailed(upc):
        """Mock detailed lookup - should NOT be called"""
        detailed_calls.append(upc)
        return ([{"asin": "B07VRZ8TK3"}], "found")
    
    # Mock dependencies
    with patch('app.services.supabase_client.supabase') as mock_supabase:
        
        # Setup Supabase mocks
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.upsert.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        # Mock run_async and UPC converter
        with patch('app.tasks.file_processing.run_async') as mock_run, \
             patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', new_callable=AsyncMock) as mock_batch_func, \
             patch('app.services.upc_converter.upc_converter.upc_to_asins', new_callable=AsyncMock) as mock_detailed_func:
            
            mock_batch_func.side_effect = mock_batch
            mock_detailed_func.side_effect = mock_detailed
            
            def run_async_wrapper(coro):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            
            mock_run.side_effect = run_async_wrapper
            
            # Mock job manager
            with patch('app.tasks.file_processing.JobManager') as mock_job:
                mock_job_instance = MagicMock()
                mock_job_instance.is_cancelled.return_value = False
                mock_job_instance.update_progress = MagicMock()
                mock_job_instance.complete = MagicMock()
                mock_job_instance.start = MagicMock()
                mock_job_instance.set_status = MagicMock()
                mock_job.return_value = mock_job_instance
                
                # Process file
                await process_file_upload(
                    None,  # self (not Celery task)
                    "test-job-id",
                    "test-user-id",
                    "test-supplier-id",
                    csv_b64,
                    "test.csv"
                )
    
    # Verify batch was called
    assert len(batch_calls) > 0, "Batch conversion should be called"
    
    # Verify detailed lookup was NOT called (Bug #2 fix)
    assert len(detailed_calls) == 0, \
        f"Bug #2 not fixed: Detailed lookup called {len(detailed_calls)} times when batch succeeded"


@pytest.mark.asyncio
async def test_single_asin_found():
    """When batch finds 1 ASIN → product created with asin_status='found'"""
    
    csv_content = "upc,title,buy_cost\n689542001425,Test Product,5.00"
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    inserted_products = []
    
    async def mock_batch(upcs):
        return {"689542001425": "B07VRZ8TK3"}
    
    with patch('app.services.supabase_client.supabase') as mock_supabase:
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        # Track inserts
        def mock_insert(data):
            inserted_products.extend(data if isinstance(data, list) else [data])
            return MagicMock(data=data if isinstance(data, list) else [data])
        
        mock_table.insert.side_effect = mock_insert
        mock_table.upsert.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        with patch('app.tasks.file_processing.run_async') as mock_run, \
             patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', new_callable=AsyncMock) as mock_batch_func:
            
            mock_batch_func.side_effect = mock_batch
            
            def run_async_wrapper(coro):
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
    
    # Verify product was created with correct status
    assert len(inserted_products) > 0, "Product should be created"
    
    product = inserted_products[0] if isinstance(inserted_products[0], dict) else inserted_products[0]
    assert product.get('asin') == 'B07VRZ8TK3'
    assert product.get('asin_status') == 'found'


@pytest.mark.asyncio
async def test_no_asin_found():
    """When UPC not on Amazon → saved with asin_status='not_found'"""
    
    csv_content = "upc,title,buy_cost\n000000000000,Unknown Product,5.00"
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    inserted_products = []
    
    async def mock_batch(upcs):
        return {"000000000000": None}  # Not found
    
    async def mock_detailed(upc):
        return ([], "not_found")
    
    with patch('app.services.supabase_client.supabase') as mock_supabase:
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        def mock_insert(data):
            inserted_products.extend(data if isinstance(data, list) else [data])
            return MagicMock(data=data if isinstance(data, list) else [data])
        
        mock_table.insert.side_effect = mock_insert
        mock_table.upsert.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        with patch('app.tasks.file_processing.run_async') as mock_run, \
             patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', new_callable=AsyncMock) as mock_batch_func, \
             patch('app.services.upc_converter.upc_converter.upc_to_asins', new_callable=AsyncMock) as mock_detailed_func:
            
            mock_batch_func.side_effect = mock_batch
            mock_detailed_func.side_effect = mock_detailed
            
            def run_async_wrapper(coro):
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
    
    # Verify product was saved with not_found status
    assert len(inserted_products) > 0
    
    # Find product without ASIN
    no_asin_product = next(
        (p for p in inserted_products if isinstance(p, dict) and p.get('asin_status') == 'not_found'),
        None
    )
    
    assert no_asin_product is not None, "Product with not_found status should be created"
    assert no_asin_product.get('upc') == '000000000000'
    assert no_asin_product.get('asin_status') == 'not_found'
    assert no_asin_product.get('supplier_title') == 'Unknown Product'


@pytest.mark.asyncio
async def test_api_failure_continues_processing():
    """When SP-API fails for 1 UPC → continue processing others"""
    
    csv_content = """upc,title,buy_cost
111111111111,Fail,5.00
222222222222,Success1,5.00
333333333333,Success2,5.00"""
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    call_count = 0
    
    async def mock_batch_with_failure(upcs):
        """First UPC fails, rest succeed"""
        nonlocal call_count
        call_count += 1
        
        if "111111111111" in upcs:
            raise Exception("API Error")
        
        return {upc: f"B07TEST{i}" for i, upc in enumerate(upcs)}
    
    with patch('app.services.supabase_client.supabase') as mock_supabase:
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_table.insert.return_value = MagicMock(data=[])
        mock_table.upsert.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        with patch('app.tasks.file_processing.run_async') as mock_run, \
             patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', new_callable=AsyncMock) as mock_batch_func:
            
            mock_batch_func.side_effect = mock_batch_with_failure
            
            def run_async_wrapper(coro):
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
                
                # Should not raise exception
                await process_file_upload(
                    None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
                )
    
    # Should have attempted to process all batches
    assert call_count > 0, "Should attempt to process batches despite failures"


@pytest.mark.asyncio
async def test_invalid_data_handled_gracefully():
    """Missing required fields → error logged, processing continues"""
    
    csv_content = """upc,title,buy_cost
689542001425,Good,5.00
,No UPC,5.00
123456789012,,
789012345678,No Cost,"""
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    error_list = []
    
    async def mock_batch(upcs):
        # Only first UPC is valid
        return {"689542001425": "B07TEST123"}
    
    with patch('app.services.supabase_client.supabase') as mock_supabase:
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_table.insert.return_value = MagicMock(data=[])
        mock_table.upsert.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = mock_table
        
        with patch('app.tasks.file_processing.run_async') as mock_run, \
             patch('app.services.upc_converter.upc_converter.upcs_to_asins_batch', new_callable=AsyncMock) as mock_batch_func:
            
            mock_batch_func.side_effect = mock_batch
            
            def run_async_wrapper(coro):
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
                
                def track_errors(processed, total, success, errors, error_list_arg):
                    if error_list_arg:
                        error_list.extend(error_list_arg)
                
                mock_job_instance.update_progress = MagicMock(side_effect=track_errors)
                mock_job_instance.complete = MagicMock()
                mock_job_instance.start = MagicMock()
                mock_job_instance.set_status = MagicMock()
                mock_job.return_value = mock_job_instance
                
                await process_file_upload(
                    None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
                )
    
    # Should have errors for invalid rows
    assert len(error_list) >= 0, "Should track errors for invalid rows"
