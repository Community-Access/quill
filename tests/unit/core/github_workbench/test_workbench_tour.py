"""The spoken tour of the GitHub Workbench (PRD D15, GH-R-115)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.core.github.workbench_prefs import WorkbenchPrefs
from quill.core.github.workbench_tour import TOUR_ID, TOUR_STEPS, TOUR_TITLE
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS
from quill.core.workbench.walk import Walk


def test_one_step_per_pane_in_f6_order_each_with_one_thing_to_do() -> None:
    panes = ("tree", "filter box", "list", "Details", "status bar")
    assert len(TOUR_STEPS) == len(panes)
    for step, pane in zip(TOUR_STEPS, panes, strict=True):
        assert pane in step
        assert "F6" in step  # how to go on
    assert WORKBENCH_KEYS["github.workbench.tour"] == "Alt+Shift+T"


def test_the_tour_is_a_walk_that_escape_can_stop() -> None:
    walk = Walk(TOUR_TITLE, TOUR_STEPS)
    assert "Escape stops" in walk.opening()
    for _ in TOUR_STEPS:
        walk.advance()
    assert walk.finished


class _Frame:
    def __init__(self) -> None:
        self.walks: list[tuple[str, tuple[str, ...]]] = []
        self._wx = SimpleNamespace(CallAfter=lambda fn, *args: fn(*args))
        self.tree = SimpleNamespace(SetFocus=lambda: None)

    def start_walk(self, title: str, _text: str, steps: tuple[str, ...]) -> None:
        self.walks.append((title, steps))


def _provider(frame: Any) -> Any:
    from quill.ui.github_workbench_tour import GitHubWorkbenchTourMixin

    provider = type("P", (GitHubWorkbenchTourMixin,), {})()
    provider.frame = frame
    return provider


def test_the_first_visit_tours_once_and_first_time_help_off_never(
    monkeypatch, tmp_path: Path
) -> None:
    from quill.core.github.workbench_tips import TipMoments

    monkeypatch.setattr("quill.core.github.workbench_tips.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("quill.core.github.workbench_prefs.load_prefs", lambda: WorkbenchPrefs())
    frame = _Frame()
    first = _provider(frame)
    first.maybe_first_tour()
    first.maybe_first_tour()
    assert frame.walks == [(TOUR_TITLE, TOUR_STEPS)]
    first._tip_moments.save()  # the window closed
    assert TOUR_ID in TipMoments.load(tmp_path / "github_workbench_tips.json").offered
    again = _Frame()
    _provider(again).maybe_first_tour()
    assert again.walks == []
    monkeypatch.setattr(
        "quill.core.github.workbench_prefs.load_prefs",
        lambda: WorkbenchPrefs(first_time_help=False),
    )
    (tmp_path / "github_workbench_tips.json").unlink()
    off = _Frame()
    _provider(off).maybe_first_tour()
    assert off.walks == []


def test_take_the_tour_always_starts_it() -> None:
    frame = _Frame()
    _provider(frame)._do_tour(None, None)
    assert frame.walks == [(TOUR_TITLE, TOUR_STEPS)]
