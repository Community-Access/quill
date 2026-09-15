"""QuillLite's own stores: settings, recovery, file bytes, the inbox, bookmarks.

Everything here is wx-free and runs against real files in a temporary directory,
because the questions worth asking are about bytes and about what survives a
crash -- neither of which a window can answer.

The one that matters most is byte honesty. A Notepad replacement is judged on
it: open a file, change nothing, save it, and the bytes must be the bytes you
started with. Every combination that gets that wrong in a real editor -- a
dropped BOM, a UTF-8 file read as cp1252, CRLF silently becoming LF, a missing
final newline appearing from nowhere -- has a case below.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.lite import inbox, recovery
from quill.core.lite import settings as settings_mod
from quill.core.lite.filetypes import is_rich_path
from quill.core.lite.textfile import (
    ENCODING_CHOICES,
    NEWLINE_CHOICES,
    decode_text,
    encode_text,
    write_bytes_atomic,
)
from quill.core.numbered_bookmarks import MAX_BOOKMARKS, BookmarkSet, label_for


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point QuillLite's whole data folder at a temporary directory."""
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(tmp_path))
    return tmp_path


# -- byte honesty --------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "encoding", "newline"),
    [
        (b"plain ascii\r\n", "utf-8", "\r\n"),
        (b"unix lines\nsecond\n", "utf-8", "\n"),
        (b"\xef\xbb\xbfwith a bom\r\n", "utf-8-sig", "\r\n"),
        (b"\xff\xfea\x00b\x00", "utf-16", "\n"),
        (b"caf\xe9 in cp1252\r\n", "cp1252", "\r\n"),
        (b"caf\xc3\xa9 in utf-8\r\n", "utf-8", "\r\n"),
    ],
)
def test_every_file_shape_round_trips_byte_for_byte(
    raw: bytes, encoding: str, newline: str
) -> None:
    """The whole product, in one assertion, six times."""
    decoded = decode_text(raw)
    assert decoded.encoding == encoding
    assert decoded.newline == newline
    assert encode_text(decoded.text, encoding=encoding, newline=newline) == raw


def test_utf8_wins_over_cp1252_because_cp1252_can_never_fail() -> None:
    """The ordering rule, stated as a test.

    cp1252 decodes *any* byte sequence, so trying it before UTF-8 would mean
    never detecting UTF-8 at all -- and every accented character in every UTF-8
    file would come back as mojibake that then got written back that way.
    """
    assert decode_text("café".encode()).text == "café"
    assert decode_text("café".encode()).encoding == "utf-8"


def test_a_file_with_no_final_newline_does_not_grow_one() -> None:
    raw = b"no trailing newline"
    decoded = decode_text(raw)
    assert encode_text(decoded.text, encoding=decoded.encoding, newline=decoded.newline) == raw


def test_a_character_the_encoding_cannot_hold_is_replaced_not_refused() -> None:
    """A save that raises is a save that loses the document.

    An em dash typed into a cp1252 file has to go somewhere. A replacement
    character is visible and recoverable; a ``UnicodeEncodeError`` that aborts
    the save is not.
    """
    written = encode_text("an em dash —", encoding="cp1252", newline="\n")
    assert isinstance(written, bytes)
    assert b"?" in written or b"\x97" in written


def test_write_bytes_atomic_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    write_bytes_atomic(target, b"first")
    write_bytes_atomic(target, b"second")
    assert target.read_bytes() == b"second"
    assert [p.name for p in tmp_path.iterdir()] == ["notes.txt"]


def test_the_choosers_offer_only_encodings_the_reader_can_produce() -> None:
    """Every offered codec is one ``decode_text`` can actually report back."""
    reportable = {"utf-8", "utf-8-sig", "utf-16", "cp1252"}
    assert {codec for codec, _name in ENCODING_CHOICES} == reportable
    assert {value for value, _name in NEWLINE_CHOICES} == {"\r\n", "\n"}


def test_only_rtf_is_rich() -> None:
    assert is_rich_path("report.rtf") and is_rich_path("REPORT.RTF")
    for plain in ("notes.txt", "readme.md", "data.csv", "script.py", "no-extension"):
        assert not is_rich_path(plain), plain


# -- settings ------------------------------------------------------------------


def test_settings_round_trip_and_a_corrupt_file_gives_defaults(data_dir: Path) -> None:
    settings = settings_mod.load()
    settings.theme = "system"
    settings.font_size = 15
    settings.remember_recent("C:/notes.txt")
    settings_mod.save(settings)
    assert settings_mod.load().theme == "system"
    assert settings_mod.load().font_size == 15

    # An editor that refuses to open because its settings file has a stray
    # comma is an editor somebody loses work to.
    settings_mod.settings_path().write_text("{not json", encoding="utf-8")
    assert settings_mod.load().theme == "dark"


def test_out_of_range_values_are_clamped_not_rejected(data_dir: Path) -> None:
    settings_mod.settings_path().write_text(
        json.dumps({"font_size": 4000, "autosave_seconds": 1, "theme": "chartreuse"}),
        encoding="utf-8",
    )
    loaded = settings_mod.load()
    assert loaded.font_size == 72
    assert loaded.autosave_seconds == 15
    assert loaded.theme == "dark"


