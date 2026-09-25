"""
AI SERVICE — routes every chat turn through the VeriSpire OrchestratorEngine.
Memory extraction and titles use a lightweight Gemini call, not the full loop.
"""
import logging
from typing import List, Optional

from app.services.verifier_engine.agents import generate_text
from app.services.verifier_engine.orchestrator import OrchestratorEngine

logger = logging.getLogger("verispire.ai")

orchestrator = OrchestratorEngine()

FALLBACK_REPLY = (
    "VeriSpire AI could not complete a verified response. Check GEMINI_API_KEY, "
    "then retry — the orchestrator will planner → generate → sandbox → verify."
)


class AIService:
    async def generate_response(
        self,
        message: str,
        history: Optional[List[dict]] = None,
        agent_key: str = "personal",
        user_context: Optional[dict] = None,
    ) -> str:
        try:
            return await orchestrator.run(
                message,
                history=history,
                agent_key=agent_key or "personal",
                user_context=user_context,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[orchestrator] failed: %s", exc)
            return FALLBACK_REPLY

    async def extract_memory(self, user_message: str, ai_reply: str) -> Optional[str]:
        extraction_prompt = (
            "Below is one exchange from a chat. If it reveals a durable fact about "
            "the user worth remembering for future conversations (a preference, "
            "project, goal, or personal detail) — reply with ONLY that fact in one "
            "short sentence. If nothing durable was revealed, reply with exactly: NONE\n\n"
            f"User: {user_message}\nAssistant: {ai_reply[:2000]}"
        )
        system = "You extract durable facts from chat exchanges. Reply with one short fact, or NONE."
        try:
            result = await generate_text(
                extraction_prompt,
                system_instruction=system,
                temperature=0.1,
            )
            result = (result or "").strip()
            if not result or result.upper().startswith("NONE") or len(result) > 220:
                return None
            return result
        except Exception:  # noqa: BLE001
            return None

    async def generate_title(self, first_message: str) -> str:
        trimmed = first_message.strip()
        if len(trimmed) <= 40:
            return trimmed or "New Conversation"
        try:
            titled = await generate_text(
                f"Write a 5-8 word conversation title for this message. Reply with the title only.\n\n{trimmed[:400]}",
                system_instruction="You write short conversation titles. No quotes.",
                temperature=0.2,
            )
            titled = (titled or "").strip().strip('"').strip("'")
            if titled and len(titled) <= 80:
                return titled
        except Exception:  # noqa: BLE001
            pass
        return trimmed[:40].rsplit(" ", 1)[0] + "..."


ai_service = AIService()
