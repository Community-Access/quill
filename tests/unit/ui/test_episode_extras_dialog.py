"""**About This Episode** -- tabs that exist, and a button that names itself.

The two things this window can get wrong are both invisible in a screenshot: a
tab that is there but empty, and a button that says OK on a row it cannot act
on. Both are pinned here against a real wx window.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.podcasts.extras import build  # noqa: E402
from quill.core.podcasts.namespace_tags import parse  # noqa: E402
from quill.ui.podcasts.episode_extras_dialog import (  # noqa: E402
    NOTHING_HEADING,
    EpisodeExtrasDialog,
)

_SHOW = (
    '<channel><podcast:person role="Host">Alice Adams</podcast:person>'
    '<podcast:podroll><podcast:remoteItem feedUrl="https://one.example/feed"/>'
    "</podcast:podroll></channel>"
)
_EPISODE = (
    '<item><podcast:soundbite startTime="60" duration="30">The good bit</podcast:soundbite></item>'
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make(parent, **kwargs):
    extras = build(show_tags=parse(_SHOW), episode_tags=parse(_EPISODE), show_title="The Show")
    return EpisodeExtrasDialog(parent, extras=extras, episode_title="Ep 1", **kwargs)


def test_a_tab_exists_only_when_it_has_something_in_it(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = _make(frame)
    try:
        titles = [
            dialog._notebook.GetPageText(index) for index in range(dialog._notebook.GetPageCount())
        ]
        # No Live, Support, Other Audio or Place tabs: this feed published none.
        assert titles == ["People", "Highlights", "Recommended"]
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_the_button_is_named_from_the_highlighted_row(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = _make(frame, subscribe_feed=lambda _url: True)
    try:
        # A person with no link: the control says so rather than declining later.
        assert dialog._action_btn.GetLabel() == "Nothing to Open"
        assert dialog._action_btn.IsEnabled() is False
        dialog._notebook.SetSelection(2)
        dialog._sync_button()
        assert dialog._action_btn.GetLabel() == "&Subscribe to This Podcast"
        assert dialog._action_btn.IsEnabled() is True
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_a_row_with_no_handler_is_disabled_rather_than_silently_declining(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = _make(frame)  # no subscribe_feed supplied
    try:
        dialog._notebook.SetSelection(2)
        dialog._sync_button()
        assert dialog._action_btn.IsEnabled() is False
        assert dialog.activate_selected() is False
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_activating_a_row_reports_the_outcome_either_way(wx_app) -> None:
    frame = wx.Frame(None)
    said: list[str] = []
    dialog = _make(frame, subscribe_feed=lambda _url: False, announce=said.append)
    try:
        dialog._notebook.SetSelection(2)
        dialog._sync_button()
        assert dialog.activate_selected() is False
        assert said and "could not be opened" in said[-1]
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_a_podcast_that_published_nothing_still_gets_a_window_that_says_so(wx_app) -> None:
    # "Publishes no extra details" and "cannot read them" are different facts,
    # and a greyed-out menu item cannot tell somebody which one it is.
    frame = wx.Frame(None)
    dialog = EpisodeExtrasDialog(frame, extras=build())
    try:
        assert dialog._notebook is None
        assert dialog.selected_row() is None
        assert "no extra details" in NOTHING_HEADING
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_the_dialog_is_registered_in_the_inventory() -> None:
    inventory = json.loads(
        (Path(__file__).parent / "fixtures" / "dialog_inventory.json").read_text(encoding="utf-8")
    )
    key = "quill/ui/podcasts/episode_extras_dialog.py::EpisodeExtrasDialog.__init__::wx.Dialog"
    assert key in inventory
