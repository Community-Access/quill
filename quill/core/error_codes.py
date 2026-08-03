"""Stable, greppable error codes for support triage (beta-2 fix pass).

A pasted error message should let us pinpoint the exact failure branch without
back-and-forth with the user. :class:`CodedError` carries a class-level
``code`` that its ``__str__`` prefixes onto the message, e.g.
``[QUILL-SPEECH-WHISPER-DL-404] The model reference is out of date...``.

Code format: ``QUILL-<DOMAIN>-<SUBSYSTEM>-<SHORT-REASON>`` -- stable and
greppable, with no incrementing numbers to keep in sync by hand.

Every custom top-level exception class in ``quill/core``, ``quill/io``, and
``quill/stability`` mixes this in (enforced by
:mod:`quill.tools.error_code_audit`, GATE-EC). A new exception class must
inherit ``CodedError`` (or an already-coded parent) and declare its own
``code`` or the gate fails.

The migrated shape is ``class FooError(CodedError):`` -- NOT
``class FooError(Exception, CodedError):``. ``CodedError`` already inherits
``Exception``, so explicitly listing both, in that order, is an
unresolvable MRO and raises ``TypeError`` at class-definition time.
"""

from __future__ import annotations

from typing import ClassVar

#: What-to-do sentences per error code (the error-specificity programme).
#:
#: A sighted user can often open the failing file or dialog and see the
#: problem; a blind user cannot, so the message must carry both the diagnosis
#: (the raiser's specific message) and the next action (this hint). Keyed by
#: code so the whole catalogue lives in one greppable place; a class may
#: instead set ``user_hint`` directly when its hint is not shared.
#:
#: Write hints as complete sentences naming the concrete next step -- a menu
#: path, a setting, a command -- never "an error occurred" or "try again".
USER_HINTS: dict[str, str] = {
    "QUILL-AI-CHAT-FAILED": (
        "Check your AI provider and key in the AI Hub, or switch to a local model."
    ),
    "QUILL-AI-DOCQA-FAILED": (
        "Check your AI provider and key in the AI Hub, or switch to a local model."
    ),
    "QUILL-AI-TTS-FAILED": ("Check the voice engine under Tools > Speech, or pick another voice."),
    "QUILL-AI-TRANSCRIBE-FAILED": (
        "Check the transcription engine in the AI Hub; the local Whisper model "
        "works without a key or a connection."
    ),
    "QUILL-PANDOC-UNAVAILABLE": (
        "Install Pandoc from Help > Download Optional Components to convert this format."
    ),
    "QUILL-IO-OCR-UNAVAILABLE": (
        "Install the OCR components from Help > Download Optional Components."
    ),
    "QUILL-IO-REMOTE-TRANSPORT": (
        "Check the address, credentials, and connection under File > Manage Remote Sites."
    ),
    "QUILL-SSH-CLIENT-NO-PARAMIKO": (
        "SSH support is not installed in this build; reinstall QUILL or add the "
        "paramiko package to enable it."
    ),
    "QUILL-RELEASE-ASSET-FAILED": (
        "Check your internet connection, then retry the download from "
        "Help > Download Optional Components."
    ),
    "QUILL-SPEECH-PROVIDER-FAILED": (
        "Choose a different voice or engine under Tools > Speech; bundled eSpeak "
        "always works offline."
    ),
    "QUILL-QUILLIN-FRAMEWORK-FAILED": (
        "Open Tools > Quillins to see which extension failed and disable or reinstall it."
    ),
    "QUILL-IO-DOCCONVERT-FAILED": (
        "Try File > Save As with a different format, or install Pandoc from "
        "Help > Download Optional Components for more formats."
    ),
    "QUILL-SPEECH-WHISPER-DL-404": (
        "The model reference is out of date. Update QUILL, or pick a different "
        "model under Tools > Speech."
    ),
    "QUILL-SPEECH-WHISPER-DL-NET": (
        "Check your internet connection and try the download again; a partial "
        "download resumes where it stopped."
    ),
    "QUILL-SPEECH-WHISPER-DL-CHK": (
        "The downloaded file did not match its checksum. Delete it and download "
        "again from Tools > Speech."
    ),
    "QUILL-SPEECH-ENGINE-INSTALL": (
        "Retry the install from Help > Download Optional Components; bundled "
        "eSpeak keeps working in the meantime."
    ),
    "QUILL-SPEECH-FFMPEG-INSTALL": (
        "Retry the ffmpeg download from Tools > Speech, or install ffmpeg "
        "yourself and put it on PATH."
    ),
    "QUILL-SPEECH-CAPTURE-UNAVAILABLE": (
        "Check that a microphone is connected and allowed for desktop apps in "
        "Windows Settings > Privacy > Microphone."
    ),
    "QUILL-IO-SAVE-UNSUPPORTED": (
        "Use File > Save As and choose one of the offered formats for this document."
    ),
    "QUILL-GIT-WORKTREE-NO-GIT": (
        "Install git from Help > Download Optional Components, then open "
        "Tools > Local Git > Worktrees... again."
    ),
}


class CodedError(Exception):
    """Mixin for exceptions that carry a stable support-triage code."""

    code: ClassVar[str] = ""

    #: Optional per-class what-to-do sentence; overrides the USER_HINTS table.
    user_hint: ClassVar[str] = ""

    def __str__(self) -> str:
        message = super().__str__()
        return f"[{self.code}] {message}" if self.code else message

    def user_message(self) -> str:
        """The full user-facing sentence: the specific diagnosis plus the next step.

        ``str(self)`` already carries the code and the raiser's specific
        message; this appends the what-to-do hint for the code, so every
        surfaced error tells the user both what failed and what to do about
        it without needing to see a screen.
        """
        message = str(self)
        hint = self.user_hint.strip() or USER_HINTS.get(self.code, "")
        if hint and hint not in message:
            return f"{message.rstrip()} {hint}".strip()
        return message


def user_facing_message(error: BaseException) -> str:
    """The best user-facing text for any exception.

    CodedError instances get their diagnosis-plus-next-step sentence; anything
    else falls back to ``str(error)``, and an exception with no message at all
    falls back to its class name rather than an empty string -- a blank error
    is indistinguishable from a crash to someone who cannot see the dialog.
    """
    if isinstance(error, CodedError):
        text = error.user_message()
    else:
        text = str(error)
    return text.strip() or error.__class__.__name__
