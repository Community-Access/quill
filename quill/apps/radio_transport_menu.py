"""The Playback menu's two transport rows, and keeping their labels true.

**Radio's main window could not pause anything** (fixed 2026-08-25). The
Playback menu carried one transport row, Play/Stop on Ctrl+P, wired to
``_on_play_stop_button`` -- which *stops*. So pressing Ctrl+P in the main
window ended a recording, a downloaded file or a finished video where the same
key, in every other window of the app, paused it: ``transport.play_pause`` is
Ctrl+P too, and the shared transport keyboard installs it everywhere the main
window is not. One key, two meanings, decided by which window had focus.

The answer is the pair the rest of the app already wears (see
:mod:`quill.core.radio.transport_commands`): one row that starts and ends, one
row that pauses.

* **Play / Stop** keeps Ctrl+P and keeps its behaviour exactly. Moving it would
  change what Ctrl+P does for somebody who has been pressing it since 1.0, and
  a fix that rewrites muscle memory is not a fix.
* **Pause / Resume** is new, on Ctrl+Space -- what a media player has meant by
  pause for as long as there have been media players, and the last short chord
  this menu bar had free (Ctrl+Shift is exhausted; Ctrl+Alt has one letter
  left). Dimmed with a reason on a live station, because a live stream is
  going out now and there is nothing to hold.

Both labels are re-read from the same ``faces()`` call the player panel's
buttons and the tray menu use, so the three can never disagree about what is
playing. Extracted from ``radio.py``, which is on its GATE-11 ceiling and is
not improved by knowing how a menu row is relabelled.
"""

from __future__ import annotations

from typing import Any


def append_items(app: Any, playback_menu: Any, wx: Any) -> tuple[Any, Any]:
    """Append Play/Stop and Pause/Resume, adjacent. Returns their ids to pin.

    Adjacent on purpose: they are the two halves of one question, and a
    listener arrowing the Playback menu should meet them together rather than
    find pause eleven rows further down.
    """
    play_id, pause_id = wx.NewIdRef(), wx.NewIdRef()
    # Ctrl+P is spelled out rather than routed through _menu_label: this row
    # runs the app's own _on_play_stop_button, not the transport table's
    # play_pause verb, and labelling it with that verb's binding would promise
    # a key that does something else here.
    playback_menu.Append(play_id, "&Play\tCtrl+P")
    playback_menu.Append(pause_id, app._menu_label("Pau&se", "radio.pause"))
    app.frame.Bind(wx.EVT_MENU, lambda _e: app._on_play_stop_button(), id=play_id)
    app.frame.Bind(wx.EVT_MENU, lambda _e: _pause(app), id=pause_id)
    app._play_menu_item_id = play_id
    app._pause_menu_item_id = pause_id
    app._keep_menu_ids(play_id, pause_id)
    return play_id, pause_id


def _pause(app: Any) -> None:
    """Hold a recording where it is, or pick it up again -- and say which.

    Refuses out loud on a live station rather than silently doing nothing: a
    key that does nothing is indistinguishable from a key nobody bound, which
    is how the missing row went unreported in the first place.
    """
    from quill.core.radio import transport_commands as tc
    from quill.ui.radio import transport_face

    _primary, pause = transport_face.faces(app)
    if not pause.enabled:
        app._announce(f"{pause.plain}: {pause.reason}.")
        return
    resuming = pause.command_id == tc.PLAY_PAUSE and pause.plain == "Resume"
    app.radio_toggle_play_pause()
    app._announce("Resumed." if resuming else "Paused.")


def refresh_labels(app: Any) -> None:
    """Put the current faces on both rows. Never raises; no-op before build.

    ``SetLabel`` on a menu bar item is how the Play row has always followed the
    player; the Pause row follows the same way rather than growing a second
    mechanism.
    """
    from quill.ui.radio import transport_face

    menu_bar = app.frame.GetMenuBar()
    if menu_bar is None:
        return
    primary, pause = transport_face.faces(app)
    play_id = getattr(app, "_play_menu_item_id", None)
    if play_id is not None:
        # The menu keeps its own mnemonic (&Play / &Stop): the panel's button
        # takes Alt+P, and on a frame a button mnemonic and a menu-bar one
        # compete (#1208).
        menu_bar.SetLabel(int(play_id), f"&{primary.plain}\tCtrl+P")
    pause_id = getattr(app, "_pause_menu_item_id", None)
    if pause_id is not None:
        menu_bar.SetLabel(int(pause_id), app._menu_label(pause.label, "radio.pause"))
        menu_bar.Enable(int(pause_id), pause.enabled)


__all__ = ["append_items", "refresh_labels"]
