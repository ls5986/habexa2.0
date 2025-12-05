# Excel Upload - KEHE Supplier Format Support

## Overview
Added hardcoded column mapping support for KEHE supplier Excel format with UPC → ASIN conversion. The system can now handle 43,000+ record Excel files.

## Format Detected
The system automatically detects the KEHE supplier format by checking for these columns:
- `UPC` (required)
- `WHOLESALE` (buy cost)
- `PACK` (MOQ/minimum order quantity)
- `DESCRIPTION` (product description)
- `BRAND` (brand name)
- `RETAIL` (suggested retail price - optional)

## Column Mapping (Hardcoded)

| KEHE Column | Maps To | Usage |
|-------------|---------|-------|
| `UPC` | Product Identifier | Converted to ASIN via SP-API |
| `WHOLESALE` | `buy_cost` | Wholesale price per unit |
| `PACK` | `moq` | Minimum order quantity |
| `DESCRIPTION` | `notes` | Product description stored as notes |
| `BRAND` | `brand` | Brand name stored on product |
| `RETAIL` | Reference only | Not stored, used for reference |

## File Processing Flow

1. **Upload**: Frontend accepts `.xlsx` files via `FileUploadModal.jsx`
2. **Detection**: Backend detects KEHE format by checking column headers
3. **Parsing**: Uses hardcoded column mapping to extract data
4. **UPC → ASIN Conversion**: Each UPC is converted to ASIN using SP-API
5. **Batch Processing**: Products created in batches of 100
6. **Auto-Analysis**: After upload, products are queued for profitability analysis

## Performance Considerations

### For 43,000 Records:
- **Upload Time**: ~2-5 minutes (depends on file size)
- **Parsing Time**: ~1-2 minutes (Excel parsing is fast)
- **UPC → ASIN Conversion**: ⚠️ **This is the bottleneck**
  - Each UPC conversion requires an SP-API call
  - SP-API has rate limits (~0.5 requests/second per endpoint)
  - **Estimated time: 24-48 hours for 43k UPCs** (if done sequentially)
  
### Recommendations:
1. **Test First**: Upload a small sample (100-500 rows) to verify everything works
2. **Batch Processing**: The system processes in batches of 100, so it's optimized
3. **Background Processing**: All UPC conversions happen in the background via Celery
4. **Monitor Progress**: Check job status in the UI to see progress

## Files Modified

### Backend
- `backend/app/tasks/file_processing.py`
  - Added `is_kehe_format()` - detects KEHE format
  - Added `parse_kehe_row()` - hardcoded column mapping
  - Updated `parse_excel()` - preserves original column names
  - Added UPC → ASIN conversion support
  - Added batch processing for UPC conversions

### Frontend
- `frontend/src/components/features/products/FileUploadModal.jsx` - Already supports `.xlsx` files

## How to Test

### 1. Test with Small Sample First
```python
# Create a test file with 10 rows
import pandas as pd
df = pd.read_excel('Unpublished_DC27_Bk 12_17[13].xlsx', nrows=10)
df.to_excel('test_kehe_sample.xlsx', index=False)
```

### 2. Upload via UI
1. Go to Products page
2. Click "Upload Price List"
3. Select supplier (or create new one)
4. Upload `test_kehe_sample.xlsx`
5. Monitor job progress

### 3. Verify Results
- Check Products page for new products
- Verify UPCs were converted to ASINs
- Verify buy cost, MOQ, and notes are correct
- Products should auto-queue for analysis

## Expected Behavior

### Successful Upload:
- Job status shows "processing" → "completed"
- Progress bar shows rows processed
- Results show:
  - Products created: X
  - Deals processed: X
  - Errors: (if any)

### UPC Conversion:
- Each UPC is converted to ASIN via SP-API
- Failed conversions are logged as errors
- Successful conversions create products with ASIN

### Error Handling:
- Missing UPC → Row skipped with error message
- Invalid UPC → Row skipped with error message
- Failed ASIN conversion → Row skipped with error message
- All errors are logged and returned in job results

## Testing the Full 43k File

⚠️ **Important Notes:**
1. **Time Estimate**: With 43k UPCs, expect 24-48 hours for all conversions
2. **Rate Limits**: SP-API has rate limits, so conversions happen slowly
3. **Background Processing**: Job runs in background - you can close browser
4. **Monitor Progress**: Check job status periodically via UI or backend logs

### Recommended Approach:
1. **Start with 1,000 rows** to test
2. **Monitor for 1-2 hours** to verify conversion rate
3. **If working well**, upload full file
4. **Let it run overnight** - it's a long-running background job

## Troubleshooting

### "Could not convert UPC to ASIN"
- UPC might not exist on Amazon
- SP-API might be rate-limited (wait and retry)
- UPC format might be invalid

### "Missing UPC in KEHE format"
- Row doesn't have UPC column
- UPC column is empty
- Check Excel file structure

### Processing is Slow
- **Normal** - UPC conversions take time due to SP-API rate limits
- Check Celery worker logs for progress
- Monitor job status via UI

## Next Steps

1. **Test with small sample** (10-100 rows)
2. **Verify column mapping** is correct
3. **Check UPC → ASIN conversion** works
4. **Monitor processing time** for sample
5. **Upload full file** if sample works well

## Column Detection Logic

The system detects KEHE format if at least 2 of these columns are present:
- `UPC`
- `WHOLESALE`
- `PACK`

This ensures compatibility even if the file structure varies slightly.

