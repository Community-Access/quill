"""Unit tests for the shared companion-app close flow (AppShellFrame).

``handle_app_close`` + ``_run_close_confirm`` are the one close path Quill Radio,
Quill Cast, and Audio Studio all share. The rule they enforce: never ShowModal
from inside an EVT_CLOSE handler (unreliable on wxMSW -- it made Alt+F4 do
nothing while work was running); veto and run the confirm dialog deferred via
CallAfter instead. These drive the methods directly with a fake host -- no wx
app, no real dialog.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.app_shell import AppShellFrame


def _host(*, close_action: str = "ask", exit_requested: bool = False) -> Any:
    deferred: list[tuple[Any, tuple[Any, ...]]] = []
    calls: list[str] = []
    host = SimpleNamespace(
        _closing_in_progress=False,
        _exit_requested=exit_requested,
        _wx=SimpleNamespace(CallAfter=lambda fn, *a: deferred.append((fn, a))),
        frame=SimpleNamespace(Close=lambda: calls.append("frame.Close")),
        _send_to_tray=lambda: calls.append("send_to_tray"),
    )
    host._deferred = deferred  # type: ignore[attr-defined]
    host._calls = calls  # type: ignore[attr-defined]
    host._close_action = close_action  # type: ignore[attr-defined]
    # handle_app_close schedules self._run_close_confirm; give the fake host the
    # real shared implementation bound to it.
    host._run_close_confirm = lambda confirm: AppShellFrame._run_close_confirm(host, confirm)
    return host


def _event() -> tuple[Any, list[bool], list[bool]]:
    skipped: list[bool] = []
    vetoed: list[bool] = []
    event = SimpleNamespace(Skip=lambda: skipped.append(True), Veto=lambda: vetoed.append(True))
    return event, skipped, vetoed


def _shutdown(host: Any) -> None:
    host._calls.append("shutdown")


def test_reentrant_close_is_vetoed_and_does_nothing() -> None:
    host = _host()
    host._closing_in_progress = True
    event, skipped, vetoed = _event()

    AppShellFrame.handle_app_close(
        host,
        event,
        close_action="ask",
        protected=True,
        confirm=lambda: "exit",
        shutdown=lambda: _shutdown(host),
    )

    assert vetoed == [True] and skipped == []
    assert host._calls == [] and host._deferred == []


def test_ask_with_nothing_protected_closes_straight_away() -> None:
    host = _host()
    event, skipped, vetoed = _event()

    AppShellFrame.handle_app_close(
        host,
        event,
        close_action="ask",
        protected=False,
        confirm=lambda: "exit",
        shutdown=lambda: _shutdown(host),
    )

    assert host._calls == ["shutdown"], "nothing to protect -> exit like a normal window"
    assert skipped == [True] and vetoed == []
    assert host._deferred == [], "no dialog scheduled"


def test_ask_with_protected_work_defers_the_confirm() -> None:
    host = _host()
    confirm = lambda: "exit"  # noqa: E731
    event, skipped, vetoed = _event()

    AppShellFrame.handle_app_close(
        host,
        event,
        close_action="ask",
        protected=True,
        confirm=confirm,
        shutdown=lambda: _shutdown(host),
    )

    assert vetoed == [True] and skipped == []
    assert host._closing_in_progress is True, "guard held until the deferred dialog finishes"
    assert host._calls == [], "no shutdown, no modal from inside EVT_CLOSE"
    assert len(host._deferred) == 1
    fn, args = host._deferred[0]
    assert fn == host._run_close_confirm and args == (confirm,)


def test_minimize_preference_vetoes_and_goes_to_tray() -> None:
    host = _host(close_action="minimize")
    event, skipped, vetoed = _event()

    AppShellFrame.handle_app_close(
        host,
        event,
        close_action="minimize",
        protected=True,
        confirm=lambda: "exit",
        shutdown=lambda: _shutdown(host),
    )

    assert vetoed == [True] and skipped == []
    assert host._calls == ["send_to_tray"], "minimize tucks to the tray, no shutdown"


def test_exit_requested_bypasses_ask_and_minimize() -> None:
    # A deliberate menu/tray Exit closes for real even with close_action minimize.
    host = _host(close_action="minimize", exit_requested=True)
    event, skipped, vetoed = _event()

    AppShellFrame.handle_app_close(
        host,
        event,
        close_action="minimize",
        protected=True,
        confirm=lambda: "exit",
        shutdown=lambda: _shutdown(host),
    )

    assert host._exit_requested is False, "the one-shot flag is consumed"
    assert host._calls == ["shutdown"] and skipped == [True] and vetoed == []


def test_run_close_confirm_cancel_keeps_open_and_resets_guard() -> None:
    host = _host()
    host._closing_in_progress = True

    AppShellFrame._run_close_confirm(host, lambda: None)

    assert host._calls == [], "cancel does nothing"
    assert host._closing_in_progress is False


def test_run_close_confirm_minimize_goes_to_tray() -> None:
    host = _host()
    host._closing_in_progress = True

    AppShellFrame._run_close_confirm(host, lambda: "minimize")

    assert host._calls == ["send_to_tray"]
    assert host._closing_in_progress is False


def test_run_close_confirm_exit_reenters_close_deliberately() -> None:
    host = _host()
    host._closing_in_progress = True

    AppShellFrame._run_close_confirm(host, lambda: "exit")

    assert host._exit_requested is True, "re-enters the close path as a deliberate Exit"
    assert host._calls == ["frame.Close"]
    assert host._closing_in_progress is False


def test_run_close_confirm_resets_guard_when_confirm_raises() -> None:
    host = _host()
    host._closing_in_progress = True

    def _boom() -> str:
        raise RuntimeError("boom")

    try:
        AppShellFrame._run_close_confirm(host, _boom)
    except RuntimeError:
        pass

    assert host._closing_in_progress is False, "a crash must not wedge the app closed"
