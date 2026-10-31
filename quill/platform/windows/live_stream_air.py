"""Is the stream really on air? (Studio PRD BCAST-027.)

A connection that has sent nothing is not a broadcast. "On air" and "back on
air" are said only once the server has taken at least two seconds of encoded
audio, measured from the encoder's own progress report (FFmpeg's
``-progress``) and, for SHOUTcast, scaled by the share of the encoded bytes
Studio's client has actually handed to the connection. "Taken" means the
operating system accepted it for sending, and the buffers on the way hold
several seconds, so a server that answers and then reads nothing looks on air
until they fill; once the encoder's output stops advancing the show is off air
again and that is said once (``LiveStream._check_still_moving``). An authentication
refusal at any attempt, not only the first, ends the retries with the reason.

The lesson is Tony Gebhard's, from TG Drop Deck; the code is QUILL's own.
"""

from __future__ import annotations

import re
from collections import deque

from quill.core.streaming import StreamingError

ON_AIR = "On air."
BACK_ON_AIR = "The stream is back on air."
#: Seconds of encoded audio the server must take before the show is on air.
ACCEPTED_SECONDS = 2.0
#: A connection that has taken no audio after this long is said to be stuck.
SILENT_CONNECTION_SECONDS = 10.0
#: On air, output that has not advanced for this long means the server stopped taking it.
STALLED_SECONDS = 4.0
REFUSED = "The server refused the user name or password."
_REFUSAL = re.compile(r"\b401\b|unauthori[sz]ed|authentication failed", re.IGNORECASE)


class StreamRefused(StreamingError):
    """The server refused the stream's credentials; trying again cannot help."""

    code = "QUILL-STUDIO-STREAM-REFUSED"


def is_auth_refusal(lines: list[str] | deque[str]) -> bool:
    """Whether FFmpeg's last words say the server refused the login."""
    return any(_REFUSAL.search(line) for line in lines)


class EncoderProgress:
    """What one encoder has produced, read from its ``-progress`` lines."""

    def __init__(self) -> None:
        self.out_seconds = 0.0
        self.total_bytes = 0
        self.sent_bytes = 0  # SHOUTcast only: bytes handed to the connection
        self.tail: deque[str] = deque(maxlen=20)

    def feed(self, line: str) -> None:
        text = line.strip()
        key, sep, value = text.partition("=")
        if not sep or not key.isidentifier():
            if text:
                self.tail.append(text)  # a log line, kept for the reason it failed
            return
        try:
            if key in ("out_time_us", "out_time_ms"):  # both are microseconds
                self.out_seconds = max(self.out_seconds, int(value) / 1_000_000)
            elif key == "total_size":
                self.total_bytes = max(self.total_bytes, int(value))
        except ValueError:
            return

    def accepted_seconds(self, *, counted_bytes: bool) -> float:
        """Seconds of audio the server has taken.

        For Icecast FFmpeg writes to the server itself, so what it has encoded
        and written is what the connection took. For SHOUTcast FFmpeg writes to
        Studio, so only the share Studio has sent counts.
        """
        if not counted_bytes:
            return self.out_seconds
        if self.total_bytes <= 0:
            return 0.0
        return self.out_seconds * min(1.0, self.sent_bytes / self.total_bytes)
