"""The sinks: one per channel, each wrapping something that already works.

Deliberately adapters rather than rewrites (#1292-#1296). ``AnnouncementEngine``
holds hard-won behaviour -- the no-double-talk rule that a live screen reader
always beats the SAPI self-voice (#966), the Prism context-lifetime rule where a
``Backend`` dangles if its ``Context`` is collected (#700), the SAPI apartment
and worker-thread rules -- and none of that is worth re-deriving. Same for the
earcon player, the notification store, and the verbosity history: each one works;
what was missing was a single place that drives them all.

Every sink here takes its dependency **injected as a callable**, which is what
keeps ``quill/core/announce`` free of wx, ctypes and platform imports while
still driving real hardware in the shell. It also makes each channel testable
with a two-line fake.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.announce.message import Announcement, Channel, Severity
from quill.core.announce.sinks import BaseSink, SinkStatus


class SpeechSink(BaseSink):
    """Speech, through the existing announcement engine (#1292).

    ``speak(text, force_speech)`` is exactly ``AnnouncementEngine.announce``'s
    signature, so the adapter is a rename rather than a reimplementation: the
    engine keeps owning backend selection, self-voice fallback, and interrupt
    semantics. Severity maps onto the ``force_speech`` boolean the engine already
    speaks -- WARNING and ERROR interrupt, everything else stays polite.
    """

    channel = Channel.SPEECH

    def __init__(
        self,
        speak: Callable[[str, bool], str | None],
        *,
        backend_name: Callable[[], str] | None = None,
    ) -> None:
        super().__init__()
        self._speak = speak
        self._backend_name = backend_name

    def deliver(self, announcement: Announcement) -> None:
        error = self._speak(announcement.text, announcement.force_speech)
        if error:
            self.note_error(str(error))
            raise RuntimeError(error)

    def probe(self) -> SinkStatus:
        backend = self._backend_name() if self._backend_name is not None else ""
        available = bool(backend) and backend.lower() not in {"status_only", "none"}
        return SinkStatus(
            channel=self.channel,
            available=available,
            backend=backend,
            detail="" if available else "no speech backend is active",
            last_error=self.last_error,
        )


class BrailleSink(BaseSink):
    """A braille display, through whichever bridge the shell provides (#1293).

    The P0 fix (#1289) proved the dispatch; this makes it a channel like any
    other. Two things it must keep from that fix: braille failure is reported
    rather than allowed to cost the user their speech (the service isolates it),
    and an ERROR holds the display rather than flashing past -- the one message a
    reader most needs to catch should not disappear on the next status update.
    """

    channel = Channel.BRAILLE

    def __init__(
        self,
        braille: Callable[[str], str],
        *,
        supports_braille: Callable[[], bool] | None = None,
        backend_name: Callable[[], str] | None = None,
        hold: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self._braille = braille
        self._supports = supports_braille
        self._backend_name = backend_name
        #: Optional "keep this on the display" hook for ERROR; bridges that
        #: cannot hold simply flash, which is still better than nothing.
        self._hold = hold

    def deliver(self, announcement: Announcement) -> None:
        text = announcement.braille
        if not text.strip():
            return
        if announcement.severity is Severity.ERROR and self._hold is not None:
            self._hold(text)
            return
        error = self._braille(text)
        if error:
            self.note_error(str(error))
            raise RuntimeError(error)

    def probe(self) -> SinkStatus:
        supported = self._supports() if self._supports is not None else True
        backend = self._backend_name() if self._backend_name is not None else ""
        return SinkStatus(
            channel=self.channel,
            available=supported,
            backend=backend,
            detail="" if supported else "no braille display connected",
            last_error=self.last_error,
        )


class SoundSink(BaseSink):
    """Earcons, through the shell's sound player (#1294).

    The cue leads the message: it plays before speech reaches the reader, which
    is what makes an earcon useful as a "that worked" confirmation rather than a
    noise arriving after the fact. Sinks are delivered in installation order, so
    installing this one first is the whole mechanism.
    """

    channel = Channel.SOUND

    def __init__(
        self,
        play: Callable[[str], None],
        *,
        is_enabled: Callable[[str], bool] | None = None,
    ) -> None:
        super().__init__()
        self._play = play
        #: Honours settings.sound_events_disabled without this module needing to
        #: know the setting exists.
        self._is_enabled = is_enabled

    def deliver(self, announcement: Announcement) -> None:
        event = announcement.sound_event
        if not event:
            return
        if self._is_enabled is not None and not self._is_enabled(event):
            return
        self._play(event)

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel,
            available=True,
            backend="sound pack",
            last_error=self.last_error,
        )


class VisualSink(BaseSink):
    """The status line, with a message slot standing status cannot clobber (#1295).

    The bug this prevents: a status refresh (word count, cursor position) landing
    a fraction of a second after an announcement wipes the announcement off the
    only surface a sighted-but-not-listening user had. The message keeps its own
    slot for a persistence window; standing status renders around it.
    """

    channel = Channel.VISUAL

    def __init__(
        self,
        show: Callable[[str], None],
        *,
        clock: Callable[[], float] | None = None,
        persistence_seconds: float = 5.0,
    ) -> None:
        super().__init__()
        import time

        self._show = show
        self._clock = clock or time.monotonic
        self._persistence = persistence_seconds
        self._message = ""
        self._shown_at = 0.0

    def deliver(self, announcement: Announcement) -> None:
        self._message = announcement.text
        self._shown_at = self._clock()
        self._show(announcement.text)

    def last_message(self) -> str:
        """The announcement still inside its persistence window, else ""."""
        if not self._message:
            return ""
        if (self._clock() - self._shown_at) >= self._persistence:
            return ""
        return self._message

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel, available=True, backend="status bar", last_error=self.last_error
        )


class NotificationSink(BaseSink):
    """Warnings and errors, into the notification history (#1295).

    Only problems land here. A notification list that also carries every "Saved"
    is a log, and a log nobody reads is worse than no list at all.
    """

    channel = Channel.NOTIFICATION

    def __init__(self, add: Callable[[str, str], object]) -> None:
        super().__init__()
        self._add = add

    def deliver(self, announcement: Announcement) -> None:
        if not announcement.severity.is_problem:
            return
        self._add(announcement.text, announcement.severity.value)

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel,
            available=True,
            backend="notifications",
            last_error=self.last_error,
        )


class EchoSink(BaseSink):
    """The Spoken Echo ring buffer -- "what did it just say?" (#1296)."""

    channel = Channel.ECHO

    def __init__(self, record: Callable[[str], None]) -> None:
        super().__init__()
        self._record = record

    def deliver(self, announcement: Announcement) -> None:
        self._record(announcement.text)

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel, available=True, backend="echo", last_error=self.last_error
        )


class HistorySink(BaseSink):
    """The bounded, redacting announcement history (#1296).

    Redaction is the reason this is a sink rather than a log call: history is
    read back into a support bundle, and a token value that reached a status
    message must not reach a file the user is about to email.
    """

    channel = Channel.HISTORY

    def __init__(self, record: Callable[[str, str], None]) -> None:
        super().__init__()
        self._record = record

    def deliver(self, announcement: Announcement) -> None:
        self._record(announcement.text, announcement.severity.value)

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel, available=True, backend="history", last_error=self.last_error
        )


class TranscriptSink(BaseSink):
    """The headless transcript the UIA suite asserts against (#1296).

    Always installed, including in CI where no screen reader exists: the
    regression suite proves "QUILL said X" by reading this, so it has to work
    with nothing attached.
    """

    channel = Channel.TRANSCRIPT

    def __init__(self, write: Callable[[str], None]) -> None:
        super().__init__()
        self._write = write

    def deliver(self, announcement: Announcement) -> None:
        self._write(announcement.text)

    def probe(self) -> SinkStatus:
        return SinkStatus(
            channel=self.channel, available=True, backend="transcript", last_error=self.last_error
        )
