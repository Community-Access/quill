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

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

_LOG = logging.getLogger(__name__)

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
    # Display priority: lower sorts higher in the dialog (importance order).
    # Left at the default for dictionaries, which are grouped and sorted by name.
    priority: int = 500
    # None means "same as installed" for every ordinary single-download
    # component. The Dictation row is the one exception: the engine binary
    # alone isn't usable without a downloaded model, so it passes its own
    # two-tier readiness here. Read via effective_ready, never this field
    # directly, so every other call site keeps its current behavior for free.
    ready: bool | None = None

    @property
    def status_label(self) -> str:
        return "Installed" if self.installed else "Available to download"

    @property
    def effective_ready(self) -> bool:
        """Whether Download/Test should treat this component as fully usable.

        Distinct from ``installed`` (which drives status_label/Manage/Remove):
        for most components the two agree, but the Dictation row is installed
        as soon as an engine binary is present even with no model downloaded
        yet -- not actually usable, so Download/Test must not treat it as done.
        """
        return self.installed if self.ready is None else self.ready


# Read Aloud engine id a voice component provides, so removing it can reset the
# active engine to the always-present SAPI 5 floor (the UI does the reset +
# menu refresh; see the design's "remove closes the loop" decision).
_ENGINE_BY_COMPONENT: dict[str, str] = {
    "kokoro": "kokoro",
    "piper": "piper",
    "espeak": "espeak",
    "dectalk": "dectalk",
}


def read_aloud_engine_for_component(component_id: str) -> str | None:
    """The ``settings.read_aloud_engine`` value this component provides, or None."""
    return _ENGINE_BY_COMPONENT.get(component_id)


def available_live_voices(engine: str) -> list:
    """Voices for *engine* that can be heard live right now (wx-free).

    The hub's Test picker offers only these, so every entry actually
    synthesizes -- undownloaded Piper/Kokoro catalog voices are filtered out,
    while the built-in eSpeak/DECtalk/SAPI voices are always available once the
    engine itself is present. A broken lister degrades to an empty list rather
    than blocking Test.
    """
    from quill.core import read_aloud as ra

    safe = (engine or "").strip().lower()
    try:
        if safe == "piper":
            return [v for v in ra.list_piper_catalog_voices() if v.installed]
        if safe == "kokoro":
            return [v for v in ra.list_kokoro_voices() if v.installed]
        if safe == "espeak":
            return list(ra.list_espeak_voices())
        if safe == "dectalk":
            return list(ra.list_dectalk_voices())
        if safe == "sapi5":
            return list(ra.list_voices())
    except Exception:  # noqa: BLE001 - a broken lister must never block Test
        return []
    return []


def voice_pick_label(voice: object) -> str:
    """Label for a voice in the Test picker: name plus accent/style note."""
    accent = str(getattr(voice, "accent", "") or "")
    description = str(getattr(voice, "description", "") or "")
    name = str(getattr(voice, "name", "") or "")
    extra = ", ".join(part for part in (accent, description) if part)
    return f"{name} ({extra})" if extra else name


# Offline STT engines whose downloadable *models* live in Manage Speech Models.
_STT_ENGINES = frozenset({"whispercpp", "vosk"})


def manage_target(component_id: str) -> str | None:
    """Where the hub should route "Manage…" for this component, or None.

    Models and voices are multi-item spaces with their own tested dialogs; the
    hub links to them rather than absorbing them (meet-people-where-they-are).
    Returns "models" for offline STT engines (Manage Speech Models), "voices"
    for Read Aloud voice engines (Manage Voices), else None (no Manage action).
    """
    if component_id in _STT_ENGINES:
        return "models"
    if read_aloud_engine_for_component(component_id) is not None:
        return "voices"
    return None


def _app_data_root() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir()


