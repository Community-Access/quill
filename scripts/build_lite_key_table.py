"""Regenerate the key table in QuillLite's user guide from the command table.

The guide's key list has to be the keys that are actually bound. A guide that
names a key the app does not bind sends somebody to press nothing -- and for a
screen-reader user that is not a moment of confusion, it is a minute of
hunting a menu to find out whether the key or the reader is at fault.

``tests/unit/core/lite/test_lite_docs.py`` already asserts that every bound key
and every command name appears in the guide. This script is the other half:
rather than being told what is missing and hand-patching a Markdown table,
regenerate the block between ``<!-- keys:start -->`` and ``<!-- keys:end -->``
from :data:`quill.core.lite.commands.COMMANDS`, which is the same list the menu
bar is built from. There is then no third place for the two to disagree.

Run after changing the command table::

    python scripts/build_lite_key_table.py          # rewrite the guide
    python scripts/build_lite_key_table.py --check  # fail if it has drifted

The prose outside the markers is authored and is never touched.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.lite.commands import COMMANDS, plain_label, split_menu  # noqa: E402
from quill.core.lite.keymap import DEFAULT_ALIASES  # noqa: E402

GUIDE = REPO_ROOT / "standalone" / "quilllite" / "docs" / "userguide.md"

_START = "<!-- keys:start -->"
_END = "<!-- keys:end -->"

#: Keys the table cannot carry, because they are built per window from however
#: many documents or recent files there happen to be.
_PER_WINDOW = [
    ("**Alt+1** to **Alt+9**", "Go to that numbered document"),
    ("**Alt+Shift+1** to **Alt+Shift+9**", "Reopen that recent file"),
]

_PREAMBLE = """
Generated from the same table that builds the menus, so it cannot drift from
what is actually bound. **Ctrl+F1** shows this list inside the app.
"""

_POSTAMBLE = """
Two of these read differently on a keyboard than in a table: **Ctrl+Shift+>**
and **Ctrl+Shift+<** are the keys your fingers know, and they are listed above
as `Ctrl+Shift+.` and `Ctrl+Shift+,` because that is the same physical key and
the spelling wx understands.
"""

#: The heading over the second-chord table, and the sentence that explains it.
#: These are real bindings that are in no menu label, so a table built only from
#: the menu rows would be telling somebody their whole keyboard and leaving six
#: keys out of it.
_ALIAS_PREAMBLE = """
### Second keys

A few commands answer to two keys. The first is the one the menu shows; the
second is here because it is the key a hand trained on Word or on a home-row
editor already reaches for. Both work, always, and rebinding the first in the
Keyboard Manager leaves the second alone.
"""


def render() -> str:
    """The whole block between the markers, ready to drop in."""
    lines: list[str] = [_PREAMBLE.strip(), ""]
    # Grouped by menu path rather than by run of adjacent rows. The Tools menu
    # is the reason: its rows are interrupted by the Spelling submenu and then
    # resume, so a generator that started a new heading every time the path
    # changed printed "### Tools" twice, with five rows stranded under the
    # second one. Somebody hunting Quiet Mode found the first table, did not
    # find it there, and had no reason to suppose there was a second table of
    # the same name further down.
    order: list[str] = []
    grouped: dict[str, list[tuple[str, str]]] = {}
    for menu, label, key, _handler, kind in COMMANDS:
        # "sub" rows are submenu titles: no key of their own, and the submenu
        # they name gets its own heading from the rows that do carry keys.
        if kind in {"sep", "sub"}:
            continue
        if menu not in grouped:
            order.append(menu)
            grouped[menu] = []
        grouped[menu].append((key, plain_label(label)))
    for menu in order:
        if lines and lines[-1] != "":
            lines.append("")  # a heading needs air above it, in Markdown and by ear
        parent, child = split_menu(menu)
        # "Edit|Selection" is the table's way of saying "submenu"; a reader
        # wants the path, not the separator.
        heading = f"{plain_label(parent)} ▸ {plain_label(child)}" if child else plain_label(parent)
        lines += [f"### {heading}", "", "| Key | Command |", "|---|---|"]
        lines += [f"| **{key}** | {label} |" for key, label in grouped[menu]]
    lines += ["", "### Built per window", "", "| Key | Command |", "|---|---|"]
    lines += [f"| {key} | {what} |" for key, what in _PER_WINDOW]
    # The aliases are bound, and they appear in no menu label -- so a table
    # built only from the menu rows tells somebody their whole keyboard and
    # leaves six working keys out of it.
    titles = {
        handler: (plain_label(label), key)
        for _menu, label, key, handler, kind in COMMANDS
        if kind not in {"sep", "sub"} and handler
    }
    lines += ["", _ALIAS_PREAMBLE.strip(), ""]
    lines += ["| Second key | Command | The key the menu shows |", "|---|---|---|"]
    for handler, alias in DEFAULT_ALIASES.items():
        name, primary = titles.get(handler, (handler, ""))
        lines.append(f"| **{alias}** | {name} | **{primary}** |")
    lines += ["", _POSTAMBLE.strip(), ""]
    return "\n".join(lines)


def rebuilt(text: str) -> str:
    """*text* with the block between the markers replaced."""
    if _START not in text or _END not in text:
        raise SystemExit(f"{GUIDE} has no {_START} / {_END} markers to write between.")
    head, rest = text.split(_START, 1)
    _stale, tail = rest.split(_END, 1)
    return f"{head}{_START}\n\n{render()}\n{_END}{tail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the guide's table is not what the command table renders",
    )
    args = parser.parse_args()

    text = GUIDE.read_text(encoding="utf-8")
    updated = rebuilt(text)
    if args.check:
        if updated != text:
            print(f"{GUIDE} is out of date. Run: python scripts/build_lite_key_table.py")
            return 1
        print(f"{GUIDE} key table is current.")
        return 0
    if updated == text:
        print(f"{GUIDE} key table already current.")
        return 0
    GUIDE.write_text(updated, encoding="utf-8", newline="")
    print(f"Rewrote the key table in {GUIDE}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
