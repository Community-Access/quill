"""By Name operations within one site: rename, split, merge, reassign, replace (PRD 15.12).

:mod:`quill.core.wordpress.workbench_across` lists every value of a kind
(terms, field values, authors, media, patterns, links, blocks and shortcodes,
forms) with where it is used. This module changes a value **everywhere it is
used**, as a list of :class:`Edit` objects that the window previews site by
site and item by item before anything is sent:

- **terms** (categories, tags and every custom taxonomy the scan read): rename
  (name and slug), split (chosen items move to a new term), merge (every item
  moves to another term, then the old term is deleted), reassign (items move
  to another existing term, the old one stays);
- **field values**: rename (the value changes on every item that has it),
  split (only on chosen items), merge (into another value already in use);
- **authors**: reassign (every item to another person) and split (chosen
  items only);
- **media, patterns, links, shortcodes, forms**: replace (the content of
  every item that uses it is rewritten to use another).

Each :class:`Edit` carries the item's state as read (``before``) and a
**conflict stamp**: :func:`apply_edits` reads the item again first, and an
item changed on the site since the scan is left alone and said so. Undo
(:func:`undo_edits`) sends ``before`` back, and only for edits that can truly
be restored; a merge deletes the old term, so it is said to be final.

Wx-free; requests go through the site's own client, off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered

__all__ = [
    "Edit",
    "Outcome",
    "apply_edits",
    "field_items",
    "items_missing_field",
    "outcome_report",
    "part_uses",
    "plan_author",
    "plan_field",
    "plan_part_rename",
    "plan_replace",
    "plan_term_move",
    "plan_term_rename",
    "split_term",
    "term_base",
    "term_uses",
    "undo_edits",
    "unread_preview",
]


@dataclass(frozen=True)
class Edit:
    """One request that changes one thing on one site, with what it was before."""

    site: str
    route: str
    title: str
    body: Mapping[str, Any]
    before: Mapping[str, Any] | None  # None: cannot be put back
    stamp_field: str = ""  # read again before sending; a different value is a conflict
    stamp: Any = None
    words: str = ""  # the preview line

    @property
    def line(self) -> str:
        return f"{self.site}: {self.title}: {self.words}"


@dataclass(frozen=True)
class Outcome:
    """What happened to one edit: sent, refused by the site, or left alone after a conflict."""

    site: str
    title: str
    ok: bool
    words: str

    @property
    def line(self) -> str:
        return f"{self.site}: {self.title}: {self.words}"


def _content(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("content")) or rendered(raw.get("content"))


def _title(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("title")) or rendered(raw.get("title")) or f"#{raw.get('id', '')}"


def _item_route(raw: Mapping[str, Any]) -> str:
    base = "pages" if raw.get("type") == "page" else "posts"
    return f"wp/v2/{base}/{raw.get('id')}"


def _item_edit(
    site: str,
    raw: Mapping[str, Any],
    body: Mapping[str, Any],
    before: Mapping[str, Any],
    words: str,
) -> Edit:
    return Edit(
        site,
        _item_route(raw),
        _title(raw),
        body,
        before,
        "modified_gmt",
        raw.get("modified_gmt"),
        words,
    )


# -- terms ------------------------------------------------------------------------


def term_base(scan: Any, taxonomy: str) -> str:
    """The REST base of *taxonomy*: its route under wp/v2 and the item field naming its terms."""
    bases: Mapping[str, str] = getattr(scan, "term_bases", {}) or {}
    return bases.get(taxonomy) or {"category": "categories", "post_tag": "tags"}.get(
        taxonomy, taxonomy
    )


def _split_key(key: str) -> tuple[str, int]:
    taxonomy, _sep, ident = key.rpartition(":")
    return taxonomy, int(ident or 0)


def _term(scan: Any, key: str) -> Mapping[str, Any]:
    taxonomy, ident = _split_key(key)
    for tax, raw in scan.terms:
        if tax == taxonomy and int(raw.get("id", 0) or 0) == ident:
            return dict(raw)
    return {}


def term_uses(scan: Any, key: str) -> list[Mapping[str, Any]]:
    """Every post and page the scan read that has the term *key* (``taxonomy:id``)."""
    taxonomy, ident = _split_key(key)
    base = term_base(scan, taxonomy)
    return [raw for raw in scan.items if ident in (raw.get(base) or [])]


def plan_term_rename(scan: Any, key: str, name: str, slug: str) -> list[Edit]:
    """Rename a term (and its slug, when given): one request, wherever it is used."""
    raw = _term(scan, key)
    if not raw:
        return []
    taxonomy, ident = _split_key(key)
    body: dict[str, Any] = {"name": name}
    before: dict[str, Any] = {"name": raw.get("name", "")}
    if slug:
        body["slug"] = slug
        before["slug"] = raw.get("slug", "")
    words = f"renamed from {raw.get('name', '')} to {name}"
    if slug:
        words += f", slug {raw.get('slug', '')} to {slug}"
    return [
        Edit(
            scan.site,
            f"wp/v2/{term_base(scan, taxonomy)}/{ident}",
            str(raw.get("name", "")),
            body,
            before,
            "name",
            raw.get("name", ""),
            words,
        )
    ]


def plan_term_move(
    scan: Any, key: str, target_id: int, target_name: str, item_ids: Iterable[int] | None = None
) -> list[Edit]:
    """Move items from term *key* to *target_id*: every item, or only *item_ids*.

    The old term is taken off each item and the target put on; the items'
    other terms stay. This is reassign and merge (every item) and split
    (chosen items, to a term just made).
    """
    taxonomy, ident = _split_key(key)
    base = term_base(scan, taxonomy)
    chosen = None if item_ids is None else set(item_ids)
    old = str(_term(scan, key).get("name", "")) or key
    edits: list[Edit] = []
    for raw in term_uses(scan, key):
        if chosen is not None and int(raw.get("id", 0)) not in chosen:
            continue
        terms = [int(t) for t in raw.get(base) or []]
        moved = [t for t in terms if t != ident]
        if target_id not in moved:
            moved.append(target_id)
        edits.append(
            _item_edit(
                scan.site,
                raw,
                {base: moved},
                {base: terms},
                f"moves from {old} to {target_name}",
            )
        )
    return edits


def split_term(
    api: WordPressApi, scan: Any, key: str, new_name: str, item_ids: Iterable[int]
) -> tuple[int, list[Edit]]:
    """Make the new term for a split, and plan the chosen items' move to it.

    Returns the new term's id (to delete on undo) and the edits.
    """
    taxonomy, _ident = _split_key(key)
    made = api.post(f"wp/v2/{term_base(scan, taxonomy)}", {"name": new_name})
    new_id = int(made.get("id", 0) or 0) if isinstance(made, dict) else 0
    if not new_id:
        raise WordPressApiError(f"{scan.site} did not make the term {new_name}.")
    return new_id, plan_term_move(scan, key, new_id, new_name, item_ids)


# -- field values -------------------------------------------------------------------


def _field_pair(value: str) -> tuple[str, str]:
    key, _sep, said = value.partition(": ")
    return key, said


def field_items(scan: Any, value: str) -> list[Mapping[str, Any]]:
    """The items whose custom field has this value (``key: value`` as the row reads)."""
    key, said = _field_pair(value)
    found = []
    for raw in scan.items:
        meta = raw.get("meta")
        if isinstance(meta, dict) and key in meta and str(meta[key]) == said:
            found.append(raw)
    return found


def items_missing_field(scan: Any, key: str) -> list[str]:
    """The titles of items with no value for the field *key*."""
    missing = []
    for raw in scan.items:
        meta = raw.get("meta")
        if not isinstance(meta, dict) or meta.get(key) in ("", None, [], {}):
            missing.append(_title(raw))
    return missing


def plan_field(
    scan: Any, value: str, new_value: str, item_ids: Iterable[int] | None = None
) -> list[Edit]:
    """Change a field value on every item with it (rename, merge), or on chosen ones (split)."""
    key, said = _field_pair(value)
    chosen = None if item_ids is None else set(item_ids)
    edits = []
    for raw in field_items(scan, value):
        if chosen is not None and int(raw.get("id", 0)) not in chosen:
            continue
        old = raw["meta"][key]
        edits.append(
            _item_edit(
                scan.site,
                raw,
                {"meta": {key: new_value}},
                {"meta": {key: old}},
                f"{key} changes from {said} to {new_value}",
            )
        )
    return edits


# -- authors ------------------------------------------------------------------------


def plan_author(
    scan: Any, author: int, new_author: int, item_ids: Iterable[int] | None = None
) -> list[Edit]:
    """Give every item by *author* (or the chosen ones) to *new_author*."""
    chosen = None if item_ids is None else set(item_ids)
    old = scan.users.get(author, f"person {author}")
    new = scan.users.get(new_author, f"person {new_author}")
    edits = []
    for raw in scan.items:
        if int(raw.get("author", 0) or 0) != author:
            continue
        if chosen is not None and int(raw.get("id", 0)) not in chosen:
            continue
        edits.append(
            _item_edit(
                scan.site, raw, {"author": new_author}, {"author": author}, f"from {old} to {new}"
            )
        )
    return edits


# -- template parts (block themes) ------------------------------------------------


def _places_part(text: str, slug: str) -> bool:
    for match in re.finditer(r"<!--\s+wp:template-part\s+(\{.*?\})\s+/?-->", text):
        if re.search(rf'"slug"\s*:\s*"{re.escape(slug)}"', match.group(1)):
            return True
    return False


def part_uses(scan: Any, slug: str) -> list[str]:
    """The templates, then the posts and pages, that place the template part *slug*."""
    if not slug:
        return []
    found = [
        f"template {_title(t)}"
        for t in getattr(scan, "templates", [])
        if _places_part(_content(t), slug)
    ]
    found += [_title(raw) for raw in scan.items if _places_part(_content(raw), slug)]
    return found


def plan_part_rename(scan: Any, part_id: str, title: str) -> list[Edit]:
    """A template part's new title. Its slug stays: templates place a part by slug."""
    part = next(
        (p for p in getattr(scan, "template_parts", []) if str(p.get("id")) == part_id), None
    )
    if part is None:
        return []
    old = _title(part)
    return [
        Edit(
            scan.site,
            f"wp/v2/template-parts/{part_id}",
            old,
            {"title": title},
            {"title": old},
            "title",
            part.get("title"),
            f"title {old} becomes {title}; its slug {part.get('slug', '')} stays",
        )
    ]


