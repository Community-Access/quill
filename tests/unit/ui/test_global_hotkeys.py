"""Global hotkeys: the allowlist boundary and the browser's note filter --
pure logic, no wx construction."""

from __future__ import annotations

from quill.core.sticky_notes import StickyNote
from quill.ui.main_frame_hotkeys import GLOBAL_HOTKEY_SAFE_COMMANDS, GlobalHotkeysMixin
from quill.ui.sticky_notes_browser import filter_notes


def _note(body: str, updated: str) -> StickyNote:
    base = StickyNote.create(body)
    return StickyNote(
        id=base.id, title=base.title, body=base.body, created_at=updated, updated_at=updated
    )


def test_filter_notes_empty_query_returns_all_newest_first() -> None:
    notes = [_note("older note", "2026-01-01T00:00:00"), _note("newer note", "2026-06-01T00:00:00")]
    result = filter_notes(notes, "")
    assert [n.body for n in result] == ["newer note", "older note"]


def test_filter_notes_matches_title_and_body_case_insensitive() -> None:
    notes = [
        _note("Groceries\nmilk and eggs", "2026-01-02T00:00:00"),
        _note("Meeting\ncall with MILK vendor", "2026-01-03T00:00:00"),
        _note("Unrelated\nnothing here", "2026-01-04T00:00:00"),
    ]
    result = filter_notes(notes, "milk")
    assert len(result) == 2
    assert all("milk" in (n.title + n.body).casefold() for n in result)


def test_filter_notes_no_match() -> None:
    assert filter_notes([_note("a", "2026-01-01T00:00:00")], "zzz") == []


class _Host(GlobalHotkeysMixin):
    """Just enough host protocol to exercise _global_hotkey_bindings."""

    def __init__(self, configured: dict[str, str], legacy: str | None = None) -> None:
        self.settings = type("S", (), {"global_hotkeys": configured})()
        self._legacy = legacy

    def _binding_for(self, command_id: str) -> str | None:
        return self._legacy if command_id == "tools.sticky_note_capture" else None

    def _parse_keybinding(self, binding: str | None):
        return (1, 65) if binding else None


def test_allowlist_is_the_boundary() -> None:
    host = _Host({
        "radio.play_pause": "Ctrl+Alt+P",
        "file.save": "Ctrl+Alt+S",  # NOT on the allowlist: must be dropped
        "edit.select_all": "Ctrl+Alt+A",  # ditto
    })
    bindings = host._global_hotkey_bindings()
    assert bindings["radio.play_pause"] == "Ctrl+Alt+P"
    assert "file.save" not in bindings
    assert "edit.select_all" not in bindings


def test_blank_bindings_are_dropped() -> None:
    host = _Host({"radio.play_pause": "   "})
    assert "radio.play_pause" not in host._global_hotkey_bindings()


def test_legacy_sticky_binding_survives_unless_overridden() -> None:
    host = _Host({}, legacy="Ctrl+Alt+N")
    assert host._global_hotkey_bindings()["tools.sticky_note_capture"] == "Ctrl+Alt+N"
    host = _Host({"tools.sticky_note_capture": "Ctrl+Alt+M"}, legacy="Ctrl+Alt+N")
    assert host._global_hotkey_bindings()["tools.sticky_note_capture"] == "Ctrl+Alt+M"


def test_every_allowlisted_command_is_low_risk_by_construction() -> None:
    """Meta-guard: the allowlist stays media/notes/compose only. Anything
    document-editing or destructive being added here should fail review AND
    this test."""
    allowed_prefixes = ("radio.", "podcasts.", "notes.", "tools.sticky", "tools.post_to_mastodon")
    for command_id, _label, _needs in GLOBAL_HOTKEY_SAFE_COMMANDS:
        assert command_id.startswith(allowed_prefixes), command_id
