"""QuillLite's wx-free core: where it keeps state, what it remembers, what it binds.

QuillLite is QUILL with everything removed except the editor -- one document per
window, plain text or rich text, and nothing else. It exists for the person who
wants Notepad or WordPad with QUILL's accessibility and finds the full writing
environment more than they need.

Everything under here is deliberately **not** QUILL's own core. A Notepad-scale
product must not silently adopt a writing environment's settings file, its
recovery store, or its recent-file list, and a user who removes QuillLite must
not lose anything QUILL owns. So the four pieces below are QuillLite's own:

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
announcement path all come from the shared package. QuillLite is a small
product, not a second implementation.
"""

from __future__ import annotations

#: The product name, as it appears in window titles, the data folder, and the
#: single-instance name. One definition, so a rename cannot half-happen.
APP_NAME = "QuillLite"

#: QuillLite versions with the QUILL family rather than with QUILL itself
#: (``quill.__version__``): it ships its own installers and its own release
#: notes, exactly as Radio, Cast, Weather, Studio and Inkwell do.
APP_VERSION = "1.0.0"

__all__ = ["APP_NAME", "APP_VERSION"]
