# VICTORUS AI — Version 1

**AI Workforce Platform — Frontend + Backend Foundation (No AI Model Connected Yet)**

This is Version 1 of VICTORUS AI: the complete platform — authentication, onboarding,
a 16-page dashboard, and a REST API — built so that plugging in a real AI model
(Gemini, Claude, OpenAI, or a local Ollama model) in Version 2 requires editing
**one file**: `backend/app/services/ai_service.py`.

Every conversation route already calls `AIService.generate_response()`. Right now it
returns:

> "I'm your AI assistant. AI integration will be added in Version 2."

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JavaScript (no framework) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT (access + refresh tokens), bcrypt password hashing |

---

## 📁 Project Structure

```
victorus-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── seed.py                # Seeds the AI agent catalog
│   │   ├── core/                  # Config + security (JWT, hashing)
│   │   ├── db/                    # Engine, session, declarative base
│   │   ├── models/                # SQLAlchemy models (11 tables)
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ai_service.py      # ⭐ THE Version 2 integration point
│   │   │   ├── file_service.py
│   │   │   └── email_service.py
│   │   ├── api/v1/                # All REST routers
│   │   └── uploads/                # Local file storage (dev)
│   ├── alembic/                    # DB migration environment
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── index.html                  # Landing page
    ├── auth/                       # Login, Register, Forgot/Reset Password, OTP
    ├── onboarding/                 # 6-step onboarding wizard
    ├── dashboard/                  # 16 dashboard pages
    └── assets/
        ├── css/                    # design-system.css + per-section CSS
        └── js/                     # api.js, layout.js, ui.js, etc.
```

---

## 🚀 Getting Started

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env: set DATABASE_URL to your local PostgreSQL instance and a real SECRET_KEY

# Create the database (adjust to your Postgres setup)
createdb victorus_db

# Run migrations (or let dev auto-create tables — see note below)
alembic revision --autogenerate -m "init"
alembic upgrade head

# Seed the AI agent catalog (Developer AI, Marketing AI, etc.)
python -m app.seed

# Run the API
uvicorn app.main:app --reload --port 8000
```

The API will be live at **http://localhost:8000**, with interactive docs at
**http://localhost:8000/docs**.

> **Dev convenience:** if `APP_ENV=development` (the default), the app also calls
> `Base.metadata.create_all()` on startup, so tables exist even before you run
> Alembic migrations. Use Alembic for anything beyond local development.

### 2. Frontend

The frontend is static HTML/CSS/JS — no build step. Serve it with any static
file server, for example:

```bash
cd frontend
python -m http.server 5500
```

Then open **http://localhost:5500**. The frontend expects the API at
`http://<same-host>:8000/api/v1` (see `assets/js/api.js`).

Make sure `CORS_ORIGINS` in `backend/.env` includes whatever origin you're
serving the frontend from (e.g. `http://localhost:5500`).

---

## 🔌 Plugging In AI (Version 2)

Everything in the platform — the chat UI, the conversation API, the dummy
reply — already flows through one seam:

```python
# backend/app/services/ai_service.py

class AIService:
    async def generate_response(self, message, history, agent_key, user_context) -> str:
        return self.DEFAULT_REPLY   # <-- replace this
```

To connect Gemini, for example:

```bash
pip install google-generativeai
```

```python
import google.generativeai as genai
genai.configure(api_key=settings.GEMINI_API_KEY)

async def generate_response(self, message, history, agent_key, user_context) -> str:
    model = genai.GenerativeModel("gemini-1.5-pro")
    chat = model.start_chat(history=self._to_gemini_history(history))
    result = chat.send_message(message)
    return result.text
```

No router, model, schema, or frontend file needs to change.

---

## 🗄️ Database Schema (11 tables)

`users`, `user_profiles`, `user_skills`, `user_files`, `notifications`,
`conversations`, `messages`, `agents`, `user_agents`, `tasks`,
`activity_logs`, `login_sessions`, `api_keys`, `integrations`.

---

## 🔐 Authentication Flow

1. **Register** → account created, 6-digit OTP emailed (logged to console in dev)
2. **Verify OTP** → email marked verified
3. **Onboarding** (first login only) → 6-step wizard, saved to `user_profiles`
4. **Dashboard** → full workspace unlocked

JWT access tokens expire in 60 minutes by default; refresh tokens in 7 days.
The frontend (`assets/js/api.js`) automatically retries a request once with a
refreshed access token on a 401.

---

## 📡 API Overview

All endpoints are namespaced under `/api/v1` and documented interactively at
`/docs` (Swagger) and `/redoc`. Route groups:

`/auth`, `/onboarding`, `/profile`, `/files`, `/notifications`,
`/conversations`, `/agents`, `/tasks`, `/dashboard`, `/settings`,
`/security`, `/api-keys`, `/integrations`.

---

## ✅ What's Included in Version 1

- Full JWT auth: register, login, refresh, logout, logout-all-devices,
  forgot/reset password, change password, OTP email verification
- 6-step onboarding wizard with skill autocomplete and resume upload
- 16-page dashboard: Overview, Conversations, Memory, Agents, Integrations,
  Analytics, Tasks, Files, Notifications, Billing, Profile, Settings, Help,
  API Keys, Security, Activity Logs
- File upload/rename/delete/search/filter
- Notification center with unread counts
- Session & device management
- API key generation
- Dummy AI service wired into a real chat UI — ready for Version 2

## 🚫 What's Deliberately NOT Included (by design)

- No AI model integration (Gemini, Claude, OpenAI, Ollama) — that's Version 2
- No payment processor integration on the Billing page (UI only)
- No production email/SMTP sending (OTP and reset emails are logged to console)

---

## 📄 License

Proprietary — VICTORUS AI. All rights reserved.
