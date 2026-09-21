"""A wizard page and the wizard's own buttons share one window (GATE-14 gap).

GATE-14 scopes a class at a time, which is right for two windows and wrong for
these two: every Audio Studio page is a child of one ``wx.Dialog``, so a page
control and the ``&Next >`` button really do compete for Alt+N. Windows does not
press a duplicated mnemonic -- it cycles focus between the claimants and waits
for Enter -- so a page that claims a navigation letter cannot be left by
keyboard at all.

That is not hypothetical. The Voices page claimed ``N`` for "Remove language"
and the Chapters page claimed it for "Pause between sentences", and the wizard
could not be advanced past step 3, then step 4, from the keyboard. The nightly
UIA suite had been recording it for weeks as "QUILL never announced anything
containing 'How should chapters work'", which names neither a key nor a button.

What this gate checks, per page class:

* no two controls on one page claim the same letter; and
* no control claims a letter the wizard's own navigation shows on that page.

Which navigation buttons are showing is read from ``wizard.py`` itself, both the
labels and the ``Show()`` rules, so renaming a button updates the gate instead
of silently voiding it. ``< &Back`` is on every page; ``&Next >`` on all but the
last; ``Skip to su&mmary`` on the middle pages; ``&Start`` only on the last. The
conservative reading is used -- Back, Next and Skip are treated as present on
every page -- because a page's position in a journey is data, not structure, and
a page that moves must not quietly acquire a collision.

Source-level, like the access-key gates beside it: building the wizard needs a
``wx.App`` and a display, and the literals are what a reviewer reads and what a
regression would change.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

_PAGES_DIR = Path(__file__).resolve().parents[3] / "quill" / "ui" / "audio_studio"
_PAGE_MODULES = ("pages_start.py", "pages_documents.py", "pages_audio.py", "pages_shared.py")
_WIZARD = _PAGES_DIR / "wizard.py"

#: The navigation buttons treated as present on every page. ``&Start`` is left
#: out: it shows only on the last page, and reserving its letter everywhere
#: would cost "&Source folder" its natural key for nothing.
_ALWAYS_SHOWING = ("_back_btn", "_next_btn", "_skip_btn")


def _mnemonic(label: str) -> str:
    """The Alt letter *label* claims, upper-cased, or ``""``. ``&&`` is literal."""
    index = label.find("&")
    while index != -1 and label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label):
        return ""
    char = label[index + 1]
    return char.upper() if char.isalnum() else ""


def _ampersanded_literals(source: str, node: ast.AST) -> list[str]:
    """Every distinct string literal carrying a ``&`` inside *node*.

    A regex over the class's own source rather than a walk of ``wx.<Control>``
    calls, because these pages hand most of their labels to helpers
    (``self.add_label(...)``, ``self._tag_field(grid, ...)``) or read them from
    tuple tables -- which is exactly the shape GATE-14 cannot attribute, and
    exactly where these collisions were hiding.
    """
    segment = ast.get_source_segment(source, node) or ""
    seen: list[str] = []
    for literal in re.findall(r'"([^"\n]*&[^"\n]*)"', segment):
        if literal not in seen:
            seen.append(literal)
    return seen


def _chrome_letters() -> dict[str, str]:
    """``letter -> button label`` for the navigation showing on every page."""
    source = _WIZARD.read_text(encoding="utf-8")
    letters: dict[str, str] = {}
    for attribute in _ALWAYS_SHOWING:
        match = re.search(
            rf"self\.{re.escape(attribute)}\s*=\s*wx\.Button\((?:.|\n)*?label=_\(\"([^\"]+)\"\)",
            source,
        )
        assert match, f"{_WIZARD.name} no longer builds {attribute} with a literal label"
        label = match.group(1)
        letter = _mnemonic(label)
        if letter:
            letters[letter] = label
    return letters


def _page_classes() -> list[tuple[str, str, ast.ClassDef]]:
    out: list[tuple[str, str, ast.ClassDef]] = []
    for name in _PAGE_MODULES:
        path = _PAGES_DIR / name
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Page"):
                out.append((name, source, node))
    return out


def test_the_gate_is_actually_looking_at_something() -> None:
    """A scanner that finds nothing passes everything."""
    pages = _page_classes()
    assert len(pages) >= 6, f"only {len(pages)} wizard pages found; the scan has lost them"
    total = sum(len(_ampersanded_literals(source, node)) for _, source, node in pages)
    assert total >= 40, f"only {total} labels found across the wizard pages"
    assert _chrome_letters(), "no navigation mnemonics read from wizard.py"


def test_no_two_controls_on_one_wizard_page_claim_one_letter() -> None:
    clashes: list[str] = []
    for module, source, node in _page_classes():
        claims: dict[str, list[str]] = defaultdict(list)
        for label in _ampersanded_literals(source, node):
            letter = _mnemonic(label)
            if letter:
                claims[letter].append(label)
        for letter, labels in sorted(claims.items()):
            if len(labels) > 1:
                clashes.append(f"{module}::{node.name}: Alt+{letter} is claimed by {labels}")
    assert not clashes, "two controls on one wizard page claiming one key:\n  " + "\n  ".join(
        clashes
    )


def test_no_wizard_page_steals_a_navigation_letter() -> None:
    """Back, Next and Skip must reach their buttons from every page."""
    chrome = _chrome_letters()
    clashes: list[str] = []
    for module, source, node in _page_classes():
        for label in _ampersanded_literals(source, node):
            letter = _mnemonic(label)
            if letter in chrome:
                clashes.append(
                    f"{module}::{node.name}: {label!r} claims Alt+{letter}, which belongs to "
                    f"the wizard's {chrome[letter]!r} button on this page"
                )
    assert not clashes, (
        "a wizard page claiming a navigation key (Windows cycles instead of "
        "pressing, so the page cannot be left by keyboard):\n  " + "\n  ".join(clashes)
    )
