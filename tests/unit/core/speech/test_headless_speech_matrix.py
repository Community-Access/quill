"""Headless stress test for the batch document-to-speech pipeline (§4.8-§4.10).

Proves the whole non-UI wiring end to end with **no UI and no real TTS engine**:

    document (txt / md / html / Word) -> extract_sections -> assemble_chaptered_audio
        (fake synth) -> chaptered WAV/MP3 -> chapter markers read back

A fake synthesizer writes silent WAVs of a controlled length and format, so we can
sweep the full matrix of settings/options (output format, transition sound on/off,
gap lengths, and several "voice types" simulated as different PCM formats) and
assert the chapter timing/markers come out right. This is the harness the project
uses to validate settings before the dialog exists.

The real-engine MP3 path (SAPI 5 / Piper / ...) lives in
``test_real_engine_mp3_smoke`` and is **skipped by default**; set
``QUILL_RUN_SPEECH_INTEGRATION=1`` (and have ffmpeg + a voice installed) to run it.
"""

from __future__ import annotations

import os
import wave
import zipfile
from pathlib import Path

import pytest

from quill.core.speech.chapter_assemble import (
    ChapterAssembleOptions,
    assemble_chaptered_audio,
)
from quill.core.speech.earcon import PcmFormat
from quill.core.speech.ffmpeg import ffmpeg_available
from quill.core.speech.project_profile import (
    ChapterProfile,
    OutputProfile,
    SpeechProjectProfile,
    SynthesizerProfile,
    load_profile,
    save_profile,
    to_chapter_options,
)
from quill.core.speech.text_polish import extract_sections

_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# --- fixtures: documents and a fake engine -------------------------------- #


def make_fake_synth(fmt: PcmFormat, ms_per_word: int = 120):
    """A synth that simulates a 'voice' by writing silence in *fmt* sized by words."""

    def _synth(text: str, out: Path) -> None:
        ms = max(150, len(text.split()) * ms_per_word)
        n = int(fmt.sample_rate * ms / 1000)
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as w:
            w.setnchannels(fmt.channels)
            w.setsampwidth(fmt.sampwidth)
            w.setframerate(fmt.sample_rate)
            w.writeframes(b"\x00" * (n * fmt.sampwidth * fmt.channels))

    return _synth


def write_docx_with_headings(path: Path, items: list[tuple[str, str]]) -> Path:
    """Write a minimal .docx whose paragraphs carry Heading styles or body text.

    *items* is a list of ``(style, text)``: style "Heading1".."Heading9"/"Title"
    marks a heading paragraph; "" (or "Normal") is body text. Only
    ``word/document.xml`` is written — that is all the stdlib extractor reads.
    """
    paras: list[str] = []
    for style, text in items:
        if style and style.lower() != "normal":
            ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
        else:
            ppr = ""
        paras.append(f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>")
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_WORD_NS}"><w:body>{"".join(paras)}</w:body></w:document>'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", doc)
    return path


def _wav_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() * 1000 // w.getframerate()


# --- the matrix ----------------------------------------------------------- #

# Three simulated "voice types" as distinct PCM formats (rate, channels, width).
VOICE_FORMATS = {
    "sapi_22k_mono": PcmFormat(22050, 1, 2),
    "whisper_16k_mono": PcmFormat(16000, 1, 2),
    "studio_44k_stereo": PcmFormat(44100, 2, 2),
}


@pytest.mark.parametrize("voice", list(VOICE_FORMATS))
@pytest.mark.parametrize("sound_enabled", [False, True])
@pytest.mark.parametrize("gap_ms", [0, 800, 3000])
def test_docx_chapterization_matrix(
    tmp_path: Path, voice: str, sound_enabled: bool, gap_ms: int
) -> None:
    """Word doc with headings -> chaptered WAV across voices/sound/gap combos."""
    docx = write_docx_with_headings(
        tmp_path / "primer.docx",
        [
            ("", "Welcome to the primer."),
            ("Heading1", "Getting Started"),
            ("", "First chapter body text here."),
            ("Heading1", "Navigation"),
            ("", "Second chapter body."),
            ("Heading2", "Quick Keys"),
            ("", "A sub-section body."),
        ],
    )
    sections = extract_sections(docx)
    titles = [s.title for s in sections]
    assert titles == ["", "Getting Started", "Navigation", "Quick Keys"]

    fmt = VOICE_FORMATS[voice]
    opts = ChapterAssembleOptions(
        article_gap_ms=gap_ms,
        sound_enabled=sound_enabled,
        output_format="wav",  # WAV keeps CI deterministic (no ffmpeg dependency)
        intro_section_title="Introduction",
    )
    result = assemble_chaptered_audio(
        sections, tmp_path / "primer.wav", make_fake_synth(fmt), opts, work_dir=tmp_path / "w"
    )

    assert result.section_count == 4
    assert [c.title for c in result.chapters] == [
        "Introduction",
        "Getting Started",
        "Navigation",
        "Quick Keys",
    ]
    # contiguity holds for every combination
    for prev, nxt in zip(result.chapters, result.chapters[1:], strict=False):
        assert prev.end_ms == nxt.start_ms
    # the with-tones variant exists iff the sound is enabled, and matches timing
    if sound_enabled:
        assert result.with_tones_path is not None
        assert _wav_ms(result.output_path) == _wav_ms(result.with_tones_path)
    else:
        assert result.with_tones_path is None


