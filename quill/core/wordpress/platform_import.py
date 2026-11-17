"""Read Blogger, Medium, Substack and Squarespace exports as WXR (PRD 15.11, Moving in).

Each platform's export file is read **on this computer** and turned into the
same :class:`~quill.core.wordpress.wxr_read.WxrFile` a WordPress export gives,
so :mod:`quill.core.wordpress.wxr_import` plans, previews and sends it
unchanged: every item is made as a draft, and Ctrl+Z moves them to the Trash.

- **Blogger** (Settings > Back up content, or Google Takeout): an Atom feed.
  Posts and pages come over, labels become tags, drafts are said to be
  drafts; comments, settings and the template are left out and counted. Both
  the older ``kind#post`` categories and Takeout's ``blogger:type`` are read.
- **Medium** (Settings > Download your information): a zip with one HTML file
  per story under ``posts/``. Each file's title, subtitle, body, author and
  date are read; a file whose name starts ``draft_`` was a draft there.
- **Substack** (Settings > Export): a zip with ``posts.csv`` and each post's
  body as ``posts/<id>.<slug>.html``. Threads have no body and are left out;
  paid-only posts are imported as drafts like the rest, and said to be paid.
- **Squarespace** (Settings > Export, WordPress): a WXR file with quirks. It
  may leave out the WXR version, and its links and file addresses may be
  relative ("/blog/my-post"), so they are made whole against the site's own
  address first, which the import then points at this site. Squarespace's
  own markup is left as it is.

Pictures in Blogger, Medium and Substack exports are not in the file: the
posts keep showing them from where they are now, and :func:`read_export`'s
notes say so for the preview. Nothing here touches the network.

Zips are read in memory, never unpacked to disk: past :data:`MAX_MEMBERS`
entries, or :data:`MAX_TOTAL_BYTES` unpacked, the file is refused; a member
whose name climbs out of the archive (``..`` or an absolute path) is ignored.

Wx-free and network-free.
"""

from __future__ import annotations

import csv
import html
import io
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from quill.core.wordpress.wxr_read import (
    MAX_FILE_BYTES,
    MAX_ITEMS,
    WxrAuthor,
    WxrError,
    WxrFile,
    WxrItem,
    WxrTerm,
    read_wxr,
)

__all__ = [
    "MAX_MEMBERS",
    "MAX_TOTAL_BYTES",
    "PLATFORMS",
    "Converted",
    "PlatformExportError",
    "detect",
    "read_export",
]

MAX_MEMBERS = 5000
MAX_TOTAL_BYTES = 256 * 1024 * 1024
PLATFORMS = {
    "blogger": "Blogger",
    "medium": "Medium",
    "substack": "Substack",
    "squarespace": "Squarespace",
    "wordpress": "WordPress",
}

_ATOM = "{http://www.w3.org/2005/Atom}"
_APP = "{http://purl.org/atom/app#}"
_BLOGGER = "{http://schemas.google.com/blogger/2018}"
_KIND = "http://schemas.google.com/g/2005#kind"
_LABEL = "http://www.blogger.com/atom/ns#"


class PlatformExportError(WxrError):
    """An export QUILL cannot read as Blogger, Medium, Substack or Squarespace."""

    code = "QUILL-WP-IMPORT-PLATFORM-UNREADABLE"


@dataclass
class Converted:
    """The export as a WXR file, which platform it came from, and what the preview says."""

    platform: str
    wxr: WxrFile
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return PLATFORMS.get(self.platform, self.platform)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")[:190]


def _host(url: str) -> str:
    return urlparse(url).hostname or ""


