"""ear.md A3-A9: the questions Cast asks, and the answers it refuses to trust."""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.podcasts import ai_listening as ai
from quill.core.podcasts.models import PodcastFolder, PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary


def _ep(guid: str, title: str, minutes: int, published: str = "2026-09-01T06:00:00+00:00"):
    return PodcastEpisode(
        guid=guid,
        title=title,
        audio_url="https://x.invalid/a.mp3",
        duration_seconds=minutes * 60,
        published=published,
        description="<p>Notes about <b>braille</b>.</p>",
    )


def test_no_question_carries_an_address_or_a_position() -> None:
    show = PodcastShow(id="s", title="Show", feed_url="https://secret.invalid/feed")
    episode = _ep("g", "Ep", 30)
    episode.position_ms = 123_456
    for prompt in (
        ai.about_show_prompt(show),
        ai.for_me_prompt(show, episode, "interviews"),
        ai.summary_prompt(episode, "")[0],
        ai.listening_run_prompt([(show, episode)], 40),
    ):
        assert "secret.invalid" not in prompt
        assert "123456" not in prompt and "<b>" not in prompt


def test_a_summary_says_which_text_it_used() -> None:
    episode = _ep("g", "Ep", 30)
    assert ai.summary_prompt(episode, "")[1] == "the show notes"
    assert ai.summary_prompt(episode, "Hello and welcome")[1] == "the transcript"


def test_a_run_is_measured_by_cast_and_drops_what_does_not_resolve() -> None:
    show = PodcastShow(id="s", title="Show", feed_url="")
    candidates = [
        (show, _ep("a", "Short", 10)),
        (show, _ep("b", "Long", 50)),
        (show, _ep("c", "Mid", 20)),
    ]
    answer = (
        '{"run": [{"number": 1, "reason": "quick"}, {"number": 2}, '
        '{"number": 3}, {"number": 9}, {"number": 1}]}'
    )
    picks, discarded = ai.read_listening_run(answer, candidates, 40)
    assert [p.episode.guid for p in picks] == ["a", "c"]
    assert sum(p.minutes for p in picks) == 30
    assert len(discarded) == 3


def test_playlist_rules_resolve_names_and_drop_inventions() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="The Daily", feed_url=""))
    library.folders.append(PodcastFolder(id="f1", name="News"))
    answer = (
        '{"name": "Quick news", "episode_status": "unplayed", "max_duration_minutes": 20, '
        '"shows": ["The Daily", "Made Up"], "folders": ["News"], "published_within_days": 14}'
    )
    name, rules, discarded = ai.read_playlist_rules(answer, library)
    assert name == "Quick news"
    assert rules.show_ids == ["s1"] and rules.folder_ids == ["f1"]
    assert rules.max_duration_minutes == 20 and rules.episode_status == "unplayed"
    assert discarded == ["No podcast called Made Up."]
    assert "At most 20 minutes long." in ai.describe_rules(rules, library)


def test_chapter_titles_only_for_real_chapters() -> None:
    from quill.core.podcasts.chapters import PodcastChapter

    chapters = [
        PodcastChapter(start_ms=0, title="Part 1"),
        PodcastChapter(start_ms=60_000, title="Part 2"),
    ]
    answer = (
        '{"titles": [{"chapter": 1, "title": "Welcome and news"}, '
        '{"chapter": 5, "title": "x"}, {"chapter": 2, "title": "Part 2"}]}'
    )
    found, discarded = ai.read_chapter_titles(answer, chapters)
    assert [(c.index, c.new) for c in found] == [(0, "Welcome and news")]
    assert len(discarded) == 1


def test_tidy_finds_dormant_duplicate_and_failing_podcasts() -> None:
    library = PodcastLibrary()
    old = PodcastShow(id="old", title="Old Show", feed_url="x")
    old.episodes.append(_ep("o", "Last", 30, "2023-01-01T00:00:00+00:00"))
    library.add_show(old)
    library.add_show(PodcastShow(id="a", title="The Daily", feed_url="y"))
    library.add_show(PodcastShow(id="b", title="The Daily!", feed_url="z"))
    library.add_show(PodcastShow(id="c", title="Broken", feed_url="w"))
    rows = ai.tidy_rows(library, now=datetime(2026, 10, 3, tzinfo=UTC), failing={"c"})
    assert {(r.show_id, r.action) for r in rows} == {
        ("old", "pause"),
        ("b", "unfollow"),
        ("c", "pause"),
    }