@pytest.mark.parametrize(
    "ext,write",
    [
        (".txt", lambda p: p.write_text("Just one flat section.", encoding="utf-8")),
        (
            ".md",
            lambda p: p.write_text("# One\nbody one\n\n# Two\nbody two\n", encoding="utf-8"),
        ),
        (
            ".html",
            lambda p: p.write_text(
                "<h1>One</h1><p>body one</p><h1>Two</h1><p>body two</p>", encoding="utf-8"
            ),
        ),
    ],
)
def test_all_formats_flow_through(tmp_path: Path, ext: str, write) -> None:
    """Every supported input format reaches a chaptered output headlessly."""
    src = tmp_path / f"doc{ext}"
    write(src)
    sections = extract_sections(src)
    assert sections  # always at least one section
    opts = ChapterAssembleOptions(article_gap_ms=500, output_format="wav")
    result = assemble_chaptered_audio(
        sections, tmp_path / "out.wav", make_fake_synth(PcmFormat()), opts, work_dir=tmp_path / "w"
    )
    assert result.output_path.is_file()
    assert result.chapters[0].start_ms == 0


def test_driven_from_saved_project_profile(tmp_path: Path) -> None:
    """A profile JSON on disk drives the chapter options for an assembly (§4.10)."""
    project = tmp_path / "Daily News"
    project.mkdir()
    profile = SpeechProjectProfile(
        synthesizer=SynthesizerProfile(engine="sapi5", voice="David", rate=190),
        output=OutputProfile(format="wav"),
        chapters=ChapterProfile(
            mode="single",
            sound_enabled=True,
            sound_volume=70,
            article_gap_ms=1200,
            intro_section_title="Front Page",
        ),
    )
    save_profile(profile, project)

    reloaded = load_profile(project)
    assert reloaded is not None
    opts = to_chapter_options(reloaded)

    md = project / "edition.md"
    md.write_text("lead\n\n# Story A\naaa\n\n# Story B\nbbb\n", encoding="utf-8")
    sections = extract_sections(md)
    result = assemble_chaptered_audio(
        sections,
        project / "edition.wav",
        make_fake_synth(PcmFormat()),
        opts,
        work_dir=tmp_path / "w",
    )
    assert result.chapters[0].title == "Front Page"
    assert [c.title for c in result.chapters] == ["Front Page", "Story A", "Story B"]
    assert result.with_tones_path is not None  # sound_enabled in the profile


@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not installed")
def test_mp3_output_writes_real_chapter_markers(tmp_path: Path) -> None:
    """When ffmpeg is present, the MP3 path produces a file with readable CHAP frames."""
    from quill.core.speech.chapters import read_mp3_chapters

    md = tmp_path / "doc.md"
    md.write_text("# Alpha\naaa bbb ccc\n\n# Beta\nddd eee\n", encoding="utf-8")
    sections = extract_sections(md)
    opts = ChapterAssembleOptions(article_gap_ms=600, sound_enabled=True, output_format="mp3")
    result = assemble_chaptered_audio(
        sections, tmp_path / "doc.mp3", make_fake_synth(PcmFormat()), opts, work_dir=tmp_path / "w"
    )
    assert result.output_path.suffix == ".mp3"
    chapters = read_mp3_chapters(result.output_path)
    assert [c.title for c in chapters] == ["Alpha", "Beta"]
    # both variants carry identical markers
    assert result.with_tones_path is not None
    tones = read_mp3_chapters(result.with_tones_path)
    assert [(c.start_ms, c.end_ms) for c in tones] == [(c.start_ms, c.end_ms) for c in chapters]


@pytest.mark.skipif(
    os.environ.get("QUILL_RUN_SPEECH_INTEGRATION") != "1",
    reason="set QUILL_RUN_SPEECH_INTEGRATION=1 to run the real-engine MP3 smoke test",
)
def test_real_engine_mp3_smoke(tmp_path: Path) -> None:
    """Real SAPI 5 synthesis -> chaptered MP3 (opt-in; needs a voice + ffmpeg).

    This is the deliberately-not-run scaffold: it proves the wiring against a real
    engine when explicitly enabled, but never runs in normal CI.
    """
    from quill.core.read_aloud import synthesize_to_file_with_sapi5

    def real_synth(text: str, out: Path) -> None:
        synthesize_to_file_with_sapi5(text, out, voice="", rate=200, volume=1.0)

    md = tmp_path / "doc.md"
    md.write_text(
        "# Chapter One\nHello world.\n\n# Chapter Two\nGoodbye world.\n", encoding="utf-8"
    )
    sections = extract_sections(md)
    opts = ChapterAssembleOptions(article_gap_ms=800, sound_enabled=True, output_format="mp3")
    result = assemble_chaptered_audio(
        sections, tmp_path / "real.mp3", real_synth, opts, work_dir=tmp_path / "w"
    )
    from quill.core.speech.chapters import read_mp3_chapters

    assert result.output_path.is_file()
    assert [c.title for c in read_mp3_chapters(result.output_path)] == [
        "Chapter One",
        "Chapter Two",
    ]
