"""First run, and the one-shot tips that follow.

Three screens rather than seven, because QUILL Cast has no account, no tracker
and no cloud to explain -- and a first-run flow that pages somebody through
consent they never gave is how people learn to dismiss dialogs unread.

The rules these pin are the ones that decide whether tips are useful or an
irritation: once ever, never for somebody who does not need them, and off in one
place permanently.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.onboarding import (
    FIRST_RUN_SCREENS,
    SCREEN_BODIES,
    SCREEN_TITLES,
    TIPS,
    OnboardingState,
    describe_tips,
    mark_seen,
    needs_first_run,
    remaining_tips,
    reset_tips,
    tip_for,
)
from quill.core.podcasts.subscriptions import PodcastLibrary


def test_three_screens_not_seven_and_each_has_words() -> None:
    assert len(FIRST_RUN_SCREENS) == 3
    for key in FIRST_RUN_SCREENS:
        assert SCREEN_TITLES[key].strip()
        assert len(SCREEN_BODIES[key].split()) > 20


def test_first_run_is_skipped_for_somebody_who_already_has_podcasts() -> None:
    # An imported OPML, a restored backup, an upgrade. Explaining how to add a
    # first podcast to somebody with two hundred says nobody checked.
    state = OnboardingState()
    assert needs_first_run(state, has_shows=False) is True
    assert needs_first_run(state, has_shows=True) is False


def test_first_run_never_repeats() -> None:
    state = OnboardingState(completed_first_run=True)
    assert needs_first_run(state, has_shows=False) is False


def test_a_tip_fires_once_ever() -> None:
    state = OnboardingState()
    said = tip_for(state, "queue_vs_inbox")
    assert said and said.endswith(".")
    mark_seen(state, "queue_vs_inbox")
    # A tip that reappears is an interruption; a tip that appears once is a fact.
    assert tip_for(state, "queue_vs_inbox") == ""


def test_marking_is_separate_from_asking() -> None:
    # So a tip that could not actually be delivered -- the window closed, speech
    # was off -- is not recorded as shown.
    state = OnboardingState()
    assert tip_for(state, "per_show_settings")
    assert tip_for(state, "per_show_settings")  # still available; nothing marked it


def test_tips_switch_off_in_one_place() -> None:
    state = OnboardingState(tips_enabled=False)
    assert all(tip_for(state, tip_id) == "" for tip_id in TIPS)
    assert describe_tips(state) == "Tips are switched off."


def test_an_unknown_tip_id_is_never_invented() -> None:
    state = OnboardingState()
    assert tip_for(state, "no-such-tip") == ""
    mark_seen(state, "no-such-tip")
    assert "no-such-tip" not in state.seen_tips


def test_the_settings_line_says_where_you_stand() -> None:
    state = OnboardingState()
    assert f"{len(TIPS)} tips still to appear" in describe_tips(state)
    for tip_id in TIPS:
        mark_seen(state, tip_id)
    assert remaining_tips(state) == 0
    assert "seen every tip" in describe_tips(state)
    reset_tips(state)
    assert remaining_tips(state) == len(TIPS)


def test_an_id_from_a_newer_build_is_kept_rather_than_dropped() -> None:
    # Forgetting it would show that tip again on the way back to the new build.
    restored = OnboardingState.from_dict(
        OnboardingState(seen_tips={"from_the_future", "queue_vs_inbox"}).to_dict()
    )
    assert "from_the_future" in restored.seen_tips


@pytest.mark.parametrize("junk", [None, [], "nope", 7])
def test_a_broken_stored_record_reads_as_a_fresh_one(junk: object) -> None:
    state = OnboardingState.from_dict(junk)
    assert state.completed_first_run is False
    assert state.tips_enabled is True


def test_the_state_rides_along_with_the_library() -> None:
    library = PodcastLibrary()
    assert library.onboarding.completed_first_run is False
    assert library.onboarding.tips_enabled is True
