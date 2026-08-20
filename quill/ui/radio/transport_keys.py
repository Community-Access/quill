"""Install the transport keys on any window, so the player follows you.

The complaint this exists to answer: *"we need one player and it needs to react
accordingly with global keystrokes throughout the app so that all things can be
done quickly and easily for both Radio and Cast"* (2026-08-18) -- global
meaning **inside the app**, on every one of its windows, not taken away from
the rest of Windows.

There was already one player. What there was not was one keyboard: speed, skip
and chapters were menu items on the main frame, and a menu accelerator only
fires for the frame that owns the menu bar. Standing in Browse Stations, half
the transport did not exist.

:func:`install` fixes that for a window in one line. It builds a
``wx.AcceleratorTable`` from :data:`quill.core.radio.transport_commands.COMMANDS`
-- the same rows the menus render -- and binds each entry to a dispatcher that
finds the verb at the moment the key is pressed. So a window gains the whole
transport without importing the player, learning what a chapter is, or growing
a handler per verb.

**A key that cannot act says why.** Speed Up on a live station answers "this is
live radio, which plays at broadcast speed" rather than doing nothing, because
a silent key is indistinguishable from an unbound one -- and this window is
precisely where somebody would conclude the feature is broken.

**A key wx cannot parse is dropped loudly.** ``wx.AcceleratorEntry`` silently
ignores what it cannot understand (``Ctrl+Shift+Plus`` is the known one), which
leaves a menu advertising a key that does nothing; entries that fail to parse
are skipped here and reported to the caller so a test can fail on them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import transport_commands


def _accelerator(wx: Any, key: str, command_id: int) -> Any:
    """One parsed accelerator entry, or ``None`` when wx cannot read *key*."""
    entry = wx.AcceleratorEntry(cmd=command_id)
    try:
        if not entry.FromString(f"\t{key}"):
            return None
    except Exception:  # noqa: BLE001 - an unparsable key is a skipped key
        return None
    return entry if entry.GetKeyCode() else None


def unparsable_keys(wx: Any) -> list[str]:
    """Every command key this build of wx would silently drop.

    Exposed for the accelerator gate: a key nobody can press is worse than no
    key at all, because the menu still advertises it.
    """
    bad = []
    for command in transport_commands.COMMANDS:
        if _accelerator(wx, command.key, wx.ID_ANY if hasattr(wx, "ID_ANY") else 0) is None:
            bad.append(command.key)
    return bad


def install(
    window: Any, host: Any, *, wx: Any = None, after: Callable[[], None] | None = None
) -> int:
    """Give *window* the whole transport keyboard. Returns how many keys landed.

    *host* is whatever knows about the player -- the app frame, or a dialog
    that carries a controller. It is asked for the verb only when a key is
    actually pressed, so a window can be given the transport before its player
    exists.

    *after* runs once a key has been dispatched, acted or refused. It exists for
    a surface that *displays* the player as well as driving it: the player panel
    re-reads its status line, exactly as it does when one of its buttons is
    pressed, so a key and a button leave the panel saying the same thing.

    The existing accelerator table is *replaced*, not merged: wx has no
    "append", and every window that calls this either has no table of its own
    or has one built from these same rows.
    """
    if wx is None:
        import wx as wx_module

        wx = wx_module
    entries = []
    for command in transport_commands.COMMANDS:
        command_id = wx.NewIdRef()
        entry = _accelerator(wx, command.key, int(command_id))
        if entry is None:
            continue
        entries.append(entry)
        window.Bind(
            wx.EVT_MENU,
            lambda _event, cid=command.id: _fire(host, cid, after),
            id=int(command_id),
        )
        # wx frees an unreferenced NewIdRef, and a freed id is an accelerator
        # that fires nothing. Pin them to the window, as the browse tree's
        # context menu pins its own.
        refs = getattr(window, "_transport_id_refs", None)
        if refs is None:
            refs = window._transport_id_refs = []
        refs.append(command_id)
    window.SetAcceleratorTable(wx.AcceleratorTable(entries))
    return len(entries)


def _fire(host: Any, command_id: str, after: Callable[[], None] | None) -> bool:
    """One key press: run the verb, then let the window that showed it catch up.

    *after* runs even when the verb refused. A refusal changes nothing, so the
    readout it triggers is a no-op by design -- and making it conditional would
    mean the one case where the state changed *outside* this press never
    refreshed.
    """
    acted = perform(host, command_id)
    if after is not None:
        after()
    return acted


#: Names an app may already have registered a transport verb under, beyond the
#: obvious ones. Only the handful that genuinely differ; everything else is
#: matched by the command id's own last segment or by its verb.
_VERB_ALIASES: dict[str, tuple[str, ...]] = {
    "transport.mute": ("mute_toggle",),
    "transport.play_pause": ("toggle_play_pause",),
    "transport.speed_reset": ("reset_speed",),
    "transport.speed_down": ("slow_down",),
}


def _existing_names(command: Any) -> set[str]:
    """Every short name an app might already have this verb registered under."""
    return {
        command.id.rpartition(".")[2],
        command.verb,
        *_VERB_ALIASES.get(command.id, ()),
    }


def register_commands(host: Any, *, prefix: str) -> int:
    """Put every transport verb in the app's command palette. Returns the count.

    The palette could open a dialog and change a setting, and could not pause
    what was playing -- the transport lived on menus and keys only, so the one
    surface built for "do a thing by name" was the one surface that could not
    do the thing people do most.

    Each command runs through :func:`perform`, so a palette entry, a keystroke,
    a menu item and a button are four doors into one implementation -- refusals
    included. *prefix* namespaces the ids per app ("radio", "podcasts"), since
    each app has its own registry and the ids are stored against rebindings.
    """
    registry = getattr(host, "commands", None)
    if registry is None:
        return 0
    existing = set(getattr(registry, "_commands", {}) or {})
    registered = 0
    for command in transport_commands.COMMANDS:
        # A palette entry that opens the palette is noise in the list it opens.
        if command.id == transport_commands.COMMAND_PALETTE:
            continue
        # Quill Cast already listed most of the transport by name, and Radio
        # listed play/stop/volume. Registering a second entry for the same verb
        # would leave two identical-sounding rows in a list somebody arrows
        # through -- so an app's own entry wins and this fills the gaps.
        if any(f"{prefix}.{name}" in existing for name in _existing_names(command)):
            continue
        command_id = f"{prefix}.{command.id}"
        title = f"{prefix.title()}: {command.label.replace('&', '')}"
        try:
            registry.register(
                command_id,
                title,
                lambda cid=command.id: perform(host, cid),
                keybinding=command.key,
            )
        except ValueError:
            # Already registered (a second frame, or an app that registers its
            # own by the same id). The first wins; a duplicate is not an error
            # worth taking a window down for.
            continue
        registered += 1
    return registered


def _describe_state(state: Any) -> tuple[bool, bool]:
    """``(playing, bounded)`` from either app's playback state. Pure.

    Radio's state carries the ``station``. Quill Cast's ``PodcastPlaybackState``
    carries an episode -- ``show_id``, ``episode_guid``, ``title`` -- and has no
    ``station`` field at all. Asking only for a station therefore answered
    "Nothing is playing." to every gated verb in Cast *while an episode played*:
    Stop, skip, speed, chapters and Where Am I all refused, and the ``podcast_*``
    methods behind the gate were never reached (found 2026-08-19). The verb
    table and the alias table were both right; the question in front of them was
    asked in Radio's dialect only, and the test that covered this checked that
    Cast's methods exist rather than that they can be reached.

    An episode is always **bounded**: it is a file with a length, so position,
    speed and chapters mean something the moment one is playing -- where a live
    stream has none of the three, which is the distinction ``needs_bounded``
    exists to draw.
    """
    station = getattr(state, "station", None)
    if station is not None:
        return True, bool(getattr(station, "is_recording", False))
    if not hasattr(state, "episode_guid"):
        return False, False
    # LOADING and PAUSED both count as playing: an episode you paused is one you
    # can still stop, seek or speed up, and refusing there would be the same
    # silence this module exists to remove.
    phase = str(getattr(getattr(state, "state", None), "name", "") or "")
    playing = bool(str(getattr(state, "title", "") or "")) and phase not in {"STOPPED", "ERROR"}
    return playing, playing


def _state(host: Any) -> tuple[bool, bool]:
    """``(something is playing, it is a bounded recording)``. Never raises."""
    controller = _controller_of(host)
    if controller is None:
        return False, False
    try:
        return _describe_state(controller.state)
    except Exception:  # noqa: BLE001 - a key press must never crash on a probe
        return False, False


def _announce(host: Any, message: str) -> None:
    announce = getattr(host, "_announce", None)
    if callable(announce) and message:
        announce(message)


def perform(host: Any, command_id: str) -> bool:
    """Run one transport verb on *host*. True when it acted.

    The dispatch is by name rather than by a table of callables so that a
    window which happens to implement a verb itself (Cast's own play/pause,
    say) wins over the shared implementation without registering anything.

    Order: ``host.transport_<verb>``, then Cast's ``podcast_*``, then the shared
    implementation. **The first of those is an escape hatch nothing currently
    uses** -- no class in the repo defines a ``transport_*`` method -- so the
    live path is the last two. It is documented as first because that is where a
    window's own opinion would go if one ever needed one; do not go looking for
    the overrides.
    """
    command = transport_commands.command(command_id)
    if command is None:
        return False
    playing, bounded = _state(host)
    refusal = transport_commands.refusal(command_id, playing=playing, bounded=bounded)
    if refusal:
        _announce(host, refusal)
        return False
    own = getattr(host, f"transport_{command.verb}", None)
    if callable(own):
        own()
        return True
    # Cast next: it has its own player and its own complete set of verbs, and
    # they must win over Radio's shared implementations, which would be talking
    # to a controller Cast does not have.
    cast = _cast_verb(host, command.verb)
    if cast is not None:
        cast()
        return True
    return _shared_verb(host, command.verb)


#: How much one Volume Up or Volume Down moves the 0-100 scale, for a player
#: with no stepper of its own (Quill Cast's). Matched deliberately to
#: ``RadioPlayerController.volume_up``'s default: it was 5 here and 10 there,
#: so the same key moved a different distance depending on which window had
#: focus -- exactly the drift this module exists to end (found 2026-08-19).
VOLUME_STEP = 10


def _controller_of(host: Any) -> Any:
    return (
        getattr(host, "_radio_controller", None)
        or getattr(host, "_controller", None)
        # Quill Cast's player. Its controller has a different shape from
        # Radio's (set_rate/seek rather than set_playback_rate), which is why
        # Cast is served by its own verbs below rather than by this object.
        or getattr(host, "_podcast_controller", None)
    )


#: Quill Cast implements the whole transport already, as ``podcast_*`` methods
#: on its app frame -- it just had no way to reach them from anywhere but its
#: own menu bar. Most map by name; these four are the ones whose names differ,
#: and spelling them out here is cheaper than renaming methods two menus and a
#: keymap already point at.
_CAST_VERB_ALIASES: dict[str, str] = {
    "toggle_mute": "podcast_mute_toggle",
    "slow_down": "podcast_speed_down",
    "reset_speed": "podcast_speed_reset",
    "announce_position": "podcast_player_information",
}


def _cast_verb(host: Any, verb: str) -> Any:
    """Cast's own implementation of *verb*, or ``None``."""
    name = _CAST_VERB_ALIASES.get(verb, f"podcast_{verb}")
    found = getattr(host, name, None)
    return found if callable(found) else None


