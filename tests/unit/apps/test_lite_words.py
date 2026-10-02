"""Tools > Thesaurus, Say Word Summary, Dictionary Status and the Dictionary submenu (2026-10-02).

The commands are the shared ones (:mod:`quill.ui.word_tools_commands`); what is
reached here is each handler the Lite menu binds, with the service, the picker
and the answer window replaced by recorders at the modules the mixin looks
them up in.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import wx

from quill.ui.word_tools_commands import NEEDS_DIRECT_ROUTE

SENTENCE = "She was running fast. Then she stopped."
WORD_AT = SENTENCE.index("running") + 2


class _Recorder:
    """A stand-in frame or dialog class that remembers how it was made."""

    last: dict[str, Any] | None = None
    made: list[dict[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        record = {"args": args, "kwargs": kwargs}
        type(self).last = record
        type(self).made.append(record)

    def Show(self, *_a: Any) -> None:  # noqa: N802 - wx shape
        return None

    def Raise(self) -> None:  # noqa: N802
        return None

    def SetFocus(self) -> None:  # noqa: N802
        return None

    def Bind(self, *_a: Any, **_k: Any) -> None:  # noqa: N802
        return None

    def IsShown(self) -> bool:  # noqa: N802
        return True

    def Destroy(self) -> None:  # noqa: N802
        return None


class _WordService:
    """A direct-route service whose word-tool answers are canned JSON."""

    signed_in = False
    own_key_active = True
    chatgpt_active = False
    direct = True
    route = "own_key"

    def __init__(self, answer: dict[str, Any] | str | None = None) -> None:
        self.asked: list[tuple[str, str]] = []
        self.answer = (
            answer
            if answer is not None
            else {
                "answer": "Moving quickly on foot.",
                "choices": [
                    {"text": "sprinting", "note": "faster"},
                    {"text": "jogging", "note": "slower"},
                ],
            }
        )

    def ask(self, feature, prompt, chunks, *, on_done, on_error, **_extra):
        self.asked.append((feature, prompt))
        raw = self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
        on_done(raw, None)


@pytest.fixture
def answer_frames(monkeypatch):
    import quill.ui.word_tools_window as window

    cls = type("WordAnswerFrame", (_Recorder,), {"last": None, "made": []})
    monkeypatch.setattr(window, "WordAnswerFrame", cls)
    return cls


@pytest.fixture
def modal_passthrough(monkeypatch):
    """The shared modal gate, answering with the dialog's own ShowModal."""
    import quill.ui.dialog_contract as contract

    calls: list[str] = []

    def show(dialog, title, **_kw):
        calls.append(title)
        return dialog.ShowModal()

    monkeypatch.setattr(contract, "show_modal_dialog", show)
    return calls


@pytest.fixture
def picker(monkeypatch):
    """The two-pane thesaurus picker, replaced by a recorder that chooses a term."""
    import quill.ui.thesaurus_dialog as dialog_module

    class FakePicker:
        last: dict[str, Any] | None = None
        chosen = "sprinting"

        def __init__(self, parent, word, senses, **kwargs):
            type(self).last = {"word": word, "senses": senses, **kwargs}

        def show_modal(self):
            return type(self).chosen

        def Destroy(self):  # noqa: N802
            return None

    monkeypatch.setattr(dialog_module, "ThesaurusDialog", FakePicker)
    return FakePicker


def _on_running(lite_window):
    win = lite_window(SENTENCE)
    win.control.SetInsertionPoint(WORD_AT)
    return win


# --------------------------------------------------------------------------- #
# The thesaurus (offline)
# --------------------------------------------------------------------------- #


def test_shift_f7_finds_the_word_you_are_on_and_replaces_it_inflected(lite_window, picker):
    win = _on_running(lite_window)

    (lambda w: w.cmd_thesaurus())(win)

    assert picker.last is not None
    assert picker.last["word"] == "running (as run)"
    assert picker.last["allow_replace"] is True
    assert any("from run" in sense.label for sense in picker.last["senses"])
    assert win.control.GetValue() == SENTENCE.replace("running", "sprinting")
    assert any('Replaced "running" with "sprinting"' in said for said in win.announcements)


