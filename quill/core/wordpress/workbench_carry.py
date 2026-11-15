"""What an import, export, copy or archive carries, and what it leaves out (WP-G).

Every Workbench report that moves writing in or out ends with a **Left out**
section naming what did not travel and why, so an empty section is a promise
rather than silence (:func:`left_out_section`). For **Import a Folder of
Documents** this module also carries what a document points at:

- **Pictures** a document shows from beside it (``![alt](pics/cat.png)`` or
  ``<img src=...>``) are uploaded to the site's Media Library once each, and
  the document's links are rewritten to the uploaded address. A picture that
  is missing, is not a picture, or lives on another host is listed as left out
  with the reason; a Word file's own pictures are counted and left out,
  because the editor's Word reader gives its words only.
- **Links between the imported documents** (``[see](notes.md)``) are pointed
  at the drafts they became, once every draft exists; a link to a file that
  was not imported is left as written and listed.
- **Front matter** fields (a ``---`` block at the top) are not post fields;
  they are taken off the text and named as left out.

Wx-free; requests go through the site's own client.
"""

from __future__ import annotations

import mimetypes
import re
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route

__all__ = [
    "ARCHIVE_LEFT_OUT",
    "COPY_LEFT_OUT",
    "DocRefs",
    "EXPORT_LEFT_OUT",
    "SPREADSHEET_LEFT_OUT",
    "copy_left_out",
    "document_refs",
    "export_left_out",
    "folder_left_out",
    "left_out_section",
    "send_folder",
    "strip_front_matter",
    "word_pictures",
]

