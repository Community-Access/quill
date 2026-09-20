"""Session restore, the recovery question, and read-only at open (bad.md P2.12).

Three promises about what happens when you *arrive*:

* QUILL reopens last session's documents, unless you named a file -- somebody
  who double-clicked a file asked for that file, and burying it under
  yesterday's four answers a different question (G4).
* QuillLite offers last session's unsaved work back instead of reopening every
  slot unasked: after a crash, four windows appearing unbidden is four things
  to identify before you can work (F14).
* Both say, at open, when a file cannot be saved back -- rather than at
  `Ctrl+S`, twenty minutes later.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from quill.core.file_access import READ_ONLY_NOTICE, is_read_only
from quill.core.settings import Settings


def test_a_writable_file_is_not_read_only(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    assert is_read_only(target) is False


def test_a_read_only_file_is(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    target.chmod(stat.S_IREAD)
    try:
        assert is_read_only(target) is True
    finally:
        target.chmod(stat.S_IREAD | stat.S_IWRITE)


def test_a_file_that_does_not_exist_yet_is_not_read_only(tmp_path: Path) -> None:
    """A new document is new, not locked."""
    assert is_read_only(tmp_path / "nothing-here.txt") is False
    assert is_read_only(None) is False


def test_the_notice_names_the_consequence_not_the_state() -> None:
    """ "read-only" is a phrase people read past; Save As is what they need."""
    assert "Save As" in READ_ONLY_NOTICE


def test_both_editors_say_the_same_sentence() -> None:
    root = Path(__file__).resolve().parents[3]
    quill = (root / "quill" / "ui" / "main_frame_power_tools.py").read_text(encoding="utf-8")
    lite = (root / "quill" / "apps" / "lite_window_file.py").read_text(encoding="utf-8")
    assert "READ_ONLY_NOTICE" in quill
    assert "READ_ONLY_NOTICE" in lite


def test_the_session_settings_exist_with_quilllites_defaults() -> None:
    settings = Settings()
    assert settings.restore_session is True
    assert settings.session_files == []


def test_the_session_list_is_bounded_and_clean() -> None:
    loaded = Settings.from_dict({"session_files": ["a.txt", "  ", "b.txt"] + ["x"] * 30})
    assert "  " not in loaded.session_files
    assert len(loaded.session_files) <= 20


def test_a_nonsense_session_list_is_ignored_rather_than_crashing() -> None:
    assert Settings.from_dict({"session_files": "not-a-list"}).session_files == []


def test_quill_remembers_and_restores() -> None:
    import inspect

    from quill.ui.main_frame import MainFrame

    remember = inspect.getsource(MainFrame.remember_session)
    assert "self.settings.session_files = paths[:20]" in remember
    # Saved documents only: an untitled tab has nothing to reopen *from*.
    assert 'getattr(document, "path", None)' in remember

    # A deleted file used to be skipped in silence here. Since 2026-09-19 it is a
    # row in the chooser instead -- "it did not open" and "it opened and I have
    # not found it" sound identical, which is the one case silence actively
    # misled. What this test can still hold is that the restore consults the
    # shared decision rather than reimplementing it: the behaviour itself is
    # tested against real files in tests/unit/ui/test_session_restore_frame.py
    # and tests/unit/apps/test_lite_session_restore.py.
    restore = inspect.getsource(MainFrame.restore_session)
    assert "should_ask(" in restore
    assert 'getattr(self.settings, "restore_session", True)' in restore


def test_a_file_on_the_command_line_wins() -> None:
    import inspect

    from quill.ui.main_frame import run_app

    source = inspect.getsource(run_app)
    assert "named_a_file = True" in source
    assert "if not named_a_file:" in source
    assert source.index("named_a_file = True") < source.index("frame.restore_session()")


def test_quilllite_asks_before_restoring_unsaved_work() -> None:
    import inspect

    from quill.apps.lite import QuillLiteApp

    source = inspect.getsource(QuillLiteApp._restore_pending_work)
    assert "self._confirm_recovery(slots)" in source
    # Declining keeps the slots: "not now" must not be able to lose anything.
    assert "It will be offered again next time." in source


def test_the_question_names_what_it_found() -> None:
    import inspect

    from quill.apps.lite import QuillLiteApp

    source = inspect.getsource(QuillLiteApp._confirm_recovery)
    assert "an untitled document" in source
    assert "unsaved work from" in source


def test_read_only_detection_survives_a_permission_error(tmp_path: Path, monkeypatch) -> None:
    """Unanswerable means "not read-only": saying nothing beats refusing a save."""

    def _boom(*_args, **_kwargs):
        raise OSError("no")

    monkeypatch.setattr(os.path, "exists", _boom, raising=False)
    monkeypatch.setattr(Path, "exists", lambda self: (_ for _ in ()).throw(OSError("no")))
    assert is_read_only(tmp_path / "x.txt") is False
