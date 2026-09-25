# VeriSpire AI

**Multi-Agent AI Reasoning & Verification Engine** (HackFusion Theme 8)

VeriSpire AI plans answers, generates them, executes checkable Python in a 5-second subprocess sandbox, then runs an **independent verifier** that returns PASS / FAIL / REJECT, confidence scores, a hallucination-risk matrix, and a self-correcting audit trail.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript |
| Backend | FastAPI |
| Database | SQLite (`sqlite:///./verispire.db`) by default |
| ORM | SQLAlchemy 2.0 |
| Model | Gemini 2.5 Flash via `google-genai` |

## Project structure

```
verispire_ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── seed.py                          # Theme 8 specialist agents
│   │   ├── services/
│   │   │   ├── ai_service.py                # Routes chat through OrchestratorEngine
│   │   │   └── verifier_engine/
│   │   │       ├── sandbox.py               # Subprocess isolation + telemetry
│   │   │       ├── agents.py                # Planner, Generator, Independent Verifier
│   │   │       └── orchestrator.py          # Retry loop + honest rejection
│   │   └── ...
│   └── .env.example
└── frontend/
```

## Getting started

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # then set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Development startup creates tables and seeds verification agents automatically.

```bash
cd frontend
python -m http.server 5500
```

Open http://localhost:5500. The API lives at http://localhost:8000 (docs at `/docs`).

## Verification loop

Every chat message is handled by `OrchestratorEngine`:

1. **Planner** — decomposes the task; may recommend honest rejection.
2. **Generator** — drafts markdown (tables, code, deliverable file blocks).
3. **Sandbox** — runs extracted Python with a hard 5s timeout; captures stdout/stderr.
4. **Independent Verifier** — structured JSON: status, confidence, critique.
5. **Retry** — verifier critique is injected back into the generator up to `VERIFIER_MAX_RETRIES`.
6. **Audit trail** — collapsible metadata with confidence matrix, hallucination risk, and latency.

## Specialist agents

- Logic & Mathematical Verifier
- Hallucination & Factuality Auditor
- Sandboxed Code & Security Auditor
- Architectural & Systems Planner
- Honest Rejection & Fallacy Watchdog
- VeriSpire Orchestrator (default chat)

Re-seed anytime with `python -m app.seed` from `backend/`.

## License

Proprietary — VeriSpire AI. All rights reserved.
