"""Download My Writing, and Send a Folder as Drafts (wordpress.md 9.16).

**Download My Writing** saves every page and post on a site to a folder of
Markdown files, one per item, with the pictures beside them and a contents
page (``index.md``). It is an offline archive, a backup a person can read, and
a way to move house. A ``.quill-archive.json`` in the folder records what is
already saved and when it last changed on the site, so running it again
resumes: only new and changed items are fetched.

**Send a Folder as Drafts** turns a folder of Markdown, text or web-page files
into drafts. Each file's first heading is its title (:mod:`cross_site`), and
each is checked with Check Before Publishing first, so the one confirmation
can say what was found.

Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress import checks as chk
from quill.core.wordpress import cross_site as xs
from quill.core.wordpress import fences
from quill.core.wordpress import site as wp
from quill.core.wordpress.api import WordPressApi, WordPressApiError

MANIFEST = ".quill-archive.json"
KINDS = (("page", "Pages"), ("post", "Posts"))
ALL_STATUSES = ("publish", "draft", "pending", "future", "private")
FOLDER_SUFFIXES = (".md", ".markdown", ".txt", ".html", ".htm")


def file_stem(title: str, item_id: int) -> str:
    slug = wp.slugify(title)[:60] or "untitled"
    return f"{slug}-{item_id}"


def page_markdown(item: wp.Item) -> str:
    """One item as a readable Markdown file: a heading, its facts, then its text.

    Blocks Markdown cannot hold stay as their own HTML, so nothing is lost.
    """
    body, islands = fences.post_to_markdown(item.content)
    for key, markup in islands.items():
        pattern = re.compile(rf"^::: block \S+ {re.escape(key)}\s*$", re.M)
        body = pattern.sub(markup.replace("\\", "\\\\"), body)
    status = wp.STATUS_LABELS.get(item.status, item.status).rstrip("s")
    facts = [f"Status: {'Published' if item.status == 'publish' else status}."]
    if item.date_gmt:
        facts.append(f"Date: {wp.friendly_date(item.date_gmt)}.")
    if item.link:
        facts.append(f"Address: {item.link}")
    return f"# {item.title or '(untitled)'}\n\n" + "\n".join(facts) + "\n\n" + body.strip() + "\n"


@dataclass
class ArchiveResult:
    saved: int = 0
    unchanged: int = 0
    pictures: int = 0
    failed: list[str] = field(default_factory=list)


def download_writing(
    api: WordPressApi,
    folder: Path,
    site_url: str,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> ArchiveResult:
    """Save every page and post to *folder*; resumable through :data:`MANIFEST`."""
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / MANIFEST
    raw = read_json(manifest_path, default={})
    done: dict[str, dict[str, str]] = raw.get("done", {}) if isinstance(raw, dict) else {}
    summaries = [
        (kind, s) for kind, _name in KINDS for s in wp.list_items(api, kind, statuses=ALL_STATUSES)
    ]
    result = ArchiveResult()
    pictures = folder / "pictures"
    for number, (kind, summary) in enumerate(summaries, 1):
        key = f"{kind}-{summary.id}"
        known = done.get(key, {})
        name = file_stem(summary.title, summary.id) + ".md"
        if (
            known.get("modified_gmt") == summary.modified_gmt
            and (folder / known.get("file", name)).exists()
        ):
            result.unchanged += 1
        else:
            try:
                item = wp.load_item(api, kind, summary.id)
                text = page_markdown(item)
                for url in xs.site_pictures(item.content, site_url):
                    local = pictures / _picture_name(url)
                    if not local.exists():
                        pictures.mkdir(exist_ok=True)
                        local.write_bytes(xs.fetch_picture(api, url))
                        result.pictures += 1
                    text = text.replace(url, f"pictures/{local.name}")
                (folder / name).write_bytes(text.encode("utf-8"))
                done[key] = {
                    "modified_gmt": summary.modified_gmt,
                    "file": name,
                    "title": summary.title,
                    "kind": kind,
                    "status": summary.status,
                }
                result.saved += 1
            except WordPressApiError as exc:
                result.failed.append(f"{summary.title}: {exc.plain}")
            # Written after every item, so an interrupted run resumes where it stopped.
            write_json_atomic(manifest_path, {"done": done})
        if progress is not None:
            progress(number, len(summaries))
    (folder / "index.md").write_bytes(contents_page(done).encode("utf-8"))
    return result


def _picture_name(url: str) -> str:
    path = Path(unquote(urlparse(url).path))
    parent = re.sub(r"[^\w-]", "", "-".join(path.parts[-3:-1]))
    return f"{parent}-{path.name}" if parent else path.name


def contents_page(done: dict[str, dict[str, str]]) -> str:
    lines = ["# Contents", ""]
    for kind, name in KINDS:
        rows = sorted(
            (v for v in done.values() if v.get("kind") == kind),
            key=lambda v: v.get("title", "").casefold(),
        )
        if not rows:
            continue
        lines += [f"## {name}", ""]
        lines += [f"- [{r.get('title') or '(untitled)'}]({r.get('file', '')})" for r in rows]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def archive_sentence(site_name: str, folder: Path, result: ArchiveResult) -> str:
    parts = [f"{result.saved} saved"]
    if result.unchanged:
        parts.append(f"{result.unchanged} already up to date")
    if result.pictures:
        parts.append(f"{result.pictures} pictures")
    said = f"Your writing on {site_name} is in {folder.name}: " + ", ".join(parts) + "."
    if result.failed:
        said += f" {len(result.failed)} could not be saved; run it again to try those."
    return said


# --------------------------------------------------------------------------- #
# Send a Folder as Drafts


@dataclass(frozen=True)
class FolderFile:
    path: Path
    title: str
    text: str
    text_format: str
    findings: tuple[str, ...]


def read_folder(folder: Path, *, site_name: str) -> list[FolderFile]:
    """The folder's documents, in name order, each titled and checked."""
    out: list[FolderFile] = []
    for path in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_file() or path.suffix.lower() not in FOLDER_SUFFIXES:
            continue
        try:
            raw = path.read_bytes().decode("utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        text_format = xs.document_format(path)
        title, body = xs.title_and_body(raw, text_format, path.stem.replace("-", " ").strip())
        markup = body if text_format == "html" else fences.convert_markdown(body).html
        findings = chk.check_content(markup, title=title, site_name=site_name)
        out.append(FolderFile(path, title, body, text_format, tuple(f.message for f in findings)))
    return out


def folder_sentence(files: list[FolderFile], site_name: str) -> str:
    flagged = sum(1 for f in files if f.findings)
    head = f"Send {len(files)} files to {site_name} as drafts?"
    if flagged:
        return head + f" Check Before Publishing found things to look at in {flagged} of them."
    return head + " Check Before Publishing found nothing to look at."


def send_folder(
    api: WordPressApi,
    files: list[FolderFile],
    *,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[list[wp.Item], list[str]]:
    sent: list[wp.Item] = []
    failed: list[str] = []
    for number, file in enumerate(files, 1):
        markup = (
            file.text if file.text_format == "html" else fences.convert_markdown(file.text).html
        )
        try:
            sent.append(
                wp.create_item(
                    api,
                    wp.Item(id=0, kind="post", title=file.title, content=markup, status="draft"),
                )
            )
        except WordPressApiError as exc:
            failed.append(f"{file.path.name}: {exc.plain}")
        if progress is not None:
            progress(number, len(files))
    return sent, failed
