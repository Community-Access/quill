"""Guard against the double-announce regression (the #728 class).

``_set_status`` already speaks its message (main_frame_statusbar.py routes it
through ``announce``), so an adjacent ``self._set_status(...)`` immediately
followed by ``self._announce(...)`` speaks the action twice. The fix is to use
``_set_status`` alone when the two strings are identical, or ``_set_status_quiet``
(visible but silent) plus ``_announce`` when the status bar wants a terser line
than the spoken announcement.
"""

from __future__ import annotations

import re
from pathlib import Path

_UI_DIR = Path(__file__).resolve().parents[3] / "quill" / "ui"
_PAIR = re.compile(r"self\._set_status\([^\n]*\)\s*\n\s*self\._announce\(", re.MULTILINE)


def test_no_set_status_immediately_followed_by_announce() -> None:
    offenders: list[str] = []
    for path in sorted(_UI_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in _PAIR.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.name}:{line}")
    assert not offenders, (
        "self._set_status(X) immediately followed by self._announce(...) speaks "
        "twice (the #728 double-announce). Use _set_status alone when the text is "
        "identical, or _set_status_quiet + _announce when the status bar wants a "
        "terser line. Offenders: " + ", ".join(offenders)
    )