def _volume_of(controller: Any) -> tuple[int | None, bool]:
    """``(level 0-100 or None, muted)``, from whichever player this is.

    Radio keeps both on ``controller.state``; Cast keeps them on the controller
    (``PodcastPlayerVolumeMixin``). Reading only the state meant Cast's Volume
    Up and Down fell back to a default of 100 and jumped there from whatever the
    listener had actually set -- the same shape of mistake as ``_describe_state``
    above, and found with it.
    """
    state = getattr(controller, "state", None)
    level = getattr(state, "volume_percent", None)
    muted = getattr(state, "muted", None)
    if level is None:
        level = getattr(controller, "volume_percent", None)
    if muted is None:
        muted = getattr(controller, "muted", False)
    return (None if level is None else int(level)), bool(muted)


def _title_of(state: Any) -> str:
    """What is playing, in one line, from either state shape."""
    station = getattr(state, "station", None)
    if station is not None:
        return str(getattr(station, "display_name", "") or "Playing")
    title = str(getattr(state, "title", "") or "Playing")
    # Paused is a fact the readout must not swallow: the panel offers one
    # Play/Pause button and a listener needs to know which way it will go.
    phase = str(getattr(getattr(state, "state", None), "name", "") or "").capitalize()
    return f"{title} (paused)" if phase == "Paused" else title


