"""App sounds play on: one meaning and one chooser for every QUILL app.

Reported on QUILLVille against Quill Radio 3.2.0 (Rick Lewis, October 2026):
confirmation sounds went to the default card while the radio went to the
broadcast card. Made family-wide the same day, with None (no sounds) and
Alt+Shift+M to turn an app's sounds off and back on.
"""

from __future__ import annotations

import json

import pytest

from quill.core import app_sound_route as route
from quill.core import app_sounds_store as store
from quill.core.app_sounds_store import AppSoundChoice

_HEADSET = ("wasapi/{ca86f65f-6b12-449a-ae6d-e99036afdb13}", "Speakers (Logi USB Headset)")
_DESK = (
    "wasapi/{e633b0f5-6fbf-4e42-8b91-2dbc39479395}",
    "Speakers (Realtek High Definition Audio)",
)


def test_apps_with_audio_follow_it_and_the_rest_start_at_the_default() -> None:
    assert route.default_for(True) == route.FOLLOW
    assert route.default_for(False) == ""


def test_following_means_wherever_the_app_audio_is() -> None:
    assert route.effective_device(route.FOLLOW, _HEADSET[0]) == _HEADSET[0]
    assert route.effective_device(route.FOLLOW, "") == ""  # never chose a card: as before
    assert route.effective_device(route.NONE, _HEADSET[0]) == route.NONE
    assert route.effective_device(_DESK[0], _HEADSET[0]) == _DESK[0]


@pytest.mark.parametrize(
    ("stored", "has_audio", "expected"),
    [
        (None, True, route.FOLLOW),
        (None, False, ""),
        ("radio", True, route.FOLLOW),  # Radio 3.2.0 build 3 testing spelling
        (route.FOLLOW, False, ""),  # shared from an app that has audio
        ("  ", True, ""),
        (route.NONE, False, route.NONE),
        (_DESK[0], False, _DESK[0]),
    ],
)
def test_a_stored_value_reads_back_safely(stored: object, has_audio: bool, expected: str) -> None:
    assert route.normalize(stored, has_own_audio=has_audio) == expected


def test_the_chooser_offers_follow_only_to_an_app_with_audio() -> None:
    labels, values, index = route.choices(
        [_HEADSET, _DESK], route.FOLLOW, own_device=_HEADSET[0], own_audio_name="its audio"
    )
    assert labels[:3] == [
        "Same as its audio (now: Speakers (Logi USB Headset))",
        "System default",
        "None (no sounds)",
    ]
    assert values == [route.FOLLOW, "", route.NONE, _HEADSET[0], _DESK[0]]
    assert index == 0
    labels, values, _index = route.choices([_HEADSET], "", own_device=None)
    assert labels == ["System default", "None (no sounds)", "Speakers (Logi USB Headset)"]


def test_an_unplugged_card_stays_chosen_and_is_marked() -> None:
    labels, values, index = route.choices([_DESK], _HEADSET[0])
    assert values[index] == _HEADSET[0]
    assert labels[index].endswith("(not currently available)")


def test_the_key_turns_sounds_off_and_puts_them_back_where_they_were() -> None:
    off, remembered = route.toggled(_DESK[0], None, has_own_audio=False)
    assert (off, remembered) == (route.NONE, _DESK[0])
    assert route.toggled(off, remembered, has_own_audio=False) == (_DESK[0], None)


def test_the_system_default_is_a_place_the_key_can_go_back_to() -> None:
    off, remembered = route.toggled("", None, has_own_audio=True)
    assert remembered == ""  # not "nothing": the media app was on the default on purpose
    assert route.toggled(off, remembered, has_own_audio=True) == ("", None)


def test_none_chosen_by_hand_comes_back_to_the_app_default() -> None:
    assert route.toggled(route.NONE, None, has_own_audio=True) == (route.FOLLOW, None)
    assert route.toggled(route.NONE, None, has_own_audio=False) == ("", None)


def test_each_app_keeps_its_own_choice(tmp_path) -> None:
    store.save(tmp_path, "radio", AppSoundChoice(_HEADSET[0]))
    store.save(tmp_path, "quill", AppSoundChoice(route.NONE, ""))
    assert store.load(tmp_path, "radio", has_own_audio=True) == AppSoundChoice(_HEADSET[0])
    assert store.load(tmp_path, "quill", has_own_audio=False) == AppSoundChoice(route.NONE, "")
    assert store.load(tmp_path, "weather", has_own_audio=False) == AppSoundChoice("")
    assert store.load(tmp_path, "cast", has_own_audio=True) == AppSoundChoice(route.FOLLOW)


def test_sharing_copies_the_choice_and_each_app_reads_it_its_own_way(tmp_path) -> None:
    store.save(tmp_path, "radio", AppSoundChoice(route.FOLLOW), share_with=["cast", "quill"])
    assert store.load(tmp_path, "cast", has_own_audio=True).choice == route.FOLLOW
    assert store.load(tmp_path, "quill", has_own_audio=False).choice == ""  # nearest it has


def test_a_broken_file_reads_as_defaults_and_is_replaced_whole(tmp_path) -> None:
    (tmp_path / store.FILE_NAME).write_text("{not json", encoding="utf-8")
    assert store.load(tmp_path, "radio", has_own_audio=True) == AppSoundChoice(route.FOLLOW)
    store.save(tmp_path, "radio", AppSoundChoice(""))
    saved = json.loads((tmp_path / store.FILE_NAME).read_text(encoding="utf-8"))
    assert saved == {"version": 1, "apps": {"radio": {"choice": "", "remembered": None}}}
