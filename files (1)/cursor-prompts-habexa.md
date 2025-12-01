# Cursor AI Development Prompts for Habexa
## Complete Frontend & Backend Implementation Guide

---

# 🎨 PHASE 1: FRONTEND DEVELOPMENT

Copy this entire prompt into Cursor when starting the frontend:

---

## CURSOR PROMPT: FRONTEND

```
You are building the frontend for Habexa, an Amazon Sourcing Intelligence Platform that helps e-commerce sellers analyze product profitability from Telegram/email messages.

## PROJECT CONTEXT

Habexa is a React.js application with the following existing stack:
- Framework: React.js (Vite or CRA)
- Component Library: Material-UI (MUI) v5
- State Management: React Context API
- Routing: React Router v6
- Charts: Recharts
- HTTP Client: Axios

The backend is FastAPI (Python) and we'll build that later. For now, mock all API calls.

## DESIGN SYSTEM

Follow this design system exactly:

### Colors
```javascript
const theme = {
  palette: {
    primary: {
      main: '#2563EB',      // Blue 600
      light: '#DBEAFE',     // Blue 100
      dark: '#1D4ED8',      // Blue 700
    },
    secondary: {
      main: '#7C3AED',      // Violet 600
    },
    success: {
      main: '#10B981',      // Emerald 500 - Profitable
      light: '#D1FAE5',
    },
    warning: {
      main: '#F59E0B',      // Amber 500 - Review needed
      light: '#FEF3C7',
    },
    error: {
      main: '#EF4444',      // Red 500 - Unprofitable
      light: '#FEE2E2',
    },
    background: {
      default: '#F9FAFB',   // Gray 50
      paper: '#FFFFFF',
    },
    text: {
      primary: '#111827',   // Gray 900
      secondary: '#6B7280', // Gray 500
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: {
    borderRadius: 8,
  },
}
```

### Component Styling Rules
1. Cards: White background, 1px border (#E5E7EB), 8px border-radius, subtle shadow on hover
2. Sidebar: Dark (#0F172A), 240px expanded, 64px collapsed
3. Buttons: 8px border-radius, no all-caps text
4. Spacing: Use 8px grid (8, 16, 24, 32, 48)
5. Status indicators: Green circle = profitable, Yellow = review, Red = unprofitable

## SCREENS TO BUILD

Build these screens in order:

### 1. AppLayout Component
- Left sidebar navigation (collapsible)
- Top bar with Quick Analyze button, notifications bell, user avatar
- Main content area with proper padding

Navigation items:
- Dashboard (Home icon)
- Deal Feed (Inbox icon) - with badge showing unread count
- Suppliers (Users icon)
- Products (Package icon)
- Analyze (Search icon)
- Settings (Settings icon)

### 2. Dashboard Screen (`/dashboard`)
Features:
- Greeting with user's name and time of day
- 4 stat cards in a row: New Deals, Profitable, Pending Review, Potential Profit
- Each stat card shows: value, subtitle, trend percentage with up/down arrow
- "Hot Deals" section showing top 3 profitable products
- "Channel Activity" showing deals per Telegram channel with progress bars
- "Recent Activity" timeline

### 3. Deal Feed Screen (`/deals`)
Features:
- Live indicator (pulsing green dot)
- Filter bar: Channel dropdown, ROI filter, Category filter, Gating filter
- Tabs: All, Profitable, Pending, Saved
- Deal cards showing:
  - Status indicator (colored dot)
  - Product thumbnail placeholder
  - Title and ASIN (monospace font for ASIN)
  - Cost → Sell → Profit display
  - Metric badges: ROI%, MOQ, Rank
  - Gating badge (Ungated/Gated/Amazon Selling)
  - Supplier name and timestamp
  - Quick actions: Message, Save, Full Analysis
- Clicking a card opens slide-over panel with full details

### 4. Product Detail Panel (Slide-over)
Features:
- Product image, title, ASIN, category
- Status badges (Profitable/Unprofitable, Gating status)
- 4 metric cards: Profit, ROI, Rank, Est. Monthly Sales
- Profit Breakdown section:
  - Your Cost
  - + Shipping Est.
  - + Prep Fee
  - = Total Cost
  - Sell Price
  - - Amazon Referral (15%)
  - - FBA Fee
  - = Net Profit (highlighted)
- Supplier Info card with contact buttons
- Action buttons: Message Supplier, Save to Watchlist

### 5. Suppliers Screen (`/suppliers`)
Features:
- Add Supplier button
- Search and filter bar
- Supplier cards showing:
  - Avatar with initials
  - Name and rating (stars)
  - Contact method icons (Telegram, WhatsApp, Email)
  - Stats: Deals analyzed, Purchased, Avg ROI, Last contact
  - Tags
  - Actions: Message, View Orders, More menu

### 6. Analyze Screen (`/analyze`)
Features:
- Large input field for ASIN with "Analyze" button
- Bulk mode toggle to paste multiple ASINs
- Recent analyses list
- When analyzing: show loading state with progress steps
- Results display similar to Deal Feed cards

### 7. Settings Screen (`/settings`)
Tabs:
- Profile (name, email, password)
- Integrations (Telegram, Amazon, WhatsApp status cards)
- Alerts (ROI threshold slider, profit minimum, max rank, category preferences)
- Billing (current plan, upgrade options)

## MOCK DATA

Use this mock data structure:

```javascript
const mockDeals = [
  {
    id: 1,
    asin: 'B08XYZ1234',
    title: 'Sony Wireless Earbuds - Model XYZ',
    category: 'Electronics',
    buyCost: 45.00,
    sellPrice: 89.99,
    profit: 18.50,
    roi: 41,
    rank: 8432,
    moq: 24,
    supplierId: 1,
    supplierName: 'Wholesale Kings',
    timestamp: '2 min ago',
    status: 'profitable', // 'profitable' | 'review' | 'unprofitable'
    gating: 'ungated', // 'ungated' | 'gated' | 'amazon'
    fbaFee: 7.35,
    referralFee: 13.50,
    estimatedMonthlySales: 340,
    numFbaSellers: 5,
    numFbmSellers: 12,
    amazonIsSeller: false,
  },
  // Add more mock deals...
];

const mockSuppliers = [
  {
    id: 1,
    name: 'Wholesale Kings',
    initials: 'WK',
    rating: 4.2,
    dealsAnalyzed: 47,
    dealsPurchased: 12,
    avgRoi: 32,
    lastContact: '2 days ago',
    avgLeadTime: '5-7 days',
    telegram: '@wholesalekings',
    whatsapp: '+1234567890',
    email: 'contact@wholesalekings.com',
    tags: ['Electronics', 'Wholesale', 'Reliable'],
  },
  // Add more mock suppliers...
];
```

## CODE QUALITY REQUIREMENTS

1. Use functional components with hooks
2. Create reusable components in `/components/common/`
3. Use MUI's `sx` prop for styling, not separate CSS files
4. Implement proper loading states and skeletons
5. Add proper TypeScript types if using TypeScript
6. Use React Router for navigation
7. Implement responsive design (mobile-first)
8. Use React Context for global state (user, theme, notifications)

## FILE STRUCTURE

```
src/
├── components/
│   ├── common/
│   │   ├── StatCard.jsx
│   │   ├── DealCard.jsx
│   │   ├── SupplierCard.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── GatingBadge.jsx
│   │   └── LoadingSkeleton.jsx
│   ├── layout/
│   │   ├── AppLayout.jsx
│   │   ├── Sidebar.jsx
│   │   ├── TopBar.jsx
│   │   └── NotificationDropdown.jsx
│   └── features/
│       ├── deals/
│       │   ├── DealFeed.jsx
│       │   ├── DealFilters.jsx
│       │   └── DealDetailPanel.jsx
│       ├── suppliers/
│       │   └── SupplierList.jsx
│       └── analyze/
│           └── AnalyzeForm.jsx
├── pages/
│   ├── Dashboard.jsx
│   ├── Deals.jsx
│   ├── Suppliers.jsx
│   ├── Analyze.jsx
│   └── Settings.jsx
├── context/
│   ├── AuthContext.jsx
│   └── NotificationContext.jsx
├── hooks/
│   ├── useDeals.js
│   └── useSuppliers.js
├── services/
│   └── api.js (mock for now)
├── utils/
│   ├── formatters.js
│   └── calculations.js
├── theme/
│   └── index.js
└── App.jsx
```

## INTERACTIONS TO IMPLEMENT

1. Sidebar collapse/expand with smooth animation
2. Deal card hover effect (lift + shadow)
3. Slide-over panel for deal details (slide from right)
4. Toast notifications for actions (save, dismiss, etc.)
5. Loading skeletons while data loads
6. Real-time badge updates on navigation items
7. Filter dropdowns with checkboxes
8. Bulk selection mode in Deal Feed

## START BUILDING

Begin by:
1. Setting up the MUI theme
2. Creating the AppLayout with Sidebar and TopBar
3. Building the Dashboard with stat cards
4. Then move to Deal Feed as the core experience

Ask me clarifying questions if needed. Focus on making the UI beautiful and polished - we want this to feel like Helium 10 quality but with more personality.
```

---

# 🔧 PHASE 2: BACKEND DEVELOPMENT

After the frontend is complete, use this prompt for the backend:

---

## CURSOR PROMPT: BACKEND

```
You are building the FastAPI backend for Habexa, an Amazon Sourcing Intelligence Platform. The frontend is already built in React.

## PROJECT CONTEXT

Stack:
- Framework: FastAPI (Python 3.11+)
- Database: PostgreSQL with SQLAlchemy ORM
- Authentication: JWT tokens
- Migrations: Alembic
- Task Queue: Celery with Redis (for background jobs)
- Cache: Redis
- API Docs: Swagger/OpenAPI (built-in)

External Integrations:
- Telegram Bot API (for message extraction)
- Amazon SP-API (for product data)
- Keepa API (for historical data)
- OpenAI API (for message parsing)
- Stripe (for billing)

## DATABASE SCHEMA

Implement these tables:

```sql
-- See the full schema in the SP-API Integration Guide
-- Key tables: users, amazon_credentials, suppliers, messages, product_analyses, watchlist, orders, profit_settings, notifications
```

## PROJECT STRUCTURE

```
app/
├── api/
│   ├── v1/
│   │   ├── auth.py
│   │   ├── deals.py
│   │   ├── suppliers.py
│   │   ├── analysis.py
│   │   ├── settings.py
│   │   └── webhooks.py
│   └── deps.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── cache.py
│   └── rate_limiter.py
├── models/
│   ├── user.py
│   ├── supplier.py
│   ├── message.py
│   ├── analysis.py
│   └── notification.py
├── schemas/
│   ├── user.py
│   ├── deal.py
│   └── analysis.py
├── services/
│   ├── telegram_service.py
│   ├── amazon_auth.py
│   ├── sp_api_client.py
│   ├── asin_analyzer.py
│   ├── keepa_client.py
│   ├── openai_extractor.py
│   └── profit_calculator.py
├── tasks/
│   ├── celery_app.py
│   ├── analysis_tasks.py
│   └── notification_tasks.py
├── db/
│   ├── base.py
│   └── session.py
└── main.py
```

## API ENDPOINTS TO BUILD

### Authentication
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/auth/me

### Deals/Analysis
- GET /api/v1/deals - List deals with filters
- GET /api/v1/deals/{id} - Get single deal
- POST /api/v1/deals/{id}/save - Save to watchlist
- POST /api/v1/deals/{id}/dismiss - Dismiss deal
- POST /api/v1/analyze/single - Analyze single ASIN
- POST /api/v1/analyze/batch - Analyze multiple ASINs

### Suppliers
- GET /api/v1/suppliers - List suppliers
- POST /api/v1/suppliers - Create supplier
- GET /api/v1/suppliers/{id} - Get supplier
- PUT /api/v1/suppliers/{id} - Update supplier
- DELETE /api/v1/suppliers/{id} - Delete supplier
- POST /api/v1/suppliers/{id}/message - Send message

### Settings
- GET /api/v1/settings/profile
- PUT /api/v1/settings/profile
- GET /api/v1/settings/profit-rules
- PUT /api/v1/settings/profit-rules
- GET /api/v1/settings/alerts
- PUT /api/v1/settings/alerts

### Integrations
- POST /api/v1/integrations/telegram/connect
- DELETE /api/v1/integrations/telegram/disconnect
- GET /api/v1/integrations/telegram/channels
- POST /api/v1/integrations/amazon/connect
- DELETE /api/v1/integrations/amazon/disconnect
- POST /api/v1/integrations/amazon/sync

### Webhooks
- POST /api/v1/webhooks/telegram - Receive Telegram updates
- POST /api/v1/webhooks/stripe - Handle Stripe events

## KEY SERVICES TO IMPLEMENT

### 1. OpenAI Message Extractor
```python
# Extract ASINs, prices, MOQ from raw Telegram/email messages
# Use GPT-4 with structured output

prompt = """
Extract product information from this supplier message.
Return JSON with: asin, price, moq, notes

Message: {message}

If multiple products, return an array.
If field is not found, use null.
"""
```

### 2. SP-API Client
- Handle LWA token refresh automatically
- Implement rate limiting (see SP-API guide)
- Cache responses appropriately
- Handle errors with retry logic

### 3. ASIN Analyzer
- Fetch data from multiple APIs in parallel
- Calculate profitability
- Determine deal score (A-F)
- Check gating status

### 4. Profit Calculator
```python
def calculate_profit(
    buy_cost: float,
    sell_price: float,
    fba_fee: float,
    referral_fee: float,
    prep_cost: float = 0.50,
    inbound_shipping: float = 0.50
) -> dict:
    total_cost = buy_cost + prep_cost + inbound_shipping
    total_fees = fba_fee + referral_fee
    net_payout = sell_price - total_fees
    net_profit = net_payout - total_cost
    roi = (net_profit / total_cost) * 100 if total_cost > 0 else 0
    margin = (net_profit / sell_price) * 100 if sell_price > 0 else 0
    
    return {
        "total_cost": total_cost,
        "total_fees": total_fees,
        "net_payout": net_payout,
        "net_profit": net_profit,
        "roi": roi,
        "margin": margin
    }
```

### 5. Notification Service
- Send push notifications for profitable deals
- Queue email digests
- Respect user's quiet hours
- Track notification status

## CELERY TASKS

```python
# Background tasks for async processing

@celery_app.task
def analyze_message_task(message_id: int):
    """Process a new Telegram message, extract ASINs, analyze each."""
    pass

@celery_app.task
def batch_analysis_task(batch_id: str, items: list, user_id: int):
    """Process batch ASIN analysis."""
    pass

@celery_app.task
def send_alert_task(user_id: int, analysis_id: int):
    """Send notification for profitable deal."""
    pass

@celery_app.task
def refresh_token_task(user_id: int):
    """Refresh Amazon LWA token before expiry."""
    pass
```

## WEBSOCKET FOR REAL-TIME

```python
# Real-time deal feed updates
from fastapi import WebSocket

@app.websocket("/ws/deals/{user_id}")
async def deal_websocket(websocket: WebSocket, user_id: int):
    await websocket.accept()
    # Subscribe to user's deal updates
    # Push new deals as they're analyzed
```

## ENVIRONMENT VARIABLES

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/habexa
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key

# Amazon SP-API
LWA_CLIENT_ID=amzn1.application-oa2-client.xxx
LWA_CLIENT_SECRET=xxx
SP_API_REFRESH_TOKEN=Atzr|xxx
MARKETPLACE_ID=ATVPDKIKX0DER

# External APIs
KEEPA_API_KEY=xxx
OPENAI_API_KEY=sk-xxx

# Telegram
TELEGRAM_BOT_TOKEN=xxx

# Stripe
STRIPE_SECRET_KEY=sk_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

## BUILD ORDER

1. Set up FastAPI app with CORS, exception handlers
2. Create database models and run Alembic migrations
3. Implement auth endpoints (register, login, JWT)
4. Build suppliers CRUD
5. Implement SP-API client with token refresh
6. Build ASIN analyzer service
7. Create deals endpoints
8. Set up Celery tasks
9. Add Telegram webhook handler
10. Implement WebSocket for real-time updates
11. Add Stripe billing endpoints

## TESTING

Create tests in `/tests/`:
- Unit tests for profit calculator
- Integration tests for API endpoints
- Mock SP-API responses for testing

Start building! Ask questions if you need clarification on any integration.
```

---

# 📋 QUICK REFERENCE CARD

## Give These Files to Cursor

When working with Cursor, attach these files to your conversation:

1. **UI/UX Blueprint** - For frontend styling and component specs
2. **SP-API Integration Guide** - For backend API implementation
3. **This Cursor Prompts File** - For specific build instructions

## Workflow

```
Week 1-2: Frontend
├── Day 1-2: Theme + Layout + Sidebar
├── Day 3-4: Dashboard + Stat Cards
├── Day 5-7: Deal Feed + Detail Panel
├── Day 8-10: Suppliers + Analyze
└── Day 11-14: Settings + Polish

Week 3-4: Backend
├── Day 1-2: FastAPI setup + Auth
├── Day 3-4: Database + Models
├── Day 5-7: SP-API Integration
├── Day 8-10: Analysis Pipeline
└── Day 11-14: Telegram + Real-time
```

## Key Commands for Cursor

```
// Start new feature
"Create the [ComponentName] component following the design system in the attached blueprint"

// Fix styling
"Update the styling to match the design system - use the exact colors and spacing from the blueprint"

// Add functionality
"Implement the [feature] as described in the user stories section of the blueprint"

// Connect to backend
"Connect this component to the API endpoint [endpoint] and handle loading/error states"
```

---

*Last Updated: [Current Date]*
*Version: 1.0*
