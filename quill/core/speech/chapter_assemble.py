"""Assemble heading sections into one chaptered audio file (§4.8.5–§4.8.6).

wx-free, strict-typed, stdlib audio (``wave``). Takes document sections (title +
text), a **synthesizer callable** (so the real engines and a test fake share one
path), and chapter options, and produces:

- a **clean** file (speech + inter-article silence only), and
- when the transition sound is enabled, a **with-tones** file (the same audio with
  a short earcon spliced into each boundary) — see §4.8.5.

Both files carry **identical** ID3 chapter markers (titled from the headings), so
a listener can jump article-to-article in either variant. The earcon's length is
folded into the inter-article gap so the two variants share exactly the same
chapter timing (the clean variant pads with pure silence of the same total).

Nothing is read aloud — every stage writes PCM/MP3 to disk (§silent-batch). The
synthesizer is injected, so this whole pipeline is unit-testable headlessly with a
fake synth that writes silent WAVs of controlled length (no TTS engine required).
"""

from __future__ import annotations

import re
import wave
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.speech.chapters import (
    Chapter,
    ChapterSection,
    compute_chapters,
    write_mp3_chapters,
)
from quill.core.speech.earcon import (
    PcmFormat,
    conform_wav_frames,
    default_sound_path,
    silence_frames,
    write_default_sounder,
)
from quill.core.speech.text_polish import DocumentSection

# (text, out_wav) -> None. Writes a PCM WAV of the spoken text to out_wav. The
# real implementation is read_aloud's per-engine synthesize-to-file functions; a
# test passes a fake that writes silence of a chosen duration.
Synthesizer = Callable[[str, Path], None]


@dataclass(slots=True)
class ChapterAssembleOptions:
    """Resolved options for one chaptered assembly (mirrors the §4.8.8 settings)."""

    article_gap_ms: int = 1200
    sound_enabled: bool = False
    sound_path: Path | None = None  # None + enabled -> bundled page-turn (chime fallback)
    sound_volume: int = 100  # 0-100
    intro_section_title: str = "Introduction"
    toc_title: str = "Chapters"
    output_format: str = "mp3"  # "mp3" | "wav"
    speak_headings: bool = True  # voice each heading before its body (not just mark it)
    sentence_gap_ms: int = 0  # silence inserted between sentences within a section (0 = off)
    tail_padding_ms: int = 0  # silence appended after each section's speech (anti-clipping)
    normalize_loudness: bool = False  # two-pass loudnorm to ACX level before encoding
    # Long-document chunking: a section whose text exceeds this many characters is
    # split on safe sentence/word boundaries (via tts_chunk) and synthesized
    # chunk-by-chunk, so a very long section never becomes one over-long synthesis
    # call that risks an engine timeout. 0 = off (one call per section/sentence).
    max_chunk_chars: int = 0


@dataclass(slots=True)
class ChapterAssembleResult:
    """What an assembly produced: the clean file, the optional with-tones file, chapters."""

    output_path: Path
    chapters: list[Chapter]
    section_count: int
    with_tones_path: Path | None = None
    notes: list[str] = field(default_factory=list)


class AssembleError(Exception):
    """Raised when sections cannot be assembled (e.g. inconsistent audio formats)."""


def _wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() * 1000 // w.getframerate()


def _read_frames(path: Path, fmt: PcmFormat) -> bytes:
    """Read raw PCM frames from *path*, requiring it match the canonical *fmt*."""
    with wave.open(str(path), "rb") as w:
        got = PcmFormat(
            sample_rate=w.getframerate(),
            channels=w.getnchannels(),
            sampwidth=w.getsampwidth(),
        )
        if got != fmt:
            raise AssembleError(
                f"Audio format mismatch in {path.name}: {got} != section format {fmt}. "
                "All sections in one chaptered file must share a sample rate / channels / "
                "width (use a single engine and voice per document)."
            )
        return w.readframes(w.getnframes())


def _write_wav(path: Path, fmt: PcmFormat, frames: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(fmt.channels)
        w.setsampwidth(fmt.sampwidth)
        w.setframerate(fmt.sample_rate)
        w.writeframes(frames)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """Split *text* into sentences on ``.``/``!``/``?`` boundaries (keeping the mark).

    Deliberately simple: a few abbreviations may split early, which only adds a
    short pause, never drops text. Falls back to the whole text if nothing splits.
    """
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p.strip()]
    return parts or [text]


