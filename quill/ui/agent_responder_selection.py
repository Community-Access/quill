"""Select the active AI transport for editor agent runs."""

from __future__ import annotations

import logging
from typing import Any

from quill.core.ai.harness.native import responder_from_backend

logger = logging.getLogger(__name__)

#: The caption of the question asked before an agent run falls back to Native.
FALL_BACK_CAPTION = "Use a Different AI?"


def _native_receiver(backend: Any) -> tuple[str, str, bool]:
    """Native's provider as heard, who receives the text, and whether it stays here."""
    from quill.core.ai.own_key_providers import COMPANIES, PROVIDER_NAMES, is_local

    settings = getattr(backend, "settings", None)
    provider = str(getattr(settings, "provider", "") or "").strip().lower()
    name = PROVIDER_NAMES.get(provider, "your AI provider")
    return name, COMPANIES.get(provider, name), is_local(provider)


def _fall_back_allowed(pack_name: str, problem: str, backend: Any, controller: Any) -> bool:
    """Say, or ask, before Native answers in place of *pack_name* (2026-11 audit, gap 6).

    Native may be a different company from the engine the person chose, so the
    text goes nowhere until they say Yes, No being the default. Native on this
    computer sends nothing, so that is said and not asked.
    """
    name, company, local = _native_receiver(backend)
    if local:
        controller._set_status(
            f"{pack_name} {problem}. Using {name} instead. Nothing leaves this computer."
        )
        return True
    import wx

    question = (
        f"{pack_name} {problem}. Use {name} instead? Your text would go to "
        f"{company} over the internet. Choose No and nothing is sent."
    )
    ask = getattr(controller, "_show_message_box", None)
    if not callable(ask):
        return False
    answer = ask(question, FALL_BACK_CAPTION, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
    return answer in (wx.YES, wx.ID_YES)


def select_responder(backend: Any, controller: Any) -> tuple[Any, str]:
    """Pick the produce-text transport for the user's chosen AI engine.

    Returns ``(responder, engine_name)``. Honors the engine selected via the
    quick switcher / AI Hub: an available SDK pack supplies its own transport;
    otherwise (Native, ``auto``, or an unavailable/failed pack) it falls back to
    the provider backend -- after asking, when that is a cloud provider the
    person did not pick. When Native is required but the backend is unavailable,
    or the person said No, returns ``(None, reason)`` so the caller can report
    it. The returned callable has the same ``(AgentSpec, AIContext) -> str``
    shape either way, so the run path's threading and gateway apply are unchanged.
    """
    from quill.core.ai.quick_switch import preferred_harness_id

    app_host = getattr(controller, "_ai_host", None)
    app_host = app_host() if callable(app_host) else None
    app_name = str(getattr(app_host, "ai_agent_name", "") or "QUILL")
    data_dir = getattr(app_host, "data_dir", None)
    preferred = preferred_harness_id(data_dir=data_dir)
    fell_from: tuple[str, str] | None = None
    if preferred not in ("auto", "native"):
        from quill.ai_packs import all_packs

        pack = next(
            (p for p in all_packs(agent_name=app_name, data_dir=data_dir) if p.id == preferred),
            None,
        )
        if pack is not None:
            ok, reason = pack.is_available()
            if ok:
                try:
                    return pack.responder(), pack.display_name
                except Exception:  # noqa: BLE001 - fall back, never crash
                    # The error goes to the log, not into speech and braille.
                    logger.warning("%s could not start", pack.display_name, exc_info=True)
                    fell_from = (pack.display_name, "could not start")
            else:
                logger.info("%s is not set up: %s", pack.display_name, reason)
                fell_from = (pack.display_name, "is not set up")
    available, reason = backend.is_available()
    if not available:
        return None, reason or "AI provider is not available."
    if fell_from is not None and not _fall_back_allowed(*fell_from, backend, controller):
        return None, f"{fell_from[0]} {fell_from[1]}. Nothing was sent."
    return responder_from_backend(backend), f"Native ({app_name})"
