"""Episode Filter rules, widened: more tests, any-one-of, and "like this one".

The original rule asked two things -- the title, and a minimum length. These
tests pin what a rule can now also ask (show notes, people, type, a maximum
length, age, season and number, by words, wildcard or regular expression), the
three safety rules that carry over (a missing fact never matches a number test,
an unusable test makes its rule match nothing, nothing raises), the storage
contract with older builds, and the suggestion behind Filter Episodes Like This.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from quill.core.podcasts import episode_filters as filters
from quill.core.podcasts.filter_conditions import (
    FIELD_AGE,
    FIELD_DURATION,
    FIELD_NOTES,
    FIELD_NUMBER,
    FIELD_PEOPLE,
    FIELD_SEASON,
    FIELD_TITLE,
    FIELD_TYPE,
    OP_AT_LEAST,
    OP_AT_MOST,
    OP_CONTAINS,
    OP_ENDS,
    OP_IS,
    OP_IS_NOT,
    OP_NOT_CONTAINS,
    OP_NOT_REGEX,
    OP_REGEX,
    OP_STARTS,
    OP_WILDCARD,
    FilterCondition,
    condition_matches,
    describe_condition,
)
from quill.core.podcasts.filter_suggestions import describe_trial, suggest_rule
from quill.core.podcasts.models import PodcastEpisode
from quill.core.podcasts.models_filters import (
    MODE_FILTER_MATCHING,
    PATTERN_NONE,
    PATTERN_WILDCARD,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
)
from quill.core.podcasts.namespace_tags import NamespaceTags, Person

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _ep(
    title: str = "An Episode",
    *,
    minutes: int = 30,
    notes: str = "",
    kind: str = "",
    published: str = "Mon, 28 Sep 2026 10:00:00 +0000",
    season: int = 0,
    number: int = 0,
    people: tuple[str, ...] = (),
) -> PodcastEpisode:
    return PodcastEpisode(
        guid=title,
        title=title,
        audio_url=f"https://example.test/{title}.mp3",
        published=published,
        duration_seconds=minutes * 60,
        description=notes,
        episode_type=kind,
        season=season,
        episode_number=number,
        tags=NamespaceTags(people=[Person(name=name) for name in people]),
    )


def _rule(*conditions: FilterCondition, match_any: bool = False, **kw: object) -> EpisodeFilterRule:
    return EpisodeFilterRule(
        name="R",
        pattern_kind=str(kw.pop("pattern_kind", PATTERN_NONE)),
        pattern=str(kw.pop("pattern", "")),
        min_duration_minutes=int(kw.pop("minutes", 0)),  # type: ignore[call-overload]
        conditions=list(conditions),
        match_any=match_any,
    )


# -- text tests ------------------------------------------------------------------


def test_show_notes_are_searched_by_words_case_insensitively() -> None:
    sponsor = FilterCondition(FIELD_NOTES, OP_CONTAINS, "Sponsored by")
    assert condition_matches(sponsor, _ep(notes="This episode is SPONSORED BY Acme."))
    assert not condition_matches(sponsor, _ep(notes="An interview."))
    exact = FilterCondition(FIELD_NOTES, OP_CONTAINS, "Sponsored by", case_sensitive=True)
    assert not condition_matches(exact, _ep(notes="SPONSORED BY Acme"))


def test_does_not_contain_holds_for_empty_notes() -> None:
    # Notes that say nothing do not contain the word; that is a fact, not a gap.
    assert condition_matches(FilterCondition(FIELD_NOTES, OP_NOT_CONTAINS, "rerun"), _ep(notes=""))


@pytest.mark.parametrize(
    ("op", "value", "title", "expected"),
    [
        (OP_STARTS, "daily briefing:", "Daily Briefing: Tuesday", True),
        (OP_ENDS, "(rerun)", "Old Favourite (Rerun)", True),
        (OP_IS, "trailer", "Trailer", True),
        (OP_IS_NOT, "trailer", "Trailer", False),
        (OP_WILDCARD, "Q+A*", "Q+A with Jane", True),
        (OP_WILDCARD, "Q+A*", "A Q+A with Jane", False),  # wildcards cover the whole title
    ],
)
def test_title_tests(op: str, value: str, title: str, expected: bool) -> None:
    assert condition_matches(FilterCondition(FIELD_TITLE, op, value), _ep(title)) is expected


def test_a_regular_expression_is_found_anywhere_unless_anchored() -> None:
    found = FilterCondition(FIELD_TITLE, OP_REGEX, r"\bpart \d+\b")
    assert condition_matches(found, _ep("The Long Story, Part 3 of 5"))
    anchored = FilterCondition(FIELD_TITLE, OP_REGEX, r"^part \d+$")
    assert not condition_matches(anchored, _ep("The Long Story, Part 3 of 5"))
    negated = FilterCondition(FIELD_TITLE, OP_NOT_REGEX, r"\bpart \d+\b")
    assert condition_matches(negated, _ep("A standalone episode"))


def test_a_regular_expression_that_cannot_compile_is_unusable_and_says_why() -> None:
    broken = FilterCondition(FIELD_NOTES, OP_REGEX, "(unclosed")
    assert broken.error.startswith("its regular expression cannot be read")
    assert not condition_matches(broken, _ep(notes="(unclosed"))
    rule = _rule(broken)
    assert not rule.is_usable
    assert "not usable" in rule.pattern_error


def test_people_tests_ask_about_any_one_person() -> None:
    guests = _ep(people=("Jane Doe", "Sam Roe"))
    assert condition_matches(FilterCondition(FIELD_PEOPLE, OP_IS, "sam roe"), guests)
    assert condition_matches(FilterCondition(FIELD_PEOPLE, OP_CONTAINS, "Doe"), guests)
    assert not condition_matches(FilterCondition(FIELD_PEOPLE, OP_IS, "Sam"), guests)
    assert condition_matches(FilterCondition(FIELD_PEOPLE, OP_IS_NOT, "Pat Poe"), guests)


# -- type and numbers ---------------------------------------------------------------


def test_an_episode_with_no_type_is_a_full_episode() -> None:
    assert condition_matches(FilterCondition(FIELD_TYPE, OP_IS, "full"), _ep(kind=""))
    assert condition_matches(FilterCondition(FIELD_TYPE, OP_IS, "trailer"), _ep(kind="Trailer"))
    assert condition_matches(FilterCondition(FIELD_TYPE, OP_IS_NOT, "bonus"), _ep(kind="trailer"))
    assert FilterCondition(FIELD_TYPE, OP_IS, "teaser").error


def test_a_maximum_length_finally_exists() -> None:
    short = FilterCondition(FIELD_DURATION, OP_AT_MOST, "5")
    assert condition_matches(short, _ep(minutes=3))
    assert not condition_matches(short, _ep(minutes=45))


@pytest.mark.parametrize(
    "condition",
    [
        FilterCondition(FIELD_DURATION, OP_AT_MOST, "5"),
        FilterCondition(FIELD_AGE, OP_AT_LEAST, "0"),
        FilterCondition(FIELD_SEASON, OP_IS_NOT, "2"),
        FilterCondition(FIELD_NUMBER, OP_AT_MOST, "100"),
    ],
)
def test_a_missing_fact_never_matches_a_number_test(condition: FilterCondition) -> None:
    unknown = _ep(minutes=0, published="", season=0, number=0)
    assert not condition_matches(condition, unknown, now=NOW)


def test_age_is_counted_in_days_from_the_published_date() -> None:
    old = FilterCondition(FIELD_AGE, OP_AT_LEAST, "30")
    assert condition_matches(old, _ep(published="Mon, 01 Jun 2026 10:00:00 +0000"), now=NOW)
    assert not condition_matches(old, _ep(published="Mon, 28 Sep 2026 10:00:00 +0000"), now=NOW)
    assert not condition_matches(old, _ep(published="not a date"), now=NOW)


def test_season_and_number_compare_as_numbers() -> None:
    assert condition_matches(FilterCondition(FIELD_SEASON, OP_IS, "2"), _ep(season=2))
    assert condition_matches(FilterCondition(FIELD_NUMBER, OP_AT_LEAST, "10"), _ep(number=12))
    assert FilterCondition(FIELD_NUMBER, OP_AT_LEAST, "ten").error
    assert FilterCondition(FIELD_SEASON, OP_CONTAINS, "2").error  # no text test on a number


def test_an_unknown_field_from_a_newer_build_is_unusable_not_dropped() -> None:
    stored = {"field": "mood", "op": "is", "value": "sad"}
    condition = FilterCondition.from_dict(stored)
    assert condition is not None and not condition.is_usable
    assert not _rule(condition).is_usable  # the rule matches nothing rather than more


# -- rules: all or any ----------------------------------------------------------------


def test_every_test_has_to_hold_by_default() -> None:
    rule = _rule(
        FilterCondition(FIELD_TYPE, OP_IS, "bonus"),
        pattern_kind=PATTERN_WILDCARD,
        pattern="*members*",
    )
    assert filters.rule_matches(rule, _ep("For members only", kind="bonus"))
    assert not filters.rule_matches(rule, _ep("For members only"))


def test_any_one_test_is_enough_when_the_rule_says_so() -> None:
    rule = _rule(
        FilterCondition(FIELD_TYPE, OP_IS, "trailer"),
        FilterCondition(FIELD_DURATION, OP_AT_MOST, "5"),
        match_any=True,
    )
    assert filters.rule_matches(rule, _ep("New Season Soon", kind="trailer", minutes=40))
    assert filters.rule_matches(rule, _ep("Quick Update", minutes=2))
    assert not filters.rule_matches(rule, _ep("The Main Show", minutes=50))


def test_a_rule_with_only_tests_is_usable_and_filters() -> None:
    config = EpisodeFilterConfiguration(
        enabled=True,
        mode=MODE_FILTER_MATCHING,
        rules=[_rule(FilterCondition(FIELD_NOTES, OP_CONTAINS, "rerun"))],
    )
    assert config.is_active
    kept, dropped = filters.partition(config, [_ep("A", notes="A rerun."), _ep("B")])
    assert [e.title for e in kept] == ["B"] and [e.title for e in dropped] == ["A"]


def test_a_maximum_length_test_meets_the_duration_save_gate() -> None:
    config = EpisodeFilterConfiguration(
        enabled=True, rules=[_rule(FilterCondition(FIELD_DURATION, OP_AT_MOST, "5"))]
    )
    blocked = filters.assess_save(config, [_ep("A", minutes=0), _ep("B", minutes=0)])
    assert "duration" in blocked.blocked


# -- storage ------------------------------------------------------------------------


def test_a_filter_without_new_tests_is_still_written_as_version_one() -> None:
    # So every earlier build keeps reading a filter made the old way.
    config = EpisodeFilterConfiguration(
        enabled=True, rules=[EpisodeFilterRule(name="A", pattern="*bonus*")]
    )
    stored = config.to_dict()
    assert stored["version"] == 1
    assert "conditions" not in stored["rules"][0]  # type: ignore[index]
    assert "match_any" not in stored["rules"][0]  # type: ignore[index]


def test_a_filter_with_new_tests_round_trips_as_version_two() -> None:
    config = EpisodeFilterConfiguration(
        enabled=True,
        rules=[
            _rule(
                FilterCondition(FIELD_NOTES, OP_REGEX, r"sponsor(ed)?", case_sensitive=True),
                FilterCondition(FIELD_TYPE, OP_IS, "bonus"),
                match_any=True,
            )
        ],
    )
    stored = config.to_dict()
    assert stored["version"] == 2
    restored = EpisodeFilterConfiguration.from_dict(stored)
    assert restored is not None
    rule = restored.rules[0]
    assert rule.match_any and len(rule.conditions) == 2
    assert rule.conditions[0] == FilterCondition(FIELD_NOTES, OP_REGEX, r"sponsor(ed)?", True)
    copied = restored.copy()
    assert copied.rules[0].conditions == rule.conditions and copied.rules[0].match_any


# -- speech -------------------------------------------------------------------------


def test_a_rule_with_several_tests_says_whether_all_or_any() -> None:
    rule = _rule(
        FilterCondition(FIELD_TYPE, OP_IS, "trailer"),
        FilterCondition(FIELD_NOTES, OP_CONTAINS, "sponsor"),
        match_any=True,
    )
    said = filters.describe_rule(rule)
    assert said.startswith("R, enabled. Any one of:")
    assert "Episode type is a trailer." in said
    assert 'Show notes contains "sponsor".' in said
    assert describe_condition(FilterCondition(FIELD_DURATION, OP_AT_MOST, "5")) == (
        "Length in minutes is at most 5"
    )


# -- Filter Episodes Like This --------------------------------------------------------


def test_a_trailer_suggests_the_publishers_own_word() -> None:
    trailer = _ep("Season Two Is Coming", kind="trailer")
    others = [trailer, _ep("Episode 1"), _ep("Episode 2"), _ep("Old Trailer", kind="trailer")]
    suggestion = suggest_rule(trailer, others)
    assert suggestion.rule.name == "Trailers"
    assert suggestion.rule.conditions == [FilterCondition(FIELD_TYPE, OP_IS, "trailer")]
    assert suggestion.matches == 2 and suggestion.sample == 4
    assert "2 of the 4 newest" in suggestion.reason


def test_a_series_name_before_a_colon_is_found_and_counted() -> None:
    episodes = [
        _ep("Daily Briefing: Monday", minutes=3),
        _ep("Daily Briefing: Tuesday", minutes=3),
        _ep("The Big Interview", minutes=60),
        _ep("Daily Briefing: Wednesday", minutes=3),
    ]
    suggestion = suggest_rule(episodes[1], episodes)
    assert suggestion.rule.conditions == [
        FilterCondition(FIELD_TITLE, OP_STARTS, "Daily Briefing:")
    ]
    assert suggestion.matches == 3
    assert filters.rule_matches(suggestion.rule, episodes[0])
    assert not filters.rule_matches(suggestion.rule, episodes[2])


def test_a_much_shorter_episode_suggests_a_length_ceiling() -> None:
    episodes = [_ep(f"Show {n}", minutes=60) for n in range(5)] + [_ep("Quick note", minutes=2)]
    suggestion = suggest_rule(episodes[-1], episodes)
    assert suggestion.rule.conditions[0].field == FIELD_DURATION
    assert suggestion.rule.conditions[0].op == OP_AT_MOST
    assert suggestion.matches == 1


def test_a_one_off_falls_back_to_its_exact_title_and_says_so() -> None:
    episodes = [_ep("Alpha"), _ep("Bravo"), _ep("Charlie")]
    suggestion = suggest_rule(episodes[0], episodes)
    assert suggestion.rule.conditions == [FilterCondition(FIELD_TITLE, OP_IS, "Alpha")]
    assert "Widen it in the editor" in suggestion.reason


def test_a_suggestion_that_would_take_every_episode_is_not_offered() -> None:
    episodes = [_ep("News: One"), _ep("News: Two"), _ep("News: Three")]
    suggestion = suggest_rule(episodes[0], episodes)
    assert suggestion.matches < suggestion.sample


def test_try_it_counts_and_names_what_a_rule_catches() -> None:
    episodes = [_ep(f"Bonus {n}") for n in range(7)] + [_ep("Main")]
    rule = _rule(FilterCondition(FIELD_TITLE, OP_STARTS, "Bonus"))
    said = describe_trial(rule, episodes, filters.rule_matches)
    assert said.startswith("Matches 7 of the 8 newest episodes.")
    assert said.endswith("; and 2 more.")
    empty = describe_trial(_rule(), episodes, filters.rule_matches)
    assert empty.startswith("This rule cannot match anything yet")
