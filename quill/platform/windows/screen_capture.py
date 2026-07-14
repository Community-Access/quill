"""Image capture sources for OCR (OCR-3): clipboard and screen.

Windows-only, fully offline helpers that produce a temporary PNG path which the
existing :func:`quill.io.ocr.ocr_image` pipeline can consume unchanged. No
``wx`` imports: capturing the clipboard image, the whole screen, or the active
window is platform work, while the recognition and review surfaces stay in
``quill/io`` and ``quill/ui`` respectively.

Both ``Pillow`` (``PIL.ImageGrab``) and, for the active-window rectangle,
``pywin32`` (``win32gui``) are required. When either is missing, or the call
runs off Windows, the helpers raise :class:`ScreenCaptureError` with a clear,
announce-ready message instead of failing obscurely.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Literal

ScreenTarget = Literal["screen", "active_window"]


class ScreenCaptureError(RuntimeError):
    """Raised when a clipboard or screen capture cannot be completed."""


class ClipboardImageEmpty(ScreenCaptureError):
    """Raised when the clipboard holds no image to recognize."""


def _unsupported_message(action: str) -> str:
    """Explain *why* capture is unavailable on macOS, not just that it is (#5).

    macOS screen capture is gated behind a separate Screen Recording TCC
    permission and is not yet wired into QUILL. Pointing the user at the system
    screenshot shortcuts + the OCR import path reads as a deliberate gap with a
    workaround, not a bare omission.
    """
    return (
        f"{action} is only available on Windows. On macOS, screen capture is gated "
        "behind the Screen Recording permission (System Settings > Privacy & "
        "Security > Screen Recording) and is not yet wired into QUILL. Use the "
        "system screenshot shortcuts (Cmd+Shift+3/4/5), then OCR the saved file via "
        "File > Import."
    )


def _new_capture_path(dest_dir: Path, prefix: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{prefix}-{uuid.uuid4().hex}.png"


def capture_clipboard_image(dest_dir: Path) -> Path:
    """Save the clipboard image to a PNG under ``dest_dir`` and return its path.

    Accepts either a bitmap on the clipboard (for example from the Snipping
    Tool or a copied screenshot) or a single copied image *file*. Raises
    :class:`ClipboardImageEmpty` when the clipboard holds no usable image, and
    :class:`ScreenCaptureError` when Pillow is unavailable or the grab fails.
    """
    if os.name != "nt":  # pragma: no cover - Windows-only feature surface
        raise ScreenCaptureError(_unsupported_message("Clipboard image capture"))
    try:
        from PIL import ImageGrab
    except ImportError as exc:  # pragma: no cover - Pillow is a bundled dependency
        raise ScreenCaptureError(
            "Pillow is required for clipboard image capture but is not installed."
        ) from exc

    grabbed = ImageGrab.grabclipboard()
    if grabbed is None:
        raise ClipboardImageEmpty("The clipboard does not contain an image to recognize.")

    # A copied image file comes back as a list of paths; OCR the first image.
    if isinstance(grabbed, list):
        image_files = [Path(item) for item in grabbed]
        first_image = next(
            (
                candidate
                for candidate in image_files
                if candidate.suffix.lower()
                in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}
            ),
            None,
        )
        if first_image is None or not first_image.is_file():
            raise ClipboardImageEmpty(
                "The clipboard holds files, but none of them are images to recognize."
            )
        return first_image

    dest = _new_capture_path(dest_dir, "clipboard-ocr")
    try:
        grabbed.convert("RGB").save(dest, format="PNG")
    except OSError as exc:
        raise ScreenCaptureError(f"Could not save the clipboard image: {exc}") from exc
    return dest


def _active_window_bbox() -> tuple[int, int, int, int]:
    try:
        import win32gui
    except ImportError as exc:  # pragma: no cover - pywin32 is a bundled dependency
        raise ScreenCaptureError(
            "pywin32 is required to capture the active window but is not installed."
        ) from exc

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        raise ScreenCaptureError("No active window was found to capture.")
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    if right <= left or bottom <= top:
        raise ScreenCaptureError("The active window has no visible area to capture.")
    return left, top, right, bottom


def capture_screen(dest_dir: Path, target: ScreenTarget = "screen") -> Path:
    """Capture the whole screen or the active window to a PNG under ``dest_dir``.

    ``target`` is ``"screen"`` (the full virtual desktop, all monitors) or
    ``"active_window"`` (the foreground window's rectangle). Returns the saved
    PNG path; raises :class:`ScreenCaptureError` on any failure.
    """
    if os.name != "nt":  # pragma: no cover - Windows-only feature surface
        raise ScreenCaptureError(_unsupported_message("Screen capture"))
    try:
        from PIL import ImageGrab
    except ImportError as exc:  # pragma: no cover - Pillow is a bundled dependency
        raise ScreenCaptureError(
            "Pillow is required for screen capture but is not installed."
        ) from exc

    if target == "active_window":
        bbox = _active_window_bbox()
        image = ImageGrab.grab(bbox=bbox)
    else:
        image = ImageGrab.grab(all_screens=True)

    dest = _new_capture_path(dest_dir, f"{target}-ocr")
    try:
        image.convert("RGB").save(dest, format="PNG")
    except OSError as exc:
        raise ScreenCaptureError(f"Could not save the captured image: {exc}") from exc
    return dest


__all__ = [
    "ClipboardImageEmpty",
    "ScreenCaptureError",
    "ScreenTarget",
    "capture_clipboard_image",
    "capture_screen",
]
