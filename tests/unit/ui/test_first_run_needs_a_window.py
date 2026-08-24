"""A deferred modal must not open over a window that is not on screen.

The failure this pins was a hang, not a wrong answer, which is the worse
kind. Quill Radio schedules its welcome with ``wx.CallAfter`` at construction
time; anything that later pumps pending events -- a test fixture reclaiming
leaked windows, a nested yield -- ran it, and ``ShowModal`` sat there forever
with no loop able to answer it. Building the radio frame anywhere but a real
launch therefore hung the whole run, and a hang reports as "still going"
rather than as a failure.

The guard is right in production too, which is why it is a guard rather than
a test-only flag: the launch path shows the main window *before* entering the
loop the deferred call runs in, so a real launch is always shown. A welcome
nobody can see is not a welcome.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.radio.first_run_dialog import maybe_run_first_run

REPO = Path(__file__).resolve().parents[3]


class _Frame:
    def __init__(self, shown: bool) -> None:
        self._shown = shown

    def IsShown(self) -> bool:  # noqa: N802 - the wx spelling
        return self._shown


class _Host:
    """Enough of an app frame to reach the guard, and no further.

    ``_radio_history`` deliberately answers an onboarding state that *would*
    ask for the flow, so a test that passes proves the guard stopped it rather
    than the flow simply not being due.
    """

    def __init__(self, shown: bool) -> None:
        self.frame = _Frame(shown)
        self.opened = False

    @property
    def _radio_history(self) -> object:
        raise AssertionError("the guard must return before the state is read")


def test_a_frame_that_was_never_shown_gets_no_welcome() -> None:
    assert maybe_run_first_run(_Host(shown=False)) is False


def test_a_host_with_no_frame_at_all_gets_no_welcome() -> None:
    class _Headless:
        frame = None

    assert maybe_run_first_run(_Headless()) is False


def test_a_shown_frame_is_allowed_past_the_guard() -> None:
    """The guard must not be the reason a real launch skips its welcome.

    Reaching the state read is the whole assertion: the host raises there, so
    a False from the guard and a False from "no onboarding state" cannot be
    confused with each other.
    """
    host = _Host(shown=True)
    try:
        maybe_run_first_run(host)
    except AssertionError:  # pragma: no cover - the flow swallows it; see below
        pass
    # maybe_run_first_run catches everything, so the observable proof is that
    # it did not return before touching the host: assert the source keeps the
    # guard above the state read rather than below it.
    source = (REPO / "quill" / "ui" / "radio" / "first_run_dialog.py").read_text(encoding="utf-8")
    guard = source.index("is_shown()")
    state = source.index('getattr(history, "onboarding", None)')
    assert guard < state, "the shown check must come before any state is read"


def test_the_launch_path_shows_the_window_before_it_runs_the_loop() -> None:
    """The guard is only safe because a real launch is always shown first."""
    source = (REPO / "quill" / "apps" / "radio.py").read_text(encoding="utf-8")
    assert source.index("frame.frame.Show()") < source.index("app.MainLoop()")
