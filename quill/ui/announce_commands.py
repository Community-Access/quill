"""Commands over the announcement service, shared by every shell (#1304, #1305).

Two things a person actually needs from an announcement system, and neither
existed outside QUILL itself:

* **"What did it just say?"** -- speech is gone the moment it finishes, and a
  screen reader user who was reading something else when a status message
  passed has no way back to it. ``repeat_last_announcement`` re-announces it,
  and reads from the same service that delivered it, so it works in Quill
  Radio, Cast, Audio Studio, Weather, Converter and Beacon exactly as in QUILL.
* **"Is any of this reaching me?"** -- the self-test (#1305) announces a phrase
  on every channel and then shows what actually delivered, naming the backend
  serving each. That answer is the difference between "braille is broken" and
  "no display is connected", which is the difference between a bug report and a
  five-second fix.

The report deliberately prints failures as prose rather than status codes: it
is read aloud or in braille, by someone who may be trying to work out why they
heard nothing.
"""

from __future__ import annotations

from typing import Any

from quill.core.announce import Announcement, Channel, Severity

#: The phrase the self-test announces. Distinctive enough to recognise when it
#: arrives in speech, short enough to fit a braille display without panning.
SELF_TEST_PHRASE = "QUILL announcement self-test."

#: Spoken when there is nothing to repeat, rather than silence -- silence is the
#: symptom the command exists to diagnose.
NOTHING_TO_REPEAT = "No announcement to repeat yet."


class AnnounceCommandsMixin:
    """Repeat Last Announcement and the Announcement Self-Test."""

    def repeat_last_announcement(self) -> None:
        """Say the most recent announcement again, on every channel (#1304)."""
        text = self._last_announcement_text()
        if not text:
            self._announce(NOTHING_TO_REPEAT)
            return
        service = self._announce_service()
        if service is None:
            self._announce(text, force=True)
            return
        # force/WARNING: the user explicitly asked for this one, so it should cut
        # across whatever the reader is currently saying.
        service.announce(Announcement(text=text, severity=Severity.WARNING))

    def _last_announcement_text(self) -> str:
        """The last thing announced, from the echo history or the visual slot."""
        history = getattr(self, "_spoken_echo_history", None)
        if history:
            try:
                return str(list(history)[-1])
            except (IndexError, TypeError):
                pass
        service = self._announce_service()
        if service is None:
            return str(getattr(self, "_status_message", "") or "")
        for sink in getattr(service, "_sinks", []):  # noqa: SLF001 - documented seam
            last = getattr(sink, "last_message", None)
            if callable(last):
                text = last()
                if text:
                    return str(text)
        return str(getattr(self, "_status_message", "") or "")

    def run_announcement_self_test(self) -> None:
        """Announce a test phrase, then report which channels delivered (#1305)."""
        service = self._announce_service()
        if service is None:
            self._announce("Announcements are not available in this window.")
            return
        report = service.announce(
            Announcement(
                text=SELF_TEST_PHRASE,
                severity=Severity.WARNING,
                sound_event="document_saved",
            )
        )
        text = format_self_test_report(service, report)
        show = getattr(self, "show_text_report", None)
        if callable(show):
            show("Announcement Self-Test", text)
            return
        self._announce(summarise_self_test(report))


def format_self_test_report(service: Any, report: Any) -> str:
    """The copyable report: what delivered, what did not, and why not."""
    lines = [
        "Announcement self-test",
        "",
        f'Test phrase: "{SELF_TEST_PHRASE}"',
        "",
    ]
    statuses = {status.channel: status for status in service.probe()}
    for channel in Channel:
        status = statuses.get(channel)
        delivered = channel in getattr(report, "delivered", frozenset())
        failure = getattr(report, "failed", {}).get(channel, "")
        label = channel.value.capitalize()
        if delivered:
            backend = status.backend if status and status.backend else "unknown backend"
            lines.append(f"{label}: delivered, through {backend}.")
        elif failure:
            lines.append(f"{label}: failed. {failure}")
        elif status is not None and not status.available:
            reason = status.detail or "not available"
            lines.append(f"{label}: not delivered. {reason}.")
        else:
            lines.append(f"{label}: not delivered for this announcement.")
    lines.append("")
    lines.append(summarise_self_test(report))
    return "\n".join(lines) + "\n"


def summarise_self_test(report: Any) -> str:
    """One spoken line: how many channels carried the test."""
    delivered = sorted(channel.value for channel in getattr(report, "delivered", frozenset()))
    if not delivered:
        return "The self-test reached no channels at all."
    count = len(delivered)
    noun = "channel" if count == 1 else "channels"
    return f"The self-test reached {count} {noun}: {', '.join(delivered)}."
