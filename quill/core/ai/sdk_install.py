"""In-app, on-demand install planner for the optional SDK harness packs (Phase 10).

QUILL ships the three agentic SDKs — GitHub Copilot, Claude Agent, and OpenAI
Agents — as **optional extras** (``quill[ai-copilot]`` etc.), never bundled into
the installer. They are large, fast-moving, and most users want exactly one (the
account they already pay for), so baking all three into the Inno Setup payload
would bloat every download for everyone and pin SDK versions to the release
cadence. Instead a pack is installed *on demand* from inside the app the first
time the user chooses that engine — the "magical" path: pick Copilot, QUILL
offers to install it, runs ``pip install`` into the running environment, and the
pack self-registers on next probe.

This module is the **pure planner** for that flow. Mirroring
:mod:`quill.core.ai.device_login`, it never calls out itself: it builds the
command and the human-readable hint, and a single :func:`run_install` executes a
plan through an **injected runner** supplied at the UI boundary (where the
consent surface and :mod:`quill.stability.safe_subprocess` live). That keeps this
layer wx-free, network-free, gate-clean (no new egress/subprocess site here), and
fully unit-testable without ever touching pip.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "PackInstall",
    "PACK_INSTALLS",
    "pack_install_for",
    "install_command",
    "manual_install_hint",
    "InstallRunner",
    "InstallResult",
    "run_install",
    "PackInstallError",
    "ai_packs_dir",
    "pack_dir",
    "activate_ai_packs",
    "is_pack_importable",
    "install_supported",
    "install_pack",
]

# The distribution name; ``quill[ai-copilot]`` resolves the optional extra.
_DIST = "quill"


@dataclass(frozen=True, slots=True)
class PackInstall:
    """How to install one optional SDK harness pack.

    ``extra`` is the pyproject optional-dependencies key; ``pip_target`` is what
    ``pip install`` receives; ``requirement`` is the underlying PyPI requirement
    (shown so the user sees exactly what lands), and ``import_name`` is the module
    the pack probes for (matching :attr:`SdkHarness.sdk_modules`).
    """

    pack_id: str
    display_name: str
    extra: str
    requirement: str
    import_name: str

    @property
    def pip_target(self) -> str:
        return f"{_DIST}[{self.extra}]"


# Keyed by harness/pack id (matches the ``pack_id`` on each SdkHarness). Kept in
# step with pyproject ``[project.optional-dependencies]`` and the pack modules.
PACK_INSTALLS: dict[str, PackInstall] = {
    "copilot": PackInstall(
        pack_id="copilot",
        display_name="GitHub Copilot SDK",
        extra="ai-copilot",
        requirement="github-copilot-sdk>=1.0",
        import_name="copilot",
    ),
    "claude_agent_sdk": PackInstall(
        pack_id="claude_agent_sdk",
        display_name="Claude Agent SDK",
        extra="ai-claude",
        requirement="claude-agent-sdk>=0.1.0",
        import_name="claude_agent_sdk",
    ),
    "openai_agents": PackInstall(
        pack_id="openai_agents",
        display_name="OpenAI Agents SDK",
        extra="ai-openai",
        requirement="openai-agents>=0.1.0",
        import_name="agents",
    ),
}


def pack_install_for(pack_id: str) -> PackInstall | None:
    """Return the install spec for a pack id, or ``None`` if it is not optional.

    The Native harness (``"native"``) is always present and has no install spec,
    so it correctly returns ``None``.
    """
    return PACK_INSTALLS.get(pack_id)


def install_command(pack_id: str) -> list[str]:
    """Build the argv to install a pack into the *running* interpreter.

    Uses ``sys.executable -m pip`` so it targets the exact environment QUILL is
    running in (frozen build, venv, or system Python) rather than whatever ``pip``
    happens to be on PATH. Raises :class:`KeyError` for an unknown pack id.
    """
    spec = PACK_INSTALLS[pack_id]
    return [sys.executable, "-m", "pip", "install", spec.pip_target]


def manual_install_hint(pack_id: str) -> str:
    """The copy-pasteable command a user can run themselves, for the UI/help."""
    spec = PACK_INSTALLS[pack_id]
    return f'pip install "{spec.pip_target}"'


# A runner executes one install argv and returns (exit_code, combined_output).
# Supplied at the UI boundary (safe_subprocess) so this module stays gate-clean.
InstallRunner = Callable[["list[str]"], "tuple[int, str]"]


@dataclass(frozen=True, slots=True)
class InstallResult:
    """Outcome of an attempted pack install."""

    pack_id: str
    ok: bool
    exit_code: int
    output: str = ""
    error: str = ""

    def message(self) -> str:
        """A screen-reader-friendly summary (A11Y-1 announcement grammar)."""
        spec = PACK_INSTALLS.get(self.pack_id)
        name = spec.display_name if spec else self.pack_id
        if self.ok:
            return f"Installed {name}. The engine is ready to use."
        detail = self.error or f"the installer exited with code {self.exit_code}"
        return f"Could not install {name}: {detail}."


def run_install(pack_id: str, *, runner: InstallRunner) -> InstallResult:
    """Install a pack by handing its command to an injected ``runner``.

    Any exception from the runner is contained as a failed result, never raised,
    so the caller can announce a clean message and keep the app alive (a pack is
    always optional; QUILL works without it).
    """
    if pack_id not in PACK_INSTALLS:
        return InstallResult(pack_id, ok=False, exit_code=-1, error="Unknown SDK pack.")
    try:
        exit_code, output = runner(install_command(pack_id))
    except Exception as exc:  # runner/subprocess failure stays contained
        return InstallResult(pack_id, ok=False, exit_code=-1, error=str(exc))
    return InstallResult(
        pack_id,
        ok=exit_code == 0,
        exit_code=exit_code,
        output=output,
        error="" if exit_code == 0 else output.strip().splitlines()[-1] if output.strip() else "",
    )


# ---------------------------------------------------------------------------
# Engine-pack install (frozen-build-safe), mirroring speech engine_install.py.
# ---------------------------------------------------------------------------
# A plain ``pip install`` into the running interpreter is not writable in a
# frozen build, so the real in-app install lands each pack's underlying
# requirement, wheel-only, in a user-writable folder added to ``sys.path`` — the
# same proven pattern as the optional speech engines. The only network touch is
# the runtime's pip reaching PyPI (documented as subprocess egress in the
# network-egress audit).

_AI_PACKS_SUBDIR = "ai-packs"
_INSTALL_TIMEOUT_S = 1800.0


class PackInstallError(CodedError):
    """Raised when an optional SDK pack install fails or is unavailable."""

    code = "QUILL-AI-SDK-PACK-INSTALL"


def ai_packs_dir() -> Path:
    """The root folder holding on-demand-installed SDK packs (user-writable)."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / _AI_PACKS_SUBDIR


