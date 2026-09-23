"""Wx-free foundation for the guided local-AI setup (issue #1558).

The AI Setup Wizard offers "Ollama (on your device)" one combo row above
"Ollama Cloud" and assumes the program itself is already installed -- its
failure message is "install it free from ollama.com, then try again". The
reporter of #1558 did exactly that, got lost between the two same-named
options, and asked for what this module supplies: one guided journey that
checks the machine, fetches the installer, walks the model download, and
connects QUILL to the result.

Mirrors :mod:`quill.core.speech.guided_setup`: a pure "you are here, do this
next" status machine so the dialog is a thin renderer and the whole journey is
unit-testable without a display. No ``wx`` here.

Network notes: the reachability probe and the model pull reuse the reviewed
egress sites in :mod:`quill.core.assistant_ai` and
:mod:`quill.core.ai.onboarding`; the installer download goes through
:func:`quill.core.release_assets.download_verified` (HTTPS-only, Safe-Mode
gated, atomic). ``sha256=""`` on that download is the documented concession
for a moving "latest" URL -- ollama.com publishes no stable checksum for it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: The official Windows installer, fetched over HTTPS. A moving "latest" URL:
#: there is no stable checksum to pin, which is the one case
#: ``download_verified`` documents ``sha256=""`` for.
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/OllamaSetup.exe"

#: Where the Windows installer puts the per-user install.
_WINDOWS_INSTALL_SUBPATH = Path("Programs") / "Ollama" / "ollama.exe"

#: The three visible steps: install Ollama, download a model, connect QUILL.
TOTAL_SETUP_STEPS = 3

STAGE_INSTALL = "install"
STAGE_START = "start"
STAGE_MODEL = "model"
STAGE_READY = "ready"


def ollama_install_supported() -> bool:
    """Whether this build can download and start the installer itself.

    The guided download targets the Windows ``OllamaSetup.exe``; on other
    platforms the journey still runs, but step one says where to get Ollama
    instead of offering to fetch it.
    """
    return os.name == "nt"


def ollama_executable() -> Path | None:
    """Where Ollama is installed on this machine, or ``None``.

    PATH first, then the per-user location the Windows installer uses --
    which matters because the installer does not always land on PATH until
    the next login, so "just installed" and "on PATH" are different facts.
    """
    found = shutil.which("ollama")
    if found:
        return Path(found)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = Path(local_app_data) / _WINDOWS_INSTALL_SUBPATH
        if candidate.is_file():
            return candidate
    return None


def ollama_probe(host: str = "http://localhost:11434") -> tuple[bool, list[str]]:
    """``(reachable, installed models)`` for the local server at *host*.

    Distinguishes "server answered with no models" (reachable, ``[]``) from
    "nothing answered" (not reachable) -- the journey's step two versus step
    one -- which :func:`quill.core.ai.onboarding.ollama_status` folds into one
    message. Reuses the reviewed model-listing egress path; never raises.
    """
    from quill.core.ai.providers import default_model_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings, list_assistant_models

    settings = AssistantConnectionSettings(
        provider="ollama", host=host, model=default_model_for_provider("ollama")
    )
    try:
        models, error = list_assistant_models(settings, "", timeout_seconds=3.0, max_attempts=1)
    except Exception:  # noqa: BLE001 - any failure reads as "not reachable"
        return False, []
    if error:
        return False, []
    return True, list(models)


@dataclass(frozen=True, slots=True)
class MachineFit:
    """What this computer offers a local model, plus the spoken one-liner."""

    total_ram_gb: float
    has_gpu: bool
    free_disk_gb: float
    summary: str


def machine_fit() -> MachineFit:
    """Measure the machine and word it, before anything downloads.

    The reporter of #1558 asked for exactly this order: "checking your specs,
    downloading and installing the model and connecting the 2". Detection
    failures degrade to honest wording rather than blocking the journey
    (matching ``enough_disk_for``'s unknown-never-blocks rule).
    """
    from quill.core.speech.service import detect_has_gpu, detect_total_ram_gb

    total_ram_gb = detect_total_ram_gb()
    has_gpu = detect_has_gpu()
    free_disk_gb = -1.0
    try:
        # Models land under the user profile (~/.ollama), so that drive is
        # the one whose free space matters.
        free_disk_gb = shutil.disk_usage(Path.home()).free / (1024**3)
    except OSError:
        pass

    if total_ram_gb <= 0:
        ram_text = "RAM could not be measured"
    else:
        ram_text = f"{total_ram_gb:.0f} GB of RAM"
    gpu_text = "a graphics card" if has_gpu else "no graphics card (models run on the CPU)"
    if free_disk_gb < 0:
        disk_text = "free disk space could not be measured"
    else:
        disk_text = f"{free_disk_gb:.0f} GB free on your user drive"
    summary = (
        f"Your computer: {ram_text}, {gpu_text}, and {disk_text}. "
        "Models are stored in your user folder and typically need 1 to 5 GB each; "
        "the recommendations below already fit this machine."
    )
    return MachineFit(
        total_ram_gb=total_ram_gb,
        has_gpu=has_gpu,
        free_disk_gb=free_disk_gb,
        summary=summary,
    )


@dataclass(frozen=True, slots=True)
class LocalAISetupStatus:
    """The "you are here, do this next" state for the guided local-AI dialog.

    Pure so the dialog is a thin renderer. ``stage`` is one of
    ``STAGE_INSTALL`` / ``STAGE_START`` / ``STAGE_MODEL`` / ``STAGE_READY``;
    ``headline`` is the step banner; ``next_step`` is the single imperative
    next action. The ``can_*`` flags drive button enablement so the dialog
    never re-derives the journey logic.
    """

    stage: str
    step_number: int
    total_steps: int
    headline: str
    next_step: str
    can_install: bool
    can_pull: bool
    can_finish: bool
    installed: bool
    reachable: bool
    models: tuple[str, ...]


def local_ai_setup_status(
    *,
    installed: bool,
    reachable: bool,
    models: tuple[str, ...] = (),
    install_supported: bool = True,
) -> LocalAISetupStatus:
    """Compute the guided-journey state from one probe's results.

    Four states, three steps: not installed and not answering is step one
    (get Ollama); installed but not answering is still step one, but the fix
    is starting it rather than installing it -- collapsing those two produced
    exactly the #1558 confusion, because "install it" is wrong advice to
    somebody who already did. A server that answers with no models is step
    two; a server with models is step three, connect and finish.
    """
    if not reachable and not installed:
        if install_supported:
            next_step = (
                "Choose Download and Install Ollama. QUILL fetches the official "
                "installer from ollama.com and starts it; follow its prompts, "
                "then come back here."
            )
        else:
            next_step = (
                "Install Ollama from ollama.com for this system, start it, then choose Check Again."
            )
        return LocalAISetupStatus(
            stage=STAGE_INSTALL,
            step_number=1,
            total_steps=TOTAL_SETUP_STEPS,
            headline=f"Step 1 of {TOTAL_SETUP_STEPS}: install Ollama on this computer.",
            next_step=next_step,
            can_install=install_supported,
            can_pull=False,
            can_finish=False,
            installed=False,
            reachable=False,
            models=(),
        )
    if not reachable:
        return LocalAISetupStatus(
            stage=STAGE_START,
            step_number=1,
            total_steps=TOTAL_SETUP_STEPS,
            headline=f"Step 1 of {TOTAL_SETUP_STEPS}: Ollama is installed but not running.",
            next_step=(
                "Start Ollama from the Start menu (it stays available quietly in "
                "the background), then choose Check Again."
            ),
            can_install=False,
            can_pull=False,
            can_finish=False,
            installed=True,
            reachable=False,
            models=(),
        )
    if not models:
        return LocalAISetupStatus(
            stage=STAGE_MODEL,
            step_number=2,
            total_steps=TOTAL_SETUP_STEPS,
            headline=f"Step 2 of {TOTAL_SETUP_STEPS}: download a model.",
            next_step=(
                "Pick a model below (the first one is chosen to fit this computer) "
                "and choose Download Model. The download can take a few minutes."
            ),
            can_install=False,
            can_pull=True,
            can_finish=False,
            installed=True,
            reachable=True,
            models=(),
        )
    return LocalAISetupStatus(
        stage=STAGE_READY,
        step_number=TOTAL_SETUP_STEPS,
        total_steps=TOTAL_SETUP_STEPS,
        headline=f"Step 3 of {TOTAL_SETUP_STEPS}: connect QUILL to Ollama.",
        next_step=(
            "Pick the model to use and choose Use This Model. Everything stays "
            "on this computer; nothing you write is sent anywhere else."
        ),
        can_install=False,
        can_pull=True,
        can_finish=True,
        installed=True,
        reachable=True,
        models=tuple(models),
    )


def download_ollama_installer(
    *,
    progress: Callable[[float, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Fetch the official installer to a temp file and return its path.

    All the hardening (HTTPS-only, retry/backoff, resume, atomic staging,
    Safe-Mode refusal) is :func:`release_assets.download_verified`'s; raises
    :class:`quill.core.release_assets.ReleaseAssetError` on failure.
    """
    import tempfile

    from quill.core import release_assets

    handle, raw = tempfile.mkstemp(prefix="OllamaSetup-", suffix=".exe")
    os.close(handle)
    return release_assets.download_verified(
        [OLLAMA_DOWNLOAD_URL],
        Path(raw),
        sha256="",
        progress=progress,
        should_cancel=should_cancel,
        label="Downloading Ollama...",
    )


def launch_ollama_installer(installer: Path) -> None:
    """Start the downloaded installer and return; the user drives it.

    Not ``run_subprocess_safely``: that waits, captures output and enforces a
    30-second timeout, all wrong for a GUI installer somebody clicks through
    at their own pace. Raises ``OSError`` if Windows refuses to start it.
    """
    subprocess.Popen([str(installer)])  # noqa: S603 - fetched over HTTPS by download_verified moments ago; a GUI installer the user drives
