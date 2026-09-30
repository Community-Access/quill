"""Enter on a notification, and what happens when it cannot be followed.

The bug this closes: every notification the 3.1.0 feed check raised carried a
show id, both Open and Enter called an ``open_notification_target`` **no app
implemented**, and the window answered "There is nothing to open for this one"
every single time. The list was a log.

So the tests worth having are about the failures as much as the success. A
refusal that says nothing is the same experience as the bug -- a listener
presses Enter, hears one sentence that means "no", and has no idea whether the
show is gone, the branch is hidden, or the feature never worked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import notification_targets
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import load_library, new_id, save_library
from quill.ui import notification_open

FEED = "https://feeds.example/show"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    return tmp_path


def _seed(data_dir: Path) -> str:
    library = load_library(data_dir)
    show = PodcastShow(id=new_id(), title="The Allusionist", feed_url=FEED)
    library.add_show(show)
    save_library(data_dir, library)
    return show.id


class _Said:
    """A stand-in for ``_announce`` that remembers what it was told.

    A callable object rather than a list subclass: the hosts resolve their
    voice with ``getattr(host, "_announce", None) or _silence``, and an empty
    list is falsy -- a double that starts out empty would be replaced by the
    fallback and record nothing at all.
    """

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, message: str) -> None:
        self.lines.append(message)


# -- resolving ---------------------------------------------------------------


def test_a_live_subscription_resolves(data_dir: Path) -> None:
    show_id = _seed(data_dir)
    show, refusal = notification_open.resolve_show(notification_targets.for_show(show_id))
    assert refusal == ""
    assert show is not None and show.feed_url == FEED


def test_a_notice_written_before_targets_were_prefixed_still_resolves(data_dir: Path) -> None:
    """The bare show id 3.1.0 first wrote. These are in people's files now."""
    show_id = _seed(data_dir)
    show, refusal = notification_open.resolve_show(show_id)
    assert refusal == ""
    assert show is not None


def test_an_unsubscribed_show_says_so_rather_than_opening_something_else(data_dir: Path) -> None:
    """A notice outlives its subscription: days can pass before somebody reads
    the list, and unsubscribing in Quill Cast is enough."""
    show, refusal = notification_open.resolve_show("show:gone")
    assert show is None
    assert "not in your subscriptions" in refusal


def test_a_notice_with_no_target_reads_as_nothing_to_open(data_dir: Path) -> None:
    show, refusal = notification_open.resolve_show("")
    assert show is None
    assert refusal == notification_open.NOTHING_TO_OPEN


def test_a_station_target_is_not_opened_as_a_podcast(data_dir: Path) -> None:
    """Reminders will write these. Until something follows them, the honest
    answer is "nothing to open" -- never the wrong row."""
    target = notification_targets.for_stream("https://stream.example/live")
    show, refusal = notification_open.resolve_show(target)
    assert show is None
    assert refusal == notification_open.NOTHING_TO_OPEN


# -- Quill Radio's door -------------------------------------------------------


class _RadioHost:
    """Enough of the app frame for the door: a browse window and a voice."""

    def __init__(self, *, dialog: object = None, returns: object = None) -> None:
        self._announce = _Said()
        self._radio_browse_dialog = dialog
        self._returns = returns
        self.opened = 0

    def open_browse_stations(self) -> object:
        self.opened += 1
        return self._returns


def test_radio_opens_browse_and_reveals_the_show(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    show_id = _seed(data_dir)
    revealed: list[tuple[object, str]] = []
    monkeypatch.setattr(
        "quill.ui.radio.browse_reveal.open_to_show",
        lambda dialog, feed: (revealed.append((dialog, feed)), True)[1],
    )
    window = object()
    host = _RadioHost(returns=window)

    notification_open.open_in_radio(host, notification_targets.for_show(show_id))

    assert host.opened == 1
    assert revealed == [(window, FEED)]
    assert host._announce.lines == []  # the window moving IS the answer (GATE-13)


def test_radio_uses_the_window_it_already_had(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``open_browse_stations`` answers None when it brought an existing window
    to the front instead of building a second copy -- the dialog is still on
    the frame, and that is the one to reveal in."""
    show_id = _seed(data_dir)
    seen: list[object] = []
    monkeypatch.setattr(
        "quill.ui.radio.browse_reveal.open_to_show",
        lambda dialog, _feed: (seen.append(dialog), True)[1],
    )
    existing = object()
    host = _RadioHost(dialog=existing, returns=None)

    notification_open.open_in_radio(host, notification_targets.for_show(show_id))
    assert seen == [existing]


def test_radio_says_why_when_the_branch_is_switched_off(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Subscriptions can be hidden in Choose Browse Sources, and then there is
    no row to land on. Naming the setting is the difference between a refusal
    and a dead end."""
    show_id = _seed(data_dir)
    monkeypatch.setattr("quill.ui.radio.browse_reveal.open_to_show", lambda *_a: False)
    host = _RadioHost(returns=object())

    notification_open.open_in_radio(host, notification_targets.for_show(show_id))

    assert len(host._announce.lines) == 1
    spoken = host._announce.lines[0]
    assert "The Allusionist" in spoken
    assert "Choose Browse Sources" in spoken


def test_radio_never_opens_a_window_for_a_show_that_is_gone(data_dir: Path) -> None:
    host = _RadioHost(returns=object())
    notification_open.open_in_radio(host, "show:gone")
    assert host.opened == 0
    assert "not in your subscriptions" in host._announce.lines[0]


# -- QUILL Cast's door --------------------------------------------------------


class _CastHost:
    def __init__(self) -> None:
        self._announce = _Said()
        self.kept: list[object] = []

    def _reload_library_tree(self, *, keep_key: object = None) -> None:
        self.kept.append(keep_key)


def test_cast_lands_the_cursor_on_the_show(data_dir: Path) -> None:
    show_id = _seed(data_dir)
    host = _CastHost()
    notification_open.open_in_cast(host, notification_targets.for_show(show_id))
    assert host.kept == [("show", show_id)]
    assert host._announce.lines == []


def test_cast_says_so_when_the_show_has_gone(data_dir: Path) -> None:
    host = _CastHost()
    notification_open.open_in_cast(host, "show:gone")
    assert host.kept == []
    assert "not in your subscriptions" in host._announce.lines[0]


def test_a_host_without_a_tree_refuses_rather_than_raising(data_dir: Path) -> None:
    show_id = _seed(data_dir)

    class _Bare:
        def __init__(self) -> None:
            self._announce = _Said()

    host = _Bare()
    notification_open.open_in_cast(host, notification_targets.for_show(show_id))
    assert host._announce.lines[-1] == notification_open.NOTHING_TO_OPEN


# -- the wiring that was missing ---------------------------------------------


def test_both_apps_answer_the_name_the_notification_centre_calls() -> None:
    """The bug was not a broken handler -- it was no handler. The centre calls
    ``open_notification_target`` on its host and falls through to "nothing to
    open" when the attribute is absent, which is exactly what shipped."""
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.apps.radio import RadioAppFrame

    for frame in (RadioAppFrame, PodcastsAppFrame):
        assert callable(getattr(frame, "open_notification_target", None)), frame.__name__
