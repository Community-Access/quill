"""The chosen AI, as the Picture Maker and Visual Review reach it (wordpress.md 6.9, 6.11, 10).

Pictures go through the host's ``ai_describe_image`` (Ask About an Image's
route and gates, :mod:`quill.ui.wordpress_media_host`). The two things that
route does not cover live here, on the same editor object
(``host.ai_editor()``, the one carrying ``HostedAiMixin``): a text request to
the chosen AI -- Suggest from Page Content -- and which own key, if any, would
make a picture. Nothing new is invented: Choose Your AI decides, its
agreement applies, and every gate that stops says why itself.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

NO_AI_HERE = "AI help is not available in this window."


def editor_of(host: Any) -> Any:
    """The editor's AI side, or None when this host has none."""
    ai_editor = getattr(host, "ai_editor", None)
    return ai_editor() if callable(ai_editor) else None


def switched_on(ai: Any, announce: Callable[[str], None]) -> bool:
    """The AI area is on and the editor is not in Safe Mode; says why not otherwise."""
    if ai is None:
        announce(NO_AI_HERE)
        return False
    safe_mode = getattr(ai, "_ai_safe_mode", None)
    if callable(safe_mode) and safe_mode():
        announce("QUILL is in Safe Mode, so AI is off and nothing was sent.")
        return False
    gate = getattr(ai, "_ai_switched_on", None)
    return bool(gate()) if callable(gate) else True


def own_key_provider(ai: Any) -> str:
    """The provider of the own key in use, or "" when no own key is the connection in use."""
    service_of = getattr(ai, "_ai_service", None)
    if not callable(service_of):
        return ""
    service = service_of()
    if not getattr(service, "own_key_active", False):
        return ""
    return str(getattr(service, "own_key_provider", "") or "")


def ask_text(
    ai: Any,
    prompt: str,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> bool:
    """Send *prompt* to the chosen AI as one fresh turn. False: nothing was sent.

    The same gates as the rest of the AI menu, in the same order: the area is
    on and the agreement accepted (``_ai_ready``), and the connection in use
    does text. Each says why itself when it stops.
    """
    ready = getattr(ai, "_ai_ready", None)
    service_of = getattr(ai, "_ai_service", None)
    if not callable(ready) or not callable(service_of):
        on_error(NO_AI_HERE)
        return False
    if not ready():
        return False
    capable = getattr(ai, "_ai_capable", None)
    if callable(capable) and not capable("text"):
        return False
    service_of().converse(
        prompt,
        None,
        [],
        on_done=lambda text, _quota, _dropped: on_done(str(text)),
        on_error=on_error,
    )
    return True
