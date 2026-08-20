"""Quill Radio's first minute, and the tips that follow it.

The gap: a new listener got an empty favorites tree and no answer to *where are
the stations, how do I play one, how do I keep it?* QUILL Cast has had a
three-screen first run for months; Radio -- the app with eight directories, a
recording scheduler and live rewind -- had nothing at all.

The rules worth pinning are the ones that make this bearable rather than an
irritation: it does not run for somebody who already has stations, a tip fires
once ever, and every key it teaches is the key that is actually bound.
"""

from __future__ import annotations

from quill.core.radio.onboarding import (
    FIRST_RUN_SCREENS,
    SCREEN_BODIES,
    SCREEN_COMMANDS,
    SCREEN_TITLES,
    TIPS,
    RadioOnboardingState,
    describe_tips,
    mark_seen,
    needs_first_run,
    remaining_tips,
    reset_tips,
    screen_body,
    tip_for,
)

_BINDINGS = {
    "radio.browse": "Ctrl+B",
    "radio.add_custom_station": "Ctrl+N",
    "radio.manage_favorites": "Ctrl+Shift+M",
    "radio.play_favorite_1": "Ctrl+Alt+Shift+1",
}


def _resolve(command_id: str) -> str:
    return _BINDINGS.get(command_id, "")


# -- when it runs --------------------------------------------------------------


def test_a_brand_new_listener_gets_the_screens() -> None:
    assert needs_first_run(RadioOnboardingState(), has_favorites=False) is True


def test_somebody_who_already_has_stations_does_not() -> None:
    # However they got there: an imported list, a restored backup, an upgrade
    # from a version that predates this flow. Explaining how to find a first
    # station to somebody with forty is a way of saying nobody checked.
    assert needs_first_run(RadioOnboardingState(), has_favorites=True) is False


def test_finishing_once_is_final() -> None:
    state = RadioOnboardingState(completed_first_run=True)
    assert needs_first_run(state, has_favorites=False) is False


# -- the screens ---------------------------------------------------------------


def test_there_are_three_screens_each_with_a_title_and_a_body() -> None:
    assert len(FIRST_RUN_SCREENS) == 3
    for key in FIRST_RUN_SCREENS:
        assert SCREEN_TITLES[key]
        assert SCREEN_BODIES[key]


def test_every_placeholder_is_replaced_by_the_key_that_is_bound() -> None:
    for key in FIRST_RUN_SCREENS:
        body = screen_body(key, _resolve)
        assert "{" not in body and "}" not in body, key
    assert "Ctrl+B" in screen_body("welcome", _resolve)
    assert "Ctrl+N" in screen_body("find_station", _resolve)
    assert "Ctrl+Shift+M" in screen_body("keep_it", _resolve)


def test_a_rebound_key_is_the_one_taught() -> None:
    # The whole reason screen_body takes a resolver: teaching a default to
    # somebody who changed it is worse than teaching nothing.
    body = screen_body("welcome", lambda _c: "F9")
    assert "F9" in body
    assert "Ctrl+B" not in body


def test_an_unbound_command_names_its_menu_item_rather_than_empty_braces() -> None:
    # "press left brace browse right brace" is the failure this avoids.
    body = screen_body("welcome", lambda _c: "")
    assert "{" not in body
    assert "the menu item of the same name" in body


def test_a_resolver_that_raises_does_not_take_the_screen_with_it() -> None:
    def _boom(_command_id: str) -> str:
        raise KeyError("no keymap loaded")

    body = screen_body("find_station", _boom)
    assert "{" not in body


def test_with_no_resolver_at_all_the_screens_still_read() -> None:
    for key in FIRST_RUN_SCREENS:
        assert "{" not in screen_body(key)


def test_every_placeholder_in_a_body_has_a_command_behind_it() -> None:
    # A placeholder with no entry in SCREEN_COMMANDS would raise KeyError at
    # format() time -- on a new listener's first launch, of all moments.
    import string

    for key in FIRST_RUN_SCREENS:
        used = {
            name
            for _text, name, _spec, _conv in string.Formatter().parse(SCREEN_BODIES[key])
            if name
        }
        unknown = used - set(SCREEN_COMMANDS)
        assert not unknown, f"{key} uses {unknown}, which nothing resolves"


def test_the_command_ids_are_real_bindable_commands() -> None:
    """Every id names a command that carries a key somewhere.

    The screens teach keystrokes. An id that no longer exists renders as a menu
    route, silently, and nobody finds out -- so it fails here instead.
    """
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap import DEFAULT_KEYMAP

    known = set(DEFAULT_KEYMAP) | set(APP_KEYMAPS["radio"])
    unknown = sorted(set(SCREEN_COMMANDS.values()) - known)
    assert not unknown, f"the first-run screens name commands that do not exist: {unknown}"


# -- tips ----------------------------------------------------------------------


def test_a_tip_fires_once_and_then_never_again() -> None:
    state = RadioOnboardingState()
    assert tip_for(state, "live_rewind")
    mark_seen(state, "live_rewind")
    assert tip_for(state, "live_rewind") == ""


def test_tips_switched_off_fire_for_nothing() -> None:
    state = RadioOnboardingState(tips_enabled=False)
    for tip_id in TIPS:
        assert tip_for(state, tip_id) == ""


def test_an_unknown_tip_id_is_silence_rather_than_a_crash() -> None:
    assert tip_for(RadioOnboardingState(), "not_a_tip") == ""


def test_marking_an_unknown_id_does_not_pollute_the_store() -> None:
    state = RadioOnboardingState()
    mark_seen(state, "not_a_tip")
    assert state.seen_tips == set()


def test_show_them_again_puts_every_tip_back() -> None:
    state = RadioOnboardingState(seen_tips=set(TIPS))
    assert remaining_tips(state) == 0
    reset_tips(state)
    assert remaining_tips(state) == len(TIPS)


def test_every_tip_is_one_sentence_that_ends_as_one() -> None:
    for tip_id, sentence in TIPS.items():
        assert sentence.endswith("."), tip_id
        assert "\n" not in sentence, tip_id


# -- the settings line ---------------------------------------------------------


def test_the_settings_line_says_where_this_listener_stands() -> None:
    state = RadioOnboardingState()
    assert describe_tips(state).startswith(f"{len(TIPS)} tips")
    state.tips_enabled = False
    assert describe_tips(state) == "Tips are switched off."


def test_one_tip_left_is_singular() -> None:
    state = RadioOnboardingState(seen_tips=set(list(TIPS)[:-1]))
    assert "1 tip still" in describe_tips(state)


def test_all_seen_offers_the_way_back() -> None:
    state = RadioOnboardingState(seen_tips=set(TIPS))
    assert "Show Tips Again" in describe_tips(state)


# -- persistence ---------------------------------------------------------------


def test_the_state_round_trips() -> None:
    state = RadioOnboardingState(
        completed_first_run=True, seen_tips={"live_rewind"}, tips_enabled=False
    )
    assert RadioOnboardingState.from_dict(state.to_dict()) == state


def test_a_tip_id_from_a_newer_build_survives_a_downgrade() -> None:
    # Dropping it would show it again on the way back up.
    state = RadioOnboardingState.from_dict({"seen_tips": ["from_the_future"]})
    assert "from_the_future" in state.seen_tips


def test_junk_in_the_store_is_a_fresh_state_not_a_crash() -> None:
    assert RadioOnboardingState.from_dict("nonsense") == RadioOnboardingState()
    assert RadioOnboardingState.from_dict(None) == RadioOnboardingState()
    assert RadioOnboardingState.from_dict({"seen_tips": "not a list"}).seen_tips == set()
