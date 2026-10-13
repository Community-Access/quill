"""Rules add, hands decide: every guarantee of ``quill.core.lineups.merge``.

The example tests pin each behaviour by name; the property tests at the end run
the same guarantees over random libraries, rule sets, hand edits and clocks.
"""

from __future__ import annotations

from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from quill.core.lineups.conditions import NO, Condition
from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.merge import DAY_SECONDS, Catalogue, budget_cut, refresh
from quill.core.lineups.model import (
    HELD_ADDED,
    HELD_KEPT,
    NEW_ITEMS_BOTTOM,
    NEW_ITEMS_TOP,
    Lineup,
    Removed,
    Row,
)
from quill.core.lineups.refs import KIND_EPISODE, KIND_STATION, ItemRef, Presence, episode_ref
from quill.core.lineups.rules import (
    KEEP_ALWAYS,
    KEEP_FOLLOW,
    KEEP_FOR_DAYS,
    KEEP_UNTIL_DONE,
    KEEP_UNTIL_DONE_OR_DAYS,
    Keep,
    Rule,
)
from quill.core.podcasts.filter_conditions import OP_IS

NOW = 1_800_000_000.0


def ep(guid: str, *, played: bool = False, minutes: int = 30, heard: float = 0.0) -> ItemFacts:
    return ItemFacts(
        ref=episode_ref("show", guid),
        name=guid,
        facts={"played": played, "folder": "News"},
        length_seconds=minutes * 60,
        finished=played,
        position_fraction=heard,
    )


def st_(key: str, *, folder: str = "Morning") -> ItemFacts:
    return ItemFacts(ref=ItemRef(KIND_STATION, key), name=key, facts={"folder": folder})


def catalogue(*items: ItemFacts, unavailable: tuple[str, ...] = ()) -> Catalogue:
    kinds: dict[str, tuple[ItemFacts, ...] | None] = {KIND_EPISODE: (), KIND_STATION: ()}
    for item in items:
        kinds[item.ref.kind] = (*(kinds[item.ref.kind] or ()), item)
    for kind in unavailable:
        kinds[kind] = None
    return Catalogue(kinds, complete=frozenset({KIND_EPISODE}))


UNPLAYED = (Condition("played", OP_IS, NO),)


def unplayed_rule(keep: Keep, rule_id: str = "r1") -> Rule:
    return Rule(id=rule_id, kind=KIND_EPISODE, tests=UNPLAYED, keep=keep)


def names(lineup: Lineup) -> list[str]:
    return [row.name for row in lineup.rows]


# -- arrivals and the four Keep choices --------------------------------------------


def test_matches_arrive_in_rule_order_and_record_who_claims_them() -> None:
    lineup = Lineup(id="l", name="Morning", rules=(unplayed_rule(Keep(KEEP_FOLLOW)),))
    result = refresh(lineup, catalogue(ep("a"), ep("b"), ep("c", played=True)), NOW)
    assert names(result.lineup) == ["a", "b"]
    assert all(row.claims == {"r1": NOW} for row in result.lineup.rows)
    assert [ref.key.split("\t")[1] for ref in result.added] == ["a", "b"]


def test_while_it_matches_lets_go_when_it_stops_matching() -> None:
    lineup = refresh(
        Lineup(id="l", name="M", rules=(unplayed_rule(Keep(KEEP_FOLLOW)),)), catalogue(ep("a")), NOW
    ).lineup
    result = refresh(lineup, catalogue(ep("a", played=True)), NOW + 60)
    assert names(result.lineup) == []
    assert result.left[0].reason == "it no longer matches rule 1"
    assert result.lineup.recently_left[0].name == "a"


