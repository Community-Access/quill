"""Rules decide what comes in: scope, tests, order, limits -- and their sentences."""

from __future__ import annotations

from quill.core.lineups.conditions import NO, YES, Condition, describe, matches, ops_for
from quill.core.lineups.describe import keep_phrase, rule_sentence
from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.refs import (
    KIND_EPISODE,
    KIND_STATION,
    ItemRef,
    episode_ref,
)
from quill.core.lineups.rules import (
    KEEP_ALWAYS,
    KEEP_FOLLOW,
    KEEP_FOR_DAYS,
    KEEP_UNTIL_DONE,
    KEEP_UNTIL_DONE_OR_DAYS,
    MATCH_ANY,
    SORT_NEWEST,
    SORT_SHORTEST,
    Keep,
    Rule,
    default_keep,
    evaluate,
    new_rule,
    with_scope,
)
from quill.core.podcasts.filter_conditions import (
    OP_AT_LEAST,
    OP_AT_MOST,
    OP_CONTAINS,
    OP_IS,
    OP_IS_NOT,
    OP_NOT_CONTAINS,
    OP_REGEX,
    OP_WILDCARD,
)


def episode(guid: str, *, show="Daily", folder="News", minutes=30, age=0, played=False, at=0.0):
    return ItemFacts(
        ref=episode_ref("s-" + show, guid),
        name=f"Episode {guid}",
        facts={
            "show": show,
            "folder": folder,
            "age": age,
            "played": played,
            "labels": ("morning",),
        },
        length_seconds=minutes * 60,
        source=show,
        finished=played,
        published_at=at,
    )


def station(key: str, *, folder="Morning", tags=("news",)):
    return ItemFacts(
        ref=ItemRef(KIND_STATION, key),
        name=f"Station {key}",
        facts={"folder": folder, "tags": tags, "favorite": True},
    )


# -- conditions -------------------------------------------------------------------


def test_a_missing_number_never_matches_a_number_test() -> None:
    unknown = ItemFacts(ref=episode_ref("s", "g"), name="x", facts={"age": None})
    assert not matches(Condition("age", OP_AT_MOST, "10"), unknown)
    assert not matches(Condition("length", OP_AT_MOST, "10"), unknown)  # length 0 = unknown


def test_text_number_yesno_and_list_tests() -> None:
    item = episode("1", minutes=12, age=3, played=False)
    assert matches(Condition("name", OP_CONTAINS, "episode"), item)
    assert matches(Condition("length", OP_AT_MOST, "12"), item)
    assert not matches(Condition("length", OP_AT_LEAST, "13"), item)
    assert matches(Condition("played", OP_IS, NO), item)
    assert not matches(Condition("played", OP_IS, YES), item)
    assert matches(Condition("labels", OP_IS, "Morning"), item)
    assert matches(Condition("labels", OP_NOT_CONTAINS, "evening"), item)
    assert not matches(Condition("labels", OP_IS_NOT, "morning"), item)
    assert matches(Condition("name", OP_WILDCARD, "Episode ?"), item)
    assert matches(Condition("name", OP_REGEX, r"^Episode \d$"), item)


def test_an_unusable_test_matches_nothing_and_says_why() -> None:
    item = episode("1")
    bad_regex = Condition("name", OP_REGEX, "(")
    assert not matches(bad_regex, item)
    assert "cannot be used" in describe(bad_regex, KIND_EPISODE)
    unknown_field = Condition("colour", OP_CONTAINS, "red")
    assert not unknown_field.is_usable(KIND_EPISODE)
    no_number = Condition("age", OP_AT_MOST, "soon")
    assert "whole number of days" in no_number.error(KIND_EPISODE)


def test_ops_follow_the_field_type() -> None:
    assert OP_AT_LEAST in ops_for(KIND_EPISODE, "length")
    assert OP_REGEX not in ops_for(KIND_EPISODE, "played")
    assert ops_for(KIND_EPISODE, "nope") == ()


def test_conditions_round_trip_and_keep_the_unknown() -> None:
    raw = {"field": "future_field", "op": "future_op", "value": "x"}
    kept = Condition.from_dict(raw)
    assert kept is not None and kept.to_dict() == raw
    assert not kept.is_usable(KIND_EPISODE)


# -- rules ---------------------------------------------------------------------------


def test_scope_is_anded_with_tests_and_values_are_ored() -> None:
    rule = with_scope(new_rule(KIND_EPISODE), "folder", ["News", "Tech"])
    rule = Rule(**{**_fields(rule), "tests": (Condition("played", OP_IS, NO),)})
    items = [
        episode("a", folder="News"),
        episode("b", folder="Tech"),
        episode("c", folder="Comedy"),
        episode("d", folder="News", played=True),
    ]
    assert [i.ref.key.split("\t")[1] for i in evaluate(rule, items)] == ["a", "b"]


