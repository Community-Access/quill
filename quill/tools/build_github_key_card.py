"""Generate the GitHub Workbench key cards: print and braille (GitHub PRD D15, GH-R-115).

Two files from the one key table the window is built from
(:data:`quill.core.github.workbench_window_menu.WINDOW_MENU`, with its second
keys), so a card can never teach a key the window does not have:

- ``docs/github/key-card.html``: an accessible one-page card to print or
  read: a heading per menu, a two-column table per menu with header cells,
  the language set, and nothing conveyed by layout alone.
- ``docs/github/key-card-braille-ready.txt``: the same keys as plain ASCII
  laid out for a braille page: at most 40 characters a line and 25 lines a
  page, a form feed between pages, no tables. Open it in QUILL's Braille
  Mode, or give it to a braille translator, to make the BRF to emboss or
  read on a display; it reads as it is on a 40-cell display too.

``tests/unit/tools/test_github_key_card.py`` fails when either committed file
differs from what this writes. Regenerate with::

    python -m quill.tools.build_github_key_card --write
"""

from __future__ import annotations

import argparse
import html
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = _REPO_ROOT / "docs" / "github" / "key-card.html"
BRAILLE_PATH = _REPO_ROOT / "docs" / "github" / "key-card-braille-ready.txt"
TITLE = "GitHub Workbench Key Card"
#: A braille page: cells a line and lines a page (a common embosser page).
CELLS, LINES = 40, 25

_ALSO_NAMES = {
    "filter_alias": "Filter box (second key)",
    "inbox_home": "Inbox (second key)",
    "refresh_alias": "Refresh (second key)",
    "remove": "Remove the selected row, safely",
    "cancel_run": "Cancel a run, asking first",
}


def card() -> list[tuple[str, list[tuple[str, str]]]]:
    """(menu title, [(key, what it does)]) for every menu, then the second keys."""
    from quill.core.github.workbench_window_menu import ALIAS_KEYS, CONTROL_KEYS, WINDOW_MENU
    from quill.core.workbench.menus import MenuSub

    sections: list[tuple[str, list[tuple[str, str]]]] = []
    for spec in WINDOW_MENU:
        rows: list[tuple[str, str]] = []
        for row in spec.rows:
            inner = row.rows if isinstance(row, MenuSub) else (row,)
            prefix = f"{row.title.replace('&', '')}: " if isinstance(row, MenuSub) else ""
            for item in inner:
                if item is not None and item.key:
                    label = item.label.replace("&", "").rstrip(".").rstrip()
                    rows.append((item.key, prefix + label))
        if rows:
            sections.append((spec.title.replace("&", ""), rows))
    also = [
        (key, _ALSO_NAMES.get(command_id.rsplit(".", 1)[-1], command_id))
        for command_id, key in {**ALIAS_KEYS, **CONTROL_KEYS}.items()
    ]
    sections.append(("Also", also))
    return sections


def _ascii(text: str) -> str:
    """*text* in printable ASCII: braille-ready files carry nothing else."""
    swaps = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-"}
    out = "".join(swaps.get(ch, ch) for ch in text)
    return out.encode("ascii", "ignore").decode("ascii")


def render_html() -> str:
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{TITLE}</title>",
        "<style>",
        "body { font-family: Segoe UI, Arial, sans-serif; font-size: 12pt; margin: 1.5em; }",
        "h1 { font-size: 18pt; } h2 { font-size: 13pt; margin-top: 1em; }",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { border: 1px solid; padding: 0.15em 0.4em; text-align: left; }",
        "th[scope=col] { font-weight: bold; } td:first-child { white-space: nowrap; }",
        "@media print { body { font-size: 9pt; margin: 0; } h2 { break-after: avoid; } }",
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        f"<h1>{TITLE}</h1>",
        "<p>Every key in the GitHub Workbench window, in QUILL and QUILL Lite, by menu. "
        "F1 is help for where you are; Shift+F1 lists what you can do with the selection. "
        "Generated from the window's own key table.</p>",
    ]
    for title, rows in card():
        lines += [
            f"<h2>{html.escape(title)}</h2>",
            f"<table><caption>{html.escape(title)} keys</caption>",
            '<thead><tr><th scope="col">Key</th><th scope="col">What it does</th></tr></thead>',
            "<tbody>",
        ]
        for key, what in rows:
            lines.append(f"<tr><td>{html.escape(key)}</td><td>{html.escape(what)}</td></tr>")
        lines += ["</tbody>", "</table>"]
    lines += ["</main>", "</body>", "</html>"]
    return "\n".join(lines) + "\n"


def render_braille() -> str:
    """The card in braille-page shape: 40 cells, 25 lines, form feeds between pages."""
    flowing: list[str] = [_ascii(TITLE).upper().center(CELLS).rstrip(), ""]
    for title, rows in card():
        flowing += ["", _ascii(title).upper()]
        for key, what in rows:
            wrapped = textwrap.wrap(
                _ascii(f"{key}: {what}"),
                width=CELLS,
                subsequent_indent="  ",
                break_on_hyphens=False,
            )
            flowing += wrapped
    pages: list[list[str]] = [[]]
    for line in flowing:
        if len(pages[-1]) >= LINES:
            pages.append([])
        if not pages[-1] and not line:
            continue  # no page starts with a blank line
        pages[-1].append(line)
    return "\x0c\n".join("\n".join(page) + "\n" for page in pages if page)


def outputs() -> dict[Path, str]:
    return {HTML_PATH: render_html(), BRAILLE_PATH: render_braille()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write both cards")
    args = parser.parse_args(argv)
    drifted = []
    for path, wanted in outputs().items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if args.write:
            path.write_text(wanted, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(_REPO_ROOT)}")
        elif current != wanted:
            drifted.append(str(path.relative_to(_REPO_ROOT)))
    if drifted:
        print(f"{', '.join(drifted)} drifted; run with --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
