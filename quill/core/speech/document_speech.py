"""Drive a document end-to-end to a chaptered speech file (§4.8 glue).

This is the missing production seam between the structure-aware extractor
(:func:`quill.core.speech.text_polish.extract_sections`) and the chapter
assembler (:func:`quill.core.speech.chapter_assemble.assemble_chaptered_audio`).
The assembler deliberately takes an **injected** synthesizer so a real engine and
the test fake share one path; this module resolves a chosen engine/voice into that
synthesizer and runs the whole pipeline:

    document -> extract_sections -> assemble (per-engine synth + sounder) -> WAV/MP3

It is ``wx``-free and strict-typed (it lives in ``quill/core``), so the future
batch UI and headless callers can share exactly this resolution logic rather than
re-deriving it. Local engines (SAPI 5, Kokoro, Piper, DECtalk, eSpeak-NG) plus the
multilingual cloud providers (OpenAI / Gemini / ElevenLabs) for translated export.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from quill.core import read_aloud
from quill.core.error_codes import CodedError
from quill.core.speech.chapter_assemble import (
    ChapterAssembleOptions,
    ChapterAssembleResult,
    Synthesizer,
    assemble_chaptered_audio,
)
from quill.core.speech.text_polish import extract_sections
from quill.core.speech.translate_sections import Translator, translate_sections

# Engine ids accepted by :func:`make_synthesizer`. These mirror the
# ``read_aloud_engine`` setting and the batch options' per-engine blocks.
SUPPORTED_ENGINES = ("sapi5", "kokoro", "piper", "dectalk", "espeak")
# Multilingual cloud TTS providers (the premium tier for translated export). Each
# voice can speak any language, so these are the natural fit for a translated
# document; they require a configured API key and ffmpeg (to conform the provider's
# MP3/WAV into the splice-ready PCM WAV the assembler expects).
CLOUD_ENGINES = ("openai", "gemini", "elevenlabs")


class DocumentSpeechError(CodedError):
    """Raised when an engine cannot be resolved into a usable synthesizer."""

    code = "QUILL-SPEECH-DOCUMENT-ENGINE"


@dataclass(frozen=True, slots=True)
class SynthesisSpec:
    """A resolved request for one engine + voice + speed.

    ``rate`` is words-per-minute for SAPI 5 / eSpeak / DECtalk; ``speed`` is the
    Kokoro multiplier. ``voice`` is the engine-native voice id (e.g. ``am_liam``
    for Kokoro, a SAPI voice id, or — for Piper — the ``.onnx`` model path when
    ``piper_model`` is not given). ``executable`` overrides auto-discovery for the
    subprocess engines (Piper/DECtalk/eSpeak); when ``None`` they are discovered.
    """

    engine: str
    voice: str = ""
    rate: int = 200
    speed: float = 1.0
    volume: float = 1.0
    piper_model: Path | None = None
    executable: Path | None = None
    # Cloud-engine credentials (openai/gemini/elevenlabs only). ``api_key`` is
    # required for those engines; ``model`` falls back to the provider default.
    api_key: str = ""
    model: str = ""


def make_synthesizer(spec: SynthesisSpec) -> Synthesizer:
    """Resolve *spec* into a ``(text, out_wav) -> None`` synthesizer callable.

    Raises :class:`DocumentSpeechError` for an unknown engine or when a required
    executable/model for a subprocess engine cannot be found.
    """
    engine = spec.engine.strip().lower()
    # pyttsx3 was the historical id for the SAPI 5 path.
    if engine == "pyttsx3":
        engine = "sapi5"

    if engine == "sapi5":

        def _sapi5(text: str, out: Path) -> None:
            read_aloud.synthesize_to_file_with_sapi5(
                text, out, voice=spec.voice, rate=spec.rate, volume=spec.volume
            )

        return _sapi5

    if engine == "kokoro":

        def _kokoro(text: str, out: Path) -> None:
            read_aloud.synthesize_with_kokoro(
                text, out, voice=spec.voice or "af_heart", speed=spec.speed
            )

        return _kokoro

    if engine == "piper":
        piper_exe = spec.executable or read_aloud.discover_piper_executable()
        if piper_exe is None:
            raise DocumentSpeechError("Piper executable was not found.")
        model = spec.piper_model or (Path(spec.voice) if spec.voice else None)
        if model is None or not model.exists():
            raise DocumentSpeechError("A Piper .onnx model path is required.")
        piper_model: Path = model

        def _piper(text: str, out: Path) -> None:
            read_aloud.synthesize_with_piper(
                text, out, executable_path=piper_exe, model_path=piper_model
            )

        return _piper

    if engine == "dectalk":
        dectalk_exe = spec.executable or read_aloud.discover_dectalk_executable()
        if dectalk_exe is None:
            raise DocumentSpeechError("DECtalk runtime (DECtalk.dll) was not found.")

        def _dectalk(text: str, out: Path) -> None:
            read_aloud.synthesize_to_file_with_dectalk(
                text, out, executable_path=dectalk_exe, voice=spec.voice or "paul", rate=spec.rate
            )

        return _dectalk

    if engine == "espeak":
        espeak_exe = spec.executable or read_aloud.discover_espeak_executable()
        if espeak_exe is None:
            raise DocumentSpeechError("eSpeak-NG executable was not found.")

        def _espeak(text: str, out: Path) -> None:
            read_aloud.synthesize_with_espeak(
                text, out, executable_path=espeak_exe, voice=spec.voice or "en", rate=spec.rate
            )

        return _espeak

    if engine in CLOUD_ENGINES:
        return _make_cloud_synthesizer(engine, spec)

    raise DocumentSpeechError(
        f"Unknown speech engine {spec.engine!r}. Expected one of "
        f"{SUPPORTED_ENGINES + CLOUD_ENGINES}."
    )


def _make_cloud_synthesizer(engine: str, spec: SynthesisSpec) -> Synthesizer:
    """Resolve a cloud provider into a ``(text, out_wav) -> None`` synthesizer.

    The provider exports MP3 (OpenAI/ElevenLabs) or WAV (Gemini); we conform that
    to the splice-ready PCM WAV the assembler concatenates. Requires an API key and
    ffmpeg — both raise :class:`DocumentSpeechError` up front when missing so a
    cloud translated export fails fast rather than mid-batch.
    """
    if not spec.api_key:
        raise DocumentSpeechError(
            f"A {engine} API key is required for cloud voice synthesis. "
            "Add the key in AI Hub and try again."
        )
    from quill.core.ai import cloud_tts
    from quill.core.speech.ffmpeg import INSTALL_HINT, conform_wav, find_ffmpeg

    if find_ffmpeg() is None:
        raise DocumentSpeechError(f"ffmpeg is required to assemble cloud audio. {INSTALL_HINT}")
    model = spec.model or cloud_tts.default_model(engine)
    voice = spec.voice or cloud_tts.default_voice(engine)

    def _cloud(text: str, out: Path) -> None:
        import shutil

        work = Path(tempfile.mkdtemp(prefix="quill_cloudtts_"))
        try:
            media = cloud_tts.export_audio(
                engine,
                text,
                work / "segment",
                spec.api_key,
                model=model,
                voice=voice,
                speed=spec.speed,
            )
            conform_wav(Path(media), out)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    return _cloud


def _wrap_with_pronunciations(
    synth: Synthesizer, engine: str, dictionaries: list[Any] | None
) -> Synthesizer:
    """Wrap *synth* so the active pronunciation set is applied before synthesis."""
    if not dictionaries:
        return synth

    from quill.core.speech.pronunciation import apply_pronunciations

    engine_id = "sapi5" if engine.strip().lower() == "pyttsx3" else engine.strip().lower()

    def _corrected(text: str, out: Path) -> None:
        synth(apply_pronunciations(text, engine_id, dictionaries).text, out)

    return _corrected


def _wrap_with_failure_recording(
    synth: Synthesizer, engine: str, voice_id: str, blacklist: Any | None
) -> Synthesizer:
    """Record a voice's synthesis failure in *blacklist* (then re-raise) when given.

    Behavior this run is unchanged — the exception still propagates — but the voice
    is now remembered so a later run can skip it (the voice-failure blacklist,
    roadmap §5). A ``None`` blacklist or empty voice id is a passthrough.
    """
    if blacklist is None or not voice_id.strip():
        return synth

    def _recorded(text: str, out: Path) -> None:
        try:
            synth(text, out)
        except Exception as exc:  # noqa: BLE001 - record then re-raise unchanged
            blacklist.record_failure(engine, voice_id, str(exc))
            raise

    return _recorded


def _build_voice_rotation(
    spec: SynthesisSpec,
    voices: list[str] | None,
    pronunciation_dictionaries: list[Any] | None,
    blacklist: Any | None = None,
) -> list[Synthesizer] | None:
    """One wrapped synthesizer per voice for round-robin, or None when not in use.

    Each voice reuses *spec*'s engine and pace (so every section shares one PCM
    format and splices cleanly). Voices already on *blacklist* (the voice-failure
    blacklist) are dropped first, so a known-bad voice is skipped on later runs.
    Fewer than two distinct usable voices returns None, leaving the single-voice
    path unchanged.
    """
    cleaned: list[str] = []
    for voice in voices or []:
        name = voice.strip()
        if not name or name in cleaned:
            continue
        if blacklist is not None and blacklist.is_blacklisted(spec.engine, name):
            continue
        cleaned.append(name)
    if len(cleaned) < 2:
        return None
    rotation: list[Synthesizer] = []
    for voice in cleaned:
        synth = make_synthesizer(replace(spec, voice=voice))
        synth = _wrap_with_pronunciations(synth, spec.engine, pronunciation_dictionaries)
        rotation.append(_wrap_with_failure_recording(synth, spec.engine, voice, blacklist))
    return rotation


def _build_casting(
    spec: SynthesisSpec,
    rules: list[tuple[str, str]] | None,
    pronunciation_dictionaries: list[Any] | None,
    blacklist: Any | None = None,
) -> Any | None:
    """A ``synthesizer_for(index, title)`` from explicit casting rules, or None.

    Each cast voice reuses *spec*'s engine and pace (one PCM format across the
    book) and gets the same pronunciation + failure-recording wrappers as the
    rotation. Blacklisted voices lose their rules (those sections fall through
    to the rotation / single voice rather than failing the run).
    """
    from quill.core.speech.casting import cast_voices, normalize_rules, voice_for_section

    usable = [
        (pattern, voice)
        for pattern, voice in normalize_rules(rules)
        if blacklist is None or not blacklist.is_blacklisted(spec.engine, voice)
    ]
    if not usable:
        return None
    synth_by_voice: dict[str, Synthesizer] = {}
    for voice in cast_voices(usable):
        synth = make_synthesizer(replace(spec, voice=voice))
        synth = _wrap_with_pronunciations(synth, spec.engine, pronunciation_dictionaries)
        synth_by_voice[voice] = _wrap_with_failure_recording(synth, spec.engine, voice, blacklist)

    def synthesizer_for(index: int, title: str) -> Synthesizer | None:
        voice = voice_for_section(usable, index + 1, title)
        return synth_by_voice.get(voice) if voice else None

    return synthesizer_for


def synthesize_document_to_chaptered_file(
    source: Path,
    output_path: Path,
    spec: SynthesisSpec,
    options: ChapterAssembleOptions,
    *,
    work_dir: Path | None = None,
    pronunciation_dictionaries: list[Any] | None = None,
    combine_headings: bool = False,
    max_heading_level: int = 0,
    voice_rotation: list[str] | None = None,
    casting_rules: list[tuple[str, str]] | None = None,
    translate: Translator | None = None,
    voice_blacklist: Any | None = None,
    on_progress: Any | None = None,
) -> ChapterAssembleResult:
    """Convert one document to a chaptered audio file using a real engine.

    Extracts heading-bounded sections from *source*, synthesizes each with the
    engine described by *spec*, and assembles them into *output_path* with the
    inter-article gap / sounder and chapter markers described by *options*. When
    *work_dir* is ``None`` a temporary directory is created and removed afterward.

    *pronunciation_dictionaries* (the resolved active set, most-specific-first) is
    applied to **every spoken string** just before synthesis — so corrections
    reach the spoken heading, the body, and each sentence — while the chapter
    marker titles stay the raw heading text. Returns the
    :class:`ChapterAssembleResult` (the clean file plus, when the sounder is
    enabled, the with-tones variant carrying identical chapter timing).
    """
    sections = extract_sections(
        source, combine_headings=combine_headings, max_heading_level=max_heading_level
    )
    if not sections:
        raise DocumentSpeechError(f"No readable text found in {source.name}.")
    if translate is not None:
        sections = translate_sections(sections, translate)
    synth = make_synthesizer(spec)
    synth = _wrap_with_pronunciations(synth, spec.engine, pronunciation_dictionaries)
    synth = _wrap_with_failure_recording(synth, spec.engine, spec.voice, voice_blacklist)
    # Round-robin voices: one synthesizer per voice (same engine), cycled per
    # section by the assembler. Empty/one voice → the single synthesizer above.
    rotation = _build_voice_rotation(
        spec, voice_rotation, pronunciation_dictionaries, voice_blacklist
    )
    synthesizer_for = _build_casting(
        spec, casting_rules, pronunciation_dictionaries, voice_blacklist
    )

    owns_work_dir = work_dir is None
    work_dir = work_dir or Path(tempfile.mkdtemp(prefix="quill_docspeech_"))
    try:
        return assemble_chaptered_audio(
            sections,
            output_path,
            synth,
            options,
            work_dir=work_dir,
            synthesizers=rotation,
            synthesizer_for=synthesizer_for,
            on_progress=on_progress,
        )
    finally:
        if owns_work_dir:
            import shutil

            shutil.rmtree(work_dir, ignore_errors=True)


_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def _safe_filename(text: str, fallback: str) -> str:
    """A filesystem-safe file stem from a heading title, trimmed and de-spaced."""
    cleaned = _UNSAFE_NAME.sub(" ", text).strip().rstrip(". ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned[:80].strip() or fallback


def synthesize_document_to_separate_files(
    source: Path,
    output_dir: Path,
    spec: SynthesisSpec,
    options: ChapterAssembleOptions,
    *,
    work_dir: Path | None = None,
    pronunciation_dictionaries: list[Any] | None = None,
    combine_headings: bool = False,
    max_heading_level: int = 0,
    voice_rotation: list[str] | None = None,
    translate: Translator | None = None,
    voice_blacklist: Any | None = None,
) -> list[Path]:
    """Convert one document to **one audio file per article** (the `separate` mode).

    Each heading-bounded section becomes its own file in *output_dir*, named
    ``NNN - <heading>.<ext>`` (natural order preserved, headings made
    filesystem-safe). Each file is produced through the same single-section
    assembly path as the chaptered output (so engine, chunking, pronunciation,
    and format/encoding match), just without an inter-article boundary. With
    *combine_headings*, heading-only sections fold into the next article; with
    *voice_rotation*, each file is voiced by the next voice in the list. Returns
    the written paths in order.
    """
    sections = extract_sections(
        source, combine_headings=combine_headings, max_heading_level=max_heading_level
    )
    if not sections:
        raise DocumentSpeechError(f"No readable text found in {source.name}.")
    if translate is not None:
        sections = translate_sections(sections, translate)
    synth = make_synthesizer(spec)
    synth = _wrap_with_pronunciations(synth, spec.engine, pronunciation_dictionaries)
    synth = _wrap_with_failure_recording(synth, spec.engine, spec.voice, voice_blacklist)
    rotation = _build_voice_rotation(
        spec, voice_rotation, pronunciation_dictionaries, voice_blacklist
    )
    suffix = f".{options.output_format}" if options.output_format in {"mp3", "m4b"} else ".wav"

    owns_work_dir = work_dir is None
    work_dir = work_dir or Path(tempfile.mkdtemp(prefix="quill_docspeech_"))
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    try:
        for index, section in enumerate(sections, start=1):
            title = section.title.strip() or options.intro_section_title
            stem = f"{index:03d} - {_safe_filename(title, f'section_{index:03d}')}"
            out = output_dir / f"{stem}{suffix}"
            file_synth = rotation[(index - 1) % len(rotation)] if rotation else synth
            result = assemble_chaptered_audio(
                [section], out, file_synth, options, work_dir=work_dir / f"sep_{index:04d}"
            )
            written.append(result.output_path)
    finally:
        if owns_work_dir:
            import shutil

            shutil.rmtree(work_dir, ignore_errors=True)
    return written
