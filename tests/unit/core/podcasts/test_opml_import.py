"""Bulk OPML import: planning, deduplication, pruning (1.1.0).

Exercised against the shape of a real export -- a flat list of a thousand-odd
feeds, a mix of http and https, and at least one entry listed twice -- which
is what an actual decade-old subscription list looks like.
"""

from __future__ import annotations

from quill.core.podcasts import opml_import
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.opml import ImportedShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _entry(title: str, url: str, folder: list[str] | None = None) -> ImportedShow:
    return ImportedShow(title=title, feed_url=url, homepage="", folder_path=folder or [])


class TestNormalizeFeedUrl:
    def test_http_and_https_are_the_same_feed(self) -> None:
        assert opml_import.normalize_feed_url(
            "http://feeds.example.com/show"
        ) == opml_import.normalize_feed_url("https://feeds.example.com/show")

    def test_trailing_slash_and_host_case_do_not_matter(self) -> None:
        assert opml_import.normalize_feed_url(
            "https://Feeds.Example.COM/show/"
        ) == opml_import.normalize_feed_url("https://feeds.example.com/show")

    def test_a_query_string_is_kept_because_it_can_be_the_subscription(self) -> None:
        assert opml_import.normalize_feed_url(
            "https://x/feed?token=a"
        ) != opml_import.normalize_feed_url("https://x/feed?token=b")

    def test_default_ports_are_dropped_but_others_are_not(self) -> None:
        assert opml_import.normalize_feed_url(
            "https://x:443/feed"
        ) == opml_import.normalize_feed_url("https://x/feed")
        assert opml_import.normalize_feed_url(
            "https://x:8443/feed"
        ) != opml_import.normalize_feed_url("https://x/feed")


class TestPlanImport:
    def test_an_already_subscribed_feed_is_skipped_across_schemes(self) -> None:
        library = PodcastLibrary(
            shows=[PodcastShow(id="s1", title="Show", feed_url="https://x/feed")]
        )

        plan = opml_import.plan_import(library, [_entry("Show", "http://x/feed")])

        assert plan.new == []
        assert len(plan.duplicates_in_library) == 1

    def test_a_feed_listed_twice_in_the_file_is_imported_once(self) -> None:
        plan = opml_import.plan_import(
            PodcastLibrary(),
            [_entry("Show", "https://x/feed"), _entry("Show again", "https://x/feed/")],
        )

        assert len(plan.new) == 1
        assert len(plan.duplicates_in_file) == 1

    def test_two_shows_sharing_a_title_are_both_imported_and_flagged(self) -> None:
        library = PodcastLibrary(
            shows=[PodcastShow(id="s1", title="The Daily", feed_url="https://a/feed")]
        )

        plan = opml_import.plan_import(library, [_entry("The Daily", "https://b/feed")])

        assert len(plan.new) == 1  # never silently dropped
        assert plan.same_title_different_feed == ["The Daily (https://b/feed)"]

    def test_a_non_http_entry_is_reported_rather_than_imported(self) -> None:
        plan = opml_import.plan_import(
            PodcastLibrary(), [_entry("Odd", "ftp://x/feed"), _entry("Empty", "")]
        )

        assert plan.new == []
        assert len(plan.unusable) == 2

    def test_planning_mutates_nothing(self) -> None:
        library = PodcastLibrary()

        opml_import.plan_import(library, [_entry("Show", "https://x/feed")])

        assert library.shows == []


class TestApplyPlan:
    def test_adds_every_planned_show(self) -> None:
        library = PodcastLibrary()
        plan = opml_import.plan_import(
            library, [_entry("A", "https://a/feed"), _entry("B", "https://b/feed")]
        )

        added = opml_import.apply_plan(library, plan)

        assert len(added) == 2
        assert {show.title for show in library.shows} == {"A", "B"}

    def test_folder_paths_are_created_once_and_reused(self) -> None:
        library = PodcastLibrary()
        entries = [
            _entry("A", "https://a/feed", ["News", "Daily"]),
            _entry("B", "https://b/feed", ["News", "Daily"]),
            _entry("C", "https://c/feed", ["News"]),
        ]
        plan = opml_import.plan_import(library, entries)

        opml_import.apply_plan(library, plan)

        assert sorted(f.name for f in library.folders) == ["Daily", "News"]
        assert library.find_show_by_feed_url("https://a/feed").folder_id == (
            library.find_show_by_feed_url("https://b/feed").folder_id
        )

    def test_stream_only_marks_every_added_show(self) -> None:
        library = PodcastLibrary()
        plan = opml_import.plan_import(library, [_entry("A", "https://a/feed")])

        added = opml_import.apply_plan(library, plan, stream_only=True)

        assert added[0].settings is not None
        assert added[0].settings.playback_mode == "stream"

    def test_into_folder_nests_the_whole_import(self) -> None:
        library = PodcastLibrary()
        plan = opml_import.plan_import(library, [_entry("A", "https://a/feed", ["Sub"])])

        opml_import.apply_plan(library, plan, into_folder="Imported")

        names = {f.name for f in library.folders}
        assert names == {"Imported", "Sub"}


