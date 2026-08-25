"""Every route to "go and read the schedule again" (reported 2026-08-25).

*"the community feed is not refreshing... times were changed and I am not
seeing those"*, and then *"relaunching is not pulling a new set of data like it
is supposed to"* and *"there is already a refresh button that one can tab to as
well"*. The feed was right every time -- checked live against acbmedia.org, and
the cached copy was byte-identical to it. What was wrong was every way of
asking:

* the window honoured the hour-long cache when it opened, and the cache
  outlives the process, so relaunching re-read nothing;
* the context menu returned early with "No programme is selected", so the one
  moment you most want Refresh -- an empty or wrong-looking list -- was the one
  moment the menu would not offer it;
* there was no menu item at all, so the only route was a button inside a window
  you had to already be in;
* and a *successful* refresh changed not one word of the summary, so none of
  the above could be told apart from a fetch that had worked.

The window is not built here (it is modal, and the house pattern for this file
is to read the source it would run -- see test_calendar_play_button_label.py).
What is behavioural is pinned behaviourally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio"
_DIALOG = (_UI / "calendar_dialog.py").read_text(encoding="utf-8")
_WIRING = (_UI / "calendar_wiring.py").read_text(encoding="utf-8")


def test_opening_the_window_goes_and_asks_rather_than_trusting_the_hour() -> None:
    """ "Relaunching is not pulling a new set of data." It is now."""
    assert "self._load(refresh=True)" in _DIALOG
    assert "\n        self._load()\n" not in _DIALOG


def test_the_context_menu_no_longer_gives_up_when_nothing_is_selected() -> None:
    """The early return *was* the bug: no row, no menu, no Refresh."""
    popup = _DIALOG.split("def _popup(self)", 1)[1].split("\n    def ", 1)[0]
    body = popup.split('"""', 2)[-1]
    # Read past the docstring: it quotes the sentence the old menu announced,
    # which is exactly the string this asserts the *code* no longer contains.
    assert "No programme is selected" not in body
    assert "if event is not None:" in body
    assert "Re&fresh the Schedule" in body


def test_the_summary_is_told_when_this_copy_was_pulled() -> None:
    assert "pulled_at=self._pulled_at" in _DIALOG
    assert "self._pulled_at = datetime.now(UTC) - timedelta(seconds=age or 0.0)" in _DIALOG


def test_the_menu_route_reloads_an_open_window_rather_than_racing_it() -> None:
    """Refreshing the feed and leaving the window on the old rows would be the
    same bug in a new place."""
    assert "reload_open()" in _WIRING
    assert _WIRING.index("if reload_open():") < _WIRING.index("fetch_schedule(refresh=True)")


def test_the_menu_route_says_safe_mode_rather_than_doing_nothing() -> None:
    assert "Safe Mode is on, so the schedule is not re-read from ACB." in _WIRING


def test_reload_open_answers_false_when_no_schedule_is_open() -> None:
    from quill.ui.radio import calendar_dialog

    assert calendar_dialog.reload_open() is False


def test_reload_open_refreshes_the_window_that_is_open(monkeypatch) -> None:
    from quill.ui.radio import calendar_dialog

    refreshed: list[int] = []
    window = type("W", (), {"_refresh": lambda _self: refreshed.append(1)})()
    monkeypatch.setattr(calendar_dialog, "_OPEN", window)

    assert calendar_dialog.reload_open() is True
    assert refreshed == [1]


def test_a_window_closing_under_the_menu_does_not_break_the_menu(monkeypatch) -> None:
    """_OPEN is set from the modal path; a half-destroyed window must answer
    False rather than take the keystroke down with it."""
    from quill.ui.radio import calendar_dialog

    def _boom(_self: Any) -> None:
        raise RuntimeError("wrapped C/C++ object of type Dialog has been deleted")

    monkeypatch.setattr(calendar_dialog, "_OPEN", type("W", (), {"_refresh": _boom})())

    assert calendar_dialog.reload_open() is False


@pytest.mark.parametrize(
    "command", ["radio.acb_calendar", "radio.on_now", "radio.upcoming", "radio.refresh_calendar"]
)
def test_every_schedule_command_owns_a_key(command: str) -> None:
    from quill.core.app_keymaps import APP_KEYMAPS

    assert APP_KEYMAPS["radio"].get(command), f"{command} has no keyboard route"


def test_refresh_took_f5_because_f5_is_what_refresh_means() -> None:
    """Not a compromise: every Ctrl+Alt+Shift letter on this bar is claimed
    (the accelerator gate caught Ctrl+Alt+Shift+C colliding with Choose
    Columns), and F5 was completely unused in Quill Radio."""
    from quill.core.app_keymaps import APP_KEYMAPS

    assert APP_KEYMAPS["radio"]["radio.refresh_calendar"] == "F5"
