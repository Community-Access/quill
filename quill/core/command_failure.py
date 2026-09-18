"""What to say when a command fails (bad.md P0.9).

"Command failed: file.save" was QUILL's whole report. It named the command the
person had just pressed -- which they knew -- and said nothing about the fault,
so a full disk, a read-only folder, a character the encoding cannot hold and a
bug inside a Quillin all produced the same sentence. A listener cannot open a
log to find the rest, so that sentence was the end of the road.

The exception's own words are usually the only clue there is. They are not
beautiful, and they are enormously better than nothing.

wx-free so both editors can say the same thing, and directly tested.
"""

from __future__ import annotations

__all__ = ["describe_command_failure"]

#: Exception types whose class name says nothing a person can act on, so the
#: message alone is clearer than "ValueError: ...".
_SILENT_CLASS_NAMES = frozenset({"Exception", "RuntimeError", "ValueError", "CodedError"})


def describe_command_failure(command_id: str, error: BaseException) -> str:
    """One sentence naming the command *and* what went wrong with it.

    The command id stays because it is what a bug report needs and what the
    Keyboard Manager and the palette both show; the fault is added because it
    is the only part the person did not already know.
    """
    detail = str(error).strip()
    name = type(error).__name__
    if not detail:
        detail = name
    elif name not in _SILENT_CLASS_NAMES:
        detail = f"{name}: {detail}"
    code = getattr(error, "code", "")
    if isinstance(code, str) and code:
        detail = f"{detail} ({code})"
    return f"{command_id} failed -- {detail}"
