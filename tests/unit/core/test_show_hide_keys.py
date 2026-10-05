"""The family's show/hide keys: the defaults, the one-time move off the old ones,
and the picker's refusals (questions.md 37b, option 3, 2026-10-05). Pure logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import family_chords, show_hide_keys
from quill.core.expansion.settings import InkwellSettings, load_settings, save_settings

FOUR = ("weather", "converter", "player", "inkwell")


def test_radio_quill_and_cast_keep_their_keys_and_the_other_four_have_none() -> None:
    assert family_chords.SHOW_HIDE_DEFAULTS["radio"] == "Ctrl+Alt+Shift+R"
    assert family_chords.SHOW_HIDE_DEFAULTS["quill"] == "Ctrl+Alt+Shift+Q"
    assert family_chords.SHOW_HIDE_DEFAULTS["cast"] == "Ctrl+Alt+Shift+F12"
    for app in FOUR:
        assert family_chords.SHOW_HIDE_DEFAULTS[app] == ""
    assert InkwellSettings().tray_hotkey == ""


@pytest.mark.parametrize(
    ("app", "old"),
    [
        ("weather", "Ctrl+Alt+Shift+W"),
        ("converter", "Ctrl+Alt+Shift+C"),
        ("player", "Ctrl+Alt+Shift+P"),
        ("inkwell", "Ctrl+Shift+Alt+I"),  # spelled differently, the same key
    ],
)
def test_the_old_default_moves_to_none_and_is_told(app: str, old: str) -> None:
    assert family_chords.migrate_show_hide_key(app, old, existing_user=True) == ("", True)


def test_a_key_somebody_chose_is_kept_and_nothing_is_said() -> None:
    chosen = "Ctrl+Alt+Shift+PageUp"
    assert family_chords.migrate_show_hide_key("inkwell", chosen, existing_user=True) == (
        chosen,
        False,
    )


def test_somebody_new_is_told_nothing() -> None:
    assert family_chords.migrate_show_hide_key("weather", None, existing_user=False) == ("", False)


def test_the_sentence_is_the_one_plain_sentence_pair() -> None:
    said = family_chords.retired_key_notice("weather")
    assert said.startswith(
        "Quill Weather's show and hide key is now off by default so it no longer "
        "blocks other apps' shortcuts."
    )
    assert "Show and Hide Key" in said


def test_an_existing_weather_user_is_told_once_then_never_again(tmp_path: Path) -> None:
    chord, notice = show_hide_keys.load_show_hide_key(tmp_path, "weather", existing_user=True)
    assert chord == ""
    assert notice == family_chords.retired_key_notice("weather")
    stored = json.loads((tmp_path / show_hide_keys.STORE_NAME).read_text(encoding="utf-8"))
    assert stored == {"schema": 1, "keys": {"weather": ""}}
    assert show_hide_keys.load_show_hide_key(tmp_path, "weather", existing_user=True) == ("", "")


def test_a_new_player_user_is_told_nothing_and_a_choice_is_kept(tmp_path: Path) -> None:
    assert show_hide_keys.load_show_hide_key(tmp_path, "player", existing_user=False) == ("", "")
    show_hide_keys.save_show_hide_key(tmp_path, "player", "Ctrl+Alt+Shift+PageDown")
    assert show_hide_keys.load_show_hide_key(tmp_path, "player", existing_user=True) == (
        "Ctrl+Alt+Shift+PageDown",
        "",
    )
    assert show_hide_keys.saved_keys(tmp_path) == {"player": "Ctrl+Alt+Shift+PageDown"}


def test_having_run_before_is_a_kept_window_or_a_file_of_its_own(tmp_path: Path) -> None:
    from quill.core.window_geometry import WindowGeometry, save_geometry

    marker = tmp_path / "converter.json"
    assert not show_hide_keys.has_run_before(tmp_path, "converter", marker)
    marker.write_text("{}", encoding="utf-8")
    assert show_hide_keys.has_run_before(tmp_path, "converter", marker)
    save_geometry(tmp_path, "player", WindowGeometry())
    assert show_hide_keys.has_run_before(tmp_path, "player")


def test_inkwells_saved_old_default_moves_to_none_once(tmp_path: Path) -> None:
    settings = InkwellSettings(tray_hotkey="Ctrl+Alt+Shift+I")
    save_settings(tmp_path, settings)
    loaded = load_settings(tmp_path)
    assert loaded.take_system_keys(tmp_path, ran_before=True) == (
        "",
        family_chords.retired_key_notice("inkwell"),
    )
    again = load_settings(tmp_path)
    assert again.tray_hotkey == ""
    assert again.take_system_keys(tmp_path, ran_before=True) == ("", "")


def test_inkwells_own_choice_is_kept(tmp_path: Path) -> None:
    save_settings(tmp_path, InkwellSettings(tray_hotkey="Ctrl+Alt+Shift+Right"))
    loaded = load_settings(tmp_path)
    assert loaded.take_system_keys(tmp_path, ran_before=True) == ("Ctrl+Alt+Shift+Right", "")


# -- Inkwell's Quick Insert and Expand Word keys (2026-10-05) ---------------------


def test_inkwells_two_other_keys_are_off_by_default() -> None:
    settings = InkwellSettings()
    assert (settings.quick_insert_hotkey, settings.expand_now_hotkey) == ("", "")


def test_inkwells_old_quick_insert_and_expand_keys_move_to_none_once(tmp_path: Path) -> None:
    from quill.core.expansion.settings import retired_keys_notice

    save_settings(
        tmp_path,
        InkwellSettings(
            quick_insert_hotkey="Ctrl+Alt+Shift+K", expand_now_hotkey="Ctrl+Shift+Alt+X"
        ),
    )
    chord, said = load_settings(tmp_path).take_system_keys(tmp_path, ran_before=True)
    assert chord == ""
    assert said == retired_keys_notice(["Quick Insert", "Expand Word"])
    assert said == (
        "Quill Inkwell's Quick Insert and Expand Word keys are now off by default so they "
        "no longer block other apps' shortcuts. To choose them, open the File menu."
    )
    again = load_settings(tmp_path)
    assert (again.quick_insert_hotkey, again.expand_now_hotkey) == ("", "")
    assert again.take_system_keys(tmp_path, ran_before=True) == ("", "")


def test_inkwells_chosen_quick_insert_key_is_kept_and_only_the_old_one_moves(
    tmp_path: Path,
) -> None:
    save_settings(
        tmp_path,
        InkwellSettings(
            quick_insert_hotkey="Ctrl+Alt+Shift+PageUp", expand_now_hotkey="Ctrl+Alt+Shift+X"
        ),
    )
    _chord, said = load_settings(tmp_path).take_system_keys(tmp_path, ran_before=True)
    assert said.startswith("Quill Inkwell's Expand Word key is now off by default")
    assert said.endswith("open the File menu and choose Expand Word Key.")
    again = load_settings(tmp_path)
    assert (again.quick_insert_hotkey, again.expand_now_hotkey) == ("Ctrl+Alt+Shift+PageUp", "")


def test_a_file_from_before_the_keys_were_saved_had_the_old_defaults(tmp_path: Path) -> None:
    (tmp_path / "inkwell.json").write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    loaded = load_settings(tmp_path)
    assert (loaded.quick_insert_hotkey, loaded.expand_now_hotkey) == (
        "Ctrl+Alt+Shift+K",
        "Ctrl+Alt+Shift+X",
    )
    _chord, said = loaded.take_system_keys(tmp_path, ran_before=True)
    assert "Quick Insert and Expand Word keys" in said
    assert load_settings(tmp_path).quick_insert_hotkey == ""


def test_an_inkwell_user_with_no_settings_file_had_all_three_old_keys(tmp_path: Path) -> None:
    """Nothing was ever changed, so nothing was ever saved: all three defaults."""
    chord, said = InkwellSettings().take_system_keys(tmp_path, ran_before=True)
    assert chord == ""
    assert said.startswith(
        "Quill Inkwell's show and hide, Quick Insert and Expand Word keys are now off"
    )
    assert (tmp_path / "inkwell.json").exists()
    assert load_settings(tmp_path).take_system_keys(tmp_path, ran_before=True) == ("", "")


def test_somebody_new_to_inkwell_is_told_nothing_ever(tmp_path: Path) -> None:
    assert InkwellSettings().take_system_keys(tmp_path, ran_before=False) == ("", "")
    # The window it keeps on close must not make the next launch look like an
    # old user's: the settings file it wrote says the keys were decided.
    assert load_settings(tmp_path).take_system_keys(tmp_path, ran_before=True) == ("", "")


def test_an_inkwell_key_is_refused_when_it_is_one_of_inkwells_others() -> None:
    said = family_chords.show_hide_key_problem(
        "Ctrl+Alt+Shift+PageUp",
        app_id="inkwell",
        own={"show and hide key": "Ctrl+Alt+Shift+PageUp", "Expand Word key": ""},
    )
    assert said == "Ctrl+Alt+Shift+PageUp is already Quill Inkwell's show and hide key."
    assert (
        family_chords.suggest_show_hide_key(
            "inkwell",
            own={
                "show and hide key": "Ctrl+Alt+Shift+PageUp",
                "Expand Word key": "Ctrl+Alt+Shift+PageDown",
            },
        )
        == "Ctrl+Alt+PageUp"
    )


@pytest.mark.parametrize("chord", ["Ctrl+Alt+Shift+K", "Ctrl+Alt+Shift+X"])
def test_inkwells_old_keys_are_refused_because_the_family_uses_them(chord: str) -> None:
    said = family_chords.show_hide_key_problem(chord, app_id="inkwell")
    assert said.startswith(f"{chord} is already a shortcut in ")


def test_the_inventory_holds_only_the_three_show_hide_keys_by_default() -> None:
    keys = {
        (key.app_id, key.purpose, key.chord) for key in family_chords.default_system_wide_keys()
    }
    assert keys == {
        ("quill", "show and hide key", "Ctrl+Alt+Shift+Q"),
        ("radio", "show and hide key", "Ctrl+Alt+Shift+R"),
        ("cast", "show and hide key", "Ctrl+Alt+Shift+F12"),
    }


# -- the picker's refusals ------------------------------------------------------


@pytest.mark.parametrize(
    ("chord", "owner"),
    [
        ("Ctrl+Alt+Shift+R", "Quill Radio"),
        ("Ctrl+Alt+Shift+Q", "QUILL"),
        ("Ctrl+Shift+Alt+F12", "Quill Cast"),
    ],
)
def test_another_apps_show_hide_key_is_refused_by_name(chord: str, owner: str) -> None:
    said = family_chords.show_hide_key_problem(chord, app_id="weather")
    assert said == f"{chord} is already {owner}'s show and hide key."


@pytest.mark.parametrize(
    "chord",
    [
        "Ctrl+Alt+Shift+W",  # QUILL's Overwrite Mode, the old Weather key
        "Ctrl+Alt+Shift+Space",  # the Keyboard Manager, in both editors
        "Ctrl+Alt+F12",  # Cast's Restore
        "Alt+Shift+3",  # a numbered Open Recent row
        "Ctrl+Alt+Shift+H",  # File > Show and Hide Key itself
    ],
)
def test_a_family_shortcut_is_refused_in_one_sentence(chord: str) -> None:
    said = family_chords.show_hide_key_problem(chord, app_id="converter")
    assert said.startswith(f"{chord} is already a shortcut in ")
    assert said.endswith("whenever Quill Converter is running.")
    assert said.count(". ") == 0  # one sentence


def test_a_key_another_family_app_was_given_is_refused() -> None:
    said = family_chords.show_hide_key_problem(
        "Ctrl+Alt+Shift+PageUp", app_id="weather", taken={"player": "Ctrl+Alt+Shift+PageUp"}
    )
    assert said == "Ctrl+Alt+Shift+PageUp is already Quill Media Player's show and hide key."


def test_no_key_and_a_free_key_are_both_fine() -> None:
    assert family_chords.show_hide_key_problem("", app_id="inkwell") == ""
    assert family_chords.show_hide_key_problem("Ctrl+Alt+Shift+PageUp", app_id="inkwell") == ""
    assert family_chords.suggest_show_hide_key("inkwell") == "Ctrl+Alt+Shift+PageUp"


def test_a_key_with_no_ctrl_or_alt_is_refused() -> None:
    assert "no Ctrl or Alt" in family_chords.show_hide_key_problem("Shift+F9", app_id="player")


def test_the_installed_copy_of_the_menu_scan_is_readable() -> None:
    rows = family_chords.snapshot_chords()
    assert len(rows) > 500
    assert family_chords.snapshot_chords(Path("does-not-exist.json")) == []
