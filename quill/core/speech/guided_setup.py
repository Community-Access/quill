"""Wx-free foundation for the guided offline-speech setup in the Download
Optional Components hub.

The hub walks the user through *choosing* an offline speech engine --
whisper.cpp, Faster Whisper, or Vosk -- with plain-language explanations of
the trade-off, then choosing a model (via :mod:`quill.core.speech.service`,
which already marks one "recommended for your computer"). This module
supplies the engine step's data and a friendly default, so the UI is a thin
renderer. No ``wx`` here.

Meet-people-where-they-are: the recommended engine is the light one that works
on any machine, and the recommended model defaults small so the user is
transcribing within a minute. All three engines are reached through this one
guided flow rather than separate hub rows, so there is exactly one "offline
speech" download to find.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OfflineSpeechEngineOption:
    """One offline STT engine the user can pick in the guided flow."""

    engine_id: str  # matches the provider id: "whispercpp" | "fasterwhisper"
    name: str
    tagline: str  # short trade-off spoken as part of the radio label on focus
    summary: str  # fuller plain-language explanation for the detail area
    installed: bool
    install_supported: bool
    recommended: bool = False


# The friendly default: light, CPU-friendly, small download, works everywhere.
RECOMMENDED_ENGINE_ID = "whispercpp"

_WHISPERCPP_TAGLINE = "light and fast, works on any computer"
_WHISPERCPP_SUMMARY = (
    "Light and fast on any computer. Runs well on the CPU with a small download, "
    "and it is a great choice for most people. Pick this if you are not sure."
)
_FASTER_WHISPER_TAGLINE = "most accurate; larger and can use your graphics card"
_FASTER_WHISPER_SUMMARY = (
    "The most accurate option. It is a larger download, uses more memory, and can "
    "use your graphics card if you have one. Best when you want top-quality "
    "transcription and have a capable machine."
)
_VOSK_TAGLINE = "very low resource; best for old or low-memory machines"
_VOSK_SUMMARY = (
    "A tiny offline engine for old or low-memory machines with no GPU. Less "
    "accurate than the other two, but works on hardware where they may struggle."
)
_NEMOTRON_TAGLINE = "top English accuracy on the CPU; no GPU or torch needed"
_NEMOTRON_SUMMARY = (
    "NVIDIA's Nemotron streaming model (English only) run on the CPU via "
    "sherpa-onnx — very accurate and fast, with no graphics card required. A "
    "larger download than Vosk; a strong choice for English dictation."
)
_PARAKEET_TAGLINE = "most reliable for dictation; 25 languages, CPU-only"


def _parakeet_summary() -> str:
    """Parakeet's summary, with its capability sentence drawn from the catalog.

    The catalog is the manifest of truth for what a model can do; composing the
    sentence from it (the same ``capability_sentence`` the model-manager rows
    speak) means this picker can never promise something the catalog does not.
    """
    from quill.core.speech import catalog
    from quill.core.speech.service import capability_sentence

    info = catalog.parakeet_model_by_id(catalog.PARAKEET_RECOMMENDED_MODEL_ID)
    extra = capability_sentence(info) if info is not None else ""
    return (
        "NVIDIA's Parakeet 3 run on the CPU via sherpa-onnx — 25 languages, no "
        "graphics card or torch, and once its model is installed dictation "
        "prefers it automatically. Unlike Whisper it cannot type a phantom "
        "phrase over a silent pause." + extra
    )


def _safe(predicate) -> bool:  # type: ignore[no-untyped-def]
    """Run a detector, treating any failure as 'not available'."""
    try:
        return bool(predicate())
    except Exception:  # noqa: BLE001 - an optional engine must never break the list
        return False


def _whispercpp_installed() -> bool:
    from quill.core.speech.providers.whispercpp import resolve_whisper_executable

    return resolve_whisper_executable() is not None


def _faster_whisper_installed() -> bool:
    from quill.core.speech.engine_install import is_faster_whisper_available

    return is_faster_whisper_available()


def _faster_whisper_install_supported() -> bool:
    from quill.core.speech.engine_install import faster_whisper_install_supported

    return faster_whisper_install_supported()


def _vosk_installed() -> bool:
    from quill.core.speech.engine_install import is_vosk_available

    return is_vosk_available()


def _vosk_install_supported() -> bool:
    from quill.core.speech.engine_install import vosk_install_supported

    return vosk_install_supported()


def _nemotron_installed() -> bool:
    from quill.core.speech.engine_install import is_nemotron_available

    return is_nemotron_available()


def _nemotron_install_supported() -> bool:
    from quill.core.speech.engine_install import nemotron_install_supported

    return nemotron_install_supported()


def _parakeet_model_available() -> bool:
    """True only when the Parakeet 3 model is hosted+pinned on assets-v1
    (same offer-nothing-you-cannot-finish rule as Nemotron below)."""
    from quill.core.speech import catalog, model_mirrors

    return model_mirrors.mirror_for("parakeet", catalog.PARAKEET_RECOMMENDED_MODEL_ID) is not None


def _nemotron_model_available() -> bool:
    """True only when the Nemotron model is hosted+pinned on the assets-v1 release.

    Until the verified ONNX zip is uploaded and its SHA pinned in
    :mod:`quill.core.speech.model_mirrors`, the engine cannot finish setup (its
    ``download_model`` would fail), so it is not offered in the guided picker at
    all — no half-install of the runtime followed by a dead end. It appears
    automatically once the asset is live.
    """
    from quill.core.speech import catalog, model_mirrors

    return model_mirrors.mirror_for("nemotron", catalog.NEMOTRON_RECOMMENDED_MODEL_ID) is not None


def offline_speech_engine_options() -> list[OfflineSpeechEngineOption]:
    """The engine choices for the guided offline-speech flow, recommended first.

    whisper.cpp downloads from QUILL's own verified release asset (always
    installable); Faster Whisper installs via pip and is only offered when that
    is supported in this build. Nemotron is appended only when its model asset is
    hosted+pinned (otherwise it cannot complete setup, so it is not shown).
    """
    options = [
        OfflineSpeechEngineOption(
            engine_id="whispercpp",
            name="Whisper.cpp",
            tagline=_WHISPERCPP_TAGLINE,
            summary=_WHISPERCPP_SUMMARY,
            installed=_safe(_whispercpp_installed),
            install_supported=True,
            recommended=True,
        ),
        OfflineSpeechEngineOption(
            engine_id="fasterwhisper",
            name="Faster Whisper",
            tagline=_FASTER_WHISPER_TAGLINE,
            summary=_FASTER_WHISPER_SUMMARY,
            installed=_safe(_faster_whisper_installed),
            install_supported=_safe(_faster_whisper_install_supported),
        ),
        OfflineSpeechEngineOption(
            engine_id="vosk",
            name="Vosk",
            tagline=_VOSK_TAGLINE,
            summary=_VOSK_SUMMARY,
            installed=_safe(_vosk_installed),
            install_supported=_safe(_vosk_install_supported),
        ),
    ]
    # Parakeet 3 and Nemotron appear only once their model assets are
    # hosted+pinned (mirror-gated); until then each is fully inert and
    # unlisted. Both ride the same sherpa-onnx runtime, so Nemotron's
    # installed/installable detectors answer for Parakeet too. Parakeet sits
    # right after the recommended default because it is the engine dictation
    # itself prefers once installed.
    if _safe(_parakeet_model_available):
        options.insert(
            1,
            OfflineSpeechEngineOption(
                engine_id="parakeet",
                name="Parakeet 3 (NVIDIA)",
                tagline=_PARAKEET_TAGLINE,
                summary=_parakeet_summary(),
                installed=_safe(_nemotron_installed),
                install_supported=_safe(_nemotron_install_supported),
            ),
        )
    if _safe(_nemotron_model_available):
        options.append(
            OfflineSpeechEngineOption(
                engine_id="nemotron",
                name="Nemotron (NVIDIA)",
                tagline=_NEMOTRON_TAGLINE,
                summary=_NEMOTRON_SUMMARY,
                installed=_safe(_nemotron_installed),
                install_supported=_safe(_nemotron_install_supported),
            )
        )
    return options


def recommended_engine_id(options: list[OfflineSpeechEngineOption] | None = None) -> str:
    """The engine to preselect: an already-installed one if present, else the
    friendly default (whisper.cpp)."""
    opts = options if options is not None else offline_speech_engine_options()
    for opt in opts:
        if opt.installed:
            return opt.engine_id
    return RECOMMENDED_ENGINE_ID


@dataclass(frozen=True, slots=True)
class ModelChoice:
    """One downloadable model for the guided model step."""

    model_id: str
    display_name: str
    size_text: str
    summary: str  # what it's good for (recommended_use), for the picker
    recommended: bool  # best fit for this computer (recommend_model_id)


def _size_text(megabytes: int) -> str:
    if megabytes >= 1024:
        return f"~{megabytes / 1024:.1f} GB"
    return f"~{megabytes} MB"


def _catalog_models(engine_id: str) -> tuple:  # type: ignore[type-arg]
    from quill.core.speech import catalog

    if engine_id == "fasterwhisper":
        return catalog.FASTER_WHISPER_MODELS
    if engine_id == "vosk":
        return catalog.VOSK_MODELS
    if engine_id == "nemotron":
        return catalog.NEMOTRON_MODELS
    return catalog.WHISPER_CPP_MODELS


def models_for_engine(engine_id: str) -> list[ModelChoice]:
    """Downloadable models for *engine_id*, smallest first, with the best fit for
    this computer marked recommended.

    Built from the static catalog so the picker works *before* the engine is
    installed (the guided flow installs the engine and the chosen model together).
    """
    from quill.core.speech.service import detect_has_gpu, detect_total_ram_gb, recommend_model_id

    models = _catalog_models(engine_id)
    ids = [m.id for m in models]
    if not ids:
        return []
    try:
        best_fit = recommend_model_id(ids, detect_total_ram_gb(), detect_has_gpu())
    except Exception:  # noqa: BLE001 - detection must never break the picker
        best_fit = ids[0]
    return [
        ModelChoice(
            model_id=m.id,
            display_name=m.display_name,
            size_text=_size_text(m.approximate_size_mb),
            summary=m.recommended_use,
            recommended=m.id == best_fit,
        )
        for m in models
    ]


def default_model_id(engine_id: str) -> str:
    """The model to preselect: the smallest, so the user is transcribing within a
    minute (meet-people-where-they-are). The best-fit model is still marked
    'recommended' in the list for those who want more accuracy."""
    ids = [m.id for m in _catalog_models(engine_id)]
    return ids[0] if ids else ""


# The guided dictation journey has three visible steps: pick+install an engine,
# download a model, then test and make it the default. TOTAL_SETUP_STEPS keeps
# the "Step N of 3" wording in one place.
TOTAL_SETUP_STEPS = 3

STAGE_ENGINE = "engine"
STAGE_MODEL = "model"
STAGE_READY = "ready"


@dataclass(frozen=True, slots=True)
class DictationSetupStatus:
    """The "you are here, do this next" state for the guided dictation panel.

    Pure and wx-free so the panel is a thin renderer and the whole journey is
    unit-testable. ``stage`` is one of ``STAGE_ENGINE`` / ``STAGE_MODEL`` /
    ``STAGE_READY``; ``headline`` is the step banner; ``next_step`` is the single
    imperative next action. The ``can_*`` flags drive button enablement so the
    panel never has to re-derive the journey logic.
    """

    stage: str
    step_number: int
    total_steps: int
    headline: str
    next_step: str
    can_test: bool
    can_set_default: bool
    is_default: bool
    engine_installed: bool
    has_model: bool


def dictation_setup_status(
    *,
    engine_name: str,
    engine_installed: bool,
    has_installed_model: bool,
    is_default: bool,
    engine_install_supported: bool = True,
) -> DictationSetupStatus:
    """Compute the guided-journey state for one dictation engine.

    The three stages map to the three things a user must do, in order: get the
    engine, get a model, then test it and make it the default. Each stage names
    the single next action, so the panel can show one clear "do this next" line
    and light up exactly the right button. ``is_default`` reflects whether this
    engine is already the saved dictation default (``settings.speech_provider``).
    """
    if not engine_installed:
        if engine_install_supported:
            next_step = "Select an engine above, then choose Install selected engine."
        else:
            next_step = (
                "This engine can't be installed automatically on this system; "
                "pick another engine above."
            )
        return DictationSetupStatus(
            stage=STAGE_ENGINE,
            step_number=1,
            total_steps=TOTAL_SETUP_STEPS,
            headline=f"Step 1 of {TOTAL_SETUP_STEPS}: install the {engine_name} engine.",
            next_step=next_step,
            can_test=False,
            can_set_default=False,
            is_default=is_default,
            engine_installed=False,
            has_model=False,
        )
    if not has_installed_model:
        return DictationSetupStatus(
            stage=STAGE_MODEL,
            step_number=2,
            total_steps=TOTAL_SETUP_STEPS,
            headline=f"Step 2 of {TOTAL_SETUP_STEPS}: download a model for {engine_name}.",
            next_step=(
                "Pick a model below (a recommended one is already selected) and "
                "choose Download Selected."
            ),
            can_test=False,
            can_set_default=False,
            is_default=is_default,
            engine_installed=True,
            has_model=False,
        )
    if is_default:
        return DictationSetupStatus(
            stage=STAGE_READY,
            step_number=TOTAL_SETUP_STEPS,
            total_steps=TOTAL_SETUP_STEPS,
            headline=f"Ready: {engine_name} is your dictation default.",
            next_step=(
                "Use Test dictation to confirm it, or download another model to switch quality."
            ),
            can_test=True,
            can_set_default=False,
            is_default=True,
            engine_installed=True,
            has_model=True,
        )
    return DictationSetupStatus(
        stage=STAGE_READY,
        step_number=TOTAL_SETUP_STEPS,
        total_steps=TOTAL_SETUP_STEPS,
        headline=f"Step {TOTAL_SETUP_STEPS} of {TOTAL_SETUP_STEPS}: test {engine_name} "
        "and set it as your default.",
        next_step="Use Test dictation to try it, then choose Set as Default.",
        can_test=True,
        can_set_default=True,
        is_default=False,
        engine_installed=True,
        has_model=True,
    )
