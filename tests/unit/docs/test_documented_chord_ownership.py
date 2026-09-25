"""GATE-DOCKEY: a chord a document attributes to a command must be that command's.

``tests/unit/ui/test_documentation_chords.py`` is the first half of this: every
chord a guide *names* must be a chord something binds. Its own docstring says
what it cannot catch, and names the defect that motivated it:

    That particular defect is not one this gate can catch [...] both chords are
    still bound to something, so nothing here is stale -- they are
    **misattributed**, which needs a claim about which command owns a key and no
    document states that machine-readably.

This is that gate. A document *does* state the claim machine-readably whenever it
writes a command's name beside a chord -- "**Tools > Customize Features**
(**Ctrl+Alt+F10**)", "**Snippets -- Alt+Shift+I**", "| **F7** | Check Spelling |"
-- and QuillLite's command table is the authority for what that chord should be.

The 2026-09-24 pass found six of these across the shipped documents, every one of
them pointing at a real command:

* Back Up Settings and Restore Settings written as ``Ctrl+Alt+Shift+Q`` and
  ``Ctrl+Alt+Shift+D``; the first is Remove Quote Marks and the second is bound
  to nothing.
* Customize Features as ``Ctrl+Alt+Shift+F``.
* The Heading Organizer as ``Ctrl+Alt+Shift+O``, which is **Sound Scheme** -- so
  following the changelog opened the wrong window rather than none.
* Snippets as ``Ctrl+Shift+Insert``.
* Spelling for This Word as ``Shift+F7``.

"Nothing happened" is a guess somebody recovers from. "Something else happened"
is one they have to undo, and for a listener it is a window they must now
identify before they can leave it.

**Only pairings are checked.** A chord named on its own, a chord belonging to
Windows or to the screen reader, a chord in a sentence about history -- none of
those states a claim this gate can test, and the sibling gate covers the ones
that matter. **Aliases count as the command's own**: ``Alt+F7`` really is Next
Misspelling, and a document is right to say so.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core.lite.commands import COMMANDS, plain_label
from quill.core.lite.keymap import DEFAULT_ALIASES, chord_identity

_ROOT = Path(__file__).resolve().parents[3]

#: Every QuillLite document that attributes keys to commands. The PRD is here
#: where the sibling gate leaves it out, and the difference is the point: a PRD
#: quoting a *rejected* chord is fine, and a PRD saying "Customize Features
#: (Ctrl+Alt+Shift+F)" is wrong in exactly the way this gate exists to catch.
DOCUMENTS: tuple[Path, ...] = (
    _ROOT / "standalone" / "quilllite" / "docs" / "userguide.md",
    _ROOT / "standalone" / "quilllite" / "docs" / "announcement.md",
    _ROOT / "standalone" / "quilllite" / "docs" / "release-notes-1.0.md",
    _ROOT / "standalone" / "quilllite" / "docs" / "CHANGELOG.md",
    _ROOT / "standalone" / "quilllite" / "docs" / "prd.md",
    _ROOT / "docs" / "qa" / "quilllite-signoff.md",
)

#: A chord as any of these documents spells one. The trailing class is wide
#: because QuillLite binds ``Ctrl+,``, ``Ctrl+/``, ``Ctrl+[`` and ``Ctrl+;``.
_CHORD = r"(?:Ctrl|Alt|Shift|Win)\+[A-Za-z0-9+.,;'\[\]/=<>\-]{1,24}|F\d{1,2}"

#: A command name as a document writes one, optionally with its menu path in
#: front of it. The path is stripped before lookup -- what is being checked is
#: the chord against the leaf, because two commands never share a leaf name in
#: a way this could confuse (see ``_AMBIGUOUS``).
_NAME = r"[A-Za-z][A-Za-z0-9 .&'▸>/]*?"

#: How the two appear beside each other. Order matters only in that the chord
#: and the name swap places between the two halves of each pair.
_SEPARATORS = r"(?:\s*[—–,:-]\s*|\s+(?:is|on|opens)\s+|\s*\(\s*)"
_INSIDE_NAME_FIRST = re.compile(rf"^({_NAME})\.{{0,3}}{_SEPARATORS}({_CHORD})\)?\.?$")
_INSIDE_CHORD_FIRST = re.compile(rf"^({_CHORD}){_SEPARATORS}({_NAME})\.{{0,3}}$")
_SPAN = re.compile(r"\*\*([^*]{3,90}?)\*\*")
_ACROSS_NAME_FIRST = re.compile(
    rf"\*\*({_NAME})\.{{0,3}}\*\*[\s—–-]*\(?\s*\*?\*?({_CHORD})\*?\*?\s*\)?"
)
_ACROSS_CHORD_FIRST = re.compile(rf"\*\*({_CHORD})\*\*\s*\(\*\*({_NAME})\.{{0,3}}\*\*\)")
_TABLE_ROW = re.compile(rf"^\|\s*\*\*({_CHORD})\*\*\s*\|\s*([^|]+?)\s*\|")

#: Leaf names the command table itself uses twice, where the menu path is the
#: only thing that tells them apart. "Status Bar" is View's toggle and
#: Navigate's focus command, on different chords and both correct.
_AMBIGUOUS = frozenset({"status bar"})


def _bindings() -> dict[str, tuple[frozenset[str], tuple[str, ...]]]:
    """Leaf command name (lowercased) to the chord identities it answers to.

    The primary and its alias both count: a document that teaches ``Alt+F7`` for
    Next Misspelling is teaching a key that works.
    """
    table: dict[str, tuple[set[str], list[str]]] = {}
    for _menu, label, key, handler, kind in COMMANDS:
        if kind in {"sep", "sub"} or not key:
            continue
        name = plain_label(label).rstrip(".").lower()
        if name in _AMBIGUOUS:
            continue
        identities = {chord_identity(key)}
        spellings = [key]
        alias = DEFAULT_ALIASES.get(handler, "")
        if alias:
            identities.add(chord_identity(alias))
            spellings.append(alias)
        if name in table:
            table[name][0].update(identities)
            table[name][1].extend(spellings)
        else:
            table[name] = (identities, spellings)
    return {name: (frozenset(ids), tuple(keys)) for name, (ids, keys) in table.items()}


def _leaf(name: str) -> str:
    """The command name out of a menu path, lowercased and de-fluffed."""
    leaf = re.split(r"[▸>]", name)[-1].strip().rstrip(".").lower()
    return re.sub(r"^(?:the|a|an)\s+", "", leaf)


def _tidy(chord: str) -> str:
    """A chord with the sentence's punctuation taken back off it.

    The whole difficulty is that four of QuillLite's chords **end** in the
    punctuation a sentence would: ``Ctrl+,`` is Preferences, ``Ctrl+Shift+,`` is
    Shrink Font, ``Ctrl+;`` is Start Selection's alias, and ``Ctrl+Shift+.`` is
    Grow Font. So a character only comes off when something other than the ``+``
    is in front of it -- ``Alt+Shift+F9.`` loses its dot and ``Ctrl+,`` keeps its
    comma. Stripping unconditionally turned every one of those four into a false
    positive that read, absurdly, "documented on Ctrl+, but it is bound to
    Ctrl+,".
    """
    while len(chord) > 2 and chord[-1] in ".,:;)" and chord[-2] != "+":
        chord = chord[:-1]
    return chord


def _claims(text: str) -> list[tuple[int, str, str]]:
    """Every ``(line number, command name, chord)`` the document asserts."""
    found: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in _SPAN.finditer(line):
            inner = match.group(1).strip()
            if (hit := _INSIDE_NAME_FIRST.match(inner)) is not None:
                found.append((number, hit.group(1), hit.group(2)))
            if (hit := _INSIDE_CHORD_FIRST.match(inner)) is not None:
                found.append((number, hit.group(2), hit.group(1)))
        for match in _ACROSS_NAME_FIRST.finditer(line):
            found.append((number, match.group(1), match.group(2)))
        for match in _ACROSS_CHORD_FIRST.finditer(line):
            found.append((number, match.group(2), match.group(1)))
        for match in _TABLE_ROW.finditer(line):
            found.append((number, match.group(2), match.group(1)))
    return found


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.name)
def test_every_documented_chord_belongs_to_the_command_beside_it(document: Path) -> None:
    assert document.is_file(), f"{document} is in the corpus and not on disk"
    bindings = _bindings()
    wrong: list[str] = []
    for number, name, chord in _claims(document.read_text(encoding="utf-8")):
        entry = bindings.get(_leaf(name))
        if entry is None:
            continue  # not a command of QuillLite's; the sibling gate has it
        try:
            identity = chord_identity(_tidy(chord))
        except ValueError:
            continue  # unparseable here means it is prose, not a claim
        if identity not in entry[0]:
            wrong.append(
                f"{document.name}:{number}: '{name}' is documented on {_tidy(chord)}, "
                f"but it is bound to {' / '.join(entry[1])}"
            )
    assert not wrong, "A document attributes a key to the wrong command:\n" + "\n".join(wrong)


def test_the_gate_would_catch_the_defect_it_was_written_for() -> None:
    """The six real ones, in the shapes the documents actually used.

    Without this the gate could pass by matching nothing at all, which is how a
    regex-based check rots: somebody rewords a paragraph, the pattern stops
    finding it, and the gate goes green on a document it no longer reads.
    """
    bindings = _bindings()
    samples = [
        "**Tools ▸ Back Up Settings...** (**Ctrl+Alt+Shift+Q**) writes your configuration",
        "**Tools ▸ Customize Features** (**Ctrl+Alt+Shift+F**) lets you switch parts off",
        "- **The Heading Organizer — Ctrl+Alt+Shift+O.** Every heading in one list",
        "- **Snippets — Ctrl+Shift+Insert.** A list of every abbreviation",
        "| **Shift+F7** | Spelling for This Word |",
    ]
    for line in samples:
        claims = _claims(line)
        assert claims, f"the gate no longer reads this shape: {line}"
        assert any(
            (entry := bindings.get(_leaf(name))) is not None
            and chord_identity(_tidy(chord)) not in entry[0]
            for _number, name, chord in claims
        ), f"the gate would not have caught: {line}"


def test_the_gate_accepts_a_right_answer_and_an_alias() -> None:
    """The other half: a correct pairing, and a second key that really works."""
    bindings = _bindings()
    for line in (
        "**Tools ▸ Customize Features** (**Ctrl+Alt+F10**) lets you switch parts off",
        "| **Alt+F7** | Next Misspelling |",
        "| **F12** | Save As... |",
    ):
        for _number, name, chord in _claims(line):
            entry = bindings.get(_leaf(name))
            if entry is None:
                continue
            assert chord_identity(_tidy(chord)) in entry[0], f"false positive on: {line}"
