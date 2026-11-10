"""New Here, Merge Into, tags to categories, roles, password resets and spam (PRD 9, 11, 13a.5).

The W1 to W4 leftovers that change the site, as wx-free functions the
Workbench's mixin calls off the UI thread:

- **New Here** (Ctrl+N) for every creatable kind: :func:`creatable` says
  what the node makes and which fields to ask for, :func:`create` sends it
  (posts, pages and custom items as drafts, terms, menus).
- **Merge Into** (:func:`merge_preview`, :func:`merge_terms`): every item
  filed under one term is filed under the other, then the old term is
  deleted; the preview counts the items first.
- **Tag to category, and back** (:func:`convert_term`): the same move into
  a term of the other taxonomy, made (or found by name) first.
- **Roles, read only** (:func:`role_rows`): each default role's
  capabilities in plain words, with why the REST API cannot change them.
- **Send Password Reset** (:func:`password_reset_pointer`): WordPress has
  no REST route for it, so the Workbench opens the person's wp-admin screen,
  where Send Reset Link is one button, and says so.
- **Empty Spam** (:func:`spam_comments`, :func:`empty_spam`, tier 3) and
  **allow this sender** (:func:`allow_sender_words`).

Every request goes through the site's own client.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_permissions import ROLE_CAPABILITIES, ROLE_ORDER

__all__ = [
    "CAPABILITY_WORDS",
    "Creatable",
    "MergePreview",
    "allow_sender_words",
    "convert_term",
    "creatable",
    "create",
    "empty_spam",
    "merge_preview",
    "merge_terms",
    "password_reset_pointer",
    "role_rows",
    "spam_comments",
]


@dataclass(frozen=True)
class Creatable:
    """What New Here makes on one node: a family, its kind, and the fields asked for."""

    family: str  # "items", "terms" or "menus"
    kind: str  # the post type, the taxonomy, or "menu"
    noun: str  # "post", "category", "menu"
    fields: tuple[tuple[str, str, str], ...]  # (key, prompt, help)


_TITLE = ("title", "&Title:", "The title it starts with. It is saved as a draft.")
_NAME = ("name", "&Name:", "Its name, as the site shows it.")
_DESCRIPTION = ("description", "&Description (optional):", "A sentence about it, or nothing.")

_FIXED_CREATABLE: dict[str, Creatable] = {
    "posts": Creatable("items", "post", "post", (_TITLE,)),
    "pages": Creatable("items", "page", "page", (_TITLE,)),
    "categories": Creatable(
        "terms",
        "category",
        "category",
        (
            _NAME,
            ("parent", "&Parent number (optional):", "0 or empty for a top level."),
            _DESCRIPTION,
        ),
    ),
    "tags": Creatable("terms", "post_tag", "tag", (_NAME, _DESCRIPTION)),
    "menus": Creatable("menus", "menu", "menu", (_NAME,)),
}


def creatable(node_key: str, dynamic: str = "", *, dynamic_label: str = "") -> Creatable | None:
    """What New Here makes on *node_key* (None for a node it makes nothing on).

    *dynamic* is a dynamic node's post type or taxonomy; the custom nodes
    make items or terms of that kind.
    """
    base = node_key.split("_", 1)[0] if node_key.startswith(("posts_", "pages_")) else node_key
    if base in _FIXED_CREATABLE:
        return _FIXED_CREATABLE[base]
    noun = (dynamic_label or dynamic).rstrip("s").lower() or "item"
    if node_key == "custom_type" and dynamic:
        return Creatable("items", dynamic, noun, (_TITLE,))
    if node_key == "custom_taxonomy" and dynamic:
        return Creatable("terms", dynamic, noun, (_NAME, _DESCRIPTION))
    return None


def _info(api: WordPressApi, taxonomy: str) -> tx.TaxonomyInfo | None:
    found = tx.lookup(api, taxonomy)
    if found is None and taxonomy not in tx.CORE_TAXONOMY_BASES:
        found = tx.discover_taxonomies(api).get(taxonomy)
    return found


def _term_route(api: WordPressApi, taxonomy: str) -> str:
    found = _info(api, taxonomy)
    if found is not None:
        return found.route
    return f"wp/v2/{tx.CORE_TAXONOMY_BASES.get(taxonomy, taxonomy)}"


def create(api: WordPressApi, what: Creatable, answers: Mapping[str, str]) -> dict[str, Any]:
    """Send the new thing; the site's answer comes back."""
    if what.family == "items":
        body: dict[str, Any] = {"title": answers.get("title", ""), "status": "draft"}
        raw = api.post(kind_route(what.kind), body, context="edit")
    elif what.family == "terms":
        body = {"name": answers.get("name", "")}
        if answers.get("description"):
            body["description"] = answers["description"]
        parent = str(answers.get("parent", "") or "").strip()
        if parent.isdigit() and int(parent):
            body["parent"] = int(parent)
        raw = api.post(_term_route(api, what.kind), body)
    elif what.family == "menus":
        raw = api.post("wp/v2/menus", {"name": answers.get("name", "")})
    else:  # pragma: no cover - creatable() names only these three
        raise ValueError(what.family)
    return dict(raw) if isinstance(raw, dict) else {}


