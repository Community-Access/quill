"""Quill Inkwell's AI, in the real window (codex.md Phase 3, 10E.10, 6.12).

Its own "QUILL Inkwell" sign-in, the AI menu on the Window-menu fallback keys,
Ask about the abbreviation library, Suggest Abbreviations from a Document (a
yes before anything goes, every proposal cleared until checked), the AI line
and Safe Mode. The AI is a stand-in on the real service, so nothing leaves the
machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: Builds a real Quill Inkwell window, which owns the tray and system-wide keys.
pytestmark = pytest.mark.machine_global

_ANSWER = "1. sig -> Kind regards, Jeff\nmtg -> the Tuesday planning meeting\nbtw -> taken"


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-inkwell"
        self.web_search = False
        self.ended_by_openai = False


@pytest.fixture
def inkwell(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.inkwell import QuillInkwellFrame

    frame = QuillInkwellFrame(safe_mode=True)  # no keyboard hook
    frame._safe_mode = False
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    service = frame._ai_service()
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []
    frame.answer = _ANSWER

    def ask(feature, prompt, chunks, *, on_done, on_error, language="", requires=("text",)):
        frame.sent.append((feature, prompt, requires))
        on_done(frame.answer, None)

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append(("converse", message, list(excerpts)))
        on_done("An answer.", None, 0)

    service.ask = ask
    service.converse = converse
    service._chatgpt = _Account(signed_in=True)
    frame._ai_host().settings.ai_connection = "chatgpt"
    frame.shown = []
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: frame.shown.append(window))

    def submit(name, work, *, on_success, on_failure=None, **_kw):
        on_success(name, work())

    monkeypatch.setattr(frame._task_manager, "submit", submit)
    monkeypatch.setattr(frame, "_inkwell_ai_call_after", lambda func, *args: func(*args))
    try:
        yield frame
    finally:
        for window in [*getattr(frame, "_ai_windows", {}).values(), *frame.shown]:
            if window:
                window.Destroy()
        frame._preference_saver.flush()
        timer = getattr(frame, "_ipc_timer", None)
        if timer is not None:
            timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()


def _menu(frame, name: str):
    bar = frame.frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu(name))


def _with_library(frame, *entries: tuple[str, str]) -> None:
    from quill.core.abbreviations import (
        Abbreviation,
        AbbreviationLibrary,
        save_abbreviation_library,
    )

    library = AbbreviationLibrary(
        version=2,
        abbreviations=[
            Abbreviation(id=f"id-{name}", abbreviation=name, expansion=text)
            for name, text in entries
        ],
    )
    save_abbreviation_library(library, frame._data_dir)
    frame._library = library


def _document(tmp_path: Path, text: str, name: str = "notes.txt") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _answers(monkeypatch, frame, *, pick, send=True, review=None) -> list[str]:
    """Stand in for the three windows; returns the yes-or-no sentence asked."""
    asked: list[str] = []
    monkeypatch.setattr(frame, "_inkwell_pick_document", lambda: pick)

    def confirm(file_name: str, text: str) -> bool:
        from quill.apps.inkwell_ai import send_sentence

        asked.append(send_sentence(file_name, text, frame._inkwell_connection_name()))
        return send

    monkeypatch.setattr(frame, "_inkwell_confirm_send", confirm)
    if review is not None:
        monkeypatch.setattr(frame, "_inkwell_review_suggestions", review)
    return asked


def test_the_ai_menu_sits_before_quillville_on_the_fallback_keys(inkwell) -> None:
    bar = inkwell.frame.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert titles.index("A&I") == titles.index("&Dictation") + 1
    assert titles.index("&QuillVille") == titles.index("A&I") + 1
    labels = [i.GetItemLabel() for i in _menu(inkwell, "AI").GetMenuItems() if not i.IsSeparator()]
    assert labels == [
        "&Ask...\tCtrl+Shift+8",
        "&Which AI Am I Using\tCtrl+F8",
        "&Choose Your AI...\tCtrl+Shift+F8",
        "Suggest Abbreviations from a &Document...\tCtrl+Shift+A",
        "Use My C&hatGPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI U&sage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tAlt+Shift+F2",
    ]
    assert inkwell.commands.get("inkwell.ai_suggest") is not None


def test_inkwell_signs_in_as_itself(inkwell) -> None:
    service = inkwell._ai_service()
    assert service._app.ai_agent_name == "QUILL Inkwell"
    del service._chatgpt
    assert service.chatgpt.agent_name == "QUILL Inkwell"


def test_the_choice_is_kept_in_inkwells_own_file(inkwell) -> None:
    from quill.core.paths import app_data_dir

    inkwell._ai_host().save_settings()
    saved = json.loads((app_data_dir() / "inkwell-ai.json").read_text(encoding="utf-8"))
    assert saved["ai_connection"] == "chatgpt"


def test_ask_sends_the_library_by_name_and_expansion(inkwell) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    _with_library(inkwell, ("addr", "12 High Street"), ("btw", "by the way"))
    inkwell.cmd_ai_chat_key()
    frame = inkwell._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about your abbreviations.")
    frame._message.SetValue("What do I type most?")
    frame._send()
    facts = inkwell.sent[0][2][0]
    assert "addr -> 12 High Street" in facts and "btw -> by the way" in facts


def test_suggest_asks_first_then_adds_only_what_was_checked(inkwell, monkeypatch, tmp_path) -> None:
    from quill.core.abbreviations import load_abbreviation_library

    _with_library(inkwell, ("btw", "by the way"))
    reviewed: list[list[tuple[str, str]]] = []

    def review(proposals):
        reviewed.append(list(proposals))
        return [proposals[1]]  # only mtg is checked

    path = _document(tmp_path, "Kind regards, Jeff. The Tuesday planning meeting is on.")
    asked = _answers(monkeypatch, inkwell, pick=path, review=review)
    inkwell.cmd_inkwell_suggest()
    assert asked == [
        "All 9 words of notes.txt go to My ChatGPT plan to suggest abbreviations. "
        "The file's name and folder stay on this computer. Send them?"
    ]
    _feature, prompt, requires = inkwell.sent[0]
    assert requires == ("text",)
    assert "The Tuesday planning meeting" in prompt and "btw" in prompt
    assert str(tmp_path) not in prompt and "notes.txt" not in prompt  # never the path
    # btw already exists, so it is never offered.
    assert reviewed == [[("sig", "Kind regards, Jeff"), ("mtg", "the Tuesday planning meeting")]]
    names = [a.abbreviation for a in load_abbreviation_library(inkwell._data_dir).abbreviations]
    assert names == ["btw", "mtg"]
    assert inkwell.said[-1] == "Added 1 abbreviation."
    assert inkwell._list.GetItemCount() == 2


def test_suggest_says_no_and_nothing_goes(inkwell, monkeypatch, tmp_path) -> None:
    path = _document(tmp_path, "Some words to read.")
    _answers(monkeypatch, inkwell, pick=path, send=False)
    inkwell.cmd_inkwell_suggest()
    assert inkwell.sent == []
    assert inkwell.said[-1] == "Nothing was sent."


def test_suggest_cancelled_at_the_picker_reads_and_sends_nothing(inkwell, monkeypatch) -> None:
    asked = _answers(monkeypatch, inkwell, pick=None)
    inkwell.cmd_inkwell_suggest()
    assert asked == [] and inkwell.sent == []


def test_suggest_cancelled_at_review_adds_nothing(inkwell, monkeypatch, tmp_path) -> None:
    from quill.core.abbreviations import load_abbreviation_library

    _with_library(inkwell, ("btw", "by the way"))
    path = _document(tmp_path, "Kind regards, Jeff.")
    _answers(monkeypatch, inkwell, pick=path, review=lambda proposals: None)
    inkwell.cmd_inkwell_suggest()
    names = [a.abbreviation for a in load_abbreviation_library(inkwell._data_dir).abbreviations]
    assert names == ["btw"]
    assert inkwell.said[-1] == "No abbreviations were added."


def test_suggest_with_nothing_usable_says_so(inkwell, monkeypatch, tmp_path) -> None:
    inkwell.answer = "I could not find any repeated phrases."
    path = _document(tmp_path, "Short.")
    _answers(monkeypatch, inkwell, pick=path, review=lambda p: pytest.fail("no review"))
    inkwell.cmd_inkwell_suggest()
    assert inkwell.said[-1] == "No new abbreviations came back for notes.txt."


def test_suggest_refuses_a_file_it_cannot_read(inkwell, monkeypatch, tmp_path) -> None:
    path = _document(tmp_path, "x", name="song.mp3")
    asked = _answers(monkeypatch, inkwell, pick=path)
    inkwell.cmd_inkwell_suggest()
    assert asked == [] and inkwell.sent == []
    assert "cannot read song.mp3" in inkwell.said[-1]


def test_a_long_document_says_only_the_first_part_goes() -> None:
    from quill.apps.inkwell_ai import send_sentence

    sentence = send_sentence("book.docx", "word " * 5000, "QUILL's free AI")
    assert sentence.startswith("The first 2,400 words of book.docx go to QUILL's free AI")


def test_the_review_window_starts_with_every_box_cleared(inkwell) -> None:
    from quill.apps.inkwell_suggest_dialog import SuggestionsDialog

    dialog = SuggestionsDialog(inkwell.frame, [("sig", "Kind regards"), ("r&d", "R & D")])
    try:
        assert dialog.GetTitle() == "Suggest Abbreviations"
        assert [box.GetValue() for box in dialog._boxes] == [False, False]
        assert dialog._boxes[0].GetLabel() == "sig, expands to Kind regards"
        assert all(box.GetHelpText() for box in dialog._boxes)
        assert dialog.checked() == []
        dialog._boxes[1].SetValue(True)
        assert dialog.checked() == [("r&d", "R & D")]
    finally:
        dialog.Destroy()


def test_safe_mode_refuses_every_ai_command(inkwell, monkeypatch) -> None:
    monkeypatch.setattr(inkwell, "_inkwell_pick_document", lambda: pytest.fail("picked"))
    inkwell._safe_mode = True
    for command in (
        lambda w: w.cmd_ai_chat_key(),
        lambda w: w.cmd_ai_which(),
        lambda w: w.cmd_ai_choose(),
        lambda w: w.cmd_ai_usage(),
        lambda w: w.cmd_ai_chatgpt(),
        lambda w: w.cmd_inkwell_suggest(),
    ):
        inkwell.said.clear()
        command(inkwell)
        assert inkwell.said == ["AI is off in Safe Mode."]
    assert inkwell.sent == []


def test_the_ai_line_says_which_ai_and_enter_opens_choose(inkwell, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(inkwell), "cmd_ai_choose", lambda self: opened.append("x"))
    assert inkwell._ai_text.GetValue().startswith("AI")
    assert "Choose Your AI" in inkwell._ai_text.GetHelpText()
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_RETURN)
    inkwell._on_ai_line_key(event)
    assert opened == ["x"]


def test_the_adapter_has_no_command_of_its_own() -> None:
    from quill.apps.inkwell_ai import InkwellAiMixin

    assert [name for name in vars(InkwellAiMixin) if name.startswith("cmd_")] == []


def test_the_real_windows_go_through_the_dialog_contract(inkwell, monkeypatch) -> None:
    seen: list[tuple[str, object]] = []

    def show(dialog, label, **_kw):
        seen.append((label, dialog))
        if label == "Send the Document?":
            assert dialog.GetMessage().startswith("All 2 words of notes.txt go to My ChatGPT plan")
            return wx.ID_NO
        if label == "Suggest Abbreviations":
            dialog._boxes[0].SetValue(True)
            return wx.ID_OK
        return wx.ID_CANCEL

    monkeypatch.setattr(inkwell, "_show_modal_dialog", show)
    assert inkwell._inkwell_pick_document() is None
    assert inkwell._inkwell_confirm_send("notes.txt", "two words") is False
    assert inkwell._inkwell_review_suggestions([("sig", "Kind regards")]) == [
        ("sig", "Kind regards")
    ]
    assert [label for label, _dialog in seen] == [
        "Choose a Document",
        "Send the Document?",
        "Suggest Abbreviations",
    ]