def _section_parts(spoken: str, *, sentence_gap_ms: int, max_chunk_chars: int) -> list[str]:
    """The pieces a section is synthesized in, in priority order.

    Long-document chunking wins: a section longer than ``max_chunk_chars`` is split
    on safe sentence/word boundaries (``tts_chunk``). Otherwise, sentence splitting
    applies only when an inter-sentence gap is requested; else the whole section is
    one piece (the byte-identical legacy fast path).
    """
    if max_chunk_chars > 0 and len(spoken) > max_chunk_chars:
        from quill.core.ai.tts_chunk import chunk_text

        chunks = chunk_text(spoken, max_chunk_chars)
        if chunks:
            return chunks
    if sentence_gap_ms > 0:
        return _split_sentences(spoken)
    return [spoken]


def _synthesize_section(
    spoken: str,
    out_wav: Path,
    synthesize: Synthesizer,
    work_dir: Path,
    idx: int,
    *,
    sentence_gap_ms: int,
    tail_padding_ms: int,
    max_chunk_chars: int = 0,
    parts: list[str] | None = None,
    on_part_done: Callable[[], None] | None = None,
) -> None:
    """Synthesize one section to *out_wav*, optionally pausing between sentences,
    chunking a very long section, and padding the tail to prevent end-of-clip cutoff.

    With every knob at 0 this is a single ``synthesize`` call writing *out_wav*
    directly (byte-identical to the legacy path). Otherwise the section is split
    into pieces (chunks for a long section, else sentences), synthesized separately,
    joined with ``sentence_gap_ms`` of silence, and padded by ``tail_padding_ms``.

    *parts* may be supplied pre-computed (so the caller can total them for progress);
    *on_part_done* is invoked once per synthesized piece for fine-grained progress —
    crucial for a heading-less document, which is one giant section split into chunks.
    """
    sentence_gap_ms = max(0, sentence_gap_ms)
    tail_padding_ms = max(0, tail_padding_ms)
    if parts is None:
        parts = _section_parts(
            spoken, sentence_gap_ms=sentence_gap_ms, max_chunk_chars=max(0, max_chunk_chars)
        )

    # Fast path: nothing to splice -> one call, no re-encoding.
    if len(parts) == 1 and tail_padding_ms == 0:
        synthesize(parts[0], out_wav)
        if on_part_done is not None:
            on_part_done()
        return

    part_wavs: list[Path] = []
    for j, part in enumerate(parts):
        pw = work_dir / f"section_{idx:04d}_part_{j:03d}.wav"
        synthesize(part, pw)
        if not pw.is_file():
            raise AssembleError(f"Synthesizer did not produce audio for section {idx}, part {j}.")
        part_wavs.append(pw)
        if on_part_done is not None:
            on_part_done()

    fmt = PcmFormat.from_wav(part_wavs[0])
    gap = silence_frames(fmt, sentence_gap_ms)
    frames = bytearray()
    last = len(part_wavs) - 1
    for j, pw in enumerate(part_wavs):
        frames += _read_frames(pw, fmt)
        if j < last and sentence_gap_ms > 0:
            frames += gap
    if tail_padding_ms > 0:
        frames += silence_frames(fmt, tail_padding_ms)
    _write_wav(out_wav, fmt, bytes(frames))


def _resolve_titles(
    sections: list[DocumentSection],
    intro_title: str,
    *,
    speak_headings: bool = True,
) -> list[tuple[str, str]]:
    """Pair each section with its spoken text and a display title.

    An empty heading (the lead-in or a headingless document) takes the configured
    intro title. When *speak_headings* is true the heading is voiced before its
    body so a listener hears the chapter title (a heading with no body always
    speaks its own title so the chapter still has audio). The display title — used
    for the chapter marker — is always the heading text regardless.
    """
    resolved: list[tuple[str, str]] = []
    for sec in sections:
        title = sec.title.strip() or intro_title
        body = sec.text.strip()
        if not body:
            spoken = title
        elif speak_headings and sec.title.strip():
            spoken = f"{title}.\n{body}"
        else:
            spoken = body
        resolved.append((title, spoken))
    return resolved


