# Network Debugging Guide

## What I Fixed

1. **SP-API Catalog Data**: Added call to `/api/v1/sp-api/product/{asin}` in DealDetail.jsx
2. **Keepa Error Handling**: Improved error messages when API key is missing

## How to Check Network Responses

### Step 1: Open Browser DevTools
1. Press `F12` or `Cmd+Option+I` (Mac)
2. Go to **Network** tab
3. Clear the log (trash icon)
4. Navigate to a Deal Detail page

### Step 2: Check SP-API Catalog Request

**Look for:**
```
GET /api/v1/sp-api/product/B0D11ZGXM3
```

**Expected Response (200 OK):**
```json
{
  "asin": "B0D11ZGXM3",
  "title": "Product Title",
  "brand": "Brand Name",
  "image_url": "https://...",
  "sales_rank": 12345,
  "buy_box_price": 29.99,
  "source": "sp-api"
}
```

**If you see:**
- **404 Not Found**: Router not registered (but I verified it is)
- **401/403**: Authentication issue
- **500**: Backend error - check Render logs
- **Empty response**: SP-API credentials might be missing

### Step 3: Check Keepa Request

**Look for:**
```
GET /api/v1/keepa/product/B0D11ZGXM3?days=90
```

**Expected Response (200 OK with data):**
```json
{
  "asin": "B0D11ZGXM3",
  "stats": {...},
  "price_history": [...],
  "rank_history": [...],
  "current": {...},
  "averages": {...}
}
```

**Expected Response (200 OK with error - API key missing):**
```json
{
  "asin": "B0D11ZGXM3",
  "error": "Keepa API key not configured",
  "stats": {},
  "price_history": [],
  "rank_history": [],
  "current": {},
  "averages": {}
}
```

## Environment Variables to Check in Render

### For `habexa-backend` service:

**Required for SP-API:**
- `SP_API_LWA_APP_ID` - Your SP-API App ID
- `SP_API_LWA_CLIENT_SECRET` - Your SP-API Client Secret  
- `SP_API_REFRESH_TOKEN` - Your SP-API Refresh Token

**Required for Keepa:**
- `KEEPA_API_KEY` - Your Keepa API key

### For `habexa-celery-worker` service (if it exists):
- `KEEPA_API_KEY` - Same as above

## Quick Test Commands

You can test the endpoints directly with curl (replace `YOUR_TOKEN` with your auth token):

```bash
# Test SP-API catalog endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://habexa-backend-w5u5.onrender.com/api/v1/sp-api/product/B0D11ZGXM3

# Test Keepa endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://habexa-backend-w5u5.onrender.com/api/v1/keepa/product/B0D11ZGXM3?days=90
```

## What to Report Back

Please share:
1. **SP-API response**: Status code and full response body
2. **Keepa response**: Status code and full response body  
3. **Environment variables**: Are `KEEPA_API_KEY` and SP-API credentials set in Render?
4. **Backend logs**: Any errors in Render logs for these endpoints?

## Common Issues

### "Unknown Product" Issue
- **Cause**: SP-API catalog endpoint not returning data
- **Check**: Is `SP_API_LWA_APP_ID`, `SP_API_LWA_CLIENT_SECRET`, and `SP_API_REFRESH_TOKEN` set?
- **Check**: Does the SP-API request return 200 OK with data?

### "History Not Found" Issue  
- **Cause**: Keepa API key not configured
- **Check**: Is `KEEPA_API_KEY` set in Render?
- **Check**: Does the Keepa request return `{"error": "Keepa API key not configured"}`?

### "No product image" Issue
- **Cause**: Same as "Unknown Product" - SP-API catalog not returning `image_url`
- **Check**: SP-API response should include `image_url` field

