"""Episode Filters, wired: the menu verbs, the list, and the refresh.

The rules themselves are pinned in
``tests/unit/core/podcasts/test_episode_filters.py``. What is pinned here is
everything the UI is responsible for and the core cannot check:

* the podcast menu offers Episode Filters, and the episode menu offers the
  per-episode exemption -- dimmed, with a reason, when there is no filter;
* the episode list hides what the library scope hides and **Filtered out**
  shows exactly that, so nothing is ever unreachable;
* a refresh asks each route for its own scope, so "keep it out of the queue
  but still tell me" is a thing somebody can actually have;
* the window titles both resolve to authored F1 help (GATE-CAST-HELP scans
  for the titles; this asserts they mean something).

No wx is constructed: the dialogs are stubbed at their import sites, exactly
as ``test_cast_single_settings.py`` does, because what is being tested is the
wiring and not wxPython.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.podcasts import episode_filter_maintenance as maintenance
from quill.core.podcasts import quick_actions, surface_help
from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.models_filters import (
    PATTERN_WILDCARD,
    SCOPE_LIBRARY,
    SCOPE_NOTIFY,
    SCOPE_QUEUE,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
)
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import manager_menus
from quill.ui.podcasts.episode_search import EpisodeSearchMixin


def _episode(title: str, *, minutes: int = 30, published: str = "2026-08-01") -> PodcastEpisode:
    return PodcastEpisode(
        guid=title,
        title=title,
        audio_url=f"https://example.test/{title}.mp3",
        published=published,
        duration_seconds=minutes * 60,
    )


def _filter(pattern: str, *scopes: str) -> EpisodeFilterConfiguration:
    return EpisodeFilterConfiguration(
        enabled=True,
        scopes=set(scopes) or {SCOPE_LIBRARY},
        rules=[EpisodeFilterRule(name="Segments", pattern_kind=PATTERN_WILDCARD, pattern=pattern)],
    )


class _NoDownloads:
    """A download queue with nothing in it, which is all these paths need."""

    def get(self, _item_id: str) -> None:
        return None


class _Host(EpisodeSearchMixin):
    """As much of the Podcast Manager's contract as these paths touch."""

    def __init__(self, library: PodcastLibrary, show: PodcastShow) -> None:
        self._library = library
        self._current_show = show
        self._current_episodes: list[PodcastEpisode] = []
        self._safe_mode = False
        self.dialog = None
        self.said: list[str] = []
        self.changed = 0
        self.filled = 0
        self.mode = "all"
        self.query = ""
        self._download_queue = _NoDownloads()

    def _download_item_id(self, episode: PodcastEpisode) -> str:
        return episode.guid

    # -- the manager's own surface -------------------------------------
    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _on_library_changed(self) -> None:
        self.changed += 1

    def _fill_episodes(self, _show: object) -> None:
        self.filled += 1

    def refresh_tree(self) -> None:
        pass

    # -- what EpisodeSearchMixin asks of it ----------------------------
    def _selected_episode_filter(self) -> str:
        return self.mode

    def _episode_search_query(self) -> str:
        return self.query


@pytest.fixture
def host() -> _Host:
    show = PodcastShow(
        id="s1",
        title="A Show",
        feed_url="https://example.test/feed.xml",
        episodes=[
            _episode("The Main Episode", published="2026-08-03"),
            _episode("Daily Segment", minutes=2, published="2026-08-02"),
        ],
    )
    return _Host(PodcastLibrary(shows=[show]), show)


# -- the menus ---------------------------------------------------------------


def test_the_podcast_menu_offers_episode_filters(host: _Host) -> None:
    actions = manager_menus.show_actions(host, host._current_show)
    assert "episode_filters" in actions
    assert actions["episode_filters"].label == "Episode &Filters..."
    assert actions["episode_filters"].enabled


def test_episode_filters_is_a_quick_action_so_it_can_be_reordered() -> None:
    assert "episode_filters" in quick_actions.default_order("show")
    assert "toggle_filter_exempt" in quick_actions.default_order("episode")


