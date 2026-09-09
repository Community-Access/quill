"""Earlier Versions: the half of backups that was missing.

QuillLite has written a dated copy of every save since backups shipped, and
offered no way to read one. The files were correct and correctly named, and
getting at one meant knowing where the app keeps them, which of the hashed
folders was yours, and how to open a ``.bak``. A safety net nobody can reach is
not a safety net -- it is a folder that fills up.

Two things are worth testing beyond "the list appears", and both are about not
making things worse for somebody who is already trying to recover something:

* **Restore does not save.** It goes on the control's undo stack and leaves the
  file on disk alone, so choosing the wrong version costs one Ctrl+Z rather than
  the document.
* **A version that has gone is said out loud.** Backups are pruned, so a row can
  outlive its file between the list being built and a choice being made.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.apps.lite_window_tools import DocumentToolsMixin
from quill.core.lite import backups
from quill.core.version_history import speakable_when, version_label


class _Control:
    def __init__(self, text: str) -> None:
        self._text = text
        self._cursor = 0
        self.focused = False

    def GetValue(self) -> str:
        return self._text

    def GetLastPosition(self) -> int:
        return len(self._text)

    def GetInsertionPoint(self) -> int:
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = position

    def SetFocus(self) -> None:
        self.focused = True

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]


class _App:
    def __init__(self, *, backups_on: bool = True) -> None:
        self._on = backups_on

    def feature_enabled(self, area: str) -> bool:
        return self._on if area == "backups" else True


class _Window(DocumentToolsMixin):
    """The tools mixin, over stand-ins for the app and the control."""

    def __init__(self, path: Path | None, text: str, *, backups_on: bool = True) -> None:
        self.app = _App(backups_on=backups_on)
        self.path = path
        self.control = _Control(text)
        self.announcements: list[str] = []
        self.modified = False

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_modified(self, value: bool) -> None:
        self.modified = value

    def _touch_status(self) -> None:
        pass


@pytest.fixture
def lite_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(tmp_path / "data"))
    return tmp_path


# --------------------------------------------------------------------------- #
# The store: reading back what write_backup wrote
# --------------------------------------------------------------------------- #


def test_a_backup_reads_back_exactly_what_was_written(lite_data: Path) -> None:
    doc = lite_data / "notes.txt"
    doc.write_text("current", encoding="utf-8")

    written = backups.write_backup(doc, "an earlier draft\nwith two lines\n")

    assert written is not None
    assert backups.read_backup(written) == "an earlier draft\nwith two lines\n"


def test_non_ascii_survives_whatever_the_document_encoding_is(lite_data: Path) -> None:
    """Backups are always UTF-8; that is the whole reason they can be read back."""
    doc = lite_data / "accents.txt"
    doc.write_text("x", encoding="utf-8")

    written = backups.write_backup(doc, "café — naïve — 日本語")

    assert backups.read_backup(written) == "café — naïve — 日本語"


def test_the_timestamp_comes_out_of_the_filename(lite_data: Path) -> None:
    """So a list of twenty versions costs no reads at all."""
    doc = lite_data / "notes.txt"
    doc.write_text("x", encoding="utf-8")
    written = backups.write_backup(doc, "text")

    saved = backups.backup_saved_at(written)

    assert saved is not None
    # Written just now, and carrying a real timezone rather than a naive guess.
    assert saved.tzinfo is not None
    assert abs((datetime.now(UTC) - saved).total_seconds()) < 120


def test_a_file_that_is_not_ours_is_refused_rather_than_misdated(tmp_path: Path) -> None:
    """A plausible wrong date is worse than an honest refusal."""
    stray = tmp_path / "my-own-notes.bak"
    stray.write_text("hello", encoding="utf-8")

    assert backups.backup_saved_at(stray) is None


def test_a_missing_backup_reads_as_none_rather_than_raising(tmp_path: Path) -> None:
    """Backups are pruned; a row can outlive its file."""
    assert backups.read_backup(tmp_path / "gone.bak") is None


def test_the_collision_suffix_does_not_break_the_timestamp(lite_data: Path) -> None:
    """Two saves inside one microsecond get a "-1"; both must still date."""
    doc = lite_data / "fast.txt"
    doc.write_text("x", encoding="utf-8")
    first = backups.write_backup(doc, "one")
    collided = first.with_name(first.stem + "-1.bak")
    collided.write_text("two", encoding="utf-8")

    assert backups.backup_saved_at(collided) == backups.backup_saved_at(first)


# --------------------------------------------------------------------------- #
# The phrasing, shared with QUILL's own Restore Previous Version
# --------------------------------------------------------------------------- #


def test_today_and_yesterday_are_named_rather_than_dated() -> None:
    """Nobody thinks of this morning's save by its date."""
    now = datetime(2026, 9, 9, 18, 0).astimezone()
    assert speakable_when(now.replace(hour=16, minute=12), now) == "Today at 4:12 PM"
    yesterday = now.replace(day=8, hour=9, minute=5)
    assert speakable_when(yesterday, now) == "Yesterday at 9:05 AM"
    older = now.replace(month=8, day=30, hour=13, minute=40)
    assert speakable_when(older, now) == "August 30, 2026 at 1:40 PM"


def test_the_row_leads_with_when_and_then_the_size() -> None:
    """Front-loaded: arrowing a list, the first syllable has to distinguish it."""
    now = datetime(2026, 9, 9, 18, 0).astimezone()
    row = version_label(now.replace(hour=16, minute=12), words=2341)
    assert row == "Today at 4:12 PM - 2,341 words"
    assert version_label(now, words=1).endswith("1 word")


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


def test_with_backups_switched_off_it_says_where_to_switch_them_on() -> None:
    """An area that is off owns nothing, and silence would look like a dead key."""
    win = _Window(Path("notes.txt"), "text", backups_on=False)

    win.cmd_browse_backups()

    assert "Customize Features" in win.announcements[0]


def test_an_unsaved_document_is_told_why_there_is_nothing_to_show() -> None:
    win = _Window(None, "text")

    win.cmd_browse_backups()

    assert win.announcements == [
        "Save this document once and its earlier versions are kept from then on"
    ]


def test_no_backups_yet_names_the_document_rather_than_going_quiet(lite_data: Path) -> None:
    doc = lite_data / "fresh.txt"
    doc.write_text("text", encoding="utf-8")
    win = _Window(doc, "text")

    win.cmd_browse_backups()

    assert win.announcements == ["No earlier versions of fresh.txt yet"]


def test_restoring_replaces_the_text_undoably_and_writes_nothing(lite_data: Path) -> None:
    """Restore must not save: the file on disk is the user's last safe copy."""
    doc = lite_data / "notes.txt"
    doc.write_text("what is on disk", encoding="utf-8")
    win = _Window(doc, "what is in the window")

    win._restore_backup("an earlier draft")

    assert win.control.GetValue() == "an earlier draft"
    assert win.control.GetInsertionPoint() == 0
    assert win.modified is True
    assert doc.read_text(encoding="utf-8") == "what is on disk", "restore must not save"
    # And the user is told they can back out, because they cannot see that.
    assert "Control Z" in win.announcements[-1]
    assert "until you save" in win.announcements[-1]
