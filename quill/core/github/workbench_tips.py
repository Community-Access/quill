"""Tips at the right moment, and the two characters who speak in help (PRD D16, GH-R-116).

**QUILLBert finds things worth trying; QUILLBee explains.** They speak only in
help and tips, never in a result, with one line each. :func:`voice` puts the
name in front, or, with **Plain help** chosen in Workbench Options, says the
same words as plain "Tip" and plain help.

**At the right moment, never pushed.** A :data:`MOMENTS` tip is offered only
the *third* time somebody does a thing the slow way (a long list read
without the filter, Properties opened one row at a time, Load More pressed
again and again), only once per tip, and only in the details pane: it is not
spoken, so it interrupts nothing, and arrowing reads it when the person goes
there. **Offer a tip when it would help** in Workbench Options turns them off;
they stay in Help and Learning, Tips, where every tip always is.

:class:`TipMoments` keeps the counts in ``github_workbench_tips.json`` beside
the preferences (atomic, per person, nothing sent anywhere), written when the
Workbench window closes. wx-free and
strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "BEE",
    "BERT",
    "FILENAME",
    "LONG_LIST",
    "MOMENTS",
    "OFFER_AFTER",
    "Moment",
    "TipMoments",
    "voice",
]

FILENAME = "github_workbench_tips.json"
BERT = "QUILLBert"
BEE = "QUILLBee"
#: The time a slow way is done that brings its tip: the third (D16).
OFFER_AFTER = 3
#: A list this long is a long one to arrow through without the filter.
LONG_LIST = 30


@dataclass(frozen=True, slots=True)
class Moment:
    """A slow way of doing something, and the tip it earns."""

    id: str
    #: What the person did, as the tip's Why? says it.
    slow_way: str
    tip: str


MOMENTS: dict[str, Moment] = {
    moment.id: moment
    for moment in (
        Moment(
            "long_list_no_filter",
            "read a long list without the filter",
            "Type a word in the filter box, Ctrl+E, and only the rows with it stay; "
            "Escape clears it.",
        ),
        Moment(
            "properties_one_at_a_time",
            "opened Properties on one row after another",
            "You can select all these rows and press Alt+Enter once: one sheet changes "
            "them all, with a preview first.",
        ),
        Moment(
            "load_more_again",
            "pressed Load More again and again",
            "Load All, Ctrl+Shift+PageDown, reads every page at once.",
        ),
    )
}


def voice(character: str, text: str, *, plain: bool = False) -> str:
    """*text* as QUILLBert's tip or QUILLBee's explanation, or plainly."""
    if character == BERT:
        return f"Tip: {text}" if plain else f"{BERT}'s tip: {text}"
    if character == BEE:
        return text if plain else f"{BEE} explains: {text}"
    return text


@dataclass
class TipMoments:
    """How often each slow way was done, and which tips were already offered."""

    counts: dict[str, int] = field(default_factory=dict)
    offered: set[str] = field(default_factory=set)
    path: Path | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> TipMoments:
        target = path or app_data_dir() / FILENAME
        raw = read_json(target, default={})
        data: Mapping[str, Any] = raw if isinstance(raw, dict) else {}
        counts_raw = data.get("counts", {})
        counts = (
            {str(k): int(v) for k, v in counts_raw.items() if isinstance(v, int)}
            if isinstance(counts_raw, dict)
            else {}
        )
        offered_raw = data.get("offered", [])
        offered = {str(item) for item in offered_raw} if isinstance(offered_raw, list) else set()
        return cls(counts, offered, target)

    def save(self) -> None:
        if self.path is None:
            return
        document = {"counts": dict(sorted(self.counts.items())), "offered": sorted(self.offered)}
        try:
            write_json_atomic(self.path, document)
        except OSError:
            pass  # a tip not remembered is offered again, never an error

    def record(self, moment_id: str, *, enabled: bool = True, plain: bool = False) -> str:
        """Count one slow way; the tip's words the time it is due, else ``""``.

        Nothing is written here: the counts are kept by :meth:`save`, which the
        Workbench calls when its window closes.
        """
        moment = MOMENTS.get(moment_id)
        if moment is None or not enabled or moment_id in self.offered:
            return ""
        self.counts[moment_id] = self.counts.get(moment_id, 0) + 1
        if self.counts[moment_id] < OFFER_AFTER:
            return ""
        self.offered.add(moment_id)
        return voice(BERT, moment.tip, plain=plain)
