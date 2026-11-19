"""The GitHub Workbench's results, played and said by the shared feedback setting.

GH-R-113 and GH-R-083: :func:`quill.core.github.outcome_feedback.plan` decides,
this plays the tone through the sound manager and says the words through the
frame, which also keeps them for F9. A result said by tone alone (a bare
acknowledgement under "Play a sound") is still kept, so F9 can say it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["say_result"]


def say_result(frame: Any, announce: Callable[[str], None], text: str) -> None:
    """Play and say *text* as the person's action-feedback choice asks."""
    from quill.core.github.outcome_feedback import plan
    from quill.ui import sound_manager

    chosen = plan(
        text,
        sound_manager.action_feedback_mode(),
        has_sound=sound_manager.get_loaded_events(),
    )
    if chosen.sound:
        sound_manager.post_sound(chosen.sound)
    if frame is None:
        if chosen.speak:
            announce(text)
    elif chosen.speak:
        frame._say(text)
    else:
        frame.last_result = text
