"""Lists in and out, and the REST Console's words (PRD 15.9 and 15.10; W7).

- **Export any list** (:func:`export_rows`): the rows a Workbench list shows,
  with the columns it shows, as CSV (UTF-8 with its byte-order mark, so Excel
  opens it the right way), as an Excel workbook through openpyxl (a header
  row, the first row frozen), or as a Markdown table -- the QUILL table, which
  the editor's table commands read and its Word, EPUB and DAISY exports keep.
- **Import posts or pages from a spreadsheet** (:func:`read_spreadsheet`,
  :func:`import_mapping`, :func:`import_plan`, :func:`send_import_results`):
  columns are matched by their header, with the usual other names (Body for
  Content, Category for Categories, Publish Date for Date), and the preview
  starts with that mapping and the columns it leaves out. Each row becomes a
  draft, a pending item or a private one; a row whose Status says publish or
  future is made a draft, for publishing after a look. Categories and tags are
  names, separated by commas, found or made. The result is a sentence a row.
- **Import a folder of documents** (:func:`folder_plan`): each Markdown, text
  or Word file a draft, its first heading the title, its Markdown made blocks;
  its pictures and its links to the other files are found here and carried by
  :func:`quill.core.wordpress.workbench_carry.send_folder`, and anything not
  carried is listed (WP-G).
- **The REST Console** (:func:`parse_params`, :func:`needed_capability`,
  :func:`answer_tree`, :func:`complete_route`): completion from the site's own
  index, the capability a request needs, and the answer as a tree.

Wx-free; requests go through the site's own client.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route
from quill.core.workbench.export import export_rows, markdown_table  # shared since 2026-11-17
from quill.core.workbench.spreadsheet import header_name as _header
from quill.core.workbench.spreadsheet import read_spreadsheet

__all__ = [
    "IMPORT_COLUMNS",
    "ImportRow",
    "TreeNode",
    "answer_tree",
    "complete_route",
    "export_rows",
    "folder_plan",
    "import_mapping",
    "import_plan",
    "make_row",
    "mapping_lines",
    "markdown_table",
    "needed_capability",
    "send_import_results",
    "parse_params",
    "read_spreadsheet",
    "send_import",
]

IMPORT_COLUMNS = ("title", "content", "status", "slug", "excerpt", "categories", "tags", "date")
_STATUSES = frozenset({"draft", "pending", "publish", "private", "future"})
_KEPT_STATUSES = frozenset({"draft", "pending", "private"})
IMPORT_SYNONYMS: dict[str, str] = {
    "name": "title",
    "headline": "title",
    "body": "content",
    "text": "content",
    "summary": "excerpt",
    "category": "categories",
    "tag": "tags",
    "address": "slug",
    "publish date": "date",
    "date published": "date",
    "post status": "status",
}
DOC_SUFFIXES = (".md", ".markdown", ".txt", ".docx")


@dataclass(frozen=True)
class ImportRow:
    number: int
    fields: Mapping[str, str]
    problem: str = ""
    note: str = ""
    name: str = ""
    #: A document's pictures, links and left-out lines (:mod:`workbench_carry`).
    carry: Mapping[str, Any] = field(default_factory=dict)

    @property
    def where(self) -> str:
        return self.name or f"Row {self.number}"

    @property
    def sentence(self) -> str:
        title = self.fields.get("title", "") or "(no title)"
        status = self.fields.get("status", "") or "draft"
        if self.problem:
            return f"{self.where}, {title}: skipped, {self.problem}"
        said = f"{self.where}: {title}, as {status}" + (f" ({self.note})" if self.note else "")
        pictures, links = len(self.carry.get("pictures", {})), len(self.carry.get("links", {}))
        if pictures:
            said += f", {pictures} pictures to upload"
        if links:
            said += f", {links} links to the other drafts"
        return said


def import_mapping(headers: Iterable[str]) -> tuple[dict[str, str], list[str]]:
    """Each column the import uses and the field it fills; the columns left out."""
    mapping: dict[str, str] = {}
    ignored: list[str] = []
    for header in headers:
        clean = _header(header)
        name = clean if clean in IMPORT_COLUMNS else IMPORT_SYNONYMS.get(clean, "")
        if name and name not in mapping.values():
            mapping[clean] = name
        elif clean:
            ignored.append(clean)
    return mapping, ignored


def mapping_lines(mapping: Mapping[str, str], ignored: Sequence[str]) -> list[str]:
    """The mapping as the preview's first lines."""
    lines = [f"Column {column} fills {name}." for column, name in mapping.items()]
    if ignored:
        lines.append(f"Left out, matching no field: {', '.join(ignored)}.")
    return lines


