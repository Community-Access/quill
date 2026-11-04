"""Notes on blocks, the block editor's editorial notes (wordpress.md 9.15, WordPress 6.9+).

A note is a comment of type ``note`` on the post, never shown to visitors. The
block it belongs to carries the note's id in its ``metadata`` attribute
(``"metadata":{"noteId":12}``), so QUILL finds the block in the document by
reading block attributes through :mod:`block_spans`, in either document
format: in Markdown, a block with a note is a protected island line, and the
island keeps the attribute exactly.

A thread is one top-level note and its replies. Resolving a thread moves the
top note to ``hold`` and adds a reply carrying ``_wp_note_status: resolved``,
which is what the block editor shows as "Marked as resolved"; reopening puts
it back to ``approve``. Verified against the shape of WordPress 6.9; the
regression site (docs/qa/wordpress-test-site) is where to confirm it live.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress import block_spans as bs
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.blocks import Block
from quill.core.wordpress.site import friendly_date, plain_text, raw_text

#: The block attribute key, and the older name the feature had while in Gutenberg.
NOTE_KEYS = ("noteId", "blockCommentId")
STATUS_META = "_wp_note_status"

_ORDINALS = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
)


@dataclass(frozen=True)
class Note:
    id: int
    parent: int
    author_name: str
    date_gmt: str
    content: str
    status: str
    marker: str = ""  # "resolved" or "reopen" on a status reply

    @property
    def words(self) -> str:
        return plain_text(self.content)


@dataclass
class Thread:
    root: Note
    replies: list[Note] = field(default_factory=list)
    #: Where the block is, in words ("the second paragraph"), or "" when not found.
    place: str = ""
    #: The block's span index in the document, or None when not found.
    span: int | None = None

    @property
    def resolved(self) -> bool:
        for reply in reversed(self.replies):
            if reply.marker in ("resolved", "reopen"):
                return reply.marker == "resolved"
        return self.root.status == "hold"

    @property
    def spoken_replies(self) -> list[Note]:
        return [r for r in self.replies if r.words]

    def spoken(self) -> str:
        where = f" on {self.place}" if self.place else " on a block not in your copy"
        count = len(self.spoken_replies)
        replies = f", {count} repl{'y' if count == 1 else 'ies'}" if count else ""
        resolved = ", resolved" if self.resolved else ""
        return f"{self.root.author_name}{where}: {self.root.words}{replies}{resolved}"

    def details(self) -> str:
        lines = [f"{self.root.author_name}, {friendly_date(self.root.date_gmt)}: {self.root.words}"]
        for reply in self.replies:
            if reply.words:
                lines.append(f"{reply.author_name}, {friendly_date(reply.date_gmt)}: {reply.words}")
            elif reply.marker:
                done = "marked it resolved" if reply.marker == "resolved" else "reopened it"
                lines.append(f"{reply.author_name} {done}, {friendly_date(reply.date_gmt)}.")
        return "\n".join(lines)


def note_from_payload(raw: Mapping[str, Any]) -> Note:
    meta = raw.get("meta")
    marker = str(meta.get(STATUS_META, "") or "") if isinstance(meta, dict) else ""
    return Note(
        id=int(raw.get("id", 0) or 0),
        parent=int(raw.get("parent", 0) or 0),
        author_name=str(raw.get("author_name", "") or "Someone"),
        date_gmt=str(raw.get("date_gmt", "") or ""),
        content=raw_text(raw.get("content")),
        status=str(raw.get("status", "") or ""),
        marker=marker,
    )


def list_notes(api: WordPressApi, post_id: int) -> list[Note]:
    params: dict[str, object] = {
        "post": post_id,
        "type": "note",
        "status": "all",
        "context": "edit",
        "orderby": "date",
        "order": "asc",
    }
    return [note_from_payload(r) for r in api.iter_collection("wp/v2/comments", params)]


def threads(notes: Sequence[Note]) -> list[Thread]:
    """Top-level notes in date order, each with its replies (deeper replies flattened)."""
    by_id = {n.id: n for n in notes}
    out: dict[int, Thread] = {}
    for note in notes:
        if not note.parent or note.parent not in by_id:
            out[note.id] = Thread(note)
    for note in notes:
        if note.id in out:
            continue
        top = note.parent
        seen: set[int] = set()
        while top in by_id and by_id[top].parent and top not in seen:
            seen.add(top)
            top = by_id[top].parent
        if top in out:
            out[top].replies.append(note)
    for thread in out.values():
        thread.replies.sort(key=lambda n: n.date_gmt)
    return sorted(out.values(), key=lambda t: t.root.date_gmt)


def add_note(api: WordPressApi, post_id: int, content: str) -> Note:
    raw = api.post(
        "wp/v2/comments", {"post": post_id, "content": content, "type": "note"}, context="edit"
    )
    return note_from_payload(raw)


def reply(api: WordPressApi, post_id: int, thread: Thread, content: str) -> Note:
    raw = api.post(
        "wp/v2/comments",
        {"post": post_id, "parent": thread.root.id, "content": content, "type": "note"},
        context="edit",
    )
    return note_from_payload(raw)


def set_resolved(api: WordPressApi, post_id: int, thread: Thread, resolved: bool) -> None:
    """Resolve or reopen a thread, and leave the marker reply the block editor shows.

    The status change is what matters; a site that refuses the marker reply
    (an older 6.9 build without the meta) still has the thread resolved.
    """
    api.post(
        f"wp/v2/comments/{thread.root.id}",
        {"status": "hold" if resolved else "approve"},
        context="edit",
    )
    try:
        api.post(
            "wp/v2/comments",
            {
                "post": post_id,
                "parent": thread.root.id,
                "content": "",
                "type": "note",
                "meta": {STATUS_META: "resolved" if resolved else "reopen"},
            },
        )
    except WordPressApiError:
        pass


# --------------------------------------------------------------------------- #
# Notes and blocks


def note_id_of(block: Block | None) -> int:
    if block is None:
        return 0
    meta = block.attrs.get("metadata")
    if not isinstance(meta, dict):
        return 0
    for key in NOTE_KEYS:
        value = meta.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return 0


def set_note_id(block: Block, note_id: int) -> None:
    meta = block.attrs.get("metadata")
    meta = dict(meta) if isinstance(meta, dict) else {}
    meta["noteId"] = note_id
    block.attrs["metadata"] = meta


def ordinal(number: int) -> str:
    return _ORDINALS[number - 1] if 1 <= number <= len(_ORDINALS) else f"number {number}"


def place_words(spans: Sequence[bs.Span], index: int) -> str:
    """ "the second paragraph": the block by its kind and its count among that kind."""
    name = spans[index].name
    same = [i for i in bs.stops(spans) if spans[i].name == name]
    kind = bs.label(name).lower()
    if len(same) == 1:
        return f"the {kind}"
    position = same.index(index) + 1 if index in same else 0
    return f"the {ordinal(position)} {kind}" if position else f"a {kind}"


def locate(
    text: str,
    text_format: str,
    found: Sequence[Thread],
    islands: Mapping[str, str] | None = None,
) -> None:
    """Fill each thread's ``place`` and ``span`` from the blocks in *text*."""
    spans = bs.spans_for(text, text_format)
    where: dict[int, int] = {}
    for index in range(len(spans)):
        note_id = note_id_of(bs.block_at(text, text_format, spans, index, islands))
        if note_id and note_id not in where:
            where[note_id] = index
    for thread in found:
        index = where.get(thread.root.id)
        thread.span = index
        thread.place = place_words(spans, index) if index is not None else ""
