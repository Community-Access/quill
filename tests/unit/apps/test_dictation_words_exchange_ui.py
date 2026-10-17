"""Import, Export and the shared word list in My Words and Phrases (dict.md D-12).

The flows in ``quill/ui/dictation_words_exchange.py`` take their file chooser
and their preview as arguments, so these drive the real decisions with fakes:
no file dialog opens and nothing is typed anywhere. The window itself is
built in memory to check its controls, labels and help.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.windows_dictation.words_exchange import BACKUP_NAME, SharedWords
from quill.core.windows_dictation.words_file import WordsFile, load_words, save_words
from quill.ui import dictation_words_exchange as exchange


class _Said(list):
    def __call__(self, text: str) -> None:
        self.append(text)


def _confirm(answer: bool, seen: list[Any]) -> Any:
    def confirm(_parent: Any, plan: Any, title: str, action: str) -> bool:
        seen.append((plan, title, action))
        return answer

    return confirm


def test_export_writes_the_chosen_file_and_says_how_many(tmp_path: Path) -> None:
    said = _Said()
    words = WordsFile(words=["NVDA", "JAWS"], phrases=[("my email", "me@example.com")])
    out = exchange.run_export(None, words, said, choose=lambda _p: tmp_path / "words.csv")
    assert out == tmp_path / "words.csv"
    assert said == ["Exported 3 entries to words.csv."]
    assert out.read_text(encoding="utf-8-sig").startswith("say,write,kind")


def test_export_of_an_empty_list_says_so_and_asks_for_no_file() -> None:
    said = _Said()
    asked: list[Any] = []
    exchange.run_export(None, WordsFile(), said, choose=lambda p: asked.append(p))
    assert asked == [] and "Nothing to export" in said[0]


def test_import_previews_then_merges_backs_up_and_counts(tmp_path: Path) -> None:
    list_path = tmp_path / "dictation.md"
    words = WordsFile(words=["a", "b", "c"])
    save_words(list_path, words)
    before = list_path.read_bytes()
    source = tmp_path / "from-work.md"
    save_words(source, WordsFile(words=list("abcdefghijklmno")))
    said, seen = _Said(), []

    changed = exchange.run_import(
        None, list_path, words, said, choose=lambda _p: source, confirm=_confirm(True, seen)
    )
    assert changed
    assert said == ["Imported 12 words, 3 already there."]
    ((plan, title, action),) = seen
    assert (len(plan.new), title, action) == (12, "Import Words", "Add Them")
    assert load_words(list_path).words == list("abcdefghijklmno")
    assert (tmp_path / BACKUP_NAME).read_bytes() == before  # one import can be undone


def test_cancelling_the_preview_changes_nothing(tmp_path: Path) -> None:
    list_path = tmp_path / "dictation.md"
    words = WordsFile(words=["a"])
    save_words(list_path, words)
    source = tmp_path / "new.csv"
    source.write_text("say,write\nb,\n", encoding="utf-8")
    said: _Said = _Said()
    assert not exchange.run_import(
        None, list_path, words, said, choose=lambda _p: source, confirm=_confirm(False, [])
    )
    assert words.words == ["a"] and load_words(list_path).words == ["a"]
    assert said == [] and not (tmp_path / BACKUP_NAME).exists()


def test_a_file_with_nothing_new_is_said_without_a_preview(tmp_path: Path) -> None:
    source = tmp_path / "same.md"
    save_words(source, WordsFile(words=["a"]))
    said, seen = _Said(), []
    exchange.run_import(
        None,
        tmp_path / "d.md",
        WordsFile(words=["a"]),
        said,
        choose=lambda _p: source,
        confirm=_confirm(True, seen),
    )
    assert seen == [] and said[0].startswith("Nothing new in same.md")


def test_a_file_that_is_not_a_word_list_is_refused_out_loud(tmp_path: Path) -> None:
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nNothing here.\n", encoding="utf-8")
    said = _Said()
    exchange.run_import(None, tmp_path / "d.md", WordsFile(), said, choose=lambda _p: source)
    assert said[0].startswith("No words, phrases or corrections were found in notes.md")
    assert "QUILL-" not in said[0]  # the sentence, not the code


def _shared(tmp_path: Path) -> tuple[SharedWords, dict[str, bool]]:
    state = {"on": False}
    shared = SharedWords(
        own_path=tmp_path / "lite" / "dictation.md",
        shared_path=tmp_path / "quill" / "dictation.md",
        is_on=lambda: state["on"],
        set_on=lambda on: state.__setitem__("on", on),
    )
    return shared, state


def test_using_the_shared_list_merges_your_words_into_it(tmp_path: Path) -> None:
    shared, state = _shared(tmp_path)
    save_words(shared.own_path, WordsFile(words=["Okonkwo", "NVDA"]))
    save_words(shared.shared_path, WordsFile(words=["NVDA", "JAWS"]))
    said, seen = _Said(), []
    assert exchange.switch_shared(None, shared, True, said, confirm=_confirm(True, seen))
    assert state["on"] and shared.current_path() == shared.shared_path
    assert seen[0][1:] == ("Use the Shared Word List", "Use the Shared List")
    assert load_words(shared.shared_path).words == ["NVDA", "JAWS", "Okonkwo"]
    assert said == ["Now using the shared word list: 3 words. 1 word of yours added to it."]

    said.clear()
    assert exchange.switch_shared(None, shared, False, said)
    assert not state["on"]
    assert load_words(shared.own_path).words == ["Okonkwo", "NVDA"]  # never changed
    assert said == ["Now using QUILL Lite's own word list: 2 words."]


def test_declining_the_shared_preview_keeps_your_own_list(tmp_path: Path) -> None:
    shared, state = _shared(tmp_path)
    save_words(shared.own_path, WordsFile(words=["Okonkwo"]))
    said = _Said()
    assert not exchange.switch_shared(None, shared, True, said, confirm=_confirm(False, []))
    assert not state["on"] and not shared.shared_path.exists()
    assert said == ["Nothing changed. QUILL Lite keeps its own word list."]


# -- the window, built in memory -------------------------------------------------


@pytest.fixture
def parent(wx_app):
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()  # SetHelpText stores nothing without one
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


def _labels(window: wx.Window) -> dict[str, wx.Window]:
    return {child.GetLabel(): child for child in window.GetChildren()}


def test_the_window_has_import_and_export_with_help_and_free_access_keys(
    parent, tmp_path: Path
) -> None:
    from quill.ui.dictation_words_dialog import DictationWordsDialog

    dialog = DictationWordsDialog(parent, tmp_path / "dictation.md", say=_Said())
    try:
        labels = _labels(dialog)
        for label in ("&Import...", "E&xport..."):
            assert labels[label].GetHelpText()
        assert dialog.shared_box is None  # only QUILL Lite offers the shared list
        keys = [
            text[text.index("&") + 1].lower()
            for text in labels
            if "&" in text and not text.startswith("&&")
        ]
        assert len(keys) == len(set(keys)), keys  # GATE-14
    finally:
        dialog.Destroy()


def test_in_quill_lite_the_shared_box_switches_the_list(parent, tmp_path: Path) -> None:
    from quill.ui.dictation_words_dialog import DictationWordsDialog

    shared, state = _shared(tmp_path)
    save_words(shared.own_path, WordsFile(words=["Mine"]))
    save_words(shared.shared_path, WordsFile(words=["Mine", "Family"]))
    said = _Said()
    dialog = DictationWordsDialog(parent, shared.own_path, say=said, shared=shared)
    try:
        assert dialog.shared_box is not None and dialog.shared_box.GetHelpText()
        assert dialog.list.GetCount() == 1
        dialog.shared_box.SetValue(True)
        dialog._on_shared(None)
        assert state["on"] and dialog.path == shared.shared_path
        assert dialog.list.GetCount() == 2
        assert said[-1] == "Now using the shared word list: 2 words."
    finally:
        dialog.Destroy()


def test_the_preview_puts_the_counts_on_the_list_label(parent) -> None:
    from quill.core.windows_dictation.words_exchange import plan_merge

    plan = plan_merge(WordsFile(words=["a"]), WordsFile(words=["a", "b"]))
    dialog = exchange.ImportPreviewDialog(parent, plan, "Import Words", "Add Them")
    try:
        labels = _labels(dialog)
        assert "1 word will be added. 1 already in your list. &New entries:" in labels
        assert dialog.list.GetStrings() == ["Word: b"]
        assert labels["Add Them"].GetHelpText() and labels["Cancel"].GetHelpText()
    finally:
        dialog.Destroy()