def _rate_of(controller: Any) -> float:
    """The playback speed in force, whichever way this player spells it."""
    radio_rate = getattr(controller, "playback_rate", None)  # Radio: a method
    if callable(radio_rate):
        return float(radio_rate())
    cast_rate = getattr(controller, "rate", None)  # Cast: a property
    return float(cast_rate) if isinstance(cast_rate, int | float) else 1.0


def _position_line(controller: Any) -> str:
    """ "3 minutes of 18 minutes", from either player."""
    from quill.ui.radio import bounded_playback_ui

    if hasattr(controller, "duration_ms"):  # Radio, which also knows chapters
        return bounded_playback_ui.describe_position(controller)
    position = bounded_playback_ui.spoken_duration(int(controller.position_ms()))
    return f"{position} of {bounded_playback_ui.spoken_duration(int(controller.length_ms()))}"


def describe_now_playing(host: Any) -> str:
    """What is playing, where you are in it, how fast and how loud.

    This is the player panel's readout, and it lives here rather than in the
    panel because *both* apps summon that panel and only this module knows both
    players' shapes. Never raises: a readout that throws takes the panel with it.
    """
    controller = _controller_of(host)
    if controller is None:
        return "Nothing is playing."
    try:
        state = controller.state
        playing, bounded = _describe_state(state)
        if not playing:
            return "Nothing is playing."
        lines = [_title_of(state)]
        if bounded:
            lines.append(_position_line(controller))
            rate = _rate_of(controller)
            if rate != 1.0:
                lines.append(f"Speed {rate:g} times normal.")
        level, muted = _volume_of(controller)
        if muted:
            lines.append("Muted.")
        elif level is not None:
            lines.append(f"Volume {level} percent.")
        return "\n".join(line for line in lines if line)
    except Exception:  # noqa: BLE001 - a readout must never crash the panel
        return "Playing."


