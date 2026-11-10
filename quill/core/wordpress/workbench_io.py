"""Lists in and out, and the REST Console's words (PRD 15.9 and 15.10; W7).

- **Export any list** (:func:`export_rows`): the rows a Workbench list shows,
  with the columns it shows, as CSV (UTF-8 with its byte-order mark, so Excel
  opens it the right way) or as an Excel workbook through openpyxl, with a
  header row and the first row frozen.
- **Import posts or pages from a spreadsheet** (:func:`read_spreadsheet`,
  :func:`import_plan`, :func:`send_import`): the columns are named by their
  header (Title, Content, Status, Slug, Excerpt, Categories, Tags; any case),
  every row is previewed, and each becomes a draft unless its Status says
  otherwise. Categories and tags are names, separated by commas, found or made.
- **The REST Console** (:func:`parse_params`, :func:`needed_capability`,
  :func:`answer_tree`, :func:`complete_route`): completion from the site's own
  index, the capability a request needs, and the answer as a tree.

Wx-free; requests go through the site's own client.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route

__all__ = [
    "IMPORT_COLUMNS",
    "ImportRow",
    "TreeNode",
    "answer_tree",
    "complete_route",
    "export_rows",
    "import_plan",
    "needed_capability",
    "parse_params",
    "read_spreadsheet",
    "send_import",
]

IMPORT_COLUMNS = ("title", "content", "status", "slug", "excerpt", "categories", "tags", "date")
_STATUSES = frozenset({"draft", "pending", "publish", "private", "future"})


def export_rows(
    path: Path, headings: Sequence[str], rows: Iterable[Sequence[str]], *, kind: str = ""
) -> int:
    """Write *rows* under *headings* to *path* (``.csv`` or ``.xlsx``); the row count."""
    data = [list(map(str, row)) for row in rows]
    suffix = kind or path.suffix.lower().lstrip(".")
    if suffix == "xlsx":
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Workbench"
        sheet.append(list(headings))
        for row in data:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        book.save(str(path))
        return len(data)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(list(headings))
    writer.writerows(data)
    path.write_text(buffer.getvalue(), encoding="utf-8-sig", newline="")
    return len(data)


@dataclass(frozen=True)
class ImportRow:
    number: int
    fields: Mapping[str, str]
    problem: str = ""

    @property
    def sentence(self) -> str:
        title = self.fields.get("title", "") or "(no title)"
        status = self.fields.get("status", "") or "draft"
        if self.problem:
            return f"Row {self.number}, {title}: skipped, {self.problem}"
        return f"Row {self.number}: {title}, as {status}"


def read_spreadsheet(path: Path) -> list[dict[str, str]]:
    """Each row of a CSV or Excel file as {column: text}, columns named by the header."""
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        book = load_workbook(str(path), read_only=True, data_only=True)
        sheet = book.active
        values = [
            ["" if cell is None else str(cell) for cell in row]
            for row in sheet.iter_rows(values_only=True)
        ]
        book.close()
    else:
        text = path.read_text(encoding="utf-8-sig")
        values = [list(row) for row in csv.reader(io.StringIO(text))]
    if not values:
        return []
    header = [h.strip().lower() for h in values[0]]
    return [
        {header[i]: cell.strip() for i, cell in enumerate(row) if i < len(header) and header[i]}
        for row in values[1:]
        if any(cell.strip() for cell in row)
    ]


def import_plan(rows: Sequence[Mapping[str, str]]) -> list[ImportRow]:
    """The preview: one line per spreadsheet row, with why any row is left out."""
    plan: list[ImportRow] = []
    for number, row in enumerate(rows, start=2):
        fields = {k: v for k, v in row.items() if k in IMPORT_COLUMNS}
        status = fields.get("status", "").lower()
        problem = ""
        if not fields.get("title") and not fields.get("content"):
            problem = "it has no title and no content"
        elif status and status not in _STATUSES:
            problem = f"{status} is not a status WordPress knows"
        elif status == "future" and not fields.get("date"):
            problem = "a scheduled post needs a date"
        plan.append(ImportRow(number, fields, problem))
    return plan


def _term_ids(api: WordPressApi, route: str, names: str) -> list[int]:
    ids: list[int] = []
    for name in (n.strip() for n in names.split(",")):
        if not name:
            continue
        found = api.get(route, search=name, _fields="id,name")
        match = next(
            (t for t in found or [] if str(t.get("name", "")).casefold() == name.casefold()), None
        )
        if match is None:
            match = api.post(route, {"name": name})
        if isinstance(match, dict) and match.get("id"):
            ids.append(int(match["id"]))
    return ids


def send_import(api: WordPressApi, kind: str, plan: Sequence[ImportRow]) -> list[str]:
    """Make each previewed row; the sentences for rows the site would not take."""
    failed: list[str] = []
    for row in plan:
        if row.problem:
            continue
        fields = row.fields
        body: dict[str, Any] = {
            "title": fields.get("title", ""),
            "content": fields.get("content", ""),
            "status": (fields.get("status") or "draft").lower(),
        }
        for key in ("slug", "excerpt", "date"):
            if fields.get(key):
                body[key] = fields[key]
        try:
            if kind == "post":
                for column in ("categories", "tags"):
                    if fields.get(column):
                        body[column] = _term_ids(api, f"wp/v2/{column}", fields[column])
            api.post(kind_route(kind), body)
        except WordPressApiError as exc:
            failed.append(f"Row {row.number}: {exc.plain or exc}")
    return failed


# -- the REST Console ------------------------------------------------------------


def complete_route(typed: str, routes: Iterable[str], limit: int = 40) -> list[str]:
    """The site's routes that start with (or, failing that, contain) what was typed."""
    text = typed.strip().lstrip("/")
    every = [r.lstrip("/") for r in routes]
    starts = [r for r in every if r.startswith(text)]
    found = starts or [r for r in every if text and text in r]
    return found[:limit]


