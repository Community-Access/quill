"""The welcome runs for a new listener, once, and for nobody else.

The check that matters most here is the last group. QUILL Cast's equivalent
dialog was written, tested and wired to **nothing** -- ``FirstRunDialog`` has
no caller anywhere in the tree, so no Cast user has ever seen it. A first-run
flow with no trigger is indistinguishable from no first-run flow, so these
drive ``maybe_run_first_run`` rather than only the dialog class.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.radio.onboarding import FIRST_RUN_SCREENS, RadioOnboardingState
from quill.ui.radio import first_run_dialog
from quill.ui.radio.first_run_dialog import RadioFirstRunDialog, maybe_run_first_run


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Favorites:
    def __init__(self, count: int = 0) -> None:
        self.favorites = list(range(count))


class _History:
    def __init__(self, state: RadioOnboardingState | None = None) -> None:
        self.onboarding = state if state is not None else RadioOnboardingState()


class _Host:
    def __init__(self, *, favorites: int = 0, state: RadioOnboardingState | None = None) -> None:
        self.frame = wx.Frame(None)
        self._radio_history = _History(state)
        self._radio_favorites = _Favorites(favorites)
        self.said: list[str] = []
        self.saves = 0
        self.shown: list[str] = []
        self.browsed = 0

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _binding_for(self, command_id: str) -> str | None:
        return {"radio.browse": "Ctrl+B"}.get(command_id)

    def _save_radio_history(self) -> None:
        self.saves += 1

    def _show_modal_dialog(self, dialog: Any, title: str) -> int:
        """Stand in for the hardened modal path without opening a window."""
        self.shown.append(title)
        return wx.ID_OK

    def open_internet_radio(self, **_kw: Any) -> None:
        self.browsed += 1


# -- when it runs --------------------------------------------------------------


def test_a_new_listener_is_welcomed_and_the_choice_is_saved() -> None:
    host = _Host()

    assert maybe_run_first_run(host) is True

    assert host.shown == ["Welcome to Quill Radio"]
    assert host._radio_history.onboarding.completed_first_run is True
    assert host.saves == 1


def test_somebody_with_favorites_is_left_alone() -> None:
    host = _Host(favorites=12)

    assert maybe_run_first_run(host) is False
    assert host.shown == []


def test_it_does_not_come_back_on_the_second_launch() -> None:
    host = _Host()
    maybe_run_first_run(host)
    host.shown.clear()

    assert maybe_run_first_run(host) is False
    assert host.shown == []


def test_a_host_that_is_not_a_radio_is_survivable() -> None:
    class _Bare:
        pass

    assert maybe_run_first_run(_Bare()) is False


def test_a_failure_inside_the_flow_does_not_break_the_launch(monkeypatch) -> None:
    # The worst possible first impression is a crash on the first launch.
    def _boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("no display")

    monkeypatch.setattr(first_run_dialog, "RadioFirstRunDialog", _boom)
    host = _Host()

    assert maybe_run_first_run(host) is False


# -- the screens themselves ----------------------------------------------------


def _dialog(host: _Host, **kw: Any) -> RadioFirstRunDialog:
    return RadioFirstRunDialog(
        host.frame,
        state=host._radio_history.onboarding,
        announce=host._announce,
        resolve_key=lambda command_id: host._binding_for(command_id) or "",
        **kw,
    )


def test_the_first_screen_announces_where_you_are_in_the_flow() -> None:
    host = _Host()
    dialog = _dialog(host)
    try:
        assert host.said[-1] == f"Welcome to Quill Radio. Screen 1 of {len(FIRST_RUN_SCREENS)}."
    finally:
        dialog.dialog.Destroy()


def test_the_screen_teaches_the_key_that_is_actually_bound() -> None:
    host = _Host()
    dialog = _dialog(host)
    try:
        assert "Ctrl+B" in dialog._body.GetValue()
        assert "{" not in dialog._body.GetValue()
    finally:
        dialog.dialog.Destroy()


def test_back_is_dead_on_the_first_screen_and_alive_after_it() -> None:
    host = _Host()
    dialog = _dialog(host)
    try:
        assert dialog._back_btn.IsEnabled() is False
        dialog.go(1)
        assert dialog._back_btn.IsEnabled() is True
    finally:
        dialog.dialog.Destroy()


def test_the_last_screen_says_finish_rather_than_next() -> None:
    host = _Host()
    dialog = _dialog(host)
    try:
        dialog.go(1)
        dialog.go(1)
        assert dialog._next_btn.GetLabel() == "&Finish"
    finally:
        dialog.dialog.Destroy()


def test_browse_is_offered_only_once_the_flow_has_pointed_at_it() -> None:
    host = _Host()
    dialog = _dialog(host, on_browse=host.open_internet_radio)
    try:
        assert dialog._browse_btn.IsShown() is False
        dialog.go(1)
        assert dialog._browse_btn.IsShown() is True
    finally:
        dialog.dialog.Destroy()


def test_taking_browse_counts_as_onboarded() -> None:
    # Somebody who went and found a station has been onboarded, whatever screen
    # they were on when they left.
    host = _Host()
    dialog = _dialog(host, on_browse=host.open_internet_radio)
    try:
        dialog.go(1)
        dialog.browse()
        assert host.browsed == 1
        assert host._radio_history.onboarding.completed_first_run is True
    finally:
        dialog.dialog.Destroy()


def test_the_tips_switch_is_carried_out_of_the_flow() -> None:
    host = _Host()
    dialog = _dialog(host)
    try:
        dialog._tips_check.SetValue(False)
        dialog.finish()
        assert host._radio_history.onboarding.tips_enabled is False
    finally:
        dialog.dialog.Destroy()