# -- replacing in content -----------------------------------------------------------


def _media_by_name(scan: Any, name: str) -> Mapping[str, Any]:
    for media in scan.media:
        if str(media.get("source_url", "") or "").rsplit("/", 1)[-1] == name:
            return dict(media)
    return {}


def _pattern_id(scan: Any, title: str) -> int:
    for ident, said in scan.patterns.items():
        if said == title:
            return int(ident)
    match = re.fullmatch(r"pattern (\d+)", title)
    return int(match.group(1)) if match else 0


def _rewriter(scan: Any, kind: str, old: str, new: str) -> tuple[Any, str]:
    """A function rewriting one item's content and featured picture, and why not (or "")."""
    if kind == "links":
        return (lambda text: text.replace(old, new)), ""
    if kind == "media_usage":
        was, now = _media_by_name(scan, old), _media_by_name(scan, new)
        if not was or not now:
            return None, f"{new} is not in the site's Media Library as read."
        old_url, new_url = str(was.get("source_url")), str(now.get("source_url"))
        old_stem, new_stem = old_url.rsplit(".", 1)[0], new_url.rsplit(".", 1)[0]

        def media(text: str) -> str:
            text = text.replace(old_url, new_url).replace(old_stem, new_stem)
            return re.sub(
                rf'("id"\s*:\s*){int(was.get("id", 0))}\b', rf"\g<1>{now.get('id')}", text
            )

        return media, ""
    if kind == "patterns":
        was_id, now_id = _pattern_id(scan, old), _pattern_id(scan, new)
        if not was_id or not now_id:
            return None, f"{new} is not one of the site's synced patterns."
        return (lambda text: re.sub(rf'("ref"\s*:\s*){was_id}\b', rf"\g<1>{now_id}", text)), ""
    if kind == "forms":
        was_n, now_n = old.removeprefix("Form "), new.removeprefix("Form ")
        if not now_n.isdigit():
            return None, "Name the other form by its number, such as Form 7."
        pattern = rf'((?:qaf|baf)/form\s+\{{[^}}]*"(?:formId|id)"\s*:\s*){was_n}\b'
        return (lambda text: re.sub(pattern, rf"\g<1>{now_n}", text)), ""
    if kind == "blocks":
        match = re.fullmatch(r"\[([a-z][a-z0-9_-]*)\] shortcode", old)
        if match is None:
            return None, (
                "A block's type is its markup, so QUILL does not rewrite blocks by name; "
                "shortcodes can be replaced."
            )
        code, other = match.group(1), new.strip("[] ").removesuffix("] shortcode").strip("[] ")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", other):
            return None, "A shortcode name is lower-case letters, digits, - and _."

        def shortcode(text: str) -> str:
            text = re.sub(rf"\[{code}(?=[\s\]/])", f"[{other}", text)
            return text.replace(f"[/{code}]", f"[/{other}]")

        return shortcode, ""
    return None, f"{kind} values are not replaced in content."


