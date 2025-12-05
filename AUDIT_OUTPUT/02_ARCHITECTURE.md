# Habexa - System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  React + Vite + Material-UI                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │  Pages   │  │Components│  │ Contexts │                │
│  └──────────┘  └──────────┘  └──────────┘                │
│       │              │              │                       │
│       └──────────────┼──────────────┘                       │
│                      │                                      │
│              ┌───────▼───────┐                              │
│              │  API Client   │                              │
│              │   (Axios)     │                              │
│              └───────┬───────┘                              │
└──────────────────────┼──────────────────────────────────────┘
                       │ HTTPS
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      BACKEND                                │
│  FastAPI + Python                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │              FastAPI Application                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │   API    │  │ Services │  │  Tasks   │        │   │
│  │  │ Routers  │  │          │  │ (Celery) │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘        │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼────┐ ┌───────▼──────┐
│   Supabase   │ │  Redis  │ │   External   │
│  (PostgreSQL)│ │ (Queue) │ │     APIs     │
└──────────────┘ └─────────┘ └──────────────┘
                       │
                ┌──────▼──────┐
                │   Celery    │
                │   Workers   │
                └─────────────┘
```

## Request Flow

### 1. User Action → Frontend
```
User clicks "Analyze Product"
  ↓
React component calls hook (useAnalysis)
  ↓
Hook calls api.post('/analyze/single', { asin, buy_cost })
  ↓
Axios interceptor adds Bearer token
  ↓
Request sent to backend
```

### 2. Backend Processing
```
FastAPI receives request
  ↓
Auth middleware validates JWT token
  ↓
Route handler processes request
  ↓
Service layer calls external APIs (SP-API, Keepa)
  ↓
Data saved to Supabase
  ↓
Response returned to frontend
```

### 3. Background Processing
```
Long-running task (file upload, batch analysis)
  ↓
Endpoint creates job record
  ↓
Celery task queued in Redis
  ↓
Celery worker picks up task
  ↓
Task updates job progress
  ↓
Frontend polls job status
```

## Component Layers

### Frontend Layers

1. **Pages** (`src/pages/`)
   - Top-level route components
   - Handle data fetching
   - Compose feature components

2. **Feature Components** (`src/components/features/`)
   - Reusable feature-specific components
   - Business logic components
   - Form components

3. **Layout Components** (`src/components/layout/`)
   - AppLayout, Sidebar, TopBar
   - Navigation structure

4. **Common Components** (`src/components/common/`)
   - Shared UI components
   - Reusable widgets

5. **Contexts** (`src/context/`)
   - Global state management
   - AuthContext, StripeContext, ThemeContext, etc.

6. **Hooks** (`src/hooks/`)
   - Custom React hooks
   - Data fetching logic
   - Feature-specific hooks

7. **Services** (`src/services/`)
   - API client configuration
   - Supabase client

### Backend Layers

1. **API Layer** (`app/api/v1/`)
   - FastAPI routers
   - Request/response handling
   - Authentication checks

2. **Service Layer** (`app/services/`)
   - Business logic
   - External API clients
   - Data processing

3. **Task Layer** (`app/tasks/`)
   - Celery background tasks
   - Long-running operations
   - Job management

4. **Core Layer** (`app/core/`)
   - Configuration
   - Security utilities
   - Celery app setup

## Data Flow

### Product Analysis Flow

```
1. User uploads CSV/Excel
   ↓
2. File parsed, products created
   ↓
3. UPC → ASIN conversion (SP-API)
   ↓
4. SP-API pricing + fees
   ↓
5. Keepa historical data
   ↓
6. Profit calculation
   ↓
7. Results saved to database
   ↓
8. Frontend displays results
```

### Authentication Flow

```
1. User logs in (Supabase Auth)
   ↓
2. Supabase returns JWT token
   ↓
3. Token stored in localStorage
   ↓
4. Axios interceptor adds token to requests
   ↓
5. Backend validates token with Supabase
   ↓
6. Request processed
```

## External Integrations

### Amazon SP-API
- **Purpose:** Product data, pricing, fees, eligibility
- **Authentication:** LWA (Login with Amazon) - App credentials
- **Rate Limits:** 2 req/sec (catalog), 0.5 req/sec (pricing)
- **Client:** `app/services/sp_api_client.py`

### Keepa API
- **Purpose:** Price history, sales rank, competition data
- **Authentication:** API key
- **Rate Limits:** ~1 req/sec, token-based
- **Client:** `app/services/keepa_client.py`
- **Caching:** 24-hour cache in `keepa_cache` table

### Stripe
- **Purpose:** Subscription billing
- **Integration:** Stripe Checkout, Customer Portal
- **Service:** `app/services/stripe_service.py`

### Telegram
- **Purpose:** Monitor supplier channels for deals
- **Library:** Telethon
- **Service:** `app/services/telegram_service.py`

### Supabase
- **Purpose:** Database + Auth
- **Client:** `app/services/supabase_client.py`
- **Tables:** See 03_DATABASE.md

## Deployment Architecture

### Render.com Services

1. **habexa-backend** (Web Service)
   - FastAPI application
   - Handles HTTP requests
   - Creates Celery tasks

2. **habexa-celery-worker** (Background Worker)
   - Processes Celery tasks
   - Reads from Redis queue
   - Updates job progress

3. **habexa-frontend** (Static Site)
   - React build output
   - Served via CDN
   - API calls to backend

### Environment Variables

**Backend Required:**
- `SUPABASE_URL`, `SUPABASE_KEY`
- `SP_API_REFRESH_TOKEN`, `SP_API_LWA_APP_ID`, `SP_API_LWA_CLIENT_SECRET`
- `KEEPA_API_KEY`
- `STRIPE_SECRET_KEY`
- `REDIS_URL`
- `CELERY_BROKER_URL`

**Frontend Required:**
- `VITE_API_URL`
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

## Security

1. **Authentication:** JWT tokens via Supabase Auth
2. **Authorization:** User-scoped data (user_id checks)
3. **API Keys:** Stored in environment variables
4. **CORS:** Configured for specific origins
5. **Rate Limiting:** Token bucket for SP-API calls

## Performance Considerations

1. **Caching:**
   - Keepa data cached 24 hours
   - UPC→ASIN cache (permanent)
   - Redis for rate limiting

2. **Background Processing:**
   - Large file uploads → Celery tasks
   - Batch analysis → Celery tasks
   - Prevents frontend timeouts

3. **Database:**
   - Indexes on frequently queried columns
   - JSONB for flexible data storage
   - Materialized views (if needed)

4. **API Optimization:**
   - Batch endpoints (up to 20 ASINs)
   - Parallel processing where possible
   - Rate limiting to respect API limits

---

**Last Updated:** 2025-12-05