def test_the_exemption_verb_is_dimmed_with_a_reason_when_there_is_no_filter(
    host: _Host,
) -> None:
    """Dimmed, not hidden: a verb that came and went would read as the feature
    coming and going (11.2)."""
    episode = host._current_show.episodes[1]
    resolved = manager_menus.episode_actions(host, host._current_show, episode)[
        "toggle_filter_exempt"
    ]
    assert not resolved.enabled
    assert "no Episode Filter" in resolved.reason


def test_the_exemption_verb_names_both_directions(host: _Host) -> None:
    library, show = host._library, host._current_show
    maintenance.set_filter(library, show, _filter("*Segment*"))
    episode = show.episodes[1]

    before = manager_menus.episode_actions(host, show, episode)["toggle_filter_exempt"]
    assert before.enabled
    assert before.label.startswith("Always K")

    maintenance.set_exempt(library, show, episode, True)
    after = manager_menus.episode_actions(host, show, episode)["toggle_filter_exempt"]
    assert after.label.startswith("Apply the Episode Filter")


# -- the episode list --------------------------------------------------------


def test_the_episode_list_hides_what_the_library_scope_hides(host: _Host) -> None:
    maintenance.set_filter(host._library, host._current_show, _filter("*Segment*", SCOPE_LIBRARY))
    shown = host._apply_episode_filter(list(host._current_show.episodes))
    assert [episode.title for episode in shown] == ["The Main Episode"]


def test_filtered_out_shows_exactly_what_was_hidden(host: _Host) -> None:
    """The promise that makes a hiding scope safe to offer at all."""
    maintenance.set_filter(host._library, host._current_show, _filter("*Segment*", SCOPE_LIBRARY))
    host.mode = "filtered_out"
    shown = host._apply_episode_filter(list(host._current_show.episodes))
    assert [episode.title for episode in shown] == ["Daily Segment"]


def test_filtered_out_answers_the_rules_even_with_no_hiding_scope(host: _Host) -> None:
    """A podcast that only filters its queue still has an answer here."""
    maintenance.set_filter(host._library, host._current_show, _filter("*Segment*", SCOPE_QUEUE))
    host.mode = "filtered_out"
    assert [e.title for e in host._apply_episode_filter(list(host._current_show.episodes))] == [
        "Daily Segment"
    ]
    host.mode = "all"
    assert len(host._apply_episode_filter(list(host._current_show.episodes))) == 2


def test_an_exempted_episode_returns_to_the_list(host: _Host) -> None:
    library, show = host._library, host._current_show
    maintenance.set_filter(library, show, _filter("*Segment*", SCOPE_LIBRARY))
    maintenance.set_exempt(library, show, show.episodes[1], True)
    assert len(host._apply_episode_filter(list(show.episodes))) == 2


def test_a_podcast_with_no_filter_lists_exactly_what_it_always_did(host: _Host) -> None:
    assert len(host._apply_episode_filter(list(host._current_show.episodes))) == 2
    host.mode = "unplayed"
    assert len(host._apply_episode_filter(list(host._current_show.episodes))) == 2


# -- the refresh -------------------------------------------------------------


class _RefreshHost:
    """The main frame's contract, as much of it as the acquisition mixin uses."""

    def __init__(self, library: PodcastLibrary) -> None:
        self._podcast_library = library
        self.said: list[str] = []

    def _announce(self, message: str, force: bool = False) -> None:
        self.said.append(message)


def test_each_route_asks_for_its_own_scope() -> None:
    """Keep it out of the queue, but still tell me about it."""
    from quill.ui.main_frame_podcast_acquisition import PodcastAcquisitionMixin

    show = PodcastShow(id="s1", title="A Show", episodes=[])
    library = PodcastLibrary(shows=[show])
    arrived = [_episode("The Main Episode"), _episode("Daily Segment")]
    show.episodes.extend(arrived)
    maintenance.set_filter(library, show, _filter("*Segment*", SCOPE_QUEUE))

    host = _RefreshHost(library)
    mixin = PodcastAcquisitionMixin()
    outcome = PodcastAcquisitionMixin._podcast_filter_new_episodes(host, show, arrived)  # type: ignore[arg-type]
    assert len(outcome.filtered) == 1

    queue_side = PodcastAcquisitionMixin._podcast_filter_scope(host, show, outcome, SCOPE_QUEUE)  # type: ignore[arg-type]
    notify_side = PodcastAcquisitionMixin._podcast_filter_scope(host, show, outcome, SCOPE_NOTIFY)  # type: ignore[arg-type]
    assert [episode.title for episode in queue_side] == ["The Main Episode"]
    assert len(notify_side) == 2
    assert mixin is not None  # the mixin is instantiable on its own


