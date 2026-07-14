"""Dictation control for QUILL.

**What this does today, honestly:** on Windows, dictation toggles the operating
system's built-in dictation panel (the Win+H experience) via
``launch_windows_dictation``. QUILL does not yet capture or transcribe audio
itself. The ``engine``/``model``/``language`` fields on :class:`DictationSettings`
and the ``list_dictation_devices`` helper are forward-looking placeholders from
the offline speech engine work (issue #617); the controller currently ignores
them and always drives the OS panel. Keeping this module truthful — rather than
pretending a local vosk/whisper recognizer is wired up — is deliberate (Speech
wave S0).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

try:  # pragma: no cover - Windows-only runtime hook
    # `launch_windows_dictation` is set to the real Windows shell
    # launcher when running on Windows. On macOS/Linux the import
    # raises ImportError and we fall back to ``None`` so the public
    # methods return a clean ``DictationUnavailableError`` instead of
    # crashing at import time. Do not assume the symbol exists outside
    # Windows; gate every call on ``launch_windows_dictation is not None``.
    from quill.platform.windows.dictation import (
        launch_windows_dictation as _launch_windows_dictation,
    )

    launch_windows_dictation: Callable[[], None] | None = _launch_windows_dictation
except ImportError:  # pragma: no cover - non-Windows fallback
    launch_windows_dictation = None


@dataclass(frozen=True, slots=True)
class DictationSettings:
    """Dictation configuration.

    ``engine`` is one of ``"offline"`` / ``"windows"`` / ``"cloud"`` going
    forward. Only ``"windows"`` is functional today; ``"offline"`` and
    ``"cloud"`` are reserved for the #617 provider engine. The controller
    currently launches the OS dictation panel regardless of these fields.
    """

    engine: str = "windows"
    language: str = "en-US"
    model: str = "default"
    device_index: int | None = None


class DictationUnavailableError(RuntimeError):
    pass


class DictationController:
    def __init__(self) -> None:
        self._state = "idle"
        self._stopper: Callable[..., None] | None = None
        self._segments: list[str] = []

    @property
    def state(self) -> str:
        return self._state

    def start(
        self,
        settings: DictationSettings,
        *,
        on_state_change: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        if launch_windows_dictation is None:
            raise DictationUnavailableError("Windows dictation is only available on Windows")
        try:
            launch_windows_dictation()
        except OSError as error:
            if on_error is not None:
                on_error(str(error))
            raise DictationUnavailableError(str(error)) from error
        self._state = "listening"

    def stop(self, *, on_state_change: Callable[[str], None] | None = None) -> str:
        if self._state == "listening" and launch_windows_dictation is not None:
            try:
                launch_windows_dictation()
            except OSError:
                pass
        self._state = "idle"
        transcript = "".join(self._segments).strip()
        self._segments.clear()
        if on_state_change is not None:
            on_state_change(self._state)
        return transcript


def list_dictation_devices() -> list[str]:
    """Return available microphone device names.

    Placeholder until in-app audio capture lands with the offline speech engine
    (#617, Speech wave S3). Today dictation uses the OS panel, which manages its
    own device selection, so this returns an empty list.
    """
    return []
