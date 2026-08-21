"""Play a few seconds either side of a chapter mark, without moving the playhead.

The whole value of a preview is that it costs the listener **nothing**: they can
check a mark, decide it is wrong, fix it, and check again, and the episode they
were actually listening to has not moved. A preview that seeks the main player
would make checking more expensive than accepting -- and a feature people do not
use is the same as one that does not exist.

So this never touches the player. The requested slice is cut out with ffmpeg into
memory and played through the sound backend that already exists for earcons. A
twenty-second slice is about 640 KB of 16-bit mono, which is nothing, and cutting
it takes a fraction of a second because ffmpeg seeks before it decodes.

The cut runs on a worker thread: it is fast, but "fast" is not "instant", and the
UI thread owns the dialog the listener is arrowing through.

Lives under ``quill/ui/media`` rather than under either app: Cast previews a
worked-out chapter in an episode and Radio previews a mark in a recording, and
those are the same operation on the same kind of file. One copy, so a fix to the
seek behaviour reaches both.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any

#: Preview audio is mono at this rate. Speech, checked for a boundary -- the
#: question is "does the programme turn here", and it does not need stereo.
_SAMPLE_RATE = 22050

#: Guard against a pathological request: nobody previews four minutes.
_MAX_PREVIEW_MS = 120_000


class ChapterPreviewPlayer:
    """Plays ranges of one audio file. Independent of the episode player."""

    def __init__(self, audio_path: Path | None) -> None:
        self._path = audio_path if audio_path and audio_path.is_file() else None
        self._player: Any = None
        self._lock = threading.Lock()
        self._token = 0

    @property
    def is_available(self) -> bool:
        """Whether a preview can be played at all.

        False when the episode has not been downloaded and is not in the playback
        cache -- there are no bytes to cut. The dialog disables Preview rather
        than offering a button that explains itself only after being pressed.
        """
        if self._path is None:
            return False
        from quill.core.speech.ffmpeg import find_ffmpeg

        return bool(find_ffmpeg())

    # -- playback --------------------------------------------------------- #

    def play_range(self, from_ms: int, to_ms: int) -> None:
        """Play ``[from_ms, to_ms)``. Returns immediately; cutting happens off-thread."""
        if self._path is None:
            return
        span = max(0, int(to_ms) - int(from_ms))
        if span <= 0:
            return
        span = min(span, _MAX_PREVIEW_MS)

        with self._lock:
            self._token += 1
            token = self._token

        def _work() -> None:
            wav = self._cut(int(from_ms), span)
            # A second Preview press while the first was still cutting wins; the
            # earlier one is discarded rather than played late over the top.
            with self._lock:
                if token != self._token or not wav:
                    return
            self._play(wav, token)

        # Ad-hoc one-shot with its own cancellation: the token above is bumped by
        # every later press, so a preview still being cut is discarded rather than
        # played late. It deliberately has no host either -- the whole point of a
        # preview is that it is independent of the episode player.
        threading.Thread(
            target=_work,
            name="chapter-preview",
            daemon=True,
        ).start()  # GATE-40-OK: one-shot, cancelled by its own token

    def stop(self) -> None:
        """Silence any preview in flight, and cancel one still being cut."""
        with self._lock:
            self._token += 1
        player = self._player
        if player is not None:
            try:
                player.shutdown(timeout=0.5)
            except Exception:  # noqa: BLE001 - stopping must never raise
                pass
            self._player = None

    def close(self) -> None:
        self.stop()

    # -- internals -------------------------------------------------------- #

    def _cut(self, from_ms: int, span_ms: int) -> bytes:
        """The requested slice as WAV bytes, or ``b""``.

        ``-ss`` before ``-i`` so ffmpeg seeks rather than decoding from the top:
        the difference on a two-hour file is between instant and several seconds.
        """
        from quill.core.speech.ffmpeg import find_ffmpeg

        ffmpeg = find_ffmpeg()
        if not ffmpeg or self._path is None:
            return b""
        argv = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-ss",
            f"{from_ms / 1000:.3f}",
            "-t",
            f"{span_ms / 1000:.3f}",
            "-i",
            str(self._path),
            "-ac",
            "1",
            "-ar",
            str(_SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            "-",
        ]
        try:
            completed = subprocess.run(argv, capture_output=True, timeout=30.0, check=False)
        except (OSError, subprocess.SubprocessError):
            return b""
        return completed.stdout if completed.returncode == 0 else b""

    def _play(self, wav: bytes, token: int) -> None:
        from quill.platform.sound_player import SoundPlayer

        try:
            player = SoundPlayer()
            event_id = f"chapter-preview-{token}"
            player.register_event(event_id, wav)
            with self._lock:
                if token != self._token:
                    player.shutdown(timeout=0.2)
                    return
                previous, self._player = self._player, player
            if previous is not None:
                try:
                    previous.shutdown(timeout=0.2)
                except Exception:  # noqa: BLE001
                    pass
            player.play(event_id)
        except Exception:  # noqa: BLE001 - a preview that cannot play is not an error
            return
