"""Unit tests for the Audio Studio status bar's pure text/navigation logic.

These drive ``StudioStatusBar`` with a fake host (no wx), exercising the cell
text functions, the clamp helper, and the Tab-leaves / arrows-move navigation
contract. The wx wiring (buttons, focus, context menus) is covered by the
app-level integration tests.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.audio_studio.status_bar import StudioStatusBar, clamp_index


def _spec_text(bar: StudioStatusBar, key: str) -> str:
    spec = next(s for s in bar._specs if s.key == key)
    return spec.text()


def _host(**overrides: object) -> SimpleNamespace:
    """A minimal host with the accessor methods the cells read, overridable."""
    base: dict[str, object] = {
        "_wx": None,
        "studio_activity_text": lambda: "Ready",
        "studio_progress_text": lambda: "Idle",
        "studio_progress_details": lambda: "No task is running.",
        "studio_sleep_timer_text": lambda: "Off",
        "studio_library_text": lambda: "0 books",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_clamp_index_bounds() -> None:
    assert clamp_index(-3, 5) == 0
    assert clamp_index(9, 5) == 4
    assert clamp_index(2, 5) == 2
    # An empty bar clamps to 0 rather than raising.
    assert clamp_index(4, 0) == 0


def test_activity_cell_reads_the_host() -> None:
    bar = StudioStatusBar(_host(studio_activity_text=lambda: "Narrating chapter 3"))
    assert _spec_text(bar, "activity") == "Narrating chapter 3"


def test_progress_cell_reports_idle_and_running() -> None:
    assert _spec_text(StudioStatusBar(_host()), "progress") == "Idle"
    running = _host(studio_progress_text=lambda: "42% - Narrating documents")
    assert _spec_text(StudioStatusBar(running), "progress") == "42% - Narrating documents"


def test_sleep_and_library_cells_read_the_host() -> None:
    host = _host(
        studio_sleep_timer_text=lambda: "2 min left",
        studio_library_text=lambda: "1 book",
    )
    bar = StudioStatusBar(host)
    assert _spec_text(bar, "sleep_timer") == "2 min left"
    assert _spec_text(bar, "library") == "1 book"


def test_expected_cells_are_present_in_order() -> None:
    keys = [spec.key for spec in StudioStatusBar(_host())._specs]
    assert keys == ["activity", "progress", "sleep_timer", "library", "clock"]


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


def _bar_with_panel() -> tuple[StudioStatusBar, _NavPanel, list[str]]:
    focused: list[str] = []
    bar = StudioStatusBar(_host())
    bar._wx = _wx_key_stub()
    panel = _NavPanel()
    bar._panel = panel
    bar._cells = [SimpleNamespace(spec=spec, button=object()) for spec in bar._specs]
    bar._focus_cell = lambda index: focused.append(f"cell:{index}")  # type: ignore[method-assign]
    return bar, panel, focused


def test_tab_navigates_out_of_the_bar_forward() -> None:
    bar, panel, focused = _bar_with_panel()
    bar._on_key_down(_KeyDownEvent(9), bar._specs[0])  # Tab
    assert panel.navigations == [1], "Tab hands off forward to the next control"
    assert focused == [], "Tab must not move cell to cell"


def test_shift_tab_navigates_out_of_the_bar_backward() -> None:
    bar, panel, focused = _bar_with_panel()
    bar._on_key_down(_KeyDownEvent(9, shift=True), bar._specs[0])  # Shift+Tab
    assert panel.navigations == [0], "Shift+Tab hands off backward to the previous control"
    assert focused == []


def test_arrow_keys_still_move_cell_to_cell() -> None:
    bar, panel, focused = _bar_with_panel()
    spec = bar._specs[2]  # the "sleep_timer" cell (index 2)
    bar._on_key_down(_KeyDownEvent(316), spec)  # Right
    bar._on_key_down(_KeyDownEvent(314), spec)  # Left
    assert focused == ["cell:3", "cell:1"], "arrows still move between cells"
    assert panel.navigations == [], "arrows never leave the bar"
