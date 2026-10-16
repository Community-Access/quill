"""QUILL Lite's Preferences window claims each access key once (GATE-14).

The window is one ``wx.Dialog`` built by a function in ``lite_preferences.py``
and helpers in its sibling modules, which is the shape ``check_access_keys``
cannot see: it scopes a dialog *class* as one window and anything else per
method. So U, D, H and F were each claimed twice until 2026-10-15, and one of
each pair could not be reached by its letter. This reads every label in the
modules that build the window, the way a person meets them: all in one window.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

_APPS = Path(__file__).resolve().parents[3] / "quill" / "apps"
_LABEL = re.compile(r'"([^"\n]*?(?<!&)&([A-Za-z0-9])[^"\n]*)"')


def test_every_access_key_in_preferences_is_claimed_once() -> None:
    claims: dict[str, list[str]] = defaultdict(list)
    for module in sorted(_APPS.glob("lite_preferences*.py")):
        for number, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
            for match in _LABEL.finditer(line):
                claims[match.group(2).lower()].append(f"{module.name}:{number} {match.group(1)}")
    twice = {key: where for key, where in claims.items() if len(where) > 1}
    assert not twice, "access keys claimed twice in QUILL Lite's Preferences:\n" + "\n".join(
        f"  {key.upper()}: " + "; ".join(where) for key, where in sorted(twice.items())
    )
