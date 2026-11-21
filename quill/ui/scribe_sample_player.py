"""Play a Scribe voice sample (PRD 7.3, Play Sample), through Windows' own MCI.

The sample is a short MP3 on Scribe's site that needs no token; the client
fetches it (the reviewed REST egress site) into a temporary file, and this
plays it through the default audio output with ``mciSendStringW``, which
reads MP3 on every supported Windows without another package. Off Windows,
or if MCI refuses, :meth:`SamplePlayer.play` returns False and the dialog
says the sample could not be played.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ALIAS = "quill_scribe_sample"


def _mci(command: str) -> tuple[int, str]:
    if sys.platform != "win32":
        return 1, ""
    import ctypes

    buffer = ctypes.create_unicode_buffer(128)
    winmm = ctypes.windll.winmm  # type: ignore[attr-defined]
    code = int(winmm.mciSendStringW(command, buffer, 128, None))
    return code, buffer.value


class SamplePlayer:
    def __init__(self) -> None:
        self._file: Path | None = None

    def play(self, data: bytes) -> bool:
        self.stop()
        handle = tempfile.NamedTemporaryFile(prefix="scribe-sample-", suffix=".mp3", delete=False)
        with handle:
            handle.write(data)
        self._file = Path(handle.name)
        code, _ = _mci(f'open "{self._file}" type mpegvideo alias {_ALIAS}')
        if code != 0:
            self._cleanup()
            return False
        code, _ = _mci(f"play {_ALIAS}")
        return code == 0

    def is_playing(self) -> bool:
        code, mode = _mci(f"status {_ALIAS} mode")
        return code == 0 and mode.lower() == "playing"

    def stop(self) -> None:
        _mci(f"stop {_ALIAS}")
        _mci(f"close {_ALIAS}")
        self._cleanup()

    def _cleanup(self) -> None:
        if self._file is not None:
            try:
                self._file.unlink(missing_ok=True)
            except OSError:
                pass
            self._file = None


__all__ = ["SamplePlayer"]
