"""
Tests for ASIN selection and manual entry endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
import json


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock authenticated user."""
    with patch('app.api.deps.get_current_user') as mock:
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock.return_value = mock_user
        yield mock_user


@pytest.fixture
def mock_supabase():
    """Mock Supabase for database operations."""
    with patch('app.services.supabase_client.supabase') as mock:
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock.table.return_value = mock_table
        yield mock


@pytest.mark.asyncio
async def test_select_asin_endpoint(client, mock_current_user, mock_supabase):
    """POST /products/{id}/select-asin updates product and queues analysis"""
    
    # Create product with multiple ASINs
    product_data = {
        "id": "test-product-id",
        "user_id": "test-user-id",
        "asin": None,
        "asin_status": "multiple_found",
        "potential_asins": [
            {"asin": "B07AAA1111", "title": "Red Variant", "image": "url1"},
            {"asin": "B07BBB2222", "title": "Blue Variant", "image": "url2"}
        ],
        "upc": "689542001425"
    }
    
    # Mock Supabase responses
    def mock_execute():
        result = MagicMock()
        if mock_supabase.table().select().eq().single().execute.called:
            result.data = product_data
        elif mock_supabase.table().update().eq().execute.called:
            result.data = [{**product_data, "asin": "B07AAA1111", "asin_status": "found", "potential_asins": None}]
        else:
            result.data = []
        return result
    
    mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data=product_data)
    mock_supabase.table().update().eq().execute.return_value = MagicMock(data=[{**product_data, "asin": "B07AAA1111"}])
    mock_supabase.table().insert().execute.return_value = MagicMock(data=[{"id": "test-job-id"}])
    
    # Mock Keepa and analysis
    with patch('app.services.keepa_client.get_keepa_client') as mock_keepa, \
         patch('app.tasks.analysis.batch_analyze_products') as mock_analyze:
        
        mock_keepa_client = MagicMock()
        mock_keepa_client.get_product = MagicMock(return_value={"parent_asin": None})
        mock_keepa.return_value = mock_keepa_client
        
        mock_analyze.delay = MagicMock()
        
        # User selects first ASIN
        response = client.post(
            "/api/v1/products/test-product-id/select-asin",
            json={"asin": "B07AAA1111"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update was called
        assert mock_supabase.table().update().eq().execute.called, "Product should be updated"
        
        # Verify analysis was queued
        assert mock_analyze.delay.called, "Analysis should be queued"


@pytest.mark.asyncio
async def test_manual_asin_endpoint(client, mock_current_user, mock_supabase):
    """PATCH /products/{id}/manual-asin allows user to enter ASIN"""
    
    # Create product with no ASIN
    product_data = {
        "id": "test-product-id",
        "user_id": "test-user-id",
        "asin": None,
        "asin_status": "not_found",
        "upc": "689542001425"
    }
    
    mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data=product_data)
    mock_supabase.table().update().eq().execute.return_value = MagicMock(data=[{**product_data, "asin": "B07VRZ8TK3", "asin_status": "manual"}])
    mock_supabase.table().insert().execute.return_value = MagicMock(data=[{"id": "test-job-id"}])
    
    # Mock Keepa
    with patch('app.services.keepa_client.get_keepa_client') as mock_keepa, \
         patch('app.services.sp_api_client.sp_api_client') as mock_sp_api, \
         patch('app.tasks.analysis.batch_analyze_products') as mock_analyze:
        
        mock_keepa_client = MagicMock()
        mock_keepa_client.get_product = MagicMock(return_value={"title": "Test Product"})
        mock_keepa.return_value = mock_keepa_client
        
        mock_sp_api.get_catalog_item = MagicMock(return_value={"title": "Test Product"})
        mock_analyze.delay = MagicMock()
        
        # User enters ASIN manually
        response = client.patch(
            "/api/v1/products/test-product-id/manual-asin",
            json={"asin": "B07VRZ8TK3"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update was called
        assert mock_supabase.table().update().eq().execute.called, "Product should be updated"
        
        # Verify analysis was queued
        assert mock_analyze.delay.called, "Analysis should be queued"


@pytest.mark.asyncio
async def test_manual_asin_validates_format(client, mock_current_user, mock_supabase):
    """Manual ASIN entry rejects invalid formats"""
    
    product_data = {
        "id": "test-product-id",
        "user_id": "test-user-id",
        "asin_status": "not_found"
    }
    
    mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data=product_data)
    
    # Try invalid ASIN (too short)
    response = client.patch(
        "/api/v1/products/test-product-id/manual-asin",
        json={"asin": "B07"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 400, f"Should reject short ASIN, got {response.status_code}"
    
    # Try invalid ASIN (too long)
    response = client.patch(
        "/api/v1/products/test-product-id/manual-asin",
        json={"asin": "B07VRZ8TK3XXX"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 400, f"Should reject long ASIN, got {response.status_code}"
    
    # Valid ASIN should work
    mock_supabase.table().update().eq().execute.return_value = MagicMock(data=[{**product_data, "asin": "B07VRZ8TK3"}])
    mock_supabase.table().insert().execute.return_value = MagicMock(data=[{"id": "test-job-id"}])
    
    with patch('app.services.keepa_client.get_keepa_client'), \
         patch('app.tasks.analysis.batch_analyze_products'):
        
        response = client.patch(
            "/api/v1/products/test-product-id/manual-asin",
            json={"asin": "B07VRZ8TK3"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200, f"Valid ASIN should work, got {response.status_code}"


@pytest.mark.asyncio
async def test_select_asin_validates_potential_asins(client, mock_current_user, mock_supabase):
    """Select ASIN endpoint validates selected ASIN is in potential_asins"""
    
    product_data = {
        "id": "test-product-id",
        "user_id": "test-user-id",
        "asin_status": "multiple_found",
        "potential_asins": [
            {"asin": "B07AAA1111", "title": "Red"},
            {"asin": "B07BBB2222", "title": "Blue"}
        ]
    }
    
    mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data=product_data)
    
    # Try to select ASIN not in potential_asins
    response = client.post(
        "/api/v1/products/test-product-id/select-asin",
        json={"asin": "B07INVALID"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 400, f"Should reject ASIN not in potential_asins, got {response.status_code}"

