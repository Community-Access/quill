"""Optional, downloadable components — a single status model (wx-free).

QUILL ships a small base installer and fetches several large or redistributable
components on demand (PRD 10.2.x): the offline speech engine, neural voices,
classic voices, optional tools, and non-English spell-check dictionaries. Each had
its own scattered download entry point; this module gives a *single* status model
so a "Download Optional Components" dialog (Help menu) can show, in one place, what
is present versus what is available — the touch point the footprint plan asked for
(§10.2.5).

Pure logic, no ``wx``: it only *reports* status by asking each component's existing
detector. The download actions themselves stay in the UI (they need progress and
consent), keyed by :attr:`OptionalComponent.component_id`.
"""

from __future__ import annotations

from dataclasses import dataclass

# Categories (also the dialog's grouping labels).
SPEECH_ENGINE = "Speech engine"
VOICES = "Voices"
DICTIONARY = "Spell-check dictionary"
TOOL = "Tool"


@dataclass(frozen=True, slots=True)
class OptionalComponent:
    """One optional component and whether it is installed right now."""

    component_id: str  # stable key the UI maps to a download action
    name: str
    description: str
    category: str
    installed: bool
    size_hint: str  # human "~8 MB" etc.; "" when unknown
    # A note shown when a component is present for a reason other than a download
    # (e.g. an upgrader's bundled copy, or a system-provided tool).
    note: str = ""

    @property
    def status_label(self) -> str:
        return "Installed" if self.installed else "Available to download"


def _safe(predicate) -> bool:  # type: ignore[no-untyped-def]
    """Run a detector, treating any failure as 'not installed'."""
    try:
        return bool(predicate())
    except Exception:  # noqa: BLE001 - a broken detector must never crash the list
        return False


def _whisper_installed() -> bool:
    from quill.core.speech.providers.whispercpp import resolve_whisper_executable

    return resolve_whisper_executable() is not None


def _kokoro_installed() -> bool:
    from quill.core.read_aloud import kokoro_onnx_ready
    from quill.core.speech.engine_install import is_kokoro_onnx_available

    return kokoro_onnx_ready() and is_kokoro_onnx_available()


def _espeak_installed() -> bool:
    from quill.core.read_aloud import discover_espeak_executable

    return discover_espeak_executable() is not None


def _dectalk_installed() -> bool:
    from quill.core.read_aloud import discover_dectalk_executable

    return discover_dectalk_executable() is not None


def _ffmpeg_installed() -> bool:
    from quill.core.speech.ffmpeg import ffmpeg_available

    return ffmpeg_available()


def gather_optional_components() -> list[OptionalComponent]:
    """Return every optional component with its current installed status.

    Ordered engine -> voices -> tool -> dictionaries, then alphabetically within
    the dictionary group, so the dialog reads predictably.
    """
    out: list[OptionalComponent] = [
        OptionalComponent(
            "whispercpp",
            "Offline speech engine (whisper.cpp)",
            "Powers private, on-device dictation and transcription. SAPI 5 dictation "
            "works without it; this adds the offline Whisper engine.",
            SPEECH_ENGINE,
            _safe(_whisper_installed),
            "~8 MB",
        ),
        OptionalComponent(
            "kokoro",
            "Kokoro neural voices",
            "High-quality offline neural Read Aloud voices.",
            VOICES,
            _safe(_kokoro_installed),
            "~120 MB",
        ),
        OptionalComponent(
            "espeak",
            "eSpeak NG voices",
            "Compact offline Read Aloud engine covering many languages.",
            VOICES,
            _safe(_espeak_installed),
            "~40 MB",
        ),
        OptionalComponent(
            "dectalk",
            "DECtalk voices",
            "The classic DECtalk Read Aloud voices.",
            VOICES,
            _safe(_dectalk_installed),
            "~2 MB",
        ),
        OptionalComponent(
            "ffmpeg",
            "FFmpeg (audio export helper)",
            "Lets QUILL export speech audio as MP3, M4A/M4B, OGG, Opus, or FLAC. "
            "WAV export works without it.",
            TOOL,
            _safe(_ffmpeg_installed),
            "",
            note="Provided by FFmpeg; QUILL helps you fetch the official build.",
        ),
    ]
    out.extend(_dictionary_components())
    return out


def _dictionary_components() -> list[OptionalComponent]:
    """One entry per downloadable spell-check language, plus the installed ones."""
    try:
        from quill.core import spellcheck
    except Exception:  # noqa: BLE001
        return []
    installed = set(_safe_list(spellcheck.installed_languages))
    available = set(_safe_list(spellcheck.installable_languages))
    # English ships inside pyenchant and is never a separate download; omit it.
    installed.discard("en_US")
    langs = sorted(installed | available)
    rows: list[OptionalComponent] = []
    for lang in langs:
        try:
            display = spellcheck.language_display_name(lang)
        except Exception:  # noqa: BLE001
            display = lang
        rows.append(
            OptionalComponent(
                f"spell-{lang}",
                f"Spell-check dictionary: {display}",
                "A Hunspell dictionary so the spell checker can validate this language.",
                DICTIONARY,
                lang in installed,
                "",
            )
        )
    return rows


def _safe_list(getter) -> list:  # type: ignore[no-untyped-def]
    try:
        return list(getter())
    except Exception:  # noqa: BLE001
        return []
