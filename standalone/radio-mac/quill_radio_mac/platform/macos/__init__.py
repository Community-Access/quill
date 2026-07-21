"""macOS native integrations, all behind lazy, optional pyobjc imports.

Modules:

- :mod:`quill_radio_mac.platform.macos.announce` -- post VoiceOver
  announcements via ``NSAccessibility``.
- :mod:`quill_radio_mac.platform.macos.tts` -- ``NSSpeechSynthesizer``
  self-voicing fallback and the system voice catalog.
- :mod:`quill_radio_mac.platform.macos.sr_detect` -- detect a running
  VoiceOver process.
- :mod:`quill_radio_mac.platform.macos.media_keys` -- route the Mac media
  keys (play/pause/stop) via ``MPRemoteCommandCenter``.
- :mod:`quill_radio_mac.platform.macos.dock` -- build and install the
  app's Dock menu.

Every module in this package must import ``pyobjc`` frameworks (``AppKit``,
``Foundation``, ``MediaPlayer``) lazily, inside function bodies, and catch
``ImportError`` (and, where the framework can be present but the call can
still fail, broader exceptions) so that:

1. ``import quill_radio_mac.platform.macos.<anything>`` always succeeds,
   on any OS, with or without pyobjc installed -- this is what lets the
   pytest suite import and exercise these modules on Windows.
2. Every public function has a safe off-mac / no-pyobjc return value
   (``False``, ``[]``, or a plain no-op) instead of raising, so callers in
   ``quill_radio_mac.ui`` never need to guard calls with a platform check.

This package is only ever imported by the wx UI layer and by
``quill_radio_mac.app``; nothing in ``quill_radio_mac.core`` depends on it.
"""

from __future__ import annotations
