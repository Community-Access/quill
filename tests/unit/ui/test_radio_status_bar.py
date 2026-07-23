"""Unit tests for the Radio status bar's pure text/navigation logic.

These drive ``RadioStatusBar`` with a fake host (no wx), exercising the cell
text functions and the clamp helper. The wx wiring (buttons, focus, context
menus) is covered by the app-level integration tests.
"""

from __future__ import annotations

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
        "_radio_recorder": SimpleNamespace(active_count=0),
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


def test_now_playing_falls_back_to_stopped() -> None:
    bar = RadioStatusBar(_host())
    assert _spec_text(bar, "now_playing") == "Stopped"

    playing = RadioStatusBar(_host(_radio_status_text=lambda: "Radio: playing Jazz"))
    assert _spec_text(playing, "now_playing") == "Radio: playing Jazz"


def test_volume_cell_reports_percent_mute_and_boost() -> None:
    assert _spec_text(RadioStatusBar(_host()), "volume") == "100%"

    muted = _host(
        _radio_controller=SimpleNamespace(state=SimpleNamespace(volume_percent=0, muted=True))
    )
    assert _spec_text(RadioStatusBar(muted), "volume") == "Muted"

    boosted = _host(_radio_history=SimpleNamespace(volume_boost=True))
    assert _spec_text(RadioStatusBar(boosted), "volume") == "100% (boosted)"


def test_recording_cell_counts_active_jobs() -> None:
    assert _spec_text(RadioStatusBar(_host()), "recording") == "Idle"
    one = _host(_radio_recorder=SimpleNamespace(active_count=1))
    assert _spec_text(RadioStatusBar(one), "recording") == "Recording"
    many = _host(_radio_recorder=SimpleNamespace(active_count=3))
    assert _spec_text(RadioStatusBar(many), "recording") == "3 recording"


def test_sleep_timer_cell_off_and_remaining() -> None:
    assert _spec_text(RadioStatusBar(_host()), "sleep_timer") == "Off"
    active = _host(_sleep_timer_controller=SimpleNamespace(is_active=True, remaining_seconds=90))
    # 90 s rounds up to 2 minutes left.
    assert _spec_text(RadioStatusBar(active), "sleep_timer") == "2 min left"


def test_favorites_cell_pluralizes() -> None:
    assert _spec_text(RadioStatusBar(_host()), "favorites") == "0 stations"
    one = _host(_radio_favorites=SimpleNamespace(favorites=[object()]))
    assert _spec_text(RadioStatusBar(one), "favorites") == "1 station"
    three = _host(_radio_favorites=SimpleNamespace(favorites=[object(), object(), object()]))
    assert _spec_text(RadioStatusBar(three), "favorites") == "3 stations"


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
        WXK_RIGHT=316,
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
    spec = bar._specs[2]  # the "recording" cell (index 2)
    bar._on_key_down(_KeyDownEvent(316), spec)  # Right
    bar._on_key_down(_KeyDownEvent(314), spec)  # Left
    assert focused == ["cell:3", "cell:1"], "arrows still move between cells"
    assert panel.navigations == [], "arrows never leave the bar"
