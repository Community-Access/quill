"""Platform-specific integrations for Quill Radio for Mac.

This package holds native OS glue that has no cross-platform equivalent:
VoiceOver announcements, native speech synthesis, screen-reader detection,
media-key routing, and Dock menu wiring. Everything under
``quill_radio_mac.core`` and ``quill_radio_mac.ui`` is platform-neutral;
only code in this package (and its ``macos`` subpackage) is allowed to
import a native framework binding such as pyobjc.

Naming hazard: this package is named ``platform``, the same name as the
Python standard library module of that name. Because Python 3 uses
absolute imports by default, ``import platform`` from *anywhere* --
including from inside this package's own modules -- resolves to the
stdlib module, never to this package, as long as submodules here use
absolute imports (``import quill_radio_mac.platform.macos.announce``,
not a bare relative ``from . import announce`` that could shadow). This
package deliberately does not import the stdlib ``platform`` module
itself, to keep that guarantee obviously true rather than merely tested.

Currently only ``quill_radio_mac.platform.macos`` exists: this app targets
macOS exclusively, unlike upstream QUILL which also ships a
``quill.platform.windows`` package (dropped here per the porting rules).
"""

from __future__ import annotations
