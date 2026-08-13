"""Tests for the inferred chapter tiers (transcript segmentation, silence scan).

These are the tiers that run only when every free, authored source came up
empty, so the bar is: find real topic boundaries, refuse to invent them when
there are none, and never claim a person wrote the titles.
"""

from pathlib import Path

from quill.core.podcasts.chapter_inference import (
    PODCAST_SILENCE,
    TimedCue,
    clear_cached_inference,
    load_cached_inference,
    parse_timed_cues,
    save_cached_inference,
    segment_transcript,
    silence_chapters_for_podcast,
)
from quill.core.podcasts.chapters import PodcastChapter

VTT = """WEBVTT

00:00:00.000 --> 00:00:04.000
Welcome to the show.

00:00:04.000 --> 00:00:08.500
Today we talk about gardening.
"""

SRT = """1
00:00:01,000 --> 00:00:03,000
First line here.

2
00:00:05,500 --> 00:00:07,000
Second line here.
"""

JSON_TRANSCRIPT = (
    '{"segments": [{"startTime": 1.5, "body": "hello there"},'
    ' {"startTime": 9.25, "body": "second segment"}]}'
)


# -- timed cue parsing ---------------------------------------------------------


def test_vtt_cues_keep_their_timings() -> None:
    """The searchable parser drops timings; chapters need them kept."""
    cues = parse_timed_cues(VTT)
    assert [c.start_ms for c in cues] == [0, 4000]
    assert cues[1].text == "Today we talk about gardening."


def test_srt_cues_parse_with_comma_milliseconds() -> None:
    cues = parse_timed_cues(SRT)
    assert [c.start_ms for c in cues] == [1000, 5500]
    assert cues[0].text == "First line here."


def test_srt_index_numbers_are_not_mistaken_for_text() -> None:
    assert all(not c.text.strip().isdigit() for c in parse_timed_cues(SRT))


def test_json_transcript_segments_carry_start_times() -> None:
    cues = parse_timed_cues(JSON_TRANSCRIPT, "application/json")
    assert [c.start_ms for c in cues] == [1500, 9250]


def test_multi_line_cue_is_joined_into_one() -> None:
    text = "WEBVTT\n\n00:00:02.000 --> 00:00:06.000\nfirst part\nsecond part\n"
    cues = parse_timed_cues(text)
    assert len(cues) == 1
    assert cues[0].text == "first part second part"


def test_unparseable_transcript_yields_no_cues_rather_than_raising() -> None:
    assert parse_timed_cues("just some prose with no timings at all") == []
    assert parse_timed_cues("") == []
    assert parse_timed_cues("{not json", "application/json") == []


# -- segmentation --------------------------------------------------------------


def _topic_cues(topics: list[tuple[str, int]], *, per_topic: int = 12) -> list[TimedCue]:
    """Build cues where each topic uses a distinct vocabulary."""
    cues: list[TimedCue] = []
    ms = 0
    for words, _ in topics:
        for index in range(per_topic):
            cues.append(TimedCue(ms, f"{words} number {index}"))
            ms += 15_000
    return cues


def test_segmentation_finds_the_boundary_between_two_topics() -> None:
    cues = _topic_cues([("garden compost soil seedling", 0), ("engine gearbox clutch piston", 1)])
    chapters = segment_transcript(cues, total_ms=cues[-1].start_ms + 15_000)

    assert len(chapters) >= 2
    assert chapters[0].start_ms == 0
    # The cut should land near where the vocabulary actually changes.
    changeover = 12 * 15_000
    assert any(abs(c.start_ms - changeover) <= 90_000 for c in chapters[1:])


def test_segmentation_refuses_to_invent_chapters_in_uniform_material() -> None:
    """An episode that never changes subject should produce none, not arbitrary ones."""
    cues = [TimedCue(i * 15_000, "compost soil garden seedling water") for i in range(40)]
    assert segment_transcript(cues, total_ms=40 * 15_000) == []


def test_segmentation_needs_enough_material_to_judge() -> None:
    assert segment_transcript([TimedCue(0, "hello world")], total_ms=600_000) == []
    assert segment_transcript([], total_ms=600_000) == []