def test_the_thesaurus_asks_for_a_word_when_the_cursor_is_not_on_one(
    lite_window, picker, fake_wx_dialog, modal_passthrough
):
    fake_wx_dialog("TextEntryDialog", wx.ID_OK, GetValue="happy")
    win = lite_window("")
    picker.chosen = "glad"

    (lambda w: w.cmd_thesaurus())(win)

    assert "Thesaurus" in modal_passthrough
    assert picker.last is not None
    assert picker.last["word"] == "happy"
    assert picker.last["allow_replace"] is False
    assert win.control.GetValue() == ""  # nothing to replace, nothing replaced


def test_a_word_the_thesaurus_does_not_know_is_said_not_shown(lite_window, picker):
    win = lite_window("the zzqxv was here")
    win.control.SetInsertionPoint(5)

    (lambda w: w.cmd_thesaurus())(win)

    assert picker.last is None
    assert any("No thesaurus entry" in said for said in win.announcements)


def test_the_thesaurus_area_switched_off_owns_nothing(lite_window, picker, monkeypatch):
    win = _on_running(lite_window)
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "dictionary")

    (lambda w: w.cmd_thesaurus())(win)
    (lambda w: w.cmd_word_summary())(win)

    assert picker.last is None
    assert sum("switched off" in said for said in win.announcements) == 2


def test_say_word_summary_speaks_the_entry_without_opening_anything(lite_window):
    win = _on_running(lite_window)

    (lambda w: w.cmd_word_summary())(win)

    said = win.announcements[-1]
    assert said.startswith("running, looked up as run:")
    assert "as a verb" in said
    assert "Opposites:" in said


def test_dictionary_status_reports_counts_files_and_the_thesaurus(lite_window, monkeypatch):
    import quill.apps.lite_window_words as words

    seen: list[tuple[Any, list[str]]] = []
    monkeypatch.setattr(
        words, "show_dictionary_status", lambda parent, lines, ann: seen.append((parent, lines))
    )
    win = lite_window("text")

    (lambda w: w.cmd_dictionary_status())(win)

    parent, lines = seen[0]
    assert parent is win
    assert lines[0].startswith("Personal (your QUILL Lite dictionary): 0 words")
    assert lines[1].startswith("This document: no dictionary until the document is saved.")
    assert lines[2].startswith("Thesaurus data: installed")


# --------------------------------------------------------------------------- #
# The dictionary (AI word tools)
# --------------------------------------------------------------------------- #

_CHOICE_TOOLS = [
    (lambda w: w.cmd_word_synonyms(), "synonyms", "Synonyms That Fit"),
    (lambda w: w.cmd_word_simpler(), "simpler", "Simpler Word"),
    (lambda w: w.cmd_word_formal(), "formal", "More Formal Word"),
    (lambda w: w.cmd_word_vivid(), "vivid", "More Vivid Word"),
    (lambda w: w.cmd_word_opposites(), "opposites", "Opposites"),
    (lambda w: w.cmd_word_right(), "right_word", "Is This the Right Word?"),
    (lambda w: w.cmd_word_rhymes(), "rhymes", "Rhymes"),
    (lambda w: w.cmd_word_explorer(), "explore", "Word Explorer"),
]

_PROSE_TOOLS = [
    (lambda w: w.cmd_word_define(), "define", "Define in Context"),
    (lambda w: w.cmd_word_examples(), "examples", "Use It in a Sentence"),
    (lambda w: w.cmd_word_origin(), "origin", "Where It Comes From"),
    (lambda w: w.cmd_word_pronounce(), "pronounce", "How to Say It"),
]


@pytest.mark.parametrize(("run", "tool_id", "title"), _CHOICE_TOOLS)
def test_a_choice_tool_sends_the_word_and_its_sentence_and_offers_replace(
    lite_window, answer_frames, monkeypatch, run, tool_id, title
):
    from quill.core.ai.word_tools import TOOLS_BY_ID

    win = _on_running(lite_window)
    service = _WordService()
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    run(win)

    assert len(service.asked) == 1
    feature, prompt = service.asked[0]
    assert feature == "word_tools"
    assert "Word: running" in prompt
    assert "Sentence: She was running fast." in prompt
    assert TOOLS_BY_ID[tool_id].task.split(".")[0] in prompt
    assert "Then she stopped" not in prompt  # only the sentence, never the rest
    shown = answer_frames.last["kwargs"]
    assert title in shown["tool_label"].replace("&", "")
    assert shown["word"] == "running"
    assert shown["answer"] == "Moving quickly on foot."
    assert [c.text for c in shown["choices"]] == ["sprinting", "jogging"]
    assert shown["on_use"] is not None
    shown["on_use"]("sprinting")
    assert win.control.GetValue() == SENTENCE.replace("running", "sprinting")


