"""The announcement service: one owner for speech, braille, sound and status.

Public surface for the shells (see #1283 and its program, #1289-#1307)::

    from quill.core.announce import Announcement, AnnouncementService, Severity

    service.announce(Announcement(text="Saved note.md"))
    service.announce(error("Could not save note.md"))

Everything here is wx-free and strict-typed; delivery lives in injected sinks.
"""

from __future__ import annotations

from quill.core.announce.message import (
    ALL_CHANNELS,
    Announcement,
    Channel,
    Severity,
    error,
    info,
    routine,
    warning,
)
from quill.core.announce.policy import AnnouncementPolicy, Decision, PolicyModes, compact_braille
from quill.core.announce.service import AnnounceError, AnnouncementService, DeliveryReport
from quill.core.announce.sinks import BaseSink, Sink, SinkStatus

__all__ = [
    "ALL_CHANNELS",
    "AnnounceError",
    "Announcement",
    "AnnouncementPolicy",
    "AnnouncementService",
    "BaseSink",
    "Channel",
    "Decision",
    "DeliveryReport",
    "PolicyModes",
    "Severity",
    "Sink",
    "SinkStatus",
    "compact_braille",
    "error",
    "info",
    "routine",
    "warning",
]
