"""A local count of ChatGPT plan requests, per app, kept on this computer.

OpenAI's plan sharing has no usage API and sends no rate-limit headers; a 429
arrives when a limit is met, and that limit may be per app, so QUILL never
infers a reset (codex.md 10A.11, decision 24). What QUILL *can* say truthfully
is how many requests this app sent today and this week, and how many tokens
OpenAI reported for them (``ChatGptAnswer``). That count is kept here.

* **Local, and always called local.** Every sentence built from it says
  "counted on this computer"; it is never used to guess a limit.
* **No network call.** It is written after an answer arrives, from the answer.
* **Per app.** One file per agent name (``<data>/ai/chatgpt-usage-<slug>.json``),
  the same slug the sign-in uses, because each app signs in and is limited on
  its own.
* **Atomic.** Written through :func:`quill.core.storage.write_json_atomic`.

Days are local calendar days; "this week" starts on Monday. Only the last
fourteen days are kept, which is all either number needs.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

__all__ = ["LocalCount", "local_count", "record_request", "usage_path"]

_VERSION = 1
_KEEP_DAYS = 14
_lock = threading.Lock()


def usage_path(data_dir: Path, slug: str) -> Path:
    """Where *slug*'s count lives."""
    return Path(data_dir) / "ai" / f"chatgpt-usage-{slug or 'quill'}.json"


@dataclass(frozen=True, slots=True)
class LocalCount:
    """Requests and tokens this app sent on the plan, as counted here."""

    requests_today: int = 0
    requests_this_week: int = 0
    input_tokens_today: int = 0
    output_tokens_today: int = 0
    input_tokens_this_week: int = 0
    output_tokens_this_week: int = 0


def _today(now: datetime | None) -> date:
    return (now or datetime.now()).date()


def _read(path: Path) -> dict[str, dict[str, int]]:
    try:
        raw: Any = read_json(path, default={})
    except (OSError, ValueError):
        return {}
    days = raw.get("days") if isinstance(raw, dict) else None
    if not isinstance(days, dict):
        return {}
    clean: dict[str, dict[str, int]] = {}
    for key, value in days.items():
        if not isinstance(value, dict):
            continue
        try:
            date.fromisoformat(str(key))
        except ValueError:
            continue
        clean[str(key)] = {
            name: max(0, _int(value.get(name)))
            for name in ("requests", "input_tokens", "output_tokens")
        }
    return clean


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def record_request(
    data_dir: Path,
    slug: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    now: datetime | None = None,
) -> None:
    """Count one answered request and its tokens. Never raises: a count that
    could not be written must not turn a good answer into a failure."""
    path = usage_path(data_dir, slug)
    today = _today(now)
    with _lock:
        try:
            days = _read(path)
            slot = days.setdefault(
                today.isoformat(), {"requests": 0, "input_tokens": 0, "output_tokens": 0}
            )
            slot["requests"] += 1
            slot["input_tokens"] += max(0, int(input_tokens))
            slot["output_tokens"] += max(0, int(output_tokens))
            oldest = today - timedelta(days=_KEEP_DAYS - 1)
            kept = {k: v for k, v in days.items() if date.fromisoformat(k) >= oldest}
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(path, {"version": _VERSION, "days": kept})
        except (OSError, ValueError):
            return


def local_count(data_dir: Path, slug: str, *, now: datetime | None = None) -> LocalCount:
    """Today's and this week's count for *slug*; zeros when nothing was recorded."""
    today = _today(now)
    monday = today - timedelta(days=today.weekday())
    with _lock:
        days = _read(usage_path(data_dir, slug))
    day = days.get(today.isoformat(), {})
    week = [v for k, v in days.items() if monday <= date.fromisoformat(k) <= today]
    return LocalCount(
        requests_today=day.get("requests", 0),
        requests_this_week=sum(v.get("requests", 0) for v in week),
        input_tokens_today=day.get("input_tokens", 0),
        output_tokens_today=day.get("output_tokens", 0),
        input_tokens_this_week=sum(v.get("input_tokens", 0) for v in week),
        output_tokens_this_week=sum(v.get("output_tokens", 0) for v in week),
    )
