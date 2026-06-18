from __future__ import annotations

from dataclasses import dataclass

from quill.core.a11y_regions import RegionTracker
from quill.platform.windows.sr_announce import (
    clear_transcript,
    enable_transcript_capture,
    set_transcript_path,
    transcript_entries,
)
from quill.ui.main_frame import MainFrame


@dataclass
class _DummyDialog:
    result: int

    def ShowModal(self) -> int:
        return self.result


class _DummyWx:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def MessageBox(self, message: str, caption: str, style: int) -> int:
        self.calls.append((message, caption, style))
        return 7


def test_show_modal_dialog_announces_entry_and_exit() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._region_tracker = RegionTracker()
    dialog = _DummyDialog(result=42)
    set_transcript_path(None)
    clear_transcript()
    enable_transcript_capture(True)
    try:
        result = frame._show_modal_dialog(dialog, "Find")
        assert result == 42
        assert transcript_entries() == ["Entered Find dialog", "Exited Find dialog"]
    finally:
        enable_transcript_capture(False)
        clear_transcript()


def test_show_message_box_announces_entry_and_exit() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._region_tracker = RegionTracker()
    frame._wx = _DummyWx()
    set_transcript_path(None)
    clear_transcript()
    enable_transcript_capture(True)
    try:
        result = frame._show_message_box("Body", "Caption", 123)
        assert result == 7
        assert frame._wx.calls == [("Body", "Caption", 123)]
        assert transcript_entries() == ["Entered Caption dialog", "Exited Caption dialog"]
    finally:
        enable_transcript_capture(False)
        clear_transcript()


class _FakeContent:
    """wx-like content control whose class name drives preferred matching."""

    def __init__(self) -> None:
        self._focused = False

    def GetChildren(self) -> list[object]:
        return []

    def HasFocus(self) -> bool:
        return self._focused

    def IsEnabled(self) -> bool:
        return True

    def IsShown(self) -> bool:
        return True

    def CanAcceptFocus(self) -> bool:
        return True

    def SetFocus(self) -> None:
        self._focused = True


def _make_listbox() -> _FakeContent:
    return type("ListBox", (_FakeContent,), {})()


class _FakeDialog:
    """Stands in for a raw ``wx.Dialog`` instance."""

    def __init__(self, children: list[object], result: int = 0) -> None:
        self._children = children
        self._result = result

    def GetChildren(self) -> list[object]:
        return self._children

    def ShowModal(self) -> int:
        return self._result


class _FakeWx:
    Dialog = _FakeDialog
    CallAfter = None


def _make_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._region_tracker = RegionTracker()
    frame._wx = _FakeWx()
    return frame


def test_show_modal_dialog_focuses_content_for_raw_dialog() -> None:
    # Every raw wx.Dialog routed through the chokepoint should have its first
    # content control focused, redirecting away from the OK-button auto-park.
    frame = _make_frame()
    content = _make_listbox()
    dialog = _FakeDialog([content])

    frame._show_modal_dialog(dialog, "Test")

    assert content.HasFocus() is True


def test_show_modal_dialog_skips_dialog_subclasses() -> None:
    # wx.Dialog *subclasses* manage their own focus; the type() gate must skip
    # them so their construction-time focus is preserved.
    frame = _make_frame()
    content = _make_listbox()

    class _SubDialog(_FakeDialog):
        pass

    dialog = _SubDialog([content])

    frame._show_modal_dialog(dialog, "Test")

    assert content.HasFocus() is False


def test_show_modal_dialog_skips_native_dialogs() -> None:
    # Native dialogs are not instances of wx.Dialog here, so the gate is a
    # no-op and never touches focus.
    frame = _make_frame()
    content = _make_listbox()

    class _NativeDialog:
        def __init__(self, children: list[object]) -> None:
            self._children = children

        def GetChildren(self) -> list[object]:
            return self._children

        def ShowModal(self) -> int:
            return 0

    dialog = _NativeDialog([content])

    frame._show_modal_dialog(dialog, "Test")

    assert content.HasFocus() is False


def test_request_menu_refresh_defers_when_menu_is_open() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._menu_open_depth = 1
    frame._pending_menu_refresh = False

    class _Wx:
        pass

    frame._wx = _Wx()

    called: list[str] = []
    frame._refresh_contextual_menu_items = lambda: called.append("context")
    frame._sync_announcement_backend_menu_state = lambda: called.append("announce")
    frame._apply_watch_folder_menu_state = lambda: called.append("watch")
    frame._apply_ai_menu_enabled = lambda: called.append("ai")
    frame._refresh_recent_menu = lambda: called.append("recent")
    frame._refresh_sessions_menu = lambda: called.append("sessions")

    frame._request_menu_refresh()

    assert frame._pending_menu_refresh is True
    assert called == []


