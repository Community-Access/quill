"""Check the GitHub PRD's Appendix A, B and C against the code, and write their tables.

Appendix A and B say where every retired window's view, button and command
went ("nothing dropped"); Appendix C says, for every object, its Properties
sheet and its filters. Their rows are data
(:mod:`quill.core.github.appendix_ab_rows`, :mod:`quill.core.github.appendix_c_rows`)
and the views are read from their own registries, so this tool can:

- resolve every home a row names (a node, a menu row, a context-menu command,
  a sheet page or field, a Workbench Options choice, an editor command, a
  control inside a window), and fail on one that has gone;
- fail when a retired window gains a control, the editor's GitHub menu gains
  a row, or the action table gains a row type, that no row accounts for;
- fail when an object's sheet, row type or filter qualifier is not real;
- write the three tables into the PRD between their markers.

Run ``python -m quill.tools.github_appendix_reference`` to check (exit 1 on a
problem or a drifted table) and ``--write`` to rewrite the tables.
``tests/unit/core/workbench/test_github_appendix_mappings.py`` runs the same.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
PRD_PATH = (
    _REPO_ROOT
    / "docs"
    / "Product Requirement Documents and Specifications"
    / "github-workbench-prd.md"
)
#: The retired windows whose controls Appendix A must account for.
RETIRED_WINDOWS = ("quill/ui/github_items_dialog.py", "quill/ui/github_explore_dialog.py")
_TEMPLATE_WORDS = {"repository": "Repository", "person": "Person", "organization": "Organization"}


def _begin(name: str) -> str:
    return (
        f"<!-- BEGIN GENERATED {name}: python -m quill.tools.github_appendix_reference --write -->"
    )


def _end(name: str) -> str:
    return f"<!-- END GENERATED {name} -->"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


# -- the registries -----------------------------------------------------------------


@dataclasses.dataclass
class _Registries:
    tree: Any
    menu: set[str]
    actions: Any
    sheets: dict[str, Any]
    prefs: set[str]
    pref_pages: set[str]
    editor: set[str]
    doors: dict[str, str]
    repo_actions: set[str]
    new_here: set[str]


def _registries() -> _Registries:
    from quill.core.github import workbench_menu as editor_menu
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.item_shortcuts import NEW_HERE
    from quill.core.github.sheet_catalog import SHEETS
    from quill.core.github.workbench_help import PREF_HELP, PREF_PAGES
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.core.github.workbench_window_menu import WINDOW_MENU
    from quill.core.workbench.menus import all_rows
    from quill.ui.github_workbench_actions import REPOSITORY_ACTIONS
    from quill.ui.github_workbench_commands import ADMIN_DOORS, WORKBENCH_NODES

    editor = {row.command_id for row in editor_menu.ALL_ROWS} | {
        row.command_id
        for row in editor_menu.command_rows((
            *editor_menu.REPOSITORY_ROWS,
            *editor_menu.LOCAL_GIT_ROWS,
        ))
    }
    doors = dict(WORKBENCH_NODES) | {cid: node for cid, (node, _then) in ADMIN_DOORS.items()}
    return _Registries(
        tree=GITHUB_TREE,
        menu={
            row.command_id.removeprefix("github.workbench.") for _m, row in all_rows(WINDOW_MENU)
        },
        actions=GITHUB_ACTIONS,
        sheets=SHEETS,
        prefs=set(PREF_HELP),
        pref_pages=set(PREF_PAGES),
        editor=editor,
        doors=doors,
        repo_actions={command for _label, command in REPOSITORY_ACTIONS},
        new_here=set(NEW_HERE),
    )


def _node_exists(reg: _Registries, key: str) -> bool:
    template, sep, name = key.partition(".")
    if sep:
        try:
            reg.tree.template_node(template, name)
        except KeyError:
            return False
        return True
    try:
        reg.tree.node(key)
    except KeyError:
        return any(node.key == key for _t, node in reg.tree.all_nodes())
    return True


def _sheet_problem(reg: _Registries, spec: str) -> str:
    kind, _sep, rest = spec.partition(".")
    sheet = reg.sheets.get(kind)
    if sheet is None:
        return f"no {kind} sheet"
    page_key, _sep, field = rest.partition(".")
    pages = {page.key: page for page in sheet.sheet.pages}
    if page_key and page_key not in pages:
        return f"the {kind} sheet has no {page_key} page"
    if field and field not in {f.key for f in pages[page_key].fields}:
        return f"the {kind} sheet's {page_key} page has no {field} field"
    return ""


def resolve(ref: str, reg: _Registries | None = None) -> str:
    """What is wrong with *ref* ("" when it names something real)."""
    reg = reg or _registries()
    kind, sep, value = ref.partition(":")
    if not sep or not value:
        return f"{ref!r} is not a ref"
    if kind == "node":
        return "" if _node_exists(reg, value) else f"no node {value}"
    if kind == "menu":
        return "" if value in reg.menu else f"no menu row {value}"
    if kind == "row":
        row_type, _sep, verb = value.partition(".")
        if row_type not in reg.actions.row_types:
            return f"no row type {row_type}"
        commands = {r.command_id for r in reg.actions.rows_for(row_type)}
        return "" if f"github.workbench.{verb}" in commands else f"no {verb} on {row_type} rows"
    if kind == "new":
        return "" if value in reg.new_here else f"New Here makes nothing in {value}"
    if kind == "sheet":
        return _sheet_problem(reg, value)
    if kind == "pref":
        return "" if value in reg.prefs else f"no Workbench option {value}"
    if kind == "prefpage":
        return "" if value in reg.pref_pages else f"no Workbench Options page {value}"
    if kind == "editor":
        return "" if value in reg.editor else f"no editor GitHub menu row {value}"
    if kind == "door":
        if value not in reg.doors:
            return f"{value} opens nothing in the Workbench"
        node = reg.doors[value]
        return "" if not node or _node_exists(reg, node) else f"{value} opens missing node {node}"
    if kind == "repoaction":
        return "" if value in reg.repo_actions else f"Repository Actions... has no {value}"
    if kind == "code":
        path, _sep, text = value.partition("#")
        file = _REPO_ROOT / path
        if not file.is_file():
            return f"no file {path}"
        return "" if text in file.read_text(encoding="utf-8") else f"{path} has no {text!r}"
    return f"unknown ref kind {kind}"


# -- Appendix A and B ----------------------------------------------------------------


def _norm(label: str) -> str:
    return label.replace("&", "").replace("\u2026", "...").strip()


def retired_labels() -> set[str]:
    """Every button and captioned choice the retired windows still build."""
    found: set[str] = set()
    for path in RETIRED_WINDOWS:
        text = (_REPO_ROOT / path).read_text(encoding="utf-8")
        found |= set(re.findall(r'wx\.Button\([^)]*?label="([^"]+)"', text))
        found |= set(re.findall(r'wx\.Button\(\s*panel,\s*wx\.ID_CANCEL,\s*"([^"]+)"', text))
        found |= set(re.findall(r'wx\.StaticText\(\s*panel,\s*label="([^"]+:)"', text))
    return {_norm(label) for label in found}


def ab_problems() -> list[str]:
    """Every Appendix A or B row whose home is not real, and everything left unmapped."""
    from quill.core.github.appendix_ab_rows import APPENDIX_A, APPENDIX_B

    reg = _registries()
    problems: list[str] = []
    rows = (*APPENDIX_A, *APPENDIX_B)
    for row in rows:
        if not row.refs:
            problems.append(f"{row.today}: names no home")
        for ref in (*row.refs, *row.sheet_refs):
            wrong = resolve(ref, reg)
            if wrong:
                problems.append(f"{row.today}: {wrong}")
    named = {ref for row in rows for ref in row.refs}
    labels = {_norm(label) for row in rows for label in row.labels}
    for label in sorted(retired_labels() - labels):
        problems.append(f"a retired window's {label!r} has no Appendix A row")
    for command_id in sorted(reg.editor):
        if f"editor:{command_id}" not in named:
            problems.append(f"the editor's GitHub menu row {command_id} has no Appendix A row")
    for command_id in sorted(reg.doors):
        if f"door:{command_id}" not in named:
            problems.append(f"the door {command_id} has no Appendix A row")
    return problems


def _path(template: str, key: str) -> str:
    from quill.core.github.workbench_tree import GITHUB_TREE

    if not template:
        return " > ".join(GITHUB_TREE.path(key))
    labels: list[str] = []
    current: str | None = key
    while current is not None:
        node = GITHUB_TREE.template_node(template, current)
        labels.append(
            _TEMPLATE_WORDS.get(template, node.label) if node.parent is None else node.label
        )
        current = node.parent
    return " > ".join(reversed(labels))


def _view_rows(prefix: str, views: Iterable[tuple[str, str]]) -> list[str]:
    from quill.core.github.workbench_tree import GITHUB_TREE

    homes, loaders = GITHUB_TREE.homes(), GITHUB_TREE.loaders()
    out = []
    for key, label in views:
        loader = f"{prefix}:{key}"
        home = [_path(t, k) for t, k in homes.get(loader, [])]
        narrowed = [
            _path(t, k) for t, k in loaders.get(loader, []) if (t, k) not in homes.get(loader, [])
        ]
        where = "; ".join(home) + (f" (narrowed: {', '.join(narrowed)})" if narrowed else "")
        out.append(f"| {_cell(label)} | {_cell(where)} | `{loader}` |")
    return out


def _ref_words(refs: Iterable[str]) -> str:
    return ", ".join(f"`{ref}`" for ref in refs)


def render_a() -> str:
    from quill.core.github import explore_views
    from quill.core.github.appendix_ab_rows import APPENDIX_A
    from quill.ui import github_items_view

    out = [_begin("appendix-a"), ""]
    out += [
        "### GitHub Items' views",
        "",
        "| Today | New home | Loader |",
        "|---|---|---|",
        *_view_rows("items", github_items_view.VIEWS),
        "",
        "### Explore GitHub's views",
        "",
        "| Today | New home | Loader |",
        "|---|---|---|",
        *_view_rows("explore", explore_views.VIEWS),
    ]
    sections: dict[str, list[str]] = {}
    for row in APPENDIX_A:
        note = f" {row.reason}" if row.reason else ""
        sections.setdefault(row.section, []).append(
            f"| {_cell(row.today)} | {_cell(row.home + '.' + note)} | {_ref_words(row.refs)} |"
        )
    for section, rows in sections.items():
        out += ["", f"### {section}", "", "| Today | New home | In the code |", "|---|---|---|"]
        out += rows
    return "\n".join([*out, "", _end("appendix-a")])


def render_b() -> str:
    from quill.core.github.appendix_ab_rows import APPENDIX_B

    out = [
        _begin("appendix-b"),
        "",
        "| Existing action | New home | On the Properties sheet | In the code |",
        "|---|---|---|---|",
    ]
    for row in APPENDIX_B:
        note = f" {row.reason}" if row.reason else ""
        refs = _ref_words((*row.refs, *row.sheet_refs))
        out.append(
            f"| {_cell(row.today)} | {_cell(row.home + '.' + note)} | "
            f"{_cell(row.sheet or 'Not needed')} | {refs} |"
        )
    return "\n".join([*out, "", _end("appendix-b")])


# -- Appendix C ----------------------------------------------------------------------


def _row_fields(row_type: str) -> set[str]:
    from quill.core.github.object_filters import EXPLORE_ROW, ROW_CLASSES

    module, _sep, name = ROW_CLASSES.get(row_type, EXPLORE_ROW).partition(":")
    cls = getattr(importlib.import_module(module), name)
    return {f.name for f in dataclasses.fields(cls)}


def c_problems() -> list[str]:
    """Every Appendix C object whose sheet, rows or filters are not real, and what is unclaimed."""
    from quill.core.github import object_filters
    from quill.core.github.appendix_c_rows import APPENDIX_C, NOT_OBJECTS, SEARCH_NODES
    from quill.core.github.appendix_map import HERE, NOT_YET, SEARCH
    from quill.core.github.filter_builder import ATTRIBUTES
    from quill.core.github.filter_menu import LOCAL_QUALIFIERS
    from quill.core.workbench.tree import Scope

    reg = _registries()
    problems: list[str] = []
    row_types = set(reg.actions.row_types)
    claimed_sheets: set[str] = set()
    claimed_rows: set[str] = set()
    for entry in APPENDIX_C:
        name = entry.name
        claimed_sheets |= set(entry.sheets)
        claimed_rows |= set(entry.row_types)
        for kind in entry.sheets:
            if kind not in reg.sheets:
                problems.append(f"{name}: no {kind} sheet")
            elif reg.sheets[kind].sheet.pages[0].key != "general":
                problems.append(f"{name}: the {kind} sheet does not open on General")
        if not entry.sheets and not entry.reason:
            problems.append(f"{name}: no sheet, and no reason why")
        if not entry.row_types and not entry.home:
            problems.append(f"{name}: no list rows, and no home named")
        for row_type in entry.row_types:
            if row_type not in row_types:
                problems.append(f"{name}: no row type {row_type}")
        search = SEARCH_NODES.get(name, "")
        for item in entry.filters:
            if item.how == NOT_YET:
                if not item.why:
                    problems.append(f"{name}: {item.words} is not yet, with no reason")
                continue
            if item.how == HERE and search == "items:issues":
                if item.key not in LOCAL_QUALIFIERS:
                    problems.append(f"{name}: {item.key} is not answered here for issues")
            elif item.how == HERE:
                if not entry.row_types:
                    problems.append(f"{name}: {item.key} is answered here, but it has no list")
                for row_type in entry.row_types:
                    keys = {q.key for q in object_filters.qualifiers_for(row_type)}
                    if item.key not in keys:
                        problems.append(f"{name}: a {row_type} list does not answer {item.key}")
            elif item.how == SEARCH:
                if search == "items:issues":
                    if item.key not in {a.key for a in ATTRIBUTES}:
                        problems.append(f"{name}: the Filter Builder has no {item.key}")
                elif not search or not _node_exists(reg, search):
                    problems.append(f"{name}: {item.key} is searched, but there is no search node")
                elif reg.tree.node(search).scope is not Scope.QUERY:
                    problems.append(f"{name}: {search} does not send its filter to GitHub")
            else:
                problems.append(f"{name}: {item.words} has no way of being answered")
    for kind in sorted(set(reg.sheets) - claimed_sheets):
        problems.append(f"the {kind} sheet is in no Appendix C object")
    for row_type in sorted(row_types - claimed_rows - set(NOT_OBJECTS)):
        problems.append(f"the row type {row_type} is in no Appendix C object")
    for row_type in sorted(set(NOT_OBJECTS) & claimed_rows):
        problems.append(f"the row type {row_type} is both an object and not one")
    for row_type, qualifiers in object_filters.LOCAL.items():
        if row_type not in row_types:
            problems.append(f"qualifiers for {row_type}, which is no row type")
            continue
        fields = _row_fields(row_type)
        for q in qualifiers:
            if not q.field.startswith("@") and q.field not in fields:
                problems.append(f"{row_type}.{q.key} reads {q.field}, which its rows lack")
    return problems


def _nodes_for(row_types: Iterable[str]) -> str:
    from quill.core.github.workbench_tree import GITHUB_TREE

    wanted = set(row_types) - {"resource"}
    paths = [_path(t, n.key) for t, n in GITHUB_TREE.all_nodes() if n.row_type in wanted]
    more = f", and {len(paths) - 4} more" if len(paths) > 4 else ""
    said = ", ".join(paths[:4]) + more
    if "resource" in row_types:
        said += ("; " if said else "") + "its resource lists"
    return said


def render_c() -> str:
    from quill.core.github.appendix_c_rows import APPENDIX_C
    from quill.core.github.appendix_map import HERE, SEARCH
    from quill.core.github.sheet_catalog import SHEETS

    out = [
        _begin("appendix-c"),
        "",
        "### The map, from the code",
        "",
        "Generated from `quill/core/github/appendix_c_rows.py`, the sheet catalogue, the "
        "tree and `quill/core/github/object_filters.py`. Every qualifier is typed in a list's "
        "filter box. *Here* is checked over the rows the list loaded; *GitHub's search* is "
        "sent to GitHub: an issue or pull request list sends it, and so does the Search node "
        "for repositories, commits or people; *not yet* says why.",
        "",
        "| Object | Sheet: its pages | Its lists | Filters here | GitHub's search | Not yet |",
        "|---|---|---|---|---|---|",
    ]
    for entry in APPENDIX_C:
        sheets = "; ".join(
            f"`{kind}`: " + ", ".join(p.title for p in SHEETS[kind].sheet.pages)
            for kind in entry.sheets
        )
        if not entry.sheets:
            sheets = f"None. {entry.home}. {entry.reason}"
        lists = _nodes_for(entry.row_types) or entry.home or "None"
        here = ", ".join(f"`{f.key}:`" for f in entry.filters if f.how == HERE)
        search = ", ".join(f"`{f.key}:`" for f in entry.filters if f.how == SEARCH)
        reasons: dict[str, list[str]] = {}
        for f in entry.filters:
            if f.how not in (HERE, SEARCH):
                reasons.setdefault(f.why, []).append(f.words)
        later = "; ".join(f"{', '.join(words)}: {why}" for why, words in reasons.items())
        out.append(
            f"| {_cell(entry.name)} | {_cell(sheets)} | {_cell(lists)} | {here or 'None'} | "
            f"{search or 'None'} | {_cell(later) or 'None'} |"
        )
    return "\n".join([*out, "", _end("appendix-c")])


# -- the PRD ------------------------------------------------------------------------


def render(current: str) -> str:
    """*current* with each generated region rewritten (each must already be marked)."""
    text = current
    for name, block in (
        ("appendix-a", render_a()),
        ("appendix-b", render_b()),
        ("appendix-c", render_c()),
    ):
        begin, end = _begin(name), _end(name)
        start = text.find(begin)
        stop = text.find(end)
        if start < 0 or stop < start:
            raise ValueError(f"The PRD has no {name} markers.")
        text = text[:start] + block + text[stop + len(end) :]
    return text


def problems() -> list[str]:
    return [*ab_problems(), *c_problems()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the generated tables")
    args = parser.parse_args(argv)
    found = problems()
    for problem in found:
        print(f"GATE-GITHUB-APPENDIX: {problem}")
    current = PRD_PATH.read_text(encoding="utf-8")
    wanted = render(current)
    if args.write:
        PRD_PATH.write_text(wanted, encoding="utf-8", newline="\n")
        print(f"wrote {PRD_PATH.relative_to(_REPO_ROOT)}")
    elif wanted != current:
        print("The PRD's Appendix A, B or C tables have drifted; run with --write.")
        return 1
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
