"""QuillLite's switchable areas, and the four profiles over them.

Two questions this file answers mechanically, because both were asked of the
Customize Features dialog and neither had an answer in code:

* **Is everything in the list?** Every command that is not always-present has to
  name an area that exists, and every area has to be reachable from the dialog.
  The five areas added in 2026-09 -- Matches, Back/Forward, the Command Palette,
  Describe Character and text size -- existed as menu items belonging to no
  area at all, so no switch could reach them.
* **Does a profile produce a coherent product?** A profile is only useful if
  the menus it leaves behind are the ones its name promises. Notepad's is
  checked against what Notepad actually has.
"""

from __future__ import annotations

import pytest

from quill.core.app_features import AppFeatureSettings, apply_profile
from quill.core.lite.commands import COMMAND_AREA, COMMANDS, MENU_AREA, area_for, plain_label
from quill.core.lite.features import AREAS, DEFAULT_OFF, PROFILES, area_ids


def _settings_for(profile) -> AppFeatureSettings:
    settings = AppFeatureSettings("quilllite")
    apply_profile(settings, profile, AREAS)
    return settings


def _handlers(settings: AppFeatureSettings) -> set[str]:
    from quill.core.lite.commands import visible_commands

    return {row[3] for row in visible_commands(settings.is_enabled) if row[3]}


# ---------------------------------------------------------------------------
# the areas themselves


def test_area_ids_are_unique() -> None:
    assert len({area.id for area in AREAS}) == len(AREAS)


def test_every_area_has_a_description() -> None:
    """The description is what the search box matches on, so it is not optional."""
    for area in AREAS:
        assert area.description.strip(), area.id


def test_every_command_area_names_a_real_area() -> None:
    unknown = {area for area in COMMAND_AREA.values() if area and area not in area_ids()}
    unknown |= {area for area in MENU_AREA.values() if area and area not in area_ids()}
    assert unknown == set()


@pytest.mark.parametrize(
    "handler",
    [
        "cmd_back_location",
        "cmd_forward_location",
        "cmd_command_palette",
        "cmd_describe_character",
        "cmd_describe_character_detail",
        "cmd_zoom_in",
        "cmd_zoom_out",
        "cmd_zoom_reset",
        "cmd_find_all",
        "cmd_count_occurrences",
    ],
)
def test_the_previously_unreachable_commands_now_belong_to_an_area(handler: str) -> None:
    """Each of these was a menu item no switch in the dialog could reach."""
    row = next(r for r in COMMANDS if r[3] == handler)
    assert area_for(row[0], handler) in area_ids()


def test_encoding_is_never_switchable() -> None:
    """The two facts that decide whether a file round-trips byte-for-byte.

    File Encoding and Line Endings used to belong to the line-tools area, so
    turning off Sort Lines took it away as well. For a Notepad replacement that
    dialog is most of the job.
    """
    assert area_for("&Tools", "cmd_file_format") == ""


def test_the_switch_that_opens_the_dialog_is_never_switchable() -> None:
    """Switching off the menu holding the switch is a door that locks inside."""
    for handler in ("cmd_customize_features", "cmd_preferences"):
        row = next(r for r in COMMANDS if r[3] == handler)
        assert area_for(row[0], handler) == ""


# ---------------------------------------------------------------------------
# profiles


def test_profile_ids_are_unique() -> None:
    assert len({p.id for p in PROFILES}) == len(PROFILES)


def test_every_profile_only_names_real_areas() -> None:
    for profile in PROFILES:
        assert profile.disabled <= area_ids(), profile.id


def test_recommended_is_what_a_new_install_is() -> None:
    recommended = next(p for p in PROFILES if p.id == "recommended")
    assert recommended.disabled == DEFAULT_OFF


def test_everything_turns_nothing_off() -> None:
    assert next(p for p in PROFILES if p.id == "everything").disabled == frozenset()


def test_profiles_get_narrower_in_order() -> None:
    """Everything, Recommended, WordPad, Notepad -- each a subset of the last."""
    order = ["everything", "recommended", "wordpad", "notepad"]
    counts = [len(_handlers(_settings_for(next(p for p in PROFILES if p.id == i)))) for i in order]
    assert counts == sorted(counts, reverse=True), dict(zip(order, counts, strict=True))


