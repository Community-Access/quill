"""Out-of-process liblouis translation client (#244 / BR-021).

liblouis is NEVER imported in QUILL's process. Each translate call runs a
short-lived worker subprocess (:mod:`quill.core.braille_worker`) through
:func:`quill.stability.safe_subprocess.run_subprocess_safely`, so a liblouis
crash, hang, or memory blow-up can never take QUILL down: the subprocess is
killed on timeout and a fresh one is spawned for the next call (so a crashed
worker is effectively "restarted" with no shared state to corrupt).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass

from quill.core.error_codes import CodedError

DEFAULT_TABLE = "en-ueb-g2"


class WorkerError(CodedError):
    """A translation request failed (worker crash, bad output, or liblouis error)."""

    code = "QUILL-BRAILLE-WORKER-FAILED"


class WorkerTimeoutError(WorkerError):
    """The worker exceeded its timeout and was killed."""


class WorkerUnavailableError(WorkerError):
    """The worker subprocess could not be launched."""


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    """Health snapshot for the translation worker."""

    running: bool
    healthy: bool
    last_alive: float | None
    detail: str = ""


_last_alive: float | None = None
_last_error: str = ""


def _worker_command() -> list[str]:
    return [sys.executable, "-m", "quill.core.braille_worker"]


def _invoke(request: dict[str, str], *, timeout: float) -> dict[str, str]:
    """Run the worker once and return its parsed JSON result.

    Raises WorkerTimeoutError on timeout, WorkerUnavailableError when the
    process cannot launch, and WorkerError on a crash or an error result.
    """
    global _last_alive, _last_error
    payload = json.dumps(request)
    from quill.stability.safe_subprocess import run_subprocess_safely

    try:
        # The payload travels on stdin, never argv: a whole document's text
        # can run to hundreds of KB, well past Windows' ~32K CreateProcess
        # command-line-length limit, which made back/forward-translating any
        # sizeable document fail to launch at all (silently, from the user's
        # perspective -- confirmed by a live report on a ~450KB BRF file).
        completed = run_subprocess_safely(_worker_command(), timeout_seconds=timeout, input=payload)
    except subprocess.TimeoutExpired as exc:
        _last_error = "worker timed out"
        raise WorkerTimeoutError("liblouis worker timed out") from exc
    except (OSError, ValueError) as exc:
        _last_error = str(exc)
        raise WorkerUnavailableError(str(exc)) from exc

    if completed.returncode != 0:
        _last_error = (completed.stderr or "worker crashed").strip()
        raise WorkerError(f"liblouis worker failed: {_last_error}")

    lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
    if not lines:
        _last_error = "worker returned no result"
        raise WorkerError("liblouis worker returned no result")
    try:
        result: dict[str, str] = json.loads(lines[-1])
    except ValueError as exc:
        _last_error = "worker returned unparsable result"
        raise WorkerError("liblouis worker returned an unparsable result") from exc

    if "error" in result:
        _last_error = str(result["error"])
        raise WorkerError(str(result["error"]))
    _last_alive = time.time()
    _last_error = ""
    return result


def forward_translate(text: str, table: str = DEFAULT_TABLE, *, timeout: float = 10.0) -> str:
    """Translate plain text to BRF (forward translation)."""
    return str(
        _invoke({"cmd": "forward", "text": text, "table": table}, timeout=timeout).get("result", "")
    )


def back_translate(brf_text: str, table: str = DEFAULT_TABLE, *, timeout: float = 10.0) -> str:
    """Back-translate BRF to draft text (always treat the result as a draft)."""
    return str(
        _invoke({"cmd": "back", "text": brf_text, "table": table}, timeout=timeout).get(
            "result", ""
        )
    )


def worker_status() -> WorkerStatus:
    """Return the last-known worker health (workers are one-shot, so never running)."""
    return WorkerStatus(
        running=False,
        healthy=not _last_error,
        last_alive=_last_alive,
        detail=_last_error,
    )