def test_match_any_with_no_tests_is_not_everything_by_accident() -> None:
    rule = Rule(id="r", kind=KIND_EPISODE, match=MATCH_ANY)
    assert len(evaluate(rule, [episode("a"), episode("b")])) == 2  # no tests: the scope decides
    rule = Rule(
        id="r",
        kind=KIND_EPISODE,
        match=MATCH_ANY,
        tests=(Condition("length", OP_AT_MOST, "5"), Condition("name", OP_CONTAINS, "zzz")),
    )
    assert evaluate(rule, [episode("a", minutes=30)]) == []


def test_sort_then_per_group_then_budget_then_limit() -> None:
    items = [
        episode("1", show="A", minutes=10, at=1),
        episode("2", show="A", minutes=10, at=3),
        episode("3", show="A", minutes=10, at=2),
        episode("4", show="B", minutes=50, at=4),
    ]
    rule = Rule(id="r", kind=KIND_EPISODE, sort=SORT_NEWEST, per_group=2)
    assert [i.name for i in evaluate(rule, items)] == ["Episode 4", "Episode 2", "Episode 3"]
    budget = Rule(id="r", kind=KIND_EPISODE, sort=SORT_SHORTEST, budget_minutes=25)
    assert len(evaluate(budget, items)) == 2
    limited = Rule(id="r", kind=KIND_EPISODE, sort=SORT_NEWEST, limit=1)
    assert [i.name for i in evaluate(limited, items)] == ["Episode 4"]


def test_a_rule_only_sees_its_own_kind_and_a_disabled_rule_sees_nothing() -> None:
    rule = Rule(id="r", kind=KIND_STATION)
    assert [i.ref.key for i in evaluate(rule, [episode("x"), station("s1")])] == ["s1"]
    assert evaluate(Rule(id="r", kind=KIND_STATION, enabled=False), [station("s1")]) == []


def test_rules_round_trip() -> None:
    rule = Rule(
        id="r1",
        kind=KIND_EPISODE,
        scope=(("folder", ("News",)),),
        tests=(Condition("played", OP_IS, NO),),
        sort=SORT_NEWEST,
        limit=10,
        per_group=2,
        budget_minutes=45,
        keep=Keep(KEEP_UNTIL_DONE_OR_DAYS, days=3, max_kept=20),
    )
    assert Rule.from_dict(rule.to_dict()) == rule


def test_an_unknown_keep_mode_reads_as_always_never_as_letting_go() -> None:
    assert Keep.from_dict({"mode": "something_newer"}).mode == KEEP_ALWAYS


def test_until_finished_on_a_station_means_while_it_matches() -> None:
    assert Keep(KEEP_UNTIL_DONE).effective(KIND_STATION).mode == KEEP_FOLLOW
    assert Keep(KEEP_UNTIL_DONE_OR_DAYS, days=2).effective(KIND_STATION).mode == KEEP_FOR_DAYS
    assert Keep(KEEP_UNTIL_DONE).effective(KIND_EPISODE).mode == KEEP_UNTIL_DONE


def test_defaults_follow_the_kind() -> None:
    assert default_keep(KIND_EPISODE).mode == KEEP_UNTIL_DONE_OR_DAYS
    assert default_keep(KIND_STATION).mode == KEEP_FOLLOW


# -- sentences ------------------------------------------------------------------------


def test_every_rule_reads_back_as_one_sentence_including_when_things_go() -> None:
    rule = Rule(
        id="r",
        kind=KIND_EPISODE,
        scope=(("folder", ("News",)),),
        tests=(Condition("played", OP_IS, NO), Condition("age", OP_AT_MOST, "1")),
        sort=SORT_NEWEST,
        limit=10,
        keep=Keep(KEEP_UNTIL_DONE),
    )
    text = rule_sentence(rule, finds=7)
    assert text.startswith(
        'Podcast episodes in folder "News", where Played is no and Age is at most 1 day'
    )
    assert "newest first, no more than 10 items." in text
    assert text.endswith("They go once finished. Finds 7 now.")
    assert keep_phrase(Keep(KEEP_ALWAYS), KIND_STATION) == "They always stay."
    assert keep_phrase(Keep(KEEP_FOR_DAYS, days=1), KIND_STATION) == "They stay 1 day."


def _fields(rule: Rule) -> dict[str, object]:
    return {name: getattr(rule, name) for name in Rule.__dataclass_fields__}
