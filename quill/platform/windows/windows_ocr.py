"""Native Windows OCR recognition via ``Windows.Media.Ocr`` (OCR-1).

H-3-platform: the winrt imports are now wrapped in a try/except so this
module can be imported on machines without the winrt packages installed.  The
public entry point ``recognize_with_windows_ocr`` raises
:class:`OcrUnavailableError` at *call* time rather than failing at *import*
time.  The caller (:func:`quill.io.ocr._import_windows_ocr`) already handles
``Exception`` during import, but making the module itself importable means
``import``-time failures in CI or on non-Windows dev boxes no longer cascade
into unrelated test failures. No ``wx`` imports.

The backend is the Microsoft pywinrt ``winrt-*`` namespace packages, which
ship wheels for current CPython (including 3.13). They replace the legacy
``winsdk`` monolith, whose wheels stopped at cp312; the projected API
(class and async-method names) is identical, so only the import roots differ.
"""

from __future__ import annotations

from pathlib import Path

try:
    from winrt.windows.globalization import Language  # type: ignore[import-not-found]
    from winrt.windows.graphics.imaging import (  # type: ignore[import-not-found]
        BitmapDecoder,
    )
    from winrt.windows.media.ocr import OcrEngine  # type: ignore[import-not-found]
    from winrt.windows.storage import (  # type: ignore[import-not-found]
        FileAccessMode,
        StorageFile,
    )

    _WINRT_AVAILABLE = True
except ImportError:
    _WINRT_AVAILABLE = False
    Language = BitmapDecoder = OcrEngine = FileAccessMode = StorageFile = None  # type: ignore[assignment,misc]

from quill.io.ocr import OcrLine


def recognize_with_windows_ocr(
    path: Path, language: str | None
) -> tuple[str, list[OcrLine]]:  # pragma: no cover - requires Windows + winrt
    """Recognize text in ``path`` with the native Windows OCR engine.

    Returns the joined text and per-line :class:`OcrLine` records.  Raises
    :class:`~quill.io.ocr.OcrUnavailableError` when the ``winrt`` OCR packages
    are not installed so callers degrade gracefully instead of hitting an
    ``AttributeError`` on a ``None`` name.
    """
    if not _WINRT_AVAILABLE:
        from quill.io.ocr import OcrUnavailableError

        raise OcrUnavailableError(
            "The Windows OCR (winrt) packages are not installed. Install them with: "
            "pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging "
            "winrt-Windows.Globalization winrt-Windows.Storage"
        )

    import asyncio

    async def _run() -> tuple[str, list[OcrLine]]:
        storage_file = await StorageFile.get_file_from_path_async(str(path))
        stream = await storage_file.open_async(FileAccessMode.READ)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        if language:
            engine = OcrEngine.try_create_from_language(Language(language))
        else:
            engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            from quill.io.ocr import OcrUnavailableError

            raise OcrUnavailableError(
                "No Windows OCR language pack is installed for the requested language."
            )
        ocr_result = await engine.recognize_async(bitmap)
        lines = [OcrLine(text=line.text, confidence=-1.0) for line in ocr_result.lines]
        joined = "\n".join(line.text for line in lines)
        return joined, lines

    return asyncio.run(_run())


__all__ = ["recognize_with_windows_ocr"]