# -- terms ---------------------------------------------------------------------


@dataclass(frozen=True)
class MergePreview:
    """What Merge Into (or a conversion) would move."""

    source: str
    target: str
    items: tuple[tuple[str, int], ...]  # (post type route, id)

    @property
    def sentence(self) -> str:
        count = len(self.items)
        noun = "item" if count == 1 else "items"
        return (
            f"{count} {noun} filed under {self.source} will be filed under {self.target}, "
            f"then {self.source} is deleted. This cannot be undone with Ctrl+Z."
        )


def _types_using(api: WordPressApi, taxonomy: str) -> list[tuple[str, str]]:
    """(rest_base of the taxonomy, item route) for every post type the taxonomy is on."""
    info = _info(api, taxonomy)
    if info is None:
        base = tx.CORE_TAXONOMY_BASES.get(taxonomy, taxonomy)
        return [(base, kind_route("post"))]
    return [(info.rest_base, kind_route(kind)) for kind in (info.types or ("post",))]


def merge_preview(
    api: WordPressApi,
    taxonomy: str,
    source: tuple[int, str],
    target: tuple[int, str],
) -> MergePreview:
    """Every item filed under *source* ((id, name)), by its post type's route."""
    items: list[tuple[str, int]] = []
    for base, route in _types_using(api, taxonomy):
        for raw in api.iter_collection(
            route, {base: source[0], "status": "any", "_fields": "id"}, per_page=100
        ):
            items.append((route, int(raw.get("id", 0) or 0)))
    return MergePreview(source[1], target[1], tuple(items))


def _move(
    api: WordPressApi,
    from_base: str,
    to_base: str,
    source_id: int,
    target_id: int,
    items: Sequence[tuple[str, int]],
) -> list[int]:
    failed: list[int] = []
    for route, item_id in items:
        got = api.get(f"{route}/{item_id}", context="edit", _fields=f"id,{from_base},{to_base}")
        if not isinstance(got, dict):
            failed.append(item_id)
            continue
        old = [int(i) for i in got.get(from_base) or [] if int(i) != source_id]
        body: dict[str, Any] = {from_base: old}
        new = [int(i) for i in got.get(to_base) or []] if to_base != from_base else old
        if target_id not in new:
            new.append(target_id)
        body[to_base] = new
        try:
            api.post(f"{route}/{item_id}", body)
        except Exception:  # noqa: BLE001 - one item failing must not stop the rest
            failed.append(item_id)
    return failed


def merge_terms(
    api: WordPressApi, taxonomy: str, source_id: int, target_id: int, preview: MergePreview
) -> list[int]:
    """File every previewed item under *target_id*, then delete *source_id*.

    Returns the ids of items that could not be moved; the old term is kept
    when any failed, so nothing is left filed under nothing.
    """
    base = _types_using(api, taxonomy)[0][0]
    failed = _move(api, base, base, source_id, target_id, preview.items)
    if not failed:
        api.delete(f"{_term_route(api, taxonomy)}/{source_id}", force=True)
    return failed


def convert_term(
    api: WordPressApi, raw: Mapping[str, Any], from_taxonomy: str, to_taxonomy: str
) -> tuple[int, list[int]]:
    """A tag into a category (or back): the new term made or found by name, items moved.

    Returns the new term's id and the items that could not be moved.
    """
    name = str(raw.get("name", "") or "")
    source_id = int(raw.get("id", 0) or 0)
    to_route = _term_route(api, to_taxonomy)
    found = api.get(to_route, search=name, _fields="id,name")
    match = next(
        (t for t in found or [] if str(t.get("name", "")).casefold() == name.casefold()), None
    )
    if match is not None:
        target_id = int(match.get("id", 0) or 0)
    else:
        body = {"name": name, "slug": str(raw.get("slug", "") or "")}
        if raw.get("description"):
            body["description"] = str(raw["description"])
        made = api.post(to_route, body)
        target_id = int(made.get("id", 0) or 0) if isinstance(made, dict) else 0
    preview = merge_preview(api, from_taxonomy, (source_id, name), (target_id, name))
    from_base = _types_using(api, from_taxonomy)[0][0]
    to_base = _types_using(api, to_taxonomy)[0][0]
    failed = _move(api, from_base, to_base, source_id, target_id, preview.items)
    if not failed:
        api.delete(f"{_term_route(api, from_taxonomy)}/{source_id}", force=True)
    return target_id, failed


