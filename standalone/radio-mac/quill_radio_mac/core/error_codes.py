"""Stable, greppable error codes for support triage.

Ported from upstream ``quill.core.error_codes``. A pasted error message
should let a maintainer pinpoint the exact failure branch without
back-and-forth with the user. :class:`CodedError` carries a class-level
``code`` that its ``__str__`` prefixes onto the message, e.g.
``[QUILL-RADIO-BROWSER-HTTP] The station directory did not respond...``.

Code format: ``QUILL-<DOMAIN>-<SUBSYSTEM>-<SHORT-REASON>`` -- stable and
greppable, with no incrementing numbers to keep in sync by hand.

Only :class:`CodedError` itself lives here. The radio modules each
declare their own coded exception next to the code they protect
(``RadioBrowserError``, ``SomaFmError``, ``TritonResolverError``,
``LinkFinderError``, ``RecordingError``, and the task manager's
``CancelledError``), exactly as upstream does.

The subclassing shape is ``class FooError(CodedError):`` -- NOT
``class FooError(Exception, CodedError):``. ``CodedError`` already
inherits ``Exception``, so explicitly listing both, in that order, is an
unresolvable MRO and raises ``TypeError`` at class-definition time.

Threading contract: exception classes only; no state, safe everywhere.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

from typing import ClassVar


class CodedError(Exception):
    """Mixin for exceptions that carry a stable support-triage code.

    Subclasses set the class attribute ``code``; ``__str__`` then renders
    ``[CODE] message`` so logs, dialogs, and announcements all carry the
    greppable identifier automatically.
    """

    code: ClassVar[str] = ""

    def __str__(self) -> str:
        message = super().__str__()
        return f"[{self.code}] {message}" if self.code else message
