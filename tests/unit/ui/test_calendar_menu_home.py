"""Where the ACB Media schedule lives on the menu bar (moved 2026-08-24).

It was on Station, on the argument that a schedule is about what is *on*. But
Station is the menu of everything Quill Radio can tune and it had grown past
twenty items, while the Community menu is precisely "places this community
already goes, brought inside the app" -- which is what an ACB Media schedule
is. It now sits beside ACB Community Events.

Two things have to hold, and only one of them is placement:

* the three items go on whichever menu they are handed, fenced by a separator
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
        keys = {
            "radio.acb_calendar": "Ctrl+Shift+N",
            "radio.on_now": "Ctrl+Alt+H",
            "radio.upcoming": "Ctrl+Alt+Shift+F",
        }
        return f"{title}\t{keys[command_id]}"

    def _keep_menu_ids(self, *refs: Any) -> None:
        self.kept.extend(refs)


@pytest.fixture
def host():
    frame = wx.Frame(None)
    yield _Host(frame)
    frame.Destroy()


def test_the_three_items_land_on_the_menu_they_are_given(host) -> None:
    community = wx.Menu()

    calendar_wiring.append_menu_items(host, community, wx)

    labels = [item.GetItemLabel() for item in community.GetMenuItems()]
    assert any("Schedule" in label for label in labels)
    assert any("Now" in label for label in labels)
    assert any("Upcoming" in label for label in labels)


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
