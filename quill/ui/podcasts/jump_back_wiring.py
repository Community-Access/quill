"""Back to Where I Was in QUILL Cast (FUX-01).

Go to Position and Next / Previous Chapter note the place they leave
(:class:`~quill.core.media.jump_back.JumpBack`); **Back to Where I Was**
(Alt+Left, the family's Go Back key) returns to it, and pressing it again
returns to where you went back from. One place per playing episode: starting
another episode forgets it.

Before this, a jump was one-way, and the 15-second checkpoint wrote the new
time over the old one within a poll, so even the saved place could not help.
"""

from __future__ import annotations

from typing import Any

from quill.core.media.jump_back import NOTHING_TO_GO_BACK_TO, JumpBack, back_sentence

__all__ = ["back_to_where_i_was", "note_jump"]


def _item(controller: Any) -> str:
    state = controller.state
    if not state.show_id or not state.episode_guid:
        return ""
    return f"{state.show_id}|{state.episode_guid}"


def _jumps(host: Any) -> JumpBack:
    jumps = getattr(host, "_podcast_jump_back", None)
    if jumps is None:
        jumps = JumpBack()
        host._podcast_jump_back = jumps
    return jumps


def note_jump(host: Any, target_ms: int) -> None:
    """Remember where the playing episode is, before a jump to *target_ms*."""
    controller = getattr(host, "_podcast_controller", None)
    if controller is None:
        return
    _jumps(host).before_jump(_item(controller), int(controller.position_ms()), target_ms)


def back_to_where_i_was(host: Any) -> None:
    """Return to the place before the last jump, and say where, once."""
    controller = getattr(host, "_podcast_controller", None)
    item = _item(controller) if controller is not None else ""
    if not item:
        host._announce("Nothing is playing.")
        return
    if getattr(controller.state.state, "name", "") == "LOADING":
        host._announce("Still loading.")  # the place is kept for when it has
        return
    target = _jumps(host).back(item, int(controller.position_ms()))
    if target is None:
        host._announce(NOTHING_TO_GO_BACK_TO)
        return
    controller.seek(target)
    host._announce(back_sentence(target))