def _picture_hosts(items: list[WxrItem]) -> list[str]:
    found: set[str] = set()
    for item in items:
        for src in re.findall(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", item.content, re.I):
            if _host(src):
                found.add(_host(src))
    return sorted(found)


def _pictures_note(items: list[WxrItem], platform: str) -> str:
    hosts = _picture_hosts(items)
    if not hosts:
        return f"The {platform} export has no pictures in its posts."
    return (
        f"Pictures are not in a {platform} export, so the drafts keep showing them from "
        f"where they are now ({', '.join(hosts[:4])}); nothing is downloaded."
    )


# -- detection ------------------------------------------------------------------------


def detect(data: bytes, name: str = "the file") -> str:
    """Which platform *data* comes from: a key of :data:`PLATFORMS`, or ``""``."""
    if data[:4] == b"PK\x03\x04":
        try:
            names = _zip(data, name).namelist()
        except PlatformExportError:
            return ""
        if any(n.rsplit("/", 1)[-1] == "posts.csv" for n in names):
            return "substack"
        if any(_in_posts(n) and n.endswith(".html") for n in names):
            return "medium"
        return ""
    head = data[:4096].decode("utf-8", errors="ignore")
    if "<feed" in head and ("blogger" in head.casefold() or "Atom" in head):
        return "blogger"
    if "<rss" in head or "<channel" in head:
        lower = data[:65536].decode("utf-8", errors="ignore").casefold()
        if "wxr_version" not in lower or re.search(r"<generator>[^<]*squarespace", lower):
            return "squarespace"
        return "wordpress"
    return ""


def read_export(data: bytes, name: str = "the file") -> Converted:
    """Read any of the four exports (or a plain WXR file) as a :class:`Converted`."""
    if len(data) > MAX_FILE_BYTES:
        raise PlatformExportError(
            f"{name} is larger than {MAX_FILE_BYTES // 2**20} MB, which QUILL does not read."
        )
    platform = detect(data, name)
    if platform == "blogger":
        return read_blogger(data, name)
    if platform == "medium":
        return read_medium(data, name)
    if platform == "substack":
        return read_substack(data, name)
    if platform == "squarespace":
        return read_squarespace(data, name)
    if platform == "wordpress":
        return Converted("wordpress", read_wxr(data, name))
    raise PlatformExportError(
        f"{name} is not an export QUILL knows: not a Blogger backup, a Medium or Substack "
        "export zip, or a Squarespace or WordPress export file."
    )


# -- Blogger ----------------------------------------------------------------------------


def _atom_text(el: Any, tag: str) -> str:
    found = el.find(f"{_ATOM}{tag}")
    return (found.text or "").strip() if found is not None and found.text else ""


def _blogger_kind(entry: Any) -> str:
    typed = entry.find(f"{_BLOGGER}type")
    if typed is not None and typed.text:
        return str(typed.text).strip().lower()
    for cat in entry.findall(f"{_ATOM}category"):
        if cat.get("scheme") == _KIND:
            return str(cat.get("term", "")).rsplit("#", 1)[-1].lower()
    return ""


def _blogger_draft(entry: Any) -> bool:
    status = entry.find(f"{_BLOGGER}status")
    if status is not None and status.text:
        return str(status.text).strip().upper() != "LIVE"
    draft = entry.find(f"{_APP}control/{_APP}draft")
    return draft is not None and (draft.text or "").strip().lower() == "yes"


def _blogger_link(entry: Any) -> str:
    for link in entry.findall(f"{_ATOM}link"):
        if link.get("rel") == "alternate" and link.get("href"):
            return str(link.get("href"))
    filename = entry.find(f"{_BLOGGER}filename")
    return (filename.text or "").strip() if filename is not None and filename.text else ""


def read_blogger(data: bytes, name: str = "the file") -> Converted:
    """A Blogger backup (Atom) as WXR: posts and pages, labels as tags."""
    from quill.core.safe_xml import fromstring

    try:
        root = fromstring(data)
    except Exception as exc:  # noqa: BLE001 - any parse failure is one sentence
        raise PlatformExportError(f"{name} is not a readable Blogger backup: {exc}") from exc
    if root.tag != f"{_ATOM}feed":
        raise PlatformExportError(f"{name} is not an Atom feed, so it is not a Blogger backup.")
    blog_url = next(
        (
            str(lk.get("href"))
            for lk in root.findall(f"{_ATOM}link")
            if lk.get("rel") == "alternate"
        ),
        "",
    )
    found = WxrFile("Blogger", _atom_text(root, "title"), blog_url, blog_url)
    authors: dict[str, WxrAuthor] = {}
    terms: dict[str, WxrTerm] = {}
    skipped: dict[str, int] = {}
    drafts = 0
    for number, entry in enumerate(root.findall(f"{_ATOM}entry"), start=1):
        kind = _blogger_kind(entry)
        if kind not in ("post", "page"):
            skipped[kind or "unknown"] = skipped.get(kind or "unknown", 0) + 1
            continue
        if len(found.items) >= MAX_ITEMS:
            found.beyond_cap += 1
            continue
        author = entry.find(f"{_ATOM}author")
        who = _atom_text(author, "name") if author is not None else ""
        email = _atom_text(author, "email") if author is not None else ""
        login = who or email
        if login and login not in authors:
            authors[login] = WxrAuthor(login, "" if email == "noreply@blogger.com" else email, who)
        link = _blogger_link(entry)
        title = _atom_text(entry, "title")
        slug = link.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html") or _slug(title)
        draft = _blogger_draft(entry)
        drafts += draft
        item = WxrItem(
            post_id=number,
            post_type=kind,
            title=title,
            link=link,
            status="draft" if draft else "publish",
            creator=login,
            content=_atom_text(entry, "content"),
            excerpt="",
            slug=slug,
            date=(_atom_text(entry, "published") or "")[:19],
            parent=0,
            menu_order=0,
        )
        for cat in entry.findall(f"{_ATOM}category"):
            if cat.get("scheme") in (_LABEL, None) and cat.get("term"):
                label = str(cat.get("term"))
                terms.setdefault(label, WxrTerm("post_tag", _slug(label), label))
                item.terms.append(("post_tag", _slug(label), label))
        found.items.append(item)
    found.authors = list(authors.values())
    found.terms = list(terms.values())
    notes = [
        f"From the Blogger blog {found.title or name} ({blog_url or 'no address given'}).",
        _pictures_note(found.items, "Blogger"),
    ]
    if drafts:
        notes.append(f"{drafts} of them were drafts on Blogger.")
    for kind, count in sorted(skipped.items()):
        notes.append(f"Left out: {count} Blogger {kind} entries; only posts and pages come over.")
    return Converted("blogger", found, notes)


# -- zips: Medium and Substack -----------------------------------------------------------


def _zip(data: bytes, name: str) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise PlatformExportError(f"{name} is not a readable zip file.") from exc
    infos = archive.infolist()
    if len(infos) > MAX_MEMBERS:
        raise PlatformExportError(
            f"{name} holds more than {MAX_MEMBERS} files, which QUILL does not read."
        )
    if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        raise PlatformExportError(
            f"{name} unpacks to more than {MAX_TOTAL_BYTES // 2**20} MB, which QUILL does not read."
        )
    return archive


def _safe(member: str) -> bool:
    return not (
        member.startswith(("/", "\\")) or ".." in re.split(r"[\\/]", member) or ":" in member
    )


def _in_posts(member: str) -> bool:
    parts = member.replace("\\", "/").split("/")
    return _safe(member) and len(parts) >= 2 and parts[-2] == "posts"


def _read(archive: zipfile.ZipFile, member: str) -> str:
    return archive.read(member).decode("utf-8", errors="replace")


def _between(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    return match.group(1).strip() if match else ""


def _plain(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _medium_story(text: str) -> dict[str, str]:
    body = _between(text, r'<section[^>]*data-field="body"[^>]*>(.*?)<footer')
    body = re.sub(r"\s*</section>\s*$", "", body)
    # Medium repeats the title as the body's first heading; the draft has its own title.
    body = re.sub(
        r"^\s*(<section[^>]*>\s*(?:<div[^>]*>\s*)*)?<h3[^>]*graf--title[^>]*>.*?</h3>",
        r"\1",
        body,
        flags=re.S,
    )
    return {
        "title": _plain(_between(text, r'<h1[^>]*class="p-name"[^>]*>(.*?)</h1>'))
        or _plain(_between(text, r"<title>(.*?)</title>")),
        "subtitle": _plain(
            _between(text, r'<section[^>]*data-field="subtitle"[^>]*>(.*?)</section>')
        ),
        "body": body,
        "author": _plain(_between(text, r'<a[^>]*class="p-author h-card"[^>]*>(.*?)</a>')),
        "date": _between(text, r'<time[^>]*class="dt-published"[^>]*datetime="([^"]+)"'),
        "link": _between(text, r'<a[^>]*href="([^"]+)"[^>]*class="p-canonical"'),
    }


def read_medium(data: bytes, name: str = "the file") -> Converted:
    """A Medium export zip as WXR: each story under ``posts/`` as a post."""
    archive = _zip(data, name)
    members = sorted(n for n in archive.namelist() if _in_posts(n) and n.endswith(".html"))
    if not members:
        raise PlatformExportError(f"{name} has no posts folder, so it is not a Medium export.")
    found = WxrFile("Medium", "Medium stories", "https://medium.com", "https://medium.com")
    authors: dict[str, WxrAuthor] = {}
    drafts = 0
    for number, member in enumerate(members, start=1):
        if len(found.items) >= MAX_ITEMS:
            found.beyond_cap += 1
            continue
        story = _medium_story(_read(archive, member))
        base = member.rsplit("/", 1)[-1].removesuffix(".html")
        draft = base.startswith("draft_")
        drafts += draft
        if story["author"] and story["author"] not in authors:
            authors[story["author"]] = WxrAuthor(story["author"], "", story["author"])
        slug = re.sub(r"-[0-9a-f]{8,12}$", "", base.removeprefix("draft_").split("_", 1)[-1])
        found.items.append(
            WxrItem(
                post_id=number,
                post_type="post",
                title=story["title"],
                link=story["link"],
                status="draft" if draft else "publish",
                creator=story["author"],
                content=story["body"],
                excerpt=story["subtitle"],
                slug=_slug(slug) or _slug(story["title"]),
                date=story["date"][:19].replace("T", " "),
                parent=0,
                menu_order=0,
            )
        )
    found.authors = list(authors.values())
    notes = [
        f"From a Medium export: {len(found.items)} stories, the subtitle as each excerpt.",
        _pictures_note(found.items, "Medium"),
        "Responses, claps and highlights are not in a Medium export's stories.",
    ]
    if drafts:
        notes.append(f"{drafts} of them were drafts on Medium.")
    return Converted("medium", found, notes)


def read_substack(data: bytes, name: str = "the file") -> Converted:
    """A Substack export zip as WXR: each row of ``posts.csv`` with its HTML body."""
    archive = _zip(data, name)
    listed = [n for n in archive.namelist() if n.rsplit("/", 1)[-1] == "posts.csv" and _safe(n)]
    if not listed:
        raise PlatformExportError(f"{name} has no posts.csv, so it is not a Substack export.")
    bodies = {
        n.replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".html"): n
        for n in archive.namelist()
        if _in_posts(n) and n.endswith(".html")
    }
    rows = list(csv.DictReader(io.StringIO(_read(archive, listed[0]))))
    found = WxrFile("Substack", "Substack posts", "", "")
    threads = paid = unpublished = 0
    for number, row in enumerate(rows, start=1):
        post_id = str(row.get("post_id", "") or "").strip()
        kind = str(row.get("type", "") or "newsletter").strip()
        member = bodies.get(post_id)
        if kind == "thread" or member is None:
            threads += 1
            continue
        if len(found.items) >= MAX_ITEMS:
            found.beyond_cap += 1
            continue
        published = str(row.get("is_published", "")).strip().lower() == "true"
        unpublished += not published
        audience = str(row.get("audience", "") or "everyone").strip()
        paid += audience not in ("", "everyone")
        content = _read(archive, member)
        podcast = str(row.get("podcast_url", "") or "").strip()
        if podcast:
            content = f'<p><audio controls src="{html.escape(podcast)}"></audio></p>\n' + content
        found.items.append(
            WxrItem(
                post_id=number,
                post_type="post",
                title=str(row.get("title", "") or "").strip(),
                link="",
                status="publish" if published else "draft",
                creator="",
                content=content,
                excerpt=str(row.get("subtitle", "") or "").strip(),
                slug=_slug(post_id.partition(".")[2]),
                date=str(row.get("post_date", "") or "")[:19].replace("T", " "),
                parent=0,
                menu_order=0,
            )
        )
    notes = [
        f"From a Substack export: {len(found.items)} posts, the subtitle as each excerpt.",
        _pictures_note(found.items, "Substack"),
        "Subscribers are not imported; their list is a separate file in the export.",
    ]
    if unpublished:
        notes.append(f"{unpublished} of them were never published on Substack.")
    if paid:
        notes.append(
            f"{paid} were for paying subscribers only; here they are drafts like the rest."
        )
    if threads:
        notes.append(f"Left out: {threads} threads and posts with no body in the export.")
    return Converted("substack", found, notes)


# -- Squarespace -------------------------------------------------------------------------

_RELATIVE = re.compile(r"""(\b(?:href|src)\s*=\s*["'])(/[^/"'][^"']*|/)(["'])""", re.I)


def read_squarespace(data: bytes, name: str = "the file") -> Converted:
    """A Squarespace WXR export, its relative addresses made whole against the site."""
    wxr = read_wxr(data, name, need_version=False)
    home = wxr.blog_url or wxr.site_url
    if not home:
        match = re.search(rb"<link>\s*(https?://[^<\s]+)", data)
        home = match.group(1).decode("utf-8", "ignore") if match else ""
    wxr.blog_url = wxr.blog_url or home
    wxr.site_url = wxr.site_url or home
    wxr.version = wxr.version or "1.2 (as Squarespace writes it)"
    fixed = 0
    for item in wxr.items:
        if home:
            content, count = _RELATIVE.subn(
                lambda m: m.group(1) + urljoin(home, m.group(2)) + m.group(3), item.content
            )
            item.content, fixed = content, fixed + count
            if item.attachment_url.startswith("/"):
                item.attachment_url = urljoin(home, item.attachment_url)
                fixed += 1
            if item.link.startswith("/"):
                item.link = urljoin(home, item.link)
        if not item.slug and item.link:
            item.slug = _slug(item.link.rstrip("/").rsplit("/", 1)[-1])
    notes = [f"From the Squarespace site {wxr.title or name} ({home or 'no address given'})."]
    if fixed:
        notes.append(
            f"{fixed} addresses in the file were written from the site's root; they are read "
            f"as {home}, and links between the imported pages then point here."
        )
    notes.append(
        "Squarespace's own layout markup is kept as it is; galleries, forms and product "
        "blocks Squarespace makes on its own servers are not in the export."
    )
    return Converted("squarespace", wxr, notes)