# -- people --------------------------------------------------------------------

CAPABILITY_WORDS: Mapping[str, str] = {
    "read": "read the site while signed in",
    "edit_posts": "write posts",
    "delete_posts": "delete their own unpublished posts",
    "upload_files": "upload pictures and files",
    "publish_posts": "publish their own posts",
    "edit_published_posts": "change their own published posts",
    "delete_published_posts": "delete their own published posts",
    "moderate_comments": "moderate comments",
    "manage_categories": "manage categories and tags",
    "edit_others_posts": "change other people's posts",
    "edit_pages": "write pages",
    "publish_pages": "publish pages",
    "unfiltered_html": "write any HTML, scripts included",
    "switch_themes": "change the theme",
    "activate_plugins": "turn plugins on and off",
    "install_plugins": "install plugins",
    "update_plugins": "update plugins",
    "list_users": "see the people on the site",
    "create_users": "add people",
    "promote_users": "change people's roles",
    "delete_users": "remove people",
    "manage_options": "change the site's settings",
    "edit_theme_options": "change menus, widgets and the theme's options",
    "update_core": "update WordPress itself",
    "export": "export the site",
    "import": "import into the site",
}

_ROLE_WORDS = {
    "subscriber": "Subscriber",
    "contributor": "Contributor",
    "author": "Author",
    "editor": "Editor",
    "administrator": "Administrator",
}


def role_rows() -> list[tuple[str, str]]:
    """Each default role and, in plain words, what it may do beyond the role below it."""
    rows: list[tuple[str, str]] = []
    below: frozenset[str] = frozenset()
    for role in ROLE_ORDER:
        caps = ROLE_CAPABILITIES[role]
        added = sorted(caps - below)
        words = [CAPABILITY_WORDS[c] for c in added if c in CAPABILITY_WORDS]
        others = len(added) - len(words)
        said = ", ".join(words) or "nothing more"
        if others:
            said += f", and {others} more"
        lead = "Can" if role == "subscriber" else "Everything above, and can"
        rows.append((_ROLE_WORDS[role], f"{lead} {said}."))
        below = caps
    return rows


ROLES_CANNOT_CHANGE = (
    "WordPress's REST API reads roles but cannot change what a role may do. A role "
    "plugin such as Members or User Role Editor does that in wp-admin."
)


def password_reset_pointer(site_url: str, user_id: int, name: str) -> tuple[str, str]:
    """(the wp-admin address, the sentence) for sending *name* a password reset."""
    address = f"{site_url.rstrip('/')}/wp-admin/user-edit.php?user_id={int(user_id)}"
    sentence = (
        f"WordPress has no REST route for a password reset, so the Workbench opens "
        f"{name}'s screen in wp-admin, where Send Reset Link sends them the email."
    )
    return address, sentence


# -- spam ----------------------------------------------------------------------


def spam_comments(api: WordPressApi, *, max_pages: int = 100) -> list[int]:
    """The ids of every comment held as spam."""
    return [
        int(raw.get("id", 0) or 0)
        for raw in api.iter_collection(
            "wp/v2/comments", {"status": "spam", "_fields": "id"}, per_page=100, max_pages=max_pages
        )
    ]


def empty_spam(api: WordPressApi, ids: Sequence[int]) -> list[int]:
    """Delete every comment in *ids* permanently (tier 3); the ids that failed come back."""
    failed: list[int] = []
    for comment_id in ids:
        try:
            api.delete(f"wp/v2/comments/{comment_id}", force=True)
        except Exception:  # noqa: BLE001 - one failure must not stop the rest
            failed.append(comment_id)
    return failed


def allow_sender_words(author: str, settings: Mapping[str, Any]) -> str:
    """What allowing *author* from now on means on this site, from its discussion settings."""
    previously = settings.get("comment_previously_approved")
    if previously is False:
        return (
            f"{author}'s comment is approved. This site holds every comment for "
            "moderation, so their next one will wait too; Settings > Discussion in "
            "wp-admin changes that."
        )
    return (
        f"{author}'s comment is approved, so WordPress lets their next comments "
        "through: it allows anyone with an approved comment already. To block them "
        "again, mark a comment of theirs as spam."
    )
