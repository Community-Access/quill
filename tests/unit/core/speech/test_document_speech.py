"""Tests for the document -> chaptered-speech driver (engine resolution + flow)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from quill.core.speech import document_speech as ds
from quill.core.speech.chapter_assemble import ChapterAssembleOptions
from quill.core.speech.earcon import PcmFormat


def _write_silence(out: Path, fmt: PcmFormat | None = None, ms: int = 200) -> None:
    fmt = fmt or PcmFormat()
    n = int(fmt.sample_rate * ms / 1000)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(fmt.channels)
        w.setsampwidth(fmt.sampwidth)
        w.setframerate(fmt.sample_rate)
        w.writeframes(b"\x00" * (n * fmt.sampwidth * fmt.channels))


def test_make_synthesizer_dispatches_to_kokoro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str, float]] = []

    def fake_kokoro(text: str, out: Path, *, voice: str = "af_heart", speed: float = 1.0) -> None:
        calls.append((text, voice, speed))
        _write_silence(out)

    monkeypatch.setattr(ds.read_aloud, "synthesize_with_kokoro", fake_kokoro)
    synth = ds.make_synthesizer(ds.SynthesisSpec(engine="kokoro", voice="am_liam", speed=1.0))
    synth("hello", tmp_path / "out.wav")
    assert calls and calls[0][1] == "am_liam" and calls[0][2] == 1.0


def test_unknown_engine_raises() -> None:
    with pytest.raises(ds.DocumentSpeechError):
        ds.make_synthesizer(ds.SynthesisSpec(engine="bogus"))


def test_cloud_engine_requires_api_key() -> None:
    # A cloud provider with no key fails fast (before any synthesis call).
    with pytest.raises(ds.DocumentSpeechError, match="API key"):
        ds.make_synthesizer(ds.SynthesisSpec(engine="openai", voice="nova"))


def test_cloud_engine_requires_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    # With a key but no ffmpeg, the cloud path refuses up front (it needs ffmpeg to
    # conform the provider's MP3/WAV to the splice-ready PCM WAV).
    import quill.core.speech.ffmpeg as ffmpeg_mod

    monkeypatch.setattr(ffmpeg_mod, "find_ffmpeg", lambda: None)
    with pytest.raises(ds.DocumentSpeechError, match="ffmpeg"):
        ds.make_synthesizer(ds.SynthesisSpec(engine="openai", voice="nova", api_key="sk-x"))


def test_translate_applied_before_synthesis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.speech.text_polish import DocumentSection

    spoken: list[str] = []
    monkeypatch.setattr(
        ds, "extract_sections", lambda _src, **_kw: [DocumentSection("Hola", "mundo")]
    )

    def _record_synth(_spec):
        def _synth(text: str, out: Path) -> None:
            spoken.append(text)
            _write_silence(out)

        return _synth

    monkeypatch.setattr(ds, "make_synthesizer", _record_synth)
    ds.synthesize_document_to_chaptered_file(
        tmp_path / "doc.md",
        tmp_path / "out.wav",
        ds.SynthesisSpec(engine="sapi5", voice="x"),
        ChapterAssembleOptions(article_gap_ms=0, sound_enabled=False, output_format="wav"),
        translate=lambda t: f"EN[{t}]",
    )
    # The heading title and body were both translated before reaching the engine.
    joined = " ".join(spoken)
    assert "EN[Hola]" in joined and "EN[mundo]" in joined


def test_build_voice_rotation_one_synth_per_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def _fake_make(spec: ds.SynthesisSpec):
        voice = spec.voice
        return lambda text, out: seen.append(voice) or _write_silence(out)

    monkeypatch.setattr(ds, "make_synthesizer", _fake_make)
    base = ds.SynthesisSpec(engine="sapi5", voice="x")
    # Fewer than two distinct voices -> no rotation.
    assert ds._build_voice_rotation(base, [], None) is None
    assert ds._build_voice_rotation(base, ["only"], None) is None
    # Two+ voices -> one synthesizer per voice, in order, de-duplicated.
    rotation = ds._build_voice_rotation(base, ["Alice", "Bob", "Alice"], None)
    assert rotation is not None and len(rotation) == 2
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        for i, synth in enumerate(rotation):
            synth("hi", pathlib.Path(d) / f"{i}.wav")
    assert seen == ["Alice", "Bob"]


def test_build_voice_rotation_skips_blacklisted(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.speech.voice_blacklist import VoiceBlacklist

    seen: list[str] = []
    monkeypatch.setattr(ds, "make_synthesizer", lambda spec: lambda t, o: seen.append(spec.voice))
    bl = VoiceBlacklist()
    bl.record_failure("sapi5", "Bob")
    base = ds.SynthesisSpec(engine="sapi5", voice="x")
    # Bob is blacklisted -> only Alice + Carol remain in the rotation.
    rotation = ds._build_voice_rotation(base, ["Alice", "Bob", "Carol"], None, bl)
    assert rotation is not None and len(rotation) == 2
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        for i, synth in enumerate(rotation):
            synth("hi", pathlib.Path(d) / f"{i}.wav")
    assert seen == ["Alice", "Carol"]


def test_failure_recording_blacklists_then_reraises() -> None:
    from quill.core.speech.voice_blacklist import VoiceBlacklist

    bl = VoiceBlacklist()

    def _boom(text: str, out: Path) -> None:
        raise RuntimeError("synthesis failed")

    wrapped = ds._wrap_with_failure_recording(_boom, "sapi5", "David", bl)
    with pytest.raises(RuntimeError, match="synthesis failed"):
        wrapped("hi", Path("ignored.wav"))
    assert bl.is_blacklisted("sapi5", "David")  # recorded for next run


def test_separate_files_one_per_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.speech.text_polish import DocumentSection

    sections = [
        DocumentSection("", "intro words here"),  # empty heading -> intro title
        DocumentSection("Chapter One", "one two three"),
        DocumentSection('Bad: name? "x"', "four five"),  # unsafe chars stripped
    ]
    monkeypatch.setattr(ds, "extract_sections", lambda _src, **_kw: sections)
    monkeypatch.setattr(ds, "make_synthesizer", lambda _spec: lambda text, out: _write_silence(out))

    out_dir = tmp_path / "out"
    files = ds.synthesize_document_to_separate_files(
        tmp_path / "doc.md",
        out_dir,
        ds.SynthesisSpec(engine="sapi5"),
        ChapterAssembleOptions(
            output_format="wav", article_gap_ms=0, speak_headings=False, intro_section_title="Intro"
        ),
    )
    assert len(files) == 3
    names = [f.name for f in files]
    assert names[0] == "001 - Intro.wav"  # empty heading took the intro title
    assert names[1] == "002 - Chapter One.wav"
    # Reserved filename characters are stripped from the heading.
    assert ":" not in names[2] and "?" not in names[2] and '"' not in names[2]
    assert all(f.exists() for f in files)


def test_safe_filename_strips_and_falls_back() -> None:
    assert ds._safe_filename("a/b:c?", "fallback") == "a b c"
    assert ds._safe_filename("   ", "fallback") == "fallback"


def test_pyttsx3_alias_maps_to_sapi5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_sapi(text: str, out: Path, *, voice: str = "", rate: int = 200, volume: float = 1.0):
        seen.append(voice)
        _write_silence(out)

    monkeypatch.setattr(ds.read_aloud, "synthesize_to_file_with_sapi5", fake_sapi)
    synth = ds.make_synthesizer(ds.SynthesisSpec(engine="pyttsx3", voice="David"))
    synth("hi", tmp_path / "out.wav")
    assert seen == ["David"]


def test_end_to_end_with_fake_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """document -> sections -> assembled chaptered WAV, engine resolved internally."""

    def fake_kokoro(text: str, out: Path, *, voice: str = "af_heart", speed: float = 1.0) -> None:
        _write_silence(out, ms=max(150, len(text.split()) * 50))

    monkeypatch.setattr(ds.read_aloud, "synthesize_with_kokoro", fake_kokoro)

    md = tmp_path / "doc.md"
    md.write_text("lead in\n\n# Story A\naaa bbb\n\n# Story B\nccc\n", encoding="utf-8")

    opts = ChapterAssembleOptions(
        article_gap_ms=600,
        sound_enabled=True,
        output_format="wav",  # avoid an ffmpeg dependency in CI
        intro_section_title="Introduction",
    )
    result = ds.synthesize_document_to_chaptered_file(
        md, tmp_path / "doc.wav", ds.SynthesisSpec(engine="kokoro", voice="am_liam"), opts
    )

    assert [c.title for c in result.chapters] == ["Introduction", "Story A", "Story B"]
    assert result.output_path.is_file()
    assert result.with_tones_path is not None  # sounder enabled


def test_headingless_document_forwards_chunk_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A heading-less doc is one section; on_progress still fires per synthesized chunk."""

    def fake_kokoro(text: str, out: Path, *, voice: str = "af_heart", speed: float = 1.0) -> None:
        _write_silence(out, ms=150)

    monkeypatch.setattr(ds.read_aloud, "synthesize_with_kokoro", fake_kokoro)

    txt = tmp_path / "no_headings.txt"
    txt.write_text(" ".join(f"Sentence number {i}." for i in range(60)), encoding="utf-8")

    ticks: list[tuple[int, int]] = []
    opts = ChapterAssembleOptions(article_gap_ms=0, output_format="wav", max_chunk_chars=80)
    result = ds.synthesize_document_to_chaptered_file(
        txt,
        tmp_path / "out.wav",
        ds.SynthesisSpec(engine="kokoro", voice="am_liam"),
        opts,
        on_progress=lambda done, total: ticks.append((done, total)),
    )
    assert result.section_count == 1  # heading-less -> single section
    assert ticks[-1] == (ticks[-1][1], ticks[-1][1]) and ticks[-1][1] > 1


def test_pronunciation_dictionaries_reach_the_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Active pronunciation entries are applied to spoken text before synthesis."""
    from quill.core.speech.pronunciation import PronunciationDictionary, PronunciationEntry

    spoken: list[str] = []

    def fake_kokoro(text: str, out: Path, *, voice: str = "af_heart", speed: float = 1.0) -> None:
        spoken.append(text)
        _write_silence(out)

    monkeypatch.setattr(ds.read_aloud, "synthesize_with_kokoro", fake_kokoro)

    md = tmp_path / "doc.md"
    md.write_text("# Intro\nQUILL is great.\n", encoding="utf-8")
    dicts = [
        PronunciationDictionary(
            id="d", entries=[PronunciationEntry(term="QUILL", replacement="kwill")]
        )
    ]
    opts = ChapterAssembleOptions(output_format="wav", speak_headings=False)
    ds.synthesize_document_to_chaptered_file(
        md,
        tmp_path / "doc.wav",
        ds.SynthesisSpec(engine="kokoro", voice="am_liam"),
        opts,
        pronunciation_dictionaries=dicts,
    )
    assert any("kwill" in t for t in spoken)
    assert not any("QUILL" in t for t in spoken)