def import_plan(rows: Sequence[Mapping[str, str]]) -> list[ImportRow]:
    """The preview: one line per spreadsheet row, with why any row is left out."""
    plan: list[ImportRow] = []
    for number, row in enumerate(rows, start=2):
        mapping, _left_out = import_mapping(row)
        fields = {mapping[_header(k)]: v for k, v in row.items() if _header(k) in mapping}
        status = fields.get("status", "").lower()
        problem = note = ""
        if not fields.get("title") and not fields.get("content"):
            problem = "it has no title and no content"
        elif status and status not in _STATUSES:
            problem = f"{status} is not a status WordPress knows"
        elif status and status not in _KEPT_STATUSES:
            note = f"its Status says {status}; publish it after a look"
            fields["status"] = "draft"
        plan.append(ImportRow(number, fields, problem, note))
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
    return [s for s in send_import_results(api, kind, plan) if s.startswith("Not made")]


def make_row(
    api: WordPressApi, kind: str, row: ImportRow, *, content: str | None = None
) -> dict[str, Any]:
    """Make one previewed row on the site; what the site answered (raises on refusal)."""
    fields = row.fields
    body: dict[str, Any] = {
        "title": fields.get("title", ""),
        "content": fields.get("content", "") if content is None else content,
        "status": (fields.get("status") or "draft").lower(),
    }
    for key in ("slug", "excerpt", "date"):
        if fields.get(key):
            body[key] = fields[key]
    if kind == "post":
        for column in ("categories", "tags"):
            if fields.get(column):
                body[column] = _term_ids(api, f"wp/v2/{column}", fields[column])
    made = api.post(kind_route(kind), body)
    return made if isinstance(made, dict) else {}


def send_import_results(api: WordPressApi, kind: str, plan: Sequence[ImportRow]) -> list[str]:
    """Make each previewed row; one sentence a row: made, skipped or not made."""
    said: list[str] = []
    for row in plan:
        if row.problem:
            said.append(f"Skipped {row.where}: {row.problem}.")
            continue
        try:
            made = make_row(api, kind, row)
            ident = made.get("id", "")
            number = f", number {ident}" if ident else ""
            title = row.fields.get("title", "") or "(no title)"
            said.append(f"Made {row.where}: {title}{number}.")
        except WordPressApiError as exc:
            said.append(f"Not made {row.where}: {exc.plain or exc}")
    return said


def folder_plan(folder: Path, read: Callable[[Path], str]) -> list[ImportRow]:
    """Each document in *folder* as a draft to make, its first heading the title.

    *read* turns a file into Markdown (the editor's own Word reader for
    ``.docx``); the content goes to the site as blocks.
    """
    from quill.core.wordpress.cross_site import title_and_body
    from quill.core.wordpress.fences import markdown_to_blocks
    from quill.core.wordpress.workbench_carry import (
        document_refs,
        strip_front_matter,
        word_pictures,
    )

    plan: list[ImportRow] = []
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in DOC_SUFFIXES)
    names = [p.name for p in files]
    for number, path in enumerate(files, start=1):
        stem = {"title": path.stem}
        try:
            text = read(path)
        except Exception as exc:  # noqa: BLE001 - one file must not stop the rest
            plan.append(ImportRow(number, stem, f"it could not be read: {exc}", name=path.name))
            continue
        if not text.strip():
            plan.append(ImportRow(number, stem, "it is empty", name=path.name))
            continue
        text, front = strip_front_matter(text)
        title, body = title_and_body(text, "markdown", path.stem)
        in_word = word_pictures(path) if path.suffix.lower() == ".docx" else 0
        refs = document_refs(body, path, names, word_pictures_count=in_word)
        if front:
            refs.left_out.append(f"{path.name}: its front matter ({', '.join(front)})")
        fields = {"title": title, "content": markdown_to_blocks(body), "status": "draft"}
        carry = {"pictures": refs.pictures, "links": refs.links, "left_out": refs.left_out}
        plan.append(ImportRow(number, fields, name=path.name, carry=carry))
    return plan


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
