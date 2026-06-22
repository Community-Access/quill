"""Speech service facade (#617).

A thin, testable seam between the UI and the providers: builds the default
registry (lazily registering the whisper.cpp provider) and turns a provider's
model list into accessible, ready-to-display rows. Keeping this logic here (not
in the wx dialog) means the model-manager content is unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError

from quill.core.paths import app_data_dir
from quill.core.speech.provider import SpeechToTextProvider
from quill.core.speech.registry import SpeechProviderRegistry
from quill.core.storage import read_json, write_json_atomic

DEFAULT_PROVIDER_ID = "whispercpp"


def _prefs_path() -> object:
    return app_data_dir() / "speech-settings.json"


def load_input_device() -> int:
    """Return the saved dictation microphone index (-1 = system default)."""
    try:
        data = read_json(_prefs_path(), default={})  # type: ignore[arg-type]
    except JSONDecodeError:
        return -1
    if not isinstance(data, dict):
        return -1
    try:
        return int(data.get("input_device", -1))
    except (TypeError, ValueError):
        return -1


def save_input_device(index: int) -> None:
    """Persist the chosen dictation microphone index."""
    write_json_atomic(_prefs_path(), {"input_device": int(index)})  # type: ignore[arg-type]


def default_registry(executable_path: str | None = None) -> SpeechProviderRegistry:
    """Return a registry with the built-in providers registered (lazy import).

    The bundled whisper.cpp provider is always registered. The optional Faster
    Whisper provider registers only when its library imports successfully, so an
    uninstalled engine simply never appears in the engine chooser.
    """
    registry = SpeechProviderRegistry()
    from quill.core.speech.providers.whispercpp import WhisperCppProvider

    registry.register(WhisperCppProvider(executable_path))

    try:
        from quill.core.speech.providers.fasterwhisper import FasterWhisperProvider

        provider = FasterWhisperProvider()
        if provider.is_available():
            registry.register(provider)
    except Exception:  # noqa: BLE001 - an optional engine must never break the registry
        pass

    try:
        from quill.core.speech.providers.parakeet import ParakeetProvider

        parakeet = ParakeetProvider()
        if parakeet.is_available():
            registry.register(parakeet)
    except Exception:  # noqa: BLE001 - an optional engine must never break the registry
        pass

    # Cloud providers contributed by enabled Quillins (network-backed; the offline
    # transcribe paths skip them). Empty in Safe Mode or with no provider Quillins.
    try:
        from .quillin_providers import quillin_transcription_providers

        for cloud_provider in quillin_transcription_providers():
            registry.register(cloud_provider)
    except Exception:  # noqa: BLE001 - a contributed provider must never break the registry
        pass

    return registry


@dataclass(frozen=True, slots=True)
class ModelRow:
    """One accessible row for the model-manager list."""

    id: str
    installed: bool
    label: str
    fits: bool = True
    required_ram_gb: int = 0
    ram_warning: str = ""
    recommended: bool = False
    gpu_note: str = ""
    license_name: str = ""
    model_card_url: str = ""


def _size_text(mb: int) -> str:
    if mb >= 1000:
        return f"{mb / 1000:.1f} GB"
    return f"{mb} MB"


def detect_has_gpu() -> bool:
    """True when a CUDA GPU is present (reuses the BITS Whisperer probe, wx-free)."""
    from quill.core.bw_speech import has_nvidia_gpu

    return has_nvidia_gpu()


def machine_summary(total_ram_gb: float, has_gpu: bool) -> str:
    """One-line, speakable description of the machine for the model-manager header."""
    gpu = "a graphics card (GPU) for faster speech" if has_gpu else "no GPU (uses the CPU)"
    return f"Your computer: {total_ram_gb:.1f} GB RAM and {gpu}."


def recommend_model_id(model_ids: list[str], total_ram_gb: float, has_gpu: bool) -> str:
    """Pick the best-fit model id for this machine from those the provider offers.

    Conservative RAM tiers, nudged up one step when a GPU is present (the heavier
    models are practical with hardware acceleration). Always returns an id that is
    actually in ``model_ids`` so the recommendation is selectable.
    """
    if not model_ids:
        return ""
    if total_ram_gb <= 0:
        preference = ["small", "base", "tiny"]
    elif total_ram_gb < 3:
        preference = ["tiny", "base", "small"]
    elif total_ram_gb < 6:
        preference = ["base", "small", "tiny"]
    elif total_ram_gb < 12:
        preference = ["small", "base", "medium"]
    elif total_ram_gb < 16:
        preference = ["medium", "small", "large-v3"]
    elif has_gpu:
        preference = ["large-v3", "medium", "small"]
    else:
        preference = ["medium", "small", "large-v3"]
    for candidate in preference:
        if candidate in model_ids:
            return candidate
    return model_ids[0]


def models_dir_free_gb() -> float:
    """Free disk space (GB) where speech models are stored; -1.0 if unknown."""
    import shutil

    from quill.core.speech.models import models_root

    try:
        root = models_root()
        root.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(root).free / (1024**3)
    except Exception:  # noqa: BLE001 - unknown free space must not block a download
        return -1.0


def enough_disk_for(size_mb: int, free_gb: float, *, buffer_gb: float = 1.0) -> bool:
    """True when ``free_gb`` comfortably holds a ``size_mb`` model (plus a buffer)."""
    if free_gb < 0:
        return True  # unknown -> don't block the user
    return free_gb >= (size_mb / 1024.0) + buffer_gb


def required_ram_gb(size_mb: int) -> int:
    """Approximate the RAM a model needs to load and run, from its download size.

    whisper.cpp / CTranslate2 need roughly the weights plus working memory, so we
    map the download size onto conservative tiers (aligned with the BITS Whisperer
    machine-guidance tiers). This is a guide for the warning, not a hard gate.
    """
    if size_mb <= 200:
        return 2
    if size_mb <= 600:
        return 4
    if size_mb <= 1800:
        return 6
    return 8


def detect_total_ram_gb() -> float:
    """Total physical RAM in GB (reuses the BITS Whisperer detector, wx-free)."""
    from quill.core.bw_speech import total_ram_gb

    return total_ram_gb()


def describe_models(
    provider: SpeechToTextProvider,
    total_ram_gb: float | None = None,
    has_gpu: bool | None = None,
) -> list[ModelRow]:
    """Build accessible model rows (status, size/accuracy, fit, and machine fit).

    ``total_ram_gb`` and ``has_gpu`` describe the machine; when omitted they are
    detected. Each row carries a RAM-fit flag, a GPU note for heavier models, and
    a "recommended for this computer" marker so the UI can guide the user and a
    screen reader can announce the reason.
    """
    if total_ram_gb is None:
        total_ram_gb = detect_total_ram_gb()
    if has_gpu is None:
        has_gpu = detect_has_gpu()
    supported = list(provider.list_supported_models())
    recommended_id = recommend_model_id([m.id for m in supported], total_ram_gb, has_gpu)
    installed_ids = {m.id for m in provider.list_installed_models()}
    rows: list[ModelRow] = []
    for info in supported:
        installed = info.id in installed_ids
        state = "Installed" if installed else "Not installed"
        need = required_ram_gb(info.approximate_size_mb)
        fits = total_ram_gb <= 0 or total_ram_gb + 0.5 >= need
        if fits:
            ram_note = f"Needs about {need} GB RAM."
            ram_warning = ""
        else:
            ram_warning = (
                f"May not run on this computer: needs about {need} GB RAM, "
                f"you have {total_ram_gb:.1f} GB."
            )
            ram_note = ram_warning
        gpu_note = ""
        if info.approximate_size_mb >= 1500 and not has_gpu:
            gpu_note = "No GPU detected; expect slow transcription on the CPU."
        recommended = info.id == recommended_id
        rec_note = " Recommended for your computer." if recommended else ""
        license_name = info.license_name or ""
        license_note = f" {license_name} licensed." if license_name else ""
        label = (
            f"{info.display_name} — {state} — {_size_text(info.approximate_size_mb)} "
            f"download — {info.accuracy_tier} accuracy, {info.speed_tier} speed. "
            f"{info.recommended_use} {ram_note}"
            f"{(' ' + gpu_note) if gpu_note else ''}{rec_note}{license_note}"
        )
        rows.append(
            ModelRow(
                id=info.id,
                installed=installed,
                label=label,
                fits=fits,
                required_ram_gb=need,
                ram_warning=ram_warning,
                recommended=recommended,
                gpu_note=gpu_note,
                license_name=license_name,
                model_card_url=model_card_url(info.download_url),
            )
        )
    return rows


def model_card_url(download_url: str | None) -> str:
    """Best-effort Hugging Face model-card URL from a model's download source.

    whisper.cpp stores a full ``.../resolve/<rev>/<file>`` URL; Faster Whisper
    stores the Hub repo id (``org/name``). Returns "" when neither shape matches.
    """
    src = (download_url or "").strip()
    if not src:
        return ""
    marker = "huggingface.co/"
    if marker in src:
        rest = src.split(marker, 1)[1]
        repo = rest.split("/resolve/", 1)[0].strip("/")
        return f"https://huggingface.co/{repo}" if repo else ""
    if "/" in src and not src.lower().startswith("http"):
        return f"https://huggingface.co/{src.strip('/')}"
    return ""
