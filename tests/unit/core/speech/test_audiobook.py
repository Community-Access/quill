"""Tests for the folder-to-audiobook builder (§1.5 ChapterForge surface)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech import audiobook
from quill.core.speech.audiobook import (
    AudiobookChapter,
    build_audiobook,
    build_audiobook_command,
    build_chapter_list,
    build_concat_list,
    chapters_from_plan,
    find_cover,
    natural_key,
    scan_audio_folder,
    title_from_filename,
)


def test_natural_key_orders_numbers_numerically() -> None:
    names = ["track10.mp3", "track2.mp3", "track1.mp3"]
    assert sorted(names, key=natural_key) == ["track1.mp3", "track2.mp3", "track10.mp3"]


def test_title_from_filename_strips_track_prefix() -> None:
    assert title_from_filename(Path("01 - The Beginning.mp3")) == "The Beginning"
    assert title_from_filename(Path("02_Chapter_Two.mp3")) == "Chapter Two"
    assert title_from_filename(Path("3) Onward.m4a")) == "Onward"
    # A bare numeric name leaves nothing meaningful → "" (caller adds "Chapter N").
    assert title_from_filename(Path("01.mp3")) == ""
    # A four-digit year is not a track prefix.
    assert title_from_filename(Path("1984 Orwell.mp3")) == "1984 Orwell"


def test_find_cover_prefers_named_images(tmp_path: Path) -> None:
    (tmp_path / "random.png").write_bytes(b"x")
    (tmp_path / "cover.jpg").write_bytes(b"x")
    assert find_cover(tmp_path) == tmp_path / "cover.jpg"


def test_find_cover_none_when_no_images(tmp_path: Path) -> None:
    (tmp_path / "a.mp3").write_bytes(b"x")
    assert find_cover(tmp_path) is None


def test_scan_audio_folder_natural_sorted(tmp_path: Path) -> None:
    for name in ("10.mp3", "2.mp3", "1.mp3", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    found = scan_audio_folder(tmp_path)
    assert [p.name for p in found] == ["1.mp3", "2.mp3", "10.mp3"]


def test_build_concat_list_quotes_and_escapes() -> None:
    doc = build_concat_list([Path("/a/b.mp3"), Path("/a/it's.mp3")])
    lines = doc.strip().splitlines()
    assert lines[0].startswith("file ") and "b.mp3" in lines[0]
    # A single quote in a path is escaped for the concat demuxer.
    assert "'\\''" in lines[1]


def test_build_chapter_list_uses_titles_and_durations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audiobook, "title_from_filename", lambda p: p.stem.replace("_", " "))
    import quill.core.speech.ffmpeg as ffmpeg

    monkeypatch.setattr(ffmpeg, "probe_duration_ms", lambda p, **k: 1500)
    chapters = build_chapter_list([Path("a/One.mp3"), Path("a/01.mp3")])
    assert chapters[0].title == "One" and chapters[0].duration_ms == 1500
    # Empty derived title falls back to "Chapter N".
    monkeypatch.setattr(audiobook, "title_from_filename", lambda p: "")
    fallback = build_chapter_list([Path("a/01.mp3")])
    assert fallback[0].title == "Chapter 1"


def test_audiobook_command_m4b_maps_chapters_cover_and_uses_ipod() -> None:
    cmd = build_audiobook_command(
        "ffmpeg",
        Path("list.txt"),
        Path("out.m4b"),
        "m4b",
        ffmetadata=Path("meta.ffmeta"),
        cover=Path("cover.jpg"),
        map_chapters=True,
    )
    assert cmd[cmd.index("-f", cmd.index("concat") + 1) :][1] == "ipod"  # output muxer
    assert "concat" in cmd
    assert "-map_chapters" in cmd
    assert "attached_pic" in cmd
    assert cmd[cmd.index("-c:a") + 1] == "aac"
    assert cmd[-1] == "out.m4b"


def test_chapters_from_plan_merges_and_sums_durations(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.speech.ffmpeg as ffmpeg

    monkeypatch.setattr(ffmpeg, "probe_duration_ms", lambda p, **k: 1000)
    plan = [
        ("Intro", [Path("a/01.mp3")]),
        ("Body", [Path("a/02.mp3"), Path("a/03.mp3")]),  # a merged chapter
        ("", [Path("a/04.mp3")]),  # empty title -> "Chapter N"
    ]
    chapters = chapters_from_plan(plan)
    assert [c.title for c in chapters] == ["Intro", "Body", "Chapter 3"]
    # The merged chapter carries both files and the summed duration, one marker.
    body = chapters[1]
    assert body.path == Path("a/02.mp3")
    assert body.extra_paths == [Path("a/03.mp3")]
    assert body.all_paths == [Path("a/02.mp3"), Path("a/03.mp3")]
    assert body.duration_ms == 2000


def test_build_audiobook_command_acx_adds_loudnorm_filter() -> None:
    cmd = build_audiobook_command(
        "ffmpeg", Path("list.txt"), Path("out.m4b"), "m4b", acx_normalize=True
    )
    assert "-af" in cmd
    flt = cmd[cmd.index("-af") + 1]
    assert flt.startswith("loudnorm=")
    # Without the flag there is no audio filter (byte-identical to the old argv).
    plain = build_audiobook_command("ffmpeg", Path("list.txt"), Path("out.m4b"), "m4b")
    assert "-af" not in plain


def test_audiobook_command_mp3_skips_chapter_mapping() -> None:
    cmd = build_audiobook_command(
        "ffmpeg", Path("list.txt"), Path("out.mp3"), "mp3", ffmetadata=Path("m.ffmeta")
    )
    assert "-map_chapters" not in cmd  # MP3 chapters come from mutagen afterwards
    assert cmd[cmd.index("-c:a") + 1] == "libmp3lame"


def test_build_audiobook_rejects_empty_and_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_audiobook([], tmp_path / "out.m4b")
    chapter = AudiobookChapter(path=tmp_path / "missing.mp3", title="x", duration_ms=1000)
    with pytest.raises(ValueError):
        build_audiobook([chapter], tmp_path / "out.xyz", output_format="xyz")


def test_build_audiobook_skips_polish_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No polish kwargs -> prepare_chapter_files is never called.

    Stubs ffmpeg and the subprocess runner so the test stays millisecond-fast
    and does not require a real ffmpeg binary.
    """
    src = tmp_path / "src"
    src.mkdir()
    src_file = src / "01.mp3"
    src_file.write_bytes(b"")  # existence is what build_audiobook checks
    out = tmp_path / "book.m4b"
    chapter = AudiobookChapter(path=src_file, title="Chapter 1", duration_ms=1000)

    called = {"polish": 0}

    def fake_prepare(paths, _work, **_kwargs):  # type: ignore[no-untyped-def]
        called["polish"] += 1
        return paths

    monkeypatch.setattr("quill.core.speech.audio_edit.prepare_chapter_files", fake_prepare)
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_run(args, **_kwargs):  # type: ignore[no-untyped-def]
        for a in args:
            if a.endswith(".m4b") or a.endswith(".mp3"):
                Path(a).write_bytes(b"x")
                break
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", fake_run)

    result = build_audiobook([chapter], out, output_format="m4b")
    assert result.chapter_count == 1
    assert called["polish"] == 0


