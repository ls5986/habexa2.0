"""
Shared pytest fixtures for CSV import tests.
"""
# CRITICAL: Set test environment BEFORE any imports
import os
import sys
from unittest.mock import MagicMock
import types

os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"

# Mock Settings module BEFORE any app imports
# This prevents Pydantic validation errors during tests
class MockSettings:
    """Mock settings that returns test values."""
    SUPABASE_URL = "https://test.supabase.co"
    SUPABASE_ANON_KEY = "test_anon_key"
    SUPABASE_SERVICE_ROLE_KEY = "test_service_key"
    MARKETPLACE_ID = "ATVPDKIKX0DER"
    FRONTEND_URL = "http://localhost:3002"
    BACKEND_URL = "http://localhost:8000"
    API_V1_PREFIX = "/api/v1"
    
    def __getattr__(self, name):
        return None
    def __getitem__(self, name):
        return None

# Create mock config module and inject it BEFORE real one loads
_mock_config = types.ModuleType('app.core.config')
_mock_config.settings = MockSettings()

# Don't pre-mock app.core - let it load normally and patch after
# The Settings validation will be handled by mocking supabase.create_client

# Patch supabase.create_client globally to prevent real client creation
# This is needed because supabase_client.py creates client at module level
def _mock_create_client(*args, **kwargs):
    return MagicMock()

# Store original for restoration if needed
import supabase
_original_create_client = supabase.create_client
supabase.create_client = _mock_create_client

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_sp_api_client():
    """Mock SP-API client to avoid real API calls."""
    with patch('app.services.sp_api_client.sp_api_client') as mock:
        mock_client = MagicMock()
        mock_client.search_catalog_items = AsyncMock(return_value={
            "items": [{"asin": "B07TEST123", "summaries": [{"itemName": "Test Product"}]}]
        })
        mock_client.get_catalog_item = AsyncMock(return_value={
            "asin": "B07TEST123",
            "title": "Test Product"
        })
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_keepa_client():
    """Mock Keepa client."""
    with patch('app.services.keepa_client.get_keepa_client') as mock:
        mock_client = MagicMock()
        mock_client.get_product = AsyncMock(return_value={
            "title": "Test Product",
            "parent_asin": None,
            "variations": []
        })
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for database operations."""
    with patch('app.services.supabase_client.supabase') as mock:
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.upsert.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        mock.table.return_value = mock_table
        yield mock


@pytest.fixture
def mock_celery():
    """Mock Celery task execution."""
    with patch('app.tasks.file_processing.celery_app') as mock:
        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="test-task-id"))
        mock.return_value = mock_task
        yield mock


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """upc,title,buy_cost,moq
689542001425,Test Product 1,5.00,1
825325690596,Test Product 2,6.00,2
000000000000,Test Product 3,7.00,1"""


@pytest.fixture
def sample_kehe_excel_data():
    """Sample KEHE format Excel data structure."""
    return [
        {
            "ITEM": "SKU001",
            "UPC": "689542001425",
            "BRAND": "Test Brand",
            "DESCRIPTION": "Test Product",
            "PACK": 12,
            "WHOLESALE": 5.89,
            "PROMO QTY": None,
            "TOTAL PROMO %": None
        }
    ]


@pytest.fixture
def track_api_calls():
    """Track API call counts during tests."""
    class CallTracker:
        def __init__(self):
            self.batch_calls = []
            self.detailed_calls = []
            self.total_batch = 0
            self.total_detailed = 0
        
        def record_batch(self, upcs):
            self.batch_calls.append(len(upcs))
            self.total_batch += 1
        
        def record_detailed(self, upc):
            self.detailed_calls.append(upc)
            self.total_detailed += 1
        
        def reset(self):
            self.batch_calls = []
            self.detailed_calls = []
            self.total_batch = 0
            self.total_detailed = 0
    
    return CallTracker()


@pytest.fixture
def track_db_queries():
    """Track database queries made during test."""
    class QueryTracker:
        def __init__(self):
            self.queries = []
            self.insert_count = 0
            self.update_count = 0
            self.select_count = 0
        
        def record_query(self, query_type: str, query: str):
            self.queries.append(query)
            if 'INSERT' in query_type.upper():
                self.insert_count += 1
            elif 'UPDATE' in query_type.upper():
                self.update_count += 1
            elif 'SELECT' in query_type.upper():
                self.select_count += 1
        
        def reset(self):
            self.queries = []
            self.insert_count = 0
            self.update_count = 0
            self.select_count = 0
    
    return QueryTracker()
