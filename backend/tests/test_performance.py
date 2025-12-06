"""
Performance tests to verify API call counts and processing speed.
Verifies bug fixes result in correct performance.
"""
import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.tasks.file_processing import process_file_upload
import base64


@pytest.mark.asyncio
async def test_api_call_count_for_1000_products():
    """Verify 1,000 products = ~50 API calls (not 1,000+)"""
    
    # Create 1,000 test products
    csv_lines = ["upc,title,buy_cost"]
    for i in range(1000):
        upc = f"{i:012d}"
        csv_lines.append(f"{upc},Product{i},5.00")
    
    csv_content = "\n".join(csv_lines)
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    batch_call_count = 0
    detailed_call_count = 0
    
    async def mock_batch(upcs):
        """Track batch calls"""
        nonlocal batch_call_count
        batch_call_count += 1
        # Return ASIN for each UPC
        return {upc: f"B07TEST{i:03d}" for i, upc in enumerate(upcs)}
    
    async def mock_detailed(upc):
        """Track detailed calls - should NOT be called"""
        nonlocal detailed_call_count
        detailed_call_count += 1
        return ([{"asin": "B07TEST"}], "found")
    
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
                
                start_time = time.time()
                await process_file_upload(
                    None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
                )
                elapsed = time.time() - start_time
            
            # Should make 50 batch calls (1000 ÷ 20 = 50)
            assert batch_call_count == 50, \
                f"Expected 50 batch calls for 1000 products, got {batch_call_count}"
            
            # Detailed lookup should NOT be called (Bug #2 fix)
            assert detailed_call_count == 0, \
                f"Bug #2 not fixed: Detailed lookup called {detailed_call_count} times"


@pytest.mark.asyncio
async def test_no_redundant_calls_at_scale():
    """Verify detailed lookup NOT called when batch succeeds (Bug #2)"""
    
    # Create 100 test products
    csv_lines = ["upc,title,buy_cost"]
    for i in range(100):
        upc = f"{i:012d}"
        csv_lines.append(f"{upc},Product{i},5.00")
    
    csv_content = "\n".join(csv_lines)
    csv_b64 = base64.b64encode(csv_content.encode()).decode()
    
    batch_calls = []
    detailed_calls = []
    
    async def mock_batch(upcs):
        """Track batch calls"""
        batch_calls.append(len(upcs))
        return {upc: f"B07TEST{i:03d}" for i, upc in enumerate(upcs)}
    
    async def mock_detailed(upc):
        """Track detailed calls - should NOT be called"""
        detailed_calls.append(upc)
        return ([{"asin": "B07TEST"}], "found")
    
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
            
            # Batch called (5 times for 100 products: 20+20+20+20+20)
            assert len(batch_calls) == 5, \
                f"Expected 5 batch calls for 100 products, got {len(batch_calls)}"
            
            # All batches should be ≤ 20
            assert all(count <= 20 for count in batch_calls), \
                f"All batches should be ≤ 20, got: {batch_calls}"
            
            # Detailed should NOT be called (all batch succeeded)
            assert len(detailed_calls) == 0, \
                f"Bug #2 still exists! Detailed lookup called {len(detailed_calls)} times when batch succeeded"


@pytest.mark.asyncio
async def test_batch_size_consistency():
    """Verify all batches use correct size (20) except last"""
    
    # Test with various sizes
    for total_products in [20, 50, 100, 250, 1000]:
        csv_lines = ["upc,title,buy_cost"]
        for i in range(total_products):
            upc = f"{i:012d}"
            csv_lines.append(f"{upc},Product{i},5.00")
        
        csv_content = "\n".join(csv_lines)
        csv_b64 = base64.b64encode(csv_content.encode()).decode()
        
        batch_sizes = []
        
        async def mock_batch(upcs):
            batch_sizes.append(len(upcs))
            return {upc: f"B07TEST{i:03d}" for i, upc in enumerate(upcs)}
        
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
                    mock_job_instance.update_progress = MagicMock()
                    mock_job_instance.complete = MagicMock()
                    mock_job_instance.start = MagicMock()
                    mock_job_instance.set_status = MagicMock()
                    mock_job.return_value = mock_job_instance
                    
                    await process_file_upload(
                        None, "test-job", "test-user", "test-supplier", csv_b64, "test.csv"
                    )
            
            # All batches except last should be exactly 20
            if len(batch_sizes) > 1:
                assert all(size == 20 for size in batch_sizes[:-1]), \
                    f"For {total_products} products: All batches except last should be 20, got {batch_sizes}"
                
                # Last batch should be ≤ 20
                assert batch_sizes[-1] <= 20, \
                    f"For {total_products} products: Last batch should be ≤ 20, got {batch_sizes[-1]}"
            
            # Expected number of batches
            expected_batches = (total_products + 19) // 20  # Ceiling division
            assert len(batch_sizes) == expected_batches, \
                f"For {total_products} products: Expected {expected_batches} batches, got {len(batch_sizes)}"

