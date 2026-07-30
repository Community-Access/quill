"""A content-voice player for the listen queue (plan xxx.md 3.21).

Implements the :class:`~quill_social.services.listen.Player` protocol on Windows
SAPI 5 via ``comtypes`` -- a *separate audio path* from the screen reader, so the
article voice never double-speaks NVDA/JAWS. The neural engines (Kokoro/Piper/
WinRT OneCore) land when this merges onto the main app's ``ReadAloudController``;
SAPI 5 is the always-present floor.

Design points:
- ``available()`` probes for comtypes + a usable SpVoice without speaking, so the
  UI can offer a clear "not available" message instead of failing.
- Narration runs on a daemon thread (a blocking ``Speak``); ``stop`` purges it.
- A generation counter guards the completion callback so a stopped/superseded
  item never fires ``on_finished`` and resurrects the queue.
- ``call_soon`` marshals the completion callback back onto the UI thread
  (``wx.CallAfter`` in the shell) so auto-advance touches wx safely; the module
  itself stays wx-free.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

# SAPI ISpeechVoice.Speak flags.
_SVSF_DEFAULT = 0
_SVSF_ASYNC = 1
_SVSF_PURGE_BEFORE_SPEAK = 2


class Sapi5Player:
    """Windows SAPI 5 content voice."""

    def __init__(self, *, call_soon: Callable[[Callable[[], None]], None] | None = None) -> None:
        import comtypes.client

        self._voice = comtypes.client.CreateObject("SAPI.SpVoice")
        self._call_soon = call_soon or (lambda fn: fn())
        self._thread: threading.Thread | None = None
        self._gen = 0
        self._stopped = True

    @classmethod
    def available(cls) -> bool:
        try:
            import comtypes.client

            comtypes.client.CreateObject("SAPI.SpVoice")
            return True
        except Exception:  # noqa: BLE001 - any import/COM failure means unavailable
            return False

    def speak(self, text: str, on_finished: Callable[[], None]) -> None:
        self.stop()
        self._stopped = False
        self._gen += 1
        gen = self._gen

        def run() -> None:
            try:
                self._voice.Speak(text, _SVSF_DEFAULT)  # blocks until spoken
            except Exception:  # noqa: BLE001 - a speech failure must not crash
                pass
            if gen == self._gen and not self._stopped:
                self._call_soon(on_finished)

        self._thread = threading.Thread(target=run, name="quill-listen-tts", daemon=True)
        self._thread.start()

    def pause(self) -> None:
        try:
            self._voice.Pause()
        except Exception:  # noqa: BLE001
            pass

    def resume(self) -> None:
        try:
            self._voice.Resume()
        except Exception:  # noqa: BLE001
            pass

    def stop(self) -> None:
        self._stopped = True
        self._gen += 1
        try:
            # Purge the current utterance; async so this returns immediately.
            self._voice.Speak("", _SVSF_ASYNC | _SVSF_PURGE_BEFORE_SPEAK)
        except Exception:  # noqa: BLE001
            pass