def test_notepad_is_plain_text_only() -> None:
    handlers = _handlers(_settings_for(next(p for p in PROFILES if p.id == "notepad")))
    assert "cmd_bold" not in handlers
    assert "cmd_list_headings" not in handlers
    assert "cmd_sort_lines" not in handlers


def test_notepad_keeps_what_notepad_has() -> None:
    """Find, print, text size, word wrap, and the encoding of the file."""
    handlers = _handlers(_settings_for(next(p for p in PROFILES if p.id == "notepad")))
    for handler in (
        "cmd_find",
        "cmd_replace",
        "cmd_print",
        "cmd_page_setup",
        "cmd_zoom_in",
        "cmd_toggle_wrap",
        "cmd_file_format",
        "cmd_goto_line",
    ):
        assert handler in handlers, handler


def test_wordpad_keeps_rich_text_and_drops_the_writing_tools() -> None:
    handlers = _handlers(_settings_for(next(p for p in PROFILES if p.id == "wordpad")))
    assert "cmd_bold" in handlers
    assert "cmd_print" in handlers
    assert "cmd_sort_lines" not in handlers
    assert "cmd_manage_abbreviations" not in handlers


def test_no_profile_leaves_an_empty_menu() -> None:
    """Tidying is the part that is obvious only when it is missing."""
    from quill.core.lite.commands import visible_commands

    for profile in PROFILES:
        rows = visible_commands(_settings_for(profile).is_enabled)
        by_menu: dict[str, list[str]] = {}
        for menu, _label, _key, _handler, kind in rows:
            by_menu.setdefault(menu, []).append(kind)
        for menu, kinds in by_menu.items():
            assert any(kind != "sep" for kind in kinds), f"{profile.id}: {menu} is only separators"


def test_every_profile_still_reaches_the_customize_dialog() -> None:
    """Whatever a profile removes, it can always be undone."""
    for profile in PROFILES:
        assert "cmd_customize_features" in _handlers(_settings_for(profile)), profile.id


def test_applying_a_profile_leaves_the_seeded_marker_alone() -> None:
    """A profile has no opinion about a private marker in the same store."""
    settings = AppFeatureSettings("quilllite", {"_seeded"})
    apply_profile(settings, next(p for p in PROFILES if p.id == "everything"), AREAS)
    assert "_seeded" in settings.disabled


def test_settings_report_which_profile_they_match() -> None:
    for profile in PROFILES:
        settings = _settings_for(profile)
        matched = [p.id for p in PROFILES if settings.matches_profile(p, AREAS)]
        assert profile.id in matched


def test_a_hand_edit_matches_no_profile() -> None:
    settings = _settings_for(next(p for p in PROFILES if p.id == "everything"))
    settings.set_enabled("printing", False)
    assert not any(settings.matches_profile(p, AREAS) for p in PROFILES)


def test_profile_names_read_as_products() -> None:
    """The two named after other programs say in a word what a list cannot."""
    assert {"Notepad", "WordPad"} <= {p.name for p in PROFILES}


def test_labels_survive_a_profile(capsys: pytest.CaptureFixture[str]) -> None:
    """A sanity net: every surviving row still has a readable label."""
    from quill.core.lite.commands import visible_commands

    for profile in PROFILES:
        for _menu, label, _key, _handler, kind in visible_commands(
            _settings_for(profile).is_enabled
        ):
            if kind != "sep":
                assert plain_label(label).strip(), profile.id


# ---------------------------------------------------------------------------
# a profile's name promises more than a set of menus


def test_notepad_makes_plain_text() -> None:
    """Half of "Notepad" is the menus; the other half is what Ctrl+N creates.

    A profile that removed the Format menu and still made rich text documents
    would keep the letter of its name and break its promise -- and the user
    would find out at the Save As dialog, being offered a format they thought
    they had turned off.
    """
    notepad = next(p for p in PROFILES if p.id == "notepad")
    assert dict(notepad.settings)["default_mode"] == "plain"


def test_wordpad_makes_rich_text() -> None:
    wordpad = next(p for p in PROFILES if p.id == "wordpad")
    assert dict(wordpad.settings)["default_mode"] == "rich"


