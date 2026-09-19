"""The three magical-tier commands, in the frame (bad.md P3.7, P0.6c).

Each one exists because a screen reader is silent about something only the
application knows, and the tests are about the distinctions a listener cannot
make for themselves: whether an undo did anything, whether a command changed
anything, whether this document has headings at all.
"""

from __future__ import annotations

import pytest

from quill.core.document_text import DocumentText
from quill.core.metrics import compute_document_stats
from quill.ui.main_frame import MainFrame
from quill.ui.main_frame_magical import MagicalTierMixin


class _Editor:
    def __init__(self, text: str, *, can_undo: bool = True) -> None:
        self.text = text
        self._can_undo = can_undo
        self.undos = 0

    def CanUndo(self) -> bool:
        return self._can_undo

    def Undo(self) -> None:
        self.undos += 1


class _Host(MagicalTierMixin):
    def __init__(self, text: str = "hello world", *, can_undo: bool = True) -> None:
        self.editor = _Editor(text, can_undo=can_undo)
        self.announced: list[str] = []
        self.doc_text = DocumentText(lambda: self.editor.text)
        self._mode = "plain"
        self._kind = "markdown"
        self._read_only = False
        self._headings: list[object] = []

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _statusbar_document_stats(self) -> object:
        return compute_document_stats(self.editor.text)

    def _current_editor_mode(self) -> str:
        return self._mode

    def _effective_markup_kind(self) -> str:
        return self._kind

    def _document_is_read_only(self) -> bool:
        return self._read_only

    def _outline_entries(self) -> list[object]:
        return self._headings


# -- what is this document? ----------------------------------------------------


def test_the_summary_names_the_kind_the_size_and_the_shape() -> None:
    host = _Host("# Title\n- one\n- two\n")
    host._headings = [object()]

    host.describe_this_document()

    said = host.announced[0]
    assert said.startswith("Markdown: ")
    assert "1 heading and 2 list items" in said


def test_rich_mode_is_named_rich_text() -> None:
    host = _Host("text")
    host._mode = "rich"
    host.describe_this_document()
    assert host.announced[0].startswith("Rich Text: ")


def test_a_read_only_document_says_so_in_the_summary() -> None:
    host = _Host("text")
    host._read_only = True
    host.describe_this_document()
    assert host.announced[0].endswith("Read-only.")


def test_no_document_at_all_is_answered() -> None:
    host = _Host()
    host._statusbar_document_stats = lambda: None  # type: ignore[method-assign]
    host.describe_this_document()
    assert host.announced == ["No document is open."]


def test_a_broken_outline_does_not_break_the_summary() -> None:
    """A summary must never be the thing that fails."""
    host = _Host("text")

    def _boom() -> list[object]:
        raise RuntimeError("no outline here")

    host._outline_entries = _boom  # type: ignore[method-assign]
    host.describe_this_document()
    assert host.announced and "word" in host.announced[0]


# -- what changed? -------------------------------------------------------------


def test_nothing_recorded_is_answered_rather_than_silent() -> None:
    host = _Host()
    host.describe_last_change()
    assert host.announced == ["Nothing has changed this document yet."]


def test_the_last_change_is_described_in_the_commands_own_words() -> None:
    host = _Host()
    host.doc_text.record("Sorted lines ascending", "b\na", "a\nb", position=0)

    host.describe_last_change()

    assert "Sorted lines ascending" in host.announced[0]
    assert "same length" in host.announced[0]


# -- undo and say --------------------------------------------------------------


def test_an_undo_with_nothing_to_undo_says_so_and_does_nothing() -> None:
    host = _Host(can_undo=False)
    host.doc_text.record("Sorted lines", "b\na", "a\nb")

    host.undo_and_say_what_changed()

    assert host.editor.undos == 0
    assert host.announced == ["Nothing left to undo."]


def test_an_undo_undoes_and_says_what_it_took_back() -> None:
    host = _Host()
    host.doc_text.record("Removed duplicate lines", "a\na\nb", "a\nb")

    host.undo_and_say_what_changed()

    assert host.editor.undos == 1
    said = host.announced[0]
    assert said.startswith("Undone: Removed duplicate lines")
    assert "+1 lines" in said


def test_an_undo_with_no_journal_still_confirms_it_happened() -> None:
    host = _Host()
    host.undo_and_say_what_changed()
    assert host.editor.undos == 1
    assert host.announced == ["Undone."]


# -- the wiring ----------------------------------------------------------------


def test_all_three_reach_the_frame_and_have_keys() -> None:
    from quill.core.feature_command_map import COMMAND_FEATURE_MAP
    from quill.core.keymap import DEFAULT_KEYMAP

    for command_id, method in (
        ("view.describe_this_document", "describe_this_document"),
        ("view.describe_last_change", "describe_last_change"),
        ("edit.undo_and_say", "undo_and_say_what_changed"),
    ):
        assert hasattr(MainFrame, method), method
        assert DEFAULT_KEYMAP.get(command_id), command_id
        assert COMMAND_FEATURE_MAP.get(command_id) == "core.accessibility", command_id


def test_the_fourth_of_the_four_already_shipped() -> None:
    """Repeat Last Announcement is #1304; P3.7 approved four, three were new."""
    from quill.core.keymap import DEFAULT_KEYMAP

    assert hasattr(MainFrame, "repeat_last_announcement")
    assert "app.repeat_last_announcement" in DEFAULT_KEYMAP


def test_every_rewrite_quill_does_passes_through_the_journal() -> None:
    """The source contract P3.7 depends on: one place records, so one place knows."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    body = source[source.index("    def _replace_document_text(self") :][:3000]
    assert "self.record_edit(" in body
    # Recorded BEFORE the write, because afterwards the old text is gone.
    assert body.index("self.record_edit(") < body.index("self._atomic_replace(")


@pytest.mark.parametrize(
    "command_id",
    ["view.describe_this_document", "view.describe_last_change", "edit.undo_and_say"],
)
def test_each_command_has_a_menu_home(command_id: str) -> None:
    from pathlib import Path

    menu = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_menu.py").read_text(
        encoding="utf-8"
    )
    assert f'"{command_id}"' in menu, f"{command_id} has no menu row"
