# Telegram Monitoring Setup Guide

## ✅ What's Been Implemented

1. ✅ Database schema (`database/telegram_schema.sql`)
2. ✅ Telegram service (`backend/app/services/telegram_service.py`)
3. ✅ Product extractor (`backend/app/services/product_extractor.py`)
4. ✅ API endpoints (`backend/app/api/v1/telegram.py`)
5. ✅ Frontend TelegramConnect component
6. ✅ Frontend TelegramDeals component

## 📋 Setup Steps

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click **"API development tools"**
4. Fill out the form:
   - App title: `Habexa`
   - Short name: `habexa`
   - Platform: `Other`
   - Description: `Deal monitoring for Amazon sellers`
5. Click **"Create application"**
6. Copy your credentials:
   - **api_id**: A number like `12345678`
   - **api_hash**: A string like `abc123def456...`

### 2. Update Environment Variables

Add to your `.env`:
```bash
# Telegram API (from my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abc123def456789abc123def456789ab
```

### 3. Run Database Schema

Go to Supabase Dashboard → SQL Editor and run:
```sql
-- Copy and paste the contents of database/telegram_schema.sql
```

This creates:
- `telegram_sessions` table (encrypted session storage)
- `telegram_channels` table (monitored channels)
- `telegram_messages` table (raw messages)
- `telegram_deals` table (extracted deals)

### 4. Install Backend Dependencies

```bash
cd backend
pip install telethon aiohttp
```

### 5. Test the Integration

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Go to Settings → Integrations
4. Click "Connect Telegram"
5. Enter phone number → Receive code in Telegram
6. Verify code → Connected
7. Add channels to monitor
8. Start monitoring → Deals extracted automatically

## 🎯 Features Available

### When Telegram is Connected:
- ✅ **Auto-Monitoring** - 24/7 channel monitoring
- ✅ **Product Extraction** - AI-powered ASIN extraction from messages
- ✅ **Deal Creation** - Automatic deal records from extracted products
- ✅ **Real-time Processing** - Messages processed as they arrive
- ✅ **Channel Management** - Add/remove channels easily

### API Endpoints:
- `POST /api/v1/integrations/telegram/auth/start` - Start OAuth flow
- `POST /api/v1/integrations/telegram/auth/verify` - Verify code
- `DELETE /api/v1/integrations/telegram/disconnect` - Disconnect
- `GET /api/v1/integrations/telegram/status` - Connection status
- `GET /api/v1/integrations/telegram/channels/available` - List available channels
- `GET /api/v1/integrations/telegram/channels` - Get monitored channels
- `POST /api/v1/integrations/telegram/channels` - Add channel
- `DELETE /api/v1/integrations/telegram/channels/{id}` - Remove channel
- `POST /api/v1/integrations/telegram/monitoring/start` - Start monitoring
- `POST /api/v1/integrations/telegram/monitoring/stop` - Stop monitoring
- `GET /api/v1/integrations/telegram/deals/pending` - Get pending deals
- `GET /api/v1/integrations/telegram/messages` - Get recent messages

## ⚠️ Important Notes

1. **Session Encryption**: All Telegram sessions are encrypted using your `SECRET_KEY` before storage.

2. **Rate Limits**: Telegram has rate limits. The service handles FloodWait errors automatically.

3. **2FA Support**: If your Telegram account has 2FA enabled, you'll be prompted for your password.

4. **Channel Access**: You can only monitor channels/groups you're a member of.

5. **Product Extraction**: Uses OpenAI GPT-4o-mini to extract ASINs, prices, and MOQ from messages. Falls back to regex if OpenAI is unavailable.

## 🚀 Usage Flow

1. **Connect Telegram**: Settings → Integrations → Connect Telegram
2. **Add Channels**: Click "Add Channel" → Select channels to monitor
3. **Start Monitoring**: Click "Start Monitoring"
4. **View Deals**: Deals appear in TelegramDeals component
5. **Analyze Deals**: Click "Analyze" on individual deals or "Analyze All"

## 📊 Monitoring Stats

Each channel tracks:
- Messages received
- Deals extracted
- Last message timestamp

The integration is complete and ready to use once you add your Telegram API credentials! 🎉

