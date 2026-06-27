"""Unit tests for chaptered audio assembly (batch-document-to-speech §4.8.5-§4.8.6).

These run fully headless: a fake synthesizer writes silent WAVs of a controlled
length, so the concat / gap / earcon / chapter-tagging wiring is proven without
any TTS engine or ffmpeg. WAV output is used so no transcode is needed.
"""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from quill.core.speech.chapter_assemble import (
    AssembleError,
    ChapterAssembleOptions,
    assemble_chaptered_audio,
)
from quill.core.speech.earcon import DEFAULT_SAMPLE_RATE, PcmFormat
from quill.core.speech.text_polish import DocumentSection

_FMT = PcmFormat()


def make_fake_synth(ms_per_word: int = 200, min_ms: int = 200):
    """A synth that writes silence proportional to the word count of the text."""

    def _synth(text: str, out: Path) -> None:
        ms = max(min_ms, len(text.split()) * ms_per_word)
        n = int(_FMT.sample_rate * ms / 1000)
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as w:
            w.setnchannels(_FMT.channels)
            w.setsampwidth(_FMT.sampwidth)
            w.setframerate(_FMT.sample_rate)
            w.writeframes(b"\x00" * (n * _FMT.sampwidth * _FMT.channels))

    return _synth


def _wav_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() * 1000 // w.getframerate()


def _sections() -> list[DocumentSection]:
    return [
        DocumentSection("", "lead in words here"),  # 4 words -> 800 ms
        DocumentSection("Article One", "one two three"),  # 3 -> 600 ms
        DocumentSection("Article Two", "a b c d e"),  # 5 -> 1000 ms
    ]


def test_long_section_is_chunked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A section longer than max_chunk_chars is split on safe boundaries and
    # synthesized chunk-by-chunk; a short section stays a single call.
    from quill.core.speech import chapter_assemble

    calls: list[str] = []

    def recording_synth(text: str, out: Path) -> None:
        calls.append(text)
        make_fake_synth()(text, out)

    long_text = " ".join(f"Sentence number {i}." for i in range(40))  # > 80 chars
    chapter_assemble._synthesize_section(
        long_text,
        tmp_path / "s.wav",
        recording_synth,
        tmp_path / "w",
        0,
        sentence_gap_ms=0,
        tail_padding_ms=0,
        max_chunk_chars=80,
    )
    assert len(calls) > 1  # the long section was chunked
    assert all(len(chunk) <= 80 or len(chunk.split()) == 1 for chunk in calls)


def test_headingless_document_reports_chunk_progress(tmp_path: Path) -> None:
    # Regression for the "stuck on Preparing..." report: a heading-less document is
    # a single section, so without chunk-level progress the bar never moves until the
    # whole (long) synthesis finishes. With chunking on, on_progress must fire once
    # per chunk and finish at (total, total) even though there is only one section.
    one_big_section = [DocumentSection("", " ".join(f"Sentence number {i}." for i in range(60)))]
    opts = ChapterAssembleOptions(
        article_gap_ms=0, sound_enabled=False, output_format="wav", max_chunk_chars=80
    )
    ticks: list[tuple[int, int]] = []
    r = assemble_chaptered_audio(
        one_big_section,
        tmp_path / "o.wav",
        make_fake_synth(),
        opts,
        work_dir=tmp_path / "w",
        on_progress=lambda done, total: ticks.append((done, total)),
    )
    assert r.section_count == 1  # heading-less -> exactly one section
    # Initial 0/N tick plus one per chunk; more than one chunk for this long body.
    assert ticks[0][0] == 0
    assert ticks[-1] == (ticks[-1][1], ticks[-1][1])  # ends at total/total
    assert ticks[-1][1] > 1  # the single section was split into multiple chunks
    # Strictly increasing "done" count, one per synthesized chunk.
    assert [d for d, _t in ticks] == list(range(ticks[-1][1] + 1))


def test_short_section_not_chunked(tmp_path: Path) -> None:
    from quill.core.speech import chapter_assemble

    calls: list[str] = []
    chapter_assemble._synthesize_section(
        "short text",
        tmp_path / "s.wav",
        lambda t, o: (calls.append(t), make_fake_synth()(t, o)),
        tmp_path / "w",
        0,
        sentence_gap_ms=0,
        tail_padding_ms=0,
        max_chunk_chars=8000,
    )
    assert calls == ["short text"]  # under the cap -> one call (legacy fast path)


