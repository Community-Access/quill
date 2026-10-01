"""QUILL Cast's status bar: what each cell says, and how the keyboard moves.

Driven with a fake host and a fake wx, which is the whole reason the readouts
live in :mod:`quill.ui.podcasts.status_bar_cells` as functions of a host: a bar
whose cells can only be tested with a real window is a bar whose cells are
never tested, and Radio's equivalent tests earned their keep twice (the record
cell's two different measurements, and the arrows that leaked focus out of the
bar because Up and Down were left to wxMSW).

Three things here are not "does the code run" but "did we keep a promise":
every cell carries authored help (GATE-CAST-HELP), no cell claims an access key
(GATE-14), and entering the bar says the region and nothing else (GATE-13).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.podcasts import status_bar_cells
from quill.ui.podcasts.status_bar import CastStatusBar, clamp_index


def _controller(
    *,
    state: object | None = None,
    volume_percent: int = 100,
    muted: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        state=state or SimpleNamespace(state=None, show_id=None, episode_guid=None),
        volume_percent=volume_percent,
        muted=muted,
    )


def _library(*, queue: list[object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        queue=list(queue or []),
        shows=[],
        settings=SimpleNamespace(speed=1.0, inbox_mode="include"),
    )


def _host(**overrides: object) -> SimpleNamespace:
    """A minimal host with the attributes the cells read, overridable per test."""
    base: dict[str, Any] = {
        "_wx": None,
        "_podcast_controller": _controller(),
        "_podcast_library": _library(),
        "_podcast_download_queue": SimpleNamespace(active_count=lambda: 0, snapshot=list),
        "_sleep_timer_controller": SimpleNamespace(
            is_active=False, is_end_of_episode=False, remaining_seconds=0
        ),
        "_shows_tree": None,
        "spoken": [],
    }
    base.update(overrides)
    host = SimpleNamespace(**base)
    host._announce = host.spoken.append  # type: ignore[attr-defined]
    return host


def _spec(bar: CastStatusBar, key: str):
    return next(spec for spec in bar._specs if spec.key == key)


def _label(bar: CastStatusBar, key: str) -> str:
    return bar._button_label(_spec(bar, key))


def _name(bar: CastStatusBar, key: str) -> str:
    return bar._button_name(_spec(bar, key))


# ---------------------------------------------------------------------------
# The cells, and what they say
# ---------------------------------------------------------------------------


def test_clamp_index_keeps_a_move_inside_the_bar() -> None:
    """Arrowing past either end must stop, not wrap and not raise.

    An empty bar clamps to 0 rather than raising, because ``build`` can be
    called before the specs are ready in a partially constructed window.
    """
    assert clamp_index(-3, 9) == 0
    assert clamp_index(99, 9) == 8
    assert clamp_index(4, 9) == 4
    assert clamp_index(4, 0) == 0


def test_the_nine_cells_appear_in_the_order_a_listening_session_does() -> None:
    """The order is the design: transport, loudness, speed, then what is next.

    Pinned because a cell inserted in the middle moves every cell to its right,
    and somebody who has learned that Downloads is four rights from Play should
    not silently find the sleep timer there instead.
    """
    keys = [spec.key for spec in CastStatusBar(_host())._specs]
    assert keys == [
        "play_pause",
        "mute",
        "volume",
        "speed",
        "queue",
        "inbox",
        "downloads",
        "sleep_timer",
        "clock",
    ]


def test_the_play_cell_label_is_the_verb_pressing_it_would_perform() -> None:
    """A button labelled with a readout promises an action it does not perform.

    Three labels rather than two: an episode keeps its place when paused, so
    "Resume" is a different promise from "Play" -- and it is what the main
    window's own transport button says in the same state.
    """
    from quill.ui.podcasts.player_controller import PodcastPlayerState

    stopped = CastStatusBar(_host())
    assert _label(stopped, "play_pause") == "Play"
    assert _name(stopped, "play_pause") == "Play (Ctrl+P)"

    for state, expected in (
        (PodcastPlayerState.PLAYING, "Pause"),
        (PodcastPlayerState.LOADING, "Pause"),
        (PodcastPlayerState.PAUSED, "Resume"),
        (PodcastPlayerState.STOPPED, "Play"),
        (PodcastPlayerState.ERROR, "Play"),
    ):
        bar = CastStatusBar(
            _host(_podcast_controller=_controller(state=SimpleNamespace(state=state)))
        )
        assert _label(bar, "play_pause") == expected


def test_the_mute_cell_label_flips_with_the_muted_state() -> None:
    """Same rule as Play: the label is the action, so it cannot go stale."""
    assert _label(CastStatusBar(_host()), "mute") == "Mute"
    muted = CastStatusBar(_host(_podcast_controller=_controller(muted=True, volume_percent=0)))
    assert _label(muted, "mute") == "Unmute"
    assert _name(muted, "mute") == "Unmute (Ctrl+Alt+M)"


def test_the_volume_cell_reads_the_controller_and_not_its_state_snapshot() -> None:
    """The bug this cell was one line away from shipping.

    Radio keeps volume and mute on the playback *state*; Cast keeps them on the
    controller (``player_volume.py``). Reading the wrong one would have given a
    cell that was silently always 100% and never said "Muted".
    """
    bar = CastStatusBar(_host(_podcast_controller=_controller(volume_percent=70)))
    assert _label(bar, "volume") == "Volume: 70%"
    assert _name(bar, "volume") == "Volume, 70%"

    muted = CastStatusBar(_host(_podcast_controller=_controller(muted=True)))
    assert _label(muted, "volume") == "Volume: Muted"

    # No player built yet: the bare cell name, never a fabricated 100%.
    assert _label(CastStatusBar(_host(_podcast_controller=None)), "volume") == "Volume"


def test_the_speed_cell_says_the_speed_a_listener_would_hear() -> None:
    """``1x`` and not ``1.00x``: a trailing zero is a syllable carrying nothing."""
    bar = CastStatusBar(_host())
    assert _label(bar, "speed") == "Speed: 1x"

    faster = _host(_podcast_library=_library())
    faster._podcast_library.settings.speed = 1.5
    assert _label(CastStatusBar(faster), "speed") == "Speed: 1.5x"


def test_a_readout_with_nothing_to_say_renders_as_the_bare_cell_name() -> None:
    """A zero is a number somebody reads before finding out there is nothing.

    Four cells at rest -- queue, Inbox, downloads, sleep timer -- and none of
    them costs a listener a number on the way past.
    """
    bar = CastStatusBar(_host())
    for key, name in (
        ("queue", "Queue"),
        ("inbox", "Inbox"),
        ("downloads", "Downloads"),
        ("sleep_timer", "Sleep timer"),
    ):
        assert _spec(bar, key).text() == ""
        assert _label(bar, key) == name


def test_the_queue_cell_counts_what_is_waiting_to_play() -> None:
    """The count is the whole value of the cell: a queue you cannot see the
    size of is one you have to open to trust."""
    bar = CastStatusBar(_host(_podcast_library=_library(queue=[object()] * 4)))
    assert _label(bar, "queue") == "Queue: 4"


def test_the_inbox_cell_counts_what_the_inbox_view_counts() -> None:
    """Through ``inbox_count``, so caps and Episode Filters are already applied.

    A cell that counted raw unplayed episodes would disagree with the list it
    claims to describe, and the listener would have no way to tell which was
    lying.
    """
    from quill.core.podcasts.models import PodcastEpisode, PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary

    library = PodcastLibrary()
    library.shows.append(
        PodcastShow(
            id="s1",
            title="The Daily",
            feed_url="https://e/f.xml",
            route_to_inbox=True,
            episodes=[
                PodcastEpisode(
                    guid=f"e{i}",
                    title=f"Episode {i}",
                    audio_url=f"https://e/{i}.mp3",
                    published="2026-07-01T00:00:00",
                )
                for i in range(3)
            ],
        )
    )
    bar = CastStatusBar(_host(_podcast_library=library))
    assert _label(bar, "inbox") == "Inbox: 3"


def test_the_downloads_cell_says_what_is_in_flight_and_what_is_behind_it() -> None:
    """ "2 of 7", because the number in flight is pinned at the concurrency limit.

    Somebody who has just queued a season wants evidence the queue is moving,
    and a bare "2" that never changes is the opposite of that.
    """
    queued = [SimpleNamespace(status="queued") for _ in range(5)]
    busy = _host(
        _podcast_download_queue=SimpleNamespace(
            active_count=lambda: 2, snapshot=lambda: [*queued, SimpleNamespace(status="done")]
        )
    )
    assert _label(CastStatusBar(busy), "downloads") == "Downloads: 2 of 7"

    # Paused, or waiting on the limit: the waiting count is still the news.
    paused = _host(
        _podcast_download_queue=SimpleNamespace(active_count=lambda: 0, snapshot=lambda: queued)
    )
    assert _label(CastStatusBar(paused), "downloads") == "Downloads: 5 waiting"


def test_a_download_queue_mid_teardown_empties_the_cell_rather_than_raising() -> None:
    """The cell repaints on a timer, so an exception here closes the window.

    Also covers every older fake: a queue object without ``snapshot`` must read
    as "nothing downloading", not as a crash on the next tick.
    """
    stale = _host(_podcast_download_queue=SimpleNamespace(active_count=lambda: 3))
    assert status_bar_cells.download_counts(stale) == (0, 0)
    assert _label(CastStatusBar(stale), "downloads") == "Downloads"


def test_the_sleep_timer_cell_counts_down_and_names_the_other_kind() -> None:
    """Two timers share one cell and the number cannot tell them apart.

    "End of episode" has no minutes to report, and reporting the episode's
    remaining time there would read as a clock timer somebody could extend.
    """
    ticking = _host(
        _sleep_timer_controller=SimpleNamespace(
            is_active=True, is_end_of_episode=False, remaining_seconds=90
        )
    )
    # 90 seconds rounds up: "1 min left" would be a lie for 30 of those seconds.
    assert _label(CastStatusBar(ticking), "sleep_timer") == "Sleep timer: 2 min left"

    last_minute = _host(
        _sleep_timer_controller=SimpleNamespace(
            is_active=True, is_end_of_episode=False, remaining_seconds=30
        )
    )
    assert _label(CastStatusBar(last_minute), "sleep_timer") == "Sleep timer: 1 min left"

    episode = _host(
        _sleep_timer_controller=SimpleNamespace(
            is_active=True, is_end_of_episode=True, remaining_seconds=0
        )
    )
    assert _label(CastStatusBar(episode), "sleep_timer") == "Sleep timer: End of episode"


def test_the_clock_cell_drops_the_leading_zero() -> None:
    """ "9:05 PM", not "09:05 PM": a reader says "oh nine" for the second one."""
    text = status_bar_cells.clock_text()
    assert text and not text.startswith("0")
    assert text.endswith(("AM", "PM"))


# ---------------------------------------------------------------------------
# What Enter does
# ---------------------------------------------------------------------------


def test_each_readout_cell_answers_enter_with_the_window_behind_it() -> None:
    """A readout that did nothing on Enter is a button that lies about itself.

    The four counting cells open the surface they are counting; the number is
    the summary and the window is the detail.
    """
    calls: list[str] = []
    host = _host()
    for method in (
        "_open_play_queue",
        "open_cast_inbox",
        "open_podcast_downloads",
        "open_sleep_timer_dialog",
    ):
        setattr(host, method, lambda m=method: calls.append(m))
    bar = CastStatusBar(host)
    for key in ("queue", "inbox", "downloads", "sleep_timer"):
        _spec(bar, key).activate()
    assert calls == [
        "_open_play_queue",
        "open_cast_inbox",
        "open_podcast_downloads",
        "open_sleep_timer_dialog",
    ]


def test_the_action_cells_answer_enter_with_the_transport_command() -> None:
    """The label is the action, so Enter must be that action and nothing else."""
    calls: list[str] = []
    host = _host(
        podcast_toggle_play_pause=lambda: calls.append("play"),
        podcast_mute_toggle=lambda: calls.append("mute"),
    )
    bar = CastStatusBar(host)
    _spec(bar, "play_pause").activate()
    _spec(bar, "mute").activate()
    assert calls == ["play", "mute"]


def test_enter_on_the_volume_cell_repeats_the_level_it_is_showing() -> None:
    """A readout has to answer Enter with something, and the something is itself.

    Nothing is playing is said in words rather than left silent: a key that
    does nothing is indistinguishable from a key that stopped working.
    """
    bar = CastStatusBar(_host(_podcast_controller=_controller(volume_percent=70)))
    _spec(bar, "volume").activate()
    assert bar._host.spoken == ["Volume 70%"]

    muted = CastStatusBar(_host(_podcast_controller=_controller(muted=True)))
    _spec(muted, "volume").activate()
    assert muted._host.spoken == ["Muted"]

    silent = CastStatusBar(_host(_podcast_controller=None))
    _spec(silent, "volume").activate()
    assert silent._host.spoken == ["Nothing is playing."]


def test_enter_on_the_speed_cell_says_the_scope_as_well_as_the_number() -> None:
    """The rule every speed verb in Cast follows, and the reason it exists.

    "1.5x" does not say whether the listener has just heard about one file, one
    podcast or everything, and somebody who cannot see which row is loaded has
    no other way to find out. With nothing playing the scope is the shared
    default, which is what "every podcast" says.
    """
    bar = CastStatusBar(_host())
    _spec(bar, "speed").activate()
    assert bar._host.spoken == ["Speed 1x for every podcast"]


def test_the_speed_hint_names_the_scope_too_so_f1_and_enter_agree() -> None:
    """Two ways of asking the same question must not give different answers."""
    spec = _spec(CastStatusBar(_host()), "speed")
    assert spec.live_help is not None
    assert "every podcast" in spec.live_help()


def test_the_downloads_hint_counts_both_halves_of_the_one_number() -> None:
    """The cell shows "2 of 7"; the hint says which part is which."""
    host = _host(
        _podcast_download_queue=SimpleNamespace(
            active_count=lambda: 2, snapshot=lambda: [SimpleNamespace(status="queued")] * 5
        )
    )
    spec = _spec(CastStatusBar(host), "downloads")
    assert spec.live_help is not None
    assert spec.live_help().startswith("2 downloading, 5 waiting.")


# ---------------------------------------------------------------------------
# The cell menus: what a right-click offers, and whether it does anything
# ---------------------------------------------------------------------------


class _FakeMenu:
    """A wx.Menu that records rows and can fire one, so a menu is testable.

    The point is the *binding*, not the label: a row that appends and never
    binds looks perfect in a screenshot and does nothing when pressed, which is
    exactly the shape of failure a label-only test cannot see.
    """

    def __init__(self) -> None:
        self.labels: list[str] = []
        self._ids: list[int | None] = []
        self._handlers: dict[int, Any] = {}
        self.destroyed = False

    def Append(self, item_id: int, label: str) -> None:  # noqa: N802 - wx shape
        self.labels.append(label)
        self._ids.append(int(item_id))

    def AppendSeparator(self) -> None:  # noqa: N802 - wx shape
        self.labels.append("-")
        self._ids.append(None)

    def Bind(self, _event: object, handler: Any, *, id: int) -> None:  # noqa: A002, N802
        self._handlers[int(id)] = handler

    def Destroy(self) -> None:  # noqa: N802 - wx shape
        self.destroyed = True

    def press(self, label: str) -> None:
        """Fire the row with this label, the way a click on it would."""
        item_id = self._ids[self.labels.index(label)]
        assert item_id is not None, label
        self._handlers[item_id](None)


class _MenuWx:
    """Just enough wx for a popup menu: ids, the EVT_MENU sentinel, and Menu()."""

    def __init__(self) -> None:
        self.EVT_MENU = object()
        self.menus: list[_FakeMenu] = []
        self._next_id = 1000

    def NewIdRef(self) -> int:  # noqa: N802 - wx shape
        self._next_id += 1
        return self._next_id

    def Menu(self) -> _FakeMenu:  # noqa: N802 - wx shape
        menu = _FakeMenu()
        self.menus.append(menu)
        return menu


def _menu_bar(**overrides: object) -> CastStatusBar:
    """A bar whose cells were built against a fake wx, so menus can be built.

    The wx goes on the *host*, because ``build_specs`` captures it once at
    construction -- which is the real wiring, and swapping it afterwards would
    test a shape the app never has.
    """
    return CastStatusBar(_host(_wx=_MenuWx(), **overrides))


def _built_menu(bar: CastStatusBar, key: str) -> _FakeMenu:
    menu = bar._wx.Menu()
    spec = _spec(bar, key)
    assert spec.build_menu is not None, key
    spec.build_menu(menu)
    return menu


def test_each_cell_menu_offers_the_actions_that_belong_to_that_cell() -> None:
    """A cell menu is where the rest of a cell's subject lives.

    Pinned per cell because the grouping is the design: the transport cell
    offers other things to play, the volume pair offers loudness and the output,
    and the counting cells offer what you do to the thing they count. A row that
    drifts to a neighbouring cell is a row nobody finds again.
    """
    bar = _menu_bar()
    assert _built_menu(bar, "play_pause").labels == [
        "Stop",
        "Next in Queue",
        "Previous in Queue",
        "Continue Listening...",
    ]
    assert _built_menu(bar, "volume").labels == [
        "Volume Up",
        "Volume Down",
        "Audio Output Mode",
        "Audio Output Device...",
    ]
    # The Mute cell shares the volume menu: two halves of one control.
    assert _built_menu(bar, "mute").labels == _built_menu(bar, "volume").labels
    assert _built_menu(bar, "speed").labels == [
        "Speed Up",
        "Speed Down",
        "Reset Speed",
        "Sound Enhancements...",
    ]
    assert _built_menu(bar, "queue").labels == [
        "Play Queue...",
        "Next in Queue",
        "Clear Entire Queue...",
    ]
    assert _built_menu(bar, "inbox").labels == ["Inbox...", "Mark All as Played..."]
    assert _built_menu(bar, "downloads").labels == [
        "Downloads...",
        "Pause All Downloads",
        "Resume All Downloads",
    ]


def test_a_menu_row_actually_calls_the_command_it_names() -> None:
    """The failure a labels-only test cannot see: appended but never bound."""
    calls: list[str] = []
    bar = _menu_bar(
        podcast_volume_up=lambda: calls.append("up"),
        podcast_choose_output_device=lambda: calls.append("device"),
    )
    menu = _built_menu(bar, "volume")
    menu.press("Volume Up")
    menu.press("Audio Output Device...")
    assert calls == ["up", "device"]


def test_the_sleep_timer_row_offers_to_change_a_timer_that_is_already_set() -> None:
    """One row, two jobs, and the label has to say which one it is doing.

    "Sleep Timer..." on a running timer reads as an offer to start one, which
    is the reverse of what somebody five minutes from sleep is looking for.
    """
    off = _menu_bar()
    assert _built_menu(off, "sleep_timer").labels[0] == "Sleep Timer..."

    running = _menu_bar(
        _sleep_timer_controller=SimpleNamespace(
            is_active=True, is_end_of_episode=False, remaining_seconds=300
        )
    )
    assert _built_menu(running, "sleep_timer").labels[0] == "Change Sleep Timer..."


def test_the_context_menu_leads_with_activate_and_ends_with_the_way_out() -> None:
    """Activate first because the cell is a button and the menu must not hide
    what pressing it would do -- least guessable on a readout, where "open the
    Inbox" cannot be inferred from a number. Hide Status Bar last because the
    bar has to be dismissable from the bar: somebody who met it by accident
    should not have to find the View menu to be rid of it.
    """
    calls: list[str] = []
    bar = _menu_bar(
        open_cast_inbox=lambda: calls.append("inbox"),
        _toggle_cast_status_bar=lambda: calls.append("hide"),
    )
    spec = _spec(bar, "inbox")
    buttons = [_PopupTarget() for _ in bar._specs]
    bar._cells = [
        SimpleNamespace(spec=s, button=b) for s, b in zip(bar._specs, buttons, strict=True)
    ]
    bar._on_context_menu(_FocusEvent(), spec)
    menu = bar._wx.menus[-1]
    assert buttons[5].popped == 1, "the menu pops over the cell, not over the panel"
    assert menu.labels == [
        "Activate",
        "-",
        "Inbox...",
        "Mark All as Played...",
        "-",
        "Hide Status Bar",
    ]
    menu.press("Activate")
    menu.press("Hide Status Bar")
    assert calls == ["inbox", "hide"]
    assert menu.destroyed, "a popup that is never destroyed leaks a menu per click"


class _PopupTarget:
    """A cell button that records having a menu popped over it."""

    def __init__(self) -> None:
        self.popped = 0

    def PopupMenu(self, _menu: _FakeMenu) -> None:  # noqa: N802 - wx shape
        self.popped += 1


def test_a_cell_action_that_raises_says_so_instead_of_taking_the_bar_down() -> None:
    """A dialog that cannot open is a sentence, not a closed window."""

    def boom() -> None:
        raise RuntimeError("no dialog today")

    bar = CastStatusBar(_host(_open_play_queue=boom))
    bar._activate(_spec(bar, "queue"))
    assert bar._host.spoken == ["Could not open Queue"]


def test_a_host_missing_a_command_is_a_silent_no_op_not_a_crash() -> None:
    """The bar is wired against a frame of a dozen mixins, and a cell that
    raised because one was not mixed in would close the window on a click."""
    bar = CastStatusBar(_host())
    _spec(bar, "play_pause").activate()  # the fake host has no transport at all
    assert bar._host.spoken == []


# ---------------------------------------------------------------------------
# The promises the gates check
# ---------------------------------------------------------------------------


def test_every_cell_carries_authored_help() -> None:
    """GATE-CAST-HELP: a control with no help answers F1 with the generic line.

    Held to a real sentence rather than merely non-empty: "Volume" as help text
    passes a null check and teaches nobody anything.
    """
    for spec in CastStatusBar(_host())._specs:
        assert spec.help.endswith("."), spec.key
        assert len(spec.help.split()) >= 8, spec.key


def test_no_cell_claims_an_access_key() -> None:
    """GATE-14: Windows cycles focus between duplicate mnemonics, never pressing.

    Cast's menu bar already claims most of the alphabet, so a cell with an "&"
    would be claiming a letter twice -- and the loser of that pair silently
    cannot be reached while nothing announces the loss. F6 and the arrows are
    the route in, and they collide with nothing.
    """
    bar = CastStatusBar(_host())
    for spec in bar._specs:
        assert "&" not in bar._button_label(spec), spec.key
        assert "&" not in bar._button_name(spec), spec.key
        assert "&" not in spec.name, spec.key
    rows = [
        row
        for key, value in vars(status_bar_cells).items()
        if key.endswith("_ROWS")
        for row in value
    ]
    assert rows, "the menu tables moved; this gate is now checking nothing"
    for label, _method in rows:
        assert "&" not in label, label


def test_entering_the_bar_announces_the_region_and_moving_inside_it_is_silent() -> None:
    """GATE-13: the reader already says the control, its role and its state.

    So F6 says "Status bar" -- the one fact a jump across the window leaves
    unanswered -- and every arrow press after it says nothing at all. Radio's
    bar speaks each cell's name on arrival; this is the one place the two
    deliberately differ, and the reason is that a name repeated over the
    reader's own is absorbed as "this app is chatty" and never filed.
    """
    bar, _panel, _focused = _bar_with_panel()
    spec = bar._specs[0]

    bar._entering = True
    bar._on_cell_focus(_FocusEvent(), spec)
    assert bar._host.spoken == ["Status bar"]

    bar._on_cell_focus(_FocusEvent(), bar._specs[1])
    bar._on_cell_focus(_FocusEvent(), bar._specs[2])
    assert bar._host.spoken == ["Status bar"], "arrowing inside the bar is silent"


def test_leaving_the_bar_hands_focus_to_the_library_tree_without_a_word() -> None:
    """The tree announces itself and the row focus lands on, so a sentence here
    would be the third time the listener is told where they are."""
    tree = _FocusTarget()
    bar, _panel, _focused = _bar_with_panel(_shows_tree=tree)
    bar._inside_bar = True
    bar._on_key_down(_KeyDownEvent(27), bar._specs[0])  # Escape
    assert tree.focused == 1
    assert bar._host.spoken == []
    assert not bar._inside_bar, "the visit closes so Tab skips the bar again"


def test_every_context_menu_row_names_a_command_this_app_has() -> None:
    """A menu row naming a method nobody wrote does nothing, silently.

    Checked against the mixins that actually supply Cast's commands rather than
    against the frame, so the test does not need a window. Two names are
    allowed to be absent because they are being written alongside this bar --
    the Inbox door the new View menu also opens, and Clear Entire Queue, whose
    core half has sat in ``core/podcasts/quick_plays.py`` with no caller at all.
    When either lands, this list shrinks; nothing else may join it.
    """
    from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
    from quill.ui.main_frame_podcast_session import PodcastSessionMixin
    from quill.ui.main_frame_podcasts import PodcastsMixin
    from quill.ui.podcasts.queue_commands import QueueRunCommandsMixin

    available: set[str] = set()
    for mixin in (
        PodcastsMixin,
        PodcastSessionMixin,
        MediaSleepTimerMixin,
        QueueRunCommandsMixin,
    ):
        available |= set(dir(mixin))
    rows = [
        row
        for key, value in vars(status_bar_cells).items()
        if key.endswith("_ROWS")
        for row in value
    ]
    missing = sorted({method for _label, method in rows if method not in available})
    assert missing == ["open_cast_inbox", "podcast_clear_entire_queue"]


# ---------------------------------------------------------------------------
# Keyboard navigation: one Tab stop, nine arrow stops
# ---------------------------------------------------------------------------


class _NavPanel:
    """Fake status panel that records Navigate() calls."""

    def __init__(self) -> None:
        self.navigations: list[int] = []

    def Navigate(self, flag: int) -> bool:  # noqa: N802 - wx shape
        self.navigations.append(flag)
        return True


class _FocusTarget:
    def __init__(self) -> None:
        self.focused = 0

    def SetFocus(self) -> None:  # noqa: N802 - wx shape
        self.focused += 1


class _FocusEvent:
    def __init__(self) -> None:
        self.skipped = False

    def Skip(self) -> None:  # noqa: N802 - wx shape
        self.skipped = True


class _KeyDownEvent:
    def __init__(self, code: int, *, shift: bool = False) -> None:
        self._code = code
        self._shift = shift
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx shape
        return self._code

    def ShiftDown(self) -> bool:  # noqa: N802 - wx shape
        return self._shift

    def Skip(self) -> None:  # noqa: N802 - wx shape
        self.skipped = True


def _wx_key_stub() -> SimpleNamespace:
    """The key codes ``_on_key_down`` compares against, plus the Navigate flags."""
    return SimpleNamespace(
        WXK_LEFT=314,
        WXK_UP=315,
        WXK_RIGHT=316,
        WXK_DOWN=317,
        WXK_HOME=313,
        WXK_END=312,
        WXK_TAB=9,
        WXK_ESCAPE=27,
        WXK_RETURN=13,
        WXK_NUMPAD_ENTER=370,
        WXK_SPACE=32,
        NavigationKeyEvent=SimpleNamespace(IsForward=1, IsBackward=0),
    )


def _bar_with_panel(**overrides: object) -> tuple[CastStatusBar, _NavPanel, list[str]]:
    focused: list[str] = []
    bar = CastStatusBar(_host(**overrides))
    bar._wx = _wx_key_stub()
    panel = _NavPanel()
    bar._panel = panel
    # Populate _cells so _cell_index() can resolve a spec to its real position:
    # build() needs live wx and is not called in these headless tests.
    bar._cells = [SimpleNamespace(spec=spec, button=object()) for spec in bar._specs]
    # _focus_cell is what "move cell to cell" would call -- spy on it so we can
    # prove Tab does not do that and the arrows do.
    bar._focus_cell = lambda index: focused.append(f"cell:{index}")  # type: ignore[method-assign]
    return bar, panel, focused


def test_all_four_arrows_move_cell_to_cell_and_none_of_them_escape() -> None:
    """Up and Down matter as much as Left and Right.

    An unhandled arrow in a TAB_TRAVERSAL panel is a navigation key on wxMSW,
    and in Quill Radio it walked focus clean out of the bar into the window
    behind it until Up and Down were consumed too. Nine cells is nine chances
    to leak.
    """
    bar, panel, focused = _bar_with_panel()
    spec = bar._specs[4]  # the queue cell, index 4
    right = _KeyDownEvent(316)
    left = _KeyDownEvent(314)
    down = _KeyDownEvent(317)
    up = _KeyDownEvent(315)
    for event in (right, left, down, up):
        bar._on_key_down(event, spec)
    assert focused == ["cell:5", "cell:3", "cell:5", "cell:3"]
    assert panel.navigations == [], "an arrow never leaves the bar"
    assert not any(event.skipped for event in (right, left, down, up))


def test_home_and_end_jump_to_the_ends_of_the_bar() -> None:
    """Nine cells is far enough that arrowing to the clock is a chore."""
    bar, _panel, focused = _bar_with_panel()
    spec = bar._specs[4]
    bar._on_key_down(_KeyDownEvent(313), spec)  # Home
    bar._on_key_down(_KeyDownEvent(312), spec)  # End
    assert focused == ["cell:0", "cell:8"]


def test_tab_leaves_the_bar_rather_than_stepping_through_nine_cells() -> None:
    """The whole bar is one Tab stop: nine extra stops is a cost paid on every
    pass through the window by somebody who only wanted the next button."""
    bar, panel, focused = _bar_with_panel()
    bar._inside_bar = True
    bar._on_key_down(_KeyDownEvent(9), bar._specs[0])
    assert panel.navigations == [1], "Tab hands off forward to the next control"
    assert focused == []
    assert not bar._inside_bar, "the visit closes first, or traversal re-enters the bar"


def test_shift_tab_leaves_the_bar_backwards() -> None:
    """The other half of the same contract; easy to bind and easy to forget."""
    bar, panel, focused = _bar_with_panel()
    bar._on_key_down(_KeyDownEvent(9, shift=True), bar._specs[0])
    assert panel.navigations == [0]
    assert focused == []


def test_enter_and_space_both_activate_the_focused_cell() -> None:
    """Space is how a screen-reader user presses a button, and it arrives here
    as a key rather than as EVT_BUTTON when the bar consumes the key first."""
    calls: list[str] = []
    bar, _panel, _focused = _bar_with_panel(podcast_toggle_play_pause=lambda: calls.append("play"))
    spec = bar._specs[0]
    for code in (13, 370, 32):  # Return, numpad Enter, Space
        bar._on_key_down(_KeyDownEvent(code), spec)
    assert calls == ["play", "play", "play"]


def test_the_bar_refuses_keyboard_focus_until_somebody_visits_it() -> None:
    """The flag ``AcceptsFocusFromKeyboard`` answers, and why it is not constant.

    A control that statically refuses keyboard focus on wxMSW also refuses
    ``SetFocus``, which is what left Radio's F6 doing nothing for a day. So the
    visit opens *before* focus is asked for, and closes when focus leaves.
    """
    bar, _panel, focused = _bar_with_panel()
    assert not bar._inside_bar
    bar.is_shown = lambda: True  # type: ignore[method-assign]
    bar.focus_bar(return_focus=_FocusTarget())
    assert bar._inside_bar
    assert focused == ["cell:0"]

    bar._on_cell_blur(SimpleNamespace(GetWindow=lambda: object(), Skip=lambda: None))
    assert not bar._inside_bar, "focus left the bar, so Tab skips it again"


def test_focus_moving_between_two_cells_keeps_the_visit_open() -> None:
    """Otherwise the next arrow's SetFocus is refused mid-walk -- the same
    wxMSW rule, hit from the other side."""
    bar, _panel, _focused = _bar_with_panel()
    bar._cells = [SimpleNamespace(spec=spec, button=_FocusTarget()) for spec in bar._specs]
    bar._inside_bar = True
    bar._on_cell_blur(SimpleNamespace(GetWindow=lambda: bar._cells[1].button, Skip=lambda: None))
    assert bar._inside_bar


def test_a_hidden_bar_cannot_be_focused() -> None:
    """F6 into an invisible bar would park focus where nothing is announced."""
    bar, _panel, focused = _bar_with_panel()
    bar.is_shown = lambda: False  # type: ignore[method-assign]
    bar.focus_bar()
    assert focused == []
    assert not bar._inside_bar
