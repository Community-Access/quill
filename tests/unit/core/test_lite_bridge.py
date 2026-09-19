"""Bringing a QuillLite setup into QUILL (bad.md P2.4).

The decision this file encodes, answered 2026-09-18: **content is shared,
preferences are copied.** Abbreviations and a personal dictionary are months of
somebody's work and keeping two copies in step by hand is how one copy goes
stale; wrap and autosave are about the editor you are in, and the two are not
the same editor.

The direction is not arbitrary either. QuillLite already ships
``share_quill_abbreviations`` and ``share_quill_dictionary``, which point *it* at
QUILL's folder -- so QUILL's folder is already the shared home, and this follows
that rather than inventing a second one that could then disagree with the first.

Above all: **merging never loses.** QUILL's own entry wins every collision.
Somebody running this has been using QUILL, so what is already here is the more
recent statement, and an import that overwrites it is an import that undoes
their work.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.lite_bridge import (
    SHARED_CONTENT_STORES,
    BringPlan,
    apply_bring_plan,
    describe_plan,
    enable_lite_sharing,
    merge_json_store,
    plan_bring_from_lite,
    translate_lite_keymap,
    translate_lite_settings,
)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


# -- reading the plan ----------------------------------------------------------


def test_no_quilllite_means_nothing_to_bring_and_says_so() -> None:
    plan = BringPlan()
    assert plan.is_empty
    assert "has not been run" in describe_plan(plan)


def test_an_empty_quilllite_folder_says_it_is_empty_rather_than_succeeding(tmp_path: Path) -> None:
    plan = plan_bring_from_lite(tmp_path)
    assert plan.lite_dir == tmp_path
    assert plan.is_empty
    assert "nothing to bring" in describe_plan(plan)


def test_the_plan_finds_settings_keys_and_stores(tmp_path: Path) -> None:
    _write(tmp_path / "settings.json", {"word_wrap": False, "autosave_seconds": 30})
    _write(tmp_path / "keymap.json", {"cmd_bold": "Ctrl+Alt+B"})
    _write(tmp_path / "abbreviations.json", {"version": 2, "abbreviations": []})

    plan = plan_bring_from_lite(tmp_path)

    assert plan.settings == {"soft_wrap": False, "autosave_interval_seconds": 30}
    assert plan.keymap == {"format.bold": "Ctrl+Alt+B"}
    assert [store.key for store in plan.shared] == ["abbreviations"]


def test_the_plan_changes_nothing_on_disk(tmp_path: Path) -> None:
    """It is a question's answer, not the action: asked before anything happens."""
    _write(tmp_path / "settings.json", {"word_wrap": False})
    before = (tmp_path / "settings.json").read_bytes()

    plan_bring_from_lite(tmp_path)

    assert (tmp_path / "settings.json").read_bytes() == before


# -- translating the settings --------------------------------------------------


def test_the_renamed_fields_come_across_under_quills_names() -> None:
    brought, _skipped = translate_lite_settings({
        "word_wrap": True,
        "autosave_seconds": 45,
        "spell_check_while_typing": False,
        "check_updates_on_launch": True,
    })
    assert brought == {
        "soft_wrap": True,
        "autosave_interval_seconds": 45,
        "spellcheck_as_you_type": False,
        "auto_check_updates": True,
    }


def test_the_document_mode_is_translated_not_copied() -> None:
    """Lite's plain/rich and QUILL's format name are not the same shape."""
    assert translate_lite_settings({"default_mode": "plain"})[0] == {
        "default_new_document_format": "txt"
    }
    assert translate_lite_settings({"default_mode": "rich"})[0] == {
        "default_new_document_format": "rtf"
    }
    # A value neither side knows is left behind rather than guessed at.
    brought, skipped = translate_lite_settings({"default_mode": "something"})
    assert brought == {}
    assert skipped == ("default_mode",)


def test_the_lookalike_field_is_never_copied() -> None:
    """Lite's recent_files is a LIST; QUILL's recent_files_limit is a NUMBER."""
    brought, skipped = translate_lite_settings({"recent_files": ["a.txt", "b.txt"]})
    assert brought == {}
    assert "recent_files" in skipped


def test_this_computer_is_not_a_preference() -> None:
    brought, skipped = translate_lite_settings({
        "window_width": 900,
        "window_maximized": True,
        "session_files": ["x"],
        "word_wrap": True,
    })
    assert brought == {"soft_wrap": True}
    assert set(skipped) == {"window_width", "window_maximized", "session_files"}


def test_quilllites_own_sharing_switches_are_not_copied_into_quill() -> None:
    """They are about QuillLite reading QUILL, which is the other direction."""
    brought, skipped = translate_lite_settings({"share_quill_abbreviations": True})
    assert brought == {}
    assert skipped == ("share_quill_abbreviations",)


def test_a_field_quill_has_no_home_for_is_reported_not_dropped_silently() -> None:
    _brought, skipped = translate_lite_settings({"some_lite_only_thing": 1})
    assert skipped == ("some_lite_only_thing",)


# -- translating the keymap ----------------------------------------------------


def test_a_handler_with_no_quill_command_is_dropped_rather_than_guessed() -> None:
    assert translate_lite_keymap({"cmd_not_a_real_handler": "Ctrl+9"}) == {}


def test_an_empty_chord_is_not_a_rebinding() -> None:
    assert translate_lite_keymap({"cmd_bold": "   "}) == {}


# -- merging the stores --------------------------------------------------------


