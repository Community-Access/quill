"""Listening statistics, auto-download, inbox caps, storage (1.1.0)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.podcasts import acquisition, retention, stats
from quill.core.podcasts.inbox import inbox_pairs, is_trimmed, trim_inbox, untrim_episode
from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


def _ago_iso(days: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _episode(guid: str, *, days_old: float = 0, **kwargs) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://x/{guid}.mp3",
        published=_ago_iso(days_old),
        **kwargs,
    )


class TestFormatDuration:
    def test_speaks_hours_and_minutes_in_words(self) -> None:
        assert stats.format_duration(3 * 3600 + 47 * 60) == "3 hours, 47 minutes"

    def test_a_whole_hour_omits_the_pointless_zero_minutes(self) -> None:
        assert stats.format_duration(3600) == "1 hour"

    def test_under_a_minute_reports_seconds_rather_than_zero(self) -> None:
        assert stats.format_duration(12) == "12 seconds"

    def test_never_uses_a_clock_face(self) -> None:
        assert ":" not in stats.format_duration(9999)


class TestSummarize:
    def _sessions(self) -> list[stats.ListeningSession]:
        return [
            stats.ListeningSession("s1", "e1", seconds=600, speed=1.0, date=_ago_iso(1)),
            stats.ListeningSession(
                "s1", "e2", seconds=600, speed=1.5, completed=True, date=_ago_iso(2)
            ),
            stats.ListeningSession("s2", "e3", seconds=300, speed=1.0, date=_ago_iso(200)),
        ]

    def test_all_time_counts_everything(self) -> None:
        summary = stats.summarize(self._sessions(), period="all")

        assert summary.sessions == 3
        assert summary.total_seconds == 1500

    def test_a_period_excludes_older_sessions(self) -> None:
        summary = stats.summarize(self._sessions(), period="week")

        assert summary.sessions == 2
        assert summary.total_seconds == 1200

    def test_time_saved_by_speed_is_arithmetic_not_a_guess(self) -> None:
        summary = stats.summarize(self._sessions(), period="all")

        # 600 seconds at 1.5x buys exactly 300 seconds of extra content.
        assert summary.saved_by_speed_seconds == 300

    def test_unmeasured_trimming_is_absent_rather_than_zero(self) -> None:
        summary = stats.summarize(self._sessions(), period="all")

        assert summary.trim_measured is False
        assert summary.saved_by_trim_seconds == 0

    def test_measured_trimming_is_counted_and_flagged(self) -> None:
        sessions = [
            stats.ListeningSession(
                "s1", "e1", seconds=600, smart_speed_saved_seconds=45, date=_ago_iso(1)
            )
        ]

        summary = stats.summarize(sessions, period="all")

        assert summary.trim_measured is True
        assert summary.saved_by_trim_seconds == 45

    def test_per_show_totals_come_back_largest_first(self) -> None:
        summary = stats.summarize(self._sessions(), period="all")

        assert [row.show_id for row in summary.shows] == ["s1", "s2"]
        assert summary.shows[0].seconds == 1200

    def test_episodes_completed_counts_only_finished_sessions(self) -> None:
        assert stats.summarize(self._sessions(), period="all").episodes_completed == 1


class TestStatsStore:
    def test_round_trips_through_disk(self, tmp_path) -> None:
        session = stats.ListeningSession("s1", "e1", seconds=60, date=_ago_iso(0))

        stats.append_session(tmp_path, session)

        loaded = stats.load_sessions(tmp_path)
        assert len(loaded) == 1
        assert loaded[0].show_id == "s1"

    def test_an_empty_session_is_not_recorded(self, tmp_path) -> None:
        stats.append_session(tmp_path, stats.ListeningSession("s1", "e1", seconds=0))

        assert stats.load_sessions(tmp_path) == []

    def test_pruning_drops_sessions_past_the_retention_window(self) -> None:
        sessions = [
            stats.ListeningSession("s1", "e1", seconds=60, date=_ago_iso(200)),
            stats.ListeningSession("s1", "e2", seconds=60, date=_ago_iso(1)),
        ]

        kept = stats.prune(sessions, retention_days=90)

        assert [s.episode_guid for s in kept] == ["e2"]

    def test_an_unreadable_date_is_kept_not_discarded(self) -> None:
        sessions = [stats.ListeningSession("s1", "e1", seconds=60, date="nonsense")]

        assert stats.prune(sessions, retention_days=1) == sessions

    def test_a_missing_file_reads_as_empty(self, tmp_path) -> None:
        assert stats.load_sessions(tmp_path / "nope") == []

    def test_csv_has_a_header_and_one_row_per_session(self) -> None:
        sessions = [stats.ListeningSession("s1", "e1", seconds=60, date=_ago_iso(0))]

        text = stats.to_csv(sessions, show_titles={"s1": "Show One"})

        assert text.splitlines()[0].startswith("date,show,")
        assert "Show One" in text
        assert len(text.strip().splitlines()) == 2


class TestAutoDownload:
    def _library(self, count: int, *, mode: str = "download") -> tuple[PodcastLibrary, PodcastShow]:
        episodes = [_episode(f"e{i}", days_old=i) for i in range(5)]
        show = PodcastShow(id="s1", title="Show", feed_url="https://x/f", episodes=episodes)
        library = PodcastLibrary(shows=[show])
        library.apply_show_override(show, auto_download_count=count, playback_mode=mode)
        return library, show

    def test_off_by_default_downloads_nothing(self) -> None:
        library, show = self._library(0)

        assert acquisition.episodes_to_auto_download(library, show) == []

    def test_takes_the_newest_n(self) -> None:
        library, show = self._library(2)

        wanted = acquisition.episodes_to_auto_download(library, show)

        assert [e.guid for e in wanted] == ["e0", "e1"]

    def test_minus_one_takes_the_whole_catalog(self) -> None:
        library, show = self._library(-1)

        assert len(acquisition.episodes_to_auto_download(library, show)) == 5

    def test_always_sync_still_means_the_whole_catalog(self) -> None:
        library, show = self._library(0)
        library.apply_show_override(show, always_sync_full_catalog=True)

        assert len(acquisition.episodes_to_auto_download(library, show)) == 5

    def test_already_downloaded_episodes_are_excluded(self) -> None:
        library, show = self._library(-1)
        show.episodes[0].downloaded_path = "C:/somewhere.mp3"

        wanted = acquisition.episodes_to_auto_download(library, show)

        assert "e0" not in [e.guid for e in wanted]

    def test_a_stream_only_override_is_excluded(self) -> None:
        library, show = self._library(-1)
        show.episodes[0].mode_override = "stream"

        assert "e0" not in [e.guid for e in acquisition.episodes_to_auto_download(library, show)]

    def test_a_stream_mode_show_never_auto_downloads(self) -> None:
        library, show = self._library(3, mode="stream")

        assert acquisition.episodes_to_auto_download(library, show) == []

    def test_a_queued_episode_is_fetched_whatever_its_age(self) -> None:
        library, show = self._library(1)

        wanted = acquisition.episodes_to_auto_download(
            library, show, queued_guids=frozenset({"e4"})
        )

        assert {e.guid for e in wanted} == {"e0", "e4"}

    def test_the_inbox_toggle_is_off_by_default(self) -> None:
        library, show = self._library(0)
        show.route_to_inbox = True

        wanted = acquisition.episodes_to_auto_download(library, show, inbox_guids=frozenset({"e3"}))

        assert wanted == []


class TestAutoQueue:
    def test_new_episodes_of_an_auto_queue_show_are_queued(self) -> None:
        episodes = [_episode("e1"), _episode("e2")]
        show = PodcastShow(id="s1", title="Show", episodes=episodes, auto_queue=True)
        library = PodcastLibrary(shows=[show])

        assert acquisition.route_new_episodes(library, show, episodes) == 2
        assert len(library.queue) == 2

    def test_nothing_happens_when_the_show_does_not_auto_queue(self) -> None:
        episodes = [_episode("e1")]
        show = PodcastShow(id="s1", title="Show", episodes=episodes)
        library = PodcastLibrary(shows=[show])

        assert acquisition.route_new_episodes(library, show, episodes) == 0

    def test_an_already_played_episode_is_skipped(self) -> None:
        episodes = [_episode("e1", played=True)]
        show = PodcastShow(id="s1", title="Show", episodes=episodes, auto_queue=True)
        library = PodcastLibrary(shows=[show])

        assert acquisition.route_new_episodes(library, show, episodes) == 0

    def test_queued_items_carry_a_timestamp_so_expiry_can_measure_them(self) -> None:
        episodes = [_episode("e1")]
        show = PodcastShow(id="s1", title="Show", episodes=episodes, auto_queue=True)
        library = PodcastLibrary(shows=[show])

        acquisition.route_new_episodes(library, show, episodes)

        assert library.queue[0].added_at


class TestInboxCaps:
    def _library(self, *, max_episodes: int = 0, age_hours: int = 0) -> tuple:
        episodes = [_episode(f"e{i}", days_old=i) for i in range(5)]
        show = PodcastShow(id="s1", title="Show", episodes=episodes, route_to_inbox=True)
        library = PodcastLibrary(shows=[show])
        library.apply_show_override(
            show, inbox_max_episodes=max_episodes, inbox_age_limit_hours=age_hours
        )
        return library, show

    def test_no_caps_means_nothing_is_trimmed(self) -> None:
        library, _show = self._library()

        assert trim_inbox(library) == []
        assert len(inbox_pairs(library)) == 5

    def test_the_count_cap_keeps_the_newest(self) -> None:
        library, _show = self._library(max_episodes=2)

        trimmed = trim_inbox(library)

        assert len(trimmed) == 3
        assert {e.guid for _s, e in inbox_pairs(library)} == {"e0", "e1"}

    def test_the_age_cap_drops_older_episodes(self) -> None:
        # 36 hours, not 48, so no episode sits *exactly* on the cap. The
        # episodes are built 0, 1, 2, 3 and 4 days old from one `now()` and
        # trimmed against a second one, and `trim_inbox` keeps an episode whose
        # age equals the cap (`stamped < cutoff`). With a 48-hour cap the
        # two-day-old episode is on the line and the answer depends on whether
        # those two `now()` calls landed in the same clock tick -- which on
        # Windows, where the wall clock moves in ~15ms steps, they sometimes do.
        # 36 hours falls squarely between the one- and two-day episodes, so the
        # test measures the rule instead of the clock.
        library, _show = self._library(age_hours=36)

        trim_inbox(library)

        assert {e.guid for _s, e in inbox_pairs(library)} == {"e0", "e1"}

    def test_trimming_never_deletes_the_episode(self) -> None:
        library, show = self._library(max_episodes=1)

        trim_inbox(library)

        assert len(show.episodes) == 5
        assert all(not e.played for e in show.episodes)

    def test_a_started_episode_is_never_trimmed(self) -> None:
        library, show = self._library(max_episodes=1)
        show.episodes[4].position_ms = 5000

        trim_inbox(library)

        assert not is_trimmed(library, show, show.episodes[4])

    def test_a_queued_episode_is_never_trimmed(self) -> None:
        library, show = self._library(max_episodes=1)
        library.queue.append(QueueItem(show_id=show.id, episode_guid="e4"))

        trim_inbox(library)

        assert not is_trimmed(library, show, show.episodes[4])

    def test_a_manually_filed_episode_is_never_trimmed(self) -> None:
        from quill.core.podcasts.inbox import add_inbox_folder, file_episode

        library, show = self._library(max_episodes=1)
        folder = add_inbox_folder(library, "Later")
        file_episode(library, show, show.episodes[4], folder.id)

        trim_inbox(library)

        assert not is_trimmed(library, show, show.episodes[4])

    def test_untrim_puts_it_back(self) -> None:
        library, show = self._library(max_episodes=1)
        trim_inbox(library)
        trimmed_episode = next(e for e in show.episodes if is_trimmed(library, show, e))

        assert untrim_episode(library, show, trimmed_episode) is True
        assert not is_trimmed(library, show, trimmed_episode)

    def test_trimming_is_idempotent(self) -> None:
        library, _show = self._library(max_episodes=2)

        assert len(trim_inbox(library)) == 3
        assert trim_inbox(library) == []


class TestStorage:
    def _library(self, tmp_path, *, count: int = 3) -> tuple:
        episodes = []
        for i in range(count):
            media = tmp_path / f"e{i}.mp3"
            media.write_bytes(b"x" * 1000)
            episodes.append(
                _episode(f"e{i}", days_old=i * 10, downloaded_path=str(media), played=True)
            )
        show = PodcastShow(id="s1", title="Show", episodes=episodes)
        library = PodcastLibrary(shows=[show])
        return library, show

    def test_total_bytes_sums_the_files(self, tmp_path) -> None:
        library, _show = self._library(tmp_path)

        assert retention.total_download_bytes(library) == 3000

    def test_per_show_usage_reports_files_and_bytes(self, tmp_path) -> None:
        library, _show = self._library(tmp_path)

        rows = retention.per_show_usage(library)

        assert rows[0][1] == 3
        assert rows[0][2] == 3000

    def test_the_age_limit_deletes_old_downloads(self, tmp_path) -> None:
        library, show = self._library(tmp_path)
        # Episodes are 0, 10, and 20 days old; a five-day limit takes the
        # two older ones and leaves today's.
        library.apply_show_override(show, download_retention_days=5)

        removed = retention.apply_age_limit(library)

        assert {e.guid for _s, e, _size in removed} == {"e1", "e2"}
        assert show.episodes[0].downloaded_path

    def test_a_queued_episode_survives_the_age_limit(self, tmp_path) -> None:
        library, show = self._library(tmp_path)
        library.apply_show_override(show, download_retention_days=1)
        library.queue.append(QueueItem(show_id=show.id, episode_guid="e2"))

        retention.apply_age_limit(library)

        assert show.episodes[2].downloaded_path

    def test_a_part_played_episode_survives_the_age_limit(self, tmp_path) -> None:
        library, show = self._library(tmp_path)
        library.apply_show_override(show, download_retention_days=1)
        show.episodes[2].played = False
        show.episodes[2].position_ms = 1234

        retention.apply_age_limit(library)

        assert show.episodes[2].downloaded_path

    def test_the_cap_evicts_until_it_fits(self, tmp_path) -> None:
        library, _show = self._library(tmp_path)
        library.settings.storage_cap_mb = 0  # explicit: set via cap_bytes below

        removed = retention.enforce_storage_cap(library, cap_bytes=1500)

        assert len(removed) == 2
        assert retention.total_download_bytes(library) <= 1500

    def test_the_cap_evicts_oldest_played_first(self, tmp_path) -> None:
        library, _show = self._library(tmp_path)

        removed = retention.enforce_storage_cap(library, cap_bytes=2000)

        assert [e.guid for _s, e, _size in removed] == ["e2"]

    def test_a_cap_of_zero_is_no_cap(self, tmp_path) -> None:
        library, _show = self._library(tmp_path)

        assert retention.enforce_storage_cap(library, cap_bytes=0) == []

    def test_the_cap_never_evicts_a_protected_episode(self, tmp_path) -> None:
        library, show = self._library(tmp_path)
        for episode in show.episodes:
            library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid))

        removed = retention.enforce_storage_cap(library, cap_bytes=1)

        assert removed == []
        assert retention.total_download_bytes(library) == 3000

    def test_format_bytes_reads_naturally(self) -> None:
        assert retention.format_bytes(512) == "512 bytes"
        assert retention.format_bytes(2 * 1024 * 1024) == "2.0 MB"
