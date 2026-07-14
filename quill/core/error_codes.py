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


class CodedError(Exception):
    """Mixin for exceptions that carry a stable support-triage code."""

    code: ClassVar[str] = ""

    def __str__(self) -> str:
        message = super().__str__()
        return f"[{self.code}] {message}" if self.code else message
