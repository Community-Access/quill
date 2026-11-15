"""wp-admin parity for Posts, Pages and Media in the Workbench (wordpress.md 9.18, packages 1 to 3).

What the three wp-admin list screens and the editor's sidebar do that the
Workbench did not, built on the routes WordPress offers:

- **Counts by status** (Posts and Pages: All, Mine, Published, Drafts,
  Pending, Scheduled, Private, Trash; Media: All, Mine, Pictures, Audio,
  Video, Documents, Unattached), one ``per_page=1`` request each, read from
  ``X-WP-Total``. A view the site refuses this account is left out rather
  than said as none.
- **Per-item outcomes** for Trash, Restore and Delete Permanently on many
  rows (:func:`each`): one refusal no longer stops the rest, and the sentence
  names what was not done and why (:func:`outcome`).
- **Duplicate as Draft** on the same site (the editor's Duplicate, reused).
- **Author and Template as choices** in Properties (:func:`with_choices`):
  authors from ``wp/v2/users?who=authors``, templates from the route's own
  ``template`` enum or ``wp/v2/templates``. "Default template" is said in
  words and sent as the empty string WordPress reads (:func:`clean_body`).
- **Media:** crop by numbers in percent (:func:`parse_crop`, read back by
  :func:`crop_words`), the site's own rotate and flip, Regenerate Sizes,
  attach and detach, and Download.
- **What REST cannot do** opens the exact wp-admin screen
  (:func:`dashboard_screen`): the post lock and the original's Scale.

Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route, rendered
from quill.core.wordpress.workbench_edit import BatchResult, EditRefused
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import labelled
from quill.core.workbench.properties import FieldKind, PageSpec, SheetSpec

__all__ = [
    "DEFAULT_TEMPLATE",
    "DOWNLOAD_CAP",
    "ITEM_VIEWS",
    "MEDIA_VIEWS",
    "author_choices",
    "clean_body",
    "count",
    "counts_text",
    "crop_words",
    "dashboard_screen",
    "duplicate",
    "each",
    "NO_PICTURE",
    "edit_picture",
    "featured_value",
    "media_title",
    "picture_row",
    "with_featured",
    "outcome",
    "parse_crop",
    "picture_choices",
    "status_counts",
    "template_choices",
    "trash_rows",
    "with_choices",
]

DEFAULT_TEMPLATE = "Default template"
"""The word Properties shows for an item using its theme's default template (sent as "")."""

DOWNLOAD_CAP = 512 * 1024 * 1024
"""The biggest file Download saves; a larger one is opened in the browser instead."""

#: wp-admin's status views on Posts and Pages: the label and the query each one is.
ITEM_VIEWS: tuple[tuple[str, Mapping[str, object]], ...] = (
    ("All", {"status": "any"}),
    ("Mine", {"status": "any", "author": "me"}),
    ("Published", {"status": "publish"}),
    ("Drafts", {"status": "draft"}),
    ("Pending", {"status": "pending"}),
    ("Scheduled", {"status": "future"}),
    ("Private", {"status": "private"}),
    ("Trash", {"status": "trash"}),
)

#: The Media Library's type filter, and Mine and Unattached.
MEDIA_VIEWS: tuple[tuple[str, Mapping[str, object]], ...] = (
    ("All", {}),
    ("Mine", {"author": "me"}),
    ("Pictures", {"media_type": "image"}),
    ("Audio", {"media_type": "audio"}),
    ("Video", {"media_type": "video"}),
    ("Documents", {"media_type": "application"}),
    ("Unattached", {"parent": 0}),
)


# -- counts -----------------------------------------------------------------------


def count(api: WordPressApi, route: str, params: Mapping[str, object]) -> int | None:
    """How many *route* holds for *params*, from ``X-WP-Total`` (None when refused)."""
    query = {"context": "edit", **params, "per_page": 1, "_fields": "id"}
    try:
        response = api.request("GET", route, params=query)
    except WordPressApiError:
        return None
    total = getattr(response, "total", None)
    if total is None:
        payload = getattr(response, "payload", None)
        total = len(payload) if isinstance(payload, list) else 0
    return int(total)


def status_counts(
    api: WordPressApi, route: str, me: int, views: Sequence[tuple[str, Mapping[str, object]]]
) -> list[tuple[str, int]]:
    """Each view's count; "me" in a view's author is the signed-in person's id."""
    found: list[tuple[str, int]] = []
    for label, params in views:
        if params.get("author") == "me":
            if not me:
                continue
            params = {**params, "author": me}
        total = count(api, route, params)
        if total is not None:
            found.append((label, total))
    return found


def counts_text(what: str, site: str, counts: Sequence[tuple[str, int]]) -> str:
    """ "Posts on Community Radio: All 12, Mine 3, Published 8, ..."."""
    if not counts:
        return f"{site} would not count its {what.lower()} for this account."
    return f"{what} on {site}: " + ", ".join(f"{label} {n}" for label, n in counts) + "."


# -- many rows, one outcome each ---------------------------------------------------