def test_build_audiobook_runs_polish_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any polish flag -> prepare_chapter_files is called with the right kwargs."""
    src = tmp_path / "src"
    src.mkdir()
    src_file = src / "01.mp3"
    src_file.write_bytes(b"")
    out = tmp_path / "book.m4b"
    chapter = AudiobookChapter(path=src_file, title="Chapter 1", duration_ms=1000)

    captured: dict[str, object] = {}

    def fake_prepare(paths, work, **kwargs):  # type: ignore[no-untyped-def]
        captured["paths"] = list(paths)
        captured["work"] = work
        captured["kwargs"] = kwargs
        # Pretend polish produced a new file alongside the original.
        work.mkdir(parents=True, exist_ok=True)
        new = work / "01.mp3"
        new.write_bytes(b"x")
        return [new]

    monkeypatch.setattr("quill.core.speech.audio_edit.prepare_chapter_files", fake_prepare)
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_run(args, **_kwargs):  # type: ignore[no-untyped-def]
        for a in args:
            if a.endswith(".m4b") or a.endswith(".mp3"):
                Path(a).write_bytes(b"x")
                break
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", fake_run)

    result = build_audiobook(
        [chapter],
        out,
        output_format="m4b",
        trim_silence_files=True,
        fade_in_ms=150,
        fade_out_ms=300,
        tempo=1.1,
    )
    assert result.chapter_count == 1
    assert captured["paths"] == [src_file]
    kwargs = captured["kwargs"]
    assert kwargs["trim_silence_files"] is True
    assert kwargs["fade_in_ms"] == 150
    assert kwargs["fade_out_ms"] == 300
    assert kwargs["tempo"] == 1.1


def test_build_audiobook_polish_tempo_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tempo != 1.0 alone should trigger polish (e.g. for foreign-language tracks)."""
    src = tmp_path / "src"
    src.mkdir()
    src_file = src / "01.mp3"
    src_file.write_bytes(b"")
    out = tmp_path / "book.m4b"
    chapter = AudiobookChapter(path=src_file, title="C", duration_ms=500)

    captured: dict[str, object] = {}

    def fake_prepare(paths, work, **kwargs):  # type: ignore[no-untyped-def]
        captured["kwargs"] = kwargs
        work.mkdir(parents=True, exist_ok=True)
        new = work / "01.mp3"
        new.write_bytes(b"x")
        return [new]

    monkeypatch.setattr("quill.core.speech.audio_edit.prepare_chapter_files", fake_prepare)
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_run(args, **_kwargs):  # type: ignore[no-untyped-def]
        for a in args:
            if a.endswith(".m4b") or a.endswith(".mp3"):
                Path(a).write_bytes(b"x")
                break
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", fake_run)

    build_audiobook([chapter], out, output_format="m4b", tempo=0.9)
    assert captured["kwargs"]["tempo"] == 0.9


class _FakeCompleted:
    """Minimal stand-in for subprocess.CompletedProcess returned by the stubbed runner."""

    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
