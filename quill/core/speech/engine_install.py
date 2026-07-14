"""Optional in-app install of the Faster Whisper and Vosk speech engines (#669).

No offline engine ships in the installer: the tiny default whisper.cpp engine
downloads on demand (release_assets), and the two heavier optional engines install
here. Faster Whisper (CTranslate2-based, GPU-capable) pulls in ~110 MB of binary
dependencies; Vosk (~51 MB, self-contained libvosk) is the very-low-resource
fallback. Both install **on demand** into a user-writable folder -- no admin, not in
the installer payload -- using the runtime's own pip with **binary wheels only** (no
arbitrary build steps). Vosk additionally prefers QUILL's own pinned, SHA-256-verified
wheel from the assets-v1 release when available (source resilience, PRD 5.25f), falling
back to PyPI otherwise.

The packages land in ``<app data>/engine-packs/faster-whisper`` and that folder is
added to ``sys.path`` (see :func:`activate_engine_packs`, called once at startup),
so ``importlib.util.find_spec('faster_whisper')`` then lights the engine up in the
speech registry exactly as a source install would.

Safety mirrors the model / ffmpeg download paths: blocked in Safe Mode, on an
explicit user action only, wheel-only, and the only network touch is the runtime
pip reaching PyPI (documented in the network-egress audit as a subprocess egress).
wx-free.

Every ``install_*`` function here (Faster Whisper, Vosk, Kokoro ONNX, MP3
support) first checks for a bundled offline wheelhouse via
:func:`_bundled_wheelhouse_dir` -- the Offline Edition installer
(``--bundle-offline`` in ``scripts/build_windows_distribution.py``) stages each
engine's full dependency tree as local wheels under ``{app}/wheels/<name>``.
When present, the pip install resolves entirely from disk
(``--no-index --find-links``) and never touches PyPI; the "explicit user
action only" click still gates the install itself, it just no longer needs a
network connection to complete under the Offline Edition.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.speech import models

ProgressCallback = Callable[[float, str], None]

# On-demand engine installs run pip in a subprocess; when one fails the only
# signal a user sees is a transient status-bar line, so the actual pip error
# (the piece needed to tell a blocked network apart from a dependency problem)
# is lost. Logging it to quill.log means Help > Save Diagnostics captures it.
_LOG = logging.getLogger(__name__)

#: Subdirectory under the app-data dir that holds downloadable engine packs.
ENGINE_PACKS_SUBDIR = "engine-packs"

#: The Faster Whisper pack's folder name and import name.
_FASTER_WHISPER_PACK = "faster-whisper"
_FASTER_WHISPER_MODULE = "faster_whisper"

# Kept in sync with the ``[fasterwhisper]`` extra in pyproject.toml. Wheel-only
# (``--only-binary=:all:``) so no build backend is needed at install time.
_FASTER_WHISPER_REQUIREMENTS: tuple[str, ...] = (
    "faster-whisper>=1.0",
    "huggingface_hub>=0.20",
)

#: The Vosk pack's folder name and import name.
_VOSK_PACK = "vosk"
_VOSK_MODULE = "vosk"

# Vosk itself is the only requirement; it bundles its own native libs.
_VOSK_REQUIREMENTS: tuple[str, ...] = ("vosk>=0.3.45",)

#: The Kokoro ONNX pack's folder name and import name.
_KOKORO_ONNX_PACK = "kokoro-onnx"
_KOKORO_ONNX_MODULE = "kokoro_onnx"

# kokoro-onnx pulls in onnxruntime as a transitive dep; soundfile handles WAV I/O.
# Keep these floors in sync with the pyproject ``kokoro`` extra -- the latest
# kokoro-onnx is 0.5.0 (capped at Python <3.14), so an earlier >=0.9 floor here
# was unsatisfiable and the on-demand install could never resolve a version.
_KOKORO_ONNX_REQUIREMENTS: tuple[str, ...] = (
    "kokoro-onnx>=0.5.0",
    "soundfile>=0.14.0",
)

#: On-demand MP3 chapter-marker support (the pyproject ``mp3`` extra). Pure-Python
#: and small; installed into an engine-pack like the speech engines.
_MP3_PACK = "mp3-support"
_MP3_MODULE = "mutagen"
_MP3_REQUIREMENTS: tuple[str, ...] = ("mutagen>=1.48.1",)

_INSTALL_TIMEOUT_S = 1800.0


class EngineInstallError(CodedError):
    """Raised when the optional speech-engine download/install fails."""

    code = "QUILL-SPEECH-ENGINE-INSTALL"


def engine_packs_dir() -> Path:
    """The root folder holding downloadable engine packs (user-writable)."""
    return models.app_data_dir() / ENGINE_PACKS_SUBDIR


def faster_whisper_pack_dir() -> Path:
    """The folder a downloaded Faster Whisper engine is installed into."""
    return engine_packs_dir() / _FASTER_WHISPER_PACK


def vosk_pack_dir() -> Path:
    """The folder a downloaded Vosk engine is installed into."""
    return engine_packs_dir() / _VOSK_PACK


def kokoro_onnx_pack_dir() -> Path:
    """The folder a downloaded Kokoro ONNX engine is installed into."""
    return engine_packs_dir() / _KOKORO_ONNX_PACK


def mp3_pack_dir() -> Path:
    """The folder on-demand MP3 support (mutagen) is installed into."""
    return engine_packs_dir() / _MP3_PACK


def _known_pack_dirs() -> tuple[Path, ...]:
    return (
        faster_whisper_pack_dir(),
        vosk_pack_dir(),
        kokoro_onnx_pack_dir(),
        mp3_pack_dir(),
    )


def activate_engine_packs() -> None:
    """Prepend any installed engine-pack folders to ``sys.path`` (idempotent).

    Called once early in startup so an engine the user installed on demand is
    importable for the rest of the session. Light and safe to call when no pack
    exists -- it only touches ``sys.path`` for folders that are present.
    """
    changed = False
    for pack in _known_pack_dirs():
        try:
            if not pack.is_dir() or not any(pack.iterdir()):
                continue
        except OSError:
            continue
        entry = str(pack)
        if entry not in sys.path:
            sys.path.insert(0, entry)
            changed = True
    if changed:
        importlib.invalidate_caches()


def faster_whisper_install_supported() -> bool:
    """True when QUILL can install Faster Whisper on demand.

    Requires pip to be importable in the running runtime (the shipped build keeps
    pip for exactly this; setuptools/wheel are not needed for a wheel-only install).
    """
    return importlib.util.find_spec("pip") is not None


def is_faster_whisper_available() -> bool:
    """True when the ``faster_whisper`` module is importable (after activation)."""
    return importlib.util.find_spec(_FASTER_WHISPER_MODULE) is not None


def vosk_install_supported() -> bool:
    """True when QUILL can install Vosk on demand (pip must be importable)."""
    return importlib.util.find_spec("pip") is not None


def is_vosk_available() -> bool:
    """True when the ``vosk`` module is importable (after activation)."""
    return importlib.util.find_spec(_VOSK_MODULE) is not None


def kokoro_onnx_install_supported() -> bool:
    """True when QUILL can install kokoro-onnx on demand (pip must be importable)."""
    return importlib.util.find_spec("pip") is not None


def is_kokoro_onnx_available() -> bool:
    """True when the ``kokoro_onnx`` module is importable (after activation)."""
    return importlib.util.find_spec(_KOKORO_ONNX_MODULE) is not None


def _bundled_wheelhouse_dir(name: str) -> Path | None:
    """A pre-downloaded pip wheelhouse for engine *name*, shipped with the app.

    The Offline Edition build stages each on-demand engine's full dependency
    tree (kokoro-onnx's onnxruntime/phonemizer-fork/espeakng-loader/Babel,
    Faster Whisper's ctranslate2/huggingface_hub, Vosk's cffi, mutagen, ...) as
    local wheels under ``{app}/wheels/<name>`` (see ``_stage_pip_wheelhouse``
    in ``scripts/build_windows_distribution.py``), downloaded with the exact
    same embedded Python that will later install them, so the wheel tags
    always match. When present, the matching ``install_*`` function below
    resolves entirely from disk (``pip install --no-index --find-links``)
    instead of touching PyPI. Returns None when no bundled wheelhouse exists
    (the regular installer and portable builds never stage one, so this is
    the common case).
    """
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if not app_root:
        return None
    candidate = Path(app_root) / "wheels" / name
    try:
        if candidate.is_dir() and any(candidate.glob("*.whl")):
            return candidate
    except OSError:
        return None
    return None


def install_kokoro_onnx(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    requirements: Sequence[str] | None = None,
    python_executable: str | None = None,
    timeout_seconds: float = _INSTALL_TIMEOUT_S,
    runner: Callable[..., object] | None = None,
) -> Path:
    """Install the Kokoro ONNX engine packages, returning the pack folder.

    Mirrors :func:`install_faster_whisper` exactly: wheel-only into a
    user-writable engine-pack folder, activated on ``sys.path`` immediately.
    Installs ``kokoro-onnx`` and ``soundfile``; ``onnxruntime`` is a transitive dep.
    When the Offline Edition's bundled wheelhouse is present
    (:func:`_bundled_wheelhouse_dir`), this resolves entirely from local
    disk and never touches the network; otherwise it downloads from PyPI like
    every other on-demand engine. Raises :class:`EngineInstallError` on Safe
    Mode, unavailable pip, a non-zero pip exit, or if the engine still cannot
    be imported afterward.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise EngineInstallError("Downloading speech engines is disabled in Safe Mode.")
    if not kokoro_onnx_install_supported():
        raise EngineInstallError(
            "This build cannot install Kokoro ONNX automatically (pip is unavailable). "
            "Install it from source with: pip install kokoro-onnx soundfile"
        )

    dest = Path(dest_dir) if dest_dir is not None else kokoro_onnx_pack_dir()
    dest.mkdir(parents=True, exist_ok=True)
    reqs = tuple(requirements) if requirements is not None else _KOKORO_ONNX_REQUIREMENTS
    python_exe = python_executable or sys.executable
    if not python_exe:
        raise EngineInstallError("Could not locate the Python runtime to install into.")

    # An explicit `requirements` override (tests / advanced callers) is used
    # as-is, skipping the bundled-wheelhouse lookup, same as the Vosk pattern.
    wheelhouse = _bundled_wheelhouse_dir("kokoro") if requirements is None else None
    extra_args = ("--no-index", "--find-links", str(wheelhouse)) if wheelhouse is not None else ()

    if progress is not None:
        progress(0.05, "Preparing to install Kokoro ONNX...")
    command = _pip_command(dest, reqs, python_exe, extra_args=extra_args)
    run = runner if runner is not None else _default_runner
    _LOG.info("Kokoro ONNX install: running %s", " ".join(command))
    if progress is not None:
        label = (
            "Installing Kokoro ONNX from the offline bundle..."
            if wheelhouse is not None
            else "Downloading Kokoro ONNX packages (this may take a few minutes)..."
        )
        progress(0.15, label)

    try:
        result = run(command, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("Kokoro ONNX install: pip runner could not start")
        raise EngineInstallError(f"Could not run the installer: {exc}") from exc

    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = _tail(getattr(result, "stderr", "") or getattr(result, "stdout", ""))
        _LOG.error("Kokoro ONNX install failed (pip exit %s). Output tail: %s", returncode, detail)
        raise EngineInstallError(
            f"Kokoro ONNX installation failed (pip exit {returncode}). {detail}"
        )

    if progress is not None:
        progress(0.9, "Finishing up...")
    if str(dest) not in sys.path:
        sys.path.insert(0, str(dest))
    importlib.invalidate_caches()
    if not is_kokoro_onnx_available():
        _LOG.error("Kokoro ONNX installed into %s but the module is not importable", dest)
        raise EngineInstallError(
            "Kokoro ONNX was installed but could not be imported. Try restarting QUILL."
        )
    if progress is not None:
        progress(1.0, "Done.")
    return dest


def mp3_install_supported() -> bool:
    """True when QUILL can install MP3 support on demand (pip must be importable)."""
    return importlib.util.find_spec("pip") is not None


def is_mp3_available() -> bool:
    """True when ``mutagen`` (MP3 chapter markers) is importable (after activation)."""
    return importlib.util.find_spec(_MP3_MODULE) is not None


def install_mp3_support(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    python_executable: str | None = None,
    timeout_seconds: float = _INSTALL_TIMEOUT_S,
    runner: Callable[..., object] | None = None,
) -> Path:
    """Install MP3 chapter-marker support (mutagen) wheel-only into an engine-pack.

    Mirrors :func:`install_kokoro_onnx`: pure-Python and small, activated on
    ``sys.path`` immediately, and prefers the Offline Edition's bundled
    wheelhouse (:func:`_bundled_wheelhouse_dir`) over PyPI when present.
    Raises :class:`EngineInstallError` on Safe Mode, unavailable pip, a
    non-zero pip exit, or if mutagen still cannot import.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise EngineInstallError("Downloading components is disabled in Safe Mode.")
    if not mp3_install_supported():
        raise EngineInstallError(
            "This build cannot install MP3 support automatically (pip is unavailable). "
            "Install it from source with: pip install mutagen"
        )
    dest = Path(dest_dir) if dest_dir is not None else mp3_pack_dir()
    dest.mkdir(parents=True, exist_ok=True)
    python_exe = python_executable or sys.executable
    if not python_exe:
        raise EngineInstallError("Could not locate the Python runtime to install into.")
    wheelhouse = _bundled_wheelhouse_dir("mp3")
    extra_args = ("--no-index", "--find-links", str(wheelhouse)) if wheelhouse is not None else ()
    if progress is not None:
        progress(0.05, "Preparing to install MP3 support...")
    command = _pip_command(dest, _MP3_REQUIREMENTS, python_exe, extra_args=extra_args)
    run = runner if runner is not None else _default_runner
    _LOG.info("MP3 support install: running %s", " ".join(command))
    if progress is not None:
        label = (
            "Installing MP3 support from the offline bundle..."
            if wheelhouse is not None
            else "Downloading MP3 support (mutagen)..."
        )
        progress(0.15, label)
    try:
        result = run(command, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("MP3 support install: pip runner could not start")
        raise EngineInstallError(f"Could not run the installer: {exc}") from exc
    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = _tail(getattr(result, "stderr", "") or getattr(result, "stdout", ""))
        _LOG.error("MP3 support install failed (pip exit %s). Output tail: %s", returncode, detail)
        raise EngineInstallError(
            f"MP3 support installation failed (pip exit {returncode}). {detail}"
        )
    if progress is not None:
        progress(0.9, "Finishing up...")
    if str(dest) not in sys.path:
        sys.path.insert(0, str(dest))
    importlib.invalidate_caches()
    if not is_mp3_available():
        _LOG.error("MP3 support installed into %s but mutagen is not importable", dest)
        raise EngineInstallError(
            "MP3 support was installed but could not be imported. Try restarting QUILL."
        )
    if progress is not None:
        progress(1.0, "Done.")
    return dest


def install_vosk(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    requirements: Sequence[str] | None = None,
    python_executable: str | None = None,
    timeout_seconds: float = _INSTALL_TIMEOUT_S,
    runner: Callable[..., object] | None = None,
) -> Path:
    """Download and install the Vosk engine, returning its pack folder.

    Mirrors :func:`install_faster_whisper` exactly: wheel-only into a
    user-writable engine-pack folder, activated on ``sys.path`` immediately.
    Raises :class:`EngineInstallError` on Safe Mode, unavailable pip, a
    non-zero pip exit, or if the engine still cannot be imported afterward.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise EngineInstallError("Downloading speech engines is disabled in Safe Mode.")
    if not vosk_install_supported():
        raise EngineInstallError(
            "This build cannot install Vosk automatically (pip is unavailable). "
            "Install it from source with: pip install vosk"
        )

    dest = Path(dest_dir) if dest_dir is not None else vosk_pack_dir()
    dest.mkdir(parents=True, exist_ok=True)
    python_exe = python_executable or sys.executable
    if not python_exe:
        raise EngineInstallError("Could not locate the Python runtime to install into.")

    if progress is not None:
        progress(0.05, "Preparing to install Vosk...")

    # An explicit `requirements` override (tests / advanced callers) is used as-is.
    # Otherwise prefer, in order: the Offline Edition's bundled wheelhouse (fully
    # offline, no PyPI at all -- and unlike the assets-v1 wheel below, a `pip
    # download`-built wheelhouse captures vosk's transitive `cffi` dependency too,
    # so --no-index is safe here in a way it never was for the single pinned
    # wheel); then QUILL's pinned assets-v1 wheel (source resilience); then PyPI.
    if requirements is not None:
        reqs: tuple[str, ...] = tuple(requirements)
        extra_args: tuple[str, ...] = ()
    else:
        wheelhouse = _bundled_wheelhouse_dir("vosk")
        if wheelhouse is not None:
            reqs = _VOSK_REQUIREMENTS
            extra_args = ("--no-index", "--find-links", str(wheelhouse))
        else:
            local_wheel = _maybe_fetch_vosk_wheel(progress)
            if local_wheel is not None:
                # Pin vosk to our verified wheel by passing the file path as the
                # requirement -- pip installs exactly that file, not a PyPI-resolved
                # vosk. We deliberately do NOT pass --no-index: vosk depends on
                # ``cffi`` at install time, and under --no-index + --target pip has
                # no source for cffi (not even the base env) without a wheelhouse
                # to supply it, so it fails with "No matching distribution found
                # for cffi". Leaving the index enabled lets the dependency resolve
                # while vosk itself stays pinned to the verified wheel.
                reqs = (str(local_wheel),)
                extra_args = ()
            else:
                reqs = _VOSK_REQUIREMENTS
                extra_args = ()

    command = _pip_command(dest, reqs, python_exe, extra_args=extra_args)
    run = runner if runner is not None else _default_runner
    if progress is not None:
        label = (
            "Installing Vosk from the offline bundle..."
            if "--no-index" in extra_args
            else "Downloading Vosk (this can take a few minutes)..."
        )
        progress(0.15, label)

    try:
        result = run(command, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        raise EngineInstallError(f"Could not run the installer: {exc}") from exc

    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = _tail(getattr(result, "stderr", "") or getattr(result, "stdout", ""))
        raise EngineInstallError(f"Vosk installation failed (pip exit {returncode}). {detail}")

    if progress is not None:
        progress(0.9, "Finishing up...")
    if str(dest) not in sys.path:
        sys.path.insert(0, str(dest))
    importlib.invalidate_caches()
    if not is_vosk_available():
        raise EngineInstallError(
            "Vosk was installed but could not be imported. Try restarting QUILL."
        )
    if progress is not None:
        progress(1.0, "Done.")
    return dest


def _pip_command(
    dest: Path,
    requirements: Sequence[str],
    python_executable: str,
    *,
    extra_args: Sequence[str] = (),
) -> list[str]:
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
        *extra_args,
        "--target",
        str(dest),
        *requirements,
    ]


def _vosk_download_dir() -> Path:
    """Where the verified Vosk wheel is staged before ``pip install --no-index``."""
    return engine_packs_dir() / "_vosk-download"


def _maybe_fetch_vosk_wheel(progress: ProgressCallback | None) -> Path | None:
    """Return a locally-downloaded, SHA-verified Vosk wheel, or ``None`` for PyPI.

    Only the Windows wheel is self-hosted on the assets-v1 release, so non-Windows
    always returns ``None`` (use PyPI). When the asset is not yet pinned (no uploaded
    wheel + SHA) or any fetch step fails, this also returns ``None`` so
    :func:`install_vosk` degrades cleanly to the PyPI path — PyPI is always the backstop.
    """
    if sys.platform != "win32":
        return None
    try:
        from quill.core.release_assets import ASSETS, fetch_file, is_pinned
    except Exception:
        _LOG.warning("Could not import release_assets for the Vosk wheel fetch.", exc_info=True)
        return None
    asset = ASSETS.get("vosk")
    if asset is None or not is_pinned(asset):
        return None
    try:
        return fetch_file(
            "vosk", _vosk_download_dir(), progress=progress, label="Downloading Vosk..."
        )
    except Exception:
        _LOG.warning("Vosk wheel fetch from assets-v1 failed; falling back to PyPI.", exc_info=True)
        return None


def install_faster_whisper(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    requirements: Sequence[str] | None = None,
    python_executable: str | None = None,
    timeout_seconds: float = _INSTALL_TIMEOUT_S,
    runner: Callable[..., object] | None = None,
) -> Path:
    """Download and install the Faster Whisper engine, returning its pack folder.

    Installs wheel-only into a user-writable engine-pack folder and activates it on
    ``sys.path`` so the engine is immediately importable, preferring the Offline
    Edition's bundled wheelhouse (:func:`_bundled_wheelhouse_dir`) over PyPI when
    present. Raises :class:`EngineInstallError` on Safe Mode, an unsupported
    runtime, a non-zero pip exit, or if the engine still cannot be imported
    afterward.

    ``runner`` defaults to :func:`quill.stability.safe_subprocess.run_subprocess_safely`
    (injectable for tests); it must return an object with ``returncode``,
    ``stdout``, and ``stderr`` attributes.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise EngineInstallError("Downloading speech engines is disabled in Safe Mode.")
    if not faster_whisper_install_supported():
        raise EngineInstallError(
            "This build cannot install Faster Whisper automatically (pip is "
            'unavailable). Install it from source with: pip install -e ".[fasterwhisper]".'
        )

    dest = Path(dest_dir) if dest_dir is not None else faster_whisper_pack_dir()
    dest.mkdir(parents=True, exist_ok=True)
    reqs = tuple(requirements) if requirements is not None else _FASTER_WHISPER_REQUIREMENTS
    python_exe = python_executable or sys.executable
    if not python_exe:
        raise EngineInstallError("Could not locate the Python runtime to install into.")

    wheelhouse = _bundled_wheelhouse_dir("faster-whisper") if requirements is None else None
    extra_args = ("--no-index", "--find-links", str(wheelhouse)) if wheelhouse is not None else ()

    if progress is not None:
        progress(0.05, "Preparing to install Faster Whisper...")
    command = _pip_command(dest, reqs, python_exe, extra_args=extra_args)
    run = runner if runner is not None else _default_runner
    if progress is not None:
        label = (
            "Installing Faster Whisper from the offline bundle..."
            if wheelhouse is not None
            else "Downloading Faster Whisper (this can take a few minutes)..."
        )
        progress(0.15, label)

    try:
        result = run(command, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        raise EngineInstallError(f"Could not run the installer: {exc}") from exc

    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = _tail(getattr(result, "stderr", "") or getattr(result, "stdout", ""))
        raise EngineInstallError(
            f"Faster Whisper installation failed (pip exit {returncode}). {detail}"
        )

    if progress is not None:
        progress(0.9, "Finishing up...")
    if str(dest) not in sys.path:
        sys.path.insert(0, str(dest))
    importlib.invalidate_caches()
    if not is_faster_whisper_available():
        raise EngineInstallError(
            "Faster Whisper was installed but could not be imported. Try restarting QUILL."
        )
    if progress is not None:
        progress(1.0, "Done.")
    return dest


def _default_runner(command: Sequence[str], *, timeout_seconds: float) -> object:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely(command, timeout_seconds=timeout_seconds)


def _tail(text: str, *, limit: int = 400) -> str:
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text
