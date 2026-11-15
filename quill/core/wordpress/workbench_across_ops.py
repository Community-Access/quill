"""Across Sites operations: Make Them the Same, menus, patterns, styles, the network (15.12).

:mod:`quill.core.wordpress.workbench_across` gathers a kind by name over the
scope and says where the copies differ. This module does the work:

- :func:`gather_more` adds two kinds to Across Sites: **menus** (wp/v2/menus,
  each menu by name with its items) and **patterns** (synced patterns,
  wp/v2/blocks, by title);
- :func:`make_same_edits` turns "make them the same" into
  :class:`~quill.core.wordpress.workbench_by_name.Edit` objects, one per site
  that differs, each with what it was before (so undo can put it back) and a
  conflict stamp: terms (name, slug, description; made where missing),
  plugins (active or inactive), settings, **people** (their role), and
  patterns (their content). A site the operation cannot reach is a
  per-site :class:`Outcome` saying why, never a silent skip;
- **themes**: WordPress's REST API reads themes and cannot activate one, so
  :func:`theme_screens` names each site's wp-admin Themes screen instead;
- **menus**: :func:`menu_copy` replaces a menu's items with the winner's,
  as links rewritten to the target site's address. Item ids change, so a
  menu copy is said to be final rather than offered as undoable;
- :func:`compare_styles` reads each site's global styles (the active block
  theme's palette and font sizes, the site's own where it set them) and says
  what differs;
- :func:`network_status` and :func:`network_refusal`: Promote to Network is
  offered only where the site's own plugin schema has ``network-active``,
  which WordPress publishes only on a multisite network, and WordPress then
  checks the super-admin right itself; a refusal is said per site.

Wx-free; every request goes through the site's own client, off the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered
from quill.core.wordpress.workbench_by_name import Edit, Outcome

__all__ = [
    "MAKE_SAME_KINDS",
    "compare_styles",
    "gather_more",
    "make_same_edits",
    "menu_copy",
    "network_refusal",
    "network_status",
    "rehost",
    "revoke_plan",
    "run_edits_by_site",
    "site_styles",
    "theme_screens",
]

MAKE_SAME_KINDS = ("terms", "plugins", "settings", "users", "patterns", "themes", "menus")
"""The Across Sites kinds Make Them the Same works on."""


def _all(
    api: WordPressApi,
    route: str,
    params: Mapping[str, object],
    unread: list[str] | None = None,
) -> list[Any]:
    try:
        return list(api.iter_collection(route, params, per_page=100, max_pages=5))
    except WordPressApiError as exc:
        if unread is not None:
            unread.append(f"{route}: {exc.plain or exc}")
        return []


def _title(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("title")) or rendered(raw.get("title"))


def _menu_items(
    api: WordPressApi, menu_id: int, unread: list[str] | None = None
) -> list[dict[str, Any]]:
    items = []
    for raw in _all(api, "wp/v2/menu-items", {"menus": menu_id, "context": "edit"}, unread):
        items.append({
            "id": int(raw.get("id", 0) or 0),
            "title": _title(raw),
            "url": str(raw.get("url", "") or ""),
            "order": int(raw.get("menu_order", 0) or 0),
            "parent": int(raw.get("parent", 0) or 0),
        })
    return sorted(items, key=lambda i: i["order"])


def gather_more(
    kind: str, site: str, api: WordPressApi, unread: list[str] | None = None
) -> dict[str, Mapping[str, Any]]:
    """For menus or patterns on one site: name -> what the site has, its variant as ``value``."""
    found: dict[str, Mapping[str, Any]] = {}
    if kind == "menus":
        home = getattr(getattr(api, "address", None), "site_url", "")
        for raw in _all(api, "wp/v2/menus", {"context": "edit"}, unread):
            ident = int(raw.get("id", 0) or 0)
            items = _menu_items(api, ident, unread)
            titles = ", ".join(i["title"] for i in items[:8])
            word = "item" if len(items) == 1 else "items"
            found[str(raw.get("name", ""))] = {
                "id": ident,
                "items": items,
                "home": home,
                "value": f"{len(items)} {word}: {titles}" if items else "no items",
            }
    elif kind == "patterns":
        for raw in _all(api, "wp/v2/blocks", {"context": "edit"}, unread):
            content = raw_text(raw.get("content")) or rendered(raw.get("content"))
            found[_title(raw)] = {
                "id": int(raw.get("id", 0) or 0),
                "content": content,
                "value": f"{len(content)} characters, changed {raw.get('modified_gmt', '')[:10]}",
            }
    elif kind == "app_passwords":
        found.update(_app_passwords(api, unread))
    return found


def _passwords_of(
    api: WordPressApi,
    route: str,
    person: str,
    user: str,
    unread: list[str] | None = None,
) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for raw in _all(api, route, {}, unread):
        name = str(raw.get("name", "") or "")
        found[f"{name}, {person}"] = {
            "uuid": str(raw.get("uuid", "")),
            "route": f"{route}/{raw.get('uuid', '')}",
            "user": user,
            "value": f"last used {str(raw.get('last_used') or 'never')[:10]}",
        }
    return found


def _app_passwords(api: WordPressApi, unread: list[str] | None = None) -> dict[str, Any]:
    """Your application passwords, and others' where the site lets you read them (edit_users).

    WordPress answers another person's list only to someone who may edit
    that person; a refusal leaves those out, said by the row's absence.
    """
    found = _passwords_of(api, "wp/v2/users/me/application-passwords", "you", "me", unread)
    from quill.core.wordpress.site_admin import current_password_uuid

    signed_in = current_password_uuid(api)
    for raw in found.values():
        # The one QUILL signs in with is marked, so Revoke Everywhere refuses it.
        raw["current"] = bool(signed_in) and raw.get("uuid") == signed_in
    try:
        me = api.get("wp/v2/users/me")
        my_id = int(me.get("id", 0) or 0) if isinstance(me, dict) else 0
    except WordPressApiError:
        my_id = 0
    for user in _all(api, "wp/v2/users", {"context": "edit"}, unread):
        ident = int(user.get("id", 0) or 0)
        if not ident or ident == my_id:
            continue
        person = str(user.get("username") or user.get("email") or user.get("name") or ident)
        route = f"wp/v2/users/{ident}/application-passwords"
        found.update(_passwords_of(api, route, person, str(ident)))
    return found


def revoke_plan(
    name: str, objects: Mapping[str, Mapping[str, Any]], refusals: Mapping[str, str]
) -> tuple[list[tuple[str, str]], list[Outcome]]:
    """(site, route to delete) for each site with the password, and the sites refused."""
    plan: list[tuple[str, str]] = []
    refused: list[Outcome] = []
    from quill.core.wordpress.workbench_permissions import revoke_refusal

    for site, raw in objects.items():
        reason = refusals.get(site) or revoke_refusal(bool(raw.get("current")), site)
        if reason:
            refused.append(Outcome(site, name, False, reason))
        elif raw.get("route"):
            plan.append((site, str(raw["route"])))
    return plan, refused


# -- Make Them the Same --------------------------------------------------------------


def _term_route(name: str) -> str:
    return "wp/v2/categories" if name.endswith("(category)") else "wp/v2/tags"


def _edit_for(
    kind: str, site: str, name: str, winner: Mapping[str, Any], mine: Mapping[str, Any] | None
) -> Edit | str:
    """The edit that makes *site* match *winner*, or why it cannot be made."""
    if kind == "terms":
        route = _term_route(name)
        body = {"name": winner.get("name"), "slug": winner.get("slug")}
        if winner.get("description"):
            body["description"] = winner["description"]
        if mine is None:
            return Edit(site, route, name, body, None, words="made, as the winner has it")
        before = {k: mine.get(k, "") for k in body}
        return Edit(
            site,
            f"{route}/{mine.get('id')}",
            name,
            body,
            before,
            "slug",
            mine.get("slug"),
            f"slug {mine.get('slug')} becomes {winner.get('slug')}",
        )
    if kind == "plugins":
        if mine is None:
            return "not installed here; Install on Sites Missing It adds it"
        status = winner.get("status")
        if status == "network-active":
            return "the winner is network-active; Promote to Network does that"
        return Edit(
            site,
            f"wp/v2/plugins/{mine.get('plugin')}",
            name,
            {"status": status},
            {"status": mine.get("status")},
            "status",
            mine.get("status"),
            f"{mine.get('status')} becomes {status}",
        )
    if kind == "settings":
        mine_value = None if mine is None else mine.get("value")
        if mine is None:
            return "this site's WordPress does not have the setting"
        return Edit(
            site,
            "wp/v2/settings",
            name,
            {name: winner.get("value")},
            {name: mine_value},
            name,
            mine_value,
            f"{mine_value} becomes {winner.get('value')}",
        )
    if kind == "users":
        if mine is None:
            return (
                "this person is not on this site; adding them needs an email and a password "
                "chosen there (New Here, on that site's People)"
            )
        roles = list(winner.get("roles") or [])
        if not roles:
            return "the winner has no role to copy"
        return Edit(
            site,
            f"wp/v2/users/{mine.get('id')}",
            name,
            {"roles": roles[:1]},
            {"roles": list(mine.get("roles") or [])},
            "roles",
            list(mine.get("roles") or []),
            f"role {', '.join(mine.get('roles') or ['none'])} becomes {roles[0]}",
        )
    if kind == "patterns":
        content = winner.get("content", "")
        if mine is None:
            return Edit(
                site,
                "wp/v2/blocks",
                name,
                {"title": name, "content": content, "status": "publish"},
                None,
                words="made, with the winner's content",
            )
        return Edit(
            site,
            f"wp/v2/blocks/{mine.get('id')}",
            name,
            {"content": content},
            {"content": mine.get("content", "")},
            words="content becomes the winner's",
        )
    return f"{kind} are not changed by an edit here"


def make_same_edits(
    kind: str,
    name: str,
    plan: Sequence[tuple[str, str]],
    objects: Mapping[str, Mapping[str, Any]],
    winner: Mapping[str, Any],
) -> tuple[list[Edit], list[Outcome]]:
    """The edits for every site that differs, and the sites that cannot be made to match."""
    edits: list[Edit] = []
    refused: list[Outcome] = []
    for site, words in plan:
        if words.startswith("already"):
            continue
        if words.startswith("not read"):
            refused.append(Outcome(site, name, False, words))
            continue
        made = _edit_for(kind, site, name, winner, objects.get(site))
        if isinstance(made, Edit):
            edits.append(made)
        else:
            refused.append(Outcome(site, name, False, made))
    return edits, refused


def theme_screens(
    plan: Sequence[tuple[str, str]], objects: Mapping[str, Mapping[str, Any]], stylesheet: str
) -> tuple[list[str], list[Outcome]]:
    """The sites whose Themes screen opens to activate *stylesheet*, and those without it."""
    open_on: list[str] = []
    refused: list[Outcome] = []
    for site, words in plan:
        if words.startswith("already"):
            continue
        if words.startswith("not read"):
            refused.append(Outcome(site, stylesheet, False, words))
            continue
        if site in objects:
            open_on.append(site)
        else:
            refused.append(
                Outcome(site, stylesheet, False, "not installed; Install on Sites Missing It first")
            )
    return open_on, refused


# -- menus ------------------------------------------------------------------------


def rehost(url: str, source_home: str, target_home: str) -> str:
    """*url* on the source site, pointed at the target site; any other address unchanged."""
    if not source_home or not target_home:
        return url
    src, dst = urlparse(source_home), urlparse(target_home)
    got = urlparse(url)
    if got.netloc and got.netloc.lower() == src.netloc.lower():
        path = got.path
        if src.path.rstrip("/") and path.startswith(src.path.rstrip("/")):
            path = path[len(src.path.rstrip("/")) :]
        return got._replace(
            scheme=dst.scheme, netloc=dst.netloc, path=dst.path.rstrip("/") + path
        ).geturl()
    return url


def menu_copy(
    api: WordPressApi,
    site: str,
    name: str,
    winner: Mapping[str, Any],
    mine: Mapping[str, Any] | None,
    target_home: str,
) -> Outcome:
    """Make *site*'s menu *name* hold the winner's items, as links (made where missing)."""
    try:
        if mine is None:
            made = api.post("wp/v2/menus", {"name": name})
            menu_id = int(made.get("id", 0) or 0) if isinstance(made, dict) else 0
            if not menu_id:
                return Outcome(site, name, False, "the site did not make the menu")
        else:
            menu_id = int(mine.get("id", 0) or 0)
            for item in mine.get("items") or []:
                api.delete(f"wp/v2/menu-items/{item['id']}", force=True)
        new_ids: dict[int, int] = {}
        for item in winner.get("items") or []:
            body: dict[str, Any] = {
                "title": item["title"],
                "url": rehost(item["url"], str(winner.get("home", "")), target_home),
                "type": "custom",
                "status": "publish",
                "menus": menu_id,
                "menu_order": item["order"],
            }
            if item.get("parent") in new_ids:
                body["parent"] = new_ids[item["parent"]]
            made = api.post("wp/v2/menu-items", body)
            if isinstance(made, dict) and made.get("id"):
                new_ids[item["id"]] = int(made["id"])
    except WordPressApiError as exc:
        return Outcome(site, name, False, exc.plain or str(exc))
    count = len(winner.get("items") or [])
    return Outcome(site, name, True, f"now has the winner's {count} items, as links")


# -- global styles ------------------------------------------------------------------


def site_styles(api: WordPressApi) -> dict[str, str] | str:
    """One site's palette and font sizes in effect, by name; or why they cannot be read."""
    from quill.core.wordpress import site_styles as styles

    try:
        theme = styles.active_theme(api)
        if not theme.block_theme or not theme.stylesheet:
            return "its active theme does not use global styles"
        base = styles.theme_styles(api, theme.stylesheet)
        user: dict[str, Any] = {}
        if theme.styles_id:
            try:
                user = styles.load_user_styles(api, theme.styles_id)
            except WordPressApiError as exc:
                if exc.status not in (401, 403):
                    raise
        found = {"Theme": theme.name or theme.stylesheet}
        for entry in styles.entries(base, user):
            word = "Colour" if entry.kind == "colour" else "Font size"
            found[f"{word} {entry.name}"] = entry.value
        return found
    except WordPressApiError as exc:
        return f"not read: {exc.plain or exc}"


