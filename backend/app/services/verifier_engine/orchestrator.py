"""
Iterative multi-agent loop: Planner → Generator → Sandbox → Independent Verifier.

Retries inject verifier critique back into the generator. Exhausted retries or
explicit REJECT produce a clear, human-readable rejection. The returned payload
always includes a hallucination-risk confidence matrix and execution latency telemetry.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.verifier_engine.agents import (
    run_generator,
    run_independent_verifier,
    run_planner,
)
from app.services.verifier_engine.sandbox import execute_extracted_python

HONEST_REJECTION_TEMPLATE = """I cannot verify this request because {reason}

**Suggested Adjustment:**
{fixes}
"""


def _clamp(value: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _format_sandbox_feedback(runs: List[Dict[str, Any]]) -> str:
    if not runs:
        return ""
    lines = []
    for run in runs:
        status = "OK" if run.get("ok") else ("TIMEOUT" if run.get("timed_out") else "ERROR")
        lines.append(
            f"- run {run.get('run_id')} [{status}] exit={run.get('exit_code')} "
            f"duration_ms={run.get('duration_ms')}"
        )
        if run.get("stdout"):
            lines.append(f"  stdout: {run['stdout'][:1500]}")
        if run.get("stderr"):
            lines.append(f"  stderr: {run['stderr'][:1500]}")
        if run.get("error"):
            lines.append(f"  error: {run['error']}")
    return "\n".join(lines)


def _build_confidence_matrix(
    plan: Dict[str, Any],
    verification: Dict[str, Any],
    sandbox_runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    planner_c = _clamp(plan.get("confidence", 0.5))
    verifier_c = _clamp(verification.get("confidence", 0.5))
    factuality = _clamp(verification.get("factuality_score", verifier_c))
    logic = _clamp(verification.get("logic_score", verifier_c))
    grounding = _clamp(verification.get("grounding_score", verifier_c))

    if sandbox_runs:
        oks = sum(1 for r in sandbox_runs if r.get("ok"))
        sandbox_c = oks / len(sandbox_runs)
        if any(r.get("timed_out") for r in sandbox_runs):
            sandbox_c *= 0.4
    else:
        sandbox_c = 0.7 if not plan.get("needs_code_execution") else 0.25

    composite = round(
        0.15 * planner_c + 0.20 * logic + 0.25 * factuality + 0.20 * grounding + 0.20 * sandbox_c,
        4,
    )
    if verification.get("status") == "REJECT":
        composite = round(min(composite, 0.15), 4)
    hallucination_risk = round(1.0 - composite, 4)
    return {
        "planner": round(planner_c, 4),
        "verifier": round(verifier_c, 4),
        "factuality": round(factuality, 4),
        "logic": round(logic, 4),
        "grounding": round(grounding, 4),
        "sandbox": round(sandbox_c, 4),
        "composite_confidence": composite,
        "hallucination_risk": hallucination_risk,
    }


def _audit_markdown(audit: Dict[str, Any]) -> str:
    matrix = audit.get("confidence_matrix") or {}
    traces = audit.get("execution_traces") or []
    trace_rows = []
    for t in traces:
        trace_rows.append(
            f"| {t.get('stage', '')} | {t.get('status', '')} | {t.get('detail', '')[:180]} | {t.get('latency_ms', 0)} ms |"
        )
    if not trace_rows:
        trace_rows.append("| — | — | — | — |")

    sandbox = audit.get("sandbox_runs") or []
    sandbox_rows = []
    for run in sandbox:
        badge = "PASS" if run.get("ok") else ("TIMEOUT" if run.get("timed_out") else "FAIL")
        sandbox_rows.append(
            f"| `{run.get('run_id')}` | {badge} | {run.get('exit_code')} | {run.get('duration_ms')} ms | {(run.get('error') or 'ok')[:80]} |"
        )
    if not sandbox_rows:
        sandbox_rows.append("| — | skipped | — | — | no executable python blocks |")

    status = audit.get("final_status", "FAIL")
    return (
        "\n\n<!--VERISPIRE_AUDIT-->\n"
        "<details>\n"
        f"<summary>Verification Audit Trail — {status} · confidence {matrix.get('composite_confidence', 0)} · hallucination risk {matrix.get('hallucination_risk', 0)}</summary>\n\n"
        f"**Final status:** `{status}`  \n"
        f"**Attempts:** {audit.get('attempts')} / {audit.get('max_retries') + 1}  \n"
        f"**Total latency:** {audit.get('total_latency_ms')} ms  \n"
        f"**Hallucination risk score:** {matrix.get('hallucination_risk')}\n\n"
        "### Confidence matrix\n\n"
        "| Signal | Score |\n|---|---|\n"
        f"| Planner | {matrix.get('planner')} |\n"
        f"| Logic | {matrix.get('logic')} |\n"
        f"| Factuality | {matrix.get('factuality')} |\n"
        f"| Grounding | {matrix.get('grounding')} |\n"
        f"| Sandbox | {matrix.get('sandbox')} |\n"
        f"| Verifier | {matrix.get('verifier')} |\n"
        f"| Composite | {matrix.get('composite_confidence')} |\n"
        f"| Hallucination risk | {matrix.get('hallucination_risk')} |\n\n"
        "### Execution traces\n\n"
        "| Stage | Status | Detail | Latency |\n|---|---|---|---|\n"
        + "\n".join(trace_rows)
        + "\n\n### Sandbox telemetry\n\n"
        + "| Run | Status | Exit | Duration | Error |\n|---|---|---|---|---|\n"
        + "\n".join(sandbox_rows)
        + "\n\n"
        + f"**Verifier critique:** {audit.get('critique', '')}\n\n"
        + "</details>\n"
        + f"\n```json\n{json.dumps(audit, default=str, indent=2)[:12000]}\n```\n"
    )


class OrchestratorEngine:
    def __init__(self, max_retries: Optional[int] = None) -> None:
        self.max_retries = int(
            settings.VERIFIER_MAX_RETRIES if max_retries is None else max_retries
        )

    async def run(
        self,
        message: str,
        history: Optional[List[dict]] = None,
        agent_key: str = "orchestrator",
        user_context: Optional[dict] = None,
    ) -> str:
        started = time.perf_counter()
        traces: List[Dict[str, Any]] = []
        sandbox_runs: List[Dict[str, Any]] = []
        verifier_feedback: Optional[str] = None
        sandbox_feedback: Optional[str] = None
        answer = ""
        verification: Dict[str, Any] = {
            "status": "FAIL",
            "passed": False,
            "confidence": 0.0,
            "critique": "",
            "suggested_fixes": [],
        }

        t0 = time.perf_counter()
        plan = await run_planner(
            message, agent_key=agent_key, user_context=user_context, history=history
        )
        traces.append(
            {
                "stage": "planner",
                "status": "REJECT" if plan.get("rejection_recommended") else "PASS",
                "detail": plan.get("goal") or "Plan produced",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
        )

        if plan.get("rejection_recommended"):
            reason = plan.get("rejection_reason") or "The request contains invalid premises or ungrounded assumptions."
            answer = HONEST_REJECTION_TEMPLATE.format(
                reason=reason,
                fixes="- Provide verifiable premises, valid release versions, or specific constraints.",
            )
            verification = {
                "status": "REJECT",
                "passed": False,
                "confidence": 0.95,
                "critique": reason,
                "factuality_score": 0.1,
                "logic_score": 0.9,
                "grounding_score": 0.1,
                "suggested_fixes": ["Restate with checkable premises."],
                "fallacies": plan.get("risk_flags") or [],
                "ungrounded_claims": [],
            }
        else:
            for attempt in range(self.max_retries + 1):
                t_gen = time.perf_counter()
                generated = await run_generator(
                    message,
                    plan=plan,
                    agent_key=agent_key,
                    user_context=user_context,
                    history=history,
                    verifier_feedback=verifier_feedback,
                    sandbox_feedback=sandbox_feedback,
                )
                traces.append(
                    {
                        "stage": f"generator:{attempt + 1}",
                        "status": "PASS" if generated else "FAIL",
                        "detail": (generated or "Empty generation")[:180],
                        "latency_ms": round((time.perf_counter() - t_gen) * 1000, 2),
                    }
                )
                if not generated:
                    verifier_feedback = "Generator returned an empty response. Produce a concise, grounded answer."
                    continue

                t_sbx = time.perf_counter()
                sandbox_runs = execute_extracted_python(generated)
                if sandbox_runs or plan.get("needs_code_execution"):
                    sandbox_feedback = _format_sandbox_feedback(sandbox_runs)
                    sbx_status = "PASS" if sandbox_runs and all(r.get("ok") for r in sandbox_runs) else (
                        "FAIL" if sandbox_runs else "SKIP"
                    )
                    traces.append(
                        {
                            "stage": f"sandbox:{attempt + 1}",
                            "status": sbx_status,
                            "detail": sandbox_feedback[:180] or "No python blocks executed",
                            "latency_ms": round((time.perf_counter() - t_sbx) * 1000, 2),
                        }
                    )

                t_ver = time.perf_counter()
                verification = await run_independent_verifier(
                    message,
                    generated,
                    plan=plan,
                    sandbox_runs=sandbox_runs,
                    agent_key=agent_key,
                )
                traces.append(
                    {
                        "stage": f"verifier:{attempt + 1}",
                        "status": verification.get("status"),
                        "detail": verification.get("critique", "")[:180],
                        "latency_ms": round((time.perf_counter() - t_ver) * 1000, 2),
                    }
                )

                answer = generated
                if verification.get("status") in ("PASS", "REJECT"):
                    break

                fixes = verification.get("suggested_fixes") or []
                verifier_feedback = (
                    f"Status={verification.get('status')} confidence={verification.get('confidence')}\n"
                    f"Critique: {verification.get('critique')}\n"
                    f"Fallacies: {verification.get('fallacies')}\n"
                    f"Ungrounded claims: {verification.get('ungrounded_claims')}\n"
                    f"Suggested fixes: {fixes}\n"
                    + (f"Sandbox:\n{sandbox_feedback}" if sandbox_feedback else "")
                )
            else:
                verification["status"] = verification.get("status") or "FAIL"

            if verification.get("status") != "PASS":
                fixes = verification.get("suggested_fixes") or []
                fix_text = "\n".join(f"- {f}" for f in fixes) or "- Supply checkable premises or a narrower problem."
                if verification.get("status") == "REJECT" or not answer:
                    answer = HONEST_REJECTION_TEMPLATE.format(
                        reason=verification.get("critique") or "The requested claims could not be certified.",
                        fixes=fix_text,
                    )
                    verification["status"] = "REJECT"
                else:
                    answer = (
                        answer.rstrip()
                        + "\n\n> **Verification Notice:** "
                        + str(verification.get("critique") or "Execution outputs could not certify this answer with 100% confidence.")
                    )

        if any(run.get("security_halt") or run.get("timed_out") for run in sandbox_runs):
            verification.update({
                "status": "SECURITY HALT",
                "passed": False,
                "confidence": 1.0,
                "critique": "Subprocess sandbox halted execution due to timeout or restricted operation.",
            })

        total_ms = round((time.perf_counter() - started) * 1000, 2)
        matrix = _build_confidence_matrix(plan, verification, sandbox_runs)
        audit = {
            "final_status": verification.get("status"),
            "passed": verification.get("status") == "PASS",
            "attempts": sum(1 for t in traces if str(t.get("stage", "")).startswith("generator")),
            "max_retries": self.max_retries,
            "agent_key": agent_key,
            "plan": plan,
            "critique": verification.get("critique"),
            "fallacies": verification.get("fallacies") or [],
            "ungrounded_claims": verification.get("ungrounded_claims") or [],
            "confidence_matrix": matrix,
            "hallucination_risk": matrix.get("hallucination_risk"),
            "total_latency_ms": total_ms,
            "execution_traces": traces,
            "sandbox_runs": [
                {
                    "run_id": r.get("run_id"),
                    "ok": r.get("ok"),
                    "timed_out": r.get("timed_out"),
                    "exit_code": r.get("exit_code"),
                    "duration_ms": r.get("duration_ms"),
                    "error": r.get("error"),
                    "stdout": (r.get("stdout") or "")[:2000],
                    "stderr": (r.get("stderr") or "")[:2000],
                }
                for r in sandbox_runs
            ],
        }
        return answer.rstrip() + _audit_markdown(audit)

    async def process_query(
        self,
        prompt: str,
        *,
        agent_key: str = "orchestrator",
        history: Optional[List[dict]] = None,
        user_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Run the pipeline and expose the stable API response contract."""
        raw = await self.run(
            prompt,
            history=history,
            agent_key=agent_key,
            user_context=user_context,
        )
        marker = "<!--VERISPIRE_AUDIT-->"
        content, audit_text = (raw.split(marker, 1) + [""])[:2] if marker in raw else (raw, "")
        audit_data: Dict[str, Any] = {}
        if "```json" in audit_text:
            try:
                audit_data = json.loads(audit_text.split("```json", 1)[1].split("```", 1)[0].strip())
            except (ValueError, IndexError):
                audit_data = {}

        raw_status = str(audit_data.get("final_status") or "FAIL").upper()
        critique_text = str(audit_data.get("critique") or "").upper()
        runs = audit_data.get("sandbox_runs") or []

        if (
            "SECURITY" in raw_status
            or "HALT" in raw_status
            or "TIMEOUT" in critique_text
            or any(r.get("timed_out") or r.get("security_halt") for r in runs)
        ):
            status = "SECURITY HALT"
        elif "REJECT" in raw_status:
            status = "REJECT / REFUSAL"
        elif "PASS" in raw_status:
            status = "PASS"
        else:
            status = "FAIL / REFUTED"

        first_run = runs[0] if runs else {}
        matrix = audit_data.get("confidence_matrix") or {}
        cleaned_content = re.sub(r"###FILE:[^#]*###", "", content)
        cleaned_content = cleaned_content.replace("###END###", "").strip()

        return {
            "content": cleaned_content,
            "audit": {
                "status": status,
                "confidence": float(matrix.get("composite_confidence", 0.0)),
                "hallucination_risk": str(audit_data.get("hallucination_risk", matrix.get("hallucination_risk", "unknown"))),
                "sandbox_exit_code": first_run.get("exit_code"),
                "latency_ms": int(audit_data.get("total_latency_ms", 0)),
                "checks_run": [trace.get("stage", "") for trace in audit_data.get("execution_traces", [])],
            },
        }