def describe_volume(controller: Any) -> str:
    """The one sentence Quill Radio says about its own volume.

    There were three: "Radio volume 45" (main window and Find Stations),
    "Volume 45" (Recordings Manager -- no unit at all, so the listener has to
    know the scale) and "Volume 45 percent." (here). Same fact, three readings,
    chosen by which window had focus. This is now the only one, and every
    surface calls it.
    """
    level, muted = _volume_of(controller)
    if muted:
        return "Muted."
    if level is None:
        return ""
    return f"Volume {level} percent." if level else "Volume off."


def _step_volume(host: Any, direction: int) -> bool:
    """Volume, from any window, without that window owning a slider.

    The controller stores the level and the engine applies it, so stepping it
    here keeps every surface honest: the main window's slider, the browse
    window's slider and the status bar all read the same number back.

    **The player's own stepper wins when it has one.** Doing the arithmetic here
    instead meant two bugs at once: Radio moved 10 through the menus and 5
    through this module, and ``RadioPlayerController.volume_up`` clears mute
    before stepping where this did not -- so Volume Up while muted announced
    "Volume 5 percent." and produced no sound at all.
    """
    controller = _controller_of(host)
    if controller is None:
        return False
    try:
        stepper = getattr(controller, "volume_up" if direction > 0 else "volume_down", None)
        if callable(stepper):
            stepper()
        else:
            # Quill Cast's player has no stepper of its own. Its ``set_volume``
            # clears mute the same way Radio's ``volume_up`` does, so the two
            # paths behave alike.
            current, _muted = _volume_of(controller)
            base = 100 if current is None else current
            controller.set_volume(max(0, min(100, base + direction * VOLUME_STEP)))
    except Exception:  # noqa: BLE001 - a volume key must never crash a window
        return False
    _announce(host, describe_volume(controller))
    refresh = getattr(host, "_sync_volume_slider", None) or getattr(host, "_refresh_volume", None)
    if callable(refresh):
        refresh()
    return True


