# API Data Storage Explanation

## Why Product ID vs ASIN?

### Current Approach: Product ID
- **Product ID** is a UUID in the `products` table that uniquely identifies a product record
- **ASIN** is stored as a property of the product
- Multiple `product_sources` (deals) can reference the same product
- The endpoint uses `product_id` because:
  1. It's the primary key in the database
  2. It ensures we're updating the correct product record
  3. It's more efficient for database queries

### Alternative: ASIN-based Endpoints
We could also support ASIN-based endpoints since:
- ASIN is unique per user (enforced by database constraint)
- It's more intuitive for users
- It's what users see in the UI

**Recommendation**: Support BOTH:
- `POST /products/{product_id}/refresh-api-data` (current)
- `POST /products/by-asin/{asin}/refresh-api-data` (new, convenience endpoint)

## What Data is Tied to ASIN?

### In the `products` Table:

#### Raw API Responses (JSONB):
- `sp_api_raw_response` - Complete SP-API JSON response
- `keepa_raw_response` - Complete Keepa JSON response
- `sp_api_last_fetched` - Timestamp when SP-API data was fetched
- `keepa_last_fetched` - Timestamp when Keepa data was fetched

#### Structured Data from SP-API:
- **Product Info**: `manufacturer`, `model_number`, `part_number`, `ean`, `isbn`
- **Dimensions**: `item_length`, `item_width`, `item_height`, `item_weight`, `package_length`, `package_width`, `package_height`, `package_weight`
- **Pricing**: `list_price`, `lowest_price`, `buy_box_price`
- **Categories**: `category_rank`, `category_path`, `browse_nodes`
- **Features**: `features`, `description`, `bullet_points`, `images`

#### Structured Data from Keepa:
- **Sales Rank**: `current_sales_rank`, `sales_rank_30_day_avg`, `sales_rank_90_day_avg`, `sales_rank_180_day_avg`
- **Pricing History**: `amazon_price_current`, `amazon_price_30_day_avg`, `amazon_price_90_day_avg`, `new_price_current`, `new_price_30_day_avg`, `new_price_90_day_avg`
- **Availability**: `in_stock`, `out_of_stock_percentage`
- **Reviews**: `rating_average`, `review_count`, `review_velocity`
- **Fees**: `fba_fees`, `referral_fee_percentage`
- **Restrictions**: `is_hazmat`, `is_meltable`
- **History**: `first_available_date`, `age_in_days`

## Why Tabs Aren't Filling Out

### Issues Found:

1. **API Data Not Being Fetched on Product Creation**
   - The `fetch_and_store_all_api_data` call in `file_processing.py` might be failing silently
   - Need better error handling and logging

2. **Data Not Being Stored Correctly**
   - The `extract_keepa_structured_data` function signature might not match how it's being called
   - Need to verify the raw response is being stored

3. **Frontend Not Displaying Data**
   - The `raw_api_data` might not be included in the deal response
   - Need to ensure the endpoint returns the raw responses

## Fixes Needed:

1. ✅ Fix `run_async` call in `file_processing.py` (already done)
2. ✅ Add better error handling and logging
3. ✅ Verify `extract_keepa_structured_data` function signature
4. ✅ Ensure raw responses are stored in database
5. ✅ Add ASIN-based endpoint for convenience
6. ✅ Add comprehensive logging to track API data flow

