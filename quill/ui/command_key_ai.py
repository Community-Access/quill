"""Tier 4 for the Command Key: one question to the AI chosen in Choose Your AI.

command-key.md 7.10. When the person answered the consent question "Use My Own
AI Instead", or Jev cannot answer (offline, its limit, its credit), a sentence
the matcher on the computer could not settle is put to the AI they chose --
their ChatGPT plan, GitHub Copilot, Codex or their own key -- as one question:
"reply with one id from this list, or none". :class:`CommandPickAssist`
(``quill/core/command_catalogue/assist.py``) checks the answer against the
list, acts only when it agrees with the matcher's best guess and the command
is SAFE, and otherwise asks "Did you mean".

**Not on the free AI.** QUILL's free AI has no template for this question,
and a person on it who said yes to Jev already has the gateway route; tier 4
there would spend their free allowance on a lookup. :func:`command_pick_engine`
answers None for it, and the matcher's answer stands.

**A short deadline.** The Command Key decides while its box is closing, on the
UI thread, so the question gets :data:`DEADLINE_SECONDS` and no more; a slow
answer is a failure (logged, coded), and the matcher's answer stands. "Asking
your AI." is said first, so the wait is never silent. The request goes through
``AiService.ask`` like every other one, which answers with ``wx.CallAfter``;
while waiting, :func:`wx.SafeYield` delivers that answer and keeps every window
disabled, so nothing typed during the wait lands anywhere.

**The same gates as every AI request.** ``AiService.ask`` runs Safe Mode, the
agreement, the capability check (``requires=("text",)``, GATE-CAPS) and the
route-changed question before anything leaves.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from quill.core.command_catalogue.assist import CommandPickFailed

__all__ = ["DEADLINE_SECONDS", "FEATURE", "WORKING_LINE", "command_pick_engine"]

#: The own-key instruction row this question uses (``own_key.INSTRUCTIONS``).
FEATURE = "command_pick"
DEADLINE_SECONDS = 8.0
WORKING_LINE = "Asking your AI."


def _service_of(owner: Any) -> Any:
    """The app's AI service, or None when the app has none or cannot make one."""
    make = getattr(owner, "_ai_service", None)
    if not callable(make):
        return None
    try:
        return make()
    except Exception:  # noqa: BLE001 - an app whose AI cannot start has no tier 4
        return None


def command_pick_engine(
    owner: Any,
    announce: Callable[[str], None],
    *,
    deadline: float = DEADLINE_SECONDS,
) -> Callable[[str], str] | None:
    """``ask(prompt) -> reply`` on the connection in use, or None when there is none to ask."""
    from quill.core.ai.connection_caps import FREE

    if os.environ.get("QUILL_SAFE_MODE") == "1":
        return None
    service = _service_of(owner)
    if service is None:
        return None
    try:
        connection = str(service.connection_in_use or "")
    except Exception:  # noqa: BLE001 - a service that cannot say is not ready
        return None
    if not connection or connection == FREE:
        return None

    def ask(prompt: str) -> str:
        box: dict[str, Any] = {}
        announce(WORKING_LINE)
        request = service.ask(
            FEATURE,
            prompt,
            None,
            on_done=lambda text, _quota: box.setdefault("answer", str(text or "")),
            on_error=lambda sentence: box.setdefault("error", sentence),
            requires=("text",),
        )
        until = time.monotonic() + deadline
        while not box and time.monotonic() < until:
            import wx  # only when the answer is not already back

            wx.SafeYield(None, True)
            time.sleep(0.02)
        if not box:
            service.cancel(request)
            raise CommandPickFailed(f"The AI took longer than {deadline:g} seconds.")
        if "error" in box:
            raise CommandPickFailed(str(box["error"]))
        return str(box["answer"])

    return ask