def test_quill_wins_every_collision(tmp_path: Path) -> None:
    lite = tmp_path / "lite.json"
    quill = tmp_path / "quill.json"
    _write(lite, {"abbreviations": [{"abbreviation": "btw", "expansion": "FROM LITE"}]})
    _write(quill, {"abbreviations": [{"abbreviation": "btw", "expansion": "FROM QUILL"}]})

    added = merge_json_store(lite, quill)

    assert added == 0
    kept = json.loads(quill.read_text(encoding="utf-8"))
    assert kept["abbreviations"][0]["expansion"] == "FROM QUILL"


def test_what_only_quilllite_has_is_added(tmp_path: Path) -> None:
    lite = tmp_path / "lite.json"
    quill = tmp_path / "quill.json"
    _write(lite, {"abbreviations": [{"abbreviation": "btw", "expansion": "by the way"}]})
    _write(quill, {"abbreviations": [{"abbreviation": "ty", "expansion": "thank you"}]})

    assert merge_json_store(lite, quill) == 1
    merged = json.loads(quill.read_text(encoding="utf-8"))
    assert [a["abbreviation"] for a in merged["abbreviations"]] == ["ty", "btw"]


def test_a_missing_quill_file_takes_quilllites_whole_store(tmp_path: Path) -> None:
    lite = tmp_path / "lite.json"
    _write(lite, ["one", "two"])
    quill = tmp_path / "quill.json"

    assert merge_json_store(lite, quill) == 2
    assert json.loads(quill.read_text(encoding="utf-8")) == ["one", "two"]


def test_a_list_store_merges_by_whole_entry(tmp_path: Path) -> None:
    lite = tmp_path / "lite.json"
    quill = tmp_path / "quill.json"
    _write(lite, ["a", "b"])
    _write(quill, ["b", "c"])

    assert merge_json_store(lite, quill) == 1
    assert json.loads(quill.read_text(encoding="utf-8")) == ["b", "c", "a"]


def test_two_different_shapes_are_left_alone(tmp_path: Path) -> None:
    """A merge that cannot be done safely is a merge that is not done."""
    lite = tmp_path / "lite.json"
    quill = tmp_path / "quill.json"
    _write(lite, ["a"])
    _write(quill, {"a": 1})
    before = quill.read_bytes()

    assert merge_json_store(lite, quill) == 0
    assert quill.read_bytes() == before


def test_a_missing_quilllite_file_changes_nothing(tmp_path: Path) -> None:
    quill = tmp_path / "quill.json"
    _write(quill, {"a": 1})
    before = quill.read_bytes()

    assert merge_json_store(tmp_path / "nothing-here.json", quill) == 0
    assert quill.read_bytes() == before


def test_nothing_to_add_writes_nothing(tmp_path: Path) -> None:
    lite = tmp_path / "lite.json"
    quill = tmp_path / "quill.json"
    _write(lite, {"a": 1})
    _write(quill, {"a": 2})
    before = quill.stat().st_mtime_ns

    assert merge_json_store(lite, quill) == 0
    assert quill.stat().st_mtime_ns == before


# -- applying it ---------------------------------------------------------------


def test_applying_merges_every_store_it_found(tmp_path: Path) -> None:
    lite = tmp_path / "lite"
    quill = tmp_path / "quill"
    quill.mkdir()
    _write(lite / "abbreviations.json", {"abbreviations": [{"abbreviation": "btw"}]})
    _write(lite / "dictionaries" / "personal.json", ["colour"])

    plan = plan_bring_from_lite(lite)
    added = apply_bring_plan(plan, quill)

    assert added == {"abbreviations": 1, "dictionary": 1}
    assert (quill / "dictionaries" / "personal.json").is_file()


def test_sharing_is_switched_on_in_quilllites_own_settings(tmp_path: Path) -> None:
    """The one thing written into QuillLite's folder, and only when asked.

    Half of it -- QUILL holding the words while QuillLite still reads its own
    copy -- is the shape that makes a "shared" store look broken.
    """
    lite = tmp_path / "lite"
    _write(lite / "settings.json", {"word_wrap": True})
    _write(lite / "abbreviations.json", {"abbreviations": []})
    _write(lite / "dictionaries" / "personal.json", [])

    plan = plan_bring_from_lite(lite)
    switched = enable_lite_sharing(plan)

    assert set(switched) == {"share_quill_abbreviations", "share_quill_dictionary"}
    raw = json.loads((lite / "settings.json").read_text(encoding="utf-8"))
    assert raw["share_quill_abbreviations"] is True
    assert raw["share_quill_dictionary"] is True
    # Already on: nothing to say the second time.
    assert enable_lite_sharing(plan) == ()


def test_a_store_with_no_switch_does_not_invent_one(tmp_path: Path) -> None:
    lite = tmp_path / "lite"
    _write(lite / "settings.json", {})
    _write(lite / "copy_tray.json", {"slots": []})

    assert enable_lite_sharing(plan_bring_from_lite(lite)) == ()


# -- the report ----------------------------------------------------------------


def test_the_report_counts_first_and_names_what_is_left_behind(tmp_path: Path) -> None:
    _write(tmp_path / "settings.json", {"word_wrap": False, "window_width": 900})
    _write(tmp_path / "keymap.json", {"cmd_bold": "Ctrl+Alt+B"})
    _write(tmp_path / "abbreviations.json", {"abbreviations": []})

    report = describe_plan(plan_bring_from_lite(tmp_path))

    assert "1 setting(s) copied." in report
    assert "1 rebound key(s) copied" in report
    assert "Nothing already in QUILL is replaced." in report
    assert "Left behind (1): window_width" in report


def test_every_store_names_a_file_on_both_sides() -> None:
    for store in SHARED_CONTENT_STORES:
        assert store.lite_file and store.quill_file
        assert store.label.strip()