@pytest.mark.parametrize(("run", "tool_id", "title"), _PROSE_TOOLS)
def test_a_prose_tool_offers_nothing_to_put_in_the_document(
    lite_window, answer_frames, monkeypatch, run, tool_id, title
):
    win = _on_running(lite_window)
    service = _WordService()
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    run(win)

    assert service.asked and service.asked[0][0] == "word_tools"
    shown = answer_frames.last["kwargs"]
    assert title in shown["tool_label"].replace("&", "")
    assert shown["choices"] == ()
    assert shown["on_use"] is None


def test_replace_is_withheld_when_the_word_moved_before_the_answer_came(
    lite_window, answer_frames, monkeypatch
):
    win = _on_running(lite_window)
    service = _WordService()

    def late(feature, prompt, chunks, *, on_done, on_error, **_e):
        win.control.SetValue("Everything changed.")
        on_done(json.dumps(service.answer), None)

    service.ask = late  # type: ignore[method-assign]
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_word_synonyms())(win)

    assert answer_frames.last["kwargs"]["on_use"] is None


def test_a_reply_that_is_not_json_is_still_an_answer_with_no_choices(
    lite_window, answer_frames, monkeypatch
):
    win = _on_running(lite_window)
    monkeypatch.setattr(win, "_ai_service", lambda: _WordService("Just some **prose**."))

    (lambda w: w.cmd_word_synonyms())(win)

    shown = answer_frames.last["kwargs"]
    assert shown["answer"] == "Just some prose."
    assert shown["choices"] == ()


def test_the_dictionary_needs_a_direct_route_and_opens_the_account_window(
    lite_window, answer_frames, monkeypatch
):
    import quill.ui.hosted_ai_chatgpt as chatgpt_ui

    window = type("ChatGptFrame", (_Recorder,), {"last": None, "made": []})
    monkeypatch.setattr(chatgpt_ui, "ChatGptFrame", window)
    win = _on_running(lite_window)
    service = _WordService()
    service.direct = False
    service.own_key_active = False
    service.chatgpt = object()
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_word_define())(win)

    assert service.asked == []
    assert NEEDS_DIRECT_ROUTE in win.announcements
    assert window.last is not None
    assert answer_frames.last is None


def test_the_dictionary_refuses_when_the_ai_area_is_off(lite_window, answer_frames, monkeypatch):
    win = _on_running(lite_window)
    service = _WordService()
    monkeypatch.setattr(win, "_ai_service", lambda: service)
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "hosted_ai")

    (lambda w: w.cmd_word_define())(win)

    assert service.asked == []
    assert any("switched off" in said for said in win.announcements)


def test_a_word_tool_with_no_word_under_the_cursor_says_so(lite_window, answer_frames, monkeypatch):
    win = lite_window("")
    service = _WordService()
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_word_define())(win)

    assert service.asked == []
    assert any("Put the cursor in a word" in said for said in win.announcements)


def test_find_the_word_for_asks_for_a_meaning_and_inserts_at_the_cursor(
    lite_window, answer_frames, fake_wx_dialog, modal_passthrough, monkeypatch
):
    fake_wx_dialog("TextEntryDialog", wx.ID_OK, GetValue="pleasantly tired after work")
    win = lite_window("I felt ")
    win.control.SetInsertionPoint(7)
    service = _WordService({
        "answer": "Weary fits best.",
        "choices": [{"text": "weary", "note": ""}],
    })
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_find_word())(win)

    assert "Find the Word For" in modal_passthrough
    feature, prompt = service.asked[0]
    assert feature == "word_tools"
    assert "Description: pleasantly tired after work" in prompt
    shown = answer_frames.last["kwargs"]
    assert shown["action"] == "insert"
    assert shown["word"] == ""
    shown["on_use"]("weary")
    assert win.control.GetValue() == "I felt weary"


