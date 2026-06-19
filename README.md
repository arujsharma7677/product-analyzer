# Product Analyser API

FastAPI backend for AI-powered product image analysis using Claude API.

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your keys
3. Run schema.sql in your Supabase SQL editor
4. Install dependencies: `pip install -r requirements.txt`
5. Start server: `uvicorn app.main:app --reload`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/signup | Register new user |
| POST | /auth/login | Login, get JWT token |
| POST | /api/analyse | Analyse product images (requires auth + credits) |
| GET | /api/credits | Get my credit balance |
| POST | /api/credits/add | Add credits to a user |
| GET | /api/credits/history | My usage history |

## Deploy to Railway

1. Push to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Add all .env variables in Railway dashboard
4. Done!

## Credits System

- 1 credit = 1 product analysis (up to 5 images)
- Credits are deducted AFTER successful analysis
- All usage is logged with token count and INR cost

## Cost Reference (Claude Haiku 4.5)

- Input: $1 / 1M tokens
- Output: $5 / 1M tokens
- ~₹1.80 per analysis at $1 = ₹96
