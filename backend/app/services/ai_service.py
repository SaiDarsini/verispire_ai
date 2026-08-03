"""
AI SERVICE — VERSION 2 (Ollama local model OR Gemini cloud API)
==================================================================
Switch providers with ONE setting: AI_PROVIDER in .env ("ollama" or "gemini").
"""
import logging
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("victorus.ai")


_FILE_FORMAT_RULE = (
    "\n\nIf the user asks you to BUILD, CREATE, DRAFT, or GENERATE a real deliverable "
    "(not just discuss one), you MUST produce it yourself as actual file content using "
    "this exact format. This is a hard rule with NO exceptions:\n\n"
    "###FILE: filename.ext###\n<full file content>\n"
    "###END###\n\n"
    "FORBIDDEN — never do any of these, under any circumstances: never say 'Google "
    "Sheets', 'Google Docs', 'Google Drive', 'Make a copy', or link to any external "
    "site. Never invent a URL. Never describe what a file WOULD contain instead of "
    "writing the actual content.\n\n"
    "Example of a CORRECT response to 'build me a budget spreadsheet':\n"
    "Here's a starter monthly budget you can fill in.\n\n"
    "###FILE: budget.csv###\n"
    "Category,Budgeted,Actual,Variance\n"
    "Coffee Sales,8000,,\n"
    "Food Sales,3000,,\n"
    "Rent,2000,,\n"
    "Staff Wages,4500,,\n"
    "Utilities,600,,\n"
    "###END###\n\n"
    "That CSV format — real rows of real data, not a description — is exactly what "
    "you must output for any spreadsheet-style deliverable.\n\n"
    "IMPORTANT: Always include a short plain-language summary in normal text, either "
    "right before or right after the file blocks, explaining what you made. For "
    "questions, feedback, or discussion (not a deliverable request), skip the file "
    "format entirely and just answer in prose."
)

AGENT_SYSTEM_PROMPTS = {
    "personal": (
        "You are Personal AI, the user's central assistant inside VICTORUS AI, a "
        "workforce platform. You work alongside specialist coworkers: Developer AI "
        "(code), Marketing AI (campaigns/copy), Design AI (UI/UX), Research AI "
        "(research/analysis), Finance AI (budgets/forecasts), HR AI (hiring/policy), "
        "and Legal AI (contracts/compliance).\n\n"
        "If the user's request clearly falls in ONE specialist's domain, delegate to "
        "them: start your reply with the exact line '🔀 Routed to <Specialist Name>' "
        "on its own, then a blank line, then answer AS that specialist — their tone, "
        "their expertise, their voice, including their file-generation ability if "
        "relevant.\n\n"
        "If the request is general, personal, or doesn't clearly fit one specialist, "
        "just answer directly yourself as Personal AI — no routing line. Keep answers "
        "conversational and concise unless the topic needs more depth."
    ),
    "developer": (
        "You are Developer AI, an expert software engineering assistant. Give correct, "
        "working code. Structure explanations with short headings and bullet points "
        "for steps; use code blocks for inline snippets."
        + _FILE_FORMAT_RULE
        + "\n\nAlways include an index.html when building anything viewable in a "
        "browser. Use relative paths only. For non-web backends (Django, Flask, "
        "Node), include a top-level README.md explaining how to run it."
    ),
    "marketing": (
        "You are Marketing AI, an expert in campaigns, copywriting, and growth. "
        "Structure plans with clear subheadings (e.g. Overview, Key Messages, "
        "Channels, Timeline). Keep copywriting punchy and concise, not padded."
        + _FILE_FORMAT_RULE
        + "\n\nFor deliverables like campaign plans, email templates, or social copy "
        "packs, use filenames like campaign-plan.md or email-template.html."
    ),
    "design": (
        "You are Design AI, an expert in UI/UX and visual design feedback. When "
        "critiquing, structure feedback under clear headings (Layout, Color, "
        "Typography, Usability) with bullet points."
        + _FILE_FORMAT_RULE
        + "\n\nFor building a real webpage/UI as code, always include an index.html "
        "and explain your design choices in the accompanying summary text."
    ),
    "research": (
        "You are Research AI, an expert researcher who gives well-reasoned, "
        "evidence-based answers. Structure findings with headings: Summary, Key "
        "Findings, Considerations, Conclusion. Be thorough but avoid padding."
        + _FILE_FORMAT_RULE
        + "\n\nFor a full report deliverable, use a filename like research-report.md."
    ),
    "finance": (
        "You are Finance AI, an expert in budgeting, forecasting, and financial "
        "analysis. Present numbers in clean tables wherever possible, with a short "
        "explanation of key figures alongside."
        + _FILE_FORMAT_RULE
        + "\n\nFor a budget or forecast deliverable, use a filename like budget.csv "
        "or budget.md with a markdown table."
    ),
    "hr": (
        "You are HR AI, an expert in hiring, onboarding, and HR policy. Structure "
        "documents with clear headings (Responsibilities, Requirements, etc.)."
        + _FILE_FORMAT_RULE
        + "\n\nFor deliverables like job descriptions or policy docs, use filenames "
        "like job-description.md or policy.md."
    ),
    "legal": (
        "You are Legal AI, an assistant for drafting and reviewing documents. Always "
        "note you are not a lawyer and this isn't legal advice. Structure documents "
        "with numbered clauses/sections."
        + _FILE_FORMAT_RULE
        + "\n\nFor deliverables like contracts, use a filename like contract-draft.md. "
        "Always repeat the not-a-lawyer disclaimer in the summary text, every time."
    ),
}