def _candidate_removable_path(component_id: str) -> Path | None:
    """The on-disk copy Remove would delete for *component_id*, before safety
    checks. None when QUILL has no managed location for it.

    For a spell dictionary this is the ``<lang>.dic`` file; :func:`remove_component`
    deletes its ``.aff`` sibling alongside it.
    """
    try:
        if component_id == "kokoro":
            return _app_data_root() / "kokoro-models"
        if component_id == "whispercpp":
            return _app_data_root() / "speech-engine"
        if component_id == "dectalk":
            return _app_data_root() / "speech" / "dectalk"
        if component_id == "piper":
            from quill.core.speech.piper_install import managed_piper_dir

            return managed_piper_dir()
        if component_id == "espeak":
            from quill.core.speech.espeak_install import managed_espeak_dir

            return managed_espeak_dir()
        if component_id == "node":
            from quill.core.node_install import managed_node_dir

            return managed_node_dir()
        if component_id == "ffmpeg":
            from quill.core.speech.ffmpeg_install import managed_ffmpeg_dir

            return managed_ffmpeg_dir()
        if component_id == "braille":
            from quill.core.braille_pack import managed_braille_dir

            return managed_braille_dir()
        if component_id == "pandoc":
            from quill.core.pandoc_install import managed_pandoc_dir

            return managed_pandoc_dir()
        if component_id == "vosk":
            from quill.core.speech.engine_install import vosk_pack_dir

            return vosk_pack_dir()
        if component_id == "audio_extras":
            # Only mpv has a managed directory to remove; mutagen (the mp3
            # half) is a pip-installed package with no separate removal path,
            # matching its pre-merge behavior.
            from quill.core.speech.engine_install import engine_packs_dir

            return engine_packs_dir() / "mpv"
        if component_id == "mathcat":
            from quill.core.math.mathcat_engine import pack_dir

            return pack_dir()
        if component_id == "pdf_ocr":
            from quill.core.pdf_ocr_install import pdf_ocr_pack_dir

            return pdf_ocr_pack_dir()
        if component_id.startswith("spell-"):
            from quill.core.spellcheck import managed_hunspell_dir

            lang = component_id[len("spell-") :]
            return managed_hunspell_dir() / f"{lang}.dic"
    except Exception:  # noqa: BLE001 - a missing helper just means "not removable"
        return None
    return None


def removable_path(component_id: str) -> Path | None:
    """Return the QUILL-downloaded copy Remove may delete, or None.

    Returns a path only when it exists **and** lives under the active data dir
    (``app_data_dir()``, which is the portable data folder in portable mode). A
    system tool on PATH, an upgrader's ``{app}`` copy, or a component with no
    managed-dir helper returns None, so no Remove is offered for those.
    """
    path = _candidate_removable_path(component_id)
    if path is None:
        return None
    try:
        root = _app_data_root().resolve()
        resolved = path.resolve()
    except Exception:  # noqa: BLE001
        return None
    if not path.exists():
        return None
    # Safety: only ever delete inside the active (portable-aware) data dir.
    if resolved != root and root not in resolved.parents:
        return None
    return path


def remove_component(component_id: str) -> bool:
    """Delete QUILL's downloaded copy of *component_id* and clear caches.

    Returns True when something was removed, False when there was nothing QUILL
    can safely remove (see :func:`removable_path`). Never raises.
    """
    import shutil

    path = removable_path(component_id)
    if path is None:
        return False
    # A spell dictionary is a .dic/.aff pair in a shared dir: remove both, not
    # the whole hunspell folder (which holds other languages).
    if component_id.startswith("spell-"):
        removed_any = False
        for sibling in (path, path.with_suffix(".aff")):
            try:
                if sibling.is_file():
                    sibling.unlink()
                    removed_any = True
            except OSError:
                continue
        return removed_any
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError:
        return False
    if component_id == "kokoro":
        try:
            from quill.core.read_aloud import clear_kokoro_cache

            clear_kokoro_cache()
        except Exception:  # noqa: BLE001 - cache clear is best-effort
            pass
    return True


# The phrase a voice speaks on Test in the Download Optional Components hub.
# It lives in scripts/phrase.txt so it can be tuned without a code change; the
# built-in default is the same text, used on shipped installs where the file is
# not alongside the app.
_DEFAULT_PREVIEW_PHRASE = (
    "QUILL is where your words come to life, turning quiet thoughts into finished "
    "pages with a little sprinkle of everyday magic."
)


def voice_preview_phrase() -> str:
    """Return the Test/preview phrase, read from ``scripts/phrase.txt`` when
    present (the app root or the source tree), else the built-in default."""
    import os

    candidates: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        candidates.append(Path(app_root) / "scripts" / "phrase.txt")
    candidates.append(Path(__file__).resolve().parents[2] / "scripts" / "phrase.txt")
    for path in candidates:
        try:
            if path.is_file():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except Exception:  # noqa: BLE001 - any read problem falls back to the default
            continue
    return _DEFAULT_PREVIEW_PHRASE


