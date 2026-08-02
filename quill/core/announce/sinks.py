"""The sink protocol: one delivery mechanism, one channel (#1290).

A sink is the only place that knows *how* a channel reaches the user -- a screen
reader bridge, a braille display, an earcon player, a status bar. The service
knows none of that, which is what keeps ``quill/core/announce`` free of wx and
ctypes and lets every sink be tested with a fake.

Two things every sink owes the rest of the system:

* :meth:`Sink.deliver` -- do the work, or raise. The service isolates failures,
  so a sink is never responsible for protecting its siblings.
* :meth:`Sink.probe` -- say honestly whether it can deliver right now and why
  not. "Braille: no display connected" is a far better answer for a support
  bundle than silence, and it is the data the Self-Test surface renders.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from quill.core.announce.message import Announcement, Channel


@dataclass(frozen=True, slots=True)
class SinkStatus:
    """What one sink can deliver right now, and why not when it cannot.

    ``available`` is the honest answer to "would an announcement reach the user
    through this channel"; ``backend`` names what is serving it ("JAWS", "Prism
    / NVDA", "status bar") so a diagnostics reader can tell *which* thing is
    broken; ``detail`` carries the human reason when it is not available.
    """

    channel: Channel
    available: bool
    backend: str = ""
    detail: str = ""
    last_error: str = ""

    def as_dict(self) -> dict[str, object]:
        """Support-bundle shape (JSON-safe)."""
        return {
            "channel": self.channel.value,
            "available": self.available,
            "backend": self.backend,
            "detail": self.detail,
            "last_error": self.last_error,
        }


@runtime_checkable
class Sink(Protocol):
    """One delivery mechanism for one channel."""

    @property
    def channel(self) -> Channel:
        """Which channel this sink serves."""
        ...

    def deliver(self, announcement: Announcement) -> None:
        """Deliver *announcement*. May raise; the service isolates it."""
        ...

    def probe(self) -> SinkStatus:
        """Report whether delivery would work right now."""
        ...


class BaseSink:
    """Convenience base: remembers the last error and answers a default probe."""

    channel: Channel = Channel.VISUAL

    def __init__(self) -> None:
        self._last_error = ""

    @property
    def last_error(self) -> str:
        return self._last_error

    def note_error(self, error: str) -> None:
        self._last_error = error

    def deliver(self, announcement: Announcement) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def probe(self) -> SinkStatus:
        return SinkStatus(channel=self.channel, available=True, last_error=self._last_error)