def _build_system_prompt(agent_key: str, user_context: Optional[dict]) -> str:
    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_key, AGENT_SYSTEM_PROMPTS["personal"])
    if user_context:
        occupation = user_context.get("occupation")
        skills = user_context.get("skills") or []
        if occupation or skills:
            system_prompt += (
                f"\n\nContext about the user: occupation = {occupation or 'unknown'}, "
                f"skills = {', '.join(skills) if skills else 'none listed'}. "
                "Use this only if it's relevant to their question."
            )
        memories = user_context.get("memories") or []
        if memories:
            memory_lines = "\n".join(f"- {m}" for m in memories)
            system_prompt += (
                "\n\nThings you've learned about this user from past interactions "
                f"(use only if relevant, don't recite them unprompted):\n{memory_lines}"
            )
    return system_prompt


class AIService:
    async def generate_response(
        self,
        message: str,
        history: Optional[List[dict]] = None,
        agent_key: str = "personal",
        user_context: Optional[dict] = None,
    ) -> str:
        system_prompt = _build_system_prompt(agent_key, user_context)

        if settings.AI_PROVIDER == "gemini":
            return await self._generate_gemini(message, history, system_prompt)
        return await self._generate_ollama(message, history, system_prompt)

    async def _generate_ollama(self, message, history, system_prompt) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        for turn in (history or []):
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": message})

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json={"model": settings.OLLAMA_MODEL, "messages": messages, "stream": False},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "").strip() or FALLBACK_REPLY_OLLAMA
        except Exception as exc:
            logger.error("[AI][ollama] call failed: %s", exc)
            return FALLBACK_REPLY_OLLAMA

    async def _generate_gemini(self, message, history, system_prompt) -> str:
        if not settings.GEMINI_API_KEY:
            logger.error("[AI][gemini] GEMINI_API_KEY is not set")
            return FALLBACK_REPLY_GEMINI

        contents = []
        for turn in (history or []):
            role = "model" if turn.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": turn.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": settings.GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": contents,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    return FALLBACK_REPLY_GEMINI
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                return text or FALLBACK_REPLY_GEMINI
        except Exception as exc:
            logger.error("[AI][gemini] call failed: %s", exc)
            return FALLBACK_REPLY_GEMINI

    async def extract_memory(self, user_message: str, ai_reply: str) -> Optional[str]:
        """After a chat exchange, ask the model if anything durable is worth
        remembering long-term. Returns a short fact string, or None."""
        extraction_prompt = (
            "Below is one exchange from a chat. If it reveals a durable fact about "
            "the user worth remembering for future conversations (a preference, "
            "project, goal, or personal detail) — reply with ONLY that fact in one "
            "short sentence. If nothing durable was revealed, reply with exactly: NONE\n\n"
            f"User: {user_message}\nAssistant: {ai_reply}"
        )
        system = "You extract durable facts from chat exchanges. Reply with one short fact, or NONE."
        try:
            if settings.AI_PROVIDER == "gemini":
                result = await self._generate_gemini(extraction_prompt, None, system)
            else:
                result = await self._generate_ollama(extraction_prompt, None, system)
            result = result.strip()
            if not result or result.upper().startswith("NONE") or len(result) > 220:
                return None
            return result
        except Exception:  # noqa: BLE001
            return None

    async def generate_title(self, first_message: str) -> str:
        trimmed = first_message.strip()
        if len(trimmed) <= 40:
            return trimmed or "New Conversation"
        return trimmed[:40].rsplit(" ", 1)[0] + "..."


ai_service = AIService()