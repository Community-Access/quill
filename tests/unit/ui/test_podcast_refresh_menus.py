"""The Refresh verbs on the podcast rows, in both apps (list.md 1.7).

Refresh on a *show* answers "anything new in this one?" and already worked in
both apps -- Quill Radio re-reads the feed when you open the show, QUILL Cast
has Refresh Feed on the show menu, and neither skips a paused show. What had no
answer at all was the other question: **anything new anywhere?** Short of the
automatic check, which is off by default, the only way to ask it was to open
every show in turn.

So both apps grew a "Check All Feeds Now" verb on the rows above a show -- the
Subscriptions branch and its folders in Radio, the folder and library rows in
Cast -- and both pass ``force=True``, which is what makes them answer for
paused shows and ignore the "the other app just checked" stamp.

These are wiring tests. The behaviour behind the verb is pinned in
test_radio_podcast_refresh.py, test_podcast_check_force.py and
test_podcast_check_monitor_policy.py; what is checked here is that the verbs
exist on the rows, that they reach a monitor, and that they force.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.radio import row_actions
from quill.ui.radio import browse_podcast_actions

REPO = Path(__file__).resolve().parents[3]


class _Monitor:
    def __init__(self, started: int = 3) -> None:
        self.calls: list[bool] = []
        self._started = started

    def check_now(self, *, force: bool = False, **_kwargs: Any) -> int:
        self.calls.append(force)
        return self._started


class _Dialog:
    def __init__(self, host: Any = None) -> None:
        self._download_host = host
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


# -- Quill Radio: the rows ------------------------------------------------------


def _labels(actions) -> list[str]:
    return [action.label for action in actions]


def _ids(actions) -> list[str]:
    return [action.id for action in actions]


def test_the_subscriptions_branch_offers_it() -> None:
    actions = row_actions.folder_actions("mypodcasts", row_actions.FolderState())
    assert row_actions.REFRESH_ALL_PODCASTS in _ids(actions)


def test_a_podcast_folder_offers_it() -> None:
    actions = row_actions.folder_actions("mypodcastfolder", row_actions.FolderState())
    assert row_actions.REFRESH_ALL_PODCASTS in _ids(actions)


def test_the_verb_advertises_a_keyboard_letter_nobody_else_claims() -> None:
    """A row verb is reached by a letter, not only by arrowing down to it."""
    for kind in ("mypodcasts", "mypodcastfolder"):
        actions = row_actions.folder_actions(kind, row_actions.FolderState())
        letters = [label.split("&", 1)[1][0].lower() for label in _labels(actions) if "&" in label]
        assert len(letters) == len(set(letters)), f"{kind} claims a letter twice"
        assert "k" in letters


def test_a_show_row_still_offers_plain_refresh() -> None:
    """Refresh on a show is the per-show question and must not have moved."""
    state = row_actions.FolderState(is_podcast_show=True, subscribed=True)
    assert row_actions.REFRESH in _ids(row_actions.folder_actions("mypodcastshow", state))


def test_an_episode_shelf_is_not_offered_a_library_wide_check() -> None:
    """The verb belongs above a show, not on one and not on a station folder."""
    for kind in ("mypodcastshow", "favorites", "popular"):
        actions = row_actions.folder_actions(kind, row_actions.FolderState())
        assert row_actions.REFRESH_ALL_PODCASTS not in _ids(actions)


# -- Quill Radio: the handler ---------------------------------------------------


def test_it_forces_and_says_it_started() -> None:
    monitor = _Monitor()
    host = type("_Host", (), {"_podcast_refresh_monitor": monitor})()
    dialog = _Dialog(host)

    browse_podcast_actions.refresh_all_feeds(dialog)

    assert monitor.calls == [True]
    assert dialog.said == ["Checking subscribed feeds..."]


def test_the_same_tree_inside_quill_finds_casts_monitor() -> None:
    """One tree, two apps, two names for the thing that does the checking."""
    monitor = _Monitor()
    host = type("_Host", (), {"_podcast_check_monitor": monitor})()
    dialog = _Dialog(host)

    browse_podcast_actions.refresh_all_feeds(dialog)

    assert monitor.calls == [True]


def test_no_monitor_says_so_rather_than_doing_nothing() -> None:
    dialog = _Dialog(object())

    browse_podcast_actions.refresh_all_feeds(dialog)

    assert dialog.said == ["Subscribed feeds cannot be checked right now."]


# -- QUILL Cast -----------------------------------------------------------------


def test_cast_offers_the_verb_on_its_tree() -> None:
    source = (REPO / "quill" / "ui" / "podcasts" / "manager_dialog.py").read_text(encoding="utf-8")
    assert "Chec&k All Feeds Now" in source
    assert "self._on_check_all_feeds()" in source


def test_casts_handler_forces() -> None:
    from quill.ui.podcasts.manager_actions import ManagerActionsMixin

    monitor = _Monitor()

    class _Manager(ManagerActionsMixin):
        _transport_host = type("_Host", (), {"_podcast_check_monitor": monitor})()
        _safe_mode = False

        def __init__(self) -> None:
            self.said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    manager = _Manager()
    manager._on_check_all_feeds()

    assert monitor.calls == [True]
    # The count up front: this verb's result arrives show by show, so
    # "checking three feeds" is what says when it is finished.
    assert manager.said == ["Checking 3 feeds..."]


def test_casts_handler_says_so_when_there_is_no_feed_to_check() -> None:
    from quill.ui.podcasts.manager_actions import ManagerActionsMixin

    monitor = _Monitor(started=0)

    class _Manager(ManagerActionsMixin):
        _transport_host = type("_Host", (), {"_podcast_check_monitor": monitor})()
        _safe_mode = False

        def __init__(self) -> None:
            self.said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    manager = _Manager()
    manager._on_check_all_feeds()

    assert manager.said == ["No subscribed feed to check."]


def test_casts_handler_refuses_in_safe_mode() -> None:
    from quill.ui.podcasts.manager_actions import ManagerActionsMixin

    monitor = _Monitor()

    class _Manager(ManagerActionsMixin):
        _transport_host = type("_Host", (), {"_podcast_check_monitor": monitor})()
        _safe_mode = True

        def __init__(self) -> None:
            self.said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    manager = _Manager()
    manager._on_check_all_feeds()

    assert monitor.calls == []
    assert manager.said == ["Subscribed feeds cannot be checked right now."]


def test_casts_show_menu_still_offers_refresh_feed_on_a_paused_show() -> None:
    """A pause must never mean unreachable, which is what makes it safe."""
    source = (REPO / "quill" / "ui" / "podcasts" / "manager_menus.py").read_text(encoding="utf-8")
    refresh = source[source.index('"refresh"') : source.index('"toggle_favorite"')]
    # Dimmed only for a show with no feed at all, or in Safe Mode -- never for
    # a pause. A row that could not be refreshed would be a row you could
    # strand with one keystroke.
    assert "paused" not in refresh


# -- the standalone app could not reach the setting at all ----------------------


def test_standalone_cast_falls_back_to_its_own_history_record() -> None:
    """The monitor asked for ``self.settings``, which standalone Cast has not.

    So ``podcast_check_enabled`` read as False forever and the background check
    was unreachable in that app -- a whole feature with no route to it.
    """
    source = (REPO / "quill" / "ui" / "main_frame_podcasts.py").read_text(encoding="utf-8")
    provider = source[source.index("settings_provider=") : source.index("library_provider=")]
    assert "_podcast_history" in provider


def test_standalone_cast_offers_the_setting_in_preferences() -> None:
    source = (REPO / "quill" / "apps" / "podcasts.py").read_text(encoding="utf-8")
    assert "history.podcast_check_enabled" in source
    assert "history.podcast_check_interval_minutes" in source
    # Re-applied on save, so a cadence you just chose is the one that is
    # running -- not the one that will be running after the next launch.
    assert "monitor.apply()" in source
