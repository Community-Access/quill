"""The person's saved My Words, for More Dictation Settings' command word check.

Moved out of :mod:`quill.ui.dictation_more_dialog` (GATE-11) unchanged.
"""

from __future__ import annotations


def saved_my_words() -> list[str]:
    """My Words from the saved dictation profile; none when it cannot be read."""
    try:
        from quill.core.speech.dictation_profile import default_profile_path
        from quill.core.windows_dictation.profile import load

        return list(load(default_profile_path()).vocabulary)
    except Exception:  # noqa: BLE001 - no words is a fine answer
        return []
