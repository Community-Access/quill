"""Scribe Status: everything QUILL knows about the account and the queue, as text.

The Scribe Status dialog (:mod:`quill.ui.scribe_status_dialog`) shows this in
one read-only multi-line field, so a screen reader arrows through it line by
line and a braille display pans it. The first line is the one fact most people
open it for (who is signed in and the pages left); then the sections, each a
heading line followed by its facts:

* **Account** -- name, email, phone, organization, subscription, sign-in.
* **Usage** -- pages left, and the family's pace against Scribe's rate limit.
* **Now converting** -- the job under way: stage, percent, time left.
* **Waiting** -- queued jobs and jobs waiting for the person.
* **Recent** -- finished jobs still in the queue on this computer.

**Only what is real.** Every account fact comes from ``GET /api/account_info``
and ``GET /api/billing`` (:class:`quill.core.scribe.model.Account`); every job
fact from the family queue file (:mod:`quill.core.scribe.queue`). Scribe's API
reports pages left but not pages used, a plan name or a page limit, and sends no
rate-limit headers, so the pace is the family's own count. The token is never
shown; the sign-in line says only whether it renews by itself.

wx-free, no I/O: :func:`build_status` is a pure function of
:class:`StatusInputs`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime

from quill.core.scribe import CONVERSIONS_TITLE, PRODUCT_NAME
from quill.core.scribe import queue as q
from quill.core.scribe.model import Account, formats_phrase, pages_left_phrase
from quill.core.scribe.sentences import status_sentence

#: The section headings, in order (tests and the guide name them).
SECTIONS = ("Account", "Usage", "Now converting", "Waiting", "Recent")

#: Finished jobs listed under Recent, newest first.
RECENT_LIMIT = 5

#: Jobs the runner is working on now (``BUSY`` is the one Scribe asked to wait).
_UNDER_WAY = frozenset({q.UPLOADING, q.CONVERTING, q.DOWNLOADING, q.BUSY})

#: Scribe's own limit, which the website's use shares (PRD 3.5).
_SCRIBE_LIMIT = 10


@dataclass(frozen=True, slots=True)
class StatusInputs:
    """What the dialog gathered: local facts at once, the account when it came."""

    app_name: str = "QUILL"
    signed_in: bool = False
    #: True when a refresh token is kept, so the sign-in renews by itself.
    renews: bool = True
    #: Unix seconds the access token ends, for a sign-in that cannot renew.
    sign_in_ends: float = 0.0
    account: Account | None = None
    #: True while the account is being read.
    checking: bool = False
    #: The account could not be read: the server's sentence and the QUILL code.
    error_message: str = ""
    error_code: str = ""
    #: The sign-in has ended (``QUILL-SCRIBE-SIGNIN``): offer Sign In again.
    sign_in_ended: bool = False
    jobs: tuple[q.Job, ...] = ()
    #: The app holding the runner lock (doing the work), or ``""``.
    runner_app: str = ""
    actions_this_minute: int = 0
    paused_until: float = 0.0
    now: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class StatusReport:
    first_line: str
    text: str
    #: Show the Sign In button (not signed in, or the sign-in has ended).
    offer_sign_in: bool


def _clock(seconds: float, now: float | None = None) -> str:
    """Hours and minutes; seconds only when it is less than a minute away."""
    soon = now is not None and 0 <= seconds - now < 60
    return time.strftime("%H:%M:%S" if soon else "%H:%M", time.localtime(seconds))


def _day(seconds: float) -> str:
    stamp = time.localtime(seconds)
    return f"{stamp.tm_mday} {time.strftime('%B', stamp)}, {time.strftime('%H:%M', stamp)}"


def renewal_date(iso: str) -> str:
    """``"2026-12-12T00:00:00Z"`` as ``"12 December 2026"``; the text as it came
    if it is not ISO 8601 (it is the server's, so it is shown rather than lost)."""
    text = (iso or "").strip()
    if not text:
        return ""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    # The date as Scribe gave it: a renewal at midnight UTC converted to the
    # local zone would land on the day before in the Americas.
    return f"{moment.day} {moment.strftime('%B %Y')}"


def first_line(inputs: StatusInputs) -> str:
    """The most important fact, alone on the first line."""
    if not inputs.signed_in or inputs.sign_in_ended:
        if inputs.sign_in_ended:
            return f"Your {PRODUCT_NAME} sign-in has ended. Sign In to see your account."
        return f"You are not signed in to {PRODUCT_NAME}. Sign In to see your account."
    account = inputs.account
    if inputs.error_message:
        # Before the account: a failed refresh keeps the last account below it.
        code = f" ({inputs.error_code})" if inputs.error_code else ""
        return f"Signed in, but your Scribe account could not be read: {inputs.error_message}{code}"
    if account is not None:
        named = bool(f"{account.first_name}{account.last_name}{account.email}".strip())
        who = f"Signed in as {account.name}" if named else "Signed in"
        if account.organization_name:
            who += f", using credits from {account.organization_name}"
        if account.pages_remaining is None:
            return f"{who}. Scribe did not say how many pages are left."
        pages = pages_left_phrase(account.pages_remaining)
        return f"{who}. {pages[0].upper()}{pages[1:]}."
    return "Signed in. Checking your Scribe account..."


def _account_lines(inputs: StatusInputs) -> list[str]:
    if not inputs.signed_in or inputs.sign_in_ended:
        return ["Not signed in. Sign In opens Scribe's own sign-in page in your browser."]
    account = inputs.account
    lines: list[str] = []
    if account is None:
        if inputs.error_message:
            lines.append("Your name and pages could not be read; Refresh tries again.")
        else:
            lines.append("Checking your Scribe account...")
    else:
        name = f"{account.first_name} {account.last_name}".strip()
        if name:
            lines.append(f"Name: {name}")
        if account.email:
            lines.append(f"Email: {account.email}")
        if account.phone_number:
            lines.append(f"Phone: {account.phone_number}")
        if account.organization_name:
            lines.append(f"Organization: {account.organization_name}")
        lines.append(f"Subscription: {_subscription(account)}")
    lines.append(f"Sign-in: {_sign_in(inputs)}")
    return lines


def _subscription(account: Account) -> str:
    if not account.has_subscription:
        return "none."
    where = {"app_store": "bought in the App Store", "web": "bought on the Scribe website"}
    text = "active"
    if account.subscription_store in where:
        text += f", {where[account.subscription_store]}"
    renews = renewal_date(account.subscription_renews_at)
    if renews:
        text += f", renews {renews}"
    return text + "."


def _sign_in(inputs: StatusInputs) -> str:
    if inputs.renews:
        return "kept on this computer for every QUILL app, and renewed by itself."
    if inputs.sign_in_ends > inputs.now:
        return f"ends at {_clock(inputs.sign_in_ends, inputs.now)}; then sign in again."
    return "ended; sign in again."


def _usage_lines(inputs: StatusInputs) -> list[str]:
    lines: list[str] = []
    account = inputs.account
    if not inputs.signed_in or inputs.sign_in_ended:
        lines.append("Pages left: sign in to see them.")
    elif account is None or account.pages_remaining is None:
        lines.append("Pages left: not known yet." if account is None else "Pages left: not known.")
    else:
        pool = (
            f", using credits from {account.organization_name}" if account.organization_name else ""
        )
        lines.append(f"Pages left: {account.pages_remaining:,}{pool}.")
    if inputs.paused_until > inputs.now:
        lines.append(
            f"Pace: Scribe asked {inputs.app_name} to slow down; the next upload or "
            f"conversion starts at {_clock(inputs.paused_until, inputs.now)}."
        )
    else:
        lines.append(
            f"Pace: {inputs.actions_this_minute} of {q.ACTION_LIMIT} uploads and conversions "
            f"this minute. Scribe allows {_SCRIBE_LIMIT}, including its website."
        )
    return lines


def _job_formats(job: q.Job) -> str:
    return f" Formats: {formats_phrase(job.formats)}." if job.formats else ""


def _now_lines(inputs: StatusInputs, under_way: list[q.Job]) -> list[str]:
    if not under_way:
        return ["Nothing is converting."]
    lines: list[str] = []
    for job in under_way:
        line = status_sentence(job)
        if job.state == q.BUSY and job.not_before > inputs.now:
            at = _clock(job.not_before, inputs.now)
            line = f"{job.display_name}: {job.state_words}; trying again at {at}."
        lines.append(line + _job_formats(job))
        if job.message:
            lines.append(f"Latest from Scribe: {job.message}")
    if inputs.runner_app:
        lines.append(f"{inputs.runner_app} is doing the work.")
    return lines


def _waiting_lines(waiting: list[q.Job]) -> list[str]:
    if not waiting:
        return ["Nothing is waiting."]
    lines = []
    for job in waiting:
        line = f"{job.display_name}: {job.state_words}.{_job_formats(job)}"
        if job.state in q.NEEDS_PERSON:
            line += f" {CONVERSIONS_TITLE} has what to do."
        lines.append(line)
    return lines


def _recent_lines(finished: list[q.Job]) -> list[str]:
    if not finished:
        return ["No finished conversions on this computer."]
    lines = []
    for job in finished[:RECENT_LIMIT]:
        line = (
            f"{job.display_name}: {job.state_words}.{_job_formats(job)} Sent {_day(job.created)}."
        )
        if job.state == q.FAILED and job.message:
            line += f" {job.message}"
        lines.append(line)
    more = len(finished) - RECENT_LIMIT
    if more > 0:
        lines.append(f"{more} more in {CONVERSIONS_TITLE}.")
    return lines


def build_status(inputs: StatusInputs) -> StatusReport:
    """The dialog's whole text, first line first, then each section."""
    jobs = sorted(inputs.jobs, key=lambda job: job.created)
    under_way = [job for job in jobs if job.state in _UNDER_WAY]
    waiting = [job for job in jobs if job.state == q.QUEUED or job.state in q.NEEDS_PERSON]
    finished = sorted(
        (job for job in jobs if job.state in q.FINISHED), key=lambda j: j.created, reverse=True
    )
    head = first_line(inputs)
    sections = (
        ("Account", _account_lines(inputs)),
        ("Usage", _usage_lines(inputs)),
        ("Now converting", _now_lines(inputs, under_way)),
        (f"Waiting ({len(waiting)})" if waiting else "Waiting", _waiting_lines(waiting)),
        ("Recent", _recent_lines(finished)),
    )
    blocks = [head]
    for heading, lines in sections:
        blocks.append("\n".join([heading, *lines]))
    return StatusReport(
        first_line=head,
        text="\n\n".join(blocks),
        offer_sign_in=not inputs.signed_in or inputs.sign_in_ended,
    )


__all__ = [
    "RECENT_LIMIT",
    "SECTIONS",
    "StatusInputs",
    "StatusReport",
    "build_status",
    "first_line",
    "renewal_date",
]
