"""Unit tests for the Radio status bar's pure text/navigation logic.

These drive ``RadioStatusBar`` with a fake host (no wx), exercising the cell
text functions and the clamp helper. The wx wiring (buttons, focus, context
menus) is covered by the app-level integration tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from quill.ui.radio.status_bar import RadioStatusBar, clamp_index


def _spec_text(bar: RadioStatusBar, key: str) -> str:
    spec = next(s for s in bar._specs if s.key == key)
    return spec.text()


def _host(**overrides: object) -> SimpleNamespace:
    """A minimal host with the attributes the cells read, overridable per test."""
    base: dict[str, object] = {
        "_wx": None,
        "_radio_status_text": lambda: "",
        "_radio_controller": SimpleNamespace(
            state=SimpleNamespace(volume_percent=100, muted=False)
        ),
        "_radio_recorder": SimpleNamespace(active_count=0, active_jobs=list),
        "_sleep_timer_controller": SimpleNamespace(is_active=False, remaining_seconds=0),
        "_radio_favorites": SimpleNamespace(favorites=[]),
        "_radio_history": SimpleNamespace(volume_boost=False),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_clamp_index_bounds() -> None:
    assert clamp_index(-3, 5) == 0
    assert clamp_index(9, 5) == 4
    assert clamp_index(2, 5) == 2
    # An empty bar clamps to 0 rather than raising.
    assert clamp_index(4, 0) == 0


def _spec(bar: RadioStatusBar, key: str):
    return next(s for s in bar._specs if s.key == key)


def test_the_bar_leads_with_actions_and_dropped_the_readout_cells() -> None:
    # 2026-08-23 redesign: a bar of buttons leads with actions. The
    # now-playing readout (a "button that says stopped") and the favorites
    # count ("Favorites 1 button") came off; Play/Stop and Mute/Unmute came on.
    bar = RadioStatusBar(_host())
    keys = [s.key for s in bar._specs]
    assert keys == ["play_stop", "mute", "volume", "recording", "sleep_timer", "clock"]


def test_play_stop_cell_label_is_the_action_it_would_perform() -> None:
    from quill.ui.radio.playback_state import RadioPlayerState

    stopped = RadioStatusBar(_host())
    assert stopped._button_label(_spec(stopped, "play_stop")) == "Play"
    assert stopped._button_name(_spec(stopped, "play_stop")) == "Play (Ctrl+P)"

    playing = RadioStatusBar(
        _host(
            _radio_controller=SimpleNamespace(
                state=SimpleNamespace(
                    state=RadioPlayerState.PLAYING, volume_percent=80, muted=False
                )
            )
        )
    )
    assert playing._button_label(_spec(playing, "play_stop")) == "Stop"


def test_mute_cell_label_follows_the_muted_state() -> None:
    bar = RadioStatusBar(_host())
    assert bar._button_label(_spec(bar, "mute")) == "Mute"
    muted = RadioStatusBar(
        _host(
            _radio_controller=SimpleNamespace(state=SimpleNamespace(volume_percent=0, muted=True))
        )
    )
    assert muted._button_label(_spec(muted, "mute")) == "Unmute"
    assert muted._button_name(_spec(muted, "mute")) == "Unmute (Ctrl+M)"


def test_record_cell_says_the_verb_and_wears_the_progress() -> None:
    idle = RadioStatusBar(_host())
    assert idle._button_label(_spec(idle, "recording")) == "Record Now"
    running = RadioStatusBar(_host(_radio_recorder=_recorder(_job(18, 60, requested=True))))
    assert running._button_label(_spec(running, "recording")) == "Stop Recording (42 min left)"


def test_volume_cell_reports_percent_mute_and_boost() -> None:
    assert _spec_text(RadioStatusBar(_host()), "volume") == "100%"

    muted = _host(
        _radio_controller=SimpleNamespace(state=SimpleNamespace(volume_percent=0, muted=True))
    )
    assert _spec_text(RadioStatusBar(muted), "volume") == "Muted"

    boosted = _host(_radio_history=SimpleNamespace(volume_boost=True))
    assert _spec_text(RadioStatusBar(boosted), "volume") == "100% (boosted)"


def _recorder(*jobs: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(active_count=len(jobs), active_jobs=lambda: list(jobs))


def _job(minutes_ago: int, minutes: int, requested: bool) -> SimpleNamespace:
    return SimpleNamespace(
        started_at=datetime.now() - timedelta(minutes=minutes_ago),
        minutes=minutes,
        duration_requested=requested,
    )


def test_record_label_counts_active_jobs_and_says_how_long() -> None:
    # A capture with a length the listener chose counts down to it...
    one = _host(_radio_recorder=_recorder(_job(18, 60, requested=True)))
    assert RadioStatusBar(one)._label_record() == "Stop Recording (42 min left)"
    # ...and one started with Record Now counts up, because its `minutes` is a
    # disk-safety cap rather than a plan. See core.radio.recording_progress.
    open_ended = _host(_radio_recorder=_recorder(_job(18, 180, requested=False)))
    assert RadioStatusBar(open_ended)._label_record() == "Stop Recording (18 min so far)"
    many = _host(
        _radio_recorder=_recorder(
            _job(18, 60, requested=True),
            _job(5, 30, requested=True),
            _job(2, 180, requested=False),
        )
    )
    assert RadioStatusBar(many)._label_record() == "Stop Recording (3 recordings, 25 min left)"


def test_a_recorder_without_job_snapshots_degrades_to_record_now() -> None:
    """A cell repainted on a timer must never take the bar down.

    A recorder mid-teardown (and any older fake) has no ``active_jobs``, and the
    only acceptable answer to that is a quiet one.
    """
    stale = _host(_radio_recorder=SimpleNamespace(active_count=2))
    assert RadioStatusBar(stale)._label_record() == "Record Now"


def test_the_recording_hint_follows_what_the_cell_is_showing() -> None:
    bar = RadioStatusBar(_host(_radio_recorder=_recorder(_job(18, 60, requested=True))))
    spec = next(s for s in bar._specs if s.key == "recording")
    assert spec.live_help is not None
    assert "counts down" in spec.live_help()


def test_sleep_timer_cell_off_and_remaining() -> None:
    assert _spec_text(RadioStatusBar(_host()), "sleep_timer") == "Off"
    active = _host(_sleep_timer_controller=SimpleNamespace(is_active=True, remaining_seconds=90))
    # 90 s rounds up to 2 minutes left.
    assert _spec_text(RadioStatusBar(active), "sleep_timer") == "2 min left"


# ---------------------------------------------------------------------------
# Tab navigation: the whole bar is one Tab stop, not one-per-cell.
# Arrow keys move cell to cell; Tab / Shift+Tab leave the bar.
# ---------------------------------------------------------------------------


class _NavPanel:
    """Fake status panel that records Navigate() calls."""

    def __init__(self) -> None:
        self.navigations: list[int] = []

    def Navigate(self, flag: int) -> bool:  # noqa: N802 - wx shape
        self.navigations.append(flag)
        return True


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
    # The key codes _on_key_down compares against, plus the Navigate flags.
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


def _bar_with_panel() -> tuple[RadioStatusBar, _NavPanel, list[str]]:
    focused: list[str] = []
    bar = RadioStatusBar(_host())
    bar._wx = _wx_key_stub()
    panel = _NavPanel()
    bar._panel = panel
    # Populate _cells so _cell_index() can resolve a spec to its real position
    # (build() -- which needs live wx -- is not called in these headless tests).
    bar._cells = [SimpleNamespace(spec=spec, button=object()) for spec in bar._specs]
    # _focus_cell is what "move cell to cell" would call -- spy on it so we can
    # prove Tab no longer does that.
    bar._focus_cell = lambda index: focused.append(f"cell:{index}")  # type: ignore[method-assign]
    return bar, panel, focused


def test_tab_navigates_out_of_the_bar_forward() -> None:
    bar, panel, focused = _bar_with_panel()
    spec = bar._specs[0]
    bar._on_key_down(_KeyDownEvent(9), spec)  # Tab
    assert panel.navigations == [1], "Tab hands off forward to the next control"
    assert focused == [], "Tab must not move cell to cell any more"


def test_shift_tab_navigates_out_of_the_bar_backward() -> None:
    bar, panel, focused = _bar_with_panel()
    spec = bar._specs[0]
    bar._on_key_down(_KeyDownEvent(9, shift=True), spec)  # Shift+Tab
    assert panel.navigations == [0], "Shift+Tab hands off backward to the previous control"
    assert focused == []


def test_arrow_keys_still_move_cell_to_cell() -> None:
    # Regression guard: the Tab change must not disturb Left/Right cell movement.
    bar, panel, focused = _bar_with_panel()
    spec = bar._specs[2]  # the "volume" cell (index 2)
    bar._on_key_down(_KeyDownEvent(316), spec)  # Right
    bar._on_key_down(_KeyDownEvent(314), spec)  # Left
    assert focused == ["cell:3", "cell:1"], "arrows still move between cells"
    assert panel.navigations == [], "arrows never leave the bar"


def test_up_and_down_arrows_are_consumed_and_move_cells_too() -> None:
    # 2026-08-23: an unhandled Up/Down in a TAB_TRAVERSAL panel is a
    # navigation key on wxMSW -- it walked focus out of the bar into the main
    # window's now-playing readout. All four arrows must be consumed.
    bar, panel, focused = _bar_with_panel()
    spec = bar._specs[2]
    up = _KeyDownEvent(315)  # WXK_UP
    down = _KeyDownEvent(317)  # WXK_DOWN
    bar._on_key_down(down, spec)
    bar._on_key_down(up, spec)
    assert focused == ["cell:3", "cell:1"], "Up and Down move between cells like Left and Right"
    assert not up.skipped and not down.skipped, "consumed -- never handed to wx navigation"
    assert panel.navigations == []
