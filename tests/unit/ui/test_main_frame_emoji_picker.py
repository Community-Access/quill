"""Tests for EmojiPickerMixin (Insert > Emoji...).

Constructing a real wx.Dialog is not exercised in this suite (matching the
repo's dialog-test convention elsewhere), so the dialog class itself is
covered by source-contract assertions; the mixin's command logic is covered
with a fake host and a monkeypatched EmojiPickerDialog.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui.main_frame_emoji_picker import EmojiPickerMixin

_SRC = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_emoji_picker.py"
_TEXT = _SRC.read_text(encoding="utf-8")


class _FakeCommands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, Any, Any]] = []

    def try_register(self, command_id: str, label: str, handler: Any, binding: Any) -> None:
        self.registered.append((command_id, label, handler, binding))


class _FakeEditor:
    def __init__(self) -> None:
        self.written: list[str] = []

    def WriteText(self, text: str) -> None:
        self.written.append(text)


class _Host(EmojiPickerMixin):
    def __init__(self) -> None:
        self._wx = SimpleNamespace(ICON_INFORMATION=1, OK=1)
        self.frame = object()
        self.editor = _FakeEditor()
        self.commands = _FakeCommands()
        self.announcements: list[str] = []
        self.message_boxes: list[tuple[str, str]] = []

    def _binding_for(self, _command_id: str) -> str:
        return ""

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _show_message_box(self, message: str, title: str, _style: int) -> int:
        self.message_boxes.append((message, title))
        return 0


# ---------------------------------------------------------------------------
# Dialog source contract
# ---------------------------------------------------------------------------


def test_dialog_uses_show_modal_dialog_and_apply_modal_ids() -> None:
    assert "show_modal_dialog(self.dialog" in _TEXT
    assert "apply_modal_ids(" in _TEXT
    assert "ShowModal()" not in _TEXT


def test_dialog_controls_are_all_named() -> None:
    for ctrl in (
        "_search_ctrl",
        "_category_list",
        "_results",
        "_description",
        "_insert_btn",
        "_favorite_btn",
    ):
        assert f"self.{ctrl}.SetName(" in _TEXT, f"{ctrl} is missing an accessible name"


def test_favorites_and_recent_are_the_first_two_categories() -> None:
    method = _TEXT[_TEXT.index("self._categories = ") :][:120]
    assert "_FAVORITES, _RECENT" in method


def test_favoriting_never_touches_the_catalog_only_the_usage_store() -> None:
    assert "self._usage.toggle_favorite(" in _TEXT
    assert "self._usage.record_used(" in _TEXT
    assert "quill.core.emoji_usage import EmojiUsage" in _TEXT


def test_search_covers_symbol_emoticon_name_keyword_and_description() -> None:
    """The search box's own label promises every field the catalog carries;
    the actual ranking logic lives in quill.core.emoji_data.search (covered
    by test_emoji_data.py) -- this just confirms the dialog routes typed text
    into it rather than filtering some narrower subset itself."""
    assert "self._emoji_data.search(query)" in _TEXT
    assert ":) " in _TEXT  # the search box's placeholder/label mentions a smiley example


def test_category_browsing_and_search_do_not_fight_each_other() -> None:
    method = _TEXT[_TEXT.index("def _on_category_selected") :][:300]
    assert "self._search_ctrl.GetValue().strip()" in method


# ---------------------------------------------------------------------------
# insert_emoji()
# ---------------------------------------------------------------------------


def test_insert_emoji_shows_message_when_catalog_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("quill.core.emoji_data.is_available", lambda: False)
    host = _Host()
    host.insert_emoji()
    assert host.editor.written == []
    assert host.message_boxes  # explained rather than silently doing nothing


def test_insert_emoji_inserts_chosen_character_and_announces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("quill.core.emoji_data.is_available", lambda: True)
    chosen = SimpleNamespace(char="\U0001f600", name="grinning face")
    monkeypatch.setattr(
        "quill.ui.main_frame_emoji_picker.EmojiPickerDialog",
        lambda *a, **k: SimpleNamespace(show=lambda: chosen),
    )
    host = _Host()
    host.insert_emoji()
    assert host.editor.written == ["\U0001f600"]
    assert host.announcements == ["Inserted grinning face"]


def test_insert_emoji_cancelled_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.emoji_data.is_available", lambda: True)
    monkeypatch.setattr(
        "quill.ui.main_frame_emoji_picker.EmojiPickerDialog",
        lambda *a, **k: SimpleNamespace(show=lambda: None),
    )
    host = _Host()
    host.insert_emoji()
    assert host.editor.written == []
    assert host.announcements == []


def test_register_emoji_picker_commands() -> None:
    host = _Host()
    host._register_emoji_picker_commands()
    ids = {entry[0] for entry in host.commands.registered}
    assert ids == {"edit.insert_emoji"}
