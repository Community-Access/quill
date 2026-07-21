"""Composer capability and accessibility checks (PRD 15.3, 15.6, 21.5).

Given a draft and its target accounts, the composer model reports -- per network
-- the character count, remaining length, thread segment count, and every
capability or accessibility problem the user should know before publishing:
visibility not allowed on this network, quotes/polls unsupported, too many media
attachments, alt text missing, content warning on a network that lacks them,
and whether the draft is eligible for native scheduling.

This is pure logic over the capability registry, so the composer can show a live
"will this work everywhere?" panel without any network call (PRD 6.3, 15.6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill_social.capabilities import Capabilities
from quill_social.model import Account, Draft
from quill_social.services.thread_splitter import (
    mastodon_counter,
    split_thread,
)


@dataclass
class NetworkReport:
    account_id: str
    account_label: str
    network: str
    length: int
    limit: int
    remaining: int
    segments: int
    fits: bool
    scheduling_eligible: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class CompositionReport:
    per_network: list[NetworkReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.per_network)

    @property
    def any_thread(self) -> bool:
        return any(r.segments > 1 for r in self.per_network)

    def summary(self) -> str:
        if not self.per_network:
            return "No target accounts selected."
        bits = []
        for r in self.per_network:
            state = "ok" if r.ok else f"{len(r.errors)} problem(s)"
            seg = f", {r.segments} segments" if r.segments > 1 else ""
            bits.append(f"{r.account_label}: {r.length}/{r.limit}{seg}, {state}")
        return "; ".join(bits)


def _counter_for(network: str):
    return mastodon_counter if network == "mastodon" else len


def _text_for(draft: Draft, network: str) -> str:
    """The variant text for a network, falling back to the base text (PRD 15.6)."""
    return draft.variants.get(network) or draft.text


def analyze_draft(
    draft: Draft,
    accounts: dict[str, Account],
    caps: dict[str, Capabilities],
) -> CompositionReport:
    """Build a per-network composition report for a draft.

    ``accounts`` and ``caps`` are keyed by account id. Any target without an
    account record is reported as an error rather than silently dropped.
    """
    report = CompositionReport()
    for account_id in draft.targets:
        account = accounts.get(account_id)
        if account is None:
            report.per_network.append(
                NetworkReport(
                    account_id=account_id, account_label=account_id, network="unknown",
                    length=0, limit=0, remaining=0, segments=0, fits=False,
                    scheduling_eligible=False,
                    errors=["account is not connected"],
                )
            )
            continue
        cap = caps.get(account_id) or Capabilities(network=account.network)
        counter = _counter_for(account.network)
        text = _text_for(draft, account.network)
        length = counter(text)
        limit = cap.char_limit
        errors: list[str] = []
        warnings: list[str] = []

        # Threading / length.
        if draft.thread_mode:
            split = split_thread(text, limit, counter=counter)
            segments = split.count
            if split.any_over_limit:
                errors.append(
                    "a segment has an unbreakable token longer than the limit")
        else:
            segments = 1
            if length > limit:
                errors.append(
                    f"over the {limit}-character limit by {length - limit}; "
                    "turn on thread mode to split it")

        # Visibility.
        if not cap.allows_visibility(draft.visibility):
            allowed = ", ".join(cap.visibilities)
            errors.append(
                f"visibility '{draft.visibility}' is not supported here "
                f"(allowed: {allowed})")

        # Quote / poll.
        if draft.quote_of and not cap.supports_quote:
            errors.append("this account does not support quote posts")
        if draft.poll and not cap.supports_polls:
            errors.append("this network has no native polls; "
                          "consider an external accessible poll")
        if draft.poll and cap.supports_polls and len(draft.poll.options) > cap.max_poll_options:
            errors.append(
                f"poll has more than {cap.max_poll_options} options")

        # Content warning.
        if draft.content_warning and not cap.supports_content_warnings:
            warnings.append("content warnings are not supported here; "
                            "it will be dropped")

        # Media + alt text (PRD 21.5 accessibility assistant).
        if len(draft.media) > cap.max_media_attachments:
            errors.append(
                f"too many media attachments ({len(draft.media)} > "
                f"{cap.max_media_attachments})")
        missing_alt = [m for m in draft.media if not m.has_alt]
        if missing_alt:
            warnings.append(
                f"{len(missing_alt)} of {len(draft.media)} attachments "
                "are missing alt text")

        scheduling_eligible = cap.supports_native_scheduling or True  # local tier always
        report.per_network.append(
            NetworkReport(
                account_id=account_id,
                account_label=account.label,
                network=account.network,
                length=length,
                limit=limit,
                remaining=limit - length,
                segments=segments,
                fits=length <= limit or draft.thread_mode,
                scheduling_eligible=scheduling_eligible,
                errors=errors,
                warnings=warnings,
            )
        )
    return report
