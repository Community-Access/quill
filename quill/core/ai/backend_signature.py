"""What the default AI backend is decided from, read cheaply (2026-11 audit, gap 1).

A window that keeps an :class:`~quill.core.ai.assistant.Assistant` compares
:func:`default_backend_signature` before each use and builds a new one when it
changed, so a provider switch, or a key signed out, reaches every feature at
once instead of at the next restart. wx-free and strict-typed.
"""

from __future__ import annotations

__all__ = ["default_backend_signature"]


def default_backend_signature() -> tuple[str, ...]:
    """What :func:`make_default_backend` would decide from, read cheaply.

    A caller that keeps an :class:`Assistant` compares this before each use and
    builds a new one when it changed, so a provider switch, or a key signed out,
    reaches every feature at once instead of at the next restart (2026-11
    audit, gap 1). Only whether a key is there is compared, never the key itself.
    """
    parts: list[str] = []
    try:
        from quill.core.assistant_ai import (
            assistant_connection_path,
            load_assistant_connection_settings,
        )

        if assistant_connection_path().exists():
            from quill.core.ai.provider_backend import provider_api_key

            conn = load_assistant_connection_settings()
            has_key = "key" if provider_api_key(conn.provider) else "no key"
            parts += [conn.provider, conn.host, conn.model, has_key]
    except Exception:  # noqa: BLE001 - unreadable means "rebuild", never a crash
        parts.append("unreadable")
    try:
        from quill.core.settings import load_settings

        chat = load_settings()
        parts += [
            str(getattr(chat, "ai_chat_default_provider", "") or ""),
            str(getattr(chat, "ai_prompt_default_model", "") or ""),
            str(getattr(chat, "ai_chat_default_model", "") or ""),
        ]
    except Exception:  # noqa: BLE001
        parts.append("unreadable")
    return tuple(parts)
