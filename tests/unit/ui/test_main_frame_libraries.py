"""Tests that open_prompt_library and open_skill_library route through _show_modal_dialog."""

from __future__ import annotations

from pathlib import Path

import quill.ui.main_frame as main_frame_module
from quill.core.document import Document
from quill.ui.main_frame import MainFrame


class _Frame:
    pass


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame.document = Document(path=Path("note.md"), text="hello")
    frame.settings = type("Settings", (), {})()
    frame.keymap = {}
    frame._notifications = []
    frame._wx = type("Wx", (), {"version": staticmethod(lambda: "4.2-test"), "ID_OK": 5100})()
    frame._set_status = lambda message: setattr(frame, "_status_message", message)
    frame._record_notification = lambda message, category="info": None
    frame._announce = lambda *_args, **_kwargs: None
    return frame


class _FakeInnerDialog:
    def __init__(self):
        self._centered = False

    def CenterOnParent(self):
        self._centered = True

    def ShowModal(self):
        raise AssertionError("ShowModal must not be called directly")

    def Destroy(self):
        pass


class _FakePromptLibraryDialog:
    def __init__(self, *_args, **_kwargs):
        self.dialog = _FakeInnerDialog()

    def close(self):
        pass


class _FakeSkillLibraryDialog:
    def __init__(self, *_args, **_kwargs):
        self.dialog = _FakeInnerDialog()

    def close(self):
        pass


def test_open_prompt_library_uses_show_modal_dialog(monkeypatch) -> None:
    frame = _build_frame()
    modal_calls: list[str] = []
    frame._show_modal_dialog = lambda _dlg, label, **_kw: (
        modal_calls.append(label) or frame._wx.ID_OK
    )

    monkeypatch.setattr(
        main_frame_module, "PromptLibraryDialog", _FakePromptLibraryDialog, raising=False
    )
    monkeypatch.setattr(frame, "_get_prompt_library", lambda: object())
    monkeypatch.setattr(frame, "_current_document_title", lambda: "note.md")

    class _FakeEditor:
        def GetStringSelection(self):
            return ""

        def GetValue(self):
            return "hello"

    frame.editor = _FakeEditor()

    from quill.ui import prompt_library_dialog as pld_mod

    monkeypatch.setattr(pld_mod, "PromptLibraryDialog", _FakePromptLibraryDialog)

    frame.open_prompt_library()

    assert modal_calls == ["Prompt Library"]


class _FakeAILibraryDialog:
    def __init__(self, *_args, **_kwargs):
        self.dialog = _FakeInnerDialog()

    def close(self):
        pass


def test_open_ai_library_uses_show_modal_dialog(monkeypatch) -> None:
    frame = _build_frame()
    modal_calls: list[str] = []
    frame._show_modal_dialog = lambda _dlg, label, **_kw: (
        modal_calls.append(label) or frame._wx.ID_OK
    )

    monkeypatch.setattr(frame, "_get_prompt_library", lambda: object())
    monkeypatch.setattr(frame, "_current_document_title", lambda: "note.md")
    monkeypatch.setattr(frame, "_ai_insert_text", lambda *_: None)
    frame._skill_store_cache = object()

    class _FakeEditor:
        def GetStringSelection(self):
            return ""

        def GetValue(self):
            return "hello"

    frame.editor = _FakeEditor()

    from quill.ui import agent_editor_host as aeh_mod
    from quill.ui import ai_library_dialog as ail_mod

    monkeypatch.setattr(ail_mod, "AILibraryDialog", _FakeAILibraryDialog)
    monkeypatch.setattr(aeh_mod, "_catalog_agents", lambda: [])

    frame.open_ai_library()

    assert modal_calls == ["AI Library"]


def test_open_skill_library_uses_show_modal_dialog(monkeypatch) -> None:
    frame = _build_frame()
    modal_calls: list[str] = []
    frame._show_modal_dialog = lambda _dlg, label, **_kw: (
        modal_calls.append(label) or frame._wx.ID_OK
    )

    monkeypatch.setattr(frame, "_get_skill_files", lambda: [])
    monkeypatch.setattr(frame, "_current_document_title", lambda: "note.md")
    monkeypatch.setattr(frame, "_ai_insert_text", lambda *_: None)

    class _FakeEditor:
        def GetStringSelection(self):
            return ""

        def GetValue(self):
            return "hello"

    frame.editor = _FakeEditor()

    from quill.ui import skill_library_dialog as sld_mod

    monkeypatch.setattr(sld_mod, "SkillLibraryDialog", _FakeSkillLibraryDialog)

    frame.open_skill_library()

    assert modal_calls == ["Skill Library"]
