"""Optional on-demand install of the free PDF/Office text-extraction pipeline
(MarkItDown + pdfplumber + pypdf, the ``pdf-ocr`` pyproject extra).

These were briefly a base runtime dependency (#909: a build had shipped with
neither the old ``[pages]`` extra nor a base dependency, so a clean install had
no PDF/Office text extractor at all and Import -> PDF/OCR failed out of the
box). They are pure-Python, pip-installable, wheel-only packages -- the same
shape as :mod:`quill.core.speech.engine_install`'s MP3-support pack -- so the
honest #909 fix is to make them a genuine one-click download via Help >
Download Optional Components, not to force them onto every install regardless
of whether that install ever touches a PDF or Office document.

The pack lands in ``<app data>/engine-packs/pdf-ocr`` and that folder is added
to ``sys.path`` (see :func:`activate_pdf_ocr_pack`, called once at startup),
so ``importlib.util.find_spec('markitdown')`` (etc.) then lights the pipeline
up in ``quill/io/pdf.py``/``quill/io/docconvert.py`` exactly as a source
install would.

Safety mirrors every other on-demand pack: blocked in Safe Mode, on an
explicit user action only, wheel-only, the only network touch is the
runtime's own pip reaching PyPI (documented in the network-egress audit).
wx-free.
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
from quill.core.paths import app_data_dir

ProgressCallback = Callable[[float, str], None]

_LOG = logging.getLogger(__name__)

#: Subdirectory under the app-data dir's engine-packs root.
_PDF_OCR_PACK = "pdf-ocr"

#: The modules whose presence marks the pack as usable. markitdown is the
#: Tier-1 Office+PDF converter; pdfplumber/pypdf are the PDF text floor
#: quill/io/pdf.py falls back through. All three install together (they are
#: one pyproject extra), but importability is checked per-module so a partial
#: environment is reported precisely, not as an opaque "not installed."
_PDF_OCR_MODULES: tuple[str, ...] = ("markitdown", "pdfplumber", "pypdf")

# Kept in sync with the ``pdf-ocr`` extra in pyproject.toml.
_PDF_OCR_REQUIREMENTS: tuple[str, ...] = (
    "markitdown[docx,pptx,xlsx,xls,pdf]>=0.1.6",
    "pdfplumber>=0.11.9",
    "pypdf>=6.11.0",
)

_INSTALL_TIMEOUT_S = 1800.0


class PdfOcrInstallError(CodedError):
    """Raised when the optional PDF/Office text-extraction download/install fails."""

    code = "QUILL-IO-PDF-OCR-INSTALL"


def pdf_ocr_pack_dir() -> Path:
    """The folder the on-demand PDF/Office extraction pack installs into."""
    return app_data_dir() / "engine-packs" / _PDF_OCR_PACK


def activate_pdf_ocr_pack() -> None:
    """Prepend the pdf-ocr pack folder to ``sys.path`` if installed (idempotent).

    Called once early in startup so a pack the user installed on demand is
    importable for the rest of the session. Safe to call when no pack exists.
    """
    pack = pdf_ocr_pack_dir()
    try:
        if not pack.is_dir() or not any(pack.iterdir()):
            return
    except OSError:
        return
    entry = str(pack)
    if entry not in sys.path:
        sys.path.insert(0, entry)
        importlib.invalidate_caches()


def pdf_ocr_install_supported() -> bool:
    """True when QUILL can install the pack on demand (pip must be importable)."""
    return importlib.util.find_spec("pip") is not None


def is_pdf_ocr_available() -> bool:
    """True when every module the pack provides is importable (after activation)."""
    return all(importlib.util.find_spec(name) is not None for name in _PDF_OCR_MODULES)


def missing_pdf_ocr_modules() -> tuple[str, ...]:
    """Which of the pack's modules are not importable right now."""
    return tuple(name for name in _PDF_OCR_MODULES if importlib.util.find_spec(name) is None)


def install_pdf_ocr_support(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    python_executable: str | None = None,
    timeout_seconds: float = _INSTALL_TIMEOUT_S,
    runner: Callable[..., object] | None = None,
) -> Path:
    """Install the free PDF/Office text-extraction pack, wheel-only.

    Mirrors ``engine_install.install_mp3_support``: pure-Python and small,
    activated on ``sys.path`` immediately. Raises :class:`PdfOcrInstallError`
    on Safe Mode, unavailable pip, a non-zero pip exit, or if the pack still
    cannot import afterward.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise PdfOcrInstallError("Downloading components is disabled in Safe Mode.")
    if not pdf_ocr_install_supported():
        raise PdfOcrInstallError(
            "This build cannot install PDF/Office text extraction automatically "
            "(pip is unavailable). Install it from source with: "
            "pip install markitdown[docx,pptx,xlsx,xls,pdf] pdfplumber pypdf"
        )
    dest = Path(dest_dir) if dest_dir is not None else pdf_ocr_pack_dir()
    dest.mkdir(parents=True, exist_ok=True)
    python_exe = python_executable or sys.executable
    if not python_exe:
        raise PdfOcrInstallError("Could not locate the Python runtime to install into.")
    if progress is not None:
        progress(0.05, "Preparing to install PDF/Office text extraction...")
    command = _pip_command(dest, _PDF_OCR_REQUIREMENTS, python_exe)
    run = runner if runner is not None else _default_runner
    _LOG.info("PDF/Office text extraction install: running %s", " ".join(command))
    if progress is not None:
        progress(0.15, "Downloading PDF/Office text extraction (MarkItDown, pdfplumber, pypdf)...")
    try:
        result = run(command, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("PDF/Office text extraction install: pip runner could not start")
        raise PdfOcrInstallError(f"Could not run the installer: {exc}") from exc
    returncode = int(getattr(result, "returncode", 1))
    if returncode != 0:
        detail = _tail(getattr(result, "stderr", "") or getattr(result, "stdout", ""))
        _LOG.error(
            "PDF/Office text extraction install failed (pip exit %s). Output tail: %s",
            returncode,
            detail,
        )
        raise PdfOcrInstallError(
            f"PDF/Office text extraction installation failed (pip exit {returncode}). {detail}"
        )
    if progress is not None:
        progress(0.9, "Finishing up...")
    if str(dest) not in sys.path:
        sys.path.insert(0, str(dest))
    importlib.invalidate_caches()
    if not is_pdf_ocr_available():
        still_missing = missing_pdf_ocr_modules()
        _LOG.error(
            "PDF/Office text extraction installed into %s but still missing: %s",
            dest,
            ", ".join(still_missing),
        )
        raise PdfOcrInstallError(
            "PDF/Office text extraction was installed but could not be fully imported "
            f"(still missing: {', '.join(still_missing)}). Try restarting QUILL."
        )
    if progress is not None:
        progress(1.0, "Done.")
    return dest


def _pip_command(dest: Path, requirements: Sequence[str], python_executable: str) -> list[str]:
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
        *requirements,
    ]


def _default_runner(command: Sequence[str], *, timeout_seconds: float) -> object:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely(command, timeout_seconds=timeout_seconds)


def _tail(text: str, *, limit: int = 400) -> str:
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text
