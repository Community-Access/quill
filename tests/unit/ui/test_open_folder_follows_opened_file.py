"""The next Open dialog starts beside the file that was opened last.

The Open dialogs always remembered their own folder. A file opened any other
way -- from Explorer, the command line, a recent-files entry -- did not, so
the next Ctrl+O started wherever the last dialog had been.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import quill.ui.main_frame as main_frame_module
from quill.ui.main_frame import MainFrame


class _Stop(Exception):
    pass


def _bare_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._last_file_dir = ""
    frame._trusted_locations = set()
    frame._clear_empty_workspace_state = lambda: None  # type: ignore[method-assign]
    return frame


def test_a_freshly_opened_file_steers_the_next_open_dialog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "from explorer"
    folder.mkdir()
    target = folder / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    frame = _bare_frame()
    frame._pdf_open_needs_password = lambda *_a: False  # type: ignore[method-assign]

    def _stop(*_a: object, **_k: object) -> object:
        raise _Stop

    # Stop right after the document is accepted: the folder is remembered
    # before anything is installed into the window.
    frame._maybe_apply_illumination = _stop  # type: ignore[method-assign]

    with pytest.raises(_Stop):
        frame._finish_open_document(
            (object(), None),
            selected_path=target,
            suffix=".txt",
            existing_index=-1,
            record_recent=True,
            line=None,
            column=None,
        )

    assert frame._last_file_dir == str(folder)
    assert frame._file_dialog_default_dir() == str(folder)
    assert frame._simple_open_initial_dir() == folder


def test_reopening_a_file_already_in_a_tab_also_steers_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "already open.md"
    target.write_text("# Hi", encoding="utf-8")
    monkeypatch.setattr(main_frame_module, "is_trusted_location", lambda *_a: True)
    frame = _bare_frame()
    frame._find_tab_index = lambda _path: 0  # type: ignore[method-assign]
    frame._select_tab = lambda _index: None  # type: ignore[method-assign]
    frame._record_recent = lambda _path: None  # type: ignore[method-assign]
    frame._position_editor_at = lambda **_k: None  # type: ignore[method-assign]
    frame._set_status = lambda _text: None  # type: ignore[method-assign]

    frame.open_file(target)

    assert frame._last_file_dir == str(tmp_path)


def test_a_path_whose_folder_is_gone_leaves_the_last_folder_alone(tmp_path: Path) -> None:
    frame = _bare_frame()
    frame._last_file_dir = str(tmp_path)
    frame._remember_open_folder(tmp_path / "missing" / "file.txt")
    assert frame._last_file_dir == str(tmp_path)