def test_a_bool_is_not_accepted_as_an_int(data_dir: Path) -> None:
    """``isinstance(True, int)`` is true in Python, and font_size 'True' is not 1."""
    settings_mod.settings_path().write_text(json.dumps({"font_size": True}), encoding="utf-8")
    assert settings_mod.load().font_size == 12


def test_recent_files_move_to_the_head_without_duplicating(data_dir: Path) -> None:
    settings = settings_mod.Settings()
    for path in ("a.txt", "b.txt", "a.txt"):
        settings.remember_recent(path)
    assert settings.recent_files[:2] == ["a.txt", "b.txt"]
    assert settings.recent_files.count("a.txt") == 1


# -- recovery ------------------------------------------------------------------


def test_a_written_slot_comes_back_and_a_discarded_one_does_not(data_dir: Path) -> None:
    slot = recovery.new_slot("plain", "C:/notes.txt")
    slot.content_path.write_text("unsaved work", encoding="utf-8")
    recovery.write_meta(slot)
    pending = recovery.pending()
    assert [s.original_path for s in pending] == ["C:/notes.txt"]
    assert pending[0].title == "notes.txt"
    recovery.discard(slot)
    assert recovery.pending() == []


def test_an_empty_slot_is_not_offered_back(data_dir: Path) -> None:
    """Offering it would replace a real document with nothing."""
    slot = recovery.new_slot("plain")
    slot.content_path.write_text("", encoding="utf-8")
    recovery.write_meta(slot)
    assert recovery.pending() == []
    assert not slot.meta_path.exists()


def test_a_clean_session_leaves_the_recovery_folder_empty(data_dir: Path) -> None:
    slot = recovery.new_slot("rich")
    slot.content_path.write_text("{\\rtf1}", encoding="utf-8")
    recovery.write_meta(slot)
    recovery.discard(slot)
    assert list(recovery.recovery_dir().glob("*")) == []


# -- the single-instance inbox -------------------------------------------------


def test_a_launch_with_files_asks_for_those_files(data_dir: Path) -> None:
    assert inbox.post_request([Path("a.txt"), Path("b.txt")], None)
    lines = inbox.read_requests()
    assert [Path(line).name for line in lines] == ["a.txt", "b.txt"]
    assert inbox.read_requests() == [], "a request must be consumed exactly once"


def test_a_launch_with_nothing_asks_for_a_window(data_dir: Path) -> None:
    """Otherwise starting the app again from the Start Menu appears to do nothing."""
    assert inbox.post_request([], None)
    assert inbox.read_requests() == [inbox.NEW_DEFAULT]


def test_an_explicit_mode_asks_for_a_window_in_that_mode(data_dir: Path) -> None:
    assert inbox.post_request([], "rich")
    assert inbox.read_requests() == [inbox.NEW_RICH]


def test_the_instance_marker_round_trips_and_clears(data_dir: Path) -> None:
    inbox.claim_instance_marker(4242)
    assert inbox.running_instance_pid() == 4242
    inbox.clear_instance_marker()
    assert inbox.running_instance_pid() == 0


# -- numbered bookmarks --------------------------------------------------------


def test_bookmarks_are_listed_in_document_order_not_by_number() -> None:
    marks = BookmarkSet()
    marks.set(3, 10, "later")
    marks.set(1, 200, "last")
    marks.set(2, 5, "first")
    assert [m.label for m in marks.all()] == ["first", "later", "last"]


def test_bookmarks_move_with_the_text_around_them() -> None:
    """A bookmark that is wrong is worse than one that does not exist."""
    marks = BookmarkSet()
    marks.set(1, 100, "middle")
    marks.shift(at=50, delta=+20)
    assert marks.get(1).position == 120
    marks.shift(at=50, delta=-20)
    assert marks.get(1).position == 100
    # A deletion that swallows a bookmark collapses it onto the deletion point
    # rather than dropping it silently.
    marks.shift(at=10, delta=-500)
    assert marks.get(1).position == 10


def test_a_bookmark_before_the_edit_does_not_move() -> None:
    marks = BookmarkSet()
    marks.set(1, 10, "early")
    marks.shift(at=100, delta=+50)
    assert marks.get(1).position == 10


def test_next_and_previous_wrap_around() -> None:
    marks = BookmarkSet()
    marks.set(1, 10, "a")
    marks.set(2, 90, "b")
    assert marks.next_after(95).position == 10
    assert marks.previous_before(5).position == 90


def test_the_slots_run_out_by_reusing_rather_than_refusing() -> None:
    marks = BookmarkSet()
    for number in range(1, MAX_BOOKMARKS + 1):
        marks.set(number, number * 10, f"m{number}")
    assert marks.next_free_number() == 1
    with pytest.raises(ValueError):
        marks.set(MAX_BOOKMARKS + 1, 0, "too many")


