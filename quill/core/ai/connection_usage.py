"""Usage, made easy: one sentence per connection, and the one line Ctrl+8 speaks.

The one Usage view (codex.md 10A.11) lists one row a connection that is set up,
and every row says **whose number it is**: QUILL's count for the free AI, a
count kept on this computer for the ChatGPT plan, OpenAI's last answer for an
own key. A local count is always called a local count, a service's number is
always named as the service's, and money is never computed. Everything is a
sentence (decision 13): no meter, gauge or colour carries a number.

The own-key numbers come from the ``x-ratelimit-*`` headers OpenAI sends with
every answer. They are captured from the answer the person already asked for
(:func:`remember_rate_limits`, called by the own-key client), never by a
request of their own, and kept in memory for this session only.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.ai.chatgpt_usage import LocalCount
from quill.core.ai.connection_caps import CHATGPT, CODEX, CONNECTION_NAMES, COPILOT, FREE, OWN_KEY
from quill.core.ai.connection_choice import (
    NO_AI_IN_USE,
    ROW_STATES,
    SIGNED_OUT_BY_OPENAI,
    ConnectionFacts,
    in_use,
    row_states,
)
from quill.core.ai.copilot_quota import CopilotQuota, usage_clause
from quill.core.ai.own_key_providers import LOCAL_ABOUT, PROVIDER_NAMES, USAGE_URLS, is_local

__all__ = [
    "CHATGPT_USAGE_URL",
    "GITHUB_USAGE_URL",
    "RateLimitSnapshot",
    "UsageRow",
    "clear_rate_limits",
    "last_rate_limits",
    "remember_rate_limits",
    "status_cell_text",
    "usage_rows",
    "which_ai_sentence",
]

CHATGPT_USAGE_URL = "https://chatgpt.com/settings/usage"
GITHUB_USAGE_URL = "https://github.com/settings/billing"
_OWN_KEY_USAGE_URLS = USAGE_URLS
_PROVIDER_NAMES = PROVIDER_NAMES


# -- the own key's rate-limit headers -------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RateLimitSnapshot:
    """What OpenAI's last answer said is left, from its ``x-ratelimit-*`` headers."""

    limit_requests: int | None = None
    remaining_requests: int | None = None
    reset_requests: str = ""
    limit_tokens: int | None = None
    remaining_tokens: int | None = None
    reset_tokens: str = ""


_snapshot_lock = threading.Lock()
_snapshots: dict[str, RateLimitSnapshot] = {}


def _header(headers: Any, name: str) -> str:
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    value = getter(name)
    if value is None and isinstance(headers, Mapping):
        for key, candidate in headers.items():
            if str(key).lower() == name:
                value = candidate
                break
    return str(value or "").strip()


def _number(text: str) -> int | None:
    try:
        return int(float(text)) if text else None
    except ValueError:
        return None


def remember_rate_limits(provider: str, headers: Any) -> None:
    """Keep the ``x-ratelimit-*`` headers of an answer that already arrived.

    Ignores an answer that carries none (Gemini sends none; a proxy may strip
    them), so the last real numbers are never replaced with blanks.
    """
    snapshot = RateLimitSnapshot(
        limit_requests=_number(_header(headers, "x-ratelimit-limit-requests")),
        remaining_requests=_number(_header(headers, "x-ratelimit-remaining-requests")),
        reset_requests=_header(headers, "x-ratelimit-reset-requests"),
        limit_tokens=_number(_header(headers, "x-ratelimit-limit-tokens")),
        remaining_tokens=_number(_header(headers, "x-ratelimit-remaining-tokens")),
        reset_tokens=_header(headers, "x-ratelimit-reset-tokens"),
    )
    if snapshot.remaining_requests is None and snapshot.remaining_tokens is None:
        return
    with _snapshot_lock:
        _snapshots[provider] = snapshot


def last_rate_limits(provider: str) -> RateLimitSnapshot | None:
    with _snapshot_lock:
        return _snapshots.get(provider)


def clear_rate_limits() -> None:
    with _snapshot_lock:
        _snapshots.clear()


# -- the rows ------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class UsageRow:
    """One row of the Usage view: the sentence, more detail, and Manage Usage's page."""

    connection: str
    sentence: str
    detail: str = ""
    manage_url: str = ""


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}" if count == 1 else f"{count:,} {word}s"


def _free_clause(quota: Any) -> str:
    if quota is None:
        return "no count yet; QUILL's service sends one with your next request."
    daily_cap = int(getattr(quota, "daily_cap", 0) or 0)
    if daily_cap:
        used = int(getattr(quota, "daily_used", 0) or 0)
        return f"{used:,} of {daily_cap:,} requests today, by QUILL's count. Resets at midnight."
    monthly_cap = int(getattr(quota, "monthly_cap", 0) or 0)
    used = int(getattr(quota, "monthly_used", 0) or 0)
    return f"{used:,} of {monthly_cap:,} requests this month, by QUILL's count."


def _chatgpt_clause(count: LocalCount | None, app_name: str) -> str:
    today = count.requests_today if count is not None else 0
    return f"{_plural(today, 'request')} today from {app_name}, counted on this computer."


def _chatgpt_detail(count: LocalCount | None, app_name: str) -> str:
    if count is None:
        return ""
    return (
        f"This week, {_plural(count.requests_this_week, 'request')} from {app_name}, "
        f"with {count.input_tokens_this_week:,} tokens sent and "
        f"{count.output_tokens_this_week:,} received, as OpenAI reported them. "
        "Counted on this computer."
    )


