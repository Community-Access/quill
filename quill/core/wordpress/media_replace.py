"""Replace a media file, keeping its address where the site can (wp_missing.md, Media).

Core WordPress has **no REST route that swaps an attachment's file in place**:
``POST wp/v2/media`` makes a new attachment and ``wp/v2/media/{id}/edit``
makes an edited copy (WordPress Trac #49096 asks for one). Enable Media
Replace, the plugin most sites use for this, works only in wp-admin: it adds
a Replace Media box to the attachment's edit screen and registers no REST
route. So Replace File has three paths, chosen by what the site says:

- **In place** (:func:`replace_route`, :func:`replace_in_place`): where the
  site's own REST index lists a route under a plugin's namespace shaped like
  ``.../media/(?P<id>...)/replace`` (or ``.../replace-media/(?P<id>...)``)
  that takes POST, the new file is sent there as the raw body, the way
  ``wp/v2/media`` takes an upload. QUILL then reads the attachment back and
  says whether its address really stayed the same, and remakes a picture's
  sizes. No such route is verified against a live install yet (wordpress.md
  19), so the read-back is what QUILL trusts, not the answer.
- **wp-admin** (:func:`emr_screen`): where Enable Media Replace is active,
  its box on the attachment's edit screen, in the browser.
- **New file, uses repointed** (:func:`plan_repoint`): the new file is
  uploaded as a new attachment and every post, page, synced pattern,
  featured image and REST-visible custom field that used the old one is
  rewritten to the new one, previewed, conflict-checked and undoable through
  :mod:`quill.core.wordpress.workbench_by_name`'s :class:`Edit`. The file's
  address changes; links from other websites to the old address break unless
  a redirect is added (:func:`redirect_for`, through ``redirection/v1``).

Wx-free; every request goes through the site's own client, off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered
from quill.core.wordpress.workbench_by_name import Edit

__all__ = [
    "EMR_PLUGIN",
    "FileFacts",
    "Repoint",
    "emr_active",
    "emr_screen",
    "file_facts",
    "plan_repoint",
    "preview_lines",
    "redirect_for",
    "replace_in_place",
    "replace_route",
    "repoint_edits",
    "rewrite_uses",
    "said_after_repoint",
]

EMR_PLUGIN = "enable-media-replace/enable-media-replace"
"""Enable Media Replace's plugin id in ``wp/v2/plugins``."""

_ID = r"\(\?P<id>[^)]*\)"
_REPLACE_ROUTES = (
    re.compile(rf"^/(?!wp/v2/)[^?]+/(?:media|attachments?)/{_ID}/replace(?:-file)?$"),
    re.compile(rf"^/(?!wp/v2/)[^?]+/replace(?:-media|-file)?/{_ID}$"),
)
_SCAN_TYPES = (("post", "wp/v2/posts"), ("page", "wp/v2/pages"), ("pattern", "wp/v2/blocks"))
_FIELDS = "id,type,title,content,featured_media,meta,modified_gmt"


@dataclass(frozen=True)
class FileFacts:
    """What a preview says about one file: its name, size and type."""

    name: str
    size: int
    kind: str

    def words(self) -> str:
        from quill.core.wordpress.site import human_size

        size = human_size(self.size) if self.size else "size not given"
        return f"{self.name}, {size}, {self.kind or 'type not given'}"


def file_facts(raw: Mapping[str, Any]) -> FileFacts:
    """An attachment's name, size and type, as the site reports them."""
    details = raw.get("media_details")
    details = details if isinstance(details, Mapping) else {}
    address = str(raw.get("source_url", "") or "")
    return FileFacts(
        address.rsplit("/", 1)[-1] or rendered(raw.get("title")),
        int(details.get("filesize", 0) or 0),
        str(raw.get("mime_type", "") or ""),
    )


def replace_route(routes: Mapping[str, Any], media_id: int) -> str:
    """The route that replaces *media_id*'s file in place, from the site's index; "" if none.

    Only a route the site itself lists under a plugin's namespace, shaped like
    a replace route, that takes POST. Core's ``wp/v2`` has none.
    """
    for route, entry in routes.items():
        if not any(rx.search(route) for rx in _REPLACE_ROUTES):
            continue
        methods = entry.get("methods", ()) if isinstance(entry, Mapping) else ()
        if methods and "POST" not in [str(m).upper() for m in methods]:
            continue
        return re.sub(_ID, str(int(media_id)), route).lstrip("/")
    return ""


