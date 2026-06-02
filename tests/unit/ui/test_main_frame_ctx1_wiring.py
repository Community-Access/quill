"""Source-contract test for CTX-1 context menu wiring in main_frame."""

from pathlib import Path


def test_ctx1_imports_are_present() -> None:
    """CTX-1 wiring imports context_menu module."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # Core context_menu imports must be present.
    assert "from quill.core.context_menu import" in source
    assert "CMD_LOOK_UP" in source
    assert "CMD_THESAURUS" in source
    assert "CMD_SPELL_SUGGESTION" in source
    assert "CursorContext" in source
    assert "build_context_menu" in source


def test_ctx1_builder_method_exists() -> None:
    """CTX-1 wiring has _build_ctx1_menu_items method."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    assert "def _build_ctx1_menu_items(self)" in source
    # The method calls build_context_menu with is_feature_enabled.
    assert "build_context_menu(" in source
    assert "is_feature_enabled=self._feature_enabled" in source


def test_ctx1_menu_item_handlers_wired() -> None:
    """CTX-1 wiring binds handlers for all context menu commands."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # All CTX-1 command handlers are implemented.
    assert "CMD_SPELL_SUGGESTION" in source
    assert "CMD_SPELL_ADD" in source
    assert "CMD_SPELL_IGNORE" in source
    assert "CMD_LOOK_UP" in source
    assert "CMD_THESAURUS" in source
    assert "CMD_CUT" in source
    assert "CMD_COPY" in source
    assert "CMD_PASTE" in source
