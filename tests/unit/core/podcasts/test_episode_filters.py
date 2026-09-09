"""Episode Filters: the decisions, the scopes, and every way they fail open.

The feature this ports (Earshot's Episode Filters V1, TestFlight build 243)
shipped with a list of named regression tests, and the ones worth keeping are
the ones that pin a *promise* rather than a code path. They are all here, plus
the ones QUILL Cast's own shape added:

* Preview evaluates the draft while the switch is off, and while no scope is
  ticked -- the defect device testing found first, and its scope-shaped twin.
* Keep matching with no usable rule can neither be saved nor reject a feed.
* The duration save gate: refuses no coverage, asks on partial, allows full.
* Scopes are independent, and a scope that is off behaves exactly like no
  filter at all.
* A hiding scope never makes an episode unreachable, and an exemption beats
  every rule in every scope.
* Nothing anywhere deletes, marks, moves, or re-times an episode.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts import episode_filter_maintenance as maintenance
from quill.core.podcasts import episode_filters as filters
from quill.core.podcasts import inbox, playlists, virtual_views
from quill.core.podcasts.acquisition import episodes_to_auto_download, route_new_episodes
from quill.core.podcasts.filtering import search_everywhere
from quill.core.podcasts.models import (
    Playlist,
    PlaylistRules,
    PodcastEpisode,
    PodcastShow,
    QueueItem,
)
from quill.core.podcasts.models_filters import (
    DEFAULT_SCOPES,
    FILTER_SCOPES,
    MODE_FILTER_MATCHING,
    MODE_KEEP_MATCHING,
    PATTERN_REGEX,
    PATTERN_WILDCARD,
    SCOPE_DOWNLOAD,
    SCOPE_INBOX,
    SCOPE_LIBRARY,
    SCOPE_PLAYLISTS,
    SCOPE_QUEUE,
    SCOPE_SEARCH,
    SCOPE_VIEWS,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
)
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(
    title: str, *, guid: str = "", minutes: int = 30, published: str = "2026-08-01"
) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid or title,
        title=title,
        audio_url=f"https://example.test/{guid or title}.mp3",
        published=published,
        duration_seconds=minutes * 60,
    )


def _wildcard(pattern: str, **kwargs: object) -> EpisodeFilterRule:
    return EpisodeFilterRule(
        name=kwargs.pop("name", "Segments"),  # type: ignore[arg-type]
        pattern_kind=PATTERN_WILDCARD,
        pattern=pattern,
        **kwargs,  # type: ignore[arg-type]
    )


def _config(*rules: EpisodeFilterRule, **kwargs: object) -> EpisodeFilterConfiguration:
    return EpisodeFilterConfiguration(
        enabled=bool(kwargs.pop("enabled", True)),
        mode=str(kwargs.pop("mode", MODE_FILTER_MATCHING)),
        scopes=set(kwargs.pop("scopes", DEFAULT_SCOPES)),  # type: ignore[arg-type]
        rules=list(rules),
    )


@pytest.fixture
def library_and_show() -> tuple[PodcastLibrary, PodcastShow]:
    show = PodcastShow(
        id="s1",
        title="A Show",
        feed_url="https://example.test/feed.xml",
        route_to_inbox=True,
        episodes=[
            _episode("The Main Episode", published="2026-08-03"),
            _episode("First Date Update", minutes=18, published="2026-08-02"),
            _episode("Second Date Update", minutes=18, published="2026-08-01"),
        ],
    )
    return PodcastLibrary(shows=[show]), show


# -- matching ----------------------------------------------------------------


def test_wildcards_cover_the_whole_title_and_escape_everything_else() -> None:
    """``*`` and ``?`` are the whole vocabulary; ``+`` means a plus sign."""
    assert filters.rule_matches(_wildcard("*Date*"), _episode("First Date Update"))
    assert not filters.rule_matches(_wildcard("Date"), _episode("First Date Update"))
    assert filters.rule_matches(_wildcard("Q+A*"), _episode("Q+A (short)"))
    assert not filters.rule_matches(_wildcard("Q+A*"), _episode("QQQA"))
    assert filters.rule_matches(_wildcard("Episode ?"), _episode("Episode 4"))
    assert not filters.rule_matches(_wildcard("Episode ?"), _episode("Episode 44"))


def test_matching_is_case_insensitive_until_asked_otherwise() -> None:
    assert filters.rule_matches(_wildcard("*date*"), _episode("First DATE Report"))
    assert not filters.rule_matches(
        _wildcard("*date*", case_sensitive=True), _episode("First DATE Report")
    )
    assert filters.rule_matches(
        _wildcard("*DATE*", case_sensitive=True), _episode("First DATE Report")
    )


def test_an_episode_with_no_duration_never_matches_a_duration_rule() -> None:
    """A missing length is not a short episode."""
    rule = EpisodeFilterRule(name="Long", min_duration_minutes=45)
    assert filters.rule_matches(rule, _episode("Long one", minutes=60))
    assert not filters.rule_matches(rule, _episode("Short one", minutes=10))
    assert not filters.rule_matches(rule, _episode("Unknown", minutes=0))


def test_title_and_duration_within_one_rule_are_anded() -> None:
    rule = _wildcard("*bonus*", min_duration_minutes=45)
    assert filters.rule_matches(rule, _episode("A bonus chat", minutes=60))
    assert not filters.rule_matches(rule, _episode("A bonus chat", minutes=10))
    assert not filters.rule_matches(rule, _episode("The main show", minutes=60))


def test_rules_across_a_configuration_are_ored() -> None:
    config = _config(_wildcard("*trailer*", name="Trailers"), _wildcard("*bonus*", name="Bonus"))
    assert not filters.keeps(config, _episode("A trailer"))
    assert not filters.keeps(config, _episode("A bonus"))
    assert filters.keeps(config, _episode("The show"))


def test_an_unusable_rule_matches_nothing_in_either_mode() -> None:
    """The whole fail-open story, in one assertion."""
    broken = EpisodeFilterRule(name="Broken", pattern_kind=PATTERN_REGEX, pattern="(unclosed")
    assert not broken.is_usable
    assert not filters.rule_matches(broken, _episode("anything"))
    for mode in (MODE_FILTER_MATCHING, MODE_KEEP_MATCHING):
        config = _config(broken, mode=mode)
        assert not config.is_active
        assert filters.keeps(config, _episode("anything"))


def test_keep_matching_with_zero_enabled_rules_bypasses_ingest(library_and_show) -> None:
    """A damaged Keep-matching filter must not swallow a whole podcast."""
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(mode=MODE_KEEP_MATCHING))
    outcome = maintenance.route_refresh(library, show, list(show.episodes))
    assert outcome.filtered == []
    assert len(outcome.kept) == 3


def test_deleting_the_last_keep_rule_leaves_the_feed_untouched(library_and_show) -> None:
    library, show = library_and_show
    config = _config(_wildcard("*main*"), mode=MODE_KEEP_MATCHING)
    maintenance.set_filter(library, show, config)
    config.rules.clear()
    outcome = maintenance.route_refresh(library, show, list(show.episodes))
    assert outcome.filtered == []
    assert not filters.assess_save(config, show.episodes).ok


# -- preview -----------------------------------------------------------------


def test_preview_evaluates_the_draft_while_filtering_is_off() -> None:
    """The defect device testing found first, pinned."""
    config = _config(_wildcard("*Date*"), enabled=False)
    rows = filters.preview(config, [_episode("First Date Update"), _episode("The Main Episode")])
    assert [row.decision for row in rows] == ["Kept", "Filtered"] or [
        row.decision for row in rows
    ] == ["Filtered", "Kept"]
    assert sum(1 for row in rows if not row.kept) == 1


def test_preview_evaluates_the_draft_while_no_scope_is_ticked() -> None:
    """Its scope-shaped twin: Preview answers about the rules, not the scopes."""
    config = _config(_wildcard("*Date*"), scopes=set())
    rows = filters.preview(config, [_episode("First Date Update")])
    assert rows[0].kept is False


def test_preview_never_mutates_the_configuration_it_was_given() -> None:
    config = _config(_wildcard("*Date*"), enabled=False, scopes=set())
    filters.preview(config, [_episode("First Date Update")])
    assert config.enabled is False
    assert config.scopes == set()


def test_preview_looks_at_the_newest_fifty_only() -> None:
    episodes = [_episode(f"Episode {n}", published=f"2026-01-{n:02d}") for n in range(1, 32)]
    episodes += [_episode(f"Older {n}", published="2025-01-01") for n in range(30)]
    rows = filters.preview(_config(_wildcard("*Older*")), episodes)
    assert len(rows) == filters.PREVIEW_LIMIT


def test_preview_summary_counts_and_calls_out_a_total_rejection() -> None:
    rows = filters.preview(_config(_wildcard("*")), [_episode("Anything")])
    assert "Every one of the 1 newest episodes would be filtered out" in filters.preview_summary(
        rows
    )
    assert "no stored episodes yet" in filters.preview_summary([])


# -- the save gate -----------------------------------------------------------


def test_on_with_no_enabled_rule_cannot_be_saved() -> None:
    assessment = filters.assess_save(_config(), [])
    assert not assessment.ok
    assert "no rule is switched on" in assessment.blocked


def test_an_invalid_regular_expression_cannot_be_saved_and_says_why() -> None:
    rule = EpisodeFilterRule(name="Broken", pattern_kind=PATTERN_REGEX, pattern="(unclosed")
    assessment = filters.assess_save(_config(rule), [])
    assert not assessment.ok
    assert "Broken" in assessment.blocked
    assert "cannot be read" in assessment.blocked


def test_on_with_no_scope_cannot_be_saved() -> None:
    assessment = filters.assess_save(_config(_wildcard("*x*"), scopes=set()), [])
    assert not assessment.ok
    assert "Where this applies" in assessment.blocked


def test_duration_gate_refuses_when_no_sampled_episode_reports_a_length() -> None:
    config = _config(EpisodeFilterRule(name="Long", min_duration_minutes=45))
    lengthless = [_episode(f"Episode {n}", minutes=0) for n in range(5)]
    assert not filters.assess_save(config, lengthless).ok
    # An empty sample counts as no coverage too.
    assert not filters.assess_save(config, []).ok


def test_duration_gate_asks_on_partial_coverage_and_says_the_count() -> None:
    config = _config(EpisodeFilterRule(name="Long", min_duration_minutes=45))
    episodes = [_episode("With", minutes=60), _episode("Without", minutes=0)]
    assessment = filters.assess_save(config, episodes)
    assert assessment.ok
    assert "Only 1 of the 2" in assessment.confirm


def test_duration_gate_allows_complete_coverage_without_asking() -> None:
    config = _config(EpisodeFilterRule(name="Long", min_duration_minutes=45))
    assessment = filters.assess_save(config, [_episode("With", minutes=60)])
    assert assessment.ok
    assert assessment.confirm == ""


def test_a_hiding_scope_always_asks_and_names_the_way_back() -> None:
    config = _config(_wildcard("*x*"), scopes={SCOPE_LIBRARY})
    assessment = filters.assess_save(config, [_episode("Anything")])
    assert assessment.ok
    assert "Filtered out" in assessment.confirm
    assert "not deleted" in assessment.confirm


def test_routing_scopes_alone_need_no_confirmation() -> None:
    assessment = filters.assess_save(_config(_wildcard("*x*")), [_episode("Anything")])
    assert assessment.ok
    assert assessment.confirm == ""


# -- storage -----------------------------------------------------------------


def test_a_configuration_round_trips() -> None:
    config = _config(
        _wildcard("*Date*", case_sensitive=True, min_duration_minutes=10),
        mode=MODE_KEEP_MATCHING,
        scopes={SCOPE_INBOX, SCOPE_LIBRARY},
    )
    restored = EpisodeFilterConfiguration.from_dict(config.to_dict())
    assert restored is not None
    assert restored.mode == MODE_KEEP_MATCHING
    assert restored.scopes == {SCOPE_INBOX, SCOPE_LIBRARY}
    assert restored.rules[0].pattern == "*Date*"
    assert restored.rules[0].case_sensitive is True
    assert restored.rules[0].min_duration_minutes == 10


def test_an_unknown_version_reads_as_no_filter_at_all() -> None:
    assert EpisodeFilterConfiguration.from_dict({"version": 2, "enabled": True}) is None
    assert EpisodeFilterConfiguration.from_dict("nonsense") is None
    assert EpisodeFilterConfiguration.from_dict({"enabled": True}) is None


def test_a_stored_file_without_scopes_reads_as_the_routing_four() -> None:
    stored = {"version": 1, "enabled": True, "mode": MODE_FILTER_MATCHING, "rules": []}
    restored = EpisodeFilterConfiguration.from_dict(stored)
    assert restored is not None
    assert restored.scopes == set(DEFAULT_SCOPES)


def test_an_unknown_scope_name_is_dropped_rather_than_honoured() -> None:
    stored = {"version": 1, "enabled": True, "scopes": ["inbox", "teleportation"], "rules": []}
    restored = EpisodeFilterConfiguration.from_dict(stored)
    assert restored is not None
    assert restored.scopes == {SCOPE_INBOX}


def test_the_library_persists_filters_exemptions_and_reviews(tmp_path) -> None:
    from quill.core.podcasts.subscriptions import load_library, save_library

    show = PodcastShow(id="s1", title="A Show", episodes=[_episode("One")])
    library = PodcastLibrary(shows=[show])
    maintenance.set_filter(library, show, _config(_wildcard("*One*")))
    maintenance.set_exempt(library, show, show.episodes[0], True)
    maintenance.mark_needs_review(library, show)
    save_library(tmp_path, library)

    reloaded = load_library(tmp_path)
    restored_show = reloaded.find_show("s1")
    assert restored_show is not None
    assert maintenance.filter_for(reloaded, restored_show) is not None
    assert maintenance.is_exempt(reloaded, restored_show, restored_show.episodes[0])
    assert maintenance.needs_review(reloaded, restored_show)


# -- scopes ------------------------------------------------------------------


def test_a_scope_that_is_off_behaves_exactly_like_no_filter(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_INBOX}))
    episode = show.find_episode("First Date Update")
    assert episode is not None
    assert maintenance.hidden_from(library, show, episode, SCOPE_INBOX)
    for scope in FILTER_SCOPES:
        if scope != SCOPE_INBOX:
            assert not maintenance.hidden_from(library, show, episode, scope)


def test_the_inbox_honours_the_inbox_scope_and_only_that(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_INBOX}))
    titles = [episode.title for _show, episode in inbox.inbox_pairs(library)]
    assert titles == ["The Main Episode"]
    # Every episode is still in the podcast's own list, untouched.
    assert len(show.episodes) == 3


def test_unticking_a_scope_puts_the_episodes_back_at_once(library_and_show) -> None:
    """The reason the verdict is asked and not stamped."""
    library, show = library_and_show
    config = _config(_wildcard("*Date*"), scopes={SCOPE_INBOX})
    maintenance.set_filter(library, show, config)
    assert len(inbox.inbox_pairs(library)) == 1
    config.scopes = set()
    assert len(inbox.inbox_pairs(library)) == 3


def test_the_views_scope_covers_new_episodes_and_continue_listening(library_and_show) -> None:
    library, show = library_and_show
    show.episodes[1].position_ms = 5000
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_VIEWS}))
    assert [e.title for _s, e in virtual_views.virtual_view_pairs(library, "new_episodes")] == [
        "The Main Episode"
    ]
    assert virtual_views.virtual_view_pairs(library, "continue_listening") == []


def test_the_playlists_scope_keeps_rejects_out_of_a_smart_playlist(library_and_show) -> None:
    library, show = library_and_show
    library.playlists.append(
        Playlist(id="p1", name="Everything", kind="smart", rules=PlaylistRules())
    )
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_PLAYLISTS}))
    resolved = playlists.resolve_playlist(library, library.playlists[0])
    assert [episode.title for _s, episode in resolved] == ["The Main Episode"]


def test_the_search_scope_is_off_by_default_and_works_when_ticked(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*")))
    assert len(search_everywhere(library, "date")) == 2
    maintenance.set_filter(
        library, show, _config(_wildcard("*Date*"), scopes={SCOPE_INBOX, SCOPE_SEARCH})
    )
    assert search_everywhere(library, "date") == []


def test_the_download_scope_gates_auto_download(library_and_show) -> None:
    library, show = library_and_show
    library.settings.auto_download_count = -1
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_DOWNLOAD}))
    wanted = [episode.title for episode in episodes_to_auto_download(library, show)]
    assert wanted == ["The Main Episode"]


def test_the_queue_scope_gates_auto_queue(library_and_show) -> None:
    library, show = library_and_show
    show.auto_queue = True
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_QUEUE}))
    assert route_new_episodes(library, show, list(show.episodes)) == 1
    assert [item.episode_guid for item in library.queue] == ["The Main Episode"]


# -- exemptions and the way back ---------------------------------------------


def test_an_exemption_beats_every_rule_in_every_scope(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes=set(FILTER_SCOPES)))
    episode = show.find_episode("First Date Update")
    assert episode is not None
    assert maintenance.set_exempt(library, show, episode, True)
    for scope in FILTER_SCOPES:
        assert not maintenance.hidden_from(library, show, episode, scope)
    assert maintenance.set_exempt(library, show, episode, False)
    assert maintenance.hidden_from(library, show, episode, SCOPE_LIBRARY)


def test_an_exemption_survives_editing_the_rules(library_and_show) -> None:
    library, show = library_and_show
    config = _config(_wildcard("*Date*"), scopes={SCOPE_LIBRARY})
    maintenance.set_filter(library, show, config)
    episode = show.find_episode("First Date Update")
    assert episode is not None
    maintenance.set_exempt(library, show, episode, True)
    config.rules.append(_wildcard("*Update*", name="Also updates"))
    assert not maintenance.hidden_from(library, show, episode, SCOPE_LIBRARY)


def test_hidden_and_visible_are_exact_complements(library_and_show) -> None:
    """Nothing a hiding scope removes is unreachable."""
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_LIBRARY}))
    shown = maintenance.visible(library, show, show.episodes, SCOPE_LIBRARY)
    held = maintenance.hidden(library, show, show.episodes, SCOPE_LIBRARY)
    assert len(shown) + len(held) == len(show.episodes)
    assert not set(e.guid for e in shown) & set(e.guid for e in held)


def test_clearing_a_filter_restores_everything_and_forgets_exemptions(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_INBOX}))
    maintenance.set_exempt(library, show, show.episodes[1], True)
    maintenance.mark_needs_review(library, show)
    assert maintenance.clear_filter(library, show)
    assert len(inbox.inbox_pairs(library)) == 3
    assert maintenance.exemptions(library, show) == set()
    assert not maintenance.needs_review(library, show)


# -- the refresh -------------------------------------------------------------


def test_a_refresh_changes_nothing_about_the_episodes(library_and_show) -> None:
    library, show = library_and_show
    show.episodes[1].played = True
    show.episodes[1].position_ms = 1234
    show.episodes[1].downloaded_path = "C:/somewhere.mp3"
    maintenance.set_filter(library, show, _config(_wildcard("*Date*")))
    maintenance.route_refresh(library, show, list(show.episodes))
    assert show.episodes[1].played is True
    assert show.episodes[1].position_ms == 1234
    assert show.episodes[1].downloaded_path == "C:/somewhere.mp3"
    assert len(show.episodes) == 3
    assert library.inbox_assignments == {}


def test_keep_matching_rejecting_everything_raises_needs_review(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(
        library, show, _config(_wildcard("*never matches*"), mode=MODE_KEEP_MATCHING)
    )
    outcome = maintenance.route_refresh(library, show, list(show.episodes))
    assert outcome.raised_review
    assert maintenance.needs_review(library, show)
    assert maintenance.clear_needs_review(library, show)
    assert not maintenance.needs_review(library, show)


def test_filter_matching_rejecting_everything_is_not_a_warning(library_and_show) -> None:
    """Under Filter matching, "it caught everything" is an ordinary result."""
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*")))
    outcome = maintenance.route_refresh(library, show, list(show.episodes))
    assert outcome.filtered and not outcome.kept
    assert not outcome.raised_review
    assert not maintenance.needs_review(library, show)


def test_a_scope_that_is_off_gets_every_arrived_episode(library_and_show) -> None:
    library, show = library_and_show
    maintenance.set_filter(library, show, _config(_wildcard("*Date*"), scopes={SCOPE_INBOX}))
    outcome = maintenance.route_refresh(library, show, list(show.episodes))
    assert len(maintenance.announce_candidates(library, show, outcome)) == 3
    assert len(maintenance.queue_candidates(library, show, outcome)) == 3


def test_a_podcast_with_no_filter_takes_the_same_path_it_always_did(library_and_show) -> None:
    library, show = library_and_show
    outcome = maintenance.route_refresh(library, show, list(show.episodes))
    assert outcome.kept == show.episodes
    assert outcome.filtered == []
    assert not outcome.raised_review


# -- applying to the Play Queue ----------------------------------------------


def test_apply_to_existing_clears_the_queue_and_keeps_what_is_playing(library_and_show) -> None:
    library, show = library_and_show
    for episode in show.episodes:
        library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
    config = _config(_wildcard("*Date*"), scopes={SCOPE_QUEUE})
    maintenance.set_filter(library, show, config)
    outcome = maintenance.apply_to_existing(
        library, show, config, playing=(show.id, "First Date Update")
    )
    assert outcome.queue_removed == 1
    assert outcome.playing_kept is True
    assert [item.episode_guid for item in library.queue] == [
        "The Main Episode",
        "First Date Update",
    ]


def test_apply_to_existing_never_changes_played_state_or_downloads(library_and_show) -> None:
    library, show = library_and_show
    episode = show.episodes[1]
    episode.played = True
    episode.position_ms = 9000
    episode.downloaded_path = "C:/kept.mp3"
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
    config = _config(_wildcard("*Date*"), scopes={SCOPE_QUEUE})
    maintenance.apply_to_existing(library, show, config)
    assert episode.played is True
    assert episode.position_ms == 9000
    assert episode.downloaded_path == "C:/kept.mp3"
    assert show.find_episode(episode.guid) is episode


def test_apply_to_existing_does_nothing_without_the_queue_scope(library_and_show) -> None:
    library, show = library_and_show
    library.queue.append(QueueItem(show_id=show.id, episode_guid="First Date Update"))
    config = _config(_wildcard("*Date*"), scopes={SCOPE_LIBRARY})
    assert maintenance.apply_to_existing(library, show, config).queue_removed == 0
    assert len(library.queue) == 1


def test_apply_to_existing_leaves_an_exempted_episode_queued(library_and_show) -> None:
    library, show = library_and_show
    episode = show.episodes[1]
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
    config = _config(_wildcard("*Date*"), scopes={SCOPE_QUEUE})
    maintenance.set_filter(library, show, config)
    maintenance.set_exempt(library, show, episode, True)
    assert maintenance.apply_to_existing(library, show, config).queue_removed == 0


# -- the words ---------------------------------------------------------------


def test_a_rule_speaks_its_name_then_its_state_then_its_criteria() -> None:
    rule = _wildcard("*date*", name="Segments", min_duration_minutes=45)
    spoken = filters.describe_rule(rule)
    assert spoken.startswith("Segments, enabled.")
    assert "Wildcard title, *date*." in spoken
    assert "Duration at least 45 minutes." in spoken
    rule.enabled = False
    assert filters.describe_rule(rule).startswith("Segments, disabled.")


def test_a_preview_row_leads_with_the_decision() -> None:
    rows = filters.preview(
        _config(_wildcard("*Date*")), [_episode("First Date Update", minutes=18)]
    )
    spoken = filters.describe_preview_row(rows[0])
    assert spoken == "Filtered, First Date Update, 18 minutes."


def test_a_preview_row_can_name_the_rule_that_decided_it() -> None:
    """Asked for only when there is more than one rule to choose between."""
    config = _config(_wildcard("*Date*", name="Segments"), _wildcard("*Trailer*", name="Trailers"))
    rows = filters.preview(config, [_episode("First Date Update", minutes=18)])
    assert filters.describe_preview_row(rows[0]) == "Filtered, First Date Update, 18 minutes."
    assert filters.describe_preview_row(rows[0], with_reason=True).endswith("Matched Segments.")


def test_a_preview_row_says_when_the_feed_gave_no_length() -> None:
    rows = filters.preview(_config(_wildcard("*nope*")), [_episode("Mystery", minutes=0)])
    assert filters.describe_preview_row(rows[0]).endswith("length unknown.")


def test_the_configuration_summary_names_where_it_applies() -> None:
    config = _config(_wildcard("*x*"), scopes={SCOPE_INBOX, SCOPE_LIBRARY})
    spoken = filters.describe_configuration(config)
    assert "the Inbox" in spoken
    assert "this podcast's episode list" in spoken


def test_an_inactive_configuration_says_so_plainly() -> None:
    assert "off for this podcast" in filters.describe_configuration(None)
    assert "off for this podcast" in filters.describe_configuration(_config(enabled=False))
    assert "applies nowhere" in filters.describe_configuration(
        _config(_wildcard("*x*"), scopes=set())
    )


def test_the_refresh_sentence_says_nothing_was_deleted_and_where_to_look() -> None:
    """Routing scopes are not listed; hiding scopes are, with the way back."""
    routing = filters.describe_refresh_outcome("A Show", 2, 3)
    assert "2 new, 3 episodes filtered out for A Show" in routing
    assert "nothing was deleted" in routing
    assert "in the podcast's episode list as usual" in routing

    hiding = filters.describe_refresh_outcome("A Show", 0, 1, hidden="this podcast's episode list")
    assert "1 episode filtered out for A Show" in hiding
    assert "hidden from this podcast's episode list" in hiding
    assert "choose Filtered out" in hiding

    assert filters.describe_refresh_outcome("A Show", 2, 0) == ""


def test_the_apply_result_reports_the_count_and_the_playing_exception() -> None:
    spoken = filters.describe_apply_result("A Show", 2, True)
    assert "2 episodes removed from the Play Queue" in spoken
    assert "playing now was left in the queue" in spoken
    assert "Nothing was deleted" in spoken
    assert "Nothing in the Play Queue matched it" in filters.describe_apply_result(
        "A Show", 0, False
    )


def test_the_needs_review_warning_says_nothing_was_lost() -> None:
    spoken = filters.describe_needs_review("A Show")
    assert "Nothing was lost" in spoken
    assert "Episode Filters" in spoken


def test_every_scope_has_a_label_a_summary_and_its_own_access_key() -> None:
    """Eight checkboxes, so eight mnemonics, and no two the same (GATE-14)."""
    from quill.core.podcasts.models_filters import SCOPE_LABELS, SCOPE_SUMMARIES

    keys: list[str] = []
    for scope in FILTER_SCOPES:
        label = SCOPE_LABELS.get(scope, "")
        assert label
        assert SCOPE_SUMMARIES.get(scope)
        assert "&" not in SCOPE_SUMMARIES[scope]
        marker = label.find("&")
        assert marker >= 0, f"{scope} has no access key"
        keys.append(label[marker + 1].lower())
    assert len(set(keys)) == len(keys), f"duplicate scope access keys: {keys}"
