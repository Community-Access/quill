"""Select the active AI transport for editor agent runs."""

from __future__ import annotations

from typing import Any

from quill.core.ai.harness.native import responder_from_backend


def select_responder(backend: Any, controller: Any) -> tuple[Any, str]:
    """Pick the produce-text transport for the user's chosen AI engine.

    Returns ``(responder, engine_name)``. Honors the engine selected via the
    quick switcher / AI Hub: an available SDK pack supplies its own transport;
    otherwise (Native, ``auto``, or an unavailable/failed pack) it falls back to
    the provider backend. When Native is required but the backend is unavailable,
    returns ``(None, reason)`` so the caller can report it. The returned callable
    has the same ``(AgentSpec, AIContext) -> str`` shape either way, so the run
    path's threading and gateway apply are unchanged.
    """
    from quill.core.ai.quick_switch import preferred_harness_id

    app_host = getattr(controller, "_ai_host", None)
    app_host = app_host() if callable(app_host) else None
    app_name = str(getattr(app_host, "ai_agent_name", "") or "QUILL")
    data_dir = getattr(app_host, "data_dir", None)
    preferred = preferred_harness_id(data_dir=data_dir)
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
                except Exception as exc:  # noqa: BLE001 - fall back, never crash
                    controller._set_status(
                        f"{pack.display_name} could not start ({exc}); using Native."
                    )
            else:
                controller._set_status(
                    f"{pack.display_name} is not set up; using Native. {reason or ''}".strip()
                )
    available, reason = backend.is_available()
    if not available:
        return None, reason or "AI provider is not available."
    return responder_from_backend(backend), f"Native ({app_name})"