def test_until_finished_stays_after_it_stops_matching_and_goes_once_heard() -> None:
    rule = Rule(
        id="r1",
        kind=KIND_EPISODE,
        tests=(Condition("folder", OP_IS, "News"),),
        keep=Keep(KEEP_UNTIL_DONE),
    )
    lineup = refresh(Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a")), NOW).lineup
    moved_folder = replace(ep("a"), facts={"played": False, "folder": "Elsewhere"})
    assert names(refresh(lineup, catalogue(moved_folder), NOW + 60).lineup) == ["a"]
    almost = refresh(lineup, catalogue(ep("a", heard=0.94)), NOW + 60).lineup
    assert names(almost) == ["a"]
    done = refresh(lineup, catalogue(ep("a", heard=0.96)), NOW + 60)
    assert names(done.lineup) == [] and done.left[0].reason == "finished"


def test_for_days_is_measured_from_the_claim_not_counted_in_refreshes() -> None:
    rule = unplayed_rule(Keep(KEEP_FOR_DAYS, days=3))
    lineup = refresh(Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a")), NOW).lineup
    for hours in (1, 24, 48, 71):
        lineup = refresh(lineup, catalogue(ep("a")), NOW + hours * 3600).lineup
        assert names(lineup) == ["a"]
    result = refresh(lineup, catalogue(ep("a")), NOW + 3 * DAY_SECONDS)
    assert names(result.lineup) == [] and result.left[0].reason == "3 days passed"


def test_an_item_let_go_while_still_matching_does_not_come_straight_back() -> None:
    rule = unplayed_rule(Keep(KEEP_FOR_DAYS, days=1))
    lineup = refresh(Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a")), NOW).lineup
    lineup = refresh(lineup, catalogue(ep("a")), NOW + DAY_SECONDS).lineup
    assert names(lineup) == []
    # Still in the feed and still unplayed the next day: it stays gone ...
    assert names(refresh(lineup, catalogue(ep("a")), NOW + 2 * DAY_SECONDS).lineup) == []
    # ... until the rule stops matching it, after which a new match is a new arrival.
    lineup = refresh(lineup, catalogue(ep("a", played=True)), NOW + 3 * DAY_SECONDS).lineup
    assert names(refresh(lineup, catalogue(ep("a")), NOW + 4 * DAY_SECONDS).lineup) == ["a"]


def test_until_finished_or_days_goes_at_whichever_comes_first() -> None:
    rule = unplayed_rule(Keep(KEEP_UNTIL_DONE_OR_DAYS, days=7))
    lineup = refresh(
        Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a"), ep("b")), NOW
    ).lineup
    later = refresh(lineup, catalogue(ep("a", heard=1.0), ep("b")), NOW + DAY_SECONDS)
    assert names(later.lineup) == ["b"] and later.left[0].reason == "finished"
    week = refresh(later.lineup, catalogue(ep("b")), NOW + 8 * DAY_SECONDS)
    assert week.left[0].reason == "7 days passed"


def test_always_never_lets_go_even_when_the_item_is_missing() -> None:
    rule = Rule(id="r1", kind=KIND_EPISODE, keep=Keep(KEEP_ALWAYS))
    lineup = refresh(Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a")), NOW).lineup
    gone = refresh(lineup, catalogue(), NOW + 60)
    assert names(gone.lineup) == ["a"]
    assert (
        Catalogue({KIND_EPISODE: ()}, frozenset({KIND_EPISODE})).lookup(lineup.rows[0].ref)[0]
        is Presence.MISSING
    )


def test_a_missing_item_leaves_a_non_always_rule_and_says_so() -> None:
    lineup = refresh(
        Lineup(id="l", name="M", rules=(unplayed_rule(Keep(KEEP_UNTIL_DONE)),)),
        catalogue(ep("a")),
        NOW,
    ).lineup
    result = refresh(lineup, catalogue(), NOW + 60)
    assert names(result.lineup) == [] and result.left[0].reason == "it no longer exists"


# -- the listener's hands -----------------------------------------------------------


def test_kept_and_added_rows_never_leave_and_removed_never_return() -> None:
    rule = unplayed_rule(Keep(KEEP_FOLLOW))
    lineup = refresh(
        Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a"), ep("b")), NOW
    ).lineup
    a, b = lineup.rows
    lineup = replace(
        lineup,
        rows=(
            replace(a, held=HELD_KEPT),
            Row(ref=ItemRef(KIND_STATION, "x"), name="x", held=HELD_ADDED),
        ),
        removed=(Removed(b.ref, "b", NOW),),
    )
    result = refresh(lineup, catalogue(ep("a", played=True), ep("b")), NOW + 60)
    assert names(result.lineup) == ["a", "x"]
    assert not result.added


def test_two_rules_claiming_one_item_it_stays_while_either_holds_it() -> None:
    follow = unplayed_rule(Keep(KEEP_FOLLOW), "r1")
    always = Rule(id="r2", kind=KIND_EPISODE, keep=Keep(KEEP_ALWAYS))
    lineup = refresh(
        Lineup(id="l", name="M", rules=(follow, always)), catalogue(ep("a")), NOW
    ).lineup
    assert lineup.rows[0].claims == {"r1": NOW, "r2": NOW}  # both, in one refresh
    after = refresh(lineup, catalogue(ep("a", played=True)), NOW + 60).lineup
    assert names(after) == ["a"] and set(after.rows[0].claims) == {"r2"}


# -- what can never happen ------------------------------------------------------------


def test_nothing_leaves_because_its_owner_could_not_be_read() -> None:
    rule = unplayed_rule(Keep(KEEP_FOLLOW))
    lineup = refresh(Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a")), NOW).lineup
    result = refresh(lineup, catalogue(unavailable=(KIND_EPISODE,)), NOW + 10 * DAY_SECONDS)
    assert names(result.lineup) == ["a"] and not result.left


def test_refresh_never_reorders_survivors() -> None:
    rule = Rule(id="r1", kind=KIND_STATION, keep=Keep(KEEP_FOLLOW))
    lineup = refresh(
        Lineup(id="l", name="M", rules=(rule,)), catalogue(st_("a"), st_("b"), st_("c")), NOW
    ).lineup
    lineup = replace(
        lineup, rows=(lineup.rows[2], lineup.rows[0], lineup.rows[1])
    )  # the listener's order
    again = refresh(lineup, catalogue(st_("a"), st_("b"), st_("c"), st_("d")), NOW + 60).lineup
    assert names(again) == ["c", "a", "b", "d"]


def test_new_items_go_with_their_rule_or_at_the_top_or_bottom() -> None:
    stations = Rule(id="r1", kind=KIND_STATION, keep=Keep(KEEP_ALWAYS))
    episodes = unplayed_rule(Keep(KEEP_FOLLOW), "r2")
    lineup = refresh(
        Lineup(id="l", name="M", rules=(stations, episodes)), catalogue(st_("s1"), ep("e1")), NOW
    ).lineup
    assert names(lineup) == ["s1", "e1"]
    grown = catalogue(st_("s1"), st_("s2"), ep("e1"), ep("e2"))
    assert names(refresh(lineup, grown, NOW + 1).lineup) == ["s1", "s2", "e1", "e2"]
    assert names(refresh(replace(lineup, new_items=NEW_ITEMS_TOP), grown, NOW + 1).lineup) == [
        "s2",
        "e2",
        "s1",
        "e1",
    ]
    assert names(refresh(replace(lineup, new_items=NEW_ITEMS_BOTTOM), grown, NOW + 1).lineup) == [
        "s1",
        "e1",
        "s2",
        "e2",
    ]


def test_a_cap_keeps_the_newest_claims_and_remembers_what_it_let_go() -> None:
    rule = unplayed_rule(Keep(KEEP_ALWAYS, max_kept=2))
    lineup = refresh(
        Lineup(id="l", name="M", rules=(rule,)), catalogue(ep("a"), ep("b")), NOW
    ).lineup
    result = refresh(lineup, catalogue(ep("a"), ep("b"), ep("c")), NOW + 60)
    assert names(result.lineup) == ["b", "c"] or names(result.lineup) == ["a", "c"]
    assert result.left and result.left[0].reason == "rule 1 keeps at most 2"
    again = refresh(result.lineup, catalogue(ep("a"), ep("b"), ep("c")), NOW + 120)
    assert names(again.lineup) == names(result.lineup) and not again.left


def test_a_big_loss_is_reported() -> None:
    rule = unplayed_rule(Keep(KEEP_FOLLOW))
    many = [ep(str(i)) for i in range(20)]
    lineup = refresh(Lineup(id="l", name="M", rules=(rule,)), catalogue(*many), NOW).lineup
    result = refresh(lineup, catalogue(*[ep(str(i), played=True) for i in range(20)]), NOW + 60)
    assert result.big_loss and len(result.left) == 20


def test_budget_never_leaves_out_a_row_somebody_placed() -> None:
    a, b, c = (Row(ref=ItemRef(KIND_STATION, k), name=k, claims={"r": NOW}) for k in "abc")
    lineup = Lineup(id="l", name="M", rows=(a, b, replace(c, moved=True)), budget_minutes=40)
    lengths = {a.ref: 20 * 60, b.ref: 20 * 60, c.ref: 20 * 60}
    assert budget_cut(lineup, lengths) == {b.ref}


# -- properties -------------------------------------------------------------------------

keys = st.sampled_from([f"g{i}" for i in range(8)])
facts = st.builds(
    lambda guid, played, heard: ep(guid, played=played, heard=heard),
    keys,
    st.booleans(),
    st.sampled_from([0.0, 0.5, 1.0]),
)
libraries = st.lists(facts, max_size=8, unique_by=lambda item: item.ref)
keeps = st.builds(
    Keep,
    st.sampled_from([
        KEEP_FOLLOW,
        KEEP_UNTIL_DONE,
        KEEP_FOR_DAYS,
        KEEP_UNTIL_DONE_OR_DAYS,
        KEEP_ALWAYS,
    ]),
    st.integers(1, 3),
    st.just(95),
    st.sampled_from([0, 0, 2, 4]),
)
rule_sets = st.lists(keeps, min_size=1, max_size=3).map(
    lambda ks: tuple(
        Rule(id=f"r{i}", kind=KIND_EPISODE, tests=UNPLAYED if i % 2 == 0 else (), keep=k)
        for i, k in enumerate(ks)
    )
)
steps = st.lists(st.tuples(libraries, st.integers(0, 2 * DAY_SECONDS)), min_size=1, max_size=5)


@settings(max_examples=150, deadline=None)
@given(rule_sets, steps, st.sampled_from([None, "keep", "remove"]))
def test_the_guarantees_hold_over_random_histories(rules, history, hand) -> None:
    lineup = Lineup(id="l", name="M", rules=rules)
    clock = NOW
    held: set[ItemRef] = set()
    removed: set[ItemRef] = set()
    for library, elapsed in history:
        clock += elapsed
        before = lineup
        result = refresh(lineup, catalogue(*library), clock)
        after = result.lineup
        # 3: a removed item never returns
        assert not removed & {row.ref for row in after.rows}
        # 4: a kept item never leaves
        assert held <= {row.ref for row in after.rows}
        # 5: survivors keep their relative order
        surviving = [row.ref for row in before.rows if row.ref in {r.ref for r in after.rows}]
        assert [row.ref for row in after.rows if row.ref in set(surviving)] == surviving
        # 2: everything that left is recorded with a reason
        left = {row.ref for row in before.rows} - {row.ref for row in after.rows}
        assert left == {departure.ref for departure in result.left}
        assert all(departure.reason for departure in result.left)
        # 6: idempotent
        twice = refresh(after, catalogue(*library), clock)
        assert [r.ref for r in twice.lineup.rows] == [r.ref for r in after.rows]
        assert [r.claims for r in twice.lineup.rows] == [r.claims for r in after.rows]
        assert not twice.added and not twice.left
        # one row per item, always
        assert len({row.ref for row in after.rows}) == len(after.rows)
        lineup = after
        if hand and lineup.rows:
            first = lineup.rows[0]
            if hand == "keep":
                held.add(first.ref)
                lineup = replace(lineup, rows=(replace(first, held=HELD_KEPT), *lineup.rows[1:]))
            else:
                removed.add(first.ref)
                held.discard(first.ref)
                lineup = replace(
                    lineup,
                    rows=lineup.rows[1:],
                    removed=(Removed(first.ref, first.name, clock), *lineup.removed),
                )


@settings(max_examples=100, deadline=None)
@given(rule_sets, libraries, st.integers(0, 30 * DAY_SECONDS))
def test_an_unreadable_owner_never_costs_a_row(rules, library, elapsed) -> None:
    lineup = refresh(Lineup(id="l", name="M", rules=rules), catalogue(*library), NOW).lineup
    result = refresh(lineup, catalogue(unavailable=(KIND_EPISODE,)), NOW + elapsed)
    assert [row.ref for row in result.lineup.rows] == [row.ref for row in lineup.rows]
    assert not result.left
