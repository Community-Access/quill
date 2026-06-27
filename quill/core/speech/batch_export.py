"""Batch TTS export: folder-scan → text-extract → synthesize → WAV files.

wx-free; all synthesis calls block the caller's thread.  The UI layer
wraps :func:`run_batch_export` in its own thread and uses ``wx.CallAfter``
for progress updates.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from quill.core.speech.batch_discovery import discover_files
from quill.core.speech.batch_manifest import write_manifest
from quill.core.speech.ffmpeg import AudioMetadata
from quill.core.speech.pronunciation import PronunciationDictionary, apply_pronunciations
from quill.core.speech.text_normalize import TextNormalizationOptions, normalize_for_tts
from quill.core.speech.text_polish import UnsupportedFormatError, extract_text, polish_for_tts

__all__ = [
    "BatchExportOptions",
    "BatchFileResult",
    "TransformPreview",
    "discover_files",
    "run_batch_export",
    "transform_preview",
    "write_manifest",
    "SUPPORTED_EXTENSIONS",
]

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".md", ".html", ".htm", ".docx", ".txt")

BatchStatus = Literal["pending", "processing", "done", "error", "skipped"]

# wav (always available) plus the ffmpeg-encoded listening formats. mp3/m4b/…
# fall back to wav per-file when ffmpeg is absent (§4.1).
OutputFormat = Literal["wav", "mp3", "m4a", "m4b", "opus", "flac", "ogg"]
_COMPRESSED_FORMATS: frozenset[str] = frozenset({"mp3", "m4a", "m4b", "opus", "flac", "ogg"})

# What to do when a target file already exists.
ExistingPolicy = Literal["skip", "overwrite", "rename"]

# Engines that are NOT safe to drive from several threads at once: SAPI 5 is a
# single-apartment COM voice and Kokoro shares one cached in-process model. These
# are pinned to one worker regardless of ``max_workers`` (§4 concurrency guard).
_SINGLE_THREAD_ENGINES: frozenset[str] = frozenset({"sapi5", "kokoro", "pyttsx3"})


@dataclass
class BatchExportOptions:
    source_folder: Path
    output_folder: Path
    engine: str = "sapi5"
    extensions: list[str] = field(default_factory=lambda: [".md", ".html", ".docx", ".txt"])
    recursive: bool = True
    # Discovery filters (§discovery): semicolon/comma-separated glob lists matched
    # against each file's name and its path relative to the source folder. An empty
    # include list keeps everything; exclude wins over include. ``max_file_bytes``
    # of 0 means "no size cap".
    include_glob: str = ""
    exclude_glob: str = ""
    max_file_bytes: int = 0
    # Output format (§4.1): "wav" (default, always available) or a compressed
    # format (mp3/m4a/m4b/opus/flac/ogg — requires ffmpeg; falls back to wav with a
    # per-file note when ffmpeg is absent).
    output_format: OutputFormat = "wav"
    # MP3 encode quality: libmp3lame VBR -q:a (0 best/largest .. 9 smallest).
    mp3_vbr_quality: str = "4"
    # Uniform WAV output: re-sample / down-mix to these when set (None = leave as
    # the engine produced it). Requires ffmpeg; ignored silently when unavailable.
    wav_sample_rate: int | None = None
    wav_channels: int | None = None
    # Existing-file policy (§4.1 resume): "skip" leaves a present output untouched
    # (cheap resume), "overwrite" re-synthesizes it, "rename" writes a unique
    # sibling ("name (2).mp3"). ``skip_existing`` is the legacy boolean alias for
    # "skip" and is honored when set for backwards compatibility.
    on_existing: ExistingPolicy = "overwrite"
    skip_existing: bool = False
    # Output layout: mirror the source tree (default) or flatten into one folder;
    # ``filename_template`` renames each stem with {stem}/{index}/{index0} fields.
    flatten: bool = False
    filename_template: str = ""
    # Audiobook / file tags stamped on compressed outputs (none for wav). The
    # per-file title defaults to the document stem when ``metadata.title`` is blank.
    metadata: AudioMetadata = field(default_factory=AudioMetadata)
    # Error policy: stop the whole batch on the first hard error, and/or retry a
    # failed synthesis up to ``retry_count`` extra times (flaky subprocess engines).
    stop_on_error: bool = False
    retry_count: int = 0
    # Concurrency: synthesize up to this many files at once. Clamped to 1 for the
    # single-apartment engines (see ``_SINGLE_THREAD_ENGINES``).
    max_workers: int = 1
    # Write a manifest.json + manifest.csv of the run into the output folder.
    write_manifest: bool = False
    # SAPI 5 (Windows system voice)
    sapi5_voice: str = ""
    sapi5_rate: int = 200
    sapi5_volume: float = 1.0
    # DECtalk
    dectalk_executable: Path | None = None
    dectalk_voice: str = "paul"
    dectalk_rate: int = 180
    dectalk_dictionary: Path | None = None
    # Piper
    piper_executable: Path | None = None
    piper_model: Path | None = None
    piper_length_scale: float | None = None  # >1 slower, <1 faster; None = model default
    piper_noise_scale: float | None = None
    piper_noise_w: float | None = None
    # Kokoro
    kokoro_voice: str = "af_heart"
    kokoro_speed: float = 1.0
    # eSpeak-NG
    espeak_executable: Path | None = None
    espeak_voice: str = "en"
    espeak_rate: int = 175
    espeak_pitch: int | None = None  # 0-99; None = engine default
    espeak_word_gap_ms: int | None = None  # extra silence between words; None = default
    # Pronunciation dictionaries (§4.7): the resolved active set for this engine
    # and (the source folder as) project. Applied as a silent text transform before
    # synthesis — batch writes audio files to disk and never reads aloud.
    pronunciation_dictionaries: list[PronunciationDictionary] = field(default_factory=list)
    # Text normalization (§4.9): when set, cleans typography/unicode and speaks
    # phones/emails/URLs clearly before pronunciation + polish. None = skip.
    normalization: TextNormalizationOptions | None = None


@dataclass
class BatchFileResult:
    source_path: Path
    output_path: Path | None = None
    status: BatchStatus = "pending"
    error: str | None = None
    duration_s: float | None = None
    pronunciation_applied: int = 0  # §4.7.10 per-file substitution count


ProgressFn = Callable[[int, int, "BatchFileResult"], None]
"""Called after each file: (done_count, total_count, updated_result)."""


def _apply_template(stem: str, template: str, index: int, total: int) -> str:
    """Render ``filename_template`` for one file, falling back to ``stem`` safely.

    Recognized fields: ``{stem}``, ``{index}`` (1-based), ``{index0}`` (0-based),
    ``{total}``. Zero-padded forms like ``{index:03d}`` work too. A malformed
    template degrades to the original stem rather than raising.
    """
    if not template.strip():
        return stem
    try:
        rendered = template.format(stem=stem, index=index, index0=index - 1, total=total).strip()
    except (KeyError, IndexError, ValueError):
        return stem
    return rendered or stem


def _output_path_for(
    source: Path,
    source_root: Path,
    output_root: Path,
    output_format: OutputFormat = "wav",
    *,
    flatten: bool = False,
    filename_template: str = "",
    index: int = 1,
    total: int = 1,
) -> Path:
    """Resolve the output path for *source*.

    Mirrors *source*'s relative tree under *output_root* (or flattens to a single
    folder when ``flatten``), renames the stem via ``filename_template`` when set,
    and applies the format suffix.
    """
    try:
        rel = source.relative_to(source_root)
    except ValueError:
        rel = Path(source.name)
    stem = _apply_template(rel.stem, filename_template, index, total)
    if flatten:
        target = output_root / stem
    else:
        target = output_root / rel.parent / stem
    return target.with_suffix(f".{output_format}")


def _synthesize_one(text: str, output_path: Path, opts: BatchExportOptions) -> None:
    """Call the appropriate synthesis function for the configured engine."""
    from quill.core.read_aloud import (
        ReadAloudUnavailableError,
        synthesize_to_file_with_dectalk,
        synthesize_to_file_with_sapi5,
        synthesize_with_espeak,
        synthesize_with_kokoro,
        synthesize_with_piper,
    )

    engine = opts.engine.strip().lower()
    if engine == "pyttsx3":  # migrate the retired engine id
        engine = "sapi5"

    if engine == "sapi5":
        synthesize_to_file_with_sapi5(
            text,
            output_path,
            voice=opts.sapi5_voice,
            rate=opts.sapi5_rate,
            volume=opts.sapi5_volume,
        )
    elif engine == "dectalk":
        if opts.dectalk_executable is None:
            raise ReadAloudUnavailableError("DECtalk executable not configured")
        synthesize_to_file_with_dectalk(
            text,
            output_path,
            executable_path=opts.dectalk_executable,
            voice=opts.dectalk_voice,
            rate=opts.dectalk_rate,
            dictionary_path=opts.dectalk_dictionary,
        )
    elif engine == "piper":
        if opts.piper_executable is None:
            raise ReadAloudUnavailableError("Piper executable not configured")
        if opts.piper_model is None:
            raise ReadAloudUnavailableError("Piper model not configured")
        synthesize_with_piper(
            text,
            output_path,
            executable_path=opts.piper_executable,
            model_path=opts.piper_model,
            length_scale=opts.piper_length_scale,
            noise_scale=opts.piper_noise_scale,
            noise_w=opts.piper_noise_w,
        )
    elif engine == "kokoro":
        synthesize_with_kokoro(
            text,
            output_path,
            voice=opts.kokoro_voice,
            speed=opts.kokoro_speed,
        )
    elif engine == "espeak":
        if opts.espeak_executable is None:
            raise ReadAloudUnavailableError("eSpeak-NG executable not configured")
        synthesize_with_espeak(
            text,
            output_path,
            executable_path=opts.espeak_executable,
            voice=opts.espeak_voice,
            rate=opts.espeak_rate,
            pitch=opts.espeak_pitch,
            word_gap_ms=opts.espeak_word_gap_ms,
        )
    else:
        raise ReadAloudUnavailableError(f"Unknown engine: {engine!r}")


def _file_metadata(opts: BatchExportOptions, out: Path, index: int) -> AudioMetadata:
    """Per-file tags: the configured metadata, with title/track filled per file."""
    base = opts.metadata
    return AudioMetadata(
        title=base.title.strip() or out.stem,
        artist=base.artist,
        album=base.album,
        album_artist=base.album_artist,
        genre=base.genre,
        year=base.year,
        track=base.track.strip() or str(index),
        comment=base.comment,
    )


def _synthesize_to_output(
    text: str,
    out: Path,
    opts: BatchExportOptions,
    res: BatchFileResult,
    *,
    index: int = 1,
) -> None:
    """Synthesize *text* to *out*, honoring ``output_format`` and tags.

    For WAV, synthesize straight to *out* (optionally re-sampled/down-mixed to the
    requested rate/channels). For a compressed format, synthesize to a temp WAV
    and encode with ffmpeg; if ffmpeg is unavailable or the encode fails, fall back
    to a sibling WAV and note it on *res* (never hard-fail the batch — §4.1).
    """
    import tempfile

    from quill.core.speech.ffmpeg import (
        TranscodeError,
        conform_wav,
        ffmpeg_available,
        transcode_audio,
    )

    fmt = opts.output_format
    if fmt not in _COMPRESSED_FORMATS:
        # WAV output. Conform to a uniform rate/channels only when asked and able.
        if (opts.wav_sample_rate or opts.wav_channels) and ffmpeg_available():
            with tempfile.TemporaryDirectory(prefix="quill_batch_wav_") as tmp:
                wav_tmp = Path(tmp) / (out.stem + ".raw.wav")
                _synthesize_one(text, wav_tmp, opts)
                try:
                    conform_wav(
                        wav_tmp,
                        out,
                        sample_rate=opts.wav_sample_rate,
                        channels=opts.wav_channels,
                    )
                except TranscodeError as exc:
                    wav_tmp.replace(out)
                    res.error = f"WAV conform failed ({exc}); saved as synthesized"
            return
        _synthesize_one(text, out, opts)
        return

    if not ffmpeg_available():
        wav_out = out.with_suffix(".wav")
        _synthesize_one(text, wav_out, opts)
        res.output_path = wav_out
        res.error = f"ffmpeg not found; saved WAV instead of {fmt.upper()}"
        return

    with tempfile.TemporaryDirectory(prefix="quill_batch_enc_") as tmp:
        wav_tmp = Path(tmp) / (out.stem + ".wav")
        _synthesize_one(text, wav_tmp, opts)
        try:
            transcode_audio(
                wav_tmp,
                out,
                fmt,
                mp3_vbr_quality=opts.mp3_vbr_quality,
                metadata=_file_metadata(opts, out, index),
            )
        except TranscodeError as exc:
            wav_out = out.with_suffix(".wav")
            wav_tmp.replace(wav_out)
            res.output_path = wav_out
            res.error = f"{fmt.upper()} encode failed ({exc}); saved WAV instead"


def _unique_path(out: Path) -> Path:
    """Return *out*, or the first free ``name (N).ext`` sibling if it exists."""
    if not out.exists():
        return out
    parent, stem, suffix = out.parent, out.stem, out.suffix
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_existing(out: Path, options: BatchExportOptions, res: BatchFileResult) -> Path | None:
    """Apply the existing-file policy; return the path to write, or None to skip.

    The legacy ``skip_existing`` boolean still forces "skip" when set, so old
    callers keep their resume behaviour.
    """
    policy: ExistingPolicy = "skip" if options.skip_existing else options.on_existing
    if not out.exists():
        return out
    if policy == "skip":
        res.output_path = out
        res.status = "skipped"
        res.error = "Already exported"
        return None
    if policy == "rename":
        return _unique_path(out)
    return out  # overwrite


def _synthesize_with_retry(
    text: str,
    out: Path,
    options: BatchExportOptions,
    res: BatchFileResult,
    index: int,
) -> None:
    """Synthesize, retrying hard failures up to ``retry_count`` extra times."""
    attempts = max(0, options.retry_count) + 1
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            _synthesize_to_output(text, out, options, res, index=index)
            return
        except Exception as exc:  # noqa: BLE001 - retry transient engine failures
            last_exc = exc
            res.error = None
    if last_exc is not None:
        raise last_exc


def _process_one(
    options: BatchExportOptions,
    res: BatchFileResult,
    index: int,
    total: int,
) -> None:
    """Run the full extract -> normalize -> synthesize pipeline for one file.

    Updates *res* in place; never raises (per-file failures are recorded on *res*).
    """
    out = _output_path_for(
        res.source_path,
        options.source_folder,
        options.output_folder,
        options.output_format,
        flatten=options.flatten,
        filename_template=options.filename_template,
        index=index,
        total=total,
    )
    target = _resolve_existing(out, options, res)
    if target is None:
        return  # skipped by the existing-file policy; status already set

    t0 = time.monotonic()
    try:
        text = extract_text(res.source_path)
        # §4.9.5: text normalization runs first (cleans typography; speaks
        # phones/emails/URLs) so pronunciation matching sees clean text.
        if options.normalization is not None:
            text = normalize_for_tts(text, options.normalization)
        # §4.7.4: pronunciation correction runs before polishing, as a silent
        # text transform (no audio) — the same stage the live path uses.
        if options.pronunciation_dictionaries:
            applied = apply_pronunciations(text, options.engine, options.pronunciation_dictionaries)
            text = applied.text
            res.pronunciation_applied = applied.total_applied
        text = polish_for_tts(text)
        if not text.strip():
            res.status = "skipped"
            res.error = "No speakable text"
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        res.output_path = target
        _synthesize_with_retry(text, target, options, res, index)
        res.status = "done"
        res.duration_s = time.monotonic() - t0
    except UnsupportedFormatError as exc:
        res.status = "skipped"
        res.error = str(exc)
    except Exception as exc:  # noqa: BLE001
        res.status = "error"
        res.error = str(exc)


def _effective_workers(options: BatchExportOptions) -> int:
    """Worker count, clamped to 1 for single-apartment engines (SAPI 5, Kokoro)."""
    if options.engine.strip().lower() in _SINGLE_THREAD_ENGINES:
        return 1
    return max(1, int(options.max_workers))


def run_batch_export(
    options: BatchExportOptions,
    results: list[BatchFileResult],
    on_progress: ProgressFn,
    cancel_event: threading.Event,
) -> None:
    """Process every file in *results*.

    *results* must be pre-populated (e.g. from :func:`discover_files`) with
    ``status="pending"``. Updates each entry in-place and calls *on_progress*
    after every file so the UI can refresh. Honors the existing-file policy,
    retries, stop-on-error, and (for process-safe engines) ``max_workers``. When
    ``write_manifest`` is set, a manifest.json/.csv is written at the end.
    """
    total = len(results)
    workers = _effective_workers(options)
    if workers <= 1:
        _run_sequential(options, results, on_progress, cancel_event, total)
    else:
        _run_parallel(options, results, on_progress, cancel_event, total, workers)

    if options.write_manifest:
        try:
            write_manifest(options.output_folder, results)
        except OSError:
            pass


def _run_sequential(
    options: BatchExportOptions,
    results: list[BatchFileResult],
    on_progress: ProgressFn,
    cancel_event: threading.Event,
    total: int,
) -> None:
    done = 0
    for index, res in enumerate(results, start=1):
        if cancel_event.is_set():
            res.status = "skipped"
            on_progress(done, total, res)
            continue
        res.status = "processing"
        on_progress(done, total, res)
        _process_one(options, res, index, total)
        if res.status == "error" and options.stop_on_error:
            cancel_event.set()
        done += 1
        on_progress(done, total, res)


def _run_parallel(
    options: BatchExportOptions,
    results: list[BatchFileResult],
    on_progress: ProgressFn,
    cancel_event: threading.Event,
    total: int,
    workers: int,
) -> None:
    lock = threading.Lock()

    def task(index: int, res: BatchFileResult) -> BatchFileResult:
        if cancel_event.is_set():
            if res.status == "pending":
                res.status = "skipped"
            return res
        _process_one(options, res, index, total)
        if res.status == "error" and options.stop_on_error:
            cancel_event.set()
        return res

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(task, i, r) for i, r in enumerate(results, start=1)]
        for future in futures:
            res = future.result()
            with lock:
                done += 1
                on_progress(done, total, res)


# write_manifest is defined in batch_manifest.py and imported at the top of this
# module; it remains importable from batch_export for callers and __all__.


@dataclass
class TransformPreview:
    """The result of the dry-run text transform: what a file will say, and how
    many pronunciation substitutions were applied."""

    text: str
    substitutions: int


def count_words(text: str) -> int:
    """Whitespace-delimited word count — the unit the progress dialog reports in."""
    return len(text.split())


def count_document_words(path: Path) -> int:
    """Words in *path*'s readable text, or 0 when it cannot be read.

    Used to pre-compute the corpus size so batch progress can be reported as a
    percentage (words processed / total words). Best-effort: an unreadable or
    unsupported file contributes 0 rather than aborting the count.
    """
    try:
        return count_words(extract_text(path))
    except (UnsupportedFormatError, OSError, ValueError):
        return 0


def transform_preview(
    text: str,
    *,
    engine: str = "sapi5",
    normalization: TextNormalizationOptions | None = None,
    pronunciation_dictionaries: list[PronunciationDictionary] | None = None,
) -> TransformPreview:
    """Run the batch text-transform pipeline without synthesizing (the dry run).

    Mirrors the per-file pipeline in :func:`_process_one` — normalize → pronounce →
    polish — and returns the exact text a file would speak plus the pronunciation
    substitution count, so the user can review the transform before paying for
    synthesis.
    """
    if normalization is not None:
        text = normalize_for_tts(text, normalization)
    substitutions = 0
    if pronunciation_dictionaries:
        applied = apply_pronunciations(text, engine, pronunciation_dictionaries)
        text = applied.text
        substitutions = applied.total_applied
    return TransformPreview(text=polish_for_tts(text), substitutions=substitutions)
