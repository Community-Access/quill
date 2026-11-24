"""What the app says when a part it ships with is missing (2026-11-23).

A bundled tool or library can go missing from a copy of an app: an
interrupted unzip, an antivirus quarantine, a folder somebody tidied. The
sentence that says so used to be written for whoever built the app -- a
script name and its flags, ``pip install``, "this build", "the in-process
runtime" -- none of which a person can act on. Every such sentence now comes
from here, so they all say the same two things in the same order: what does
not work, and how to get it back.

The wording was reviewed for speech and braille (Desktop Accessibility
Specialist, 2026-11-23): a period rather than a colon between the two halves,
because NVDA and JAWS do not speak a colon and some voices do not pause on
one; "this copy of the app", because the same sentence serves QUILL and QUILL
Lite; and a new folder for the portable copy, because unzipping over the old
one can keep the damaged files.

Wx-free.
"""

from __future__ import annotations

__all__ = [
    "COPILOT_DAMAGED",
    "COPILOT_MISSING",
    "CODEX_MISSING",
    "REPAIR_SENTENCE",
    "damaged_part",
    "missing_part",
]

#: How to get a missing part back, the same everywhere.
REPAIR_SENTENCE = (
    "To fix this, install the app again. If you use the portable version, download "
    "it again and unzip it to a new folder."
)


def missing_part(effect: str, missing: str) -> str:
    """*effect* (what does not work) and *missing* (what is gone), then the repair.

    Both halves are whole sentences without their final period:
    ``missing_part("The Practice Site cannot start", "Its WordPress files are
    missing from this copy of the app")``.
    """
    return f"{effect}. {missing}. {REPAIR_SENTENCE}"


def damaged_part(effect: str, part: str = "A part it needs") -> str:
    """The same, for a part that is there but cannot be used."""
    return f"{effect}. {part} is damaged. {REPAIR_SENTENCE}"


#: The AI engines both editors carry. Said as the reason a connection is
#: unavailable; they used to speak of "the in-process runtime" and "this build".
COPILOT_MISSING = missing_part(
    "GitHub Copilot cannot start", "A part it needs is missing from this copy of the app"
)
COPILOT_DAMAGED = damaged_part("GitHub Copilot cannot start")
CODEX_MISSING = missing_part(
    "Codex cannot start", "Its files are missing from this copy of the app"
)
