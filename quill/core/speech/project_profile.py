"""Project-remembered speech settings — ``<project>/.quill/speech-project.json`` (§4.10).

wx-free, strict-typed. A *project* is a folder of documents; this module persists
that folder's whole speech profile so the user configures **once per project**:
the synthesizer (engine + voice + rate/speed), the output format, the chapter
options, the text-normalization options, and which pronunciation dictionaries
(and their formats) are active.

The on-disk format is documented in ``docs/planning/speech-project-format.md`` and
schema-described in ``quill/core/schemas/speech_project.json``. The dataclasses
here are the in-memory mirror, with ``to_dict`` / ``from_dict`` (tolerant of
missing keys and old versions) and ``load_profile`` / ``save_profile`` for the
atomic JSON file. Convenience converters (:func:`to_batch_options`,
:func:`to_chapter_options`) turn a profile into the runtime option objects so the
batch pipeline can be driven straight from a project file — including headlessly
in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

PROJECT_DIRNAME = ".quill"
PROFILE_FILENAME = "speech-project.json"
# v1: original profile (synthesizer, discovery, output, chapters, etc.).
# v2: adds top-level ``book_credits`` and ``library_mode`` booleans.
#     ``from_dict`` is tolerant of v1 data: missing fields default
#     to False so older project folders load without an upgrade.
PROFILE_VERSION = 2

_VALID_ENGINES = {"sapi5", "dectalk", "piper", "kokoro", "espeak", "macos"}
_VALID_FORMATS = {"wav", "mp3", "m4a", "m4b", "opus", "flac", "ogg"}
_VALID_EXISTING = {"skip", "overwrite", "rename"}
_VALID_CHAPTER_MODES = {"none", "single", "separate"}
_VALID_SCOPES = {"global", "project"}
_VALID_TRANSLATION_PROVIDERS = {"ai_assistant", "libretranslate"}
_DEFAULT_EXTENSIONS = [".docx", ".md", ".html", ".txt"]
# Dictionary file formats we know how to read. "quill-json" is the native
# PronunciationDictionary schema; others are reserved for future importers.
_VALID_DICT_FORMATS = {"quill-json", "sapi-lexicon", "csv"}


def _clamp_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return default


def _opt_int(value: Any, lo: int, hi: int) -> int | None:
    """Clamp ``value`` to [lo, hi], or None when it is missing/blank/invalid."""
    if value is None or value == "":
        return None
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return None


def _str_list(value: Any, default: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
        return items or list(default)
    return list(default)


@dataclass(slots=True)
class SynthesizerProfile:
    """The chosen engine and its voice/pace. ``extra`` holds engine-specific keys."""

    engine: str = "sapi5"
    voice: str = ""
    rate: int = 200  # words-per-minute style rate (SAPI/eSpeak/DECtalk)
    volume: float = 1.0  # 0.0-1.0
    speed: float = 1.0  # multiplier engines that use one (Kokoro)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "speed": self.speed,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SynthesizerProfile:
        engine = str(data.get("engine", "sapi5")).strip().lower()
        if engine not in _VALID_ENGINES:
            engine = "sapi5"
        extra = data.get("extra")
        return cls(
            engine=engine,
            voice=str(data.get("voice", "")),
            rate=_clamp_int(data.get("rate", 200), 200, 50, 800),
            volume=_as_float(data.get("volume", 1.0), 1.0, 0.0, 1.0),
            speed=_as_float(data.get("speed", 1.0), 1.0, 0.25, 4.0),
            extra=dict(extra) if isinstance(extra, dict) else {},
        )


@dataclass(slots=True)
class DiscoveryProfile:
    """Which files in the project folder are converted (§discovery)."""

    extensions: list[str] = field(default_factory=lambda: list(_DEFAULT_EXTENSIONS))
    recursive: bool = True
    include_glob: str = ""  # ;/,-separated globs; empty = include all
    exclude_glob: str = ""  # ;/,-separated globs; wins over include
    max_file_bytes: int = 0  # 0 = no size cap

    def to_dict(self) -> dict[str, Any]:
        return {
            "extensions": list(self.extensions),
            "recursive": self.recursive,
            "include_glob": self.include_glob,
            "exclude_glob": self.exclude_glob,
            "max_file_bytes": self.max_file_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiscoveryProfile:
        return cls(
            extensions=_str_list(data.get("extensions"), _DEFAULT_EXTENSIONS),
            recursive=bool(data.get("recursive", True)),
            include_glob=str(data.get("include_glob", "")).strip(),
            exclude_glob=str(data.get("exclude_glob", "")).strip(),
            max_file_bytes=_clamp_int(data.get("max_file_bytes", 0), 0, 0, 1 << 40),
        )


@dataclass(slots=True)
class OutputProfile:
    """How the audio is written: format, encode quality, naming, and resume."""

    format: str = "wav"  # wav | mp3 | m4a | m4b | opus | flac | ogg
    skip_existing: bool = False  # legacy alias for on_existing="skip"
    on_existing: str = "overwrite"  # skip | overwrite | rename
    mp3_vbr_quality: int = 4  # libmp3lame -q:a, 0 (best) .. 9 (smallest)
    wav_sample_rate: int | None = None  # uniform WAV rate; None = leave as synthesized
    wav_channels: int | None = None  # uniform WAV channels; None = leave as synthesized
    flatten: bool = False  # collapse the source tree into one output folder
    filename_template: str = ""  # rename stems, e.g. "{index:03d} - {stem}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "skip_existing": self.skip_existing,
            "on_existing": self.on_existing,
            "mp3_vbr_quality": self.mp3_vbr_quality,
            "wav_sample_rate": self.wav_sample_rate,
            "wav_channels": self.wav_channels,
            "flatten": self.flatten,
            "filename_template": self.filename_template,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutputProfile:
        fmt = str(data.get("format", "wav")).strip().lower()
        if fmt not in _VALID_FORMATS:
            fmt = "wav"
        existing = str(data.get("on_existing", "overwrite")).strip().lower()
        if existing not in _VALID_EXISTING:
            existing = "overwrite"
        return cls(
            format=fmt,
            skip_existing=bool(data.get("skip_existing", False)),
            on_existing=existing,
            mp3_vbr_quality=_clamp_int(data.get("mp3_vbr_quality", 4), 4, 0, 9),
            wav_sample_rate=_opt_int(data.get("wav_sample_rate"), 8000, 192000),
            wav_channels=_opt_int(data.get("wav_channels"), 1, 2),
            flatten=bool(data.get("flatten", False)),
            filename_template=str(data.get("filename_template", "")).strip(),
        )


@dataclass(slots=True)
class MetadataProfile:
    """Audiobook / file tags stamped on compressed outputs (none for WAV)."""

    album: str = ""
    author: str = ""  # ffmpeg "artist" (the writing/narrating credit)
    album_artist: str = ""
    genre: str = ""
    year: str = ""
    comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "album": self.album,
            "author": self.author,
            "album_artist": self.album_artist,
            "genre": self.genre,
            "year": self.year,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetadataProfile:
        return cls(
            album=str(data.get("album", "")),
            author=str(data.get("author", "")),
            album_artist=str(data.get("album_artist", "")),
            genre=str(data.get("genre", "")),
            year=str(data.get("year", "")),
            comment=str(data.get("comment", "")),
        )

    def to_audio_metadata(self) -> Any:
        """Build a :class:`quill.core.speech.ffmpeg.AudioMetadata` (lazy import)."""
        from quill.core.speech.ffmpeg import AudioMetadata

        return AudioMetadata(
            artist=self.author,
            album=self.album,
            album_artist=self.album_artist or self.author,
            genre=self.genre,
            year=self.year,
            comment=self.comment,
        )


@dataclass(slots=True)
class ExecutionProfile:
    """How the batch runs: error policy, concurrency, and run report."""

    stop_on_error: bool = False
    retry_count: int = 0  # extra attempts per file on hard failure
    max_workers: int = 1  # parallel files (clamped to 1 for SAPI 5 / Kokoro)
    write_manifest: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "stop_on_error": self.stop_on_error,
            "retry_count": self.retry_count,
            "max_workers": self.max_workers,
            "write_manifest": self.write_manifest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionProfile:
        return cls(
            stop_on_error=bool(data.get("stop_on_error", False)),
            retry_count=_clamp_int(data.get("retry_count", 0), 0, 0, 10),
            max_workers=_clamp_int(data.get("max_workers", 1), 1, 1, 16),
            write_manifest=bool(data.get("write_manifest", False)),
        )


@dataclass(slots=True)
class ChapterProfile:
    """Chapterization options (§4.8.8), mirrored from the app settings."""

    mode: str = "none"  # none | single | separate
    sound_enabled: bool = False
    sound_id: str = ""  # sound-pack id; "" = bundled placeholder chime
    sound_volume: int = 100  # 0-100
    article_gap_ms: int = 1200  # 0-10000
    sentence_gap_ms: int = 0  # 0-10000; silence between sentences within a section (opt-in)
    tail_padding_ms: int = 300  # 0-10000; trailing silence per section (anti-clipping default)
    intro_section_title: str = "Introduction"
    # Fold empty headings into the next article before synthesis (ACB-style).
    combine_headings: bool = False
    # Normalize each output to ACX audiobook loudness (two-pass loudnorm).
    normalize_loudness: bool = False
    # Ordered voice ids (of the chosen engine) cycled one per article/heading;
    # empty or a single voice means the single `synthesizer.voice` is used.
    round_robin_voices: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "sound_enabled": self.sound_enabled,
            "sound_id": self.sound_id,
            "sound_volume": self.sound_volume,
            "article_gap_ms": self.article_gap_ms,
            "sentence_gap_ms": self.sentence_gap_ms,
            "tail_padding_ms": self.tail_padding_ms,
            "intro_section_title": self.intro_section_title,
            "combine_headings": self.combine_headings,
            "normalize_loudness": self.normalize_loudness,
            "round_robin_voices": list(self.round_robin_voices),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChapterProfile:
        mode = str(data.get("mode", "none")).strip().lower()
        if mode not in _VALID_CHAPTER_MODES:
            mode = "none"
        title = str(data.get("intro_section_title", "Introduction")).strip() or "Introduction"
        raw_voices = data.get("round_robin_voices", [])
        voices: tuple[str, ...] = ()
        if isinstance(raw_voices, list):
            seen: list[str] = []
            for item in raw_voices:
                name = str(item).strip()
                if name and name not in seen:
                    seen.append(name)
            voices = tuple(seen)
        return cls(
            mode=mode,
            sound_enabled=bool(data.get("sound_enabled", False)),
            sound_id=str(data.get("sound_id", "")).strip(),
            sound_volume=_clamp_int(data.get("sound_volume", 100), 100, 0, 100),
            article_gap_ms=_clamp_int(data.get("article_gap_ms", 1200), 1200, 0, 10000),
            sentence_gap_ms=_clamp_int(data.get("sentence_gap_ms", 0), 0, 0, 10000),
            tail_padding_ms=_clamp_int(data.get("tail_padding_ms", 300), 300, 0, 10000),
            intro_section_title=title,
            combine_headings=bool(data.get("combine_headings", False)),
            normalize_loudness=bool(data.get("normalize_loudness", False)),
            round_robin_voices=voices,
        )


@dataclass(slots=True)
class DictionaryRef:
    """A reference to one pronunciation dictionary the project uses (§4.7)."""

    id: str
    scope: str = "global"  # global | project
    format: str = "quill-json"
    path: str = ""  # for project scope: path relative to the project root; "" = by id

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "scope": self.scope, "format": self.format, "path": self.path}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DictionaryRef:
        scope = str(data.get("scope", "global")).strip().lower()
        if scope not in _VALID_SCOPES:
            scope = "global"
        fmt = str(data.get("format", "quill-json")).strip().lower()
        if fmt not in _VALID_DICT_FORMATS:
            fmt = "quill-json"
        return cls(
            id=str(data.get("id", "")).strip(),
            scope=scope,
            format=fmt,
            path=str(data.get("path", "")).strip(),
        )


@dataclass(slots=True)
class PronunciationProfile:
    """Which pronunciation dictionaries (and formats) are active for the project."""

    enabled: bool = True
    dictionaries: list[DictionaryRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "dictionaries": [d.to_dict() for d in self.dictionaries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PronunciationProfile:
        raw = data.get("dictionaries")
        dicts = (
            [DictionaryRef.from_dict(d) for d in raw if isinstance(d, dict) and d.get("id")]
            if isinstance(raw, list)
            else []
        )
        return cls(enabled=bool(data.get("enabled", True)), dictionaries=dicts)


@dataclass(slots=True)
class TranslationTarget:
    """One translated-export target: a language and the voice that speaks it (§7)."""

    language: str  # ISO 639-1 base code, e.g. "es"
    engine: str  # espeak | sapi5 | openai | gemini | elevenlabs
    voice: str  # engine-native voice id

    def to_dict(self) -> dict[str, Any]:
        return {"language": self.language, "engine": self.engine, "voice": self.voice}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranslationTarget:
        return cls(
            language=str(data.get("language", "")).strip(),
            engine=str(data.get("engine", "")).strip(),
            voice=str(data.get("voice", "")).strip(),
        )


@dataclass(slots=True)
class TranslationProfile:
    """Remembered translated-export targets and backend for the project (§7)."""

    provider: str = "ai_assistant"  # ai_assistant | libretranslate
    libretranslate_url: str = "http://localhost:5000"
    targets: list[TranslationTarget] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "libretranslate_url": self.libretranslate_url,
            "targets": [t.to_dict() for t in self.targets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranslationProfile:
        provider = str(data.get("provider", "ai_assistant")).strip().lower()
        if provider not in _VALID_TRANSLATION_PROVIDERS:
            provider = "ai_assistant"
        raw = data.get("targets")
        targets = (
            [
                TranslationTarget.from_dict(t)
                for t in raw
                if isinstance(t, dict) and str(t.get("language", "")).strip()
            ]
            if isinstance(raw, list)
            else []
        )
        url = str(data.get("libretranslate_url", "http://localhost:5000")).strip()
        return cls(
            provider=provider,
            libretranslate_url=url or "http://localhost:5000",
            targets=targets,
        )


@dataclass(slots=True)
class SpeechProjectProfile:
    """The complete remembered speech profile for one project folder (§4.10)."""

    version: int = PROFILE_VERSION
    synthesizer: SynthesizerProfile = field(default_factory=SynthesizerProfile)
    discovery: DiscoveryProfile = field(default_factory=DiscoveryProfile)
    output: OutputProfile = field(default_factory=OutputProfile)
    chapters: ChapterProfile = field(default_factory=ChapterProfile)
    # Serialized TextNormalizationOptions (empty = recommended defaults).
    normalization: dict[str, Any] = field(default_factory=dict)
    pronunciation: PronunciationProfile = field(default_factory=PronunciationProfile)
    metadata: MetadataProfile = field(default_factory=MetadataProfile)
    execution: ExecutionProfile = field(default_factory=ExecutionProfile)
    translation: TranslationProfile = field(default_factory=TranslationProfile)
    # Phase 4-6 fields the wizard collects on the output / audio source
    # pages. Persisted at the top level so a per-folder auto-remember
    # covers them and "Skip to summary" stays a 3-keystroke fast-path on the
    # second run.
    book_credits: bool = False
    library_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "synthesizer": self.synthesizer.to_dict(),
            "discovery": self.discovery.to_dict(),
            "output": self.output.to_dict(),
            "chapters": self.chapters.to_dict(),
            "normalization": dict(self.normalization),
            "pronunciation": self.pronunciation.to_dict(),
            "metadata": self.metadata.to_dict(),
            "execution": self.execution.to_dict(),
            "translation": self.translation.to_dict(),
            "book_credits": bool(self.book_credits),
            "library_mode": bool(self.library_mode),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpeechProjectProfile:
        if not isinstance(data, dict):
            return cls()
        norm = data.get("normalization")
        return cls(
            version=_clamp_int(data.get("version", PROFILE_VERSION), PROFILE_VERSION, 1, 1000),
            synthesizer=SynthesizerProfile.from_dict(_sub(data, "synthesizer")),
            discovery=DiscoveryProfile.from_dict(_sub(data, "discovery")),
            output=OutputProfile.from_dict(_sub(data, "output")),
            chapters=ChapterProfile.from_dict(_sub(data, "chapters")),
            normalization=dict(norm) if isinstance(norm, dict) else {},
            pronunciation=PronunciationProfile.from_dict(_sub(data, "pronunciation")),
            metadata=MetadataProfile.from_dict(_sub(data, "metadata")),
            execution=ExecutionProfile.from_dict(_sub(data, "execution")),
            translation=TranslationProfile.from_dict(_sub(data, "translation")),
            # v1 -> v2 tolerance: missing top-level booleans default to False.
            book_credits=bool(data.get("book_credits", False)),
            library_mode=bool(data.get("library_mode", False)),
        )


def _sub(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def profile_path(project_dir: Path) -> Path:
    """Path to the project's speech profile file (may not exist yet)."""
    return project_dir / PROJECT_DIRNAME / PROFILE_FILENAME


