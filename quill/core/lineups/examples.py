"""Starter Lineups, offered as editable copies -- the way Cast seeds its playlists.

Each one shows a different Keep choice, because "how long things stay" is the
idea a listener most needs to see working. Every starter is a plain set of
rules: once created it belongs to the listener, and nothing here is consulted
again. A starter that names a folder the listener does not have finds nothing
and its rule says so ("folder "News", which does not exist").

YouTube rules see saved videos and playlists and followed channels; videos in a
channel's feed are fetched over the network and not kept on disk, so there is
deliberately no "every new upload" starter.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.lineups.conditions import NO, YES, Condition
from quill.core.lineups.refs import KIND_EPISODE, KIND_STATION, KIND_YT_VIDEO
from quill.core.lineups.rules import (
    KEEP_ALWAYS,
    KEEP_FOLLOW,
    KEEP_FOR_DAYS,
    KEEP_UNTIL_DONE,
    KEEP_UNTIL_DONE_OR_DAYS,
    SORT_NEWEST,
    SORT_OLDEST,
    Keep,
    Rule,
    new_rule_id,
)
from quill.core.podcasts.filter_conditions import OP_AT_MOST, OP_CONTAINS, OP_IS


@dataclass(frozen=True, slots=True)
class Example:
    name: str
    summary: str
    rules: tuple[Rule, ...]


def _rule(kind: str, **fields: object) -> Rule:
    return Rule(id=new_rule_id(), kind=kind, **fields)  # type: ignore[arg-type]


UNPLAYED = Condition("played", OP_IS, NO)


def examples() -> tuple[Example, ...]:
    """The starters, with fresh rule ids every time they are asked for."""
    return (
        Example(
            "Morning",
            "Your Morning stations, always, then today's unplayed news.",
            (
                _rule(KIND_STATION, scope=(("folder", ("Morning",)),), keep=Keep(KEEP_ALWAYS)),
                _rule(
                    KIND_EPISODE,
                    scope=(("folder", ("News",)),),
                    tests=(UNPLAYED, Condition("age", OP_AT_MOST, "1")),
                    sort=SORT_NEWEST,
                    keep=Keep(KEEP_UNTIL_DONE_OR_DAYS, days=2),
                ),
            ),
        ),
        Example(
            "New This Week",
            "Unplayed episodes from the last seven days, newest first.",
            (
                _rule(
                    KIND_EPISODE,
                    tests=(UNPLAYED, Condition("age", OP_AT_MOST, "7")),
                    sort=SORT_NEWEST,
                    limit=20,
                    keep=Keep(KEEP_UNTIL_DONE_OR_DAYS, days=7),
                ),
            ),
        ),
        Example(
            "Latest From Each",
            "The newest unplayed episode of every podcast you follow.",
            (
                _rule(
                    KIND_EPISODE,
                    tests=(UNPLAYED,),
                    sort=SORT_NEWEST,
                    per_group=1,
                    keep=Keep(KEEP_FOLLOW),
                ),
            ),
        ),
        Example(
            "Commute",
            "Short unplayed episodes, oldest first, up to 45 minutes.",
            (
                _rule(
                    KIND_EPISODE,
                    tests=(UNPLAYED, Condition("length", OP_AT_MOST, "40")),
                    sort=SORT_OLDEST,
                    budget_minutes=45,
                    keep=Keep(KEEP_UNTIL_DONE),
                ),
            ),
        ),
        Example(
            "Saved YouTube",
            "YouTube videos you saved, each kept for two weeks.",
            (
                _rule(
                    KIND_YT_VIDEO,
                    tests=(Condition("saved", OP_IS, YES),),
                    keep=Keep(KEEP_FOR_DAYS, days=14),
                ),
            ),
        ),
        Example(
            "Live News",
            "Stations tagged news, and saved YouTube streams that are live.",
            (
                _rule(
                    KIND_STATION,
                    tests=(
                        Condition("tags", OP_CONTAINS, "news"),
                        Condition("my_tags", OP_CONTAINS, "news"),
                    ),
                    match="any",
                    keep=Keep(KEEP_FOLLOW),
                ),
                _rule(
                    KIND_YT_VIDEO, tests=(Condition("live", OP_IS, YES),), keep=Keep(KEEP_FOLLOW)
                ),
            ),
        ),
        Example(
            "Finish These",
            "Episodes you started and have not finished.",
            (
                _rule(
                    KIND_EPISODE,
                    tests=(Condition("in_progress", OP_IS, YES),),
                    keep=Keep(KEEP_UNTIL_DONE),
                ),
            ),
        ),
    )


__all__ = ["Example", "examples"]