def each(
    rows: Sequence[WbRow], act: Callable[[WbRow], object], done_word: str
) -> list[BatchResult]:
    """Run *act* on every row; a refusal is that row's outcome, never the end of the rest."""
    results: list[BatchResult] = []
    for row in rows:
        try:
            act(row)
        except WordPressApiError as exc:
            results.append(BatchResult(row, False, f"{row.title}: {exc.plain}"))
            continue
        except CodedError as exc:
            results.append(
                BatchResult(row, False, f"{row.title}: {exc.args[0] if exc.args else exc}")
            )
            continue
        results.append(BatchResult(row, True, f"{row.title}: {done_word}"))
    return results


def outcome(results: Sequence[BatchResult], did: str, site: str) -> str:
    """ "Moved 3 of 4 items to the Trash on X. Not done: Hello: not allowed."."""
    good = sum(1 for r in results if r.ok)
    total = len(results)
    noun = "item" if total == 1 else "items"
    amount = f"{good} of {total} {noun}" if good != total else f"{total} {noun}"
    said = did.replace("{n}", amount) + f" on {site}."
    failed = [r.sentence for r in results if not r.ok]
    if failed:
        said += " Not done: " + "; ".join(failed[:3])
        if len(failed) > 3:
            said += f"; and {len(failed) - 3} more"
        said += "."
    return said


def trash_rows(api: WordPressApi, kind: str, site: str) -> list[WbRow]:
    """Every item of *kind* in the Trash, for Empty Trash (one row each, no body)."""
    from quill.core.wordpress.workbench_rows import item_row

    params = {"context": "edit", "status": "trash", "_fields": "id,title,status,type"}
    return [item_row(raw, kind, site) for raw in api.iter_collection(kind_route(kind), params)]


# -- Duplicate -----------------------------------------------------------------------


def duplicate(api: WordPressApi, row: WbRow) -> Any:
    """A new draft copy of *row* on its own site (the editor's Duplicate); returns the Item."""
    from quill.core.wordpress import cross_site as xs
    from quill.core.wordpress import site as wp

    item = wp.load_item(api, row.subkind, int(row.key))
    return wp.create_item(api, xs.as_new_draft(item, same_site=True))


# -- Properties: author and template as choices ----------------------------------------


def author_choices(api: WordPressApi) -> tuple[str, ...]:
    """Everyone who can write, as "Name (id)"; empty when the site will not list them."""
    try:
        people = api.get("wp/v2/users", who="authors", per_page=100, _fields="id,name")
    except WordPressApiError:
        return ()
    if not isinstance(people, list):
        return ()
    return tuple(
        labelled(str(p.get("name", "")), int(p.get("id", 0) or 0))
        for p in people
        if isinstance(p, dict) and p.get("id")
    )


def template_choices(api: WordPressApi, kind: str) -> tuple[str, ...]:
    """The templates *kind* may use: the route's ``template`` enum, else ``wp/v2/templates``."""
    from quill.core.wordpress.field_plugins import route_properties

    try:
        props = route_properties(api, kind_route(kind))
    except Exception:  # noqa: BLE001 - a route without OPTIONS falls back to the templates list
        props = {}
    spec = props.get("template") if isinstance(props, Mapping) else None
    enum = spec.get("enum") if isinstance(spec, Mapping) else None
    if isinstance(enum, list) and [e for e in enum if e]:
        return tuple(str(e) for e in enum if e)
    try:
        found = api.get("wp/v2/templates", post_type=kind, _fields="slug")
    except WordPressApiError:
        return ()
    if not isinstance(found, list):
        return ()
    return tuple(str(t.get("slug", "")) for t in found if isinstance(t, dict) and t.get("slug"))


def with_choices(
    sheet: SheetSpec,
    values: dict[str, Any],
    *,
    authors: Sequence[str] = (),
    templates: Sequence[str] = (),
) -> SheetSpec:
    """*sheet* with Author and Template as choices; *values* says the default template in words.

    Author becomes a choice only when the item has one, so an empty value is
    never silently replaced by the first name in the list.
    """
    if templates and "template" in values:
        values["template"] = str(values.get("template") or "") or DEFAULT_TEMPLATE
    pages: list[PageSpec] = []
    for page in sheet.pages:
        fields = []
        for spec in page.fields:
            if spec.key == "author" and authors and values.get("author"):
                spec = replace(
                    spec,
                    kind=FieldKind.CHOICE,
                    choices=tuple(authors),
                    help="Who it is by. Changing another person's needs the Editor role.",
                )
            elif spec.key == "template" and templates:
                spec = replace(
                    spec,
                    kind=FieldKind.CHOICE,
                    choices=(DEFAULT_TEMPLATE, *templates),
                    help="The theme template it uses; Default template is the theme's own.",
                )
            fields.append(spec)
        pages.append(replace(page, fields=tuple(fields)))
    return replace(sheet, pages=tuple(pages))


NO_PICTURE = "No featured image (0)"
"""What the featured image field holds once Remove Featured Image is pressed (sent as 0)."""