def test_the_format_a_profile_claims_agrees_with_the_areas_it_keeps() -> None:
    """The check that would have caught the mismatch: no profile may create a
    document kind it has removed every way to work with."""
    for profile in PROFILES:
        mode = dict(profile.settings).get("default_mode")
        if mode != "rich":
            continue
        assert "rich_text" not in profile.disabled, (
            f"{profile.id} creates rich text and has switched the Format menu off"
        )


def test_only_the_two_named_after_products_claim_a_setting() -> None:
    """Recommended and Everything are statements about areas, and nothing else.

    A profile that quietly rewrote a setting the user chose would make the
    Choice a mode rather than a starting point.
    """
    claiming = sorted(p.id for p in PROFILES if p.settings)
    assert claiming == ["notepad", "wordpad"]


def test_every_claimed_setting_is_a_real_field() -> None:
    """A profile naming a field the settings object does not have is silently inert."""
    from quill.core.lite.settings import Settings

    defaults = Settings()
    for profile in PROFILES:
        for name, _value in profile.settings:
            assert hasattr(defaults, name), f"{profile.id} claims unknown setting {name!r}"


def test_every_claimed_value_is_one_the_setting_accepts() -> None:
    """Normalisation would silently undo a value outside the vocabulary."""
    from quill.core.lite.settings import Settings

    for profile in PROFILES:
        settings = Settings()
        for name, value in profile.settings:
            setattr(settings, name, value)
        settings.normalized()
        for name, value in profile.settings:
            assert getattr(settings, name) == value, (
                f"{profile.id}'s {name}={value!r} is normalised away"
            )


def test_applying_a_profile_reports_what_it_changed() -> None:
    from quill.core.app_features import apply_profile_settings
    from quill.core.lite.settings import Settings

    settings = Settings()
    settings.default_mode = "plain"
    wordpad = next(p for p in PROFILES if p.id == "wordpad")

    assert apply_profile_settings(settings, wordpad) == ["default_mode"]
    assert settings.default_mode == "rich"
    # Applying it again changes nothing, and says so.
    assert apply_profile_settings(settings, wordpad) == []


# ---------------------------------------------------------------------------
# the descriptions, which are now on screen and on F1


def test_every_profile_has_a_description_worth_the_space() -> None:
    """It sits under the Choice and answers F1 on it, so a stub is a visible stub."""
    for profile in PROFILES:
        assert len(profile.description) > 120, f"{profile.id}: {profile.description!r}"


def test_a_description_says_how_many_areas_it_leaves_on() -> None:
    """The one number somebody comparing four profiles actually wants."""
    words = {0: "zero", 2: "Two", 5: "Five", 14: "fourteen", 17: "seventeen"}
    for profile in PROFILES:
        on = len(AREAS) - len(profile.disabled)
        spelled = words.get(on, str(on))
        assert spelled.lower() in profile.description.lower(), (
            f"{profile.id} keeps {on} areas and does not say so: {profile.description!r}"
        )


def test_a_profile_that_claims_a_format_says_so_in_words() -> None:
    """The half of the name a list of menus cannot express."""
    for profile in PROFILES:
        mode = dict(profile.settings).get("default_mode")
        if mode is None:
            continue
        assert "Ctrl+N" in profile.description, profile.id
        assert mode in profile.description, profile.id


def test_no_description_promises_an_area_the_profile_removes() -> None:
    """A description that names a feature the profile turns off is worse than none.

    Checked against the areas each profile actually disables, by the words
    those areas are known by, so an edit to either side has to keep them
    agreeing.
    """
    named_by = {
        "rich_text": "Format menu",
        "spelling": "spell check",
        "bookmarks": "bookmarks",
        "clipboard": "clipboard history",
        "command_palette": "command palette",
    }
    for profile in PROFILES:
        for area_id, phrase in named_by.items():
            if area_id not in profile.disabled:
                continue
            index = profile.description.lower().find(phrase.lower())
            if index < 0:
                continue
            before = profile.description[:index].lower()
            assert "no " in before or "without" in before or "off" in before, (
                f"{profile.id} names {phrase!r} without saying it is gone"
            )
