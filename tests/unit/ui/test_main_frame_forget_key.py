"""Source-contract test for SEC-7 Forget API Key wiring in main_frame."""

from pathlib import Path


def _source() -> str:
    ui = Path("quill/ui")
    return (
        (ui / "main_frame.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_menu.py").read_text(encoding="utf-8")
    )


def test_forget_key_menu_item_removed_from_menu() -> None:
    source = _source()
    # The id and handler remain (per-provider "Forget this provider's key" now
    # lives in the AI Hub), but the standalone global "Forget API Key" menu item
    # was removed as part of the AI Hub consolidation (AICONS-1).
    assert "self._id_ai_forget_key = wx.NewIdRef()" in source
    assert '"&Forget API Key"' not in source


def test_forget_key_menu_item_is_bound() -> None:
    source = _source()
    assert "id=self._id_ai_forget_key" in source
    assert "self._forget_assistant_api_key()" in source


def test_forget_key_handler_clears_both_stores() -> None:
    source = _source()
    assert "def _forget_assistant_api_key(self) -> None:" in source
    # The handler confirms, then calls the core clear function.
    assert "from quill.core.assistant_ai import clear_assistant_api_key" in source
    assert "clear_assistant_api_key()" in source


def test_forget_key_disabled_when_no_key_stored() -> None:
    """Issue #128: 'Forget API Key' is greyed out when nothing is stored."""
    source = _source()
    # The menu-enable pass gates the forget item on key presence, separate from
    # the AI on/off toggle loop.
    assert "def _assistant_api_key_present(self) -> bool:" in source
    assert "bar.Enable(self._id_ai_forget_key, self._assistant_api_key_present())" in source
    # Forgetting a key refreshes the menu so the item greys out immediately.
    assert "self._request_menu_refresh()" in source


class _FakeMenuBar:
    def __init__(self, known_ids: set[object]) -> None:
        self._known = known_ids
        self.enabled: dict[object, bool] = {}

    def FindItemById(self, item_id: object) -> object | None:  # noqa: N802
        return object() if item_id in self._known else None

    def Enable(self, item_id: object, enable: bool) -> None:  # noqa: N802
        self.enabled[item_id] = enable


def test_apply_ai_menu_enabled_gates_forget_key_on_presence(monkeypatch) -> None:
    """The forget item tracks key presence independent of the AI toggle."""
    from types import SimpleNamespace

    from quill.ui.main_frame import MainFrame

    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: False)

    forget_id = object()
    bar = _FakeMenuBar({forget_id})
    frame = MainFrame.__new__(MainFrame)
    frame._menu_open_depth = 0
    frame._id_ai_forget_key = forget_id
    # Only the forget id is known to the bar; the AI-toggle ids are absent.
    for name in (
        "_id_ai_hub",
        "_id_ask_quill_chat",
        "_id_ask_quill_voice",
        "_id_ai_model",
        "_id_ai_switch_engine",
        "_id_ai_copilot_setup",
        "_id_ai_session_browser",
        "_id_ai_assistant",
        "_id_ai_prompt_studio",
        "_id_ai_agent_center",
        "_id_ai_rewrite_selection",
        "_id_ai_summarize_selection",
        "_id_ai_expand_selection",
        "_id_ai_generate_toc",
        "_id_ai_thesaurus",
        "_id_ai_continue_writing",
        "_id_ai_fix_grammar",
        "_id_train_style",
    ):
        setattr(frame, name, object())
    frame.frame = SimpleNamespace(GetMenuBar=lambda: bar)

    monkeypatch.setattr(frame, "_assistant_api_key_present", lambda: True, raising=False)
    frame._apply_ai_menu_enabled()
    assert bar.enabled[forget_id] is True

    monkeypatch.setattr(frame, "_assistant_api_key_present", lambda: False, raising=False)
    frame._apply_ai_menu_enabled()
    assert bar.enabled[forget_id] is False
