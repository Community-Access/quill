"""Quill Radio for Mac: a standalone, screen-reader-first internet radio app.

This package is a self-contained macOS port of Quill Radio from the QUILL
project. Upstream code (the ``quill`` package) is adapted in, never
imported: every module here stands alone so the app installs and runs with
nothing but Python, wxPython, and (optionally) pyobjc.

Package layout:

- ``quill_radio_mac.core``: wx-free logic (models, persistence, network
  clients, recording, scheduling). Importable headless; the whole pytest
  suite runs against it on any platform.
- ``quill_radio_mac.ui``: the wxPython frame, player controller, mpv
  engine, and dialogs.
- ``quill_radio_mac.platform.macos``: optional macOS integrations
  (VoiceOver announcements, media keys, Dock menu) behind lazy pyobjc
  imports.

Threading contract: importing this package performs no IO and starts no
threads. It must never import wx -- ``python -c "import quill_radio_mac"``
has to succeed on a machine without wxPython so core tests stay headless.
The wx.App bootstrap lives in :mod:`quill_radio_mac.app` and is only
imported by ``__main__`` and the console/gui entry points.

macOS notes: application data lives under
``~/Library/Application Support/Quill`` (see
:mod:`quill_radio_mac.core.paths`), deliberately the same folder name the
Windows app uses under ``%APPDATA%`` so a copied data folder just works.
"""

from __future__ import annotations

# Version of this standalone app (independent of upstream QUILL's version).
__version__ = "1.0.0"

# Short name used in window titles, announcements, and data-schema fields
# that must stay byte-compatible with the Windows app.
APP_NAME = "Quill Radio"

# Long name for the About dialog, the macOS bundle, and documentation.
APP_DISPLAY_NAME = "Quill Radio for Mac"

# GitHub coordinates used by the update checker (core.updates) to find
# releases of this app.
GITHUB_OWNER = "Community-Access"
GITHUB_REPO = "quill-radio-mac"

__all__ = [
    "__version__",
    "APP_NAME",
    "APP_DISPLAY_NAME",
    "GITHUB_OWNER",
    "GITHUB_REPO",
]