def emr_active(plugins: Iterable[Mapping[str, Any]]) -> bool:
    """Whether Enable Media Replace is installed and active on the site."""
    return any(
        str(p.get("plugin", "")) == EMR_PLUGIN and str(p.get("status", "")) == "active"
        for p in plugins
    )


def emr_screen(site_url: str, media_id: int) -> str:
    """The attachment's wp-admin edit screen, where Enable Media Replace adds its box."""
    return f"{site_url.rstrip('/')}/wp-admin/post.php?post={int(media_id)}&action=edit"


def preview_lines(old: FileFacts, new: FileFacts, address: str, *, in_place: bool) -> list[str]:
    """The preview: old and new file, and what happens to the address."""
    lines = [f"Now: {old.words()}.", f"New: {new.words()}."]
    if in_place:
        lines += [
            f"The address stays the same: {address}",
            "Pictures have their sizes remade after the file is replaced.",
        ]
    else:
        lines += [
            f"The address changes. The old one is {address}; the new one is whatever the "
            "site gives the upload.",
        ]
    if old.kind and new.kind and old.kind != new.kind:
        lines.append(f"The type changes from {old.kind} to {new.kind}.")
    return lines


def _plain(address: str) -> str:
    return address.split("?", 1)[0].split("#", 1)[0]


def replace_in_place(
    api: WordPressApi,
    route: str,
    media_id: int,
    filename: str,
    content: bytes,
    content_type: str,
    old_address: str,
) -> tuple[bool, str]:
    """Send the new file to *route*, read the attachment back, remake sizes: (kept, sentence).

    *kept* is True only when the read-back address equals *old_address*.
    """
    api.upload(route, filename, content, content_type)
    after = api.get(f"wp/v2/media/{int(media_id)}", context="edit")
    after = after if isinstance(after, Mapping) else {}
    now = str(after.get("source_url", "") or "")
    facts = file_facts(after)
    if _plain(now) != _plain(old_address):
        return False, (
            f"The site took the file, but its address is now {now or 'not given'}, not "
            f"{old_address}. Links to the old address may break."
        )
    said = (
        f"Replaced. The address is the same, {old_address}, and the site now has {facts.words()}."
    )
    if str(after.get("mime_type", "")).startswith("image/"):
        try:
            api.post(
                f"wp/v2/media/{int(media_id)}/post-process", {"action": "create-image-subsizes"}
            )
            said += " Its sizes were remade."
        except WordPressApiError as exc:
            said += f" Its sizes were not remade: {exc.plain or exc}"
    return True, said


# -- the honest alternative: a new file, and every use pointed at it -----------------


@dataclass
class Repoint:
    """Every use of the old file the scan found, and what the scan could not change."""

    site: str
    old_id: int
    old_url: str
    items: list[Mapping[str, Any]] = field(default_factory=list)
    numeric_meta: list[str] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        said = [f"{_kind(raw)} {_title(raw)}: {', '.join(_uses(self, raw))}" for raw in self.items]
        said += [f"Not changed: {m}" for m in self.numeric_meta]
        said += [f"Not read, so not changed: {u}" for u in self.unread]
        return said


def _kind(raw: Mapping[str, Any]) -> str:
    return {"page": "Page", "wp_block": "Pattern"}.get(str(raw.get("type", "")), "Post")


def _title(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("title")) or rendered(raw.get("title")) or f"#{raw.get('id', '')}"


def _stem_pattern(old_url: str) -> re.Pattern[str]:
    """The old file's address, its sized copies (``-300x200``, ``-scaled``) and escaped form."""
    base, _dot, ext = old_url.rpartition(".")
    if not base:
        return re.compile(re.escape(old_url))
    tail = r"(?:-\d+x\d+|-scaled|-rotated)*\." + re.escape(ext)
    plain = re.escape(base) + tail
    escaped = re.escape(base.replace("/", "\\/")) + tail
    return re.compile(f"(?:{plain}|{escaped})", re.IGNORECASE)


def rewrite_uses(text: str, old_id: int, old_url: str, new_id: int, new_url: str) -> str:
    """*text* with every use of the old file pointed at the new one.

    The address and its sized copies become the new file's address (a sized
    copy becomes the full file, which the theme scales); ``wp-image-<id>``
    classes and block ``id`` / ``mediaId`` attributes take the new number.
    """
    if not text:
        return text
    pattern = _stem_pattern(old_url)

    def address(match: re.Match[str]) -> str:
        return new_url.replace("/", "\\/") if "\\/" in match.group(0) else new_url

    text = pattern.sub(address, text) if old_url else text
    text = re.sub(rf"\bwp-image-{int(old_id)}\b", f"wp-image-{int(new_id)}", text)
    block = (
        r'(<!--\s*wp:(?:image|audio|video|file|cover|media-text|gallery)\b[^>]*?"'
        rf'(?:id|mediaId)"\s*:\s*){int(old_id)}\b'
    )
    return re.sub(block, rf"\g<1>{int(new_id)}", text)


