"""GATE-CATALOGUE, and the folds into the family command catalogue.

docs/design/command-key.md sections 5 and 15. The catalogue is the one place a
command's spoken name, aliases, examples, description and risk live; three
older tables were folded into it, and each fold has a test here that nothing
was lost on the way.
"""

from __future__ import annotations

import dataclasses

import pytest

from quill.core import command_catalogue as cat
from quill.core.command_catalogue import CommandSpec, Kind, Risk
from quill.tools import command_catalogue_audit as audit

pytestmark = pytest.mark.smoke

#: The agents' safe list as it stood before it became a view of the catalogue.
#: Changing it is a security decision, so it is frozen here, order and all.
_SAFE_TOOL_IDS_BEFORE = (
    "file.save",
    "file.save_all",
    "file.new",
    "edit.undo",
    "edit.redo",
    "edit.select_all",
    "format.bold",
    "format.italic",
    "format.upper_case",
    "format.lower_case",
    "format.title_case",
    "format.sentence_case",
    "format.insert_bullet_list",
    "format.insert_numbered_list",
    "tools.word_count",
    "tools.spell_check_dialog",
    "tools.read_aloud_start_pause",
    "tools.read_aloud_stop",
    "navigate.next_heading",
    "navigate.previous_heading",
    "navigate.outline_navigator",
    "edit.find",
    "view.toggle_soft_wrap",
    "app.command_palette",
)

#: The palette's old ``COMMAND_ALIASES``, frozen, so a search that found a
#: command before still finds it.
_PALETTE_ALIASES_BEFORE = {
    "file.new": "create blank fresh",
    "file.open": "load browse",
    "file.save": "write store keep",
    "file.save_as": "duplicate save copy",
    "file.restore_backup": "recover previous version undelete",
    "file.print": "printer paper",
    "file.open_url": "web address link internet",
    "app.preferences": "settings options configure",
    "app.preferences_hub": "preferences hub recipes working modes quillin glow pages",
    "app.exit": "quit leave shut down",
    "app.announcement_self_test": "speech test braille test output check",
    "app.report_editor_surface": "braille diagnostic surface class emulation",
    "app.braille_ab": "braille compare test display cell dots emulate system edit",
    "edit.undo": "revert back mistake",
    "edit.redo": "again restore change",
    "edit.replace_all": "search substitute swap",
    "edit.copy_to_next_slot": "clipboard tray multi copy",
    "view.toggle_dark_mode": "theme light night appearance",
    "view.toggle_soft_wrap": "word wrap line wrap",
    "view.send_to_tray": "minimize background hide",
    "verbosity.where_am_i": "position location context orient",
    "tools.copy_diagnostic_summary": "debug info support report",
}

#: Words deliberately given up, each with why. "search" now leads to Find
#: rather than Replace All, which is what a person typing it means.
_PALETTE_WORDS_GIVEN_UP = {("edit.replace_all", "search")}


# -- the gate ------------------------------------------------------------------


def test_every_command_is_a_row_or_classified() -> None:
    problems = audit.classification_problems(audit.load_snapshot())
    assert not problems, "\n".join(problems)


def test_no_row_breaks_a_catalogue_rule() -> None:
    problems = audit.row_problems()
    assert not problems, "\n".join(problems)


def test_the_unreviewed_list_cannot_grow_by_rewriting_the_snapshot() -> None:
    previous = audit.load_snapshot()
    assert not audit.growth(previous, audit.snapshot_for(previous))
    shrunk = {app: {"unreviewed": table["unreviewed"][1:]} for app, table in previous.items()}
    assert audit.growth(shrunk, audit.snapshot_for(previous))


def test_the_audit_is_rostered_and_passes() -> None:
    from quill.tools.platform_report import GATES

    assert any("quill.tools.command_catalogue_audit" in gate.argv for gate in GATES)
    assert audit.main([]) == 0


@pytest.mark.parametrize(
    ("change", "complaint"),
    [
        (dict(id="file.delete_everything", risk=Risk.SAFE), "cannot be SAFE"),
        (dict(risk=Risk.CONFIRM, agent_ok=True), "offered to agents"),
        (dict(examples=()), "no example"),
        (dict(description=""), "no description"),
        (dict(risk=Risk.NEVER, where="", examples=(), agent_ok=False), "does not say where"),
        (dict(aliases=("scratch that",)), "dictation phrase"),
        (dict(opposite="file.no_such_row"), "opposite"),
        (dict(id="file.not_a_real_command"), "not a command"),
    ],
)
def test_each_rule_catches_its_own_breakage(change: dict[str, object], complaint: str) -> None:
    good = cat.row("file.save")
    assert good is not None
    bad = dataclasses.replace(good, **change)  # type: ignore[arg-type]
    problems = audit.row_problems([bad])
    assert any(complaint in item for item in problems), problems


def test_an_alias_shared_by_two_offered_rows_is_caught() -> None:
    save = cat.row("file.save")
    new = cat.row("file.new")
    assert save is not None and new is not None
    clash = dataclasses.replace(new, aliases=("keep",))
    assert any("also file.save" in item for item in audit.row_problems([save, clash]))