def assemble_chaptered_audio(
    sections: list[DocumentSection],
    output_path: Path,
    synthesize: Synthesizer,
    options: ChapterAssembleOptions,
    *,
    work_dir: Path,
    synthesizers: list[Synthesizer] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> ChapterAssembleResult:
    """Synthesize, concat (with gap/earcon), tag, and write the chaptered file(s).

    *work_dir* holds the per-section temp WAVs (caller owns its lifetime). Returns
    a :class:`ChapterAssembleResult`; raises :class:`AssembleError` on bad input.

    When *synthesizers* is given (round-robin voices), section ``i`` is voiced by
    ``synthesizers[i % len(synthesizers)]`` so each article/heading gets the next
    voice in the list; otherwise the single *synthesize* is used for every section.
    All voices must share one PCM format (use voices of a single engine), since the
    sections are spliced into one file.
    """
    if not sections:
        raise AssembleError("No sections to assemble.")

    work_dir.mkdir(parents=True, exist_ok=True)
    resolved = _resolve_titles(
        sections, options.intro_section_title, speak_headings=options.speak_headings
    )
    rotation = [s for s in (synthesizers or []) if s is not None]

    # 1. Synthesize each section to its own WAV and measure it. Parts are computed
    #    up front so progress can be reported per synthesized chunk — a heading-less
    #    document is one section split into several chunks, so chunk-level reporting
    #    is the only way its progress bar moves at all.
    section_parts = [
        _section_parts(
            spoken,
            sentence_gap_ms=options.sentence_gap_ms,
            max_chunk_chars=max(0, options.max_chunk_chars),
        )
        for _title, spoken in resolved
    ]
    total_parts = sum(len(p) for p in section_parts) or 1
    done_parts = 0
    if on_progress is not None:
        on_progress(0, total_parts)

    section_wavs: list[Path] = []
    section_durations: list[int] = []
    for i, (_title, spoken) in enumerate(resolved):
        wav = work_dir / f"section_{i:04d}.wav"
        section_synth = rotation[i % len(rotation)] if rotation else synthesize

        def _tick() -> None:
            nonlocal done_parts
            done_parts += 1
            if on_progress is not None:
                on_progress(done_parts, total_parts)

        _synthesize_section(
            spoken,
            wav,
            section_synth,
            work_dir,
            i,
            sentence_gap_ms=options.sentence_gap_ms,
            tail_padding_ms=options.tail_padding_ms,
            max_chunk_chars=options.max_chunk_chars,
            parts=section_parts[i],
            on_part_done=_tick,
        )
        if not wav.is_file():
            raise AssembleError(f"Synthesizer did not produce audio for section {i}.")
        section_wavs.append(wav)
        section_durations.append(_wav_duration_ms(wav))

    # 2. Canonical PCM format = the first section's; silence/earcon match it.
    fmt = PcmFormat.from_wav(section_wavs[0])

    # 3. The earcon (optional). Its length folds into the gap so both the clean
    #    and with-tones variants share identical chapter timing (§4.8.5).
    earcon_frames = b""
    notes: list[str] = []
    if options.sound_enabled:
        earcon_wav = work_dir / "earcon.wav"
        volume = max(0, min(100, options.sound_volume)) / 100.0
        # Use the chosen sound, else the bundled default page-turn cue. Either is
        # conformed to the section format (resample/mix), so any WAV splices cleanly
        # instead of being rejected for a format mismatch.
        chosen = options.sound_path or default_sound_path()
        if chosen is not None and chosen.is_file():
            try:
                earcon_frames = conform_wav_frames(chosen, fmt, volume=volume)
            except (ValueError, wave.Error, OSError):
                notes.append("Could not read the transition sound; used the default chime.")
        if not earcon_frames:
            # Last resort: the synthesized placeholder chime, generated at the
            # section format so it always splices.
            write_default_sounder(earcon_wav, fmt, volume=volume)
            earcon_frames = _read_frames(earcon_wav, fmt)

    base_gap = max(0, options.article_gap_ms)

    # 4. Build the with-tones boundary (or pure silence when sound is off), then
    #    derive everything else from its exact frame length so the clean and
    #    with-tones variants share byte-for-byte identical chapter timing (§4.8.5).
    if options.sound_enabled and earcon_frames:
        boundary = (
            silence_frames(fmt, base_gap // 2)
            + earcon_frames
            + silence_frames(fmt, base_gap - base_gap // 2)
        )
    else:
        boundary = silence_frames(fmt, base_gap)
    bytes_per_frame = fmt.sampwidth * fmt.channels
    effective_gap = (len(boundary) // bytes_per_frame) * 1000 // fmt.sample_rate
    clean_boundary = b"\x00" * len(boundary)  # same length as the tones boundary

    # 5. Chapters (single computation; both variants use this timing).
    chapter_sections = [
        ChapterSection(title=title, duration_ms=dur)
        for (title, _spoken), dur in zip(resolved, section_durations, strict=True)
    ]
    chapters = compute_chapters(chapter_sections, gap_ms=effective_gap)

    # 6. Clean variant: sections + pure silence (same length as the boundary).
    clean_wav = work_dir / "assembled_clean.wav"
    _write_wav(clean_wav, fmt, _join(section_wavs, clean_boundary, fmt))
    # Loudness normalization (two-pass loudnorm) before encoding, so chapter timing
    # (loudnorm preserves duration) and the markers added in _finalize both survive.
    if options.normalize_loudness:
        from quill.core.speech.loudness import normalize_wav_loudness

        if not normalize_wav_loudness(clean_wav):
            notes.append("Loudness normalization unavailable (ffmpeg missing); saved as-is.")
    clean_out = _finalize(clean_wav, output_path, options.output_format, chapters, options, notes)

    result = ChapterAssembleResult(
        output_path=clean_out,
        chapters=chapters,
        section_count=len(sections),
        notes=notes,
    )

    # 7. With-tones variant: the same audio with the earcon spliced into each gap.
    if options.sound_enabled and earcon_frames:
        tones_wav = work_dir / "assembled_tones.wav"
        _write_wav(tones_wav, fmt, _join(section_wavs, boundary, fmt))
        if options.normalize_loudness:
            from quill.core.speech.loudness import normalize_wav_loudness

            normalize_wav_loudness(tones_wav)
        result.with_tones_path = _finalize(
            tones_wav,
            _with_tones_name(output_path),
            options.output_format,
            chapters,
            options,
            notes,
        )

    return result


def _join(section_wavs: list[Path], boundary: bytes, fmt: PcmFormat) -> bytes:
    """Concatenate section frames, inserting *boundary* between (not after last)."""
    out = bytearray()
    last = len(section_wavs) - 1
    for i, wav in enumerate(section_wavs):
        out += _read_frames(wav, fmt)
        if i < last:
            out += boundary
    return bytes(out)


def _finalize(
    assembled_wav: Path,
    target: Path,
    output_format: str,
    chapters: list[Chapter],
    options: ChapterAssembleOptions,
    notes: list[str],
) -> Path:
    """Place the assembled WAV at *target* (transcoding to MP3/M4B if asked) and tag it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "mp3":
        from quill.core.speech.ffmpeg import TranscodeError, ffmpeg_available, transcode_to_mp3

        if ffmpeg_available():
            try:
                transcode_to_mp3(assembled_wav, target)
                write_mp3_chapters(target, chapters, toc_title=options.toc_title)
                return target
            except TranscodeError as exc:
                notes.append(f"MP3 encode failed ({exc}); saved WAV instead.")
        else:
            notes.append("ffmpeg not found; saved WAV instead of MP3.")
        target = target.with_suffix(".wav")
    elif output_format == "m4b":
        # M4B audiobook with native MP4 chapter atoms (the Apple/audiobook format),
        # written from the same chapter timing as the MP3 CHAP frames.
        from quill.core.speech.ffmpeg import (
            TranscodeError,
            encode_m4b_with_chapters,
            ffmpeg_available,
        )

        if ffmpeg_available():
            try:
                encode_m4b_with_chapters(
                    assembled_wav,
                    target,
                    [(c.title, c.start_ms, c.end_ms) for c in chapters],
                )
                return target
            except TranscodeError as exc:
                notes.append(f"M4B encode failed ({exc}); saved WAV instead.")
        else:
            notes.append("ffmpeg not found; saved WAV instead of M4B.")
        target = target.with_suffix(".wav")

    # WAV output (or MP3 fallback): WAV has no CHAP frames, so write a sidecar
    # chapters file alongside it for tools that can read it.
    import shutil

    shutil.copyfile(assembled_wav, target)
    _write_chapter_sidecar(target, chapters)
    return target


def _write_chapter_sidecar(audio_path: Path, chapters: list[Chapter]) -> None:
    """Write a simple ``<name>.chapters.txt`` (ms ranges + titles) next to WAV output."""
    lines = [f"{c.start_ms}\t{c.end_ms}\t{c.title}" for c in chapters]
    audio_path.with_suffix(".chapters.txt").write_text("\n".join(lines), encoding="utf-8")


def _with_tones_name(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem} (with chapter tones){output_path.suffix}")