def test_cancelling_find_the_word_for_sends_nothing(
    lite_window, answer_frames, fake_wx_dialog, modal_passthrough, monkeypatch
):
    fake_wx_dialog("TextEntryDialog", wx.ID_CANCEL, GetValue="")
    win = lite_window("text")
    service = _WordService()
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_find_word())(win)

    assert service.asked == []
    assert answer_frames.last is None


# --------------------------------------------------------------------------- #
# The context menu: two submenus on the word
# --------------------------------------------------------------------------- #


def _submenus(menu: wx.Menu) -> dict[str, wx.Menu]:
    return {
        item.GetItemLabelText(): item.GetSubMenu()
        for item in menu.GetMenuItems()
        if item.GetSubMenu() is not None
    }


def test_the_context_menu_carries_thesaurus_and_dictionary_submenus_on_a_word(
    wx_app, lite_window, monkeypatch
):
    win = _on_running(lite_window)
    monkeypatch.setattr(win, "_ai_service", lambda: _WordService())
    popup = wx.Menu()

    added = win.append_word_submenus(popup, SENTENCE, WORD_AT, (0, 0))

    assert added is True
    subs = _submenus(popup)
    assert 'Thesaurus for "running"' in subs
    assert 'Dictionary for "running"' in subs
    thesaurus_rows = [i.GetItemLabelText() for i in subs['Thesaurus for "running"'].GetMenuItems()]
    assert thesaurus_rows[0] != ""  # a replacement, one keystroke away
    assert any(label.startswith("More in Thesaurus") for label in thesaurus_rows)
    assert any(label.startswith("Say Word Summary") for label in thesaurus_rows)
    dictionary_rows = [
        i.GetItemLabelText() for i in subs['Dictionary for "running"'].GetMenuItems()
    ]
    assert any(label.startswith("Define in Context") for label in dictionary_rows)
    assert any(label.startswith("Find the Word For") for label in dictionary_rows)
    assert dictionary_rows[0].startswith('Look Up "running"')
    assert len([r for r in dictionary_rows if r]) == 14
    popup.Destroy()


def test_a_selected_word_wins_over_the_caret(wx_app, lite_window, monkeypatch):
    win = lite_window(SENTENCE)
    monkeypatch.setattr(win, "_ai_service", lambda: _WordService())
    popup = wx.Menu()
    start = SENTENCE.index("stopped")

    win.append_word_submenus(popup, SENTENCE, 0, (start, start + len("stopped")))

    assert 'Thesaurus for "stopped"' in _submenus(popup)
    popup.Destroy()


def test_without_a_direct_route_the_dictionary_submenu_is_one_setup_row(
    wx_app, lite_window, monkeypatch
):
    win = _on_running(lite_window)
    service = _WordService()
    service.direct = False
    monkeypatch.setattr(win, "_ai_service", lambda: service)
    popup = wx.Menu()

    win._append_dictionary_submenu(popup, _span())

    rows = [
        i.GetItemLabelText() for i in _submenus(popup)['Dictionary for "running"'].GetMenuItems()
    ]
    assert [r for r in rows if r] == rows[:1] + rows[2:]  # Look Up, a separator, the setup row
    assert rows[0].startswith('Look Up "running"')
    assert rows[2].startswith("Set Up the Dictionary")
    popup.Destroy()


def test_a_replacement_row_replaces_the_word_and_says_so(wx_app, lite_window, monkeypatch):
    win = _on_running(lite_window)
    monkeypatch.setattr(win, "_ai_service", lambda: _WordService())
    popup = wx.Menu()
    win._append_thesaurus_submenu(popup, _span())
    first = _submenus(popup)['Thesaurus for "running"'].GetMenuItems()[0]
    event = wx.CommandEvent(wx.wxEVT_MENU, first.GetId())

    popup.ProcessEvent(event)

    assert first.GetItemLabelText() in win.control.GetValue()
    assert any("Replaced" in said for said in win.announcements)
    popup.Destroy()


def test_no_word_means_no_submenus(wx_app, lite_window):
    win = lite_window("   ")
    win.control.SetInsertionPoint(1)
    popup = wx.Menu()

    assert win.append_word_submenus(popup, "   ", 1, (0, 0)) is False
    assert popup.GetMenuItemCount() == 0
    popup.Destroy()


def _span():
    from quill.core.word_lookup import WordSpan

    start = SENTENCE.index("running")
    return WordSpan("running", start, start + len("running"))