def plan_replace(scan: Any, kind: str, old: str, new: str) -> tuple[list[Edit], str]:
    """Rewrite every item using *old* to use *new* instead; or no edits and why."""
    rewrite, reason = _rewriter(scan, kind, old, new)
    if rewrite is None:
        return [], reason
    edits = []
    was = _media_by_name(scan, old) if kind == "media_usage" else {}
    now = _media_by_name(scan, new) if kind == "media_usage" else {}
    for raw in scan.items:
        text = _content(raw)
        changed = rewrite(text)
        body: dict[str, Any] = {}
        before: dict[str, Any] = {}
        if changed != text:
            body["content"], before["content"] = changed, text
        featured = int(raw.get("featured_media", 0) or 0)
        if was and featured and featured == int(was.get("id", -1)):
            body["featured_media"], before["featured_media"] = int(now.get("id", 0)), featured
        if body:
            edits.append(_item_edit(scan.site, raw, body, before, f"uses {new} instead of {old}"))
    return edits, "" if edits else f"Nothing the scan read uses {old}."


# -- sending, the conflict check, and undo ----------------------------------------


def _current(api: WordPressApi, edit: Edit) -> Any:
    raw = api.get(edit.route, context="edit", _fields=edit.stamp_field)
    return raw.get(edit.stamp_field) if isinstance(raw, dict) else None


