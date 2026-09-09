"""The per-podcast settings proposal: the chain, the catalogue, the policies.

Three things are pinned here and they are the three the proposal turns on.

**The chain composes.** Shared default, folder, podcast, nearest wins -- and a
level with no opinion is invisible rather than a copy of the level above. That
distinction is the whole point: without it, changing a shared default silently
stops reaching the podcasts that were ever touched by a folder edit.

**Every setting is described.** A label, help that says what it does *not* do,
the levels it is allowed at, and words for its value. That description is what
makes ninety-odd settings searchable and reportable instead of merely stored.

**Each setting actually decides something.** A stored value nothing reads is a
checkbox that lies, so every policy below is asserted against the behaviour it
governs rather than against the value it holds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quill.core.podcasts import (
    check_state,
    row_speech,
    settings_catalog,
    show_policy,
    title_cleanup,
)
from quill.core.podcasts.models import PodcastFolder, PodcastSettings, PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.settings_resolver import (
    clear_scope,
    clear_value,
    describe_provenance,
    effective_settings,
    migrate_legacy_overrides,
    resolve,
    set_value,
    value_of,
)
from quill.core.podcasts.settings_types import LEVEL_FOLDER, LEVEL_GLOBAL, LEVEL_SHOW
from quill.core.podcasts.sorting import sort_episodes
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(title: str, **kwargs) -> PodcastEpisode:
    return PodcastEpisode(
        guid=kwargs.pop("guid", title),
        title=title,
        audio_url=f"https://example.test/{title}.mp3",
        **kwargs,
    )


def _def(setting_id: str):
    definition = settings_catalog.definition(setting_id)
    assert definition is not None, setting_id
    return definition


@pytest.fixture
def library() -> PodcastLibrary:
    news = PodcastFolder(id="f-news", name="News")
    politics = PodcastFolder(id="f-pol", name="Politics", parent_folder_id="f-news")
    daily = PodcastShow(id="s-daily", title="The Daily", folder_id="f-pol")
    weekly = PodcastShow(id="s-weekly", title="A Weekly Show")
    return PodcastLibrary(shows=[daily, weekly], folders=[news, politics])


# -- the chain ---------------------------------------------------------------


def test_a_podcast_with_no_opinion_follows_the_shared_default(library) -> None:
    show = library.find_show("s-daily")
    assert value_of(library, _def("speed"), show=show) == 1.0
    library.settings.speed = 1.5
    assert value_of(library, _def("speed"), show=show) == 1.5


def test_a_folder_is_a_real_level_and_reaches_its_subfolders(library) -> None:
    daily = library.find_show("s-daily")
    weekly = library.find_show("s-weekly")
    set_value(library, _def("refresh_minutes"), 60, level=LEVEL_FOLDER, scope_id="f-news")
    assert value_of(library, _def("refresh_minutes"), show=daily) == 60
    assert value_of(library, _def("refresh_minutes"), show=weekly) == 0


def test_the_nearest_level_wins(library) -> None:
    show = library.find_show("s-daily")
    library.settings.speed = 1.0
    set_value(library, _def("speed"), 1.5, level=LEVEL_FOLDER, scope_id="f-news")
    set_value(library, _def("speed"), 2.0, level=LEVEL_FOLDER, scope_id="f-pol")
    assert value_of(library, _def("speed"), show=show) == 2.0
    set_value(library, _def("speed"), 3.0, level=LEVEL_SHOW, scope_id=show.id)
    assert value_of(library, _def("speed"), show=show) == 3.0


def test_clearing_a_level_falls_back_rather_than_writing_the_default(library) -> None:
    """The distinction the whole model exists to preserve."""
    show = library.find_show("s-daily")
    set_value(library, _def("speed"), 1.5, level=LEVEL_FOLDER, scope_id="f-news")
    set_value(library, _def("speed"), 3.0, level=LEVEL_SHOW, scope_id=show.id)
    assert clear_value(library, _def("speed"), level=LEVEL_SHOW, scope_id=show.id)
    assert value_of(library, _def("speed"), show=show) == 1.5


def test_a_setting_is_never_read_at_a_level_it_does_not_allow(library) -> None:
    show = library.find_show("s-daily")
    definition = _def("download_root")
    assert definition.global_only
    library.scope_overrides[f"show:{show.id}"] = {"download_root": "C:/nope"}
    assert value_of(library, definition, show=show) == ""


def test_provenance_names_the_level_that_answered(library) -> None:
    show = library.find_show("s-daily")
    assert "shared default" in describe_provenance(
        _def("speed"), resolve(library, _def("speed"), show=show)
    )
    set_value(library, _def("speed"), 1.5, level=LEVEL_FOLDER, scope_id="f-news")
    said = describe_provenance(_def("speed"), resolve(library, _def("speed"), show=show))
    assert "folder News" in said
    set_value(library, _def("speed"), 2.0, level=LEVEL_SHOW, scope_id=show.id)
    assert "this podcast" in describe_provenance(
        _def("speed"), resolve(library, _def("speed"), show=show)
    )


def test_a_folder_cycle_cannot_hang_the_resolver(library) -> None:
    library.find_folder("f-news").parent_folder_id = "f-pol"
    show = library.find_show("s-daily")
    assert value_of(library, _def("speed"), show=show) == 1.0


# -- the compatibility bridge ------------------------------------------------


def test_effective_settings_returns_the_shared_record_untouched(library) -> None:
    """The fast path: no override anywhere means nothing is allocated."""
    show = library.find_show("s-weekly")
    assert effective_settings(library, show) is library.settings


def test_effective_settings_folds_in_folder_and_show(library) -> None:
    show = library.find_show("s-daily")
    set_value(library, _def("speed"), 1.5, level=LEVEL_FOLDER, scope_id="f-news")
    set_value(library, _def("inbox_max_episodes"), 7, level=LEVEL_SHOW, scope_id=show.id)
    resolved = effective_settings(library, show)
    assert resolved.speed == 1.5
    assert resolved.inbox_max_episodes == 7
    assert resolved.retention_count == library.settings.retention_count


def test_apply_show_override_writes_only_the_fields_named(library) -> None:
    """The bug this replaces: it used to freeze every other setting too."""
    show = library.find_show("s-daily")
    library.apply_show_override(show, speed=2.0)
    library.settings.retention_count = 11
    assert library.effective_settings(show).speed == 2.0
    assert library.effective_settings(show).retention_count == 11


def test_a_legacy_whole_record_override_migrates_by_diffing(library) -> None:
    show = library.find_show("s-daily")
    show.settings = PodcastSettings(speed=2.0)
    moved = migrate_legacy_overrides(library)
    assert moved == 1
    assert show.settings is None
    stored = library.scope_overrides[f"show:{show.id}"]
    assert stored == {"speed": 2.0}
    # Everything that matched the shared default is read as "no opinion", so a
    # later change to the default still reaches this podcast.
    library.settings.retention_count = 9
    assert library.effective_settings(show).retention_count == 9


def test_following_the_shared_defaults_drops_every_opinion(library) -> None:
    show = library.find_show("s-daily")
    set_value(library, _def("speed"), 2.0, level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, _def("inbox_max_episodes"), 4, level=LEVEL_SHOW, scope_id=show.id)
    assert clear_scope(library, level=LEVEL_SHOW, scope_id=show.id) == 2
    assert library.effective_settings(show) is library.settings


# -- the catalogue -----------------------------------------------------------


def test_every_setting_says_what_it_does_not_do() -> None:
    """The house rule, applied to the catalogue as well as the help tables."""
    import re

    negative = re.compile(
        r"\b(never|not|no |nothing|neither|nor|instead of|rather than|only|"
        r"without|cannot|leaves|untouched|stay|stays|unchanged|does not|"
        r"is not|it does|separate)\b",
        re.IGNORECASE,
    )
    missing = [item.id for item in settings_catalog.CATALOG if not negative.search(item.help)]
    assert missing == [], "catalogue help with no 'and what it does not do' half: " + ", ".join(
        missing
    )


def test_every_setting_has_a_label_a_level_and_a_sane_default() -> None:
    for item in settings_catalog.CATALOG:
        assert item.label.strip(), item.id
        assert item.levels, item.id
        assert item.coerce(item.default) == item.default, item.id


def test_ids_are_unique_and_fields_map_back() -> None:
    ids = [item.id for item in settings_catalog.CATALOG]
    assert len(set(ids)) == len(ids)
    assert settings_catalog.by_field("speed") is _def("speed")


def test_search_finds_a_setting_by_a_word_somebody_would_type() -> None:
    assert [hit.id for hit in settings_catalog.search("wifi")] == ["download_on_metered"]
    assert "volume_boost" == settings_catalog.search("volume")[0].id
    assert any(hit.id == "refresh_minutes" for hit in settings_catalog.search("cadence"))
    assert settings_catalog.search("   ") == []


def test_search_puts_a_label_match_before_a_help_match() -> None:
    """A label that *starts* with the word outranks one that merely contains
    it, which outranks a hit buried in the help -- otherwise a search for
    "volume" puts Volume Boost twelfth and nobody uses it twice."""
    hits = [hit.id for hit in settings_catalog.search("inbox")]
    assert hits.index("inbox_max_episodes") < hits.index("auto_download_inbox")
    assert hits.index("auto_download_inbox") < hits.index("episode_list_view_mode")


def test_the_search_summary_counts_rather_than_saying_found() -> None:
    hits = settings_catalog.search("inbox")
    assert f"{len(hits)} settings match" in settings_catalog.search_summary(hits, "inbox")
    assert "No setting matches" in settings_catalog.search_summary([], "zzz")


def test_changed_reports_only_what_differs(library) -> None:
    show = library.find_show("s-daily")
    assert settings_catalog.changed(library, show=show) == []
    set_value(library, _def("speed"), 2.0, level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, _def("refresh_minutes"), 60, level=LEVEL_FOLDER, scope_id="f-news")
    entries = settings_catalog.changed(library, show=show)
    assert {entry.definition.id for entry in entries} == {"speed", "refresh_minutes"}
    assert any("folder: News" in entry.label() for entry in entries)
    assert "2 settings" in settings_catalog.changed_summary(entries, subject=show.title)


def test_changed_summary_says_so_when_nothing_differs(library) -> None:
    said = settings_catalog.changed_summary([], subject="The Daily")
    assert "Nothing for The Daily differs" in said


# -- 7.1 / 7.19: the check ---------------------------------------------------


def test_each_podcast_is_due_on_its_own_cadence(library) -> None:
    daily = library.find_show("s-daily")
    set_value(library, _def("refresh_minutes"), 60, level=LEVEL_SHOW, scope_id=daily.id)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    assert check_state.is_due(library, daily, now=now)  # never checked
    check_state.record_success(library, daily, now=now)
    assert not check_state.is_due(library, daily, now=now + timedelta(minutes=30))
    assert check_state.is_due(library, daily, now=now + timedelta(minutes=61))


def test_a_cadence_of_zero_is_manually_only(library) -> None:
    show = library.find_show("s-weekly")
    assert show_policy.cadence_minutes(library, show) == 0
    assert not check_state.is_due(library, show)


def test_a_failed_run_earns_one_sentence_not_one_per_check(library) -> None:
    show = library.find_show("s-daily")
    set_value(library, _def("failed_check_notice"), 3, level=LEVEL_SHOW, scope_id=show.id)
    for _ in range(2):
        check_state.record_failure(library, show)
        assert check_state.failure_notice(library, show) == ""
    check_state.record_failure(library, show)
    said = check_state.failure_notice(library, show)
    assert "3 times in a row" in said
    assert "still trying" in said
    assert check_state.failure_notice(library, show) == ""  # latched
    check_state.record_success(library, show)
    assert check_state.failure_run(library, show) == 0


def test_a_podcast_that_goes_quiet_is_reported_once_and_again_later(library) -> None:
    show = library.find_show("s-daily")
    set_value(library, _def("quiet_feed_weeks"), 2, level=LEVEL_SHOW, scope_id=show.id)
    start = datetime(2026, 6, 1, tzinfo=UTC)
    check_state.record_success(library, show, new_episodes=1, now=start)
    assert check_state.quiet_notice(library, show, now=start + timedelta(days=6)) == ""
    said = check_state.quiet_notice(library, show, now=start + timedelta(days=21))
    assert "published nothing for 2 weeks" in said
    assert "still subscribed" in said
    assert check_state.quiet_notice(library, show, now=start + timedelta(days=22)) == ""
    # Publishing again clears the latch, so the next silence is reported too.
    check_state.record_success(library, show, new_episodes=1, now=start + timedelta(days=30))
    assert check_state.quiet_notice(library, show, now=start + timedelta(days=60))


# -- 7.2 / 7.6 / 7.10: arrival ----------------------------------------------


def test_backfill_is_a_one_off_separate_from_the_download_count(library) -> None:
    show = library.find_show("s-daily")
    episodes = [_episode(f"E{n:02d}", published=f"2026-08-{n:02d}") for n in range(1, 11)]
    assert show_policy.backfill_episodes(library, show, episodes) == []
    set_value(library, _def("backfill_mode"), "newest", level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, _def("backfill_count"), 3, level=LEVEL_SHOW, scope_id=show.id)
    picked = show_policy.backfill_episodes(library, show, episodes)
    assert [e.title for e in picked] == ["E10", "E09", "E08"]
    set_value(library, _def("backfill_mode"), "all", level=LEVEL_SHOW, scope_id=show.id)
    assert len(show_policy.backfill_episodes(library, show, episodes)) == 10


def test_a_backfill_mark_becomes_an_actual_download(library) -> None:
    """A setting that marks and never fetches is a checkbox that lies."""
    from quill.core.podcasts.acquisition import episodes_to_auto_download

    show = library.find_show("s-daily")
    show.episodes = [_episode(f"E{n:02d}", published=f"2026-08-{n:02d}") for n in range(1, 6)]
    assert episodes_to_auto_download(library, show) == []
    set_value(library, _def("backfill_mode"), "newest", level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, _def("backfill_count"), 2, level=LEVEL_SHOW, scope_id=show.id)
    for episode in show_policy.backfill_episodes(library, show, show.episodes):
        episode.mode_override = "download"
    assert {e.title for e in episodes_to_auto_download(library, show)} == {"E05", "E04"}


def test_the_download_window_wraps_midnight_and_defaults_to_whenever(library) -> None:
    show = library.find_show("s-daily")
    assert show_policy.in_download_window(library, show, now=datetime(2026, 8, 29, 14))
    set_value(library, _def("download_window_start"), 22, level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, _def("download_window_end"), 6, level=LEVEL_SHOW, scope_id=show.id)
    assert show_policy.in_download_window(library, show, now=datetime(2026, 8, 29, 23))
    assert show_policy.in_download_window(library, show, now=datetime(2026, 8, 29, 2))
    assert not show_policy.in_download_window(library, show, now=datetime(2026, 8, 29, 14))


def test_auto_queue_can_start_a_series_at_the_beginning(library) -> None:
    show = library.find_show("s-daily")
    show.episodes = [
        _episode("First", published="2026-01-01"),
        _episode("Second", published="2026-02-01"),
        _episode("Third", published="2026-03-01"),
    ]
    arrived = [show.episodes[-1]]
    assert show_policy.queue_candidates(library, show, arrived) == arrived
    set_value(library, _def("auto_queue_order"), "oldest", level=LEVEL_SHOW, scope_id=show.id)
    assert [e.title for e in show_policy.queue_candidates(library, show, arrived)] == ["First"]


# -- 7.3 / 7.4: how a podcast reads -----------------------------------------


def test_title_cleanup_tidies_the_reading_and_never_the_feed(library) -> None:
    show = library.find_show("s-daily")
    episode = _episode("Ep. 412: The Harbour")
    show.episodes = [episode]
    set_value(
        library,
        _def("title_cleanup"),
        [{"pattern": "Ep. *: ", "kind": "prefix"}],
        level=LEVEL_SHOW,
        scope_id=show.id,
    )
    assert show_policy.display_title(library, show, episode) == "The Harbour"
    assert episode.title == "Ep. 412: The Harbour"


def test_a_cleanup_rule_can_never_empty_a_title() -> None:
    assert title_cleanup.apply_rules("Ep. 1", [title_cleanup.TitleRule("*")]) == "Ep. 1"


def test_a_wildcard_star_is_not_greedy() -> None:
    """A greedy star would eat a title with a second colon down to nothing."""
    cleaned = title_cleanup.apply_rules(
        "Ep. 4: Harbour: Part Two", [title_cleanup.TitleRule("Ep. *: ")]
    )
    assert cleaned == "Harbour: Part Two"


def test_the_pronunciation_override_changes_speech_and_not_the_name(library) -> None:
    show = library.find_show("s-daily")
    assert show_policy.spoken_show_name(library, show) == "The Daily"
    set_value(library, _def("speech_name"), "The Dayly", level=LEVEL_SHOW, scope_id=show.id)
    assert show_policy.spoken_show_name(library, show) == "The Dayly"
    assert show.title == "The Daily"


# -- 7.5: attention ----------------------------------------------------------


def test_notify_priority_has_three_positions(library) -> None:
    show = library.find_show("s-daily")
    assert show_policy.notify_priority(library, show) == "normal"
    set_value(library, _def("notify_priority"), "quiet", level=LEVEL_SHOW, scope_id=show.id)
    assert show_policy.is_quiet(library, show)
    assert show_policy.earcon(library, show) == ""


def test_the_old_announce_switch_reads_as_urgent(library) -> None:
    """A podcast that had the boolean on meant "tell me by name"."""
    show = library.find_show("s-daily")
    show.notify_new_episodes = True
    assert show_policy.notify_priority(library, show) == "interrupt"


# -- 7.9 / 7.11 / 7.22: order, storage, view --------------------------------


def test_season_and_episode_numbers_sort_a_serial_correctly() -> None:
    episodes = [
        _episode("c", season=2, episode_number=1),
        _episode("a", season=1, episode_number=2),
        _episode("b", season=1, episode_number=10),
        _episode("unnumbered"),
    ]
    assert [e.title for e in sort_episodes(episodes, "season_episode")] == [
        "a",
        "b",
        "c",
        "unnumbered",
    ]


def test_a_pinned_podcast_is_exempt_from_the_automatic_sweeps(library) -> None:
    from quill.core.podcasts.retention import is_protected

    show = library.find_show("s-daily")
    episode = _episode("One", downloaded_path="C:/one.mp3")
    show.episodes = [episode]
    assert not is_protected(library, show, episode)
    set_value(library, _def("storage_pinned"), True, level=LEVEL_SHOW, scope_id=show.id)
    assert is_protected(library, show, episode)


def test_the_catalogue_view_limit_is_a_view_and_not_a_trim(library) -> None:
    show = library.find_show("s-daily")
    show.episodes = [_episode(f"E{n:03d}", published=f"2026-01-{n:02d}") for n in range(1, 21)]
    assert len(show_policy.visible_episodes(library, show, show.episodes)) == 20
    set_value(library, _def("catalog_view_limit"), 5, level=LEVEL_SHOW, scope_id=show.id)
    assert len(show_policy.visible_episodes(library, show, show.episodes)) == 5
    assert len(show.episodes) == 20  # nothing was removed


# -- 7.13 / 7.17 / 7.21: skip, labels, republish ----------------------------


def test_chapter_skip_patterns_match_by_wildcard(library) -> None:
    show = library.find_show("s-daily")
    set_value(
        library,
        _def("chapter_skip_patterns"),
        ["*Sponsor*", "Ad break"],
        level=LEVEL_SHOW,
        scope_id=show.id,
    )
    assert show_policy.skips_chapter(library, show, "A word from our Sponsor")
    assert show_policy.skips_chapter(library, show, "ad break")
    assert not show_policy.skips_chapter(library, show, "The interview")


def test_labels_are_per_podcast_and_never_move_it(library) -> None:
    show = library.find_show("s-daily")
    assert show_policy.labels(library, show) == []
    library.show_labels[show.id] = ["news", "short"]
    assert show_policy.labels(library, show) == ["news", "short"]
    assert show.folder_id == "f-pol"


def test_a_smart_playlist_can_ask_for_a_label(library) -> None:
    from quill.core.podcasts.models import Playlist, PlaylistRules
    from quill.core.podcasts.playlists import resolve_playlist

    daily = library.find_show("s-daily")
    weekly = library.find_show("s-weekly")
    daily.episodes = [_episode("From daily")]
    weekly.episodes = [_episode("From weekly")]
    library.show_labels[daily.id] = ["news"]
    playlist = Playlist(id="p", name="News", kind="smart", rules=PlaylistRules(labels=["news"]))
    assert [e.title for _s, e in resolve_playlist(library, playlist)] == ["From daily"]


def test_republish_handling_is_per_podcast(library) -> None:
    show = library.find_show("s-daily")
    assert show_policy.republished_as_new(library, show)
    set_value(library, _def("republished_as_new"), False, level=LEVEL_SHOW, scope_id=show.id)
    assert not show_policy.republished_as_new(library, show)


# -- 7.12 / 7.14: variants and row speech -----------------------------------


def test_a_variant_preference_never_leaves_an_episode_unplayable(library) -> None:
    show = library.find_show("s-daily")
    episode = _episode("One")
    set_value(library, _def("preferred_variant"), "smallest", level=LEVEL_SHOW, scope_id=show.id)
    # No alternates published: the publisher's own enclosure, unchanged.
    assert show_policy.audio_url(library, show, episode) == episode.audio_url


def test_row_speech_is_per_podcast(library) -> None:
    from quill.core.podcasts.settings_resolver import values_for

    show = library.find_show("s-daily")
    set_value(library, _def("row_say_date"), False, level=LEVEL_SHOW, scope_id=show.id)
    speech = row_speech.RowSpeech.from_values(values_for(library, row_speech.SETTINGS, show=show))
    assert speech.say_date is False
    other = library.find_show("s-weekly")
    assert row_speech.RowSpeech.from_values(
        values_for(library, row_speech.SETTINGS, show=other)
    ).say_date


def test_a_row_never_repeats_the_window_it_is_in() -> None:
    episode = _episode("A Talk", duration_seconds=1800)
    speech = row_speech.RowSpeech(order=row_speech.ORDER_PODCAST_FIRST)
    inside = row_speech.compose_row(episode, speech, show_title="My Show", cross_show=False)
    assert "My Show" not in inside
    across = row_speech.compose_row(episode, speech, show_title="My Show", cross_show=True)
    assert across.startswith("My Show")


def test_every_part_of_a_row_can_be_switched_off() -> None:
    episode = _episode("A Talk", duration_seconds=1800)
    bare = row_speech.RowSpeech(
        say_podcast=False,
        say_date=False,
        duration=row_speech.DURATION_OFF,
        say_download=False,
    )
    assert row_speech.compose_row(episode, bare, show_title="My Show", cross_show=True) == "A Talk"


def test_a_missing_length_says_nothing_rather_than_zero() -> None:
    assert row_speech.format_length(0) == ""
    assert row_speech.format_length(3900) == "1 hour 5 minutes"


def test_the_row_order_migration_reads_the_old_boolean(tmp_path) -> None:
    from quill.core.podcasts.subscriptions import load_library, save_library

    library = PodcastLibrary()
    library.settings.announce_show_name_first = True
    save_library(tmp_path, library)
    assert load_library(tmp_path).extra_settings["row_order"] == "podcast_first"


# -- persistence -------------------------------------------------------------


def test_the_whole_chain_round_trips(tmp_path, library) -> None:
    from quill.core.podcasts.subscriptions import load_library, save_library

    show = library.find_show("s-daily")
    set_value(library, _def("speed"), 1.5, level=LEVEL_FOLDER, scope_id="f-news")
    set_value(library, _def("catalog_view_limit"), 25, level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, _def("announce_max_per_hour"), 4, level=LEVEL_GLOBAL)
    library.show_labels[show.id] = ["news"]
    check_state.record_failure(library, show)
    save_library(tmp_path, library)

    reloaded = load_library(tmp_path)
    restored = reloaded.find_show("s-daily")
    assert restored is not None
    assert value_of(reloaded, _def("speed"), show=restored) == 1.5
    assert value_of(reloaded, _def("catalog_view_limit"), show=restored) == 25
    assert show_policy.announce_budget(reloaded) == 4
    assert reloaded.labels_for(restored.id) == ["news"]
    assert check_state.failure_run(reloaded, restored) == 1


def test_an_empty_override_bucket_is_not_written(tmp_path, library) -> None:
    """An absent key and a stored key must stay different things."""
    import json

    from quill.core.podcasts.subscriptions import save_library

    show = library.find_show("s-daily")
    set_value(library, _def("speed"), 1.5, level=LEVEL_SHOW, scope_id=show.id)
    clear_value(library, _def("speed"), level=LEVEL_SHOW, scope_id=show.id)
    save_library(tmp_path, library)
    stored = json.loads((tmp_path / "podcasts_library.json").read_text(encoding="utf-8"))
    assert stored["scope_overrides"] == {}


def test_an_unknown_stored_value_reads_as_the_default(library) -> None:
    show = library.find_show("s-daily")
    library.scope_overrides[f"show:{show.id}"] = {"notify_priority": "shouting"}
    assert show_policy.notify_priority(library, show) == "normal"


def test_the_feed_reader_keeps_the_publishers_numbering() -> None:
    from quill.core.podcasts.feed_reader import parse_feed

    raw = b"""<?xml version="1.0"?><rss version="2.0"
      xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
      <title>S</title><item><title>One</title>
      <enclosure url="https://e/1.mp3" type="audio/mpeg"/>
      <guid>1</guid><itunes:season>2</itunes:season>
      <itunes:episode>14</itunes:episode>
      <itunes:episodeType>bonus</itunes:episodeType></item></channel></rss>"""
    episode = parse_feed(raw).episodes[0]
    assert (episode.season, episode.episode_number) == (2, 14)
    assert episode.episode_type == "bonus"
    assert episode.number_label() == "Season 2, episode 14"