def _content(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("content")) or rendered(raw.get("content"))


def _meta_hits(raw: Mapping[str, Any], old_url: str) -> list[str]:
    meta = raw.get("meta")
    if not isinstance(meta, Mapping):
        return []
    return [k for k, v in meta.items() if isinstance(v, str) and old_url and old_url in v]


def _uses(plan: Repoint, raw: Mapping[str, Any]) -> list[str]:
    said = []
    if rewrite_uses(_content(raw), plan.old_id, plan.old_url, 0, "\x00") != _content(raw):
        said.append("its text")
    if int(raw.get("featured_media", 0) or 0) == plan.old_id:
        said.append("its featured image")
    said += [f"the custom field {k}" for k in _meta_hits(raw, plan.old_url)]
    return said


def plan_repoint(api: WordPressApi, site: str, old: Mapping[str, Any]) -> Repoint:
    """Read every post, page and synced pattern, and keep the ones that use *old*."""
    plan = Repoint(site, int(old.get("id", 0) or 0), str(old.get("source_url", "") or ""))
    params = {
        "context": "edit",
        "status": "publish,future,draft,pending,private",
        "_fields": _FIELDS,
    }
    for word, route in _SCAN_TYPES:
        try:
            for raw in api.iter_collection(route, params):
                if _uses(plan, raw):
                    plan.items.append(raw)
                meta = raw.get("meta")
                for key, value in meta.items() if isinstance(meta, Mapping) else ():
                    if isinstance(value, int) and not isinstance(value, bool):
                        if value == plan.old_id and key != "featured_media":
                            plan.numeric_meta.append(
                                f"{_title(raw)}: the custom field {key} holds {value}, which "
                                "may be this file's number; QUILL leaves numbers alone"
                            )
        except WordPressApiError as exc:
            plan.unread.append(f"{word}s ({exc.plain or exc})")
    return plan


def repoint_edits(plan: Repoint, new_id: int, new_url: str) -> list[Edit]:
    """One conflict-checked :class:`Edit` per item, once the new file's number is known."""
    edits = []
    for raw in plan.items:
        body: dict[str, Any] = {}
        before: dict[str, Any] = {}
        text = _content(raw)
        changed = rewrite_uses(text, plan.old_id, plan.old_url, new_id, new_url)
        if changed != text:
            body["content"], before["content"] = changed, text
        if int(raw.get("featured_media", 0) or 0) == plan.old_id:
            body["featured_media"], before["featured_media"] = new_id, plan.old_id
        hits = _meta_hits(raw, plan.old_url)
        if hits:
            found = raw.get("meta")
            meta: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
            body["meta"] = {k: str(meta[k]).replace(plan.old_url, new_url) for k in hits}
            before["meta"] = {k: meta[k] for k in hits}
        if body:
            base = {"page": "pages", "wp_block": "blocks"}.get(str(raw.get("type")), "posts")
            edits.append(
                Edit(
                    plan.site,
                    f"wp/v2/{base}/{raw.get('id')}",
                    _title(raw),
                    body,
                    before,
                    "modified_gmt",
                    raw.get("modified_gmt"),
                    "uses the new file",
                )
            )
    return edits


def redirect_for(old_url: str, new_url: str, group_id: int) -> dict[str, Any]:
    """Redirection's body for a 301 from the old file's address to the new one."""
    from quill.core.wordpress.workbench_sweep import redirect_body

    body = redirect_body(old_url, new_url, group_id)
    body["title"] = "Made by QUILL when a media file was replaced"
    return body


def said_after_repoint(
    changed: int, failed: Sequence[str], *, redirect: str, old_kept: bool
) -> str:
    """The closing sentence: the address changed, how many places QUILL updated, what breaks."""
    said = f"The file's address changes; QUILL updated {changed} places that used it."
    if failed:
        said += f" {len(failed)} were not changed: {failed[0]}."
    said += (
        f" {redirect}"
        if redirect
        else " Links from other websites to the old address will break unless a redirect is added."
    )
    said += " The old file is still in the library." if old_kept else " The old file was deleted."
    return said
