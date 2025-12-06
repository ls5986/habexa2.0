"""
Tests for UPC to ASIN conversion logic.
Verifies Bug #1 fix: Correct batch size (20, not 100).
"""
# Import conftest first to set up test environment
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.upc_converter import UPCConverter


@pytest.mark.asyncio
async def test_upc_batching_uses_correct_size():
    """Verify Bug #1 fix: upcs_to_asins_batch limits to 20 UPCs per call"""
    
    # Create 50 test UPCs
    upcs = [f"00000000000{i:02d}" for i in range(50)]
    
    # Mock SP-API to track call count and batch sizes
    call_tracker = []
    
    async def mock_search_catalog_items(identifiers, identifiers_type, marketplace_id):
        """Track each batch call."""
        call_tracker.append({
            'count': len(identifiers),
            'identifiers': identifiers
        })
        # Return mock response
        return {
            "items": [
                {"asin": f"B07TEST{i:03d}", "summaries": [{"itemName": f"Product {i}"}]}
                for i in range(len(identifiers))
            ]
        }
    
    with patch('app.services.sp_api_client.sp_api_client.search_catalog_items', new_callable=AsyncMock, side_effect=mock_search_catalog_items):
        converter = UPCConverter()
        
        # Process UPCs - method should only process first 20
        result = await converter.upcs_to_asins_batch(upcs)
        
        # Method only processes first 20 UPCs per call (chunking happens in file_processing.py)
        assert len(call_tracker) == 1, f"Expected 1 API call for batch method, got {len(call_tracker)}"
        
        # Should only process 20 UPCs even though 50 were passed
        assert call_tracker[0]['count'] == 20, \
            f"Batch should process only 20 UPCs (SP-API limit), got {call_tracker[0]['count']}"
        
        # Result should only contain 20 UPCs
        assert len(result) == 20, \
            f"Result should contain 20 UPCs, got {len(result)}"


@pytest.mark.asyncio
async def test_upc_batch_size_limit():
    """Verify batch size is capped at 20 (SP-API limit)"""
    
    # Create 100 UPCs
    upcs = [f"{i:012d}" for i in range(100)]
    
    call_tracker = []
    
    async def mock_search(identifiers, identifiers_type, marketplace_id):
        call_tracker.append(len(identifiers))
        return {"items": [{"asin": "B07TEST"} for _ in identifiers]}
    
    with patch('app.services.sp_api_client.sp_api_client.search_catalog_items', side_effect=mock_search):
        converter = UPCConverter()
        await converter.upcs_to_asins_batch(upcs)
        
        # Should make 5 calls (100 ÷ 20 = 5)
        assert len(call_tracker) == 5
        
        # All batches should be ≤ 20
        assert all(count <= 20 for count in call_tracker), \
            f"All batches should be ≤ 20, got: {call_tracker}"


@pytest.mark.asyncio
async def test_upc_normalization():
    """Verify UPCs are normalized correctly before batching"""
    
    # UPCs with various formats
    upcs = [
        "689542001425",      # Standard
        "689-542-001-425",   # With dashes
        "689 542 001 425",   # With spaces
        "0689542001425.0"    # With leading zero and decimal
    ]
    
    async def mock_search(identifiers, identifiers_type, marketplace_id):
        # All should be normalized to digits only
        assert all(upc.isdigit() for upc in identifiers), \
            f"UPCs should be normalized to digits only: {identifiers}"
        return {"items": [{"asin": "B07TEST"} for _ in identifiers]}
    
    with patch('app.services.sp_api_client.sp_api_client.search_catalog_items', side_effect=mock_search):
        converter = UPCConverter()
        await converter.upcs_to_asins_batch(upcs)


@pytest.mark.asyncio
async def test_upc_to_asins_returns_multiple():
    """Verify upc_to_asins returns all ASINs when multiple found"""
    
    async def mock_search(identifiers, identifiers_type, marketplace_id):
        # Return multiple items for same UPC
        return {
            "items": [
                {"asin": "B07AAA1111", "summaries": [{"itemName": "Red Variant"}]},
                {"asin": "B07BBB2222", "summaries": [{"itemName": "Blue Variant"}]}
            ]
        }
    
    with patch('app.services.sp_api_client.sp_api_client.search_catalog_items', side_effect=mock_search):
        converter = UPCConverter()
        asins, status = await converter.upc_to_asins("689542001425")
        
        assert status == "multiple"
        assert len(asins) == 2
        assert asins[0]["asin"] == "B07AAA1111"
        assert asins[1]["asin"] == "B07BBB2222"


@pytest.mark.asyncio
async def test_upc_to_asins_returns_single():
    """Verify upc_to_asins returns single ASIN when one found"""
    
    async def mock_search(identifiers, identifiers_type, marketplace_id):
        return {
            "items": [
                {"asin": "B07TEST123", "summaries": [{"itemName": "Single Product"}]}
            ]
        }
    
    with patch('app.services.sp_api_client.sp_api_client.search_catalog_items', side_effect=mock_search):
        converter = UPCConverter()
        asins, status = await converter.upc_to_asins("689542001425")
        
        assert status == "found"
        assert len(asins) == 1
        assert asins[0]["asin"] == "B07TEST123"


@pytest.mark.asyncio
async def test_upc_to_asins_not_found():
    """Verify upc_to_asins returns not_found when no ASINs"""
    
    async def mock_search(identifiers, identifiers_type, marketplace_id):
        return {"items": []}
    
    with patch('app.services.sp_api_client.sp_api_client.search_catalog_items', side_effect=mock_search):
        converter = UPCConverter()
        asins, status = await converter.upc_to_asins("000000000000")
        
        assert status == "not_found"
        assert len(asins) == 0

