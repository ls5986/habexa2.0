# Habexa - Amazon Sourcing Intelligence Platform

Complete full-stack application for analyzing Amazon product profitability from Telegram/email supplier messages.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.11+
- Supabase account
- Environment variables configured (see `.env.example`)

### 1. Database Setup

1. Go to your Supabase dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `database/schema.sql`
4. Run the SQL script

### 2. Frontend Setup

```bash
cd frontend
pnpm install
cp ../.env .env.local  # Copy and configure environment variables
pnpm dev
```

Frontend will run on `http://localhost:5173`

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env .env  # Copy and configure environment variables
uvicorn app.main:app --reload
```

Backend will run on `http://localhost:8000`

## 📁 Project Structure

```
habexa2.0/
├── frontend/          # React + Vite + MUI
├── backend/           # FastAPI + Python
├── database/          # Supabase schema
└── .env              # Environment variables
```

## 🔑 Environment Variables

See `.env.example` for all required variables. Key ones:

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `ASIN_DATA_API_KEY` - ASIN Data API key
- `OPENAI_API_KEY` - OpenAI API key for message extraction
- `SECRET_KEY` - Random secret for JWT signing

## 🎨 Design System

- Primary Purple: `#7C6AFA`
- Navy: `#1A1A4E`
- Success (Profitable): `#10B981`
- Warning (Review): `#F59E0B`
- Error (Unprofitable): `#EF4444`

## 📚 API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Testing

### Frontend
```bash
cd frontend
pnpm test
```

### Backend
```bash
cd backend
pytest
```

## 📝 Next Steps

1. Set up all environment variables
2. Run database schema in Supabase
3. Start backend server
4. Start frontend dev server
5. Register a new account
6. Connect Telegram/Amazon integrations
7. Start analyzing deals!

## 🐛 Troubleshooting

- **CORS errors**: Make sure `FRONTEND_URL` in backend `.env` matches your frontend URL
- **Database errors**: Verify Supabase connection and that schema is applied
- **API errors**: Check that all API keys are valid in `.env`

## 📄 License

Proprietary - All rights reserved

