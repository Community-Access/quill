"""One node type for the whole Browse Stations tree.

Before this, the tree dialog knew the *shape* of every source: adding iHeart
meant three new node-kind strings and edits in six places (``_SOURCES``,
``_EXPANDABLE``, ``_LEAF_KINDS``, ``_fetch_children``, ``_subtree_children``,
``_add_children``), and Networks cost three more. Nine further sources at that
rate is twenty-five kind strings and a twenty-branch ``if`` ladder inside a wx
dialog that already carried a size budget.

So the dialog now knows exactly two things: a node is a **folder** you can open,
or a **leaf** you can play. Everything else -- how a genre becomes stations, how
TuneIn drills, how Apple's storefronts nest -- lives in
:mod:`quill.core.radio.browse_sources`, which is wx-free and unit-tested without
a UI.

The rules that make that work:

**``node_id`` is opaque to the UI.** It is a string the source parses and the
dialog only ever hands back. TuneIn's is a browse URL, iHeart's a genre id,
Apple's a storefront-and-genre pair. The dialog never branches on it.

**A leaf is playable now, or resolvable on demand.** ``resolve_lazily`` marks the
second: TuneIn stations and Apple shows cost a round trip before they can play,
and pre-resolving a folder full of them would be dozens of requests to show a
list nobody has chosen from yet.

**Ids must be stable across sessions.** ``browse_position.py`` remembers where
you were by path, so an id may not embed a cursor, a timestamp, or a fetched
payload. This is why a letter group under an iHeart genre re-derives its
stations from the (cached) genre rather than carrying them.

**A folder that knows its size says so.** ``child_count`` lets the tree announce
"Comedy, 214 stations" *before* the round trip that opens it, which is a real
gain for someone deciding whether to spend the wait.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio.models import RadioStation

#: Separator for multi-part node ids (``iheartletter:1310\tB``). A tab cannot
#: occur in a genre name, a country, or a URL, so parsing stays unambiguous
#: without escaping.
ARG_SEP = "\t"


@dataclass(frozen=True, slots=True)
class BrowseNode:
    """One row in the browse tree: a folder to open, or something to play."""

    node_id: str
    label: str
    is_folder: bool = False
    station: RadioStation | None = None
    #: Spoken after the label, so nothing surprises the listener after Enter --
    #: "opens in your browser", "resolves first", "affiliate search".
    note: str = ""
    #: Children, when the source knows the count cheaply. ``None`` means unknown.
    child_count: int | None = None
    #: A leaf whose stream URL costs a network round trip at activation time.
    resolve_lazily: bool = False
    #: An action rather than a folder or a station -- "Add a Server...",
    #: "More...". The dialog dispatches ``node_id`` to its command table.
    is_action: bool = False

    @property
    def is_leaf(self) -> bool:
        return not self.is_folder and not self.is_action

    @property
    def spoken_label(self) -> str:
        """Label plus count plus note, as the tree should announce it."""
        parts = [self.label]
        if self.child_count is not None:
            parts.append(f"{self.child_count} item{'' if self.child_count == 1 else 's'}")
        if self.note:
            parts.append(self.note)
        return ", ".join(parts)


def folder(
    node_id: str, label: str, *, note: str = "", child_count: int | None = None
) -> BrowseNode:
    """A node the listener can open."""
    return BrowseNode(
        node_id=node_id, label=label, is_folder=True, note=note, child_count=child_count
    )


def leaf(station: RadioStation, *, node_id: str = "", note: str = "") -> BrowseNode:
    """A directly playable station."""
    return BrowseNode(
        node_id=node_id or f"station{ARG_SEP}{station.stream_url}",
        label=station.display_name,
        station=station,
        note=note,
    )


def lazy_leaf(node_id: str, label: str, *, note: str = "") -> BrowseNode:
    """A playable row whose stream URL is resolved when it is activated."""
    return BrowseNode(node_id=node_id, label=label, resolve_lazily=True, note=note)


def action(node_id: str, label: str, *, note: str = "") -> BrowseNode:
    """A row that runs a command instead of opening or playing."""
    return BrowseNode(node_id=node_id, label=label, is_action=True, note=note)


def split_id(node_id: str) -> tuple[str, list[str]]:
    """``"iheartletter:1310\\tB"`` -> ``("iheartletter", ["1310", "B"])`` (pure).

    An id with no colon is a bare source name with no arguments.
    """
    kind, _, rest = node_id.partition(":")
    return kind, (rest.split(ARG_SEP) if rest else [])


def make_id(kind: str, *args: str) -> str:
    """Build a node id from its kind and arguments (pure)."""
    return f"{kind}:{ARG_SEP.join(args)}" if args else kind
