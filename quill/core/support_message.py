"""The message every app sends when somebody asks support for help.

One address, one shape, one place that decides what a support message says --
so Quill Radio's report and QUILL Lite's report arrive looking like the same
product wrote them, and so the wording can be fixed once.

Two things this module deliberately does *not* do:

* **It never touches GitHub.** ``Community-Access/quill`` is public, and a
  person describing a screen-reader failure may name their employer, their
  configuration or the document they were working on. That belongs in the
  help desk, not in a searchable public repository -- the rule
  ``docs/design/2026-08-26-feedback-redesign-for-freescout.md`` is built on.
* **It never holds a credential.** The mail path hands the finished message to
  the reader's own mail client; the server path posts to a relay that holds the
  only secret. A desktop app with an SMTP password in it is the GitHub token
  problem wearing different clothes.

Everything here is pure: build a :class:`SupportMessage`, ask for a subject, a
body or a ``mailto:`` URL. Nothing sends, so the whole shape is testable
without a network, a mail client or wx.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote

#: The public support address. FreeScout answers it; Postmark delivers it.
SUPPORT_EMAIL = "support@community-access.org"

#: What the menu item is called in every app, without its mnemonic.
SUPPORT_MENU_TITLE = "Get Help from Support"

#: The family key. Free in every app's menu bar as of 2026-09-11, and it sits
#: one key along from Tutorials (Ctrl+Alt+F1) because it is the same question
#: asked a different way: "I am stuck, who can tell me?"
SUPPORT_MENU_KEY = "Ctrl+Alt+F2"

#: A ``mailto:`` URL longer than this is refused by Windows' shell handler and
#: by several mail clients -- silently, which is the dangerous part: the client
#: opens with a truncated body and the reporter never knows. We cut it
#: ourselves instead, and say so, with the whole text on the clipboard.
MAILTO_URL_LIMIT = 1800

_TRUNCATION_NOTE = (
    "\n\n[This message was shortened to fit your mail program. "
    "The complete text is on your clipboard -- paste it here with Control V.]"
)


@dataclass(frozen=True)
class SupportMessage:
    """One person's message to support, and what the app knows about it."""

    product: str
    summary: str
    message: str
    category: str = "Bug Report"
    expected: str = ""
    steps: str = ""
    reply_email: str = ""
    platform: str = ""
    screen_reader: str = ""
    extra: Mapping[str, str] = field(default_factory=dict)


def build_subject(message: SupportMessage) -> str:
    """The email subject: product first, so triage starts from what we know.

    The agent's first job is to decide which of nine products this is about
    (§1.4 of the plan). The app already knows; making a person infer it from
    the body is work we handed them for nothing.
    """
    product = message.product.strip() or "QUILL"
    summary = message.summary.strip() or "Support request"
    return f"[{product}] {summary}"


def build_body(message: SupportMessage) -> str:
    """The plain-text body, in the order an agent reads it."""
    lines: list[str] = []
    sections: list[tuple[str, str]] = [
        ("What happened", message.message),
        ("What I expected", message.expected),
        ("Steps to reproduce", message.steps),
    ]
    for heading, text in sections:
        body = text.strip()
        if not body:
            continue
        lines.append(heading)
        lines.append("-" * len(heading))
        lines.append(body)
        lines.append("")

    facts: list[tuple[str, str]] = [
        ("Product", message.product),
        ("Category", message.category),
        ("Operating system", message.platform),
        ("Screen reader", message.screen_reader),
        ("Reply to", message.reply_email),
    ]
    facts.extend((str(key), str(value)) for key, value in message.extra.items())
    known = [f"{label}: {value.strip()}" for label, value in facts if value and value.strip()]
    if known:
        lines.append("About this report")
        lines.append("-----------------")
        lines.extend(known)
    return "\n".join(lines).strip() + "\n"


