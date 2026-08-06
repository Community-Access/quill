"""Behavior tests for the Regular Expression Helper 2.0 dialog (#1328 P1)."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.regex_helper.catalog import CATEGORIES, recipes_by_category  # noqa: E402
from quill.ui.regex_helper_dialog import _explanation_text, _results_text  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_results_text_reads_matches_as_sentences() -> None:
    text = _results_text(r"\d+", "Call 555 then 911.", None)
    assert text.startswith("2 matches.")
    assert "Match 1: line 1, column 6: 555" in text
    assert "Match 2: line 1, column 15: 911" in text


def test_results_text_reports_pattern_errors_in_words() -> None:
    text = _results_text(r"(unclosed", "sample", None)
    assert "Unclosed group" in text
    assert "character 1" in text, "the diagnosis names the exact position"


def test_results_text_includes_replace_preview_for_templates() -> None:
    text = _results_text(r"(\w+), (\w+)", "Bishop, Jeff", r"\2 \1")
    assert "Replace preview" in text


def test_explanation_text_narrates_typed_patterns() -> None:
    text = _explanation_text(None, r"^\d+")
    assert text, "typed patterns must always be explained"
    lowered = text.lower()
    assert "digit" in lowered
    assert "start" in lowered


def test_explanation_text_diagnoses_broken_patterns() -> None:
    text = _explanation_text(None, r"(oops")
    assert "character" in text.lower() or "parenthesis" in text.lower()


def test_dialog_tree_holds_every_category(wx_app, monkeypatch) -> None:
    from quill.ui import regex_helper_dialog

    frame = wx.Frame(None)

    class _Editor:
        def GetStringSelection(self) -> str:
            return ""

        def GetValue(self) -> str:
            return "sample document text"

    class _Controller:
        _wx = wx

        def __init__(self) -> None:
            self.frame = frame
            self.editor = _Editor()
            self.statuses: list[str] = []
            self.seeded: dict[str, object] = {}

        def _set_status(self, message: str) -> None:
            self.statuses.append(message)

        def _copy_to_clipboard(self, _text: str) -> bool:
            return True

        def _show_modal_dialog(self, dialog: object, _label: str) -> int:
            # Inspect the fully built dialog instead of running a modal loop.
            tree = None
            for child in dialog.GetChildren():
                if isinstance(child, wx.TreeCtrl):
                    tree = child
                    break
            assert tree is not None, "the recipe tree must exist"
            root = tree.GetRootItem()
            categories = []
            item, cookie = tree.GetFirstChild(root)
            while item.IsOk():
                categories.append(tree.GetItemText(item))
                item, cookie = tree.GetNextChild(root, cookie)
            populated = {c for c in CATEGORIES if recipes_by_category().get(c)}
            assert len(categories) == len(populated), "one tree node per populated category"
            for label in categories:
                assert label.rsplit(" (", 1)[0] in populated
            return wx.ID_CLOSE

    controller = _Controller()
    try:
        regex_helper_dialog.open_regex_helper(controller)
    finally:
        frame.Destroy()
