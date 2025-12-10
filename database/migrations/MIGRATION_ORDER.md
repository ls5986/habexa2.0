# Migration Order for Pack and Sales Fields

Run these migrations **in this exact order** in Supabase SQL Editor:

## Step 1: Add Pack/Wholesale Columns
```sql
-- Run: database/migrations/ADD_PACK_AND_WHOLESALE_COLUMNS.sql
```
This adds:
- `pack_size` (INTEGER)
- `wholesale_cost` (DECIMAL)

## Step 2: Add Sales/Promo Columns
```sql
-- Run: database/migrations/ADD_SALES_COLUMNS_TO_PRODUCT_SOURCES.sql
```
This adds:
- `percent_off` (DECIMAL)
- `promo_qty` (INTEGER)

## Step 3: Update View and RPC Function
```sql
-- Run: database/migrations/ADD_PACK_AND_SALES_FIELDS_TO_VIEW.sql
```
This updates:
- `product_deals` view to include all new fields
- `filter_product_deals` RPC function to include all new fields

---

## Quick Copy-Paste (All in Order)

1. **First**, copy and paste the contents of `ADD_PACK_AND_WHOLESALE_COLUMNS.sql`
2. **Then**, copy and paste the contents of `ADD_SALES_COLUMNS_TO_PRODUCT_SOURCES.sql`
3. **Finally**, copy and paste the contents of `ADD_PACK_AND_SALES_FIELDS_TO_VIEW.sql`

---

## Why This Order?

The view references columns that must exist first. If you try to run the view migration before the column migrations, you'll get:
```
ERROR: column ps.pack_size does not exist
ERROR: column ps.percent_off does not exist
```

By running them in order, each migration builds on the previous one.

