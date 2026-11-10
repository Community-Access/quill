"""Bulk Edit, synced patterns, fonts, and the categories-and-tags extras (wordpress.md 9.13).

Wx-free; every request goes through ``WordPressApi``. Anything that changes
many items at once is one ``batch/v1`` request and returns a record of what
it changed, so the window can offer Undo.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import (
    Term,
    create_term,
    delete_term,
    kind_route,
    list_terms,
    raw_text,
    rendered,
    taxonomy_route,
)

# --------------------------------------------------------------------------- #
# Bulk Edit (9.13)

#: What Bulk Edit can change: (field, what a person calls it, which kinds).
BULK_FIELDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("status", "Status", ("post", "page")),
    ("author", "Author", ("post", "page")),
    ("categories", "Add a category", ("post",)),
    ("tags", "Add a tag", ("post",)),
    ("comment_status", "Comments", ("post", "page")),
    ("parent", "Parent page", ("page",)),
)

BULK_STATUSES = (
    ("publish", "Published"),
    ("draft", "Draft"),
    ("pending", "Pending review"),
    ("private", "Private"),
)


def bulk_fields(kind: str) -> list[tuple[str, str]]:
    return [(f, label) for f, label, kinds in BULK_FIELDS if kind in kinds]


def current_values(api: WordPressApi, kind: str, ids: list[int], field: str) -> dict[int, Any]:
    params: dict[str, object] = {
        "include": ids,
        "status": "any",
        "context": "edit",
        "_fields": f"id,{field}",
    }
    return {
        int(r.get("id", 0)): r.get(field) for r in api.iter_collection(kind_route(kind), params)
    }


def bulk_edit(
    api: WordPressApi, *, site_id: str, kind: str, ids: list[int], field: str, value: Any
) -> dict[str, Any]:
    """Change *field* on every item in one batch; return the record Undo needs.

    For categories and tags *value* is one term id, added to what each item
    already has; for everything else it replaces the field.
    """
    before = current_values(api, kind, ids, field)
    requests: list[dict[str, Any]] = []
    for item_id in ids:
        new: Any = value
        if field in {"categories", "tags"}:
            had = [int(x) for x in before.get(item_id) or []]
            new = sorted({*had, int(value)})
        requests.append({
            "method": "POST",
            "path": f"/{kind_route(kind)}/{item_id}",
            "body": {field: new},
        })
    api.batch(requests)
    return {
        "site_id": site_id,
        "kind": kind,
        "field": field,
        "before": {str(k): v for k, v in before.items()},
    }


def undo_bulk_edit(api: WordPressApi, record: dict[str, Any]) -> int:
    kind = str(record.get("kind", "post"))
    field = str(record.get("field", ""))
    before = record.get("before", {}) or {}
    if not field or not before:
        return 0
    api.batch([
        {"method": "POST", "path": f"/{kind_route(kind)}/{int(i)}", "body": {field: v}}
        for i, v in before.items()
    ])
    return len(before)


# --------------------------------------------------------------------------- #
# Synced patterns (9.13)


@dataclass(frozen=True)
class Pattern:
    id: int
    title: str
    synced: bool
    content: str

    def spoken(self, uses: int) -> str:
        kind = "synced" if self.synced else "not synced"
        where = f"used in {uses} {'place' if uses == 1 else 'places'}" if uses else "not used"
        return f"{self.title or '(untitled)'}, {kind}, {where}"


def list_patterns(api: WordPressApi) -> list[Pattern]:
    params: dict[str, object] = {"context": "edit", "status": "publish"}
    return [
        Pattern(
            id=int(r.get("id", 0)),
            title=raw_text(r.get("title")),
            synced=str(r.get("wp_pattern_sync_status", "") or "") != "unsynced",
            content=raw_text(r.get("content")),
        )
        for r in api.iter_collection("wp/v2/blocks", params)
    ]


_REF = re.compile(r'<!--\s+wp:block\s+\{[^}]*"ref":(\d+)[^}]*\}\s+/-->')


@dataclass(frozen=True)
class Use:
    kind: str
    id: int
    title: str
    content: str


def pattern_uses(api: WordPressApi) -> dict[int, list[Use]]:
    """Which pages and posts use each synced pattern, by reading their content."""
    uses: dict[int, list[Use]] = {}
    for kind in ("page", "post"):
        params: dict[str, object] = {
            "context": "edit",
            "status": "any",
            "_fields": "id,title,content",
        }
        for r in api.iter_collection(kind_route(kind), params):
            content = raw_text(r.get("content"))
            for ref in {int(m) for m in _REF.findall(content)}:
                uses.setdefault(ref, []).append(
                    Use(
                        kind, int(r.get("id", 0)), rendered(r.get("title")) or "(untitled)", content
                    )
                )
    return uses


def rename_pattern(api: WordPressApi, pattern_id: int, title: str) -> None:
    api.post(f"wp/v2/blocks/{pattern_id}", {"title": title})


def save_pattern_content(api: WordPressApi, pattern_id: int, content: str) -> None:
    api.post(f"wp/v2/blocks/{pattern_id}", {"content": content})


def create_pattern(api: WordPressApi, title: str, content: str, *, synced: bool = True) -> Pattern:
    body = {
        "title": title,
        "content": content,
        "status": "publish",
        "wp_pattern_sync_status": "" if synced else "unsynced",
    }
    raw = api.post("wp/v2/blocks", body, context="edit")
    return Pattern(int(raw.get("id", 0)) if isinstance(raw, dict) else 0, title, synced, content)


def unsync_pattern(api: WordPressApi, pattern: Pattern, uses: list[Use]) -> int:
    """Turn each use into ordinary blocks, then mark the pattern not synced.

    Nothing on the site goes missing: every page shows what it showed before.
    """
    requests: list[dict[str, Any]] = []
    for use in uses:
        replaced = re.sub(
            r'<!--\s+wp:block\s+\{[^}]*"ref":' + str(pattern.id) + r"\b[^}]*\}\s+/-->",
            lambda _m: pattern.content,
            use.content,
        )
        requests.append({
            "method": "POST",
            "path": f"/{kind_route(use.kind)}/{use.id}",
            "body": {"content": replaced},
        })
    if requests:
        api.batch(requests)
    api.post(f"wp/v2/blocks/{pattern.id}", {"wp_pattern_sync_status": "unsynced"})
    return len(requests)


def delete_pattern(api: WordPressApi, pattern_id: int) -> None:
    api.delete(f"wp/v2/blocks/{pattern_id}")


# --------------------------------------------------------------------------- #
# Fonts (9.13; WordPress 6.5+)


@dataclass(frozen=True)
class Font:
    id: int
    name: str
    slug: str
    family: str
    faces: int

    def spoken(self) -> str:
        return f"{self.name}, {describe_font(self.family)}, {self.faces} faces"


@dataclass(frozen=True)
class FontChoice:
    collection: str
    name: str
    slug: str
    family: str
    categories: tuple[str, ...]
    settings: dict[str, Any]

    def spoken(self) -> str:
        return f"{self.name}, {describe_font(self.family, self.categories)}, from {self.collection}"


def describe_font(family: str, categories: tuple[str, ...] = ()) -> str:
    """Plain words: serif or sans serif, and what it suits."""
    text = (family + " " + " ".join(categories)).lower()
    if "monospace" in text:
        return "monospace, suits code"
    if "handwriting" in text or "cursive" in text:
        return "handwriting, suits short headings only"
    if "display" in text:
        return "display, suits headings"
    if "sans-serif" in text or "sans serif" in text:
        return "sans serif, suits body text and headings"
    if "serif" in text:
        return "serif, suits body text"
    return "style not stated"


def list_fonts(api: WordPressApi) -> list[Font]:
    params: dict[str, object] = {"context": "edit"}
    fonts: list[Font] = []
    for r in api.iter_collection("wp/v2/font-families", params):
        settings = r.get("font_family_settings", {}) or {}
        fonts.append(
            Font(
                id=int(r.get("id", 0)),
                name=str(settings.get("name", "")),
                slug=str(settings.get("slug", "")),
                family=str(settings.get("fontFamily", "")),
                faces=len(r.get("font_faces", []) or []),
            )
        )
    return fonts


def list_font_choices(api: WordPressApi) -> list[FontChoice]:
    raw = api.get("wp/v2/font-collections")
    choices: list[FontChoice] = []
    for collection in raw if isinstance(raw, list) else []:
        if not isinstance(collection, dict):
            continue
        name = str(collection.get("name", ""))
        for fam in collection.get("font_families", []) or []:
            settings = fam.get("font_family_settings", {}) if isinstance(fam, dict) else {}
            if not isinstance(settings, dict):
                continue
            choices.append(
                FontChoice(
                    collection=name,
                    name=str(settings.get("name", "")),
                    slug=str(settings.get("slug", "")),
                    family=str(settings.get("fontFamily", "")),
                    categories=tuple(str(c) for c in fam.get("categories", []) or []),
                    settings=settings,
                )
            )
    return choices


def install_font(api: WordPressApi, choice: FontChoice) -> Font:
    """The family, then each of its faces, from the collection's own files."""
    family_settings = {k: v for k, v in choice.settings.items() if k != "fontFace"}
    raw = api.post("wp/v2/font-families", {"font_family_settings": json.dumps(family_settings)})
    family_id = int(raw.get("id", 0)) if isinstance(raw, dict) else 0
    faces = [f for f in choice.settings.get("fontFace", []) or [] if isinstance(f, dict)]
    for face in faces:
        api.post(
            f"wp/v2/font-families/{family_id}/font-faces",
            {"font_face_settings": json.dumps(face)},
        )
    return Font(family_id, choice.name, choice.slug, choice.family, len(faces))


