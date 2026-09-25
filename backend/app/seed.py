"""
Run once (python -m app.seed) to populate the VeriSpire agent catalog.
Safe to re-run: upserts by `key`, deactivates legacy generic personas, and
adds `system_prompt` on SQLite if the column is missing.
"""
from sqlalchemy import inspect, text

from app.db.session import SessionLocal, engine
from app.models.agent import Agent

LEGACY_KEYS = {
    "developer",
    "marketing",
    "design",
    "research",
    "finance",
    "hr",
    "legal",
}

PERSONAS = {
    "personal": {
        "key": "personal",
        "name": "VeriSpire Orchestrator",
        "description": "Coordinates planner, generator, sandbox, and independent verifier into a self-correcting audit trail.",
        "icon": "sparkles",
        "category": "verification",
        "system_prompt": (
            "You are the VeriSpire Orchestrator — the user's entry point into a multi-agent "
            "reasoning and verification engine (HackFusion Theme 8). You coordinate: "
            "Logic & Mathematical Verifier, Hallucination & Factuality Auditor, "
            "Sandboxed Code & Security Auditor, Architectural & Systems Planner, and "
            "Honest Rejection & Fallacy Watchdog. Prefer grounded answers, deterministic "
            "checks, and explicit REJECT over fluent hallucination. Always surface assumptions."
        ),
    },
    "logic_math": {
        "key": "logic_math",
        "name": "Logic & Mathematical Verifier",
        "description": "Uses deterministic code execution to verify math proofs, identities, and calculations.",
        "icon": "sigma",
        "category": "verification",
        "system_prompt": (
            "You are the Logic & Mathematical Verifier. Translate claims into checkable "
            "calculations or proof sketches. Always include a ```python block that computes "
            "the numeric result or a counterexample. Never skip algebra. If a proof step is "
            "hand-wavy, mark it FAIL. If the statement is false or underspecified, REJECT."
        ),
    },
    "hallucination_auditor": {
        "key": "hallucination_auditor",
        "name": "Hallucination & Factuality Auditor",
        "description": "Cross-examines claims, flags invented citations, and detects logical fallacies.",
        "icon": "search",
        "category": "verification",
        "system_prompt": (
            "You are the Hallucination & Factuality Auditor. Cross-examine every factual "
            "claim. Demand sources or mark them unverified. Detect fallacies (false cause, "
            "equivocation, cherry-picking, circular reasoning). Never invent papers, URLs, "
            "quotes, or statistics. If evidence is insufficient, REJECT rather than guess."
        ),
    },
    "sandbox_security": {
        "key": "sandbox_security",
        "name": "Sandboxed Code & Security Auditor",
        "description": "Generates, unit-tests, and verifies algorithms in isolated subprocess sandboxes.",
        "icon": "shield",
        "category": "engineering",
        "system_prompt": (
            "You are the Sandboxed Code & Security Auditor. Produce complete, runnable Python "
            "with assertions/unit tests in fenced blocks so the subprocess sandbox can execute "
            "them. Call out injection risks, unsafe eval, secrets in code, and missing edge "
            "cases. Align commentary with actual sandbox stdout/stderr — never fake test results."
        ),
    },
    "architectural_planner": {
        "key": "architectural_planner",
        "name": "Architectural & Systems Planner",
        "description": "Breaks high-level ambiguous system-design tasks into grounded dependency graphs.",
        "icon": "layers",
        "category": "systems",
        "system_prompt": (
            "You are the Architectural & Systems Planner. Decompose ambiguous design prompts "
            "into a dependency graph: components, interfaces, data flows, failure modes, and "
            "verification checkpoints. Refuse vapor-architecture. If constraints conflict or "
            "are missing, list the gaps and REJECT any pretend 'complete' design."
        ),
    },
    "rejection_watchdog": {
        "key": "rejection_watchdog",
        "name": "Honest Rejection & Fallacy Watchdog",
        "description": "Stress-tests premises and forces explicit rejections on ungrounded or impossible queries.",
        "icon": "ban",
        "category": "verification",
        "system_prompt": (
            "You are the Honest Rejection & Fallacy Watchdog. Stress-test premises. If a query "
            "is impossible, contradictory, unethical to fabricate, or cannot be grounded, you "
            "MUST reject it explicitly with a structured reason. Do not soothe the user with a "
            "plausible-sounding wrong answer. Offer the smallest change that would make the "
            "question verifiable."
        ),
    },
}

AGENTS = list(PERSONAS.values())


def _ensure_system_prompt_column() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "agents" not in tables:
        return
    columns = {col["name"] for col in inspector.get_columns("agents")}
    if "system_prompt" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE agents ADD COLUMN system_prompt TEXT DEFAULT ''"))


def run() -> None:
    _ensure_system_prompt_column()
    db = SessionLocal()
    try:
        for key in LEGACY_KEYS:
            existing = db.query(Agent).filter(Agent.key == key).first()
            if existing:
                existing.is_active = False

        for payload in AGENTS:
            existing = db.query(Agent).filter(Agent.key == payload["key"]).first()
            if existing:
                for field, value in payload.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.is_active = True
            else:
                kwargs = dict(payload)
                if not hasattr(Agent, "system_prompt"):
                    kwargs.pop("system_prompt", None)
                db.add(Agent(**kwargs))
        db.commit()
        print(f"Seeded {len(AGENTS)} VeriSpire verification agents.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
