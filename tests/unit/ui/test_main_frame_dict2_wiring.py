"""Source-contract test for DICT-2 Look Up dialog wiring in main_frame."""

from pathlib import Path


def test_dict2_imports_are_present() -> None:
    """DICT-2 wiring imports lexical module."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # Core lexical imports must be present.
    assert "from quill.core.lexical import" in source
    assert "default_service" in source
    # Check for individual imports in source regardless of formatting.
    assert "build_lookup_items" in source
    assert "render_lookup" in source


def test_dict2_service_initialized() -> None:
    """DICT-2 wiring initializes _lexical_service."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # The lexical service is initialized in __init__.
    assert "self._lexical_service = default_service(include_online=True)" in source


def test_dict2_lookup_dialog_method_exists() -> None:
    """DICT-2 wiring has show_lookup_dialog method."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    assert "def show_lookup_dialog(self, word: str)" in source
    # The method queries the lexical service.
    assert "self._lexical_service.lookup(" in source
    # The method renders the lookup result.
    assert "render_lookup(result)" in source
    # The method builds selectable items.
    assert "build_lookup_items(result)" in source


def test_dict2_dialog_uses_textctrl_readonly() -> None:
    """DICT-2 dialog uses wx.TE_READONLY TextCtrl for screen readers."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    # The lookup dialog uses a read-only, multiline TextCtrl.
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in source


def test_dict2_thesaurus_fallback_method_exists() -> None:
    """DICT-2 wiring has show_thesaurus_or_lookup fallback method."""
    main_frame_path = Path("quill/ui/main_frame.py")
    source = main_frame_path.read_text(encoding="utf-8")

    assert "def show_thesaurus_or_lookup(self, word: str)" in source
    assert "self.show_lookup_dialog(word)" in source