def with_featured(sheet: SheetSpec) -> SheetSpec:
    """*sheet* with its featured image field named for what it holds: a picture by title."""
    pages: list[PageSpec] = []
    for page in sheet.pages:
        fields = tuple(
            replace(
                spec,
                label="Featured image",
                kind=FieldKind.TEXT,
                help=(
                    "The picture shown with it, by title and number, such as Sky (9). "
                    "Choose from Library lists the site's pictures with their alt text; "
                    "Remove Featured Image clears it."
                ),
            )
            if spec.key == "featured_media"
            else spec
            for spec in page.fields
        )
        pages.append(replace(page, fields=fields))
    return replace(sheet, pages=tuple(pages))


def featured_value(api: WordPressApi, ident: object) -> str:
    """ "Sky (9)" for picture 9, "" for none; just the number when the site will not say."""
    number = int(str(ident or 0) or 0) if str(ident or "").isdigit() else 0
    if not number:
        return ""
    try:
        raw = api.get(f"wp/v2/media/{number}", _fields="id,title,slug")
    except WordPressApiError:
        return str(number)
    return labelled(media_title(raw) if isinstance(raw, dict) else "", number)


def picture_row(row: WbRow) -> str:
    """One picture in Choose from Library: its title, then its alt text or that it has none."""
    alt = str(row.raw.get("alt_text", "") or "").strip()
    return f"{row.title}, alt text: {alt}" if alt else f"{row.title}, no alt text"


def clean_body(body: dict[str, Any]) -> dict[str, Any]:
    """Default template, said in words on the sheet, goes back as WordPress's empty string."""
    if body.get("template") == DEFAULT_TEMPLATE:
        body["template"] = ""
    return body


# -- Media: crop by numbers, rotate and flip -------------------------------------------

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def parse_crop(text: str) -> dict[str, float]:
    """ "10, 0, 80, 100" (left, top, width, height in percent) as the crop modifier's args."""
    numbers = [float(n) for n in _NUMBER.findall(text or "")]
    if len(numbers) != 4:
        raise EditRefused(
            "Give four numbers in percent: from the left, from the top, width and height, "
            "such as 10, 0, 80, 100."
        )
    left, top, width, height = numbers
    if min(numbers) < 0 or width <= 0 or height <= 0:
        raise EditRefused("Width and height must be more than 0, and nothing below 0.")
    if left + width > 100 or top + height > 100:
        raise EditRefused(
            "The crop goes past the picture's edge: left plus width, and top "
            "plus height, may be at most 100."
        )
    return {"left": left, "top": top, "width": width, "height": height}


def _pc(value: float) -> str:
    return f"{value:g} percent"


def crop_words(box: Mapping[str, float]) -> str:
    """The crop read back in words, so a number typed wrong is heard before it is sent."""
    return (
        f"keeps {_pc(box['width'])} of the width, starting {_pc(box['left'])} from the left, "
        f"and {_pc(box['height'])} of the height, starting {_pc(box['top'])} from the top"
    )


def picture_choices(modifiers: Sequence[str], width: int, height: int) -> list[tuple[str, Any]]:
    """The edits this site takes, as (label, modifiers); "crop" rows need the picture's size."""
    from quill.core.wordpress import media_edit as me

    allowed = set(modifiers)
    rows: list[tuple[str, Any]] = []
    for edit in me.EDITS:
        if edit.needs not in allowed or (edit.needs == "crop" and not (width and height)):
            continue
        rows.append((edit.label, edit.modifiers(width, height)))
    return rows


def edit_picture(api: WordPressApi, row: WbRow, modifiers: Sequence[Mapping[str, Any]]) -> Any:
    """``POST media/{id}/edit``: WordPress keeps the original and returns the new item."""
    source = str(row.raw.get("source_url", "") or row.link)
    return api.post(
        f"wp/v2/media/{row.key}/edit",
        {"src": source, "modifiers": [dict(m) for m in modifiers]},
        context="edit",
    )


def media_title(raw: Mapping[str, Any]) -> str:
    return rendered(raw.get("title")) or str(raw.get("slug", "") or raw.get("id", ""))


# -- what REST cannot do --------------------------------------------------------------

_DASHBOARD_WHY = {
    "item": (
        "wp-admin's editor for it, which shows who is editing it now and takes over the "
        "lock; WordPress's REST API does not expose the edit lock."
    ),
    "media": (
        "wp-admin's Edit Media screen, whose Edit Image scales the original to a width and "
        "height; WordPress's REST edit route only rotates, flips and crops."
    ),
}


def dashboard_screen(site_url: str, row: WbRow) -> tuple[str, str]:
    """(address, why) of the wp-admin screen for *row*; ("", why) when there is none."""
    why = _DASHBOARD_WHY.get(row.kind, "")
    base = (site_url or "").rstrip("/")
    if not why or not base or not row.key.isdigit():
        return "", why
    return f"{base}/wp-admin/post.php?post={row.key}&action=edit", why
