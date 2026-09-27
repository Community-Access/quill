"""Where a file's chapters come from, and where they land (chapter_plan)."""

from __future__ import annotations

from pathlib import Path

from quill.core.audio import chapter_plan as cp
from quill.core.audio.convert import ConversionJob, ConversionSpec, build_convert_command
from quill.core.speech.audio_tags_core import Chapter


def _chapters(*bounds: tuple[str, int, int]) -> list[Chapter]:
    return [Chapter(i, title, a, b) for i, (title, a, b) in enumerate(bounds)]


def test_every_format_has_a_home_for_chapters() -> None:
    from quill.core.audio.formats import OUTPUT_ORDER

    homes = {fmt: cp.chapter_home(fmt) for fmt in OUTPUT_ORDER}
    assert homes["mp3"] == homes["m4b"] == homes["mkv"] == homes["opus"] == "native"
    assert homes["ogg"] == homes["flac"] == "comments"
    assert homes["wav"] == homes["aiff"] == homes["ac3"] == "cue"
    assert set(homes.values()) == {"native", "comments", "cue"}


def test_every_n_minutes_folds_a_short_tail_into_the_last_part() -> None:
    parts = cp.every_n_minutes(11 * 60_000 + 30_000, 5)
    assert [(c.title, c.start_ms) for c in parts] == [
        ("Part 1", 0),
        ("Part 2", 300_000),
        ("Part 3", 600_000),
    ]
    assert parts[-1].end_ms == 690_000
    assert len(cp.every_n_minutes(5 * 60_000 + 20_000, 5)) == 1  # 20 s tail joins
    assert cp.every_n_minutes(30_000, 10)[0].end_ms == 30_000


def test_keep_only_part_clips_and_shifts_the_chapters() -> None:
    marks = _chapters(("A", 0, 12_000), ("B", 12_000, 24_000), ("C", 24_000, 36_000))
    clipped = cp.clip_chapters(marks, 13_000, 30_000)
    assert [(c.title, c.start_ms, c.end_ms) for c in clipped] == [
        ("B", 0, 11_000),
        ("C", 11_000, 17_000),
    ]
    assert cp.clip_chapters(marks, 11_800, 0)[0].title == "B"  # a 200 ms sliver is dropped


def test_a_chapter_list_beside_the_file_is_found_and_read(tmp_path: Path) -> None:
    source = tmp_path / "Lecture 3.mp3"
    source.write_bytes(b"x")
    (tmp_path / "Lecture 3.chapters.txt").write_text(
        "0:00 Welcome\n1:30 Questions\n4:05 Summary\n", encoding="utf-8"
    )
    found = cp.find_chapter_list(source, 5 * 60_000)
    assert found is not None
    path, chapters = found
    assert path.name == "Lecture 3.chapters.txt"
    assert [(c.title, c.start_ms) for c in chapters] == [
        ("Welcome", 0),
        ("Questions", 90_000),
        ("Summary", 245_000),
    ]


def test_a_plain_txt_beside_it_counts_only_if_it_is_a_chapter_list(tmp_path: Path) -> None:
    source = tmp_path / "talk.wav"
    source.write_bytes(b"x")
    (tmp_path / "talk.txt").write_text("A transcript, not chapters.\n", encoding="utf-8")
    assert cp.find_chapter_list(source, 60_000) is None
    note = cp.resolve_chapters(source, cp.LIST, total_ms=60_000)[1]
    assert "No chapter list beside it" in note


def test_resolve_keep_and_none() -> None:
    own = _chapters(("A", 0, 5000), ("B", 5000, 9000))
    assert cp.resolve_chapters(Path("x.mp3"), cp.NONE) == ([], "")
    assert cp.resolve_chapters(Path("x.mp3"), cp.KEEP) == (None, "")
    assert cp.resolve_chapters(Path("x.mp3"), cp.KEEP, own=own)[0] == own
    every = cp.resolve_chapters(Path("x.mp3"), cp.every(5), total_ms=11 * 60_000)[0]
    assert every is not None and len(every) == 3


def test_vorbis_comments_and_cue_text(tmp_path: Path) -> None:
    marks = _chapters(("Opening", 0, 8000), ("Close", 8000, 3_725_500))
    comments = cp.vorbis_chapter_comments(marks)
    assert comments == {
        "CHAPTER001": "00:00:00.000",
        "CHAPTER001NAME": "Opening",
        "CHAPTER002": "00:00:08.000",
        "CHAPTER002NAME": "Close",
    }
    wav = tmp_path / "book.wav"
    wav.write_bytes(b"RIFF")
    cue = cp.write_cue_beside(wav, marks)
    text = cue.read_text(encoding="utf-8")
    assert cue.name == "book.cue" and 'FILE "book.wav" WAVE' in text and text.count("TRACK") == 2
    assert "cue" in cp.place_chapters(wav, "wav", marks)
    assert cp.place_chapters(wav, "wav", marks[:1]) == ""  # one chapter is no chapters


def test_the_command_takes_a_chapter_list_or_removes_chapters() -> None:
    job = ConversionJob(Path("a.m4b"), Path("b.mp3"), ConversionSpec(fmt="mp3"))
    with_list = build_convert_command("ffmpeg", job, chapters_meta=Path("c.ffmeta"))
    at = with_list.index("c.ffmeta")
    assert with_list[at - 1] == "-i" and with_list[at + 1 : at + 3] == ["-map_chapters", "1"]
    removed = ConversionJob(
        Path("a.m4b"), Path("b.mp3"), ConversionSpec(fmt="mp3", chapter_source="none")
    )
    cmd = build_convert_command("ffmpeg", removed)
    assert cmd[cmd.index("-map_chapters") + 1] == "-1"
    assert "-map_chapters" not in build_convert_command("ffmpeg", job)