def load_profile(project_dir: Path) -> SpeechProjectProfile | None:
    """Load the project's speech profile, or ``None`` when the folder has none."""
    path = profile_path(project_dir)
    if not path.is_file():
        return None
    raw = read_json(path, default=None)
    if not isinstance(raw, dict):
        return None
    return SpeechProjectProfile.from_dict(raw)


def save_profile(profile: SpeechProjectProfile, project_dir: Path) -> Path:
    """Write *profile* to ``<project_dir>/.quill/speech-project.json`` atomically."""
    path = profile_path(project_dir)
    write_json_atomic(path, profile.to_dict())
    return path


# --- Profile -> runtime options (drives the batch pipeline from a project) --- #


def to_chapter_options(profile: SpeechProjectProfile) -> Any:
    """Build a :class:`ChapterAssembleOptions` from a profile (lazy import)."""
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions

    ch = profile.chapters
    return ChapterAssembleOptions(
        article_gap_ms=ch.article_gap_ms,
        sound_enabled=ch.sound_enabled,
        sound_path=None,  # sound_id resolution to a real file is a UI/sound-pack concern
        sound_volume=ch.sound_volume,
        intro_section_title=ch.intro_section_title,
        output_format=profile.output.format,
        sentence_gap_ms=ch.sentence_gap_ms,
        tail_padding_ms=ch.tail_padding_ms,
    )