def apply_edits(api: WordPressApi, edits: Sequence[Edit]) -> tuple[list[Outcome], list[Edit]]:
    """Send each edit after its conflict check: per-item outcomes, and the edits that were sent."""
    outcomes: list[Outcome] = []
    sent: list[Edit] = []
    for edit in edits:
        try:
            if edit.stamp_field and edit.stamp is not None:
                now = _current(api, edit)
                if now != edit.stamp:
                    outcomes.append(
                        Outcome(
                            edit.site,
                            edit.title,
                            False,
                            "changed on the site since QUILL read it, so it was left alone; "
                            "read the list again and retry",
                        )
                    )
                    continue
            api.post(edit.route, dict(edit.body))
        except WordPressApiError as exc:
            outcomes.append(Outcome(edit.site, edit.title, False, exc.plain or str(exc)))
            continue
        outcomes.append(Outcome(edit.site, edit.title, True, edit.words))
        sent.append(edit)
    return outcomes, sent


def undo_edits(api_for: Any, sent: Sequence[Edit]) -> str:
    """Put back what *sent* changed, newest first; edits with no ``before`` are said, not faked."""
    put = 0
    kept: list[str] = []
    for edit in reversed(sent):
        if edit.before is None:
            kept.append(edit.title)
            continue
        try:
            api_for(edit.site).post(edit.route, dict(edit.before))
            put += 1
        except WordPressApiError as exc:
            kept.append(f"{edit.title} ({exc.plain or exc})")
    said = f"Put {put} back as they were."
    if kept:
        said += f" Not put back: {'; '.join(kept[:3])}."
    return said


def unread_preview(scan: Any, kind: str) -> tuple[str, list[str]]:
    """What a preview must say about lists the scan could not read for *kind*.

    The sentence (empty when every list was read) and one preview line per
    list, so an operation planned from a partial scan says so instead of
    looking complete (complete.md 8).
    """
    from quill.core.wordpress.workbench_across import scan_unread, unread_note

    missed = scan_unread(scan, kind)
    lines = [f"Not read on {scan.site}: {u}" for u in missed]
    return unread_note(scan.site, missed), lines


def outcome_report(outcomes: Sequence[Outcome]) -> tuple[str, str]:
    """A one-sentence summary and the full per-item report."""
    good = sum(1 for o in outcomes if o.ok)
    said = f"{good} of {len(outcomes)} changed."
    failed = [o for o in outcomes if not o.ok]
    if failed:
        said += f" {len(failed)} not: {failed[0].line}."
    lines = [("Done. " if o.ok else "Not done. ") + o.line for o in outcomes]
    return said, "\n".join(lines) or "Nothing to change."
