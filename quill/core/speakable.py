"""Text a screen reader cannot name a control character in.

A PDF opens in QUILL and QUILL Lite with a form feed (``"\\f"``, U+000C)
between its pages, because that is what Go To's Page list and the Page cell
count (:mod:`quill.core.navigation`). Text near a page break then reaches
announcements -- a selection's first words, a deleted line, a find result --
and handed on raw, a screen reader may say the character's name ("form feed")
in the middle of a sentence, while a braille display shows a dot pattern for
it. :func:`speakable_controls` is applied once, where every announcement in
the family leaves for the reader
(:class:`quill.platform.windows.prism_bridge.AnnouncementEngine`, speech and
braille), and to QUILL Lite's status-bar message, which JAWS reads aloud with
Insert+Page Down (2026-10-17).

Kept apart from :mod:`quill.core.speech_text`, which reshapes text QUILL did not
write (Markdown, HTML, decorative Unicode) and is applied only where that text
is announced; this is smaller and applies to everything.

wx-free, strict-typed, no I/O.
"""

from __future__ import annotations

import re

__all__ = ["speakable_controls"]

#: The page break (form feed) and vertical tab: a boundary between lines, so a
#: listener hears a pause where a reader of the page sees a new line or page.
_LINE_BOUNDARY_CONTROLS = re.compile("[\x0b\x0c]")

#: Every other C0 and C1 control character except tab, newline and carriage
#: return. None of them carries anything a listener can use.
_SILENT_CONTROLS = re.compile("[\x00-\x08\x0e-\x1f\x7f-\x9f]")


def speakable_controls(text: str) -> str:
    """*text* with page breaks as line breaks and other control characters gone.

    Tab, newline and carriage return survive: they are how a listener hears
    structure, and the announcement sinks decide their own line handling.
    """
    if not text:
        return text
    return _SILENT_CONTROLS.sub("", _LINE_BOUNDARY_CONTROLS.sub("\n", text))
