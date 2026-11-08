"""The Command Key's error codes (command-key.md 7.9, GATE-EC)."""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = ["CommandNoLongerAvailable", "CommandNotOffered"]


class CommandNotOffered(CodedError):
    """A matcher or an engine named a command that was not on the candidate list.

    It is never run. It is logged as a defect, because the list is the whole of
    what any matcher may choose from.
    """

    code = "QUILL-CORE-COMMAND-NOT-OFFERED"


class CommandNoLongerAvailable(CodedError):
    """The chosen command became unavailable between choosing it and running it."""

    code = "QUILL-CORE-COMMAND-NO-LONGER-AVAILABLE"
