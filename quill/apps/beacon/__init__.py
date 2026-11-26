"""QuillBeacon -- accessible, local-first bookmark and location manager.

Standalone companion app in the QUILL family, following the pattern set by
Quill Cast (``quill-cast``) and Quill Radio (``quill-radio``): a thin product
wrapper around an engine. The engine lives in this package for the first
slice; the production target is ``quill/apps/beacon.py`` reusing
``quill.ui.app_shell.AppShellFrame`` (see Docs/PRD.md section 44.1).

Tagline: *Find your way back to anything.*
"""

from __future__ import annotations

__version__ = "0.1.0"
__title__ = "QuillBeacon"

#: Shared-store components this app uses when present but runs without:
#: beacon/player.py offers an opt-in libmpv backend and falls back to
#: wx.media. Declared so the refcount registry keeps a present copy from
#: being garbage-collected out from under an installed Beacon
#: (app-profiles.json).
OPTIONAL_COMPONENTS: tuple[str, ...] = ("mpv",)


def main() -> int:
    """Entry point used by the console/gui script and the PyInstaller launcher."""
    from quill.core import components

    components.register_running_app("beacon", OPTIONAL_COMPONENTS)

    from quill.apps.beacon.app import run

    return run()


__all__ = ["main", "__version__", "__title__"]