def test_a_bookmark_label_is_the_line_it_is_on() -> None:
    text = "first line\n\n   \nthe third real line"
    assert label_for(text, 2) == "first line"
    assert label_for(text, 12) == "(blank line)"
    assert label_for("", 0) == "(empty document)"


def test_only_what_differs_from_the_default_is_written(data_dir: Path) -> None:
    """The delta store, which is the whole reason this is not a plain dump.

    A file that spells out every field freezes today's defaults into every
    user's profile forever: change the default theme in 1.1 and the person who
    never expressed a preference does not move with it, because their file says
    "dark" rather than saying nothing.
    """
    settings_mod.save(settings_mod.Settings())
    on_disk = json.loads(settings_mod.settings_path().read_text(encoding="utf-8"))
    assert on_disk == {"schema": settings_mod.SCHEMA}, on_disk

    changed = settings_mod.Settings()
    changed.theme = "system"
    settings_mod.save(changed)
    on_disk = json.loads(settings_mod.settings_path().read_text(encoding="utf-8"))
    assert on_disk == {"schema": settings_mod.SCHEMA, "theme": "system"}, on_disk
    assert settings_mod.load().theme == "system"
    # And everything untouched still comes from code, not from the file.
    assert settings_mod.load().word_wrap is settings_mod.Settings().word_wrap


def test_a_file_from_a_future_version_still_opens(data_dir: Path) -> None:
    """Unknown keys are ignored rather than fatal: an editor must always open."""
    settings_mod.settings_path().write_text(
        json.dumps({"schema": 99, "theme": "system", "a_field_from_2027": True}),
        encoding="utf-8",
    )
    assert settings_mod.load().theme == "system"


# -- switchable feature areas --------------------------------------------------


def test_the_default_off_set_is_seeded_once_and_a_change_of_mind_sticks(
    data_dir: Path,
) -> None:
    from quill.core.lite import features as features_mod

    settings = features_mod.load_features(data_dir)
    assert not settings.is_enabled("autoformat")
    assert settings.is_enabled("rich_text"), "everything unlisted must default on"

    # Turning a default-off area ON must survive the next launch: seeding once
    # is the difference between "starts off" and "keeps switching itself off".
    settings.set_enabled("autoformat", True)
    features_mod.save_features(data_dir, settings)
    assert features_mod.load_features(data_dir).is_enabled("autoformat")


def test_every_area_the_command_table_names_actually_exists() -> None:
    """A command mapped to a typo'd area would be permanently invisible."""
    from quill.core.lite import features as features_mod
    from quill.core.lite.commands import COMMAND_AREA, MENU_AREA

    known = features_mod.area_ids()
    # "" is the explicit always-on answer -- a handler saying "whatever menu I
    # am in, I am not switchable" (Editor Font, in the rich-text Format menu).
    named = {area for area in set(COMMAND_AREA.values()) | set(MENU_AREA.values()) if area}
    assert named <= known, f"unknown areas: {sorted(named - known)}"


def test_switching_everything_off_still_leaves_a_usable_editor() -> None:
    """The floor, with every switch off. Four of the nine menus survive thin.

    Format is left holding Editor Font alone, which is Notepad's Format menu and
    the point: the face the editor draws in is not a rich-text feature. Insert
    keeps the date, a special character, an emoji and a line break -- four ways
    of putting a character in, none of which is a markup feature. Navigate keeps
    Back, Forward and the F6 route to the status bar, none of which belong to
    the headings or bookmarks areas. Tools keeps indenting -- an editor that
    cannot indent is broken rather than small -- and the two rows that switch
    everything else back on, which must never be switchable themselves.
    """
    from quill.core.lite.commands import menu_titles, visible_commands

    rows = visible_commands(lambda _area: False)
    menus = [menu for menu in menu_titles() if any(row[0] == menu for row in rows)]
    assert menus == [
        "&File",
        "&Edit",
        "&View",
        "&Insert",
        "F&ormat",
        "&Navigate",
        "&Tools",
        "&Window",
        "&Help",
    ], menus
    handlers = {row[3] for row in rows}
    for essential in (
        "cmd_new",
        "cmd_open",
        "cmd_save",
        "cmd_find",
        "cmd_context_help",
        "cmd_editor_font",
        "cmd_preferences",
        "cmd_customize_features",
        # The way back from having switched abbreviations off with the key.
        "cmd_toggle_abbreviations",
    ):
        assert essential in handlers, essential


def test_no_menu_is_left_with_only_separators_in_it() -> None:
    """Tidying is easy to forget and is read out loud when it is."""
    from quill.core.lite.commands import visible_commands

    for switch in (lambda _a: True, lambda _a: False, lambda a: a in {"tools", "printing"}):
        rows = visible_commands(switch)
        for menu in {row[0] for row in rows}:
            items = [row for row in rows if row[0] == menu]
            assert any(row[4] != "sep" for row in items), f"{menu} is only separators"
            assert items[0][4] != "sep", f"{menu} starts with a separator"
            assert items[-1][4] != "sep", f"{menu} ends with a separator"
            assert not any(
                a[4] == "sep" and b[4] == "sep" for a, b in zip(items, items[1:], strict=False)
            ), f"{menu} has two separators in a row"
