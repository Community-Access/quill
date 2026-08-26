"""The two-pane Thesaurus picker.

Three of these tests pin decisions that are easy to undo by accident and whose
breakage is silent -- nothing raises, nothing looks wrong, and the surface just
becomes worse to use with a screen reader:

* Nothing is announced when the sense selection changes. QUILL speaks with
  ``interrupt=False``, so an announcement queues *behind* the screen reader
  rather than replacing it; one per arrow-press leaves somebody several
  utterances behind their own cursor.
* The dialog is held, not subclassed. ``_show_modal_dialog`` lands initial
  focus on the content control, but its guard is ``type(dialog) is wx.Dialog``
  -- an identity check a subclass fails silently, opening the dialog on a
  button instead of the senses.
* The inserted term is never the displayed label. Replacing "light" with
  "opposite: heavy" would be a funny bug in a serious place.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.thesaurus import SenseRow  # noqa: E402
from quill.ui.thesaurus_dialog import ThesaurusDialog  # noqa: E402

SENSES = (
    SenseRow(
        label="adjective: airy, buoyant, floaty, 2 more",
        part_of_speech="adjective",
        rows=(
            ("airy", "airy"),
            ("buoyant", "buoyant"),
            ("opposite: heavy", "heavy"),
        ),
    ),
    SenseRow(
        label="noun: visible light, visible radiation",
        part_of_speech="noun",
        rows=(("visible light", "visible light"), ("broader: radiation", "radiation")),
    ),
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Recorder:
    def __init__(self, *, copy_ok: bool = True) -> None:
        self.copied: list[str] = []
        self.announced: list[str] = []
        self.ended: list[int] = []
        self.shown: list[str] = []
        self.modal_result = 0
        self._copy_ok = copy_ok

    def show_modal(self, dialog: object, label: str) -> int:
        """Stands in for MainFrame._show_modal_dialog, which needs a live host."""
        self.shown.append(label)
        return self.modal_result

    def copy(self, term: str) -> bool:
        self.copied.append(term)
        return self._copy_ok

    def announce(self, message: str) -> None:
        self.announced.append(message)


def _make(wx_app, *, allow_replace: bool = True, copy_ok: bool = True):
    frame = wx.Frame(None)
    recorder = _Recorder(copy_ok=copy_ok)
    picker = ThesaurusDialog(
        frame,
        "light",
        SENSES,
        allow_replace=allow_replace,
        show_modal_dialog=recorder.show_modal,
        on_copy=recorder.copy,
        announce=recorder.announce,
    )
    # EndModal outside a modal loop is not safe to call for real; record it.
    picker.dialog.EndModal = recorder.ended.append  # type: ignore[method-assign]
    return frame, picker, recorder


def _close(frame, picker) -> None:
    picker.Destroy()
    frame.Destroy()


def test_opens_on_the_first_sense_with_its_words_shown(wx_app):
    frame, picker, _ = _make(wx_app)
    try:
        assert picker._sense_list.GetCount() == 2
        assert picker._sense_list.GetSelection() == 0
        assert list(picker._word_list.GetStrings()) == ["airy", "buoyant", "opposite: heavy"]
        assert picker._word_list.GetSelection() == 0
    finally:
        _close(frame, picker)


def test_the_dialog_is_held_not_subclassed(wx_app):
    """_show_modal_dialog's focus guard is an identity check. A subclass passes
    every other test in this file and silently opens on a button."""
    frame, picker, _ = _make(wx_app)
    try:
        assert type(picker.dialog) is wx.Dialog
    finally:
        _close(frame, picker)


def test_changing_the_sense_repopulates_and_relabels_but_says_nothing(wx_app):
    """The label is how the new sense reaches the user -- read by the screen
    reader when they tab in, not spoken over their arrow keys."""
    frame, picker, recorder = _make(wx_app)
    try:
        picker._sense_list.SetSelection(1)
        picker._on_sense_changed(None)

        assert list(picker._word_list.GetStrings()) == ["visible light", "broader: radiation"]
        label = picker._words_label.GetLabel()
        assert "noun" in label and "sense 2" in label
        assert recorder.announced == [], "a sense change must not speak"
    finally:
        _close(frame, picker)


def test_each_list_is_named_by_the_label_created_before_it(wx_app):
    """On wxMSW the accessible name comes from the preceding static text, so
    the creation order is the contract."""
    frame, picker, _ = _make(wx_app)
    try:
        children = list(picker.dialog.GetChildren())
        senses_label = children.index(picker._senses_label)
        sense_list = children.index(picker._sense_list)
        words_label = children.index(picker._words_label)
        word_list = children.index(picker._word_list)
        assert senses_label < sense_list
        assert words_label < word_list
        assert "light" in picker._senses_label.GetLabel()
    finally:
        _close(frame, picker)


def test_the_inserted_term_is_never_the_displayed_label(wx_app):
    frame, picker, recorder = _make(wx_app)
    try:
        picker._word_list.SetSelection(2)  # "opposite: heavy"
        assert picker._selected_term() == "heavy"

        picker._replace_selected()
        assert picker.chosen_term == "heavy"
        assert recorder.ended == [wx.ID_OK]
    finally:
        _close(frame, picker)


def test_copy_reports_once_and_leaves_the_dialog_open(wx_app):
    """The one announcement this surface makes: the user has just pressed a
    key, focus is settled, and nothing else is speaking."""
    frame, picker, recorder = _make(wx_app)
    try:
        picker._word_list.SetSelection(1)
        picker._copy_selected()

        assert recorder.copied == ["buoyant"]
        assert len(recorder.announced) == 1
        assert "buoyant" in recorder.announced[0]
        assert recorder.ended == [], "Copy must not close the dialog"
    finally:
        _close(frame, picker)


def test_a_failed_copy_says_nothing_rather_than_lying(wx_app):
    frame, picker, recorder = _make(wx_app, copy_ok=False)
    try:
        picker._word_list.SetSelection(0)
        picker._copy_selected()
        assert recorder.copied == ["airy"]
        assert recorder.announced == []
    finally:
        _close(frame, picker)


def test_without_a_target_replace_is_disabled_and_copy_takes_enter(wx_app):
    """A disabled default button is a dead Enter key, which is a worse trap in
    a dialog than in a form."""
    frame, picker, recorder = _make(wx_app, allow_replace=False)
    try:
        assert not picker._replace_btn.IsEnabled()
        assert picker.dialog.GetDefaultItem() is picker._copy_btn

        picker._word_list.SetSelection(0)
        picker._activate_word()  # Enter on a word
        assert recorder.copied == ["airy"]
        assert recorder.ended == []
        assert picker.chosen_term == ""
    finally:
        _close(frame, picker)


def test_enter_on_a_word_replaces_when_there_is_a_target(wx_app):
    frame, picker, recorder = _make(wx_app)
    try:
        picker._word_list.SetSelection(0)
        picker._activate_word()
        assert picker.chosen_term == "airy"
        assert recorder.ended == [wx.ID_OK]
        assert recorder.copied == []
    finally:
        _close(frame, picker)


def test_no_senses_leaves_an_empty_word_pane_rather_than_raising(wx_app):
    frame = wx.Frame(None)
    recorder = _Recorder()
    picker = ThesaurusDialog(
        frame,
        "x",
        (),
        allow_replace=True,
        show_modal_dialog=recorder.show_modal,
        on_copy=recorder.copy,
        announce=recorder.announce,
    )
    try:
        assert picker._sense_list.GetCount() == 0
        assert picker._word_list.GetCount() == 0
        assert picker._selected_term() == ""
        picker._replace_selected()  # must not raise, must not end the modal
        assert picker.chosen_term == ""
    finally:
        _close(frame, picker)


def test_show_modal_returns_the_term_only_when_replace_was_chosen(wx_app):
    """Close, Escape and copy-then-close all mean "insert nothing"."""
    frame, picker, recorder = _make(wx_app)
    try:
        picker.chosen_term = "airy"
        recorder.modal_result = wx.ID_OK
        assert picker.show_modal() == "airy"
        assert recorder.shown == ["Thesaurus"]

        recorder.modal_result = wx.ID_CANCEL
        assert picker.show_modal() == ""
    finally:
        _close(frame, picker)


def test_it_shows_through_the_hardened_gate_and_not_ShowModal(wx_app):
    """Every modal in the app goes through MainFrame._show_modal_dialog, which
    is what applies the shared keyboard and focus contract."""
    frame, picker, recorder = _make(wx_app)
    try:
        recorder.modal_result = wx.ID_CANCEL
        picker.show_modal()
        assert recorder.shown == ["Thesaurus"]
    finally:
        _close(frame, picker)
