"""The hosted AI's feature catalogue: tools the server offers that this build
does not have built in.

``GET /v1/config`` carries a ``features`` list (added 2026-10): one entry per
feature the service has switched on, each with an ``id`` (the value sent as
``feature`` to ``/v1/chat``, naming a fixed template on the server), a
``label``, one sentence of ``help``, the kind of ``input`` it takes, and its
``max_input_tokens``. A
new text tool on the server is a template there and an entry in that list --
no release of QUILL or QUILL Lite -- and the pad (:mod:`quill.ui.hosted_ai_pad`)
offers it as one more row, run through exactly the path every built-in row
takes. Its answer opens in the ordinary AI Result window -- a title the F1
catalogue already knows, where a title invented by the server would answer F1
with nothing written for it.

**Everything here is remote input**, so nothing is trusted. An entry is kept
only if every field is the right type and shape: an id that looks like an id,
a label and a help sentence that are plain printable text of a sensible length,
an input kind this build knows how to collect. A malformed entry is dropped on
its own; a malformed list is an empty catalogue. :func:`parse_catalogue` never
raises, because a catalogue the client cannot read must cost the person
nothing but the extra rows -- never the limits that came in the same answer.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = [
    "INPUT_DOCUMENT",
    "INPUT_PROMPT",
    "INPUT_SELECTION",
    "MAX_ENTRIES",
    "SUPPORTED_INPUTS",
    "CatalogueFeature",
    "extra_features",
    "parse_catalogue",
]

#: A passage from the document: the selection, else the paragraph, else the
#: section. The shape of Summarize.
INPUT_SELECTION = "selection"
#: Only what the person types; nothing from the document. The shape of Ask.
INPUT_PROMPT = "prompt"
#: A typed question plus excerpts picked from the document to answer it. The
#: shape of Ask a Question About the Document.
INPUT_DOCUMENT = "document"

#: The input kinds this build can collect. Anything else -- ``conversation``,
#: which only the built-in Have a Conversation row uses, or a kind a later
#: server invents -- is skipped, never guessed at.
SUPPORTED_INPUTS: frozenset[str] = frozenset({INPUT_SELECTION, INPUT_PROMPT, INPUT_DOCUMENT})

#: At most this many entries are read. A list is a list somebody arrows
#: through; a server sending hundreds is a bug, not a menu.
MAX_ENTRIES = 40

_ID = re.compile(r"[a-z][a-z0-9_]{0,39}")
_MAX_LABEL = 60
_MAX_HELP = 400
#: The largest per-feature input ceiling believed; above it the global limit
#: stands. The server re-checks every size whatever the client believes.
_MAX_TOKENS = 1_000_000


@dataclass(frozen=True, slots=True)
class CatalogueFeature:
    """One feature the service describes, already validated."""

    id: str
    label: str
    help: str
    input: str
    #: This feature's input ceiling in tokens, or 0 for "the global one".
    max_input_tokens: int = 0


def _plain(value: Any, limit: int) -> str:
    """*value* as one line of plain text, or "" when it is not usable.

    Control characters (a stray newline, a bell, a right-to-left override) are
    removed rather than trusted: this text goes into a list a screen reader
    reads. An ampersand is kept as written -- the
    list it lands in is a list box, not a menu, so it is not a mnemonic.
    """
    if not isinstance(value, str):
        return ""
    cleaned = "".join(
        " " if ch.isspace() else ch for ch in value if ch.isspace() or ch.isprintable()
    )
    cleaned = " ".join(cleaned.split())
    if not cleaned or len(cleaned) > limit:
        return ""
    return cleaned


def _entry(raw: Any) -> CatalogueFeature | None:
    if not isinstance(raw, dict):
        return None
    feature_id = raw.get("id")
    if not isinstance(feature_id, str) or not _ID.fullmatch(feature_id):
        return None
    kind = raw.get("input")
    if not isinstance(kind, str) or kind not in SUPPORTED_INPUTS:
        return None
    label = _plain(raw.get("label"), _MAX_LABEL)
    help_text = _plain(raw.get("help"), _MAX_HELP)
    if not label or not help_text:
        return None
    tokens = raw.get("max_input_tokens", 0)
    # bool is an int in Python; True is not a token count.
    if isinstance(tokens, bool) or not isinstance(tokens, int) or not 0 < tokens <= _MAX_TOKENS:
        tokens = 0
    return CatalogueFeature(feature_id, label, help_text, kind, tokens)


def parse_catalogue(raw: Any) -> tuple[CatalogueFeature, ...]:
    """The usable entries of *raw*, in the server's order. Never raises.

    A duplicate id keeps its first entry, and so does a duplicate label: two
    rows a listener cannot tell apart are one row too many.
    """
    if not isinstance(raw, list):
        return ()
    kept: list[CatalogueFeature] = []
    ids: set[str] = set()
    labels: set[str] = set()
    for item in raw[:MAX_ENTRIES]:
        entry = _entry(item)
        if entry is None or entry.id in ids or entry.label.casefold() in labels:
            continue
        ids.add(entry.id)
        labels.add(entry.label.casefold())
        kept.append(entry)
    return tuple(kept)


def extra_features(
    catalogue: tuple[CatalogueFeature, ...],
    built_in_ids: set[str] | frozenset[str],
    built_in_labels: set[str] | frozenset[str] = frozenset(),
) -> tuple[CatalogueFeature, ...]:
    """The entries this build does not already offer itself.

    Matched by id, and by label as well: a server entry that would sit in the
    list under the same words as a built-in row is left out, because a
    listener would hear the same row twice and could not tell which is which.
    """
    labels = {label.casefold() for label in built_in_labels}
    return tuple(
        entry
        for entry in catalogue
        if entry.id not in built_in_ids and entry.label.casefold() not in labels
    )