def test_an_unclassified_command_fails_the_gate() -> None:
    snapshot = audit.load_snapshot()
    snapshot["quill"]["unreviewed"] = snapshot["quill"]["unreviewed"][1:]
    assert audit.classification_problems(snapshot)


# -- the shape of the table ----------------------------------------------------


def test_ids_are_unique_within_each_app() -> None:
    for app in cat.APPS:
        ids = [spec.id for spec in cat.rows_for_app(app)]
        assert len(ids) == len(set(ids)), app


def test_every_offered_row_has_three_examples() -> None:
    """The plan's target is three; every reviewed row meets it, so it is a floor now."""
    thin = [spec.id for spec in cat.all_rows() if spec.offered and len(spec.examples) < 3]
    assert not thin


def test_opposites_point_back() -> None:
    for app in ("quill", "radio"):
        for spec in cat.rows_for_app(app):
            if spec.opposite and spec.kind is Kind.STEP:
                other = cat.row(spec.opposite, app)
                assert other is not None and other.opposite == spec.id, spec.id


def test_never_rows_are_never_offered() -> None:
    for spec in cat.all_rows():
        assert spec.offered is (spec.risk is not Risk.NEVER)


def test_words_are_lower_case_title_aliases_and_examples() -> None:
    spec = CommandSpec("x.y", "Title", aliases=("One",), examples=("Two Three",))
    assert spec.words() == ("title", "one", "two three")


# -- QUILL Lite is a view of QUILL (rule 10) ------------------------------------


def test_every_lite_row_is_a_quill_row_under_a_lite_id() -> None:
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    for spec in cat.rows_for_app("lite"):
        assert spec.id.startswith(cat.LITE_PREFIX)
        handler = spec.id.removeprefix(cat.LITE_PREFIX)
        quill = cat.row(COMMAND_EQUIVALENTS[handler])
        assert quill is not None
        assert dataclasses.replace(spec, id=quill.id, apps=quill.apps) == quill


def test_lite_reaches_the_rows_the_plan_names() -> None:
    for handler in ("cmd_save", "cmd_undo", "cmd_goto_line", "cmd_close", "cmd_clear_bookmarks"):
        assert cat.row(cat.LITE_PREFIX + handler, "lite") is not None, handler
    close = cat.row("lite.cmd_close", "lite")
    assert close is not None and close.risk is Risk.CONFIRM
    assert cat.row("lite.cmd_exit", "lite") is not None
    assert cat.row("lite.cmd_exit", "lite").risk is Risk.NEVER  # type: ignore[union-attr]


def test_lite_has_no_read_aloud_because_it_has_no_equivalent() -> None:
    assert not [spec for spec in cat.rows_for_app("lite") if "read_aloud" in spec.title.lower()]
    assert cat.lite_handler_for("tools.read_aloud_start_pause") == ()
    assert "cmd_save" in cat.lite_handler_for("file.save")


# -- the folds ----------------------------------------------------------------


def test_the_agent_safe_list_is_a_view_and_did_not_change() -> None:
    from quill.core.ai.agent import SAFE_TOOL_IDS

    assert SAFE_TOOL_IDS == _SAFE_TOOL_IDS_BEFORE
    assert cat.agent_ok_ids("quill") == _SAFE_TOOL_IDS_BEFORE
    assert cat.agent_ok_ids("radio") == ()


def test_every_palette_alias_word_is_still_searchable() -> None:
    from quill.core.commands import Command
    from quill.core.palette import _searchable_text

    lost: list[str] = []
    for command_id, words in _PALETTE_ALIASES_BEFORE.items():
        spec = cat.row(command_id)
        assert spec is not None, command_id
        text = _searchable_text(Command(command_id, spec.title, None, lambda: None, "core"))
        for word in words.split():
            if word not in text and (command_id, word) not in _PALETTE_WORDS_GIVEN_UP:
                lost.append(f"{command_id}: {word}")
    assert not lost


def test_palette_still_ranks_by_alias() -> None:
    from quill.core.commands import Command
    from quill.core.palette import rank_commands

    commands = [
        Command("app.exit", "Exit", "Ctrl+Q", lambda: None, "core"),
        Command("app.preferences", "Preferences", "Ctrl+,", lambda: None, "core"),
        Command("view.toggle_dark_mode", "Toggle Dark Mode", None, lambda: None, "core"),
    ]
    assert rank_commands(commands, "quit", {})[0].id == "app.exit"
    assert rank_commands(commands, "settings", {})[0].id == "app.preferences"
    assert rank_commands(commands, "theme", {})[0].id == "view.toggle_dark_mode"


def test_voice_phrases_come_from_the_catalogue() -> None:
    from quill.core.speech import voice_commands as vc

    assert "save file" in vc._phrases_for("file.save", "Save")
    assert "count words" in vc._phrases_for("tools.word_count", "Word Count")
    assert not hasattr(vc, "_ALIASES")


def test_palette_alias_text_reaches_lite_and_radio_ids() -> None:
    assert "louder" in cat.palette_alias_text("radio.volume_up")
    assert "write" in cat.palette_alias_text("lite.cmd_save")
    assert cat.palette_alias_text("no.such.command") == ""
    assert cat.aliases_for("no.such.command") == ()
