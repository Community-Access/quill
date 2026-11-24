"""FUX-10 in Quill Converter and Quill Studio: F1 says the selected row's situation.

Converter's queue keeps the last run's result for each file, and F1 on a row
says it. Studio's Your Books tree says a group row opens nothing and a moved
book cannot open, and the Chapter Workbench list has one help text again (a
second ``SetHelpText`` used to replace the first). Fakes throughout.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.apps import converter_row_help
from quill.core.audio_studio import library_row_help
from quill.ui import app_context_help

REPO = Path(__file__).resolve().parents[3]

# -- Quill Converter ----------------------------------------------------------------


def _result(source: str, *, ok: bool = True, error: str = "", skipped: bool = False) -> Any:
    job = SimpleNamespace(source=Path(source), dest=Path(source).with_suffix(".mp3"))
    return SimpleNamespace(job=job, ok=ok, error=error, skipped=skipped)


def _queue(entries: list[str], selected: int) -> Any:
    return SimpleNamespace(
        _entries=[(Path(entry), None) for entry in entries],
        _list=SimpleNamespace(GetSelection=lambda: selected),
    )


def test_converter_says_nothing_before_the_first_run() -> None:
    assert converter_row_help.describe_selected_row(_queue(["C:/a/talk.wav"], 0)) == ""


def test_converter_f1_says_a_file_converted_and_to_what() -> None:
    host = _queue(["C:/a/talk.wav"], 0)
    converter_row_help.remember(host, [_result("C:/a/talk.wav")])
    said = app_context_help.selection_help_of(host._list)
    assert said == "Last time, this file converted to talk.mp3."


def test_converter_f1_says_why_a_file_failed() -> None:
    host = _queue(["C:/a/talk.wav"], 0)
    converter_row_help.remember(
        host, [_result("C:/a/talk.wav", ok=False, error="input file not found")]
    )
    assert converter_row_help.describe_selected_row(host) == (
        "Last time, this file failed: input file not found. Ctrl+R has the full report."
    )


def test_converter_f1_counts_the_parts_of_a_file_split_by_chapters() -> None:
    host = _queue(["C:/a/book.m4b"], 0)
    one, two = _result("C:/a/book.m4b"), _result("C:/a/book.m4b", ok=False, error="Full.")
    converter_row_help.remember(host, [one, two])
    assert converter_row_help.describe_selected_row(host) == (
        "Last time, this file was split into 2 parts: 1 converted, 1 failed. "
        "Ctrl+R has the full report."
    )


def test_converter_f1_says_a_file_was_skipped_when_stopped() -> None:
    host = _queue(["C:/a/talk.wav"], 0)
    converter_row_help.remember(host, [_result("C:/a/talk.wav", ok=False, skipped=True)])
    assert "skipped, because the conversion was stopped" in (
        converter_row_help.describe_selected_row(host)
    )


def test_converter_f1_counts_a_folders_files() -> None:
    host = _queue(["C:/a/talk.wav", "C:/b"], 1)
    converter_row_help.remember(
        host,
        [
            _result("C:/a/talk.wav"),
            _result("C:/b/one.wav"),
            _result("C:/b/sub/two.wav", ok=False, error="Bad."),
            _result("C:/b/three.wav", ok=False, skipped=True),
        ],
    )
    assert converter_row_help.describe_selected_row(host) == (
        "Last time, of the files in this folder: 1 converted, 1 failed, 1 skipped. "
        "Ctrl+R has the full report."
    )


def test_converter_keeps_the_results_when_a_run_finishes() -> None:
    from quill.apps.converter_actions import ConverterActionsMixin

    host = _queue(["C:/a/talk.wav"], 0)
    host._end_work = lambda: None
    host._report_text = lambda *_a: "report"
    host._set_status = host._announce = lambda *_a, **_k: None
    host._settings = SimpleNamespace(open_folder_when_done=False)
    result = SimpleNamespace(
        results=[_result("C:/a/talk.wav")], failed=0, converted=1, summary=lambda _n: "Done."
    )
    ConverterActionsMixin._finish_batch(host, result, 1, Path("C:/out"), "", 1.0)
    assert app_context_help.selection_help_of(host._list).startswith("Last time, this file")


# -- Quill Studio -------------------------------------------------------------------


class _Item:
    def IsOk(self) -> bool:  # noqa: N802 - wx's name
        return True


class _Tree:
    def __init__(self, data: tuple[str, str], text: str = "") -> None:
        self._data, self._text = data, text

    def GetSelection(self) -> _Item:  # noqa: N802 - wx's name
        return _Item()

    def GetItemData(self, _item: _Item) -> tuple[str, str]:  # noqa: N802 - wx's name
        return self._data

    def GetItemText(self, _item: _Item) -> str:  # noqa: N802 - wx's name
        return self._text


def test_studio_f1_on_a_group_row_says_enter_opens_nothing() -> None:
    from quill.apps.studio_library_window import describe_selected_row

    for kind in ("view", "folder"):
        assert describe_selected_row(_Tree((kind, "favorites"))) == library_row_help.GROUP_ROW


def test_studio_f1_on_a_book_that_moved_says_so(tmp_path: Path) -> None:
    from quill.apps.studio_library_window import describe_selected_row

    gone = tmp_path / "gone.m4b"
    said = describe_selected_row(_Tree(("book", str(gone)), "Gone Book"))
    assert said.startswith("Gone Book is no longer where it was;")
    assert "Enter only warns that it is gone." in said
    assert "no file is deleted" in said


def test_studio_f1_on_a_book_that_is_there_adds_nothing(tmp_path: Path) -> None:
    from quill.apps.studio_library_window import describe_selected_row

    here = tmp_path / "here.m4b"
    here.write_bytes(b"")
    assert describe_selected_row(_Tree(("book", str(here)), "Here")) == ""


def test_studio_enter_on_a_group_says_it_is_a_group() -> None:
    from quill.apps.studio_library_window import enter_without_book

    assert enter_without_book(_Tree(("view", "favorites"))) == (
        "This is a group; arrow down to a book."
    )
    assert enter_without_book(None).startswith("No book selected.")


def test_studio_says_a_missing_book_one_way_everywhere() -> None:
    from quill.apps.studio import StudioAppFrame

    assert StudioAppFrame._missing_book_announcement("A") == library_row_help.missing_book("A")


def test_chapter_workbench_list_has_one_help_text_that_says_enter_plays() -> None:
    path = REPO / "quill/ui/audio_studio/chapter_workbench.py"
    texts = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "SetHelpText"
            and ast.unparse(node.func.value) == "self._chapter_list"
        ):
            texts.append(ast.literal_eval(node.args[0]))
    assert len(texts) == 1
    assert "Enter plays the chapter" in texts[0]
    assert "nudges" in texts[0]


def test_studio_library_window_opens_and_its_tree_answers_f1() -> None:
    """Ctrl+Alt+Y imported a module that does not exist, so the window never opened."""
    import pytest

    wx = pytest.importorskip("wx")
    from tests.wx_session import shared_wx_app

    shared_wx_app()
    from quill.apps.studio_library_window import ensure_library_window

    def fill(tree: Any = None) -> None:
        return None

    frame, tree = ensure_library_window(
        parent=None,
        title="Quill Studio Library",
        existing=None,
        reload_tree=fill,
        on_activate=lambda _e: None,
        on_context_menu=lambda _e: None,
        on_key=lambda e: e.Skip(),
        on_destroy=lambda: None,
    )
    try:
        assert isinstance(tree, wx.TreeCtrl)
        assert app_context_help.selection_help_of(tree) == ""  # nothing selected yet
        assert callable(getattr(tree, "_quill_selection_help", None))
    finally:
        frame.Destroy()


def test_studio_library_window_is_filled_once_its_tree_is_known(monkeypatch) -> None:
    """The window called the app's no-argument reload with the tree (a TypeError),
    and before the app knew the tree, so Your Books opened empty."""
    from quill.apps import studio_library_window
    from quill.apps.studio import StudioAppFrame

    calls: list[Any] = []

    def fake_ensure(**kwargs: Any) -> tuple[str, str]:
        kwargs["reload_tree"]("tree")  # the window's own call, with the tree
        return "frame", "tree"

    monkeypatch.setattr(studio_library_window, "ensure_library_window", fake_ensure)
    host = SimpleNamespace(
        frame=None,
        _on_tree_activate=None,
        _on_tree_context_menu=None,
        _on_tree_key=None,
    )
    host._reload_library_tree = lambda: calls.append(host._library_tree)
    StudioAppFrame._open_library_window(host)
    assert calls == ["tree"]
