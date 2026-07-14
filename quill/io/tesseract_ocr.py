"""Local Tesseract OCR backend (free-first document conversion, Tier 2).

Tesseract is QUILL's free, offline, **CPU-only** answer for scanned documents:
real OCR for images (and, via :mod:`quill.core.docconvert`, image-based PDFs)
that runs entirely on the user's machine — no upload, no API key, no consent
prompt, no GPU. It complements the zero-install ``Windows.Media.Ocr`` backend
in :mod:`quill.io.ocr` with a cross-platform engine that also reports per-word
confidence, which the free-first router uses to decide when a scan came out
too weak to trust.

The engine binary is a verified downloadable component (see
:mod:`quill.core.tesseract_install`); this module only *discovers* and *runs*
an already-present executable. No ``wx`` imports; subprocess execution goes
through :func:`quill.stability.safe_subprocess.run_subprocess_safely`.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.io.ocr import (
    OcrFailedError,
    OcrLine,
    OcrResult,
    OcrUnavailableError,
)

#: Stable engine id for the local Tesseract backend.
ENGINE_TESSERACT = "tesseract"

#: Default recognition language (Tesseract three-letter code, not BCP-47).
DEFAULT_LANGUAGE = "eng"

_TSV_TIMEOUT_S = 300.0


def managed_tesseract_dir() -> Path:
    """The folder the downloaded Tesseract engine installs into (discovery-searched)."""
    return app_data_dir() / "ocr" / "tesseract"


def discover_tesseract_executable(override: str | None = None) -> Path | None:
    """Locate ``tesseract`` without running anything.

    Search order: an explicit settings override, the QUILL-managed component
    folder, ``PATH``, then the conventional Windows install location. Returns
    ``None`` when no candidate exists so callers can degrade to an honest
    "engine not installed" state.
    """
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate
    managed = managed_tesseract_dir()
    if managed.is_dir():
        for found in sorted(managed.rglob("tesseract.exe")):
            return found
        for found in sorted(managed.rglob("tesseract")):
            if found.is_file():
                return found
    on_path = shutil.which("tesseract")
    if on_path:
        return Path(on_path)
    if sys.platform == "win32":
        conventional = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        if conventional.is_file():
            return conventional
    return None


def tesseract_available(override: str | None = None) -> bool:
    """True when a Tesseract executable can be found right now."""
    return discover_tesseract_executable(override) is not None


@dataclass(slots=True)
class TesseractPageResult:
    """One OCR pass over a single image: text, lines, and mean confidence."""

    text: str
    lines: list[OcrLine]
    mean_confidence: float


def _parse_tsv(payload: str) -> TesseractPageResult:
    """Build line-grouped text + confidences from Tesseract's TSV output.

    TSV rows at level 5 are words carrying ``conf`` (0-100; -1 for non-text).
    Words are grouped into lines by (page, block, paragraph, line); paragraphs
    are separated by a blank line so headings and body text stay distinct for
    a screen-reader listener.
    """
    lines: list[OcrLine] = []
    rendered: list[str] = []
    confidences: list[float] = []
    current_key: tuple[str, str, str, str] | None = None
    current_par: tuple[str, str, str] | None = None
    words: list[str] = []
    word_confs: list[float] = []

    def _flush() -> None:
        nonlocal words, word_confs
        if not words:
            return
        text = " ".join(words)
        conf = sum(word_confs) / len(word_confs) if word_confs else -1.0
        lines.append(OcrLine(text=text, confidence=conf))
        rendered.append(text)
        if word_confs:
            confidences.extend(word_confs)
        words = []
        word_confs = []

    rows = payload.splitlines()
    for row in rows[1:]:  # skip the header row
        columns = row.split("\t")
        if len(columns) < 12:
            continue
        level = columns[0]
        if level != "5":
            continue
        word = columns[11].strip()
        if not word:
            continue
        key = (columns[1], columns[2], columns[3], columns[4])
        par = (columns[1], columns[2], columns[3])
        if current_key is not None and key != current_key:
            _flush()
            if current_par is not None and par != current_par:
                rendered.append("")
        current_key = key
        current_par = par
        words.append(word)
        try:
            conf = float(columns[10])
        except ValueError:
            conf = -1.0
        if conf >= 0.0:
            word_confs.append(conf)
    _flush()

    text = "\n".join(rendered).strip()
    mean = sum(confidences) / len(confidences) if confidences else -1.0
    return TesseractPageResult(
        text=text + "\n" if text else "",
        lines=lines,
        mean_confidence=mean,
    )


def ocr_image_with_tesseract(
    path: Path,
    language: str = DEFAULT_LANGUAGE,
    *,
    executable: Path | None = None,
    timeout_seconds: float = _TSV_TIMEOUT_S,
) -> OcrResult:
    """Recognize text in a single image with the local Tesseract engine.

    Raises :class:`OcrUnavailableError` when no engine is installed and
    :class:`OcrFailedError` when the engine runs but fails. The result carries
    per-line confidence so the caller can gauge scan quality.
    """
    from quill.stability.safe_subprocess import run_subprocess_safely

    exe = executable or discover_tesseract_executable()
    if exe is None:
        raise OcrUnavailableError(
            "The local Tesseract OCR engine is not installed. "
            "Install it from Tools > OCR and Document Conversion."
        )
    completed = run_subprocess_safely(
        [str(exe), str(path), "stdout", "-l", language or DEFAULT_LANGUAGE, "tsv"],
        timeout_seconds=timeout_seconds,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()
        raise OcrFailedError(
            "Tesseract could not read this image" + (f": {detail[-1]}" if detail else ".")
        )
    page = _parse_tsv(completed.stdout or "")
    return OcrResult(
        text=page.text,
        engine=ENGINE_TESSERACT,
        executable=str(exe),
        language=language or DEFAULT_LANGUAGE,
        lines=page.lines,
    )


__all__ = [
    "DEFAULT_LANGUAGE",
    "ENGINE_TESSERACT",
    "TesseractPageResult",
    "discover_tesseract_executable",
    "managed_tesseract_dir",
    "ocr_image_with_tesseract",
    "tesseract_available",
]