def build_mailto_url(
    message: SupportMessage,
    *,
    address: str = SUPPORT_EMAIL,
    limit: int = MAILTO_URL_LIMIT,
) -> tuple[str, bool]:
    """Return ``(url, was_shortened)`` for *message*.

    ``was_shortened`` is the caller's cue to put the full body on the clipboard
    and say so out loud. A mail client that quietly opens with half a bug
    report is the failure this flag exists to prevent.

    The limit is on the **encoded** URL and every field counts toward it.
    Until 2026-11 only the body was shortened, so a long subject produced a
    4,735-character URL against the 1,800 limit while still reporting
    ``was_shortened=True``. Now the subject is cut too (it may take at most
    a third of the room), lengths are measured after percent-encoding, so an
    accented letter costs six characters and an emoji twelve, and a cut never
    splits a character. The complete text is the caller's clipboard fallback
    (:func:`build_subject` and :func:`build_body` are untouched).
    """
    subject = build_subject(message)
    body = build_body(message)
    url = _mailto(address, subject, body)
    if len(url) <= limit:
        return url, False

    fixed = len(_mailto(address, "", ""))
    note = _TRUNCATION_NOTE.strip()
    # The subject keeps its beginning -- the product and what the person
    # typed first -- and gives up its tail. It may use whatever a short body
    # leaves, but never less than a third of the room, and never so much that
    # the body cannot say the full text is on the clipboard.
    total = limit - fixed
    body_need = _encoded_len(body.rstrip() + _TRUNCATION_NOTE)
    subject_room = max(0, min(_encoded_len(subject), max(total // 3, total - body_need)))
    subject = _fit_encoded(subject, subject_room, marker="…")
    body_room = limit - fixed - _encoded_len(subject)
    # Shrink the body to fit, keeping the beginning -- which is what the
    # person actually typed -- and losing the tail.
    tail = _TRUNCATION_NOTE
    head_room = body_room - _encoded_len(tail)
    if head_room > 0:
        candidate = _fit_encoded(body, head_room).rstrip() + tail
    else:
        candidate = _fit_encoded(note, body_room)
    url = _mailto(address, subject, candidate)
    if len(url) > limit:  # pragma: no cover - only an absurdly small limit
        url = _mailto(address, _fit_encoded(subject, 0), _fit_encoded(note, limit - fixed))
    return url, True


def _encoded_len(text: str) -> int:
    return len(quote(text, safe=""))


def _fit_encoded(text: str, room: int, *, marker: str = "") -> str:
    """The longest prefix of *text* whose percent-encoding fits in *room*.

    Cut on whole characters, so a multi-byte character is either all there
    or not there, and the URL still decodes. *marker* (an ellipsis on a
    subject) is appended when anything was cut, and counted in the room.
    """
    if _encoded_len(text) <= room:
        return text
    marker_cost = _encoded_len(marker)
    budget = room - marker_cost
    if budget <= 0:
        return ""
    used = 0
    end = 0
    for char in text:
        cost = _encoded_len(char)
        if used + cost > budget:
            break
        used += cost
        end += 1
    return text[:end].rstrip() + marker


def _mailto(address: str, subject: str, body: str) -> str:
    return (
        f"mailto:{quote(address, safe='@')}"
        f"?subject={quote(subject, safe='')}"
        f"&body={quote(body, safe='')}"
    )


def validate(message: SupportMessage) -> list[str]:
    """Everything wrong with *message*, in the order to say it. Empty is fine.

    The email address is optional on purpose: somebody who does not want to
    give one should still be able to report a problem. They simply will not get
    an answer, and the dialog says that in those words rather than making the
    field required.
    """
    problems: list[str] = []
    if not message.summary.strip():
        problems.append("Give the message a subject, so support knows what it is about.")
    if not message.message.strip():
        problems.append("Describe what happened, in as much or as little detail as you like.")
    reply = message.reply_email.strip()
    if reply and ("@" not in reply or reply.startswith("@") or reply.endswith("@")):
        problems.append("That email address does not look right. Leave it empty to send anyway.")
    return problems