def _own_key_clause(provider: str, snapshot: RateLimitSnapshot | None) -> str:
    company = _PROVIDER_NAMES.get(provider, provider)
    if provider == "gemini":
        return "Google reports no count of what is left."
    if is_local(provider):
        return f"no limit and no bill. {LOCAL_ABOUT}"
    if snapshot is None or snapshot.remaining_requests is None:
        return f"no count yet; {company} sends one with each answer."
    left = snapshot.remaining_requests
    return f"{_plural(left, 'request')} left this minute, from {company}'s last answer."


def usage_rows(
    facts: ConnectionFacts,
    *,
    app_name: str = "QUILL",
    free_quota: Any = None,
    chatgpt_count: LocalCount | None = None,
    own_key_limits: RateLimitSnapshot | None = None,
    copilot_quota: CopilotQuota | None = None,
) -> list[UsageRow]:
    """One row per connection that is set up, in window order (10A.11).

    The free AI is always listed (it is the default and needs no sign-in to be
    chosen); Copilot is listed as not available yet until this build carries
    it, and with GitHub's own count (*copilot_quota*, read by
    ``CopilotChat.quota``) once this app is signed in.
    """
    rows: list[UsageRow] = []
    rows.append(UsageRow(FREE, f"{CONNECTION_NAMES[FREE]}: {_free_clause(free_quota)}"))
    if facts.chatgpt_signed_in:
        rows.append(
            UsageRow(
                CHATGPT,
                f"{CONNECTION_NAMES[CHATGPT]}: {_chatgpt_clause(chatgpt_count, app_name)} "
                "OpenAI sets the limits; Manage usage opens them.",
                detail=_chatgpt_detail(chatgpt_count, app_name),
                manage_url=CHATGPT_USAGE_URL,
            )
        )
    if not facts.copilot_available:
        rows.append(UsageRow(COPILOT, f"{CONNECTION_NAMES[COPILOT]}: not available yet."))
    elif facts.copilot_signed_in:
        rows.append(
            UsageRow(
                COPILOT,
                f"{CONNECTION_NAMES[COPILOT]}: {usage_clause(copilot_quota)}",
                manage_url=GITHUB_USAGE_URL,
            )
        )
    if facts.own_key_ready:
        provider = facts.own_key_provider
        company = _PROVIDER_NAMES.get(provider, provider)
        rows.append(
            UsageRow(
                OWN_KEY,
                f"{CONNECTION_NAMES[OWN_KEY]}, {company}: "
                f"{_own_key_clause(provider, own_key_limits)}"
                + ("" if is_local(provider) else f" Your bill is on {company}'s page."),
                manage_url=_OWN_KEY_USAGE_URLS.get(provider, ""),
            )
        )
    return rows


# -- Ctrl+8 and the status cell ---------------------------------------------------- #


def which_ai_sentence(
    facts: ConnectionFacts,
    *,
    model: str = "",
    app_name: str = "QUILL",
    free_quota: Any = None,
    chatgpt_count: LocalCount | None = None,
    own_key_limits: RateLimitSnapshot | None = None,
    copilot_quota: CopilotQuota | None = None,
) -> str:
    """The one line Which AI Am I Using speaks: connection, model, one usage clause.

    "My ChatGPT plan, gpt-6. 3 requests today from QUILL, counted on this
    computer." Codex says where its single requests go (10A.13).
    """
    active = in_use(facts)
    if not active:
        stored = facts.stored
        rows = {row.connection: row for row in row_states(facts)}
        if stored in rows and rows[stored].state == SIGNED_OUT_BY_OPENAI:
            return f"{CONNECTION_NAMES[stored]}, {ROW_STATES[SIGNED_OUT_BY_OPENAI]}. {NO_AI_IN_USE}"
        return NO_AI_IN_USE
    name = CONNECTION_NAMES[active]
    chosen = model.strip()
    if active == FREE:
        return f"{name}, QUILL chooses the model. {_capital(_free_clause(free_quota))}"
    if active == CODEX:
        return (
            "Codex, on your ChatGPT plan. Single requests go to the plan directly. "
            f"{_capital(_chatgpt_clause(chatgpt_count, app_name))}"
        )
    if active == CHATGPT:
        lead = f"{name}, {chosen}" if chosen else name
        return f"{lead}. {_capital(_chatgpt_clause(chatgpt_count, app_name))}"
    if active == OWN_KEY:
        provider = facts.own_key_provider
        company = _PROVIDER_NAMES.get(provider, provider)
        lead = f"{name}, {company}" + (f", {chosen}" if chosen else "")
        return f"{lead}. {_capital(_own_key_clause(provider, own_key_limits))}"
    lead = f"{name}, {chosen}" if chosen else name
    if active == COPILOT and copilot_quota is not None:
        return f"{lead}. {usage_clause(copilot_quota)}"
    return f"{lead}."


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


_SHORT_NAMES = {
    FREE: "free",
    CHATGPT: "ChatGPT plan",
    COPILOT: "Copilot",
    CODEX: "Codex",
    OWN_KEY: "own key",
}


def status_cell_text(facts: ConnectionFacts, *, model: str = "") -> str:
    """The status-bar cell (decision 19): "AI: ChatGPT plan", "AI: Copilot, Auto"."""
    active = in_use(facts)
    if not active:
        return "AI: none"
    short = _SHORT_NAMES[active]
    if active == COPILOT and model.strip():
        return f"AI: {short}, {model.strip()}"
    return f"AI: {short}"
