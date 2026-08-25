"""What the two transport controls read right now, in both apps.

**One control that starts and ends, one that pauses** (2026-08-25). Every
surface in Quill Radio and QUILL Cast used to carry Play/Pause *and* Stop side
by side, and on a live station one of the pair was always a lie: a live stream
cannot be paused, so Play/Pause meant Play/Restart and Stop was the only
control that ended anything. The ACB Media Schedule window had already settled
it the right way -- one button that says Play, then says Stop -- and this is
that rule generalised to the content the schedule window does not have:
podcasts, recordings, downloaded and local files, finished videos.

The wording and the dimming rules are pure and live in
:mod:`quill.core.radio.transport_commands` (``primary_face``/``pause_face``).
What lives here is the part that needs the *player*: reading the phase out of
two differently-shaped playback states, and rendering the pair into a wx menu.

Split out of :mod:`quill.ui.radio.transport_keys` under GATE-11, and it is a
real seam either way: that module answers "may this verb run, and what runs
it", this one answers "what should the control say".
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import transport_commands as tc


def state(host: Any) -> tuple[bool, bool, bool]:
    """``(playing, bounded, paused)`` -- what the transport controls read.

    Narrower than :func:`quill.ui.radio.transport_keys._state`, deliberately.
    That one answers "may this verb run" and is generous on purpose: a paused
    episode counts as playing there so Stop and seek are not refused. A *label*
    cannot be generous -- a button reading Stop while nothing is on is the bug
    the single-control rule exists to fix -- so this asks what phase the player
    is actually in.

    Both dialects, as everywhere in this corner: Radio's ``RadioPlayerState``
    and Quill Cast's episode phase. Never raises; an unreadable player is
    "nothing is playing", which dims rather than lies.
    """
    from quill.ui.radio import transport_keys

    controller = transport_keys._controller_of(host)
    if controller is None:
        return False, False, False
    try:
        snapshot = controller.state
    except Exception:  # noqa: BLE001 - a probe must never crash a refresh
        return False, False, False
    if hasattr(snapshot, "episode_guid"):
        # Quill Cast. An episode is always bounded -- it is a file with a
        # length -- and its phase is an enum of Cast's own, so the name is the
        # only thing this module may read off it.
        name = str(getattr(getattr(snapshot, "state", None), "name", "") or "")
        if not str(getattr(snapshot, "title", "") or "") or name in {"STOPPED", "ERROR"}:
            return False, False, False
        return name != "PAUSED", True, name == "PAUSED"
    # Quill Radio. Bounded means a *recording* -- a downloaded or local file
    # with a length -- as against a live stream, which has none of the three
    # things bounded playback is for.
    from quill.ui.radio.playback_state import ACTIVE_STATES, RadioPlayerState

    station = getattr(snapshot, "station", None)
    if station is None:
        return False, False, False
    phase = getattr(snapshot, "state", None)
    paused = phase is RadioPlayerState.PAUSED
    playing = phase in ACTIVE_STATES
    if not playing and not paused:
        return False, False, False
    return playing, bool(getattr(station, "is_recording", False)), paused


def faces(host: Any) -> tuple[tc.TransportFace, tc.TransportFace]:
    """``(primary, pause)`` for *host*'s player, as one reading of one state.

    One call rather than two so the pair can never be resolved from two
    different moments -- a Stop button beside a Pause button that still thinks
    nothing is playing is the same class of disagreement this whole corner of
    the app exists to prevent.
    """
    playing, bounded, paused = state(host)
    return (
        tc.primary_face(playing=playing, paused=paused),
        tc.pause_face(playing=playing, bounded=bounded, paused=paused),
    )


def append_menu_rows(host: Any, menu: Any, wx: Any) -> tuple[Any, Any]:
    """Append the Play/Stop and Pause/Resume rows. Returns their ids to pin.

    For menus rebuilt on every popup (the status bar's, the tray's), so the
    labels are always current without a refresh hook. Pause is appended dimmed
    rather than skipped on live radio: a row that comes and goes moves every
    row under it in a list somebody arrows through.
    """
    primary, pause = faces(host)
    play_id, pause_id = wx.NewIdRef(), wx.NewIdRef()
    menu.Append(play_id, primary.plain)
    menu.Append(pause_id, pause.plain)
    menu.Enable(pause_id, pause.enabled)
    menu.Bind(wx.EVT_MENU, lambda _e: host.radio_play_stop_toggle(), id=play_id)
    menu.Bind(wx.EVT_MENU, lambda _e: host.radio_toggle_play_pause(), id=pause_id)
    return play_id, pause_id


__all__ = ["append_menu_rows", "faces", "state"]