SPREADSHEET_LEFT_OUT = (
    "Not carried from a spreadsheet: pictures and featured images, authors (each item is "
    "yours), custom fields, comments and publishing (published or scheduled rows are drafts)."
)
EXPORT_LEFT_OUT = (
    "each item's full text, its pictures and files, and rows outside the list as shown "
    "(filtered out, or not loaded yet)"
)
COPY_LEFT_OUT = (
    "Not copied: comments, revisions, custom fields, publishing (a new item is a draft, a "
    "private one included), sticky and template choices, and taxonomies other than "
    "categories and tags."
)
ARCHIVE_LEFT_OUT = (
    "Left out: comments, revisions, categories, tags, excerpts, featured images, custom "
    "fields, and pictures kept on other sites (their links stay)."
)
_PICTURES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".bmp"})
_IMAGE_MD = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_IMAGE_HTML = re.compile(r"""<img\b[^>]*?\bsrc=["']([^"']+)["']""", re.IGNORECASE)
_LINK_MD = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_LINK_HTML = re.compile(r"""<a\b[^>]*?\bhref=["']([^"']+)["']""", re.IGNORECASE)
_FRONT = re.compile(r"\A\s*---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


def left_out_section(items: Iterable[str]) -> list[str]:
    """The report's closing section: a heading line, then one line a thing."""
    listed = [item for item in items if item]
    if not listed:
        return ["", "Left out: nothing."]
    return ["", "Left out:", *(f"- {item}" for item in listed)]


def export_left_out(shown: Sequence[str], every: Sequence[str]) -> str:
    """What Export List does not write: hidden columns, then the rest."""
    hidden = [column for column in every if column not in shown]
    said = f"columns you have hidden ({', '.join(hidden)}), " if hidden else ""
    return f"Left out: {said}{EXPORT_LEFT_OUT}."


def copy_left_out(sources: Iterable[Mapping[str, Any]]) -> list[str]:
    """What Copy to Site does not carry, and any block from a plugin the target may lack."""
    said = [COPY_LEFT_OUT]
    plugin_blocks: set[str] = set()
    private = 0
    for raw in sources:
        if raw.get("status") == "private":
            private += 1
        content = raw.get("content")
        text = content.get("raw", "") if isinstance(content, Mapping) else str(content or "")
        for name in re.findall(r"<!-- wp:([a-z0-9-]+/[a-z0-9-]+)", str(text)):
            plugin_blocks.add(name)
    if private:
        said.append(f"{private} private items arrive as drafts, not private.")
    if plugin_blocks:
        said.append(
            "Blocks from plugins are copied as written and show only where the target has "
            f"the same plugin: {', '.join(sorted(plugin_blocks))}."
        )
    return said


def strip_front_matter(text: str) -> tuple[str, list[str]]:
    """*text* without a ``---`` front-matter block, and the field names it had."""
    match = _FRONT.match(text)
    if not match:
        return text, []
    names = [
        line.split(":", 1)[0].strip()
        for line in match.group(1).splitlines()
        if ":" in line and not line.startswith((" ", "\t", "-"))
    ]
    return text[match.end() :], [n for n in names if n]


def word_pictures(path: Path) -> int:
    """How many pictures a Word file holds (its ``word/media`` parts); 0 if unreadable."""
    try:
        with zipfile.ZipFile(path) as book:
            return sum(1 for n in book.namelist() if n.startswith("word/media/"))
    except (OSError, zipfile.BadZipFile):
        return 0


@dataclass
class DocRefs:
    """What one document points at, sorted into what travels and what does not."""

    #: The reference as written -> the picture file beside the document.
    pictures: dict[str, Path] = field(default_factory=dict)
    #: The reference as written -> the name of the imported file it links to.
    links: dict[str, str] = field(default_factory=dict)
    left_out: list[str] = field(default_factory=list)


def _local(ref: str) -> str:
    """The path in a reference, or "" for an address, an anchor or an e-mail link."""
    parsed = urlparse(ref)
    if parsed.scheme or ref.startswith(("#", "//")):
        return ""
    return unquote(parsed.path)


def document_refs(
    markdown: str, source: Path, imported: Iterable[str], *, word_pictures_count: int = 0
) -> DocRefs:
    """Sort the pictures and links in *markdown* (from *source*) for the import."""
    refs = DocRefs()
    names = {name.casefold(): name for name in imported}
    folder = source.parent
    for ref in [m.group(2) for m in _IMAGE_MD.finditer(markdown)] + _IMAGE_HTML.findall(markdown):
        local = _local(ref)
        if not local:
            host = urlparse(ref).hostname or "another site"
            refs.left_out.append(f"{source.name}: the picture {ref} stays on {host}, not uploaded")
            continue
        path = (folder / local).resolve()
        if path.suffix.lower() not in _PICTURES:
            refs.left_out.append(f"{source.name}: {ref} is not a picture, so it is not uploaded")
        elif not path.is_file():
            refs.left_out.append(f"{source.name}: the picture {ref} was not found beside it")
        else:
            refs.pictures[ref] = path
    for ref in [m.group(1) for m in _LINK_MD.finditer(markdown)] + _LINK_HTML.findall(markdown):
        local = _local(ref)
        if not local or ref in refs.pictures:
            continue
        target = Path(local)
        name = names.get(target.name.casefold()) if (folder / target).parent == folder else None
        if name:
            refs.links[ref] = name
        else:
            refs.left_out.append(
                f"{source.name}: the link to {ref} is left as written: it is not one of the "
                "files imported"
            )
    if word_pictures_count:
        refs.left_out.append(
            f"{source.name}: its {word_pictures_count} pictures (QUILL reads a Word file's "
            "words only)"
        )
    return refs


def folder_left_out(plan: Sequence[Any]) -> list[str]:
    """Every row's left-out lines, in file order."""
    return [line for row in plan for line in row.carry.get("left_out", ())]


def _swap(content: str, ref: str, address: str) -> str:
    """Point every quoted use of *ref* at *address*; an inline picture becomes a picture."""
    quoted = re.escape(ref)
    content = re.sub(
        rf'!<a href="{quoted}">([^<]*)</a>',
        lambda m: f'<img src="{address}" alt="{m.group(1)}"/>',
        content,
    )
    return content.replace(f'"{ref}"', f'"{address}"').replace(f"'{ref}'", f"'{address}'")


def _upload(api: WordPressApi, path: Path, read: Callable[[Path], bytes]) -> str:
    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    made = api.upload("wp/v2/media", path.name, read(path), kind)
    address = str(made.get("source_url", "") or "") if isinstance(made, Mapping) else ""
    if not address:
        raise WordPressApiError("the site did not say where it put the file")
    return address


def send_folder(
    api: WordPressApi,
    kind: str,
    plan: Sequence[Any],
    *,
    read: Callable[[Path], bytes] = Path.read_bytes,
) -> list[str]:
    """Make each previewed document, carrying its pictures and links; the report.

    Pictures are uploaded once each and the content rewritten before the
    draft is made; links between documents are pointed at their drafts once
    every draft exists. The report ends with :func:`left_out_section`.
    """
    from quill.core.wordpress.workbench_io import make_row

    said: list[str] = []
    left_out = folder_left_out(plan)
    uploaded: dict[Path, str] = {}
    made: dict[str, Mapping[str, Any]] = {}
    pending: list[tuple[Any, Mapping[str, Any], str]] = []
    for row in plan:
        if row.problem:
            said.append(f"Skipped {row.where}: {row.problem}.")
            continue
        content = str(row.fields.get("content", ""))
        for ref, path in row.carry.get("pictures", {}).items():
            try:
                if path not in uploaded:
                    uploaded[path] = _upload(api, path, read)
                    said.append(f"Uploaded the picture {path.name}.")
                content = _swap(content, ref, uploaded[path])
            except (WordPressApiError, OSError) as exc:
                reason = getattr(exc, "plain", "") or exc
                left_out.append(f"{row.where}: the picture {ref} could not be uploaded: {reason}")
        try:
            answer = make_row(api, kind, row, content=content)
        except WordPressApiError as exc:
            said.append(f"Not made {row.where}: {exc.plain or exc}")
            continue
        ident = answer.get("id", "")
        said.append(
            f"Made {row.where}: {row.fields.get('title') or '(no title)'}"
            + (f", number {ident}." if ident else ".")
        )
        made[row.where] = answer
        if row.carry.get("links"):
            pending.append((row, answer, content))
    for row, done, content in pending:
        linked = content
        for ref, name in row.carry["links"].items():
            target = made.get(name)
            address = str(target.get("link", "") or "") if target else ""
            if address:
                linked = _swap(linked, ref, address)
            else:
                left_out.append(
                    f"{row.where}: the link to {ref} is left as written: {name} was not made"
                )
        if linked != content and done.get("id"):
            try:
                api.post(f"{kind_route(kind)}/{done['id']}", {"content": linked})
                said.append(f"Linked {row.where} to the other drafts it names.")
            except WordPressApiError as exc:
                left_out.append(
                    f"{row.where}: its links were not pointed at the drafts: {exc.plain or exc}"
                )
    return said + left_out_section(left_out)
