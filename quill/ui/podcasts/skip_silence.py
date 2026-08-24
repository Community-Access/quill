"""Skip Silence from the transport, in QUILL Cast (11.7).

Cast has had this as **Smart Speed**, a per-show setting in Podcast Settings.
What it did not have was a way to reach it *while listening*, which is the
only moment anybody forms an opinion about it -- and Quill Radio gained the
same verb on the same key (Ctrl+Shift+9), so the two players answer it alike.

Same scope as the speed commands: the playing show's own override when
something is playing, otherwise the shared default. Heard immediately -- the
filter is part of the graph the player already renders, and the controller
reloads at the current position rather than from the top, because somebody
forty minutes in must not be sent back to the beginning to get it.

Extracted from ``main_frame_podcast_session.py`` under GATE-11.
"""

from __future__ import annotations

from typing import Any


def toggle_skip_silence(host: Any) -> None:
    """Turn Skip Silence on or off for whatever scope is in force, and say so."""
    show, settings = host._podcast_speed_context()
    wanted = not bool(settings.smart_speed_enabled)
    if show is not None:
        host._podcast_library.apply_show_override(show, smart_speed_enabled=wanted)
        target = show.title
    else:
        host._podcast_library.settings.smart_speed_enabled = wanted
        target = "every podcast"
    host._save_podcast_library()
    controller = getattr(host, "_podcast_controller", None)
    if controller is not None and controller.state.show_id is not None:
        apply_now = getattr(controller, "set_smart_speed", None)
        if callable(apply_now):
            apply_now(wanted)
    host._announce(
        f"Skip Silence on for {target}. Long pauses are shortened as this plays."
        if wanted
        else f"Skip Silence off for {target}. Pauses play at their full length again."
    )
