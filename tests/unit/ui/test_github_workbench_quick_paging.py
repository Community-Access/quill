"""A paged quick command runs behind Cancel, and says its outcome once (GX11).

The mixin over stubs: the progress window is a recorder, background work runs
inline, and "Cancel" is pressed by setting the stop the window was given.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.every_page import Paging, PagingStopped
from quill.core.github.quick_actions import Quick
from quill.ui.github_workbench_quick import GitHubWorkbenchQuickMixin


class _Window:
    def __init__(self, cancel: Any) -> None:
        self.cancel, self.counts, self.closed = cancel, [], 0

    def quietly(self, rows: int) -> None:
        self.counts.append(rows)

    def finish(self) -> None:
        self.closed += 1


class _Bench(GitHubWorkbenchQuickMixin):
    def __init__(self) -> None:
        self.said: list[str] = []
        self.shown: list[tuple[str, str]] = []
        self.windows: list[_Window] = []
        self.frame = None

    def github_api(self) -> Any:
        return object()

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _paging_window(self, _title: str, cancel: Any) -> _Window:
        self.windows.append(_Window(cancel))
        return self.windows[-1]

    def _quick_done(self, quick: Quick, said: str) -> None:
        self.shown.append((quick.label, said))


def _quick(paged: Any) -> Quick:
    return Quick(
        "q",
        "Security Overview",
        ("organization",),
        frozenset({"org"}),
        "help",
        (),
        lambda _a, _c: "",
        lambda data, _c: str(data),
        report=True,
        paged=paged,
    )


def test_a_finished_read_is_shown_once_and_the_window_closes() -> None:
    def paged(_api: Any, _ctx: dict[str, str], paging: Paging) -> str:
        paging.progress(100)
        paging.progress(150)
        return "Read every page: 150 alerts in 2 pages."

    bench = _Bench()
    bench._quick_ask(_quick(paged), {"org": "acme"})
    assert bench.shown == [("Security Overview", "Read every page: 150 alerts in 2 pages.")]
    assert bench.said == []  # nothing spoken while it read
    assert bench.windows[0].counts == [100, 150] and bench.windows[0].closed == 1


def test_cancel_stops_the_read_and_shows_no_partial_count() -> None:
    def paged(_api: Any, _ctx: dict[str, str], paging: Paging) -> str:
        bench.windows[0].cancel()  # the person presses Cancel during the read
        assert paging.should_cancel()
        raise PagingStopped(200, 2)

    bench = _Bench()
    bench._quick_ask(_quick(paged), {"org": "acme"})
    assert bench.shown == []
    assert bench.said == [
        "Stopped Security Overview after reading 200 entries. Nothing is shown, because part "
        "of the count would read as all of it."
    ]
    assert bench.windows[0].closed == 1
