"""No garbled text in what people hear or read.

When UTF-8 is read as Windows-1252 and written back, a dash becomes three
characters (a-circumflex, euro, quote) and a screen reader reads them out one
by one. One edit is enough, and nothing else notices. The idea and the check
are from Kelly Ford's Quick Describe, whose hygiene test caught a dash an edit
had turned into "a-circumflex, euro".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

# Windows-1252 readings of UTF-8 lead bytes, and the replacement character,
# written as escapes so this file cannot trip its own check.
_GARBLED = re.compile("\\u00e2\\u20ac|\\u00c3[\\u00a0-\\u00bf]|\\u00c2[\\u00a0-\\u00bf]|\\ufffd")

#: Source people hear (strings in the code) and the app guides people read.
_GLOBS = {"quill": "quill/**/*.py", "standalone": "standalone/*/docs/*.md"}


def _files(root: str) -> list[Path]:
    return sorted(ROOT.glob(_GLOBS[root]))


def _garbled_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        f"{path.relative_to(ROOT)}:{number}: {line.strip()[:80]}"
        for number, line in enumerate(text.splitlines(), 1)
        if _GARBLED.search(line)
    ]


def test_the_pattern_catches_the_known_shapes():
    bad = ("a â€” b", "cafÃ©", "Â§ 4", "x�y")
    good = ("a — b", "café", "§ 4", "Kelly Ford")
    for text in bad:
        assert _GARBLED.search(text), text
    for text in good:
        assert not _GARBLED.search(text), text


@pytest.mark.parametrize("root", sorted(_GLOBS))
def test_no_garbled_text(root):
    problems = [line for path in _files(root) for line in _garbled_lines(path)]
    assert not problems, "Garbled text (UTF-8 read as Windows-1252):\n" + "\n".join(problems)