def test_request_menu_refresh_flushes_when_menu_is_closed() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._menu_open_depth = 0
    frame._pending_menu_refresh = False

    class _Wx:
        pass

    frame._wx = _Wx()

    called: list[str] = []
    frame._refresh_contextual_menu_items = lambda: called.append("context")
    frame._sync_announcement_backend_menu_state = lambda: called.append("announce")
    frame._apply_watch_folder_menu_state = lambda: called.append("watch")
    frame._apply_ai_menu_enabled = lambda: called.append("ai")
    frame._refresh_recent_menu = lambda: called.append("recent")
    frame._refresh_sessions_menu = lambda: called.append("sessions")

    frame._request_menu_refresh()

    assert frame._pending_menu_refresh is False
    assert called == ["recent", "sessions", "context", "announce", "watch", "ai"]


def test_refresh_recent_menu_defers_when_menu_is_open() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._menu_open_depth = 1
    frame._pending_menu_refresh = False

    class _Wx:
        pass

    frame._wx = _Wx()
    frame._recent_menu = object()
    frame._request_menu_refresh = MainFrame._request_menu_refresh.__get__(frame, MainFrame)

    frame._refresh_recent_menu()

    assert frame._pending_menu_refresh is True


def test_refresh_sessions_menu_defers_when_menu_is_open() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._menu_open_depth = 1
    frame._pending_menu_refresh = False

    class _Wx:
        pass

    frame._wx = _Wx()
    frame._sessions_menu = object()
    frame._request_menu_refresh = MainFrame._request_menu_refresh.__get__(frame, MainFrame)

    frame._refresh_sessions_menu()

    assert frame._pending_menu_refresh is True


class _StubEditor:
    def __init__(self, text: str, selection: tuple[int, int], cursor: int) -> None:
        self._text = text
        self._selection = selection
        self._cursor = cursor

    def GetValue(self) -> str:
        return self._text

    def GetSelection(self) -> tuple[int, int]:
        return self._selection

    def GetInsertionPoint(self) -> int:
        return self._cursor


def _writing_action_frame(editor: _StubEditor) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.editor = editor
    frame._status_messages = []
    frame._set_status = frame._status_messages.append
    frame._writing_prompts = []
    frame.open_writing_assistant = frame._writing_prompts.append
    frame._ai_require_connection = lambda: None  # prevent real AI threads in tests
    return frame


def test_writing_action_blocked_when_ai_disabled(monkeypatch) -> None:
    import quill.core.ai.model_manager as model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: False)
    editor = _StubEditor("Hello world.", selection=(0, 5), cursor=0)
    frame = _writing_action_frame(editor)

    frame.open_ai_rewrite_selection()

    assert any("AI is turned off" in msg for msg in frame._status_messages)


def test_writing_action_falls_back_to_paragraph_without_selection(monkeypatch) -> None:
    import quill.core.ai.model_manager as model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)
    text = "First paragraph.\n\nSecond paragraph here."
    cursor = text.index("Second")
    editor = _StubEditor(text, selection=(cursor, cursor), cursor=cursor)
    frame = _writing_action_frame(editor)

    frame.open_ai_rewrite_selection()

    assert any("paragraph" in msg for msg in frame._status_messages)


def test_summarize_falls_back_to_whole_document_without_selection(monkeypatch) -> None:
    import quill.core.ai.model_manager as model_manager
    import quill.core.assistant_agents as aa

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)

    captured: dict[str, object] = {}

    def _fake_build(
        agent_id: str, *, selection_text: str = "", document_text: str = "", **_: object
    ) -> None:
        captured["agent_id"] = agent_id
        captured["document_text"] = document_text
        return None

    monkeypatch.setattr(aa, "build_agent_plan", _fake_build)

    text = "Alpha.\n\nBeta.\n\nGamma."
    editor = _StubEditor(text, selection=(2, 2), cursor=2)
    frame = _writing_action_frame(editor)
    from quill.core.assistant_ai import AssistantConnectionSettings

    frame._ai_require_connection = lambda: (AssistantConnectionSettings(provider="ollama"), "")

    frame.open_ai_summarize_selection()

    assert captured.get("agent_id") == "summarize"
    assert "Gamma." in captured.get("document_text", "")
