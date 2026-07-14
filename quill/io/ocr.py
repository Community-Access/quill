"""Native Windows OCR (image-to-text) engine (OCR-1).

This module is UI-framework-agnostic (no ``wx``). It exposes a small backend
contract so text can be pulled from images fully offline through the native
``Windows.Media.Ocr`` runtime (zero-install), with a shared :class:`OcrResult`
that carries the recognized text plus per-line confidence. When the native
engine is unavailable the module raises :class:`OcrUnavailableError` with a
clear message rather than failing silently.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class OcrUnavailableError(RuntimeError):
    pass


class OcrFailedError(RuntimeError):
    pass


class OcrCancelledError(RuntimeError):
    pass


#: The single built-in OCR engine id (native ``Windows.Media.Ocr``).
ENGINE_WINDOWS = "windows"

#: Lines whose confidence falls below this (on a 0-100 scale) are flagged for
#: review in the OCR review surface (OCR-4). A confidence of -1 means the
#: backend did not report one and is never treated as low.
LOW_CONFIDENCE_THRESHOLD = 60.0


@dataclass(slots=True)
class OcrLine:
    """One recognized line of text with an optional confidence (0-100)."""

    text: str
    confidence: float = -1.0

    @property
    def is_low_confidence(self) -> bool:
        return 0.0 <= self.confidence < LOW_CONFIDENCE_THRESHOLD


@dataclass(slots=True)
class OcrResult:
    text: str
    engine: str
    executable: str = ""
    language: str = ""
    lines: list[OcrLine] = field(default_factory=list)

    @property
    def low_confidence_lines(self) -> list[OcrLine]:
        """Recognized lines flagged below the confidence threshold (OCR-4)."""
        return [line for line in self.lines if line.is_low_confidence]


# Progress/cancel callbacks shared by every backend.
ProgressFn = Callable[[str], None]
CancelFn = Callable[[], bool]


class OcrBackend(Protocol):
    """The contract every OCR backend implements.

    ``backend_id`` is the stable engine id (``windows``); ``is_available``
    reports whether the backend can run on this machine right now (its runtime
    is present); ``run`` performs recognition.
    """

    backend_id: str

    def is_available(self) -> bool: ...

    def run(
        self,
        path: Path,
        language: str | None,
        on_progress: ProgressFn | None,
        cancel_requested: CancelFn | None,
    ) -> OcrResult: ...


@dataclass(slots=True)
class WindowsOcrBackend:
    """Native ``Windows.Media.Ocr`` backend, fully offline and zero-install (OCR-1).

    Recognition uses the WinRT OCR engine via the ``winrt-*`` packages when present.
    On a non-Windows machine or without the projection installed,
    :meth:`is_available` returns ``False`` so selection falls back cleanly.
    """

    backend_id: str = ENGINE_WINDOWS

    def is_available(self) -> bool:
        return _import_windows_ocr() is not None

    def run(
        self,
        path: Path,
        language: str | None,
        on_progress: ProgressFn | None,
        cancel_requested: CancelFn | None,
    ) -> OcrResult:
        recognize = _import_windows_ocr()
        if recognize is None:
            raise OcrUnavailableError(
                "The native Windows OCR engine is not available on this machine. "
                "Open OCR setup to choose an engine."
            )
        if on_progress is not None:
            on_progress("Running OCR...")
        if cancel_requested is not None and cancel_requested():
            raise OcrCancelledError("OCR cancelled.")
        text, lines = recognize(path, language)
        return OcrResult(
            text=text.rstrip() + "\n" if text else "",
            engine=ENGINE_WINDOWS,
            executable="",
            language=language or "",
            lines=lines,
        )


def _import_windows_ocr() -> Callable[[Path, str | None], tuple[str, list[OcrLine]]] | None:
    """Return a callable that runs WinRT OCR, or ``None`` when unavailable.

    Kept isolated so the rest of the module never imports a platform-only
    dependency at module load and remains testable on any OS.
    """
    try:  # pragma: no cover - platform/runtime dependent
        from quill.platform.windows.windows_ocr import recognize_with_windows_ocr
    except ImportError:
        return None
    return recognize_with_windows_ocr  # pragma: no cover


def default_backends() -> dict[str, OcrBackend]:
    """The built-in OCR backends keyed by engine id."""
    return {
        ENGINE_WINDOWS: WindowsOcrBackend(),
    }


def available_engines(backends: Mapping[str, OcrBackend] | None = None) -> list[str]:
    """Engine ids whose backend can run on this machine right now."""
    registry = dict(backends) if backends is not None else default_backends()
    return [engine for engine, backend in registry.items() if backend.is_available()]


def ocr_image(
    path: Path,
    language: str | None = None,
    on_progress: ProgressFn | None = None,
    cancel_requested: CancelFn | None = None,
    backends: Mapping[str, OcrBackend] | None = None,
) -> OcrResult:
    """Recognize text in ``path`` using the native Windows OCR backend.

    ``language`` is an optional BCP-47 tag (for example ``en-US``); when
    omitted the engine uses the system's recognition languages. Raises
    :class:`OcrUnavailableError` when the native engine is not present on this
    machine. The backend performs recognition and returns an
    :class:`OcrResult` with text and per-line confidence.
    """
    registry = dict(backends) if backends is not None else default_backends()
    backend = registry.get(ENGINE_WINDOWS)
    if backend is None or not backend.is_available():
        raise OcrUnavailableError("The native Windows OCR engine is not available on this machine.")
    return backend.run(path, language, on_progress, cancel_requested)


def render_ocr_review(result: OcrResult) -> str:
    """Render an OCR result as plain text for the accessible review surface (OCR-4).

    The header names the engine and language and notes how many lines fell
    below the confidence threshold; low-confidence lines are marked inline with
    a leading flag so a screen-reader user can find them quickly.
    """
    header_bits = [f"Engine: {result.engine or 'unknown'}"]
    if result.language:
        header_bits.append(f"Language: {result.language}")
    low = result.low_confidence_lines
    if result.lines:
        if low:
            header_bits.append(f"{len(low)} of {len(result.lines)} lines need review")
        else:
            header_bits.append("All lines recognized with good confidence")
    header = " | ".join(header_bits)
    if result.lines:
        body_lines = [
            f"[review {line.confidence:.0f}%] {line.text}" if line.is_low_confidence else line.text
            for line in result.lines
        ]
    else:
        body_lines = result.text.splitlines()
    return header + "\n\n" + "\n".join(body_lines)


__all__ = [
    "ENGINE_WINDOWS",
    "LOW_CONFIDENCE_THRESHOLD",
    "CancelFn",
    "OcrBackend",
    "OcrCancelledError",
    "OcrFailedError",
    "OcrLine",
    "OcrResult",
    "OcrUnavailableError",
    "ProgressFn",
    "WindowsOcrBackend",
    "available_engines",
    "default_backends",
    "ocr_image",
    "render_ocr_review",
]
