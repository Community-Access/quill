"""The announcement service: one owner for every channel (#1290, #1297).

Nothing owned announcements before this. Speech lived in two of three shells,
braille lived nowhere, earcons lived only in QUILL, and verbosity lived only in
QUILL -- so six companion apps could not mute, brailleize, or record anything.
The service is the single place an announcement enters, and sinks are the single
place one leaves.

Two guarantees make it safe to depend on:

* **A failing sink is isolated.** A braille display unplugged mid-sentence, a
  sound pack that will not load, a screen reader that went away -- each takes
  down its own channel and nothing else. The user still hears the message.
* **The first failure per sink is recorded, not repeated.** An announcement
  storm through a broken channel should leave one honest diagnostic, not ten
  thousand log lines.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from quill.core.announce.message import Announcement, Channel
from quill.core.announce.policy import AnnouncementPolicy, Decision
from quill.core.announce.sinks import Sink, SinkStatus
from quill.core.error_codes import CodedError


class AnnounceError(CodedError):
    """Raised when the announcement service is misconfigured."""

    code = "QUILL-CORE-ANNOUNCE-SERVICE"


@dataclass(frozen=True, slots=True)
class DeliveryReport:
    """What happened to one announcement, for tests and diagnostics."""

    delivered: frozenset[Channel] = field(default_factory=frozenset)
    skipped: frozenset[Channel] = field(default_factory=frozenset)
    failed: dict[Channel, str] = field(default_factory=dict)

    @property
    def spoke(self) -> bool:
        return Channel.SPEECH in self.delivered

    @property
    def brailled(self) -> bool:
        return Channel.BRAILLE in self.delivered


class AnnouncementService:
    """Fan one announcement out to every sink the policy allows."""

    def __init__(
        self,
        sinks: Iterable[Sink] | None = None,
        *,
        policy: AnnouncementPolicy | None = None,
    ) -> None:
        self._sinks: list[Sink] = list(sinks or [])
        self._policy = policy or AnnouncementPolicy()
        #: One recorded error per channel: the first failure, kept until it
        #: succeeds again, so diagnostics show what broke without a flood.
        self._errors: dict[Channel, str] = {}

    # -- composition ---------------------------------------------------------

    def add_sink(self, sink: Sink) -> None:
        """Install *sink*. Later sinks receive announcements after earlier ones."""
        self._sinks.append(sink)

    def remove_channel(self, channel: Channel) -> None:
        """Drop every sink serving *channel* (used when a shell tears down)."""
        self._sinks = [sink for sink in self._sinks if sink.channel is not channel]

    @property
    def policy(self) -> AnnouncementPolicy:
        return self._policy

    def set_policy(self, policy: AnnouncementPolicy) -> None:
        self._policy = policy

    def channels(self) -> frozenset[Channel]:
        """Which channels currently have a sink installed."""
        return frozenset(sink.channel for sink in self._sinks)

    # -- delivery ------------------------------------------------------------

    def announce(self, announcement: Announcement) -> DeliveryReport:
        """Deliver *announcement* on every channel the policy allows.

        Never raises: a sink that fails is recorded and skipped so the remaining
        channels still reach the user. That is the whole point of routing them
        separately -- a broken display must not cost someone their speech.
        """
        decision = self._policy.decide(announcement)
        delivered: set[Channel] = set()
        skipped: set[Channel] = set()
        failed: dict[Channel, str] = {}
        for sink in self._sinks:
            channel = sink.channel
            if not self._allows(decision, announcement, channel):
                skipped.add(channel)
                continue
            # A channel that cannot reach the user right now (no display
            # connected, no reader running) is skipped, not failed -- the
            # difference matters in the self-test report.
            can_deliver = getattr(sink, "can_deliver", None)
            if callable(can_deliver) and not can_deliver():
                skipped.add(channel)
                continue
            try:
                sink.deliver(self._shaped(announcement, decision, channel))
            except Exception as exc:  # noqa: BLE001 - one channel must never take the others
                message = f"{channel.value} announcement failed: {exc}"
                failed[channel] = message
                self._errors.setdefault(channel, message)
                continue
            delivered.add(channel)
            self._errors.pop(channel, None)
        return DeliveryReport(
            delivered=frozenset(delivered),
            skipped=frozenset(skipped),
            failed=failed,
        )

    @staticmethod
    def _allows(decision: Decision, announcement: Announcement, channel: Channel) -> bool:
        return announcement.wants(channel) and channel in decision.channels

    @staticmethod
    def _shaped(announcement: Announcement, decision: Decision, channel: Channel) -> Announcement:
        """The announcement as this channel should receive it.

        Only braille differs today: the policy may hand a channel its own text
        (the compact form, or a sticky error), and a sink should not have to
        reach back into the policy to find it.
        """
        if channel is Channel.BRAILLE and decision.braille_text:
            return Announcement(
                text=announcement.text,
                braille_text=decision.braille_text,
                severity=announcement.severity,
                channels=announcement.channels,
                sound_event=announcement.sound_event,
                region=announcement.region,
                dedupe_key=announcement.dedupe_key,
                context=announcement.context,
            )
        return announcement

    # -- diagnostics (A8) ----------------------------------------------------

    def probe(self) -> list[SinkStatus]:
        """Ask every sink whether it could deliver right now.

        Honest by design: a channel with no sink at all reports unavailable with
        the reason, rather than being silently absent from the report.
        """
        statuses: list[SinkStatus] = []
        seen: set[Channel] = set()
        for sink in self._sinks:
            try:
                status = sink.probe()
            except Exception as exc:  # noqa: BLE001 - a probe must never raise at the caller
                status = SinkStatus(
                    channel=sink.channel,
                    available=False,
                    detail=f"probe failed: {exc}",
                )
            recorded = self._errors.get(sink.channel, "")
            if recorded and not status.last_error:
                status = SinkStatus(
                    channel=status.channel,
                    available=status.available,
                    backend=status.backend,
                    detail=status.detail,
                    last_error=recorded,
                )
            statuses.append(status)
            seen.add(sink.channel)
        for channel in Channel:
            if channel not in seen:
                statuses.append(
                    SinkStatus(
                        channel=channel,
                        available=False,
                        detail="no sink installed for this channel",
                    )
                )
        return statuses

    def diagnostics(self) -> dict[str, object]:
        """The support-bundle shape for the whole service."""
        return {
            "announce_channels": sorted(channel.value for channel in self.channels()),
            "announce_sinks": [status.as_dict() for status in self.probe()],
        }
