"""
Subprocess isolation for deterministic code and math verification.

Runs untrusted snippets in a short-lived child process with a hard timeout,
captures stdout/stderr, and returns execution telemetry — never raises to
the caller.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings

DEFAULT_TIMEOUT = float(getattr(settings, "SANDBOX_TIMEOUT_SECONDS", 5.0) or 5.0)

_RESTRICTED_ENV_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE")

_SECURITY_PATTERNS = (
    r"\bwhile\s+True\b",
    r"\bfor\s+\w+\s+in\s+iter\(.*None",
    r"(?:os|pathlib|shutil)\.(?:remove|unlink|rmtree|system|popen|fork)\b",
    r"(?:rm\s+-rf|del\s+/[sq]|format\s+[a-z]:)",
    r"open\s*\([^\n]*(?:\.env|/etc/|\\windows\\|\\system32)",
)


def _restricted_env() -> Dict[str, str]:
    env = {key: os.environ.get(key, "") for key in _RESTRICTED_ENV_KEYS if os.environ.get(key)}
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def execute_python(
    code: str,
    *,
    timeout: Optional[float] = None,
    stdin_data: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Python source in an isolated subprocess.

    Returns a telemetry dict with stdout, stderr, exit code, duration, and
    a high-level status. Exceptions and timeouts are captured, not raised.
    """
    timeout = DEFAULT_TIMEOUT if timeout is None else float(timeout)
    started = time.perf_counter()
    run_id = uuid.uuid4().hex[:12]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"verispire_sbx_{run_id}_"))
    source_path = tmp_dir / "snippet.py"

    result: Dict[str, Any] = {
        "run_id": run_id,
        "language": "python",
        "timeout_seconds": timeout,
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "timed_out": False,
        "ok": False,
        "error": None,
        "duration_ms": 0.0,
        "latency_ms": 0,
        "bytes_stdout": 0,
        "bytes_stderr": 0,
        "workdir": str(tmp_dir),
    }

    import re

    if any(re.search(pattern, code, re.IGNORECASE) for pattern in _SECURITY_PATTERNS):
        result.update({
            "security_halt": True,
            "error": "SECURITY HALT: code rejected by sandbox pre-screen",
            "stderr": "SECURITY HALT: hostile loop or destructive filesystem operation detected",
        })
        try:
            tmp_dir.rmdir()
        except OSError:
            pass
        return result

    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", code],
            cwd=str(tmp_dir),
            env=_restricted_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = process.communicate(input=stdin_data, timeout=min(timeout, 5.0))
        result["stdout"] = (stdout or "")[-8000:]
        result["stderr"] = (stderr or "")[-8000:]
        result["exit_code"] = process.returncode
        result["ok"] = process.returncode == 0
        if process.returncode != 0:
            result["error"] = f"Process exited with {process.returncode}"
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            process.kill()
            stdout, stderr = process.communicate()
        else:
            stdout, stderr = "", ""
        result["timed_out"] = True
        result["ok"] = False
        result["exit_code"] = process.returncode if process is not None else None
        result["stdout"] = ((stdout or exc.stdout or "") if isinstance(stdout or exc.stdout, str) else "")[-8000:]
        result["stderr"] = ((stderr or exc.stderr or "") if isinstance(stderr or exc.stderr, str) else "")[-8000:]
        result["error"] = f"Sandbox timeout after {timeout}s"
    except Exception as exc:  # noqa: BLE001
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["stderr"] = str(exc)
    finally:
        result["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["latency_ms"] = int(result["duration_ms"])
        result["bytes_stdout"] = len(result["stdout"].encode("utf-8", errors="replace"))
        result["bytes_stderr"] = len(result["stderr"].encode("utf-8", errors="replace"))
        try:
            for child in tmp_dir.glob("*"):
                child.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except OSError:
            pass

    return result


def extract_python_blocks(markdown: str) -> list[str]:
    """Pull fenced ```python / ```py blocks (and a trailing ```code fallback)."""
    blocks: list[str] = []
    if not markdown:
        return blocks
    fence = "```"
    i = 0
    text = markdown
    while True:
        start = text.find(fence, i)
        if start < 0:
            break
        lang_end = text.find("\n", start + 3)
        if lang_end < 0:
            break
        lang = text[start + 3 : lang_end].strip().lower()
        end = text.find(fence, lang_end + 1)
        if end < 0:
            break
        body = text[lang_end + 1 : end].strip()
        if body and lang in {"python", "py", "python3", ""}:
            # Skip empty-language fences that look like JSON/shell.
            if lang == "" and not _looks_like_python(body):
                i = end + 3
                continue
            blocks.append(body)
        i = end + 3
    return blocks


def _looks_like_python(body: str) -> bool:
    markers = ("def ", "import ", "print(", "assert ", "class ", "lambda ", "=")
    return any(m in body for m in markers)


def execute_extracted_python(markdown: str, *, timeout: Optional[float] = None) -> list[Dict[str, Any]]:
    blocks = extract_python_blocks(markdown)
    return [execute_python(block, timeout=timeout) for block in blocks]
