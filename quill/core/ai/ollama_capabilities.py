"""Dynamic Ollama model-capability discovery (no hardcoded model lists).

Ollama's ``/api/show`` endpoint returns a ``capabilities`` array per model --
for example ``["completion", "vision"]`` or ``["completion", "tools"]``. We
query it at runtime so capability badges stay correct as models are added,
renamed, or updated, instead of a name-fragment allowlist that goes stale the
moment a new model family ships.

``/api/tags`` (the model-list endpoint) does NOT include capabilities, so each
model needs its own ``/api/show`` call. These are local, best-effort calls that
reuse the already-audited :func:`quill.core.ai_chat._post_json` egress site --
no new network call site is introduced. Any failure returns ``None`` and the
caller falls back to letting the server speak its own error (the shared POST
path in :mod:`quill.core.assistant_ai` surfaces the response body).

This module is wx-free and strict-typed; the pure helpers
(:func:`capability_badge`, :func:`format_model_line`, :func:`capability_summary`)
are unit-tested directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

# Per-call timeout for /api/show. Local Ollama answers in milliseconds; this is
# a generous ceiling so a busy server does not stall the UI thread's background
# worker for long.
_SHOW_TIMEOUT_S = 5.0

# Capabilities are cached for the process: a model's capabilities do not change
# within a session, and the vision pre-flight plus AI Hub enrichment both call
# this repeatedly. Only successful lookups are cached (a None result is retried
# next time, so restarting Ollama after a failure is picked up).
_CAPABILITY_CACHE: dict[tuple[str, str], list[str]] = {}


def fetch_model_capabilities(
    host: str,
    model: str,
    *,
    timeout_seconds: float = _SHOW_TIMEOUT_S,
) -> list[str] | None:
    """Return the live ``capabilities`` array for one Ollama model, or ``None``.

    ``None`` means "could not determine" (Ollama down, old version without the
    ``capabilities`` field, network error). Callers must treat ``None`` as
    unknown and let the server respond rather than guessing. A non-``None`` list
    (possibly empty) is the authoritative capability set for the model.
    """
    base = (host or "").strip().rstrip("/")
    name = (model or "").strip()
    if not base or not name:
        return None
    cache_key = (base.lower(), name.lower())
    cached = _CAPABILITY_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    from quill.core.ai_chat import _post_json

    try:
        data = _post_json(
            f"{base}/api/show",
            {"model": name},
            {},
            int(timeout_seconds),
        )
    except Exception:  # noqa: BLE001 - best-effort: None means "unknown"
        return None
    caps = data.get("capabilities")
    if not isinstance(caps, list):
        # Older Ollama versions do not report capabilities. Treat as unknown so
        # the caller does not block a working vision model on a stale guess.
        return None
    normalized = [str(c).strip() for c in caps if isinstance(c, (str, int)) and str(c).strip()]
    _CAPABILITY_CACHE[cache_key] = list(normalized)
    return list(normalized)


def capability_badge(capabilities: Iterable[str] | None) -> str:
    """Return a short, human-facing capability label (pure).

    ``"Vision"``, ``"Tools"``, or ``"Vision + Tools"`` when either applies; an
    empty string for a plain completion model (the common case, so the display
    stays clean). ``None``/unknown yields an empty string -- the caller decides
    whether to show "unknown" separately.
    """
    if not capabilities:
        return ""
    lower = {str(c).strip().lower() for c in capabilities if str(c).strip()}
    parts: list[str] = []
    if "vision" in lower:
        parts.append("Vision")
    if "tools" in lower:
        parts.append("Tools")
    return " + ".join(parts)


def format_model_line(name: str, capabilities: Iterable[str] | None) -> str:
    """Return ``"llava:7b (Vision)"`` or the bare ``name`` when no badge applies (pure)."""
    badge = capability_badge(capabilities)
    return f"{name} ({badge})" if badge else str(name)


def capability_summary(
    model_ids: Iterable[str],
    capabilities_by_model: Mapping[str, Iterable[str] | None],
) -> str:
    """Build one speakable line listing each model with its capability badge (pure).

    Models with no badge (plain completion models) are listed by name only; the
    badge is appended only when it adds information. Example::

        "llava:7b (Vision), llama3.2:1b, qwen2.5:7b (Tools)"
    """
    parts: list[str] = []
    for name in model_ids:
        caps = capabilities_by_model.get(name)
        parts.append(format_model_line(name, caps))
    return ", ".join(parts)


def enrich_capabilities(
    host: str,
    model_ids: Iterable[str],
    *,
    timeout_seconds: float = _SHOW_TIMEOUT_S,
    max_models: int = 40,
) -> dict[str, list[str]]:
    """Fetch capabilities for each model id, returning ``{model_id: capabilities}``.

    Only models whose capabilities were successfully determined are included; a
    model absent from the result is "unknown" (caller should not infer text-only
    from absence). Sequential, best-effort, never raises. Capped at
    ``max_models`` so a very large local library does not stall the UI worker --
    beyond the cap, models are simply left unknown (the user can still pick them
    by name; the server will reject a bad choice with a surfaced error body).
    """
    base = (host or "").strip()
    if not base:
        return {}
    out: dict[str, list[str]] = {}
    seen = 0
    for name in model_ids:
        clean = (name or "").strip()
        if not clean:
            continue
        seen += 1
        if seen > max_models:
            break
        caps = fetch_model_capabilities(base, clean, timeout_seconds=timeout_seconds)
        if caps is not None:
            out[clean] = list(caps)
    return out


__all__ = [
    "fetch_model_capabilities",
    "capability_badge",
    "format_model_line",
    "capability_summary",
    "enrich_capabilities",
]