# A clean, well-recognised phrase QUILL speaks with SAPI 5 and then feeds back
# through an offline STT engine to prove transcription works (the R2 loop).
_STT_TEST_PHRASE = "The quick brown fox jumps over the lazy dog."


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """Outcome of a component self-test: an ok flag plus human-readable text."""

    ok: bool
    summary: str
    detail: str = ""
    # When set, the failure is an expected "you need to get one more piece" state,
    # not a bug: "models" -> Manage Speech Models, "voices" -> Manage Voices. The
    # dialog routes there instead of offering a bug report.
    remedy: str = ""


@dataclass(frozen=True, slots=True)
class DownloadFailure:
    """Captured detail of a failed download/install, for the rich error dialog
    and a one-click bug report."""

    component_id: str
    message: str
    detail: str = ""
    target: str = ""

    def as_report_text(self) -> str:
        lines = [f"Component: {self.component_id}", f"Error: {self.message}"]
        if self.target:
            lines.append(f"Target: {self.target}")
        if self.detail:
            lines.extend(["", "Detail:", self.detail])
        return "\n".join(lines)


def _fuzzy_match(expected: str, heard: str, *, threshold: float = 0.4) -> bool:
    """True when *heard* covers enough of *expected*'s words (STT is imperfect)."""
    import re

    def toks(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9']+", text.lower()))

    want = toks(expected)
    if not want:
        return False
    return len(want & toks(heard)) / len(want) >= threshold


def verify_component(component_id: str) -> VerifyResult:
    """Self-test *component_id* and return a human-readable result.

    Voice engines are handled by the dialog (it plays a spoken sample via the
    existing voice preview); here they just confirm readiness. STT engines run
    the SAPI->transcribe loop; tools report their version/response; the rest do a
    presence/load check. Never raises -- any failure becomes ``ok=False``.
    """
    try:
        if component_id in ("whispercpp", "fasterwhisper", "vosk"):
            result = _verify_stt(component_id)
        elif component_id in ("pandoc", "ffmpeg", "node"):
            result = _verify_tool(component_id)
        elif read_aloud_engine_for_component(component_id) is not None:
            result = VerifyResult(True, "Installed — press Test to hear a sample of this voice.")
        else:
            result = _verify_presence(component_id)
    except Exception as exc:  # noqa: BLE001 - a verify must never crash the dialog
        # Log so the failure is captured in diagnostics -- the Test result is
        # otherwise shown only on-screen and never reaches the log bundle.
        _LOG.warning("verify_component(%s) could not run: %s", component_id, exc)
        return VerifyResult(False, "The self-test could not run.", str(exc))
    if result.ok:
        _LOG.info("verify_component(%s): OK -- %s", component_id, result.summary)
    else:
        _LOG.warning(
            "verify_component(%s): FAILED -- %s%s",
            component_id,
            result.summary,
            f" | {result.detail}" if result.detail else "",
        )
    return result


def _verify_stt(component_id: str) -> VerifyResult:
    import os
    import tempfile

    from quill.core.read_aloud import synthesize_to_file_with_sapi5
    from quill.core.speech.transcribe import provider_has_installed_model, transcribe_audio_file

    # Gate on the *selected* engine, not any engine, so testing Faster Whisper
    # while only whisper.cpp has a model correctly routes to "download a model".
    if not _safe(lambda: provider_has_installed_model(component_id)):
        return VerifyResult(
            False,
            "The engine is installed, but no speech model has been downloaded yet.",
            remedy="models",
        )
    fd, wav_path = tempfile.mkstemp(prefix="quill_stt_test_", suffix=".wav")
    os.close(fd)  # mkstemp's fd must be closed or SAPI's own Open() of the same path fails
    wav = Path(wav_path)
    try:
        synthesize_to_file_with_sapi5(_STT_TEST_PHRASE, wav)
        result = transcribe_audio_file(wav, provider_id=component_id)
        heard = (getattr(result, "full_text", "") or "").strip()
    except Exception as exc:  # noqa: BLE001
        return VerifyResult(False, "The speech engine could not transcribe a test clip.", str(exc))
    finally:
        try:
            wav.unlink(missing_ok=True)
        except OSError:
            # Best-effort cleanup of the temp WAV; a leftover temp file is
            # harmless and must never mask the transcription result above.
            pass
    if _fuzzy_match(_STT_TEST_PHRASE, heard):
        return VerifyResult(True, f"It works — the engine heard: “{heard}”")
    return VerifyResult(
        False,
        f"The engine ran but the result looked off: “{heard}”",
        "This can happen transcribing the system voice; try dictating a real phrase.",
    )


def _verify_tool(component_id: str) -> VerifyResult:
    if component_id == "node":
        ok = _safe(_node_installed)
        return VerifyResult(
            ok,
            "Node.js is installed and on QUILL's path." if ok else "Node.js was not found.",
        )
    if component_id == "ffmpeg":
        from quill.core.speech.ffmpeg import ffmpeg_available

        ok = _safe(ffmpeg_available)
        return VerifyResult(
            ok, "FFmpeg is installed and responding." if ok else "FFmpeg was not found."
        )
    from quill.core.external_tools import get_external_tool_status

    status = get_external_tool_status("pandoc")
    if getattr(status, "installed", False):
        version = getattr(status, "version", "") or ""
        suffix = f" (version {version})" if version else ""
        return VerifyResult(True, f"Pandoc is installed and responding{suffix}.")
    return VerifyResult(False, "Pandoc was not found.")


def _verify_presence(component_id: str) -> VerifyResult:
    if component_id.startswith("spell-"):
        lang = component_id[len("spell-") :]
        try:
            from quill.core import spellcheck

            ok = lang in set(_safe_list(spellcheck.installed_languages))
        except Exception:  # noqa: BLE001
            ok = False
        return VerifyResult(
            ok,
            f"The {lang} dictionary is installed."
            if ok
            else f"The {lang} dictionary was not detected.",
        )
    detectors = {
        "braille": _braille_pack_installed,
        "mathcat": _mathcat_installed,
        "audio_extras": _audio_extras_installed,
    }
    detector = detectors.get(component_id)
    if detector is None:
        return VerifyResult(True, "Installed.")
    ok = _safe(detector)
    if ok and component_id == "braille":
        # Surface the embedded LibLouis version on Test, mirroring Pandoc's tool
        # self-test. braille_pack_version() reads louis.version() (the liblouis
        # library string), falling back to "unknown" when the binding can't
        # report it -- so a present-but-unversioned pack still reads cleanly.
        from quill.core.braille_pack import braille_pack_version

        version = _safe_str(braille_pack_version)
        if version and version != "unknown":
            return VerifyResult(True, f"Installed and detected — LibLouis {version}.")
        return VerifyResult(True, "Installed and detected.")
    return VerifyResult(
        ok, "Installed and detected." if ok else "Installed files were not detected."
    )


def _safe(predicate) -> bool:  # type: ignore[no-untyped-def]
    """Run a detector, treating any failure as 'not installed'."""
    try:
        return bool(predicate())
    except Exception:  # noqa: BLE001 - a broken detector must never crash the list
        return False


def _whisper_installed() -> bool:
    from quill.core.speech.providers.whispercpp import resolve_whisper_executable

    return resolve_whisper_executable() is not None


def _dictation_ready() -> bool:
    """True when some offline STT engine is installed AND has a downloaded
    model -- the Dictation row's real "ready to dictate" state.

    ``_whisper_installed`` (the row's ``installed`` detector) only checks for
    the whisper.cpp binary, so it goes True the moment the engine is fetched
    even with no model yet -- Download/Test must not treat that as "done"
    (the Test button offered no way to tell it wasn't actually usable).
    Checks all three guided-picker engines, not just whisper.cpp, so a user
    who set up Faster Whisper or Vosk instead still reads as ready.
    """
    from quill.core.speech import guided_setup
    from quill.core.speech.transcribe import provider_has_installed_model

    for opt in guided_setup.offline_speech_engine_options():
        if opt.installed and _safe(lambda pid=opt.engine_id: provider_has_installed_model(pid)):
            return True
    return False


def _vosk_installed() -> bool:
    from quill.core.speech.engine_install import is_vosk_available

    return is_vosk_available()


def _kokoro_installed() -> bool:
    from quill.core.read_aloud import kokoro_engine_ready

    return kokoro_engine_ready()


def _piper_installed() -> bool:
    from quill.core.read_aloud import discover_piper_executable

    return discover_piper_executable() is not None


def _node_installed() -> bool:
    from quill.core.node_install import is_node_available

    return is_node_available()


def _espeak_installed() -> bool:
    from quill.core.read_aloud import discover_espeak_executable

    return discover_espeak_executable() is not None


def _dectalk_installed() -> bool:
    from quill.core.read_aloud import discover_dectalk_executable

    return discover_dectalk_executable() is not None


def _ffmpeg_installed() -> bool:
    from quill.core.speech.ffmpeg import ffmpeg_available

    return ffmpeg_available()


def _braille_pack_installed() -> bool:
    from quill.core.braille_pack import is_braille_pack_installed

    return is_braille_pack_installed()


def _libmpv_installed() -> bool:
    from quill.core.speech.engine_install import engine_packs_dir

    pack = engine_packs_dir() / "mpv"
    return any((pack / name).is_file() for name in ("libmpv-2.dll", "mpv-2.dll", "libmpv.dll"))


def _pandoc_installed() -> bool:
    from quill.core.external_tools import get_external_tool_status

    return get_external_tool_status("pandoc").installed


def _mathcat_installed() -> bool:
    from quill.core.math import mathcat_engine

    return mathcat_engine.is_available()


def _mp3_installed() -> bool:
    from quill.core.speech.engine_install import is_mp3_available

    return is_mp3_available()


def _pdf_ocr_installed() -> bool:
    from quill.core.pdf_ocr_install import is_pdf_ocr_available

    return is_pdf_ocr_available()


def _audio_extras_installed() -> bool:
    """Both halves of the bundled audio-extras download: mpv playback and MP3
    chapter markers. Reports installed only once both are present, since the
    hub now offers them as a single download."""
    return _libmpv_installed() and _mp3_installed()


def gather_optional_components() -> list[OptionalComponent]:
    """Return every optional component with its current installed status.

    Sorted by ``priority`` (importance order: Pandoc and the braille pack first,
    then engines/voices/tools), with the spell-check dictionaries last, grouped
    and alphabetical, so the dialog reads predictably.
    """
    out: list[OptionalComponent] = [
        OptionalComponent(
            "pandoc",
            "Pandoc (document conversion)",
            "Imports and exports Word, ODT, EPUB, RTF, and many other formats. "
            "Plain-text and Markdown editing work without it. On Windows QUILL "
            "fetches the official build the first time a conversion needs it; "
            "on macOS install Pandoc yourself (for example via Homebrew) and "
            "QUILL finds it on the PATH.",
            TOOL,
            _safe(_pandoc_installed),
            "~45 MB",
            note="Provided by Pandoc (jgm/pandoc); QUILL fetches the official, pinned build.",
            priority=10,
        ),
        OptionalComponent(
            "pdf_ocr",
            "PDF and Office text extraction",
            "Reads text out of PDFs and Office documents (Word/PowerPoint/Excel) "
            "without Pandoc or LibreOffice installed -- MarkItDown for Office and "
            "PDF, pdfplumber and pypdf as the PDF text floor. Scanned/image-only "
            "PDFs still need OCR (File > Import > OCR) either way. Plain-text and "
            "Markdown editing, and any format Pandoc already handles, work without it.",
            TOOL,
            _safe(_pdf_ocr_installed),
            "~30 MB",
            note="MarkItDown (MIT, microsoft/markitdown), pdfplumber (MIT), and pypdf "
            "(BSD-3-Clause); fetched via pip from PyPI.",
            priority=15,
        ),
        OptionalComponent(
            "braille",
            "Braille pack (translation and BRF export)",
            "liblouis translation tables and BRF profiles that power the Translation "
            "submenu and BRF/embossing export. Reading with a braille display works "
            "without it (that is your screen reader); this adds QUILL's own "
            "translation and embossing.",
            TOOL,
            _safe(_braille_pack_installed),
            "~9 MB",
            note="QUILL braille pack (liblouis, LGPL-3.0/GPL-3.0); fetched from QUILL's "
            "pinned release.",
            priority=20,
        ),
        OptionalComponent(
            "whispercpp",
            "Dictation (offline speech)",
            "Private, on-device dictation and transcription. Opens a guided setup "
            "where you choose an engine (Whisper, Faster Whisper, or Vosk) and a "
            "model to match your computer, then test it. "
            + (
                "SAPI 5 dictation works without any of this."
                if sys.platform.startswith("win")
                else "This is the only dictation path on macOS (there is no SAPI 5)."
            ),
            SPEECH_ENGINE,
            _safe(_whisper_installed),
            "~8 MB",
            priority=30,
            ready=_safe(_dictation_ready),
        ),
        OptionalComponent(
            "kokoro",
            "Kokoro neural voices",
            "High-quality offline neural Read Aloud voices.",
            VOICES,
            _safe(_kokoro_installed),
            "~120 MB",
            priority=40,
        ),
        OptionalComponent(
            "piper",
            "Piper neural voices",
            "Fast, local, high-quality neural Read Aloud voices (dozens of English "
            "voices). A small engine download, then pick voices in Manage Voices.",
            VOICES,
            _safe(_piper_installed),
            "~22 MB",
            note="Piper (MIT, rhasspy/piper); downloaded on demand and SHA-256 verified.",
            priority=50,
        ),
        OptionalComponent(
            "espeak",
            "eSpeak NG voices",
            "Compact offline Read Aloud engine covering many languages.",
            VOICES,
            _safe(_espeak_installed),
            "~40 MB",
            priority=60,
        ),
        OptionalComponent(
            "audio_extras",
            "Audio: export, playback & chapters",
            "Everything for richer speech audio, in one place. FFmpeg lets QUILL "
            "export speech as MP3, M4A/M4B, OGG, Opus, or FLAC; the mpv engine adds "
            "gapless playback, exact seeking, and instant chapter jumps in the Audio "
            "Studio player; MP3 chapter markers embed a jumpable chapter list in MP3 "
            "audiobook exports. Each piece is fetched only when you first use its "
            "feature, so nothing large downloads until it is needed. WAV export and "
            "basic playback work without any of them.",
            TOOL,
            _safe(_audio_extras_installed),
            "~46 MB (+ FFmpeg ~90 MB when first exporting compressed audio)",
            note="FFmpeg (GPL/LGPL, official build), the mpv playback library (GPL; "
            "the download carries its licenses and a source offer), and mutagen "
            "(GPL-2.0+); fetched on demand from their official sources and QUILL's "
            "pinned release.",
            priority=90,
        ),
        OptionalComponent(
            "node",
            "Node.js runtime",
            "Runs Node (JavaScript/TypeScript) Quillins and the Developer Console's "
            "TypeScript interface. Python Quillins and the rest of QUILL work without "
            "it — this is the least-used extra, so it sits last.",
            TOOL,
            _safe(_node_installed),
            "~30 MB",
            note="Provided by the OpenJS Foundation; QUILL fetches the official build.",
            priority=110,
        ),
    ]
    # DECtalk and MathCAT ship only Windows .dll's (DECtalk.dll / libmathcat_c.dll),
    # so offering either on macOS advertised a download that could never work (#46).
    if sys.platform.startswith("win"):
        out.append(
            OptionalComponent(
                "dectalk",
                "DECtalk voices",
                "The classic DECtalk Read Aloud voices.",
                VOICES,
                _safe(_dectalk_installed),
                "~2 MB",
                priority=70,
            )
        )
        out.append(
            OptionalComponent(
                "mathcat",
                "MathCAT math speech engine",
                "Real natural-language speech for equations — used by Insert > Explore "
                'Equation Structure...\'s "Read this part aloud". Equations are still '
                "readable without it, via a simpler built-in template reading.",
                SPEECH_ENGINE,
                _safe(_mathcat_installed),
                "~3 MB",
                note="MathCAT (MIT, daisy/MathCATForC); fetched from QUILL's pinned release.",
                priority=100,
            )
        )
    out.extend(_dictionary_components())
    out.sort(key=lambda c: (c.priority, c.name))
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
                # A representative estimate: Hunspell language packs are a few MB.
                # (Exact per-language sizes are a future refinement, see the design.)
                "~4 MB",
            )
        )
    return rows


def describe_component(component: OptionalComponent) -> str:
    """A rich, human description of *component* for the dialog's detail box.

    Combines what it enables, its size, its license/source note, and its current
    state with a next-step hint. Wx-free and pure so it can be unit-tested.
    """
    lines: list[str] = [component.name, ""]
    if component.description:
        lines.append(component.description)
    if component.note:
        lines.append(component.note)
    size = component.size_hint or "size varies"
    if component.installed:
        lines.append("")
        lines.append(
            f"Status: Installed ({size}). Use Test to confirm it works, or Remove "
            "to delete QUILL's downloaded copy and turn its features back off."
        )
    else:
        lines.append("")
        lines.append(
            f"Status: Not installed. Download ({size}) to enable it — everything "
            "here is optional and the base app works without it."
        )
    return "\n".join(lines)


def _safe_list(getter) -> list:  # type: ignore[no-untyped-def]
    try:
        return list(getter())
    except Exception:  # noqa: BLE001
        return []


def _safe_str(getter) -> str:  # type: ignore[no-untyped-def]
    """Run a string getter, treating any failure (or None) as empty."""
    try:
        return str(getter() or "")
    except Exception:  # noqa: BLE001 - a broken getter must never crash the list
        return ""
