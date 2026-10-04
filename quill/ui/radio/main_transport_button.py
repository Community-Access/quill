"""The main window's one transport button: Play <station>, Stop <station>, Resume.

Jeff, 2026-10-01: "The stop button now always shows up in the app and doesn't
change to a play button when stopped. Should that happen or should it change to
play?"

It should. Stop came back to this row in 3.0.3 as a static button, because
stopping is the one action every listener needs at once without knowing a key
-- and a static Stop is a dead control the moment nothing is playing: enabled,
labelled with a verb that cannot happen, and silent about the verb that could.
So the button is the main window's primary transport face, the contract the
quality plan sets for both players (qc.md, "Radio and Cast Transport State"):

* **stopped** -- ``Play <the selected favorite>``; or, with a folder or nothing
  under the cursor, ``Play -- nothing selected``, and pressing it says what
  would work instead;
* **active** (connecting, buffering, playing, reconnecting) -- ``Stop <what is
  playing>``; live radio cannot pause, and this window is a list you play
  from, not a player, so the one button starts and ends;
* **paused** (a podcast, a recording, a local file) -- ``Resume <it>``, and
  Ctrl+Period or Station > Stop still ends it.

**The object is in the label.** On wxMSW a button is self-labelled and
``set_accessible_name`` is inert on it, so the station's name can only be heard
if it is in the label (:mod:`quill.core.transport_button`, which also elides it
so the row never reflows). The button is given a minimum width that fits the
longest label it can show, so Volume and Mute after it stay where they are.

Built here rather than in ``quill/apps/radio.py`` (at its GATE-11 budget), with
its F1 sentence inline at the construction site, where the help audit reads it.
"""

from __future__ import annotations

from typing import Any

from quill.core import transport_button as tb

__all__ = ["add_transport_button", "current_face", "press", "refresh"]

#: What the dead state tells a listener to do. Both routes are in this window.
_DEAD_HINT = "choose a station in Favorites first, or press Ctrl+B to browse for one"


def _phase(host: Any) -> str:
    """STOPPED, PLAYING or PAUSED, from the radio player. Never raises."""
    from quill.ui.radio.playback_state import ACTIVE_STATES, RadioPlayerState

    controller = getattr(host, "_radio_controller", None)
    try:
        state = controller.state.state
    except Exception:  # noqa: BLE001 - an unreadable player is "nothing is playing"
        return tb.STOPPED
    if state in ACTIVE_STATES:
        return tb.PLAYING
    if state is RadioPlayerState.PAUSED:
        return tb.PAUSED
    return tb.STOPPED


def _playing_name(host: Any) -> str:
    """What the player holds, by the name the listener gave it if they gave one."""
    controller = getattr(host, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None:
        return ""
    favorites = getattr(host, "_radio_favorites", None)
    key = str(getattr(station, "station_uuid", "") or getattr(station, "stream_url", "") or "")
    find = getattr(favorites, "find", None)
    favorite = find(key) if callable(find) and key else None
    if favorite is not None:
        return str(getattr(favorite, "display_label", "") or "")
    return str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")


def _selection(host: Any) -> tuple[str, bool]:
    """``(what the favorites cursor is on, whether Play would start it)``."""
    pick = getattr(host, "_selected_favorite", None)
    favorite = pick() if callable(pick) else None
    if favorite is None:
        return ("", False)
    return (str(getattr(favorite, "display_label", "") or ""), True)


def current_face(host: Any) -> tb.ButtonFace:
    """Label, sentence and verb for the button, as one reading of one state."""
    phase = _phase(host)
    selection, playable = _selection(host)
    return tb.face(
        phase,
        active_verb="stop",
        object_name=_playing_name(host) if phase != tb.STOPPED else "",
        selection=selection,
        can_play_selection=playable,
        mnemonics=tb.RADIO_MNEMONICS,
        dead_hint=_DEAD_HINT,
    )


def refresh(host: Any) -> None:
    """Put the current face on the button. Never raises; no-op before build."""
    button = getattr(host, "_transport_btn", None)
    if button is None:
        return
    try:
        label = current_face(host).label
        if button.GetLabel() != label:
            button.SetLabel(label)
    except Exception:  # noqa: BLE001 - a stale label is not worth a crash
        pass


def press(host: Any) -> None:
    """Do what the button says. Also what Ctrl+P and Playback > Play/Stop run."""
    face = current_face(host)
    if face.verb == "stop":
        host.radio_stop()
    elif face.verb == "resume":
        host.radio_toggle_play_pause()
    elif face.verb == "play":
        host._play_selected_favorite()
    else:
        host._announce(face.spoken)


def add_transport_button(host: Any, panel: Any, row: Any, wx: Any) -> Any:
    """Add the button to *row*, first, and return it."""
    button = wx.Button(panel, label=current_face(host).label)
    button.SetHelpText(
        "Plays the favorite selected in the list, stops whatever is playing, or "
        "resumes a paused podcast or recording. The label names which, and what. "
        "Ctrl+P does the same from anywhere; Ctrl+Period always stops."
    )
    button.Bind(wx.EVT_BUTTON, lambda _e: press(host))
    try:
        # Wide enough for the longest label it can show, so the controls after
        # it do not move when the selection or the player changes.
        widest = tb.object_label(tb.RADIO_MNEMONICS.resume, "W" * tb.MAX_LABEL_CHARS)
        width = button.GetTextExtent(widest.replace("&", ""))[0] + 24
        button.SetMinSize((width, -1))
    except Exception:  # noqa: BLE001 - a fake wx has no text extents
        pass
    row.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    host._transport_btn = button
    # The station's website comes next in Tab order, beside Play and Stop (a
    # listener's request, October 2026: Double Tap Live's schedule lives there).
    from quill.ui.radio.station_website_button import add_website_button

    add_website_button(host, panel, row, wx)
    tree = getattr(host, "_favorites_tree", None)
    if tree is not None:
        # The label names the selection, so it follows the selection.
        tree.Bind(wx.EVT_TREE_SEL_CHANGED, lambda e: (refresh(host), e.Skip()))
    return button
