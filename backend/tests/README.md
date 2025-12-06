# CSV Import Test Suite

Comprehensive automated tests for the CSV/Excel import flow, verifying bug fixes and all ASIN scenarios.

## Test Files

1. **`test_upc_conversion.py`** - UPC to ASIN conversion logic
   - Verifies Bug #1: Correct batch size (20, not 100)
   - Tests UPC normalization
   - Tests single/multiple/not_found scenarios

2. **`test_file_processing.py`** - CSV/Excel file processing
   - Verifies Bug #2: No redundant detailed lookup calls
   - Tests all ASIN scenarios (found/multiple/not_found)
   - Tests error handling and graceful failures

3. **`test_performance.py`** - Performance verification
   - Verifies API call counts (1,000 products = ~50 calls, not 1,000+)
   - Tests batch size consistency
   - Verifies no redundant calls at scale

4. **`test_asin_endpoints.py`** - ASIN selection/manual entry APIs
   - Tests `/products/{id}/select-asin` endpoint
   - Tests `/products/{id}/manual-asin` endpoint
   - Tests ASIN format validation

5. **`test_database.py`** - Database operations
   - Verifies bulk inserts
   - Tests correct `asin_status` values
   - Tests product_sources creation

6. **`conftest.py`** - Shared fixtures and mocks
   - Mock SP-API client
   - Mock Keepa client
   - Mock Supabase
   - Test utilities

## Running Tests

### Install Dependencies

```bash
pip install -r backend/requirements-test.txt
```

### Run All Tests

```bash
cd backend
./run_tests.sh
```

Or manually:

```bash
pytest backend/tests/ \
  --cov=backend/app \
  --cov-report=html \
  --cov-report=term \
  -v \
  --tb=short \
  --asyncio-mode=auto
```

### Run Specific Test File

```bash
pytest backend/tests/test_upc_conversion.py -v
pytest backend/tests/test_file_processing.py -v
pytest backend/tests/test_performance.py -v
```

## Test Coverage

### Bug Fixes Verified

✅ **Bug #1: Correct Batch Size**
- Tests verify UPCs are batched in groups of 20 (not 100)
- 50 UPCs = 3 batches (20+20+10)
- 1,000 UPCs = 50 batches

✅ **Bug #2: No Redundant Calls**
- Tests verify detailed lookup is NOT called when batch succeeds
- When batch finds ASIN → use it directly, no second API call
- Performance: 1,000 products = 50 API calls (not 1,000+)

### ASIN Scenarios Tested

✅ **Single ASIN Found**
- Product created with `asin_status='found'`
- ASIN set correctly
- Queued for analysis

✅ **Multiple ASINs Found**
- Product created with `asin_status='multiple_found'`
- `potential_asins` populated
- User can select via `/select-asin` endpoint

✅ **No ASIN Found**
- Product created with `asin_status='not_found'`
- UPC saved for manual entry
- User can enter ASIN via `/manual-asin` endpoint

### Error Handling

✅ **API Failures**
- Processing continues when one UPC fails
- Errors logged but don't stop import

✅ **Invalid Data**
- Missing UPCs handled gracefully
- Missing required fields logged as errors
- Processing continues for valid rows

### Performance

✅ **API Call Counts**
- 1,000 products = 50 batch calls (20 per batch)
- No redundant detailed lookups
- Batch size consistency verified

## Expected Results

After running tests, you should see:

```
✅ test_upc_batching_uses_correct_size PASSED
✅ test_no_redundant_detailed_lookup PASSED
✅ test_single_asin_found PASSED
✅ test_multiple_asins_found PASSED
✅ test_no_asin_found PASSED
✅ test_api_call_count_for_1000_products PASSED
✅ test_no_redundant_calls_at_scale PASSED

Coverage: 85%+
Critical bugs: VERIFIED FIXED ✅
```

## Notes

- All external APIs are mocked (no real API calls)
- Tests use `pytest-asyncio` for async support
- Coverage reports generated in `htmlcov/index.html`
- Tests are isolated and can run in any order