def test_segmentation_honours_the_minimum_chapter_length() -> None:
    cues = _topic_cues([
        ("alpha beta gamma delta", 0),
        ("kitten puppy rabbit hamster", 1),
        ("zinc iron copper tin", 2),
    ])
    chapters = segment_transcript(cues, total_ms=cues[-1].start_ms + 15_000, min_chapter_ms=90_000)
    gaps = [b.start_ms - a.start_ms for a, b in zip(chapters, chapters[1:], strict=False)]
    assert all(gap >= 90_000 for gap in gaps)


def test_segmentation_titles_quote_the_episode_rather_than_inventing_one() -> None:
    cues = _topic_cues([("garden compost soil seedling", 0), ("engine gearbox clutch piston", 1)])
    chapters = segment_transcript(cues, total_ms=cues[-1].start_ms + 15_000)
    # Each title is drawn from that section's own words.
    assert "garden" in chapters[0].title.lower()
    assert all(c.title.strip() for c in chapters)


def test_segmentation_starts_at_zero_so_the_list_covers_the_episode() -> None:
    cues = _topic_cues([("garden compost soil seedling", 0), ("engine gearbox clutch piston", 1)])
    chapters = segment_transcript(cues, total_ms=cues[-1].start_ms + 15_000)
    assert chapters[0].start_ms == 0


def test_segmentation_is_deterministic() -> None:
    cues = _topic_cues([("garden compost soil seedling", 0), ("engine gearbox clutch piston", 1)])
    first = segment_transcript(cues, total_ms=400_000)
    second = segment_transcript(cues, total_ms=400_000)
    assert [(c.start_ms, c.title) for c in first] == [(c.start_ms, c.title) for c in second]


# -- silence tier --------------------------------------------------------------


def test_podcast_silence_floor_is_far_longer_than_the_audiobook_default() -> None:
    """A five-second floor would slice an hour of talk into hundreds of pieces."""
    assert PODCAST_SILENCE.min_chapter_ms == 90_000
    assert PODCAST_SILENCE.min_silence_s > 1.0


def test_silence_chapters_drop_a_single_whole_episode_section() -> None:
    """ "The whole episode" is not a chapter list."""
    assert silence_chapters_for_podcast([], total_ms=3_600_000) == []


def test_silence_chapters_convert_real_boundaries() -> None:
    silences = [(600.0, 603.0), (1500.0, 1503.5)]
    chapters = silence_chapters_for_podcast(silences, total_ms=2_400_000)
    assert len(chapters) >= 2
    assert chapters[0].start_ms == 0
    assert all(isinstance(c, PodcastChapter) for c in chapters)


# -- sidecar cache -------------------------------------------------------------


def test_cache_round_trips_with_its_source_label(tmp_path: Path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    chapters = [PodcastChapter(0, "One"), PodcastChapter(120_000, "Two")]

    save_cached_inference("show", "guid", chapters, "transcript")
    loaded, source = load_cached_inference("show", "guid")

    assert source == "transcript"
    assert [(c.start_ms, c.title) for c in loaded] == [(0, "One"), (120_000, "Two")]


def test_cache_is_ignored_when_the_audio_file_changed(tmp_path: Path, monkeypatch) -> None:
    """Chapters computed for one file must never be shown for different audio."""
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    audio = tmp_path / "episode.mp3"
    audio.write_bytes(b"x" * 100)

    save_cached_inference("show", "guid", [PodcastChapter(0, "One")], "audio", audio_path=audio)
    assert load_cached_inference("show", "guid", audio_path=audio)[0]

    audio.write_bytes(b"y" * 5000)  # re-downloaded, different file
    assert load_cached_inference("show", "guid", audio_path=audio) == ([], "")


def test_missing_cache_reads_as_empty(tmp_path: Path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    assert load_cached_inference("nope", "nope") == ([], "")


def test_clearing_the_cache_is_safe_when_absent(tmp_path: Path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    clear_cached_inference("nope", "nope")  # must not raise