def test_m4b_without_ffmpeg_falls_back_to_wav(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The M4B path needs ffmpeg; without it the assembly must not fail — it saves
    # the WAV and records a note (mirroring the MP3 fallback).
    import quill.core.speech.ffmpeg as ffmpeg

    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: None)
    opts = ChapterAssembleOptions(article_gap_ms=200, output_format="m4b", speak_headings=False)
    result = assemble_chaptered_audio(
        _sections(), tmp_path / "book.m4b", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    assert result.output_path.suffix == ".wav"
    assert any("M4B" in note for note in result.notes)


def test_clean_chapter_offsets_no_sound(tmp_path: Path) -> None:
    # speak_headings=False keeps the spoken word counts equal to the body only, so
    # the concat/gap math below is exact (heading-speaking is covered separately).
    opts = ChapterAssembleOptions(
        article_gap_ms=500, sound_enabled=False, output_format="wav", speak_headings=False
    )
    r = assemble_chaptered_audio(
        _sections(), tmp_path / "out.wav", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    assert r.section_count == 3
    assert r.with_tones_path is None
    assert [(c.title, c.start_ms, c.end_ms) for c in r.chapters] == [
        ("Introduction", 0, 1300),  # 800 + 500 gap
        ("Article One", 1300, 2400),  # 600 + 500 gap
        ("Article Two", 2400, 3400),  # 1000, no trailing gap
    ]
    assert _wav_ms(r.output_path) == 3400


def test_empty_heading_uses_intro_title(tmp_path: Path) -> None:
    opts = ChapterAssembleOptions(
        article_gap_ms=0, sound_enabled=False, output_format="wav", intro_section_title="Front Page"
    )
    r = assemble_chaptered_audio(
        _sections(), tmp_path / "o.wav", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    assert r.chapters[0].title == "Front Page"


def test_with_tones_variant_has_identical_timing(tmp_path: Path) -> None:
    opts = ChapterAssembleOptions(
        article_gap_ms=500, sound_enabled=True, sound_volume=80, output_format="wav"
    )
    r = assemble_chaptered_audio(
        _sections(), tmp_path / "out.wav", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    assert r.with_tones_path is not None
    assert r.with_tones_path.name == "out (with chapter tones).wav"
    # clean and with-tones must be byte-for-byte the same length
    assert _wav_ms(r.output_path) == _wav_ms(r.with_tones_path)
    # The default transition sound is now the bundled page-turn cue, conformed to
    # the section format. The effective gap folds in its length, computed here the
    # same way the assembler does (gap split around the earcon).
    from quill.core.speech.earcon import conform_wav_frames, default_sound_path, silence_frames

    bpf = _FMT.sampwidth * _FMT.channels
    earcon = conform_wav_frames(default_sound_path(), _FMT, volume=0.8)
    boundary = silence_frames(_FMT, 250) + earcon + silence_frames(_FMT, 250)
    eff_gap = (len(boundary) // bpf) * 1000 // _FMT.sample_rate
    assert r.chapters[0].end_ms == 800 + eff_gap


def test_round_robin_synthesizers_cycle_per_section(tmp_path: Path) -> None:
    # Each section is voiced by the next synthesizer in the rotation (i % len).
    used: list[str] = []

    def _make(tag: str):
        def _synth(text: str, out: Path) -> None:
            used.append(tag)
            make_fake_synth()(text, out)

        return _synth

    opts = ChapterAssembleOptions(article_gap_ms=0, sound_enabled=False, output_format="wav")
    assemble_chaptered_audio(
        _sections(),  # 3 sections
        tmp_path / "rr.wav",
        _make("primary"),  # the single fallback, should be unused when rotation is set
        opts,
        work_dir=tmp_path / "w",
        synthesizers=[_make("alice"), _make("bob")],
    )
    # 3 sections, 2 voices -> alice, bob, alice (the single 'primary' never fires).
    assert used == ["alice", "bob", "alice"]


def test_chapters_are_contiguous(tmp_path: Path) -> None:
    opts = ChapterAssembleOptions(article_gap_ms=750, sound_enabled=True, output_format="wav")
    r = assemble_chaptered_audio(
        _sections(), tmp_path / "o.wav", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    for prev, nxt in zip(r.chapters, r.chapters[1:], strict=False):
        assert prev.end_ms == nxt.start_ms
    # The last chapter ends at (approximately) the end of the audio. Per-section
    # millisecond floor-rounding can accumulate a few ms vs the whole-file length;
    # markers within that tolerance are frame-accurate for navigation.
    assert 0 <= _wav_ms(r.output_path) - r.chapters[-1].end_ms <= len(r.chapters)


def test_wav_output_writes_chapter_sidecar(tmp_path: Path) -> None:
    opts = ChapterAssembleOptions(article_gap_ms=300, output_format="wav")
    r = assemble_chaptered_audio(
        _sections(), tmp_path / "o.wav", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    sidecar = r.output_path.with_suffix(".chapters.txt")
    assert sidecar.is_file()
    lines = sidecar.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert lines[0].split("\t")[2] == "Introduction"


def test_heading_only_section_speaks_its_title(tmp_path: Path) -> None:
    secs = [DocumentSection("Chapter With No Body", "")]
    opts = ChapterAssembleOptions(article_gap_ms=0, output_format="wav")
    r = assemble_chaptered_audio(
        secs, tmp_path / "o.wav", make_fake_synth(), opts, work_dir=tmp_path / "w"
    )
    assert r.chapters[0].title == "Chapter With No Body"
    assert _wav_ms(r.output_path) > 0  # the title was spoken, so there is audio


def test_speak_headings_voices_the_title_before_body(tmp_path: Path) -> None:
    """With speak_headings on (default), a section's heading is voiced, so a section
    with a real heading produces more audio than its body alone would."""
    secs = [DocumentSection("A Real Heading", "one two")]  # body = 2 words
    spoken = ChapterAssembleOptions(article_gap_ms=0, output_format="wav", speak_headings=True)
    silent = ChapterAssembleOptions(article_gap_ms=0, output_format="wav", speak_headings=False)
    r_spoken = assemble_chaptered_audio(
        secs, tmp_path / "a.wav", make_fake_synth(), spoken, work_dir=tmp_path / "a"
    )
    r_silent = assemble_chaptered_audio(
        secs, tmp_path / "b.wav", make_fake_synth(), silent, work_dir=tmp_path / "b"
    )
    # heading words ("A Real Heading.") add to the spoken text -> longer audio
    assert _wav_ms(r_spoken.output_path) > _wav_ms(r_silent.output_path)
    # the chapter marker title is the heading either way
    assert r_spoken.chapters[0].title == "A Real Heading"


def test_tail_padding_extends_each_section(tmp_path: Path) -> None:
    """A trailing pad adds silence after each section, lengthening the whole file."""
    secs = [DocumentSection("One", "a b c"), DocumentSection("Two", "d e")]
    base = ChapterAssembleOptions(
        article_gap_ms=0, output_format="wav", speak_headings=False, tail_padding_ms=0
    )
    padded = ChapterAssembleOptions(
        article_gap_ms=0, output_format="wav", speak_headings=False, tail_padding_ms=500
    )
    r0 = assemble_chaptered_audio(
        secs, tmp_path / "a.wav", make_fake_synth(), base, work_dir=tmp_path / "a"
    )
    r1 = assemble_chaptered_audio(
        secs, tmp_path / "b.wav", make_fake_synth(), padded, work_dir=tmp_path / "b"
    )
    # 2 sections x 500 ms pad = +1000 ms total
    assert _wav_ms(r1.output_path) - _wav_ms(r0.output_path) == 1000


def test_sentence_gap_inserts_pauses_between_sentences(tmp_path: Path) -> None:
    """With a sentence gap, a multi-sentence section is longer by gap x (n-1)."""
    secs = [DocumentSection("One", "first sentence. second sentence. third sentence.")]
    no_gap = ChapterAssembleOptions(
        article_gap_ms=0, output_format="wav", speak_headings=False, sentence_gap_ms=0
    )
    with_gap = ChapterAssembleOptions(
        article_gap_ms=0, output_format="wav", speak_headings=False, sentence_gap_ms=300
    )
    r0 = assemble_chaptered_audio(
        secs, tmp_path / "a.wav", make_fake_synth(), no_gap, work_dir=tmp_path / "a"
    )
    r1 = assemble_chaptered_audio(
        secs, tmp_path / "b.wav", make_fake_synth(), with_gap, work_dir=tmp_path / "b"
    )
    # 3 sentences -> 2 inter-sentence gaps of 300 ms = +600 ms
    assert _wav_ms(r1.output_path) - _wav_ms(r0.output_path) == 600
    assert r1.chapters[0].title == "One"


def test_empty_sections_raises(tmp_path: Path) -> None:
    with pytest.raises(AssembleError):
        assemble_chaptered_audio(
            [], tmp_path / "o.wav", make_fake_synth(), ChapterAssembleOptions(), work_dir=tmp_path
        )


def test_mismatched_section_format_raises(tmp_path: Path) -> None:
    def bad_synth(text: str, out: Path) -> None:
        # second section at a different sample rate than the first
        rate = DEFAULT_SAMPLE_RATE if "one" in text else 8000
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"\x00" * (rate // 2 * 2))

    secs = [DocumentSection("One", "one"), DocumentSection("Two", "two")]
    with pytest.raises(AssembleError):
        assemble_chaptered_audio(
            secs, tmp_path / "o.wav", bad_synth, ChapterAssembleOptions(), work_dir=tmp_path / "w"
        )