def pack_dir(pack_id: str) -> Path:
    """The folder a given pack is installed into."""
    return ai_packs_dir() / pack_id


def activate_ai_packs() -> None:
    """Prepend any installed SDK-pack folders to ``sys.path`` (idempotent).

    Called once early in startup so a pack installed on demand becomes
    importable — and therefore self-registers via its harness probe — for the
    rest of the session. Safe and cheap when no pack exists.
    """
    root = ai_packs_dir()
    changed = False
    for pack_id in PACK_INSTALLS:
        folder = root / pack_id
        try:
            if not folder.is_dir() or not any(folder.iterdir()):
                continue
        except OSError:
            continue
        entry = str(folder)
        if entry not in sys.path:
            sys.path.insert(0, entry)
            changed = True
    if changed:
        importlib.invalidate_caches()


def is_pack_importable(pack_id: str) -> bool:
    """True when the pack's SDK module can be imported (after activation)."""
    spec = PACK_INSTALLS.get(pack_id)
    if spec is None:
        return False
    return importlib.util.find_spec(spec.import_name) is not None


def install_supported() -> bool:
    """True when QUILL can install a pack on demand (pip must be importable)."""
    return importlib.util.find_spec("pip") is not None


def _pip_target_command(dest: Path, requirement: str, python_executable: str) -> list[str]:
    return [
        python_executable,
        "-m",
        "pip",
        "install",
        "--no-input",
        "--disable-pip-version-check",
        "--only-binary=:all:",
        "--no-warn-script-location",
        "--upgrade",
        "--target",
        str(dest),
        requirement,
    ]


def _tail(text: str, *, limit: int = 400) -> str:
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text


def install_pack(
    pack_id: str,
    progress: Callable[[float, str], None] | None = None,
    *,
    dest_dir: Path | None = None,
    python_executable: str | None = None,
    timeout_seconds: float = _INSTALL_TIMEOUT_S,
    runner: Callable[..., object] | None = None,
) -> Path:
    """Install a pack's SDK on demand into a user-writable folder; return it.

    Wheel-only, no admin, not in the installer payload, activated on ``sys.path``
    immediately so the pack is importable this session. ``runner`` defaults to
    :func:`quill.stability.safe_subprocess.run_subprocess_safely` and is
    injectable for tests. Raises :class:`PackInstallError` on Safe Mode, missing
    pip, an unknown pack, a non-zero pip exit, or if the SDK still cannot import.
    """
    spec = PACK_INSTALLS.get(pack_id)
    if spec is None:
        raise PackInstallError(f"Unknown SDK pack: {pack_id!r}.")
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise PackInstallError("Installing AI engines is disabled in Safe Mode.")
    if not install_supported():
        raise PackInstallError(
            f"This build cannot install {spec.display_name} automatically (pip is "
            f"unavailable). Install it from source with: {manual_install_hint(pack_id)}"
        )

    dest = Path(dest_dir) if dest_dir is not None else pack_dir(pack_id)
    dest.mkdir(parents=True, exist_ok=True)
    python_exe = python_executable or sys.executable
    if not python_exe:
        raise PackInstallError("Could not locate the Python runtime to install into.")

    if progress is not None:
        progress(0.05, f"Preparing to install {spec.display_name}...")
    command = _pip_target_command(dest, spec.requirement, python_exe)
    run = runner if runner is not None else _default_runner
    if progress is not None:
        progress(0.15, f"Downloading {spec.display_name} (this can take a few minutes)...")

    try:
        result = run(command, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - surface a clean message, never crash
        raise PackInstallError(f"Could not run the installer: {exc}") from exc

    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = _tail(getattr(result, "stderr", "") or getattr(result, "stdout", ""))
        raise PackInstallError(
            f"{spec.display_name} installation failed (pip exit {returncode}). {detail}"
        )

    if progress is not None:
        progress(0.9, "Finishing up...")
    if str(dest) not in sys.path:
        sys.path.insert(0, str(dest))
    importlib.invalidate_caches()
    if not is_pack_importable(pack_id):
        raise PackInstallError(
            f"{spec.display_name} was installed but could not be imported. Try restarting QUILL."
        )
    if progress is not None:
        progress(1.0, "Done.")
    return dest


def _default_runner(command: Sequence[str], *, timeout_seconds: float) -> object:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely(command, timeout_seconds=timeout_seconds)
