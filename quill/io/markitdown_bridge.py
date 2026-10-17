"""The one place QUILL calls MarkItDown, and the two things it must not do.

**It must not be asked about a format it has no converter for.** MarkItDown
reads Word (.docx), PowerPoint (.pptx), Excel and PDF, but not the old binary
Word and PowerPoint formats (.doc, .ppt). Importing it costs 11 to 14 seconds
from a source checkout on a cold start (it loads pandas, pdfminer, openpyxl,
python-pptx and the Magika model before it converts anything), and for a .doc
that whole wait ended in "no converter attempted a conversion" -- after which
the open fell through to LibreOffice anyway. Measured 2026-10-16: a .doc took
11.6 s to reach its answer and now takes the time to look for LibreOffice
(``docs/design/2026-10-16-editor-completion-measurements.md``).

**It must not let MarkItDown's own exceptions escape.** Callers degrade on
``ImportError``, ``ValueError`` and ``RuntimeError`` -- to python-docx, to
LibreOffice, to a sentence naming what is missing. MarkItDown raises its own
``MarkItDownException`` family, which none of them caught, so a file it could
not read reached the person as a raw library message instead of the fallback
that was waiting for it. Those now arrive as ``ValueError``.
"""

from __future__ import annotations

from pathlib import Path

#: Formats MarkItDown has no converter for. Asking costs the full import and
#: always fails, so the bridge answers straight away and the caller's next
#: route (LibreOffice, for these) runs without the wait.
MARKITDOWN_CANNOT_READ: frozenset[str] = frozenset({".doc", ".ppt"})


def convert_with_markitdown(path: Path) -> str:
    if Path(path).suffix.lower() in MARKITDOWN_CANNOT_READ:
        raise ValueError(f"MarkItDown has no converter for {Path(path).suffix} files")
    try:
        from markitdown import MarkItDown  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("markitdown not available") from exc

    converter = MarkItDown(enable_plugins=False)
    try:
        result = converter.convert(str(path))
    except (ImportError, ValueError, RuntimeError, OSError):
        raise
    except Exception as exc:  # noqa: BLE001 - MarkItDown's own exception family
        raise ValueError(f"MarkItDown could not read {Path(path).name}: {exc}") from exc
    text = result.text_content or ""
    if not text.strip():
        raise ValueError(f"MarkItDown produced empty output for {path.name}")
    return text.rstrip() + "\n"