def delete_font(api: WordPressApi, font_id: int) -> None:
    api.delete(f"wp/v2/font-families/{font_id}", force=True)


# --------------------------------------------------------------------------- #
# Categories and tags: Convert, Find Unused, Default Category (9.13)


def other_taxonomy(taxonomy: str) -> str:
    return "post_tag" if taxonomy == "category" else "category"


def _field(taxonomy: str) -> str:
    return "categories" if taxonomy == "category" else "tags"


def convert_term(api: WordPressApi, term: Term) -> tuple[Term, int]:
    """Category to tag, or tag to category: same name, same posts, old one deleted.

    Reuses a term of that name when the other side already has one. Returns
    the new term and how many posts moved.
    """
    target_tax = other_taxonomy(term.taxonomy)
    existing = [t for t in list_terms(api, target_tax, search=term.name) if t.name == term.name]
    if existing:
        new = existing[0]
    else:
        try:
            new = create_term(api, target_tax, term.name, description=term.description)
        except WordPressApiError as exc:
            if exc.wp_code != "term_exists":
                raise
            new = next(t for t in list_terms(api, target_tax) if t.name == term.name)
    old_field, new_field = _field(term.taxonomy), _field(target_tax)
    requests: list[dict[str, Any]] = []
    params: dict[str, object] = {
        "context": "edit",
        "status": "any",
        old_field: term.id,
        "_fields": f"id,{old_field},{new_field}",
    }
    for raw in api.iter_collection("wp/v2/posts", params):
        old_ids = [int(x) for x in raw.get(old_field, []) or [] if int(x) != term.id]
        new_ids = sorted({*(int(x) for x in raw.get(new_field, []) or []), new.id})
        requests.append({
            "method": "POST",
            "path": f"/wp/v2/posts/{int(raw['id'])}",
            "body": {old_field: old_ids, new_field: new_ids},
        })
    if requests:
        api.batch(requests)
    delete_term(api, term.taxonomy, term.id)
    return new, len(requests)


def unused(terms: list[Term], *, keep: int = 0) -> list[Term]:
    """Terms no post uses, except *keep* (the default category, which cannot go)."""
    return [t for t in terms if t.count == 0 and t.id != keep]


def delete_terms(api: WordPressApi, terms: list[Term]) -> int:
    if not terms:
        return 0
    api.batch([
        {
            "method": "DELETE",
            "path": f"/{taxonomy_route(t.taxonomy, api)}/{t.id}?force=true",
        }
        for t in terms
    ])
    return len(terms)


def default_category(api: WordPressApi) -> int:
    raw = api.get("wp/v2/settings")
    return int(raw.get("default_category", 0) or 0) if isinstance(raw, dict) else 0


def set_default_category(api: WordPressApi, term_id: int) -> None:
    api.post("wp/v2/settings", {"default_category": term_id})