def parse_params(text: str) -> dict[str, Any]:
    """``name=value`` lines, or a JSON object, as the request's parameters or body."""
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith("{"):
        value = json.loads(stripped)
        if not isinstance(value, dict):
            raise ValueError("The JSON must be an object, inside braces.")
        return value
    found: dict[str, Any] = {}
    for line in stripped.splitlines():
        if not line.strip():
            continue
        name, sep, value = line.partition("=")
        if not sep or not name.strip():
            raise ValueError(f"Write each one as name=value: {line.strip()}")
        found[name.strip()] = value.strip()
    return found


_WRITE_NEEDS = {
    "posts": "edit_posts",
    "pages": "edit_pages",
    "media": "upload_files",
    "comments": "moderate_comments",
    "categories": "manage_categories",
    "tags": "manage_categories",
    "users": "edit_users",
    "plugins": "activate_plugins",
    "themes": "switch_themes",
    "settings": "manage_options",
    "menus": "edit_theme_options",
    "menu-items": "edit_theme_options",
    "templates": "edit_theme_options",
    "template-parts": "edit_theme_options",
    "widgets": "edit_theme_options",
    "sidebars": "edit_theme_options",
}


def needed_capability(method: str, route: str) -> str:
    """The capability WordPress checks for *method* on *route*, as far as QUILL knows."""
    parts = route.strip("/").split("/")
    base = parts[2] if len(parts) > 2 and parts[0] == "wp" else ""
    if method.upper() == "GET":
        if base in ("users", "plugins", "settings"):
            return {"users": "list_users", "plugins": "activate_plugins"}.get(
                base, "manage_options"
            )
        return ""
    if base in _WRITE_NEEDS:
        need = _WRITE_NEEDS[base]
        if method.upper() == "DELETE" and base in ("posts", "pages"):
            return f"delete_{base}"
        if method.upper() == "DELETE" and base == "users":
            return "delete_users"
        return need
    return "decided by the plugin that owns the route"


@dataclass
class TreeNode:
    label: str
    children: list[TreeNode]


def _scalar(value: Any) -> str:
    if isinstance(value, str):
        return value if len(value) <= 200 else value[:200] + "..."
    return json.dumps(value)


def answer_tree(value: Any, label: str = "Answer", *, depth: int = 0) -> TreeNode:
    """The answer as a tree: each key or list item a node, values in the labels."""
    if depth > 12:
        return TreeNode(f"{label}: (deeper than shown)", [])
    if isinstance(value, dict):
        node = TreeNode(f"{label} ({len(value)} fields)", [])
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                node.children.append(answer_tree(child, str(key), depth=depth + 1))
            else:
                node.children.append(TreeNode(f"{key}: {_scalar(child)}", []))
        return node
    if isinstance(value, list):
        node = TreeNode(f"{label} ({len(value)} items)", [])
        for index, child in enumerate(value, start=1):
            node.children.append(answer_tree(child, f"Item {index}", depth=depth + 1))
        return node
    return TreeNode(f"{label}: {_scalar(value)}", [])
