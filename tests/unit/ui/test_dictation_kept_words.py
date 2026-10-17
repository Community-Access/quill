"""The window half of D-5: kept words in Recent Phrases, the history setting,
the start-up sentence, and Review Transcript's Type into a Field.

Real wx windows built in memory; no real input is sent anywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation.rescue import DictationKeep
from quill.core.windows_dictation.review_session import ReviewSession, save_rescue

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


def _seal(text: str) -> str:
    return text[::-1]


class _Clock:
    now = 5_000_000.0

    def __call__(self) -> float:
        return self.now


def _keep(folder: Path) -> DictationKeep:
    return DictationKeep(folder, "QUILL", seal=_seal, unseal=_seal, clock=_Clock())


# -- the history setting ----------------------------------------------------------- #


def test_more_dictation_settings_offers_the_history_off_by_default(wx_app) -> None:
    from quill.ui.dictation_more_dialog import MoreDictationDialog

    class _Settings:
        pass

    dialog = MoreDictationDialog(None, _Settings(), None, load_models=False)
    try:
        assert dialog.values()["windows_dictation_history_days"] == 0
        dialog.history.SetSelection(2)
        assert dialog.values()["windows_dictation_history_days"] == 7
    finally:
        dialog.Destroy()


def test_the_setting_is_one_shared_field_cleaned_by_the_loader() -> None:
    from quill.core.windows_dictation.preferences import DictationPreferences
    from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields

    assert DictationSettings().windows_dictation_history_days == 0
    assert (
        load_fields({"windows_dictation_history_days": 30})["windows_dictation_history_days"] == 30
    )
    assert load_fields({"windows_dictation_history_days": 5})["windows_dictation_history_days"] == 0
    settings = DictationSettings(windows_dictation_history_days=1)
    assert DictationPreferences.from_settings(settings).history_days == 1


# -- what Recent Phrases lists -------------------------------------------------------- #


def test_kept_words_list_not_written_then_review_then_history(tmp_path: Path) -> None:
    from quill.ui.dictation_kept import KeptWords

    clock = _Clock()
    old = DictationKeep(tmp_path, "QUILL", seal=_seal, unseal=_seal, clock=clock)
    old.remember("from yesterday", 7)
    keep = _keep(tmp_path)
    entry = keep.keep("held", "held words")
    review = tmp_path / "dictation-review.json"
    save_rescue(review, ReviewSession("a review"))
    rows = KeptWords(keep, review, 7).rows()
    assert [row.kind for row in rows] == ["held", "review", "history"]
    assert [row.text for row in rows] == ["held words", "a review", "from yesterday"]
    assert rows[1].label == "Review not finished: a review"
    rows[0].delivered()
    rows[1].discard()
    assert keep.kept() == [] and not review.exists()
    assert entry


def test_the_start_sentence_counts_what_was_not_written(tmp_path: Path) -> None:
    from quill.ui.dictation_kept import KEEP_WHERE, KeptWords, kept_at_start

    keep = _keep(tmp_path)
    review = tmp_path / "dictation-review.json"
    assert kept_at_start(KeptWords(keep, review, 0), "review notice") == ""
    save_rescue(review, ReviewSession("a review"))
    assert kept_at_start(KeptWords(keep, review, 0), "review notice") == "review notice"
    keep.keep("held", "words")
    sentence = kept_at_start(KeptWords(keep, review, 0), "review notice")
    assert sentence.startswith("2 dictated phrases were not written last time")
    assert sentence.endswith(KEEP_WHERE)


def test_a_history_left_on_disk_after_it_was_turned_off_is_deleted(tmp_path: Path) -> None:
    from quill.ui.dictation_kept import KeptWords, kept_at_start

    keep = _keep(tmp_path)
    keep.remember("kept", 7)
    kept_at_start(KeptWords(keep, None, 0), "")
    assert not keep.history_path.exists()


# -- the window ------------------------------------------------------------------------ #


class _Row:
    def __init__(self, text: str, kind: str = "held") -> None:
        self.text = text
        self.kind = kind
        self.label = f"{kind}: {text}"
        self.discarded = False
        self.written = False

    def discard(self) -> None:
        self.discarded = True

    def delivered(self) -> None:
        self.written = True


def test_the_window_lists_kept_rows_after_this_sessions_and_discards_them(wx_app) -> None:
    from quill.ui.dictation_lists_dialog import RecentPhrasesDialog

    said: list[str] = []
    held, earlier = _Row("held words"), _Row("earlier", "history")
    dialog = RecentPhrasesDialog(None, ["this session"], saved=[held, earlier], say=said.append)
    try:
        assert dialog.list.GetStrings() == ["this session", "held: held words", "history: earlier"]
        dialog.discard()
        assert said[-1].startswith("This session's phrases are not kept")
        dialog.list.SetSelection(1)
        dialog.discard()
        assert held.discarded and said[-1] == "Discarded."
        assert dialog.list.GetStrings() == ["this session", "history: earlier"]
        assert dialog.list.GetSelection() == 1
    finally:
        dialog.Destroy()


def test_clear_history_asks_first_and_no_keeps_it(wx_app) -> None:
    from quill.ui.dictation_lists_dialog import RecentPhrasesDialog

    said: list[str] = []
    cleared: list[bool] = []
    answers = [False, True]
    dialog = RecentPhrasesDialog(
        None,
        [],
        saved=[_Row("held words"), _Row("earlier", "history")],
        say=said.append,
        clear_history=lambda: cleared.append(True),
        confirm=lambda _question: answers.pop(0),
    )
    try:
        dialog.clear_history()
        assert cleared == [] and dialog.list.GetCount() == 2
        dialog.clear_history()
        assert cleared == [True] and dialog.list.GetStrings() == ["held: held words"]
        assert said[-1] == "Dictation history cleared."
    finally:
        dialog.Destroy()


def test_inserting_a_kept_row_deletes_it_only_once_written(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.windows_dictation_dialog as dialogs
    from quill.ui.windows_dictation_tools import open_recent_phrases

    row = _Row("held words")

    class _Kept:
        def rows(self) -> list[Any]:
            return [row]

        def clear_history(self) -> None:
            return None

    class _Chosen:
        def __init__(self, _parent: Any, _phrases: list[str], **_kept: Any) -> None:
            self.chosen, self.verb, self.chosen_row = row.text, "insert", row

        def Destroy(self) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(dialogs, "RecentPhrasesDialog", _Chosen)
    run = lambda _d, _l: wx.ID_OK  # noqa: E731
    open_recent_phrases(
        None, [], run_modal=run, say=print, insert_again=lambda _t: None, kept=_Kept()
    )
    assert not row.written  # waiting for a field: still kept
    open_recent_phrases(
        None, [], run_modal=run, say=print, insert_again=lambda _t: True, kept=_Kept()
    )
    assert row.written


# -- Review Transcript's Type into a Field --------------------------------------------- #


def test_type_into_a_field_takes_the_selected_part_or_all(wx_app) -> None:
    from quill.apps.transcribe_files import TranscriptReviewDialog

    dialog = TranscriptReviewDialog(None, "first part. second part.")
    try:
        dialog.EndModal = lambda _code: None  # type: ignore[method-assign]
        dialog._finish("type")
        assert (dialog.action, dialog.chosen_text) == ("type", "first part. second part.")
        dialog.text.SetSelection(0, 11)
        dialog._finish("type")
        assert dialog.chosen_text == "first part."
    finally:
        dialog.Destroy()


def test_the_reviewed_transcript_is_typed_through_insert_again(
    wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.apps.transcribe_files as files

    path = tmp_path / "talk.txt"
    path.write_text("the whole talk", encoding="utf-8")

    class _Dialog:
        def __init__(self, _parent: Any, text: str) -> None:
            self.action, self.chosen_text = "type", text

        def Destroy(self) -> None:  # noqa: N802
            pass

    typed: list[str] = []

    class _Host(files.TranscribeFilesMixin):
        frame = None

        def _show_modal_dialog(self, _dialog: Any, _label: str) -> int:
            return wx.ID_OK

        def insert_recent_phrase(self, text: str) -> None:
            typed.append(text)

    monkeypatch.setattr(files, "TranscriptReviewDialog", _Dialog)
    _Host()._dictation_open_file(path)
    assert typed == ["the whole talk"]
