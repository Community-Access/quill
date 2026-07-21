"""QUILL Social -- accessibility-first social workspace for Mastodon and Bluesky.

A standalone companion in the QUILL family, following the pattern set by
QuillBeacon (``quill-beacon``) and QUILL Audio Studio (``quill-audio-studio``):
a self-contained engine plus an accessible wxPython shell in the first slice.
The production target reuses ``quill.ui.app_shell.AppShellFrame`` (see the PRD,
section 44).

The design center is a blind keyboard and screen-reader user. Every core
action is reachable by keyboard, every important state is available as text,
and reading, drafting, organizing, splitting, and scheduling all work locally
against a deterministic mock network before a single credential is entered.

Tagline: *Every conversation within reach.*
"""

from __future__ import annotations

__version__ = "0.3.0"
__title__ = "QUILL Social"


def main() -> int:
    """Entry point used by the gui-script and the PyInstaller launcher."""
    from quill_social.ui.app import run

    return run()


__all__ = ["main", "__version__", "__title__"]