def test_the_refresh_sentence_names_the_hiding_scopes_only() -> None:
    from quill.ui.main_frame_podcast_acquisition import PodcastAcquisitionMixin

    show = PodcastShow(id="s1", title="A Show", episodes=[])
    library = PodcastLibrary(shows=[show])
    arrived = [_episode("Daily Segment")]
    show.episodes.extend(arrived)
    # A routing-only filter says the count and where the episodes still are,
    # and does *not* recite four scope names into a passing announcement.
    maintenance.set_filter(library, show, _filter("*Segment*", SCOPE_QUEUE))
    host = _RefreshHost(library)
    outcome = PodcastAcquisitionMixin._podcast_filter_new_episodes(host, show, arrived)  # type: ignore[arg-type]
    PodcastAcquisitionMixin._podcast_announce_episode_filter(host, show, outcome)  # type: ignore[arg-type]
    assert host.said
    assert "nothing was deleted" in host.said[0]
    assert "in the podcast's episode list as usual" in host.said[0]
    assert "auto-queueing" not in host.said[0]

    # A hiding filter names what it hid, and the way back.
    maintenance.set_filter(library, show, _filter("*Segment*", SCOPE_LIBRARY))
    host = _RefreshHost(library)
    outcome = PodcastAcquisitionMixin._podcast_filter_new_episodes(host, show, arrived)  # type: ignore[arg-type]
    PodcastAcquisitionMixin._podcast_announce_episode_filter(host, show, outcome)  # type: ignore[arg-type]
    assert "hidden from this podcast's episode list" in host.said[0]
    assert "choose Filtered out" in host.said[0]


# -- the queue pass ----------------------------------------------------------


def test_saving_reaches_the_queue_only_when_asked() -> None:
    show = PodcastShow(id="s1", title="A Show", episodes=[_episode("Daily Segment")])
    library = PodcastLibrary(shows=[show])
    library.queue.append(QueueItem(show_id="s1", episode_guid="Daily Segment"))
    config = _filter("*Segment*", SCOPE_QUEUE)
    maintenance.set_filter(library, show, config)
    # Merely storing the filter leaves the queue exactly as it was.
    assert len(library.queue) == 1
    assert maintenance.apply_to_existing(library, show, config).queue_removed == 1
    assert library.queue == []


# -- F1 ----------------------------------------------------------------------


def test_both_windows_answer_f1_with_authored_help() -> None:
    from quill.ui.podcasts.episode_filter_rule_dialog import TITLE as RULE_TITLE
    from quill.ui.podcasts.episode_filters_dialog import TITLE as FILTERS_TITLE

    assert surface_help.is_known_title(f"{FILTERS_TITLE} -- A Show")
    assert surface_help.is_known_title(RULE_TITLE)
    purpose = surface_help.purpose_for_title(f"{FILTERS_TITLE} -- A Show")
    assert purpose != surface_help.GENERIC_PURPOSE
    assert "never deleted" in purpose


def test_the_dialogs_read_the_shared_help_table_rather_than_their_own_literals() -> None:
    """The same rule the settings dialogs follow: one table, two windows."""
    from pathlib import Path

    from quill.core.podcasts import settings_help

    for name in ("episode_filters_dialog.py", "episode_filter_rule_dialog.py"):
        source = Path("quill/ui/podcasts", name).read_text(encoding="utf-8")
        assert "settings_help.FILTER_HELP[" in source
    # And every key those windows ask for exists.
    for key in ("enabled", "mode", "rules", "scopes", "preview", "rule_pattern"):
        assert settings_help.FILTER_HELP[key]


def _unused(*_args: Any) -> None:  # pragma: no cover - keeps Any imported honestly
    return None
