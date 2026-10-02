"""Where each AI provider's chat request goes (pure; no network).

Extracted from ``quill/core/assistant_ai.py`` under GATE-11 on 2026-10-01, when
:func:`gemini_model_id` arrived and that module sat at its budget. The URL
builders are one subject -- given a provider, a host and a model, which address
-- and nothing here sends anything. ``assistant_ai`` re-exports all three, so
every existing import keeps working.

wx-free, strict-typed.
"""

from __future__ import annotations

from urllib.parse import quote

__all__ = ["chat_endpoint", "gemini_model_id", "stream_chat_endpoint"]


def gemini_model_id(model: str) -> str:
    """*model* without the ``models/`` prefix Gemini's own listing gives it.

    ``GET /v1beta/models`` answers ``"name": "models/gemini-2.5-flash"``, and a
    name taken from that list and put into ``/v1beta/models/{model}:...`` made
    ``/v1beta/models/models/gemini-2.5-flash``, which Gemini answers with 404 --
    so a model chosen from QUILL's own list could not be used (PR #1615,
    reviewed into this change; qc.md X-07). Stripped once, here, and used by
    every Gemini URL builder and by the model list, so a stored name with the
    prefix and one without reach the same endpoint.
    """
    cleaned = (model or "").strip()
    return cleaned.removeprefix("models/")


def chat_endpoint(provider: str, host: str, model: str) -> str:
    """Return the chat endpoint URL for a provider (pure; no network)."""
    normalized = provider.strip().lower()
    host = host.rstrip("/")
    if normalized == "claude":
        return f"{host}/v1/messages"
    if normalized == "gemini":
        return f"{host}/v1beta/models/{quote(gemini_model_id(model))}:generateContent"
    if normalized == "ollama":
        return f"{host}/api/chat"
    return f"{host}/v1/chat/completions"


def stream_chat_endpoint(provider: str, host: str, model: str) -> str:
    """Return the streaming chat endpoint URL for a provider (pure; no network).

    Identical to :func:`chat_endpoint` except for Gemini, which uses a distinct
    ``:streamGenerateContent`` method with ``alt=sse`` so it returns Server-Sent
    Events instead of one buffered JSON array.
    """
    normalized = provider.strip().lower()
    if normalized == "gemini":
        host = host.rstrip("/")
        return f"{host}/v1beta/models/{quote(gemini_model_id(model))}:streamGenerateContent?alt=sse"
    return chat_endpoint(provider, host, model)
