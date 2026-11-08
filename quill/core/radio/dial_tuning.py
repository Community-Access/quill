"""Dial tuning: the station under focus plays, as a radio dial would.

The idea comes from BlindRadio by serrebidev (MIT), github.com/serrebidev/blindradio,
doc/readme.md "Dial tuning" and its "FM Sound Between Stations" setting. No
BlindRadio code is copied; the design Quill Radio follows is
docs/design/blindradio-ideas/dial-tuning.md, agreed on 2026-11-07.

This module is the whole policy and none of the plumbing:

* **Which rows tune.** Only live station lists: Favorites, Recently Played,
  Browse folders of stations, Networks and Search results. A folder, a podcast,
  a YouTube link, anything on demand and any row that needs a network round trip
  before it can play never does.
* **The settle timer.** Focus has to stay on a station for the chosen wait
  before it plays. Holding an arrow plays nothing until it stops, even with
  Instant chosen: rows arriving closer together than :data:`HOLD_GAP_S` are
  somebody holding a key, and the wait is stretched to cover the gap.
* **Neighbours.** Once a station has settled, the station before it and the one
  after it may be kept connected, muted, so the next step is near instant.
  At most :data:`MAX_WARM` of them, so never more than :data:`MAX_PLAYERS`
  players at once. Not on a metered connection when the listener said so.
* **The recording pause.** While a recording runs, moving tunes nothing, and
  that is said once, the first time somebody moves.
* **A dead station.** The hiss stops after :data:`SILENT_AFTER_S` with no
  audio, or at once when the connection fails; :data:`SAY_AFTER_S` later the
  station is said, once, to be not answering.
* **Passing through.** A station that is only being tuned past is not Recently
  Played, not Song History, not listening statistics and not scrobbled. Enter
  commits it, and from then on it is an ordinary play.

wx-free, strict-typed, and driven by an injected clock so the timers can be
tested without waiting for them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.radio.models import RadioStation

__all__ = [
    "BROWSE",
    "DEFAULT_WAIT_MS",
    "DIAL_KEYS",
    "FAVORITES",
    "HISS_LEVELS",
    "HOLD_GAP_S",
    "LIVE_LISTS",
    "MAX_PLAYERS",
    "MAX_WARM",
    "NETWORKS",
    "ON_DEMAND_SOURCES",
    "RECENT",
    "RECORDING_PAUSED",
    "SAY_AFTER_S",
    "SEARCH",
    "SILENT_AFTER_S",
    "WAIT_CHOICES",
    "DialRow",
    "DialSettings",
    "DialTuner",
    "Say",
    "Tune",
    "Warm",
    "hiss_level_index",
    "not_answering",
    "row_tunes",
    "state_word",
    "wait_index",
    "warm_candidates",
]

#: ``(milliseconds, label)`` for Preferences' "Wait before tuning". The labels
#: are what the control reads aloud, so the default says it is the default.
WAIT_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "Instant"),
    (200, "200 milliseconds"),
    (350, "350 milliseconds (default)"),
    (500, "500 milliseconds"),
    (1000, "1 second"),
)
DEFAULT_WAIT_MS = 350

#: ``(id, label)`` for the hiss level. One fixed level each, whatever the
#: volume of the station being tuned to.
HISS_LEVELS: tuple[tuple[str, str], ...] = (("low", "Low (default)"), ("medium", "Medium"))

#: Rows arriving closer together than this are a held arrow key. Key repeat on
#: Windows runs at about 30 a second; a person tapping does not get near it.
HOLD_GAP_S = 0.15
#: No audio after this long, and the hiss stops: a dial that hisses forever at
#: a dead station sounds like a station that is about to arrive.
SILENT_AFTER_S = 5.0
#: Then, this much later, the station is said once to be not answering.
SAY_AFTER_S = 3.0
#: The current station and two warm neighbours, and never more.
MAX_PLAYERS = 3
MAX_WARM = MAX_PLAYERS - 1

#: List kinds. Ids, not labels: nothing here is spoken.
FAVORITES = "favorites"
RECENT = "recent"
BROWSE = "browse"
NETWORKS = "networks"
SEARCH = "search"
LIVE_LISTS: frozenset[str] = frozenset({FAVORITES, RECENT, BROWSE, NETWORKS, SEARCH})

#: Browse sources whose rows are recordings, video or on demand, by the root
#: id ``quill.core.radio.browse_sources.ROOT_SOURCES`` gives them. A row under
#: one of these never tunes, whatever it looks like.
ON_DEMAND_SOURCES: frozenset[str] = frozenset({
    "localmedia",
    "apple",
    "podcastindex",
    "archive",
    "librivox",
    "gutenberg",
    "audiopub",
    "audius",
    "mixcloud",
    "ccmixter",
    "tv",
    "youtube",
})

#: Quill Radio's keys for the two commands (``quill.core.app_keymaps``). U for
#: tUne, since Alt+Shift+T is the station's time-shift length; P for the Playing
#: station's row. The Alt+Shift row is where Radio's menu bar still has letters.
DIAL_KEYS: dict[str, str] = {
    "radio.dial_tuning": "Alt+Shift+U",
    "radio.go_to_playing_station": "Alt+Shift+P",
}

RECORDING_PAUSED = "Tuning as you move is paused while you record. Press Enter to play a station."


def not_answering(name: str) -> str:
    """The one sentence a dead station gets."""
    return f"{name or 'That station'} is not answering."


def state_word(enabled: bool) -> str:
    """What the on/off command says: the reader cannot know the new state."""
    return (
        "Tune as you move through stations, on."
        if enabled
        else "Tune as you move through stations, off."
    )


def wait_index(wait_ms: int) -> int:
    """The Preferences index for *wait_ms*; an unknown value means the default."""
    for index, (value, _label) in enumerate(WAIT_CHOICES):
        if value == wait_ms:
            return index
    return wait_index(DEFAULT_WAIT_MS)


def hiss_level_index(level: str) -> int:
    for index, (value, _label) in enumerate(HISS_LEVELS):
        if value == level:
            return index
    return 0


def _normal_wait(value: object) -> int:
    try:
        wanted = int(str(value))
    except (TypeError, ValueError):
        return DEFAULT_WAIT_MS
    known = {ms for ms, _label in WAIT_CHOICES}
    return wanted if wanted in known else DEFAULT_WAIT_MS


@dataclass(frozen=True, slots=True)
class DialSettings:
    """Every part of dial tuning is a setting, and it ships off."""

    enabled: bool = False
    wait_ms: int = DEFAULT_WAIT_MS
    keep_neighbours: bool = True
    metered_stop: bool = True
    hiss: bool = True
    hiss_level: str = "low"
    remember_volume: bool = False

    @classmethod
    def from_history(cls, history: object) -> DialSettings:
        """Read the seven ``dial_*`` fields off a history record, defensively."""
        level = str(getattr(history, "dial_hiss_level", "low") or "low")
        return cls(
            enabled=bool(getattr(history, "dial_tuning", False)),
            wait_ms=_normal_wait(getattr(history, "dial_wait_ms", DEFAULT_WAIT_MS)),
            keep_neighbours=bool(getattr(history, "dial_keep_neighbours", True)),
            metered_stop=bool(getattr(history, "dial_metered_stop", True)),
            hiss=bool(getattr(history, "dial_hiss", True)),
            hiss_level=level if level in {v for v, _l in HISS_LEVELS} else "low",
            remember_volume=bool(getattr(history, "dial_remember_volume", False)),
        )


@dataclass(frozen=True, slots=True)
class DialRow:
    """One row a list surface offers the dial, described without wx."""

    key: str
    station: RadioStation | None = None
    list_kind: str = FAVORITES
    #: The Browse root the row sits under ("" outside Browse).
    source: str = ""
    #: The row's stream still has to be looked up (TuneIn, Apple).
    needs_resolve: bool = False

    @property
    def name(self) -> str:
        return self.station.display_name if self.station is not None else ""


def row_tunes(row: DialRow | None) -> bool:
    """Whether settling on *row* should play it (pure)."""
    if row is None or row.station is None or not row.key:
        return False
    if row.list_kind not in LIVE_LISTS or row.needs_resolve:
        return False
    if row.source in ON_DEMAND_SOURCES:
        return False
    station = row.station
    if station.is_recording or not station.stream_url:
        return False
    url = station.stream_url.strip().lower()
    if url.startswith("spotify:"):
        return False
    from quill.core.radio.youtube import is_youtube_url

    return not is_youtube_url(station.stream_url)


def warm_candidates(
    current: DialRow | None,
    before: DialRow | None,
    after: DialRow | None,
    *,
    settings: DialSettings,
    metered: bool,
) -> tuple[DialRow, ...]:
    """The neighbours worth keeping connected, after-first, at most two (pure).

    After first because people mostly move down a list. A neighbour that is the
    current station, or that does not tune, is no neighbour at all.
    """
    if not settings.enabled or not settings.keep_neighbours:
        return ()
    if metered and settings.metered_stop:
        return ()
    chosen: list[DialRow] = []
    current_key = current.key if current is not None else ""
    for row in (after, before):
        if row is None or not row_tunes(row) or row.key == current_key:
            continue
        if any(existing.key == row.key for existing in chosen):
            continue
        chosen.append(row)
    return tuple(chosen[:MAX_WARM])


@dataclass(frozen=True, slots=True)
class Tune:
    """Play this row now, as a station only passed through."""

    row: DialRow


@dataclass(frozen=True, slots=True)
class Warm:
    """Keep exactly these rows connected, muted; let every other one go."""

    rows: tuple[DialRow, ...] = ()


@dataclass(frozen=True, slots=True)
class Say:
    """Something only the app knows, said once."""

    text: str


Action = Tune | Warm | Say


@dataclass(slots=True)
class _Pending:
    row: DialRow
    before: DialRow | None
    after: DialRow | None
    deadline: float


@dataclass(slots=True)
class _Connect:
    """The station the dial last tuned, and how its connection is going."""

    row: DialRow
    started: float
    connected: bool = False
    failed_at: float | None = None
    silent_at: float | None = None
    said: bool = False
    neighbours: tuple[DialRow | None, DialRow | None] = field(default=(None, None))


class DialTuner:
    """The dial's state and timers. Every method returns what to do next."""

    def __init__(
        self,
        settings: DialSettings | None = None,
        *,
        clock: Callable[[], float],
        is_metered: Callable[[], bool] | None = None,
    ) -> None:
        self._settings = settings or DialSettings()
        self._clock = clock
        self._is_metered = is_metered or (lambda: False)
        self._pending: _Pending | None = None
        self._current: _Connect | None = None
        self._committed_key = ""
        self._last_focus: float | None = None
        self._recording_said = False
        self._hiss = False

    # -- settings ---------------------------------------------------------

    @property
    def settings(self) -> DialSettings:
        return self._settings

    def update_settings(self, settings: DialSettings) -> list[Action]:
        """Take new settings. Turning the dial off lets every neighbour go."""
        was_on = self._settings.enabled
        self._settings = settings
        if not settings.enabled:
            self._pending = None
            self._hiss = False
            return [Warm(())] if was_on else []
        if self._current is not None and not settings.hiss:
            self._hiss = False
        if self._current is not None and self._current.connected:
            before, after = self._current.neighbours
            return [Warm(self._warm_for(self._current.row, before, after))]
        return []

    # -- what the surfaces report ----------------------------------------

    def focus(
        self,
        row: DialRow | None,
        before: DialRow | None = None,
        after: DialRow | None = None,
        *,
        recording: bool = False,
    ) -> list[Action]:
        """Focus settled on *row*, which sits between *before* and *after*."""
        if not self._settings.enabled:
            return []
        now = self._clock()
        gap = None if self._last_focus is None else now - self._last_focus
        self._last_focus = now
        if not recording:
            self._recording_said = False
        if not row_tunes(row) or row is None:
            self._pending = None
            return []
        if recording:
            self._pending = None
            if self._recording_said:
                return []
            self._recording_said = True
            return [Say(RECORDING_PAUSED)]
        if self._current is not None and self._current.row.key == row.key:
            self._pending = None  # back on the station already playing
            return []
        wait = self._settings.wait_ms / 1000.0
        if gap is not None and gap < HOLD_GAP_S:
            wait = max(wait, HOLD_GAP_S)
        self._pending = _Pending(row, before, after, now + wait)
        return []

    def left_list(self) -> list[Action]:
        """Focus went somewhere else. What is playing keeps playing."""
        self._pending = None
        self._last_focus = None
        return [Warm(())] if self._settings.enabled else []

    def connected(self, key: str) -> list[Action]:
        """The tuned station is on the air."""
        current = self._current
        if current is None or current.row.key != key:
            return []
        current.connected = True
        current.failed_at = None
        current.silent_at = None
        self._hiss = False
        if key == self._committed_key:
            return []
        before, after = current.neighbours
        return [Warm(self._warm_for(current.row, before, after))]

    def failed(self, key: str) -> list[Action]:
        """The tuned station's connection gave up."""
        current = self._current
        if current is None or current.row.key != key or current.connected:
            return []
        self._hiss = False
        if current.failed_at is None:
            current.failed_at = self._clock()
        # Its neighbours were the old station's; a dead one has none worth keeping.
        return [Warm(())]

    def commit(self, key: str) -> bool:
        """Enter on the tuned station. True when there was one to commit.

        The caller then plays it for real; this only stops it counting as passed
        through, and restarts the connection watch for the reload.
        """
        current = self._current
        if current is None or current.row.key != key or key == self._committed_key:
            return False
        self._committed_key = key
        self._pending = None
        current.started = self._clock()
        current.connected = False
        current.failed_at = None
        current.silent_at = None
        current.said = False
        self._hiss = self._settings.hiss
        return True

    def forget(self) -> None:
        """Playback moved on outside the dial (a menu, a hotkey, Stop)."""
        self._current = None
        self._pending = None
        self._hiss = False

    # -- the clock ---------------------------------------------------------

    def next_due(self) -> float | None:
        """Seconds until :meth:`poll` has something to do, or None."""
        now = self._clock()
        deadlines: list[float] = []
        if self._pending is not None:
            deadlines.append(self._pending.deadline)
        current = self._current
        if current is not None and not current.connected and not current.said:
            if current.failed_at is None and current.silent_at is None:
                deadlines.append(current.started + SILENT_AFTER_S)
            elif current.row.key != self._committed_key:
                dead_from = current.failed_at or current.silent_at or now
                deadlines.append(dead_from + SAY_AFTER_S)
        if not deadlines:
            return None
        return max(0.0, min(deadlines) - now)

    def poll(self) -> list[Action]:
        """Run whatever the clock says is due."""
        if not self._settings.enabled:
            return []
        now = self._clock()
        actions: list[Action] = []
        pending = self._pending
        if pending is not None and now >= pending.deadline:
            self._pending = None
            self._current = _Connect(
                row=pending.row, started=now, neighbours=(pending.before, pending.after)
            )
            self._committed_key = ""
            self._hiss = self._settings.hiss
            # The new neighbours are warmed once this station is on the air,
            # not before: moving quickly must not open connections for every
            # row passed. The old ones stay until then, because one of them
            # may be the station just tuned, ready to be promoted.
            actions.append(Tune(pending.row))
        current = self._current
        if current is not None and not current.connected and not current.said:
            if (
                current.failed_at is None
                and current.silent_at is None
                and now - current.started >= SILENT_AFTER_S
            ):
                current.silent_at = now
                self._hiss = False
                actions.append(Warm(()))
            dead_from = current.failed_at if current.failed_at is not None else current.silent_at
            # A committed play that fails is an ordinary failure, and the
            # player says so itself; the dial only speaks for a passing tune.
            committed = current.row.key == self._committed_key
            if dead_from is not None and now - dead_from >= SAY_AFTER_S and not committed:
                current.said = True
                actions.append(Say(not_answering(current.row.name)))
        return actions

    # -- questions ---------------------------------------------------------

    @property
    def hiss_wanted(self) -> bool:
        """Whether the hiss should be sounding right now."""
        return self._hiss and self._settings.enabled and self._settings.hiss

    @property
    def current_key(self) -> str:
        return self._current.row.key if self._current is not None else ""

    @property
    def current_row(self) -> DialRow | None:
        return self._current.row if self._current is not None else None

    @property
    def pending_key(self) -> str:
        return self._pending.row.key if self._pending is not None else ""

    def passing_through(self, key: str) -> bool:
        """True while *key* is a station the dial tuned and Enter has not committed."""
        return bool(key) and key == self.current_key and key != self._committed_key

    def _warm_for(
        self, current: DialRow, before: DialRow | None, after: DialRow | None
    ) -> tuple[DialRow, ...]:
        try:
            metered = bool(self._is_metered())
        except Exception:  # noqa: BLE001 - not knowing means not metered
            metered = False
        return warm_candidates(current, before, after, settings=self._settings, metered=metered)