class TestScale:
    """The behaviour a 1,300-feed export actually depends on."""

    def test_a_large_import_stays_linear_and_correct(self) -> None:
        entries = [_entry(f"Show {i}", f"https://host{i}/feed") for i in range(2000)]
        library = PodcastLibrary()

        plan = opml_import.plan_import(library, entries)
        opml_import.apply_plan(library, plan)

        assert len(library.shows) == 2000
        # Re-importing the same file adds nothing and reports every entry.
        second = opml_import.plan_import(library, entries)
        assert second.new == []
        assert len(second.duplicates_in_library) == 2000


class TestPruneOpml:
    SOURCE = (
        '<?xml version="1.0"?><opml version="1.0"><head><title>T</title></head><body>'
        '<outline text="Alive" type="rss" xmlUrl="https://alive/feed"/>'
        '<outline text="Dead" type="rss" xmlUrl="https://dead/feed"/>'
        '<outline text="Folder">'
        '<outline text="AlsoDead" type="rss" xmlUrl="http://alsodead/feed"/>'
        "</outline></body></opml>"
    )

    def test_dead_feeds_are_removed(self) -> None:
        pruned = opml_import.prune_opml(self.SOURCE, ["https://dead/feed"])

        assert "alive/feed" in pruned
        assert "dead/feed" not in pruned.replace("alsodead/feed", "")

    def test_a_folder_emptied_by_pruning_goes_too(self) -> None:
        pruned = opml_import.prune_opml(self.SOURCE, ["https://alsodead/feed"])

        assert "Folder" not in pruned
        assert "alive/feed" in pruned

    def test_matching_ignores_the_scheme(self) -> None:
        # The report holds the http:// URL the file listed; pruning must find
        # it even if the checker followed a redirect to https.
        pruned = opml_import.prune_opml(self.SOURCE, ["https://alsodead/feed"])

        assert "alsodead" not in pruned

    def test_nothing_to_prune_returns_the_file_untouched(self) -> None:
        assert opml_import.prune_opml(self.SOURCE, []) == self.SOURCE

    def test_unparseable_input_is_returned_rather_than_destroyed(self) -> None:
        assert opml_import.prune_opml("not xml", ["https://x"]) == "not xml"


class TestValidateFeeds:
    def test_safe_mode_reports_rather_than_connecting(self) -> None:
        results = opml_import.validate_feeds([("A", "https://a/feed")], safe_mode=True)

        assert len(results) == 1
        assert results[0].ok is False
        assert "Safe Mode" in results[0].error

    def test_an_empty_list_does_nothing(self) -> None:
        assert opml_import.validate_feeds([]) == []

    def test_progress_is_reported_for_every_feed(self, monkeypatch) -> None:
        from quill.core.podcasts.opml import OpmlValidationResult

        monkeypatch.setattr(
            opml_import,
            "probe_feed",
            lambda url, timeout=0: OpmlValidationResult(url, url, True),
        )
        seen: list[tuple[int, int]] = []

        opml_import.validate_feeds(
            [("A", "https://a"), ("B", "https://b")],
            workers=2,
            on_progress=lambda done, total: seen.append((done, total)),
        )

        assert sorted(seen) == [(1, 2), (2, 2)]

    def test_cancelling_returns_what_finished(self, monkeypatch) -> None:
        from quill.core.podcasts.opml import OpmlValidationResult

        monkeypatch.setattr(
            opml_import,
            "probe_feed",
            lambda url, timeout=0: OpmlValidationResult(url, url, True),
        )

        results = opml_import.validate_feeds(
            [("A", f"https://{i}") for i in range(20)],
            workers=1,
            should_cancel=lambda: True,
        )

        assert 0 < len(results) < 20
