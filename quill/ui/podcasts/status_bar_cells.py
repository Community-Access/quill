"""What QUILL Cast's status-bar cells say, and what each one does.

The other half of :mod:`quill.ui.podcasts.status_bar`, split out under GATE-11
-- and split here rather than anywhere else on purpose. The bar divides
cleanly in two: one half is a wx widget (a panel of buttons, focus, arrows,
Tab, a popup menu) and knows nothing about podcasts; the other half is nine
statements about a listening session and knows nothing about wx. Cast has nine
cells where Quill Radio has six, and nine cells' worth of readouts, hints and
menus does not fit beside the navigation machinery inside the 600-line cap.

Everything here is a plain function of a *host* -- the ``PodcastsAppFrame`` --
which is the shape :mod:`quill.ui.podcasts.speed` and
:mod:`quill.ui.podcasts.queue_commands` already use, and the reason a test can
drive every readout with a ``SimpleNamespace`` and no wx at all.

Two rules run through the whole file.

**An action cell's label IS its action; a readout's label is its value.** The
cells are buttons, and a button labelled with a bare readout promises
something it does not do -- the lesson Radio's bar paid for on live feedback.
So Play/Pause/Resume and Mute/Unmute flip with the state, and the seven
readouts answer Enter with something worth having.

**A readout with nothing to say says nothing.** An empty queue, an empty
Inbox, no downloads and no sleep timer all render as the bare cell name rather
than as "0" or "Off": a zero is a number somebody has to read before finding
out there is nothing to read, which is the call
:mod:`quill.ui.podcasts.window_title` already makes about the Inbox count.

Every reader is defensive. The bar repaints on a timer and on every playback
change, so a controller mid-teardown -- or an older fake in a test -- must
produce an empty cell rather than an exception that takes the window down.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quill.core.podcasts.speed_scale import speed_label
from quill.ui.podcasts.window_title import inbox_count

__all__ = ["CellSpec", "build_specs", "call_host"]


@dataclass(frozen=True)
class CellSpec:
    """One status-bar cell: its stable key, spoken name, and behaviour.

    ``text`` returns the live value (``""`` for "nothing to say"), ``activate``
    is what Enter/Space does, ``help`` is the one-line hint F1 reads, and
    ``build_menu`` (if set) populates a right-click context menu with the
    actions that belong to this cell and nowhere else.
    """

    key: str
    name: str
    text: Callable[[], str]
    activate: Callable[[], None]
    help: str
    build_menu: Callable[[Any], None] | None = None
    #: An *action* cell supplies its live button label here -- "Play"/"Pause",
    #: "Mute"/"Unmute" -- and leaves ``text`` returning "".
    action_label: Callable[[], str] | None = None
    #: The shortcut an action cell teaches ("Ctrl+P"), folded into its
    #: accessible name so the bar quietly teaches the key.
    key_hint: str = ""
    #: A cell whose hint depends on live state supplies it here, and the bar's
    #: ``refresh`` keeps it current. Speed needs it because the *scope* is the
    #: half of the fact a number cannot carry -- "1.5x" does not say whether
    #: Speed Up would change one file, one podcast or everything. Downloads
    #: needs it because one number counts two different things (in flight,
    #: waiting) and which of them moved is the interesting part.
    live_help: Callable[[], str] | None = None


def call_host(host: object, name: str, *args: object) -> None:
    """Call ``host.name(*args)`` if the host has it, and do nothing if not.

    The bar is wired against a frame built from a dozen mixins, and a cell that
    raised because one of them was not mixed in would take the whole window
    down on a right-click. A missing action is a silent no-op by design.
    """
    method = getattr(host, name, None)
    if callable(method):
        method(*args)


def build_specs(host: Any, wx: Any) -> list[CellSpec]:
    """Every cell, in the order a listener meets them left to right.

    The order is the order of a listening session: what is playing, how loud,
    how fast, what is next, what has arrived, what is coming down the wire,
    when it stops, and the time.

    *wx* is only ever used to build a context menu, and may be ``None`` in a
    headless test -- the readouts and the activate actions never touch it.
    """
    return [
        CellSpec(
            key="play_pause",
            name="Play or pause",
            text=lambda: "",
            action_label=lambda: play_pause_label(host),
            key_hint="Ctrl+P",
            activate=lambda: call_host(host, "podcast_toggle_play_pause"),
            help=(
                "Start the episode, or pause it where it is. Right-click for "
                "Stop, the next and previous episode in your queue, and "
                "Continue Listening."
            ),
            build_menu=lambda menu: _append(host, wx, menu, _PLAY_ROWS),
        ),
        CellSpec(
            key="mute",
            name="Mute or unmute",
            text=lambda: "",
            action_label=lambda: mute_label(host),
            key_hint="Ctrl+Alt+M",
            activate=lambda: call_host(host, "podcast_mute_toggle"),
            help=(
                "Silence the episode without pausing it, so it keeps its "
                "place. Right-click for Volume Up, Volume Down, and where the "
                "sound comes out."
            ),
            # The Mute and Volume cells share one menu: they are two halves of
            # one control, and somebody who right-clicks either wants the
            # same list rather than half of it.
            build_menu=lambda menu: _append(host, wx, menu, _VOLUME_ROWS),
        ),
        CellSpec(
            key="volume",
            name="Volume",
            text=lambda: volume_text(host),
            activate=lambda: announce_volume(host),
            help=(
                "How loud the episode is. Press Enter to hear the level again; "
                "right-click for Volume Up, Volume Down, and where the sound "
                "comes out."
            ),
            build_menu=lambda menu: _append(host, wx, menu, _VOLUME_ROWS),
        ),
        CellSpec(
            key="speed",
            name="Speed",
            text=lambda: speed_text(host),
            activate=lambda: announce_speed(host),
            help=(
                "How fast the episode plays. Press Enter to hear the speed and "
                "what it applies to; right-click for Speed Up, Speed Down, "
                "Reset Speed, and Sound Enhancements."
            ),
            live_help=lambda: speed_help(host),
            build_menu=lambda menu: _append(host, wx, menu, _SPEED_ROWS),
        ),
        CellSpec(
            key="queue",
            name="Queue",
            text=lambda: queue_text(host),
            activate=lambda: call_host(host, "_open_play_queue"),
            help=(
                "How many episodes are waiting in the Play Queue. Press Enter "
                "to open it; right-click to play the next one or empty the "
                "queue."
            ),
            build_menu=lambda menu: _append(host, wx, menu, _QUEUE_ROWS),
        ),
        CellSpec(
            key="inbox",
            name="Inbox",
            text=lambda: inbox_text(host),
            activate=lambda: call_host(host, "open_cast_inbox"),
            help=(
                "How many new episodes are waiting in the Inbox. Press Enter "
                "to open it; right-click to mark the lot as played."
            ),
            build_menu=lambda menu: _append(host, wx, menu, _INBOX_ROWS),
        ),
        CellSpec(
            key="downloads",
            name="Downloads",
            text=lambda: downloads_text(host),
            activate=lambda: call_host(host, "open_podcast_downloads"),
            help=(
                "Episodes coming down to this computer. Press Enter to open "
                "Downloads; right-click to pause or resume them all."
            ),
            live_help=lambda: downloads_help(host),
            build_menu=lambda menu: _append(host, wx, menu, _DOWNLOAD_ROWS),
        ),
        CellSpec(
            key="sleep_timer",
            name="Sleep timer",
            text=lambda: sleep_timer_text(host),
            activate=lambda: call_host(host, "open_sleep_timer_dialog"),
            help=(
                "How long until playback stops. Press Enter to set or cancel "
                "it; right-click to stop at the end of this episode or add "
                "five minutes."
            ),
            build_menu=lambda menu: _menu_sleep_timer(host, wx, menu),
        ),
        CellSpec(
            key="clock",
            name="Time",
            text=clock_text,
            activate=lambda: announce_clock(host),
            help="The current time. Press Enter to hear the full date and time.",
        ),
    ]


# -- action labels ------------------------------------------------------------


def play_pause_label(host: Any) -> str:
    """The verb pressing it performs: Play, Pause or Resume.

    Three labels rather than two, because the main window's own transport
    button already has three (``_refresh_transport_controls``) and a bar that
    disagreed with the button six inches above it would be the confusing one.
    An episode, unlike a live stream, keeps its place when paused, so "Resume"
    is a different promise from "Play" and worth the word.
    """
    from quill.ui.podcasts.player_controller import PodcastPlayerState

    current = getattr(_state(host), "state", None)
    if current in (PodcastPlayerState.PLAYING, PodcastPlayerState.LOADING):
        return "Pause"
    if current is PodcastPlayerState.PAUSED:
        return "Resume"
    return "Play"


def mute_label(host: Any) -> str:
    controller = getattr(host, "_podcast_controller", None)
    return "Unmute" if bool(getattr(controller, "muted", False)) else "Mute"


# -- readouts -----------------------------------------------------------------


def volume_text(host: Any) -> str:
    """``"70%"``, or ``"Muted"``, or ``""`` when there is no player yet.

    Read off the *controller* rather than its state snapshot: Cast keeps volume
    and mute on the controller (``player_volume.py``) while Radio keeps them on
    the state object, and reading the wrong one here would give a cell that is
    silently always 100%.
    """
    controller = getattr(host, "_podcast_controller", None)
    if controller is None:
        return ""
    if bool(getattr(controller, "muted", False)):
        return "Muted"
    return f"{int(getattr(controller, 'volume_percent', 100) or 0)}%"


def speed_text(host: Any) -> str:
    """The speed in force, as a listener hears it: ``1.5x``, ``1x``."""
    try:
        from quill.ui.podcasts import speed

        return speed_label(speed.current_speed(host))
    except Exception:  # noqa: BLE001 - a status cell must never raise
        return ""


def queue_text(host: Any) -> str:
    """How many episodes the Play Queue holds; ``""`` when it is empty."""
    count = len(getattr(getattr(host, "_podcast_library", None), "queue", ()) or ())
    return str(count) if count else ""


def inbox_text(host: Any) -> str:
    """The Inbox as the Inbox view counts it, so the two cannot disagree."""
    count = inbox_count(getattr(host, "_podcast_library", None))
    return str(count) if count else ""


def downloads_text(host: Any) -> str:
    """What is coming down: in flight, and how many behind it.

    "2 of 7" rather than "2", because somebody who has just queued a season
    wants to know the queue is moving -- and the number in flight is held at
    the concurrency limit, so on its own it barely moves at all.
    """
    active, waiting = download_counts(host)
    if not active and not waiting:
        return ""
    if not active:
        return f"{waiting} waiting"
    return str(active) if not waiting else f"{active} of {active + waiting}"


def download_counts(host: Any) -> tuple[int, int]:
    """``(downloading, queued)``, or ``(0, 0)`` for any unhealthy queue."""
    queue = getattr(host, "_podcast_download_queue", None)
    if queue is None:
        return (0, 0)
    try:
        active = int(queue.active_count() or 0)
        waiting = sum(1 for item in queue.snapshot() if item.status == "queued")
    except Exception:  # noqa: BLE001 - a status cell must never raise
        return (0, 0)
    return (active, waiting)


def sleep_timer_text(host: Any) -> str:
    """``""`` when nothing is set -- the bar says only what is true.

    Radio's equivalent cell says "Off", which is a word a listener reads on
    every pass to learn that nothing is happening. The bare cell name says the
    same thing in silence.
    """
    timer = getattr(host, "_sleep_timer_controller", None)
    if timer is None or not bool(getattr(timer, "is_active", False)):
        return ""
    if bool(getattr(timer, "is_end_of_episode", False)):
        return "End of episode"
    seconds = int(getattr(timer, "remaining_seconds", 0) or 0)
    minutes = (seconds + 59) // 60
    return "1 min left" if minutes == 1 else f"{minutes} min left"


def clock_text() -> str:
    try:
        return datetime.now().strftime("%I:%M %p").lstrip("0")
    except Exception:  # noqa: BLE001 - a status cell must never raise
        return ""


def _state(host: Any) -> object | None:
    controller = getattr(host, "_podcast_controller", None)
    return getattr(controller, "state", None) if controller is not None else None


# -- live hints ---------------------------------------------------------------


def speed_scope_label(host: Any) -> str:
    """What a speed change would apply to, in the listener's own words.

    The same three-way ``speed.apply_speed`` resolves before it writes -- an
    imported file's own speed, then the playing podcast's, then the shared
    default -- read through that module rather than reimplemented, so the hint
    and the command can never describe different scopes.
    """
    try:
        from quill.ui.podcasts import speed

        show, episode, _settings = speed.speed_scope(host)
    except Exception:  # noqa: BLE001 - a hint must never raise
        return "every podcast"
    if episode is not None:
        return "this file only"
    if show is not None:
        return str(getattr(show, "title", "") or "this podcast")
    return "every podcast"


def speed_help(host: Any) -> str:
    return (
        "How fast the episode plays. Speed Up and Speed Down here change the "
        f"speed for {speed_scope_label(host)}. Press Enter to hear both the "
        "speed and what it applies to."
    )


def downloads_help(host: Any) -> str:
    active, waiting = download_counts(host)
    if not active and not waiting:
        return "Nothing is downloading. Press Enter to open Downloads."
    return (
        f"{active} downloading, {waiting} waiting. Press Enter to open "
        "Downloads; right-click to pause or resume them all."
    )


# -- what Enter says ----------------------------------------------------------


def announce_volume(host: Any) -> None:
    value = volume_text(host)
    if not value:
        call_host(host, "_announce", "Nothing is playing.")
        return
    call_host(host, "_announce", value if value == "Muted" else f"Volume {value}")


def announce_speed(host: Any) -> None:
    """The speed *and* the scope, which is the rule every speed verb in Cast
    follows (``ui/podcasts/speed.py``): "1.5x" on its own does not say whether
    the listener is hearing one file, one podcast or everything."""
    value = speed_text(host)
    if not value:
        return
    call_host(host, "_announce", f"Speed {value} for {speed_scope_label(host)}")


def announce_clock(host: Any) -> None:
    try:
        stamp = datetime.now().strftime("%A, %B %d, %I:%M %p")
    except Exception:  # noqa: BLE001
        return
    call_host(host, "_announce", stamp)


# -- context menus ------------------------------------------------------------
#
# Each menu is a tuple of ``(label, host method name)`` rows rather than a
# block of NewIdRef/Append/Bind per cell: the interesting part of a cell menu
# is *which* actions belong to that cell, and a table is the only shape in
# which that is readable at a glance. A row naming a method the host does not
# have does nothing rather than raising -- see :func:`call_host`.

_PLAY_ROWS: tuple[tuple[str, str], ...] = (
    ("Now Playing...", "open_now_playing"),
    ("Stop", "podcast_stop"),
    ("Next in Queue", "podcast_next_in_queue"),
    ("Previous in Queue", "podcast_previous_in_queue"),
    ("Continue Listening...", "open_continue_listening"),
)

_VOLUME_ROWS: tuple[tuple[str, str], ...] = (
    ("Volume Up", "podcast_volume_up"),
    ("Volume Down", "podcast_volume_down"),
    ("Audio Output Mode", "podcast_cycle_channel_mode"),
    ("Audio Output Device...", "podcast_choose_output_device"),
)

_SPEED_ROWS: tuple[tuple[str, str], ...] = (
    ("Speed Up", "podcast_speed_up"),
    ("Speed Down", "podcast_speed_down"),
    ("Reset Speed", "podcast_speed_reset"),
    ("Sound Enhancements...", "open_podcast_sound_enhancements"),
)

_QUEUE_ROWS: tuple[tuple[str, str], ...] = (
    ("Play Queue...", "_open_play_queue"),
    ("Next in Queue", "podcast_next_in_queue"),
    ("Clear Entire Queue...", "podcast_clear_entire_queue"),
)

_INBOX_ROWS: tuple[tuple[str, str], ...] = (
    ("Inbox...", "open_cast_inbox"),
    ("Mark All as Played...", "podcast_mark_all_played"),
)

_DOWNLOAD_ROWS: tuple[tuple[str, str], ...] = (
    ("Downloads...", "open_podcast_downloads"),
    ("Pause All Downloads", "podcast_pause_all_downloads"),
    ("Resume All Downloads", "podcast_resume_all_downloads"),
)


def _append(host: Any, wx: Any, menu: Any, rows: tuple[tuple[str, str], ...]) -> None:
    """Append *rows* to *menu*, each bound to the named host method.

    No "&" anywhere in a label. Cast's menu bar already claims most of the
    alphabet, a popup inherits the window's collisions, and a duplicate
    mnemonic is worse than none: Windows cycles focus between the duplicates
    instead of pressing, so one of the pair silently cannot be reached and
    nothing announces the loss (GATE-14). Lists this short are quicker to arrow
    than to remember a letter for.
    """
    for label, method in rows:
        item_id = wx.NewIdRef()
        menu.Append(item_id, label)
        menu.Bind(wx.EVT_MENU, lambda _e, m=method: call_host(host, m), id=item_id)


def _menu_sleep_timer(host: Any, wx: Any, menu: Any) -> None:
    """The one menu whose first label is live: "Change Sleep Timer..." once one
    is running, so the row does not offer to set a timer that is already set."""
    timer = getattr(host, "_sleep_timer_controller", None)
    active = bool(getattr(timer, "is_active", False))
    rows = (
        ("Change Sleep Timer..." if active else "Sleep Timer...", "open_sleep_timer_dialog"),
        ("Sleep at End of This Episode", "sleep_timer_end_of_episode"),
        ("Extend 5 Minutes", "extend_sleep_timer_command"),
    )
    _append(host, wx, menu, rows)