def to_batch_options(
    profile: SpeechProjectProfile,
    source_folder: Path,
    output_folder: Path,
    *,
    pronunciation_dictionaries: list[Any] | None = None,
) -> Any:
    """Build a :class:`BatchExportOptions` from a profile and source/output folders.

    Engine-specific fields are filled from the synthesizer profile (with ``extra``
    supplying per-engine keys like ``piper_model`` or ``dectalk_executable``). The
    resolved active pronunciation dictionaries are passed through unchanged.
    """
    from quill.core.speech.batch_export import BatchExportOptions

    s = profile.synthesizer
    extra = s.extra
    out = profile.output
    disc = profile.discovery
    exec_ = profile.execution
    norm = profile.normalization
    opts = BatchExportOptions(
        source_folder=source_folder,
        output_folder=output_folder,
        engine=s.engine,
        extensions=list(disc.extensions),
        recursive=disc.recursive,
        include_glob=disc.include_glob,
        exclude_glob=disc.exclude_glob,
        max_file_bytes=disc.max_file_bytes,
        output_format=out.format,  # type: ignore[arg-type]
        mp3_vbr_quality=str(out.mp3_vbr_quality),
        wav_sample_rate=out.wav_sample_rate,
        wav_channels=out.wav_channels,
        on_existing=out.on_existing,  # type: ignore[arg-type]
        skip_existing=out.skip_existing,
        flatten=out.flatten,
        filename_template=out.filename_template,
        metadata=profile.metadata.to_audio_metadata(),
        stop_on_error=exec_.stop_on_error,
        retry_count=exec_.retry_count,
        max_workers=exec_.max_workers,
        write_manifest=exec_.write_manifest,
        pronunciation_dictionaries=pronunciation_dictionaries or [],
    )
    # Carry serialized TextNormalizationOptions through when the project sets any.
    if norm:
        from quill.core.speech.text_normalize import TextNormalizationOptions

        opts.normalization = TextNormalizationOptions.from_dict(norm)
    # Engine-specific wiring from the flat profile + extra bag.
    if s.engine == "sapi5":
        opts.sapi5_voice = s.voice
        opts.sapi5_rate = s.rate
        opts.sapi5_volume = s.volume
    elif s.engine == "dectalk":
        opts.dectalk_voice = s.voice or "paul"
        opts.dectalk_rate = s.rate
        if extra.get("dectalk_executable"):
            opts.dectalk_executable = Path(str(extra["dectalk_executable"]))
        if extra.get("dectalk_dictionary"):
            opts.dectalk_dictionary = Path(str(extra["dectalk_dictionary"]))
    elif s.engine == "piper":
        if extra.get("piper_executable"):
            opts.piper_executable = Path(str(extra["piper_executable"]))
        if extra.get("piper_model"):
            opts.piper_model = Path(str(extra["piper_model"]))
        opts.piper_length_scale = _extra_float(extra.get("piper_length_scale"))
        opts.piper_noise_scale = _extra_float(extra.get("piper_noise_scale"))
        opts.piper_noise_w = _extra_float(extra.get("piper_noise_w"))
    elif s.engine == "kokoro":
        opts.kokoro_voice = s.voice or "af_heart"
        opts.kokoro_speed = s.speed
    elif s.engine == "espeak":
        opts.espeak_voice = s.voice or "en"
        opts.espeak_rate = s.rate
        if extra.get("espeak_executable"):
            opts.espeak_executable = Path(str(extra["espeak_executable"]))
        opts.espeak_pitch = _extra_int(extra.get("espeak_pitch"))
        opts.espeak_word_gap_ms = _extra_int(extra.get("espeak_word_gap_ms"))
    return opts


def _extra_float(value: Any) -> float | None:
    """Parse an optional float from the synthesizer ``extra`` bag (None when absent)."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extra_int(value: Any) -> int | None:
    """Parse an optional int from the synthesizer ``extra`` bag (None when absent)."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
