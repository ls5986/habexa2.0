# Keepa Integration Setup Guide

## ✅ What's Been Implemented

1. ✅ Database schema (`database/keepa_schema.sql`)
2. ✅ Keepa client service (`backend/app/services/keepa_client.py`)
3. ✅ API endpoints (`backend/app/api/v1/keepa.py`)
4. ✅ Analysis integration (Keepa data included in analysis)
5. ✅ Frontend `useKeepa` hook
6. ✅ PriceHistoryChart component
7. ✅ SalesEstimate component

## 📋 Setup Steps

### 1. Get Keepa API Key

1. Go to https://keepa.com
2. Sign up for an account
3. Go to https://keepa.com/#!api
4. Subscribe to a plan:
   - **Individual**: 250,000 tokens/month ($19/mo)
   - **Business**: 1,000,000 tokens/month ($49/mo)
5. Click "Access Key"
6. Copy your API key

### 2. Update Environment Variables

Add to your `.env`:
```bash
# Keepa API
KEEPA_API_KEY=your_keepa_api_key_here
```

### 3. Run Database Schema

Go to Supabase Dashboard → SQL Editor and run:
```sql
-- Copy and paste the contents of database/keepa_schema.sql
```

This creates:
- `keepa_cache` table (product data + history, 24-hour cache)
- `keepa_usage` table (token tracking)

### 4. Test the Integration

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Analyze a product → Keepa data automatically included
4. View deal detail → See price history chart
5. Check sales estimate → See velocity metrics

## 🎯 Features Available

### When Keepa is Configured:
- ✅ **Price History Charts** - 30/90/180/365 day price trends
- ✅ **Sales Rank History** - BSR trends over time
- ✅ **Sales Estimates** - Monthly sales from rank drops
- ✅ **Price Averages** - 30/90 day averages
- ✅ **Competition Data** - Offer counts, seller info
- ✅ **Out of Stock Tracking** - OOS percentage
- ✅ **Automatic Caching** - 24-hour cache reduces API calls

### API Endpoints:
- `GET /api/v1/keepa/product/{asin}?days=90` - Full product data with history
- `GET /api/v1/keepa/history/{asin}?days=90` - Just chart data
- `POST /api/v1/keepa/batch` - Batch fetch (up to 100 ASINs)
- `GET /api/v1/keepa/tokens` - Check token balance
- `GET /api/v1/keepa/sales-estimate/{asin}` - Sales velocity estimate

## 📊 Data Structure

### Price History:
- **Amazon Price** - When Amazon is selling
- **New FBA** - Lowest FBA price
- **Buy Box** - Current Buy Box price
- **New (Marketplace)** - Lowest new price overall

### Sales Estimates:
- **Rank Drops** - Each drop ≈ 1 sale
- **30/90/180 day drops** - Sales velocity indicators
- **Monthly estimate** = drops_30

### Averages:
- **30-day averages** - Short-term trends
- **90-day averages** - Medium-term trends
- Available for: price, rank, offers

## ⚠️ Important Notes

1. **Token Costs**: 
   - Product request: ~1-3 tokens
   - With history: ~2-5 tokens
   - Batch of 100: ~100-300 tokens

2. **Caching**: Data cached for 24 hours to minimize API calls

3. **Price Format**: Keepa stores prices in cents (divide by 100)

4. **Time Format**: Keepa time = minutes since 2011-01-01 UTC

5. **Rate Limits**: Keepa has rate limits. The client handles errors gracefully.

## 🚀 Usage

### In Analysis:
Keepa data is automatically included when analyzing products:
- 90-day average price
- Sales rank drops (monthly sales estimate)
- Price vs average comparison

### In Deal Detail:
- Price history chart (toggle price/rank, 30D/90D/180D/1Y)
- Sales estimate widget
- Historical stats

### Frontend Hook:
```javascript
import { useKeepa } from '../hooks/useKeepa';

const { getProduct, getHistory, getSalesEstimate, loading } = useKeepa();

// Get full product data
const data = await getProduct('B08N5WRWNW', 90);

// Get just history for charts
const history = await getHistory('B08N5WRWNW', 90);

// Get sales estimate
const estimate = await getSalesEstimate('B08N5WRWNW');
```

## 📈 Chart Features

- **Price Chart**: Shows Buy Box, FBA, Amazon prices over time
- **Rank Chart**: Shows sales rank trends (lower is better)
- **Buy Cost Reference Line**: Shows your buy cost on price chart
- **Time Periods**: 30D, 90D, 180D, 1Y
- **Interactive Tooltips**: Hover for exact values
- **Responsive**: Works on all screen sizes

The integration is complete and ready to use once you add your Keepa API key! 🎉