def _phase_of(controller: Any) -> str:
    """``"PLAYING"`` / ``"PAUSED"`` / ... from either app's state enum."""
    state = getattr(controller, "state", None)
    return str(getattr(getattr(state, "state", None), "name", "") or "").upper()


def _describe_after(verb: str, controller: Any) -> str:
    """What to say once the controller has performed *verb*. "" when nothing.

    ``bounded_playback_ui`` announces its own verbs. These three reach the
    controller directly and said **nothing at all** -- in the one module whose
    stated law is that a silent key is indistinguishable from an unbound one.
    Mute was the worst of the three: silence is the intended effect, so "did it
    mute, or did the stream drop?" had no answer (found 2026-08-19).
    """
    if verb == "stop":
        return "Stopped."
    if verb == "toggle_mute":
        return "Muted." if _volume_of(controller)[1] else "Unmuted."
    if verb == "toggle_play_pause":
        phase = _phase_of(controller)
        if phase == "PAUSED":
            return "Paused."
        if phase in {"CONNECTING", "LOADING"}:
            return "Connecting."
        if phase in {"STOPPED", "ERROR"}:
            return "Stopped."
        return "Playing."
    return ""


def _go_to_player(host: Any) -> bool:
    """Summon the player panel over whatever window you are in.

    The player has no window of its own on purpose -- see
    :mod:`quill.ui.radio.player_panel`. This is the key that brings it to you
    and, when you close it, leaves you exactly where you were. It replaces
    "Alt+Tab and a guess", which was the only answer to *"where did the thing I
    am listening to go?"* (2026-08-18).
    """
    owner = getattr(host, "_download_host", None) or getattr(host, "_transport_host", None) or host
    window = (
        getattr(host, "_win", None)
        or getattr(host, "dialog", None)
        or getattr(owner, "frame", None)
    )
    if window is None:
        _announce(host, "The player could not be opened here.")
        return False
    from quill.ui.radio import player_panel

    player_panel.summon(owner, window)
    return True


def _shared_verb(host: Any, verb: str) -> bool:
    """The default implementation of *verb*, for a host with no opinion."""
    from quill.ui.radio import bounded_playback_ui

    if verb == "volume_up":
        return _step_volume(host, 1)
    if verb == "volume_down":
        return _step_volume(host, -1)
    if verb == "go_to_player":
        return _go_to_player(host)
    shared = getattr(bounded_playback_ui, verb, None)
    if callable(shared):
        shared(host)
        return True
    controller = _controller_of(host)
    method = getattr(controller, verb, None) if controller is not None else None
    if callable(method):
        method()
        _announce(host, _describe_after(verb, controller))
        return True
    _announce(host, "That is not available in this window.")
    return False