def compare_styles(per_site: Mapping[str, dict[str, str] | str]) -> tuple[str, list[str]]:
    """A summary and one line per style that differs, then what is the same everywhere."""
    readable = {s: v for s, v in per_site.items() if isinstance(v, dict)}
    lines: list[str] = [f"{s}: {v}" for s, v in per_site.items() if isinstance(v, str)]
    names = sorted({n for v in readable.values() for n in v})
    same = 0
    for style in names:
        values = {site: v.get(style, "not set") for site, v in readable.items()}
        if len(set(values.values())) == 1:
            same += 1
            continue
        lines.append(f"{style}: " + "; ".join(f"{s} {val}" for s, val in values.items()))
    differ = len(names) - same
    summary = (
        f"{differ} of {len(names)} styles differ across {len(readable)} sites; {same} are the same."
        if readable
        else "No site's global styles could be read."
    )
    return summary, lines


# -- the network ----------------------------------------------------------------------


def network_status(api: WordPressApi) -> bool:
    """Whether the site's plugin schema offers ``network-active`` (only a multisite does)."""
    try:
        response = api.request("OPTIONS", "wp/v2/plugins")
    except WordPressApiError:
        return False
    payload = getattr(response, "payload", None)
    schema = payload.get("schema") if isinstance(payload, dict) else None
    props = schema.get("properties") if isinstance(schema, dict) else None
    status = props.get("status") if isinstance(props, dict) else None
    enum = status.get("enum") if isinstance(status, dict) else None
    return isinstance(enum, list) and "network-active" in enum


def network_refusal(site: str, is_network: bool, can_activate: bool) -> str:
    """Why Promote to Network cannot run on *site* ("" when WordPress will be asked)."""
    if not is_network:
        return (
            f"{site} is not a multisite network: its plugin schema has no network-active "
            "status, so the plugin stays per site."
        )
    if not can_activate:
        return f"Promote to Network needs a super admin of {site}'s network."
    return ""


def run_edits_by_site(
    api_for: Callable[[str], WordPressApi], edits: Sequence[Edit]
) -> tuple[list[Outcome], list[Edit]]:
    """:func:`apply_edits` site by site; a site that fails does not stop the rest."""
    from quill.core.wordpress.workbench_by_name import apply_edits

    outcomes: list[Outcome] = []
    sent: list[Edit] = []
    for site in dict.fromkeys(e.site for e in edits):
        mine = [e for e in edits if e.site == site]
        try:
            got, done = apply_edits(api_for(site), mine)
        except Exception as exc:  # noqa: BLE001 - one site's failure is that site's outcome
            got = [
                Outcome(site, e.title, False, getattr(exc, "plain", "") or str(exc)) for e in mine
            ]
            done = []
        outcomes += got
        sent += done
    return outcomes, sent
