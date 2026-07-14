"""Model registry, RAM-tiered recommendation, saved choice, and auto-download
for the llama.cpp backend.

Users pick a model in Settings (default = "Recommended", chosen from RAM); the
GGUF is downloaded automatically on first use into ``<app data>/models``. No
manual file handling. Standard library only (urllib) — no extra dependencies.
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_ProgressCallback = Callable[[int, int], None]

_CHOICE_FILE = "ai-model.json"
_LOW_RAM_THRESHOLD_GB = 8.0


@dataclass(frozen=True, slots=True)
class ModelSpec:
    id: str
    name: str
    filename: str
    url: str
    approx_gb: float
    note: str = ""
    sha256: str = ""


# Curated, free, open GGUF models hosted on non-gated public repositories.
# Each download is verified against the pinned SHA-256 before use (SEC-6).
MODELS: dict[str, ModelSpec] = {
    "llama-3.2-1b": ModelSpec(
        "llama-3.2-1b",
        "Llama 3.2 1B Instruct",
        "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/"
        "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        0.8,
        "Best for low-memory machines (under 8 GB RAM).",
        "6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83",
    ),
    "phi-4-mini": ModelSpec(
        "phi-4-mini",
        "Phi-4-mini Instruct",
        "Phi-4-mini-instruct-Q4_K_M.gguf",
        "https://huggingface.co/lmstudio-community/Phi-4-mini-instruct-GGUF/resolve/main/"
        "Phi-4-mini-instruct-Q4_K_M.gguf",
        2.5,
        "Recommended for machines with 8 GB RAM or more.",
        "3c4d3cbdf3006d81444f6c7a5a56eb93d8e0f0e2ba5963b8ab62f9fd42604233",
    ),
}


def total_ram_gb() -> float:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")  # type: ignore[attr-defined]
        phys_pages = os.sysconf("SC_PHYS_PAGES")  # type: ignore[attr-defined]
        return float(page_size) * float(phys_pages) / (1024**3)
    except (ValueError, AttributeError, OSError):
        pass
    if sys.platform.startswith("win"):
        import ctypes

        class _MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return float(stat.ullTotalPhys) / (1024**3)
    return _LOW_RAM_THRESHOLD_GB


def recommended_id() -> str:
    """The model recommended for this machine's RAM."""
    return "llama-3.2-1b" if total_ram_gb() < _LOW_RAM_THRESHOLD_GB else "phi-4-mini"


def choose_model_spec() -> ModelSpec:
    return MODELS[recommended_id()]


# --- saved choice (a Settings value) --------------------------------------


def _choice_path() -> Path:
    return app_data_dir() / "ai" / _CHOICE_FILE


def load_model_choice() -> str:
    """Return the saved model id, or 'auto' (use the RAM recommendation)."""
    raw = read_json(_choice_path(), default={})
    if isinstance(raw, dict):
        choice = str(raw.get("model", "auto"))
        if choice == "auto" or choice in MODELS:
            return choice
    return "auto"


def save_model_choice(model_id: str) -> None:
    if model_id != "auto" and model_id not in MODELS:
        raise ValueError(f"Unknown model id: {model_id}")
    write_json_atomic(_choice_path(), {"schema_version": 1, "model": model_id})


# --- AI on/off (a Settings value, set during onboarding) -------------------


def _ai_enabled_path() -> Path:
    return app_data_dir() / "ai" / "ai-enabled.json"


def load_ai_enabled() -> bool:
    """Whether the user has the AI features turned on (default on)."""
    raw = read_json(_ai_enabled_path(), default={})
    if isinstance(raw, dict) and "enabled" in raw:
        return bool(raw["enabled"])
    return True


def save_ai_enabled(enabled: bool) -> None:
    write_json_atomic(_ai_enabled_path(), {"enabled": bool(enabled)})


def resolve_spec(choice: str | None = None) -> ModelSpec:
    choice = choice or load_model_choice()
    if choice == "auto" or choice not in MODELS:
        return choose_model_spec()
    return MODELS[choice]


# --- download / resolution -------------------------------------------------


def models_dir() -> Path:
    return app_data_dir() / "models"


def model_path_for(spec: ModelSpec) -> Path:
    return models_dir() / spec.filename


def is_downloaded(spec: ModelSpec) -> bool:
    return model_path_for(spec).exists()


def ensure_model(progress: _ProgressCallback | None = None) -> str:
    """Return a local GGUF path for the chosen model, downloading it if needed.

    ``progress`` is an optional callable(downloaded_bytes, total_bytes).
    """
    override = os.environ.get("QUILL_LLAMA_MODEL")
    if override and Path(override).expanduser().exists():
        return str(Path(override).expanduser())
    spec = resolve_spec()
    target = model_path_for(spec)
    if target.exists():
        return str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _download(spec.url, target, progress, spec.sha256)
    return str(target)


def existing_model() -> str | None:
    override = os.environ.get("QUILL_LLAMA_MODEL")
    if override and Path(override).expanduser().exists():
        return str(Path(override).expanduser())
    target = model_path_for(resolve_spec())
    return str(target) if target.exists() else None


def _download(
    url: str,
    target: Path,
    progress: _ProgressCallback | None = None,
    expected_sha256: str = "",
) -> None:
    part = target.with_name(target.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Quill"})
    from quill.core.net import verified_ssl_context

    context = verified_ssl_context() if url.lower().startswith("https") else None
    digest = hashlib.sha256()
    with (
        urllib.request.urlopen(request, context=context) as response,
        open(part, "wb") as out,
    ):
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
    if expected_sha256:
        actual = digest.hexdigest()
        if actual.lower() != expected_sha256.lower():
            part.unlink(missing_ok=True)
            raise RuntimeError(
                "Downloaded model failed its integrity check and was discarded.\n"
                f"  url:      {url}\n"
                f"  expected: {expected_sha256}\n"
                f"  got:      {actual}"
            )
    part.replace(target)
