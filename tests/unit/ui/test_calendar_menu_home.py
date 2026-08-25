"""Where the ACB Media schedule lives on the menu bar (moved 2026-08-24).

It was on Station, on the argument that a schedule is about what is *on*. But
Station is the menu of everything Quill Radio can tune and it had grown past
twenty items, while the Community menu is precisely "places this community
already goes, brought inside the app" -- which is what an ACB Media schedule
is. It now sits beside ACB Community Events.

Two things have to hold, and only one of them is placement:

* the four items go on whichever menu they are handed, fenced by a separator
  only when there is something above to fence off -- a profile with the ADP
  assistant switched off gets a Community menu that opens on the schedule
  rather than on a rule;
* every item still advertises a keyboard route, which the accelerator gate
  checks across the whole bar but which is worth pinning here too, because the
  move is exactly the kind of change that drops a label's key.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.app_keymaps import APP_KEYMAPS  # noqa: E402
from quill.ui.radio import calendar_wiring  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Host:
    """Just enough of the app for a menu block to be built against."""

    def __init__(self, frame: Any) -> None:
        self.frame = frame
        self.kept: list[Any] = []

    def _menu_label(self, title: str, command_id: str) -> str:
        # Read from the real keymap rather than a copy of it. A local dict got
        # this test to pass while the fourth item had no binding at all, which
        # is the failure the accelerator rule exists to catch.
        return f"{title}\t{APP_KEYMAPS['radio'][command_id]}"

    def _keep_menu_ids(self, *refs: Any) -> None:
        self.kept.extend(refs)


@pytest.fixture
def host():
    frame = wx.Frame(None)
    yield _Host(frame)
    frame.Destroy()


def test_the_four_items_land_on_the_menu_they_are_given(host) -> None:
    community = wx.Menu()

    calendar_wiring.append_menu_items(host, community, wx)

    labels = [item.GetItemLabel() for item in community.GetMenuItems()]
    assert any("Schedule" in label for label in labels)
    assert any("Now" in label for label in labels)
    assert any("Upcoming" in label for label in labels)
    # GetItemLabelText, not GetItemLabel: the mnemonic sits inside the word
    # ("Re&fresh"), so the raw label does not contain "Refresh" at all.
    texts = [item.GetItemLabelText() for item in community.GetMenuItems()]
    assert any("Refresh" in text for text in texts)


def test_refresh_is_reachable_without_opening_the_schedule_first(host) -> None:
    """The bug it fixes: the only Refresh was a button *inside* the window,
    and the hour-long cache outlived the process, so relaunching the app
    re-read nothing (2026-08-25)."""
    community = wx.Menu()

    calendar_wiring.append_menu_items(host, community, wx)

    refresh = [i for i in community.GetMenuItems() if "Refresh" in i.GetItemLabelText()]
    assert len(refresh) == 1
    assert "\t" in refresh[0].GetItemLabel()


def test_every_schedule_item_advertises_a_key(host) -> None:
    community = wx.Menu()

    calendar_wiring.append_menu_items(host, community, wx)

    for item in community.GetMenuItems():
        assert "\t" in item.GetItemLabel(), f"{item.GetItemLabel()} has no keyboard route"


def test_an_empty_community_menu_opens_on_the_schedule_not_a_separator(host) -> None:
    """A separator at the top of a menu is a row a screen reader still lands on."""
    from quill.apps.radio_launch_tasks import append_calendar_menu

    community = wx.Menu()

    append_calendar_menu(host, community, wx)

    assert community.GetMenuItems()[0].IsSeparator() is False


def test_a_populated_community_menu_gets_its_separator(host) -> None:
    from quill.apps.radio_launch_tasks import append_calendar_menu

    community = wx.Menu()
    community.Append(wx.NewIdRef(), "Ask the Audio Description Project...\tCtrl+Alt+Shift+Q")

    append_calendar_menu(host, community, wx)

    assert community.GetMenuItems()[1].IsSeparator() is True
