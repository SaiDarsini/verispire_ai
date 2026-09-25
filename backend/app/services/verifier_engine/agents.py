"""
Discrete Gemini-backed reasoning roles: Planner, Generator, Independent Verifier.

Uses google-genai Client.aio against gemini-2.5-flash. Structured verification
returns confidence, pass/fail/reject status, and critique feedback.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger("verispire.agents")

GEMINI_MODEL = settings.GEMINI_MODEL or "gemini-2.5-flash"

VERIFICATION_SCHEMA_HINT = """
Return ONLY valid JSON matching this schema (no markdown fences):
{
  "passed": boolean,
  "status": "PASS" | "FAIL" | "REJECT",
  "confidence": number between 0 and 1,
  "critique": string,
  "fallacies": string[],
  "ungrounded_claims": string[],
  "suggested_fixes": string[],
  "factuality_score": number between 0 and 1,
  "logic_score": number between 0 and 1,
  "grounding_score": number between 0 and 1
}
Rules:
- PASS only if the answer is grounded, internally consistent, and (when code ran) compatible with sandbox results.
- FAIL if the answer is salvageable but contains errors, missing checks, or weak evidence.
- REJECT if the query is impossible, ungrounded, or the answer invents facts/proofs that cannot be justified.
"""

PLAN_SCHEMA_HINT = """
Return ONLY valid JSON matching this schema (no markdown fences):
{
  "goal": string,
  "steps": string[],
  "needs_code_execution": boolean,
  "risk_flags": string[],
  "rejection_recommended": boolean,
  "rejection_reason": string,
  "confidence": number between 0 and 1,
  "specialist_focus": string
}
"""


def _client():
    from google import genai

    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()
    candidates = getattr(response, "candidates", None) or []
    parts_out: list[str] = []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            piece = getattr(part, "text", None)
            if piece:
                parts_out.append(piece)
    return "".join(parts_out).strip()


def parse_json_object(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


async def generate_text(
    prompt: str,
    *,
    system_instruction: str = "",
    history: Optional[List[dict]] = None,
    json_mode: bool = False,
    temperature: float = 0.3,
) -> str:
    """Low-level async Gemini call via google-genai."""
    try:
        from google.genai import types
    except ImportError as exc:
        logger.error("[gemini] google-genai is not installed: %s", exc)
        return ""

    if not (settings.GEMINI_API_KEY or "").strip():
        logger.error("[gemini] GEMINI_API_KEY is empty")
        return ""

    contents: list[Any] = []
    for turn in history or []:
        role = "model" if turn.get("role") == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=str(turn.get("content") or ""))])
        )
    contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

    config_kwargs: Dict[str, Any] = {"temperature": temperature}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    try:
        client = _client()
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return _extract_text(response)
    except Exception as exc:  # noqa: BLE001
        logger.error("[gemini] generate_content failed: %s", exc)
        return ""


def _persona_preamble(agent_key: str, user_context: Optional[dict]) -> str:
    from app.seed import PERSONAS

    persona = PERSONAS.get(agent_key) or PERSONAS.get("personal") or {}
    prompt = persona.get("system_prompt") or (
        "You are VeriSpire AI, a multi-agent reasoning and verification engine. "
        "Be precise, cite assumptions, and refuse ungrounded claims."
    )
    if user_context:
        occupation = user_context.get("occupation")
        skills = user_context.get("skills") or []
        if occupation or skills:
            prompt += (
                f"\n\nUser context: occupation = {occupation or 'unknown'}, "
                f"skills = {', '.join(skills) if skills else 'none listed'}."
            )
        memories = user_context.get("memories") or []
        if memories:
            prompt += "\n\nKnown user facts:\n" + "\n".join(f"- {m}" for m in memories)
    return prompt


async def run_planner(
    message: str,
    *,
    agent_key: str = "personal",
    user_context: Optional[dict] = None,
    history: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """Planner: decompose the request into a grounded dependency graph of steps."""
    system = (
        _persona_preamble(agent_key, user_context)
        + "\n\nROLE: Architectural & Systems Planner. Break the user request into "
        "ordered, testable steps. Flag impossibility, missing premises, and whether "
        "deterministic code execution is required. Prefer rejection over speculation "
        "when the query cannot be grounded."
        + "\n\n"
        + PLAN_SCHEMA_HINT
    )
    raw = await generate_text(
        f"User request:\n{message}",
        system_instruction=system,
        history=history,
        json_mode=True,
        temperature=0.2,
    )
    plan = parse_json_object(raw)
    plan.setdefault("goal", message[:240])
    plan.setdefault("steps", ["Analyze the request", "Produce an answer", "Verify independently"])
    plan.setdefault("needs_code_execution", False)
    plan.setdefault("risk_flags", [])
    plan.setdefault("rejection_recommended", False)
    plan.setdefault("rejection_reason", "")
    plan.setdefault("confidence", 0.5)
    plan.setdefault("specialist_focus", agent_key)
    try:
        plan["confidence"] = max(0.0, min(1.0, float(plan["confidence"])))
    except (TypeError, ValueError):
        plan["confidence"] = 0.5
    return plan


async def run_generator(
    message: str,
    *,
    plan: Dict[str, Any],
    agent_key: str = "personal",
    user_context: Optional[dict] = None,
    history: Optional[List[dict]] = None,
    verifier_feedback: Optional[str] = None,
    sandbox_feedback: Optional[str] = None,
) -> str:
    """Generator: produce the user-facing answer, optionally injecting verifier critique."""
    system = (
        _persona_preamble(agent_key, user_context)
        + "\n\nROLE: Generator. Follow the plan. Use markdown (tables, headings, fenced "
        "code). For math, show working and include a ```python block that computes the "
        "result when a numeric check is possible. Never invent citations, APIs, or "
        "execution results. If you cannot ground a claim, say so explicitly."
        "\n\nIf the user asks for a real deliverable, also emit:\n"
        "###FILE: filename.ext###\n<full file content>\n###END###"
    )
    parts = [
        f"Plan goal: {plan.get('goal')}",
        "Plan steps:\n" + "\n".join(f"- {s}" for s in (plan.get("steps") or [])),
        f"Needs code execution: {plan.get('needs_code_execution')}",
        f"Risk flags: {', '.join(plan.get('risk_flags') or []) or 'none'}",
        f"User request:\n{message}",
    ]
    if verifier_feedback:
        parts.append(
            "INDEPENDENT VERIFIER FEEDBACK — revise the entire answer to address this:\n"
            + verifier_feedback
        )
    if sandbox_feedback:
        parts.append("SANDBOX EXECUTION RESULTS — align claims with this telemetry:\n" + sandbox_feedback)
    return await generate_text(
        "\n\n".join(parts),
        system_instruction=system,
        history=history,
        json_mode=False,
        temperature=0.35,
    )


async def run_independent_verifier(
    message: str,
    answer: str,
    *,
    plan: Optional[Dict[str, Any]] = None,
    sandbox_runs: Optional[List[Dict[str, Any]]] = None,
    agent_key: str = "personal",
) -> Dict[str, Any]:
    """Independent Verifier: structured JSON judgment that the generator cannot self-grade."""
    sandbox_summary = json.dumps(sandbox_runs or [], default=str)[:6000]
    system = (
        "You are VeriSpire's Independent Verifier. You did NOT write the answer. "
        "Cross-examine claims, detect hallucinations, logical fallacies, invented "
        "citations, and math that contradicts sandbox output. "
        "If sandbox execution failed or timed out, treat unverified numeric claims as FAIL. "
        "If the query is impossible or the answer is ungrounded, status MUST be REJECT. "
        "Be strict: high confidence only when evidence is explicit."
        "\n\n"
        + VERIFICATION_SCHEMA_HINT
    )
    prompt = (
        f"Original user request:\n{message}\n\n"
        f"Planner notes:\n{json.dumps(plan or {}, default=str)[:3000]}\n\n"
        f"Candidate answer:\n{answer[:12000]}\n\n"
        f"Sandbox telemetry JSON:\n{sandbox_summary}\n\n"
        f"Specialist context key: {agent_key}"
    )
    raw = await generate_text(
        prompt,
        system_instruction=system,
        json_mode=True,
        temperature=0.1,
    )
    report = parse_json_object(raw)
    status = str(report.get("status") or "").upper()
    if status not in {"PASS", "FAIL", "REJECT"}:
        passed_flag = bool(report.get("passed"))
        status = "PASS" if passed_flag else "FAIL"
    report["status"] = status
    report["passed"] = status == "PASS"
    for key in ("confidence", "factuality_score", "logic_score", "grounding_score"):
        try:
            report[key] = max(0.0, min(1.0, float(report.get(key, 0.5))))
        except (TypeError, ValueError):
            report[key] = 0.5
    report.setdefault("critique", "Verifier returned an unstructured or empty critique.")
    report.setdefault("fallacies", [])
    report.setdefault("ungrounded_claims", [])
    report.setdefault("suggested_fixes", [])
    if not raw:
        report["status"] = "FAIL"
        report["passed"] = False
        report["confidence"] = 0.2
        report["critique"] = "Independent verifier could not complete (missing API key or model error)."
    return report
