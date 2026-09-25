"""QUILL Lite's wx-free core: where it keeps state, what it remembers, what it binds.

QUILL Lite is QUILL with everything removed except the editor -- one document per
window, plain text or rich text, and nothing else. It exists for the person who
wants Notepad or WordPad with QUILL's accessibility and finds the full writing
environment more than they need.

Everything under here is deliberately **not** QUILL's own core. A Notepad-scale
product must not silently adopt a writing environment's settings file, its
recovery store, or its recent-file list, and a user who removes QUILL Lite must
not lose anything QUILL owns. So the four pieces below are QUILL Lite's own:

* :mod:`~quill.core.lite.paths` -- ``%LOCALAPPDATA%\\QuillLite``, separate from
  ``%APPDATA%\\Quill`` on purpose;
* :mod:`~quill.core.lite.settings` -- ten fields, written atomically through
  QUILL's own :func:`~quill.core.storage.write_json_atomic`;
* :mod:`~quill.core.lite.recovery` -- one slot per modified window, offered back
  on the next start;
* :mod:`~quill.core.lite.commands` -- the command table the menu bar, the
  keyboard-shortcut list and the uniqueness tests are all generated from, so
  they cannot drift apart.

What is *not* here is anything QUILL already does well: the Rich Edit surface,
the RTF safety scanner, the dialog contract, the F1 help engine and the
announcement path all come from the shared package. QUILL Lite is a small
product, not a second implementation.
"""

from __future__ import annotations

#: The product name, as people see and hear it: window titles, dialogs, About,
#: the support message. "QUILL Lite" since 2026-09-25; it was "QuillLite".
APP_NAME = "QUILL Lite"

#: The machine identifier, which did **not** change with the display name: the
#: data folder, the single-instance name and wx's application name. Renaming
#: any of those would strand every existing install's settings and recovered
#: work in a folder the new version no longer looks in, and let an old and a
#: new copy run side by side as two "only" instances.
APP_ID = "QuillLite"

#: QUILL Lite versions with the QUILL family rather than with QUILL itself
#: (``quill.__version__``): it ships its own installers and its own release
#: notes, exactly as Radio, Cast, Weather, Studio and Inkwell do.
APP_VERSION = "1.0.0"

#: Where QUILL Lite's own releases live, and the basename every one of its
#: release assets starts with (``QuillLite-Setup-Shared-1.0.0.exe``,
#: ``QuillLite-Portable-1.0.0.zip``). Deliberately *not* in
#: :data:`quill.core.companion_install.ASSET_PREFIX`: that table is the set of
#: QuillVille apps QUILL can offer to install for you, and QUILL Lite is a
#: separate product rather than a sibling QUILL launches. Check for Updates
#: (:mod:`quill.apps.lite_updates`) resolves its asset from these two.
RELEASE_REPO = "Community-Access/quill"
RELEASE_ASSET_PREFIX = "QuillLite"

__all__ = ["APP_ID", "APP_NAME", "APP_VERSION", "RELEASE_ASSET_PREFIX", "RELEASE_REPO"]
