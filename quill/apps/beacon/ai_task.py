"""Organize What I Saved: QuillBeacon's agent task (codex.md 6.10, Phase 4c).

The person says what they want ("tag everything about knitting and put it in a
Crafts collection"), and an agent engine -- My GitHub Copilot or Codex -- works
through it with Beacon's own tools in the shared agent window
(:mod:`quill.ui.agent_window`):

* ``beacon.search`` -- Beacon's own search (``search.search``, the syntax the
  search box takes), as numbered rows with an id (``I1``) the other tools take,
  then the collections and tags already in the library.
* ``beacon.read_item`` -- one saved item's title, kind, where it points, note,
  tags and collections. A file on this computer is named as such, never by its
  path.
* ``beacon.suggest_tags`` -- the local Suggest Tags helper
  (``assist.suggest_tags``); nothing is sent to work it out.
* ``beacon.tag`` and ``beacon.move`` -- each shows the change as text first and
  makes it only on Apply, through the store, as one Ctrl+Z step.

Nothing here deletes, trashes, archives, opens or publishes anything. Beacon's
store is a SQLite connection that belongs to the UI thread, so every touch of
it goes through ``ctx.on_ui``. Nothing here announces: the agent window says
each step and the closing summary, once (GATE-13).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "APP",
    "INSTRUCTION_HELP",
    "ORGANIZE",
    "beacon_task_facts",
    "beacon_task_tools",
]

APP = "beacon"

_SEARCH_LIMIT = 30
_NOTE_LIMIT = 4000
_NOT_APPLIED = "The person did not apply it."
_TOP = ("", "none", "no collection", "top level", "the top level")

ORGANIZE = AppTaskSpec(
    app=APP,
    agent_id="beacon-organize",
    title="Organize What I Saved",
    instructions=(
        "You help someone who uses a screen reader organise what they saved in "
        "QuillBeacon: web pages, files, podcast episodes and passages, each with "
        "a title, a note, tags and collections. Find items with beacon_search "
        "(it takes words, and filters such as tag:research, "
        'collection:"News", type:episode and is:favorite), read one with '
        "beacon_read_item, and get local tag ideas with beacon_suggest_tags. "
        "Use the ids the search gives (I1). Tagging and moving an item to a "
        "collection each show the change and ask the person, and they may say "
        "no. Never suggest deleting anything."
    ),
    done_words={
        f"{APP}.tag": "Tagged an item",
        f"{APP}.move": "Moved an item",
    },
)

INSTRUCTION_HELP = (
    "Type how you want what you saved organised, then press Enter. For example: "
    "tag everything about knitting as crafts and put it in a Crafts collection. "
    "Each change shows you what it will do and waits for you, and Ctrl+Z undoes "
    "it. While a task runs, what you type here goes to it as a follow-up."
)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _listing(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def beacon_task_facts(host: Any) -> str:
    """What is on screen, as text, sent with the first instruction."""
    lines: list[str] = []
    query = str(getattr(host, "last_query", "") or "").strip()
    if query:
        lines.append(f"Search box: {query}")
    selected = getattr(host, "_selected_beacon", None)
    try:
        beacon = selected() if callable(selected) else None
    except Exception:  # noqa: BLE001 - no list, no selection
        beacon = None
    if beacon is not None:
        lines.append(f"Selected item: {beacon.title or 'Untitled'}")
    return "\n".join(lines)


def _where(resource: Any) -> str:
    """Where an item points, without ever naming a path on this computer."""
    if resource is None:
        return "nowhere recorded"
    uri = str(getattr(resource, "primary_uri", "") or "")
    scheme = urlparse(uri).scheme.lower()
    if scheme in ("http", "https"):
        return uri
    if scheme == "file" or (len(uri) > 2 and uri[1] == ":") or uri.startswith("\\\\"):
        return "a file on this computer"
    return uri.split(":", 1)[0] + " link" if ":" in uri else "nowhere recorded"


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def beacon_task_tools(host: Any, ctx: AppTaskHost) -> list[FamilyTool]:
    """QuillBeacon's tools for one task."""
    found: dict[str, str] = {}

    def remember(beacon_id: str) -> str:
        for key, known in found.items():
            if known == beacon_id:
                return key
        key = f"I{len(found) + 1}"
        found[key] = beacon_id
        return key

    def item_for(args: dict[str, Any]) -> Any:
        wanted = str(args.get("item", "") or "").strip().upper()
        beacon_id = found.get(wanted)
        beacon = ctx.on_ui(lambda: host.store.get_beacon(beacon_id), None) if beacon_id else None
        if beacon is None or beacon.trashed:
            raise ToolError("Use beacon_search first, and pass the item's id, such as I1.")
        return beacon

    def title_of(args: dict[str, Any]) -> str:
        try:
            return str(item_for(args).title or "Untitled")
        except ToolError:
            return str(args.get("item", "") or "that item")

    def refresh(beacon: Any) -> None:
        """Show the change where the person is looking, as Beacon's own commands do."""
        cache = getattr(host, "_results_cache", [])
        for index, row in enumerate(cache):
            if row.beacon_id == beacon.beacon_id:
                cache[index] = beacon
        for name in ("_refresh_sidebar", "_refresh_results"):
            method = getattr(host, name, None)
            if callable(method):
                method()

    def save(beacon: Any, label: str) -> None:
        """Put *beacon* through the store as one undo step."""
        from quill.apps.beacon.undo import restore_beacons, snapshot_beacons

        store = host.store
        snaps = snapshot_beacons(store, [beacon.beacon_id])
        store.put_beacon(beacon)
        undo = getattr(host, "undo", None)
        if undo is not None:
            undo.push(label, lambda: restore_beacons(store, snaps))
        refresh(beacon)

    # -- reads ---------------------------------------------------------------

    def search_items(args: dict[str, Any]) -> str:
        from quill.apps.beacon import search

        query = " ".join(str(args.get("query", "") or "").split())

        def read() -> tuple[list[Any], list[str], list[str]]:
            rows = search.search(host.store, query, limit=_SEARCH_LIMIT)
            collections = [c.name for c in host.store.list_collections()]
            tags = [t.name for t in host.store.list_tags()]
            return rows, collections, tags

        rows, collections, tags = ctx.on_ui(read, ([], [], [])) or ([], [], [])
        lines: list[str] = []
        if rows:
            head = f"{_plural(len(rows), 'item')}" + (f" for {query}" if query else "")
            lines.append(head + ":")
            for beacon in rows:
                line = f"{remember(beacon.beacon_id)}. {beacon.title or 'Untitled'}"
                if beacon.tags:
                    line += f". Tags: {', '.join(beacon.tags)}"
                if beacon.collections:
                    line += f". In: {', '.join(beacon.collections)}"
                lines.append(line + ".")
        else:
            lines.append(f"Nothing matched {query}." if query else "Nothing is saved yet.")
        lines.append(f"Collections: {_listing(collections)}.")
        lines.append(f"Tags in use: {_listing(tags[:60])}.")
        return "\n".join(lines)

    def read_item(args: dict[str, Any]) -> str:
        beacon = item_for(args)
        resource = ctx.on_ui(lambda: host.store.get_resource(beacon.resource_id), None)
        note = str(beacon.note or "").strip()
        if len(note) > _NOTE_LIMIT:
            note = note[:_NOTE_LIMIT].rstrip() + " ..."
        state = [
            word
            for word, on in (
                ("a favourite", beacon.favorite),
                ("in the inbox", beacon.in_inbox),
                ("archived", beacon.archived),
            )
            if on
        ]
        lines = [
            f"Title: {beacon.title or 'Untitled'}",
            f"Kind: {getattr(resource, 'type', '') or 'unknown'}",
            f"Points to: {_where(resource)}",
            f"Tags: {_listing(list(beacon.tags))}",
            f"Collections: {_listing(list(beacon.collections))}",
        ]
        if state:
            lines.append(f"It is {', '.join(state)}.")
        lines.append(f"Note: {note}" if note else "Note: none")
        return "\n".join(lines)

    def suggest_tags(args: dict[str, Any]) -> str:
        from quill.apps.beacon import assist

        beacon = item_for(args)
        text = " ".join([beacon.title or "", beacon.note or ""])
        ideas = assist.suggest_tags(text, existing=list(beacon.tags), limit=8)
        if not ideas:
            return f"No new tag ideas for {beacon.title or 'that item'}."
        return (
            f"Tag ideas for {beacon.title or 'that item'}, from its own words, worked out "
            f"on this computer: {', '.join(ideas)}."
        )

    # -- what changes --------------------------------------------------------

    def _tag_list(args: dict[str, Any], key: str) -> list[str]:
        raw = args.get(key) or []
        if isinstance(raw, str):
            raw = raw.split(",")
        return [t for t in dict.fromkeys(" ".join(str(x).split()) for x in raw) if t]

    def tag_change(args: dict[str, Any]) -> tuple[Any, list[str], list[str], list[str]]:
        beacon = item_for(args)
        add = _tag_list(args, "add")
        remove = _tag_list(args, "remove")
        if not add and not remove:
            raise ToolError("Say which tags to add or remove.")
        have = list(beacon.tags)
        folded_remove = {t.casefold() for t in remove}
        after = [t for t in have if t.casefold() not in folded_remove]
        present = {t.casefold() for t in after}
        added = [t for t in add if t.casefold() not in present]
        after += added
        removed = [t for t in have if t.casefold() in folded_remove]
        if not added and not removed:
            raise ToolError(f"{beacon.title or 'That item'} already has exactly those tags.")
        return beacon, added, removed, after

    def tag(args: dict[str, Any]) -> str:
        beacon, added, removed, after = tag_change(args)
        title = beacon.title or "Untitled"
        text = "\n".join([
            f"Item: {title}",
            f"Tags now: {_listing(list(beacon.tags))}",
            f"Add: {_listing(added)}",
            f"Remove: {_listing(removed)}",
            f"Tags after: {_listing(after)}",
        ])
        if not ctx.preview(f"Tag {title}", text):
            raise ToolError(_NOT_APPLIED)
        beacon.tags = after
        ctx.on_ui(lambda: save(beacon, f"Tag {title}"), None)
        return f"Tagged {title}: {_listing(after)}. Ctrl+Z in QuillBeacon undoes it."

    def tag_summary(args: dict[str, Any]) -> str:
        try:
            beacon, added, removed, _after = tag_change(args)
        except ToolError:
            return f"Change the tags on {title_of(args)}."
        title = beacon.title or "Untitled"
        parts = []
        if added:
            parts.append(f"add the tag{'s' if len(added) > 1 else ''} {', '.join(added)}")
        if removed:
            parts.append(f"remove {', '.join(removed)}")
        return f"On {title}, {' and '.join(parts)}."

    def move_change(args: dict[str, Any]) -> tuple[Any, list[str], list[str], str]:
        beacon = item_for(args)
        target = " ".join(str(args.get("collection", "") or "").split())
        if not target or target.casefold() in _TOP:
            raise ToolError("Say which collection to move it to.")
        source = " ".join(str(args.get("from_collection", "") or "").split())
        have = list(beacon.collections)
        names = ctx.on_ui(lambda: [c.name for c in host.store.list_collections()], []) or []
        for name in names:
            if name.casefold() == target.casefold():
                target = name
        if source:
            if source.casefold() not in {c.casefold() for c in have}:
                raise ToolError(f"{beacon.title or 'That item'} is not in {source}.")
            leaving = [c for c in have if c.casefold() == source.casefold()]
        else:
            leaving = [c for c in have if c.casefold() != target.casefold()]
        after = [c for c in have if c not in leaving]
        if target.casefold() not in {c.casefold() for c in after}:
            after.append(target)
        if after == have:
            raise ToolError(f"{beacon.title or 'That item'} is already in {target}.")
        new = "" if target in names else " (a new collection)"
        return beacon, leaving, after, target + new

    def move(args: dict[str, Any]) -> str:
        beacon, leaving, after, target = move_change(args)
        title = beacon.title or "Untitled"
        text = "\n".join([
            f"Move: {title}",
            f"From: {_listing(leaving)}",
            f"To: {target}",
            f"Collections after: {_listing(after)}",
        ])
        if not ctx.preview(f"Move {title}", text):
            raise ToolError(_NOT_APPLIED)
        beacon.collections = after
        ctx.on_ui(lambda: save(beacon, f"Move {title}"), None)
        return f"Moved {title} to {target}. Ctrl+Z in QuillBeacon undoes it."

    def move_summary(args: dict[str, Any]) -> str:
        try:
            beacon, leaving, _after, target = move_change(args)
        except ToolError:
            return f"Move {title_of(args)} to another collection."
        source = f" from {', '.join(leaving)}" if leaving else ""
        return f"Move {beacon.title or 'Untitled'}{source} to {target}."

    item_arg = {"type": "string", "description": "The item's id from a search (I1)."}
    tags_arg = {"type": "array", "items": {"type": "string"}}
    write = {
        "category": PermissionCategory.MODIFY_DOCUMENT,
        "risk": RiskLevel.MEDIUM,
        "app": APP,
        "mutating": True,
    }
    return [
        FamilyTool(
            name=f"{APP}.search",
            description=(
                "Search what is saved in QuillBeacon, with the search box's syntax: "
                'words, tag:name, collection:"Name", type:episode, is:favorite. Empty '
                "lists the newest. Returns items with an id such as I1, then the "
                "collections and tags in use."
            ),
            handler=search_items,
            parameters=_schema({"query": {"type": "string", "description": "The search."}}, ()),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.read_item",
            description=(
                "Read one saved item: title, kind, where it points, tags, collections and note."
            ),
            handler=read_item,
            parameters=_schema({"item": item_arg}, ("item",)),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.suggest_tags",
            description=(
                "Tag ideas for one item from its own title and note, worked out on this "
                "computer by QuillBeacon's Suggest Tags."
            ),
            handler=suggest_tags,
            parameters=_schema({"item": item_arg}, ("item",)),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.tag",
            description=(
                "Add tags to one item, or remove them. Shows the change and asks the "
                "person first; Ctrl+Z undoes it."
            ),
            handler=tag,
            parameters=_schema(
                {
                    "item": item_arg,
                    "add": {**tags_arg, "description": "Tags to add."},
                    "remove": {**tags_arg, "description": "Tags to remove (optional)."},
                },
                ("item",),
            ),
            summarize=tag_summary,
            **write,  # type: ignore[arg-type]
        ),
        FamilyTool(
            name=f"{APP}.move",
            description=(
                "Move one item into a collection: out of the collections it is in (or "
                "only from_collection), into the one named. A new name makes a new "
                "collection. Shows the move and asks the person first."
            ),
            handler=move,
            parameters=_schema(
                {
                    "item": item_arg,
                    "collection": {"type": "string", "description": "The collection to move to."},
                    "from_collection": {
                        "type": "string",
                        "description": "Only take it out of this one (optional).",
                    },
                },
                ("item", "collection"),
            ),
            summarize=move_summary,
            **write,  # type: ignore[arg-type]
        ),
    ]
