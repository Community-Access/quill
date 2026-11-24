"""Text goes only where it was meant to go (FUX-07).

The family rule (docs/design/2026-11-19-family-ux-pilots.md, section 4): text
is inserted only into the target that was current when the input began. If
that target's identity changes, or cannot be confirmed, the text is kept and
offered as Insert or Copy. It is never typed somewhere else, and never read
aloud unasked.

Dictation already keeps that promise through its field lock
(:mod:`quill.core.windows_dictation.target_lock`). This module is the same
promise for Quill Inkwell's one-shot insertions, where a dialog of Inkwell's
own sits between choosing the text and typing it -- Quick Insert's picker and
a snippet's fill-in form -- so the focus has to be given back before anything
is typed, and giving it back can fail:

* :class:`HeldText` is the text and the place it was meant for, captured
  **before** the dialog took the focus;
* :func:`held_offer` decides, from an operation's result, whether to keep the
  text and what to say: one sentence, which never contains the text itself;
* :func:`failure_reason` is the same explanation as a short clause, for the
  places that say it rather than offer anything (a global undo that could not
  happen).

Pure and wx-free. The text in a :class:`HeldText` is held in memory only and
never logged.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.external_text import (
    ExternalTextReason,
    OperationResult,
    OperationStatus,
    TargetSnapshot,
)

__all__ = [
    "HeldOffer",
    "HeldText",
    "MOVED_REASON",
    "UNREADABLE_REASON",
    "failure_reason",
    "held_offer",
    "refusal_sentence",
]

#: Why nothing was typed when the place in front is not the one chosen.
MOVED_REASON = "the focus is not where you started"

#: Each reason code as a clause: what is wrong with the place, never what the
#: text was. "Password field" is said only for a field Windows itself marks as
#: one (UI Automation's IsPassword); nothing here claims to detect one otherwise.
_REASONS: dict[ExternalTextReason, str] = {
    ExternalTextReason.STALE_TARGET: MOVED_REASON,
    ExternalTextReason.NO_TARGET: MOVED_REASON,
    ExternalTextReason.UNKNOWN_TARGET: "Windows cannot confirm that place takes text",
    ExternalTextReason.ADAPTER_UNAVAILABLE: "Windows cannot say where the focus is",
    ExternalTextReason.TIMEOUT: "Windows took too long to say where the focus is",
    ExternalTextReason.NO_CAPABILITY: "that place does not take text",
    ExternalTextReason.READ_ONLY: "that place is read-only",
    ExternalTextReason.PROTECTED_TARGET: "Windows reports a password field there",
    ExternalTextReason.DENIED_TARGET: (
        "that is a password manager or sign-in window, where Inkwell never types"
    ),
    ExternalTextReason.ELEVATED_TARGET: (
        "that program runs as administrator, so Windows does not let Inkwell type into it"
    ),
    ExternalTextReason.PARTIAL_INJECTION: "Windows took only part of it",
    ExternalTextReason.CLIPBOARD_CHANGED: "the clipboard changed while it was being pasted",
}

#: Reasons where going back to the same place and trying again can work: the
#: focus moved, or Windows could not answer in time. A password field, a
#: read-only control or an administrator window will refuse again.
_RETRYABLE: frozenset[ExternalTextReason] = frozenset({
    ExternalTextReason.STALE_TARGET,
    ExternalTextReason.NO_TARGET,
    ExternalTextReason.ADAPTER_UNAVAILABLE,
    ExternalTextReason.TIMEOUT,
    ExternalTextReason.CLIPBOARD_CHANGED,
})


@dataclass(frozen=True, slots=True)
class HeldText:
    """Text, and the one place it may be typed.

    *target* is the focused control as it was when the input began (window,
    process and control identity, :meth:`TargetSnapshot.same_identity`).
    ``None`` means no place was captured -- Inkwell itself was in front -- and
    such text can only be copied.
    """

    text: str
    target: TargetSnapshot | None
    caret_from_end: int = 0
    backspace_count: int = 0
    trailing_text: str = ""

    def __repr__(self) -> str:  # the words are the person's: never in a log line
        return f"HeldText(<{len(self.text)} characters>, window={self.window})"

    @property
    def window(self) -> int:
        """The chosen place's window handle, or 0."""
        return self.target.window_handle if self.target is not None else 0


@dataclass(frozen=True, slots=True)
class HeldOffer:
    """What to say, and whether Insert is worth offering, for text kept back."""

    sentence: str
    can_insert: bool


def failure_reason(result: OperationResult) -> str:
    """Why *result* typed nothing, as a clause ("the focus is not where you started")."""
    return _REASONS.get(result.reason, "Windows did not accept it")


def held_offer(result: OperationResult) -> HeldOffer | None:
    """The offer to make for text that was not typed, or ``None`` when it was.

    One sentence, said once (it is the text of the window that offers Insert
    and Copy), naming the reason and the choices. It does not repeat the
    window's title ("Text Not Typed"). A partly typed result never offers
    Insert: typing it all again would double the part that landed.
    """
    if result.status is OperationStatus.APPLIED:
        return None
    reason = failure_reason(result)
    if result.reason is ExternalTextReason.PARTIAL_INJECTION:
        return HeldOffer(
            "Only part of the text was typed: check that field, and choose Copy "
            "to put all of it on the clipboard.",
            False,
        )
    if result.reason in _RETRYABLE:
        return HeldOffer(
            f"Your text was kept, because {reason}: choose Insert to go back "
            "and type it there, or Copy to put it on the clipboard.",
            True,
        )
    return HeldOffer(
        f"Your text was kept, because {reason}: choose Copy to put it on the clipboard.",
        False,
    )


#: Said when Windows cannot name the focused field before a fill-in form opens.
UNREADABLE_REASON = "Windows cannot say where the focus is"


def refusal_sentence(result: OperationResult, *, action: str) -> str:
    """What an expansion (*action* "expanded") or an undo ("undone") says when
    it did not land: one sentence, never the text. Part landed is said as
    such, and an undo that found another window says so in its own words,
    because the person did not "start" anything there."""
    if result.reason is ExternalTextReason.PARTIAL_INJECTION:
        return f"Only partly {action}; check the text."
    reason = failure_reason(result)
    if action == "undone" and reason == MOVED_REASON:
        reason = "the focus has moved to another window"
    return f"Not {action}, because {reason}."
