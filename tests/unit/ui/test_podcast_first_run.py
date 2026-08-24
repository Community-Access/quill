"""QUILL Cast's first-run flow, and the caller it went two releases without.

The dialog was written, tested and never once shown: nothing in the app ever
called it. Quill Radio's equivalent carries a docstring naming that as the
failure it exists not to repeat -- and it had gone on being true, which is the
particular way a well-tested feature can be entirely absent.

So the assertions here are as much about the wiring as the flow. A test that
only exercised `FirstRunDialog` would have passed for two releases while
nobody could reach it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.podcasts.onboarding import OnboardingState
from quill.ui.podcasts.first_run_dialog import maybe_run_first_run

wx = pytest.importorskip("wx")

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Library:
    def __init__(self, shows: int = 0) -> None:
        self.shows = list(range(shows))


class _History:
    def __init__(self, state: OnboardingState | None = None) -> None:
        self.onboarding = state if state is not None else OnboardingState()


class _Host:
    def __init__(self, *, shows: int = 0, state: OnboardingState | None = None) -> None:
        self.frame = wx.Frame(None)
        # Shown, because the flow refuses over a window that is not on screen:
        # a deferred modal with nothing behind it is a hang, not a welcome.
        self.frame.Show()
        self._podcast_history = _History(state)
        self._podcast_library = _Library(shows)
        self.said: list[str] = []
        self.saves = 0
        self.shown: list[str] = []
        self.add_opened = 0

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _save_podcast_history(self) -> None:
        self.saves += 1

    def _show_modal_dialog(self, dialog: Any, title: str) -> int:
        """Stand in for the hardened modal path without opening a window."""
        self.shown.append(title)
        return wx.ID_OK

    def _podcast_open_add_dialog(self) -> None:
        self.add_opened += 1


# -- when it runs ---------------------------------------------------------------


def test_a_new_listener_is_welcomed_and_the_choice_is_saved() -> None:
    host = _Host()

    assert maybe_run_first_run(host) is True

    assert host.shown == ["Welcome to QUILL Cast"]
    assert host._podcast_history.onboarding.completed_first_run is True
    assert host.saves == 1


def test_somebody_who_already_has_podcasts_is_left_alone() -> None:
    """However they got there -- an import, a restored setup, an upgrade.

    Explaining how to add a first podcast to somebody with two hundred is a
    way of saying nobody checked.
    """
    host = _Host(shows=200)

    assert maybe_run_first_run(host) is False
    assert host.shown == []
    assert host.saves == 0


def test_it_runs_once() -> None:
    host = _Host(state=OnboardingState(completed_first_run=True))
    assert maybe_run_first_run(host) is False


def test_skipping_still_counts_as_done() -> None:
    """Somebody who skipped chose to; showing it again would override that."""
    host = _Host()
    host._show_modal_dialog = lambda _d, _t: wx.ID_CANCEL  # type: ignore[method-assign]

    assert maybe_run_first_run(host) is True
    assert host._podcast_history.onboarding.completed_first_run is True


# -- when it must not ------------------------------------------------------------


def test_a_frame_that_was_never_shown_gets_no_welcome() -> None:
    host = _Host()
    host.frame.Hide()

    assert maybe_run_first_run(host) is False
    assert host.shown == []


def test_a_host_with_nothing_it_needs_is_refused_rather_than_crashing() -> None:
    """A welcome must never take an app down on its very first launch."""

    class _Bare:
        frame = None

    assert maybe_run_first_run(_Bare()) is False


def test_a_host_whose_history_has_no_onboarding_state_is_refused() -> None:
    host = _Host()
    host._podcast_history = object()  # type: ignore[assignment]

    assert maybe_run_first_run(host) is False


# -- the wiring, which is the part that was missing -------------------------------


def test_the_app_actually_calls_it() -> None:
    """The whole bug: a dialog nothing invoked."""
    source = (REPO / "quill" / "apps" / "podcasts.py").read_text(encoding="utf-8")
    assert "maybe_run_first_run" in source
    assert "wx.CallAfter(maybe_run_first_run, self)" in source


def test_the_launch_path_shows_the_window_before_it_runs_the_loop() -> None:
    """The shown-frame guard is only safe because a launch shows it first."""
    source = (REPO / "quill" / "apps" / "podcasts.py").read_text(encoding="utf-8")
    assert source.index("frame.frame.Show()") < source.index("app.MainLoop()")


def test_the_state_survives_a_restart() -> None:
    """A welcome that ran and was forgotten would run again every launch."""
    import tempfile

    from quill.core.podcasts.history import PodcastHistory, load_history, save_history

    with tempfile.TemporaryDirectory() as raw:
        data_dir = Path(raw)
        history = PodcastHistory()
        history.onboarding.completed_first_run = True
        history.onboarding.seen_tips.add("inbox")
        history.onboarding.tips_enabled = False
        save_history(data_dir, history)

        back = load_history(data_dir)
        assert back.onboarding.completed_first_run is True
        assert back.onboarding.seen_tips == {"inbox"}
        assert back.onboarding.tips_enabled is False


def test_an_older_history_file_reads_as_never_welcomed() -> None:
    """Upgrading is not a first launch -- but the shows check catches that."""
    import json
    import tempfile

    from quill.core.podcasts.history import load_history

    with tempfile.TemporaryDirectory() as raw:
        data_dir = Path(raw)
        (data_dir / "podcast_history.json").write_text(
            json.dumps({"resume_on_launch": True}), encoding="utf-8"
        )
        assert load_history(data_dir).onboarding.completed_first_run is False
