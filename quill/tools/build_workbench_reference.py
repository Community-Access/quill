"""Generate the GitHub Workbench tables in ``docs/github/workbench-reference.md``.

GitHub PRD section 7 and D8: the reference is generated from the same tables
the window is built from -- the Navigator tree, the menu bar and its keys,
the context menus, Workbench Options and the glossary, each with its authored
help -- so it cannot drift. Only the region between the two markers is
written; the prose around it stays hand-written.

``tests/unit/tools/test_workbench_reference.py`` fails when the committed
region differs from what this would write. Regenerate with::

    python -m quill.tools.build_workbench_reference --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = _REPO_ROOT / "docs" / "github" / "workbench-reference.md"
BEGIN = "<!-- BEGIN GENERATED: python -m quill.tools.build_workbench_reference --write -->"
END = "<!-- END GENERATED -->"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def generate() -> str:
    """The generated region, markers included."""
    from quill.core.github import workbench_help as catalogue
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.core.github.workbench_window_menu import WINDOW_MENU, WORKBENCH_KEYS
    from quill.core.workbench.menus import MenuSub, all_rows

    out = [
        BEGIN,
        "",
        "## The GitHub Workbench window, generated",
        "",
        "Everything below is generated from the tables the window is built from. "
        "The window is the GitHub Workbench; the classic GitHub Items and Explore "
        "GitHub windows stay for one release behind Workbench Options, "
        "Use the classic GitHub windows.",
        "",
        "### The Navigator tree",
        "",
        "| Node | Under | What it is |",
        "| --- | --- | --- |",
    ]
    for template, node in GITHUB_TREE.all_nodes():
        where = template or "the top"
        if node.parent:
            where = f"{where}, {node.parent}" if template else node.parent
        words = catalogue.node_help_for(template, node.key)
        out.append(f"| {_cell(node.label)} (`{template}:{node.key}`) | {where} | {_cell(words)} |")
    out += ["", "### The menu bar and its keys", ""]
    for spec in WINDOW_MENU:
        out += [
            f"#### {spec.title.replace('&', '')}",
            "",
            "| Row | Key | What it does |",
            "| --- | --- | --- |",
        ]
        for row in spec.rows:
            if isinstance(row, MenuSub):
                title = row.title.replace("&", "")
                for inner in row.rows:
                    if inner is not None:
                        label = f"{title} > {inner.label.replace('&', '')}"
                        key = inner.key or "(submenu letter)"
                        out.append(f"| {_cell(label)} | {key} | {_cell(inner.help)} |")
                if row.dynamic:
                    out.append(f"| {_cell(title)} | (submenu letter) | {_cell(row.help)} |")
            elif row is not None:
                label = row.label.replace("&", "")
                out.append(f"| {_cell(label)} | {row.key} | {_cell(row.help)} |")
        out.append("")
    out += [
        "Keys the window answers that are not menu rows:",
        "",
        "| Key | Command id |",
        "| --- | --- |",
    ]
    menu_ids = {row.command_id for _spec, row in all_rows(WINDOW_MENU)}
    for command_id, key in WORKBENCH_KEYS.items():
        if command_id not in menu_ids:
            out.append(f"| {key} | `{command_id}` |")
    out += ["", "### Context menus, by row type", ""]
    for kind in GITHUB_ACTIONS.row_types:
        top, more = GITHUB_ACTIONS.menu_for(kind)
        shown = ", ".join(row.label for row in top[:-1])
        extra = f"; More: {', '.join(row.label for row in more)}" if more else ""
        out.append(f"- **{kind}**: {shown}{extra}; {top[-1].label}")
    out += [
        "",
        "### Workbench Options",
        "",
        "| Setting | Page | Label | What it does |",
        "| --- | --- | --- | --- |",
    ]
    for name, (page, label, help_text) in catalogue.PREF_HELP.items():
        clean = label.replace("&", "").rstrip(":")
        out.append(f"| `{name}` | {page} | {_cell(clean)} | {_cell(help_text)} |")
    out += ["", "### GitHub words", ""]
    for term, text in sorted(catalogue.GLOSSARY.items()):
        out.append(f"- **{term}**: {text}")
    out += ["", END]
    return "\n".join(out) + "\n"


def render(text: str) -> str:
    """*text* with its generated region replaced (or appended when it has none)."""
    region = generate()
    if BEGIN in text and END in text:
        head = text[: text.index(BEGIN)]
        tail = text[text.index(END) + len(END) :].lstrip("\n")
        return head + region + (("\n" + tail) if tail else "")
    return text.rstrip("\n") + "\n\n" + region


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the generated region")
    args = parser.parse_args(argv)
    current = OUTPUT_PATH.read_text(encoding="utf-8")
    wanted = render(current)
    if args.write:
        OUTPUT_PATH.write_text(wanted, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT_PATH.relative_to(_REPO_ROOT)}")
        return 0
    if wanted != current:
        print("docs/github/workbench-reference.md has drifted; run with --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
