"""Go to Position in QUILL Cast: type a time and land there (11.8).

Cast could already do this, from a Winamp letter key -- which means it
existed for whoever had those keys on and knew about them, and for nobody
else. It is a menu item and a palette command now, over the same dialog Quill
Radio opens and the one parser both players share: labelled Hours / Minutes /
Seconds spin controls as the primary input, an optional timecode field for
people who would rather type, OK as the default button.

Scrubbing by keystroke is fine for seconds and useless for "the bit forty
minutes in".

Extracted from ``main_frame_podcast_session.py`` under GATE-11.
"""

from __future__ import annotations

from typing import Any


def go_to_position(host: Any) -> None:
    """Type a position and land there -- 1:02:03, 62:03, or 3723 (11.8).

    The same Go to Position dialog Quill Radio opens: labelled Hours /
    Minutes / Seconds spin controls as the primary input, an optional
    timecode field for people who would rather type, OK as the default
    button, and one tested parser behind both. Cast could already do this
    from a Winamp letter key, which means it existed for whoever had
    those keys on and knew about them, and for nobody else -- so it is a
    menu item and a palette command now.

    Scrubbing by keystroke is fine for seconds and useless for "the bit
    forty minutes in".
    """
    import wx

    from quill.ui.dialog_contract import show_modal_dialog
    from quill.ui.media.go_to_position_dialog import GoToPositionDialog

    controller = getattr(host, "_podcast_controller", None)
    if controller is None or controller.state.show_id is None:
        host._announce("Nothing is playing to jump within.")
        return
    length = int(controller.length_ms())
    if length <= 0:
        host._announce("This episode has no known length yet, so there is nothing to jump within.")
        return
    dialog = GoToPositionDialog(
        host.frame,
        duration_ms=length,
        current_ms=int(controller.position_ms()),
        announce=host._announce,
    )
    try:
        if show_modal_dialog(dialog, "Go to Position", announce=host._announce) != wx.ID_OK:
            return
        target = dialog.get_target_ms()
        clamped = dialog.clamped_message()
    finally:
        dialog.Destroy()
    controller.seek(target)
    from quill.core.media.timecode import format_spoken

    host._announce(clamped or f"At {format_spoken(target)}.")
