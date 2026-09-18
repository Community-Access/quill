"""The frame half of bad.md P2.8: stale bookmarks, a dropped Bold, a loud list.

L7 -- List Bookmarks printed the raw stored offset while *jumping* re-anchored
by snippet, so after any edit every row named a line the jump would not land on.
A list of jump points whose numbers are wrong is worse than a list with no
numbers, because it is checkable and wrong. The re-anchored offset was also
written back in memory only, so the tab and the file kept the pre-edit value
until the next Set Bookmark.

R11 -- choosing "Convert to Rich Text" in the plain-text formatting prompt
converted the document and then returned, so the Bold you pressed Ctrl+B for
never happened, and nothing said so.

C8 -- the Copy Tray dialog announced "Slot N loaded" on every list move, which
the screen reader had just read for itself (GATE-13).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.ui.main_frame import MainFrame


class _BookmarkHost:
    """Just the bookmark helpers, and a record of what was persisted."""

    _resolve_bookmark_target = MainFrame._resolve_bookmark_target

    def __init__(self, text: str, stored: int, resolved: int) -> None:
        from quill.core.bookmarks import set_bookmark

        self._bookmarks = set_bookmark({}, "start", stored)
        self._bookmark_anchors = {"start": object()}
        self._resolved = resolved
        self.editor = _Editor(text)
        self.saves = 0
        self.captured: list[tuple[str, int]] = []

    def _capture_bookmark_anchor(self, name: str, position: int) -> None:
        self.captured.append((name, position))

    def _save_active_bookmarks(self) -> None:
        self.saves += 1


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text

    def GetValue(self) -> str:
        return self._text


@pytest.fixture
def _resolves_to(monkeypatch: pytest.MonkeyPatch):
    def _install(position: int) -> None:
        import quill.ui.main_frame as module

        monkeypatch.setattr(module, "resolve_anchor", lambda _text, _anchor: position)

    return _install


def test_a_moved_bookmark_is_written_back_to_disk(_resolves_to) -> None:
    _resolves_to(40)
    host = _BookmarkHost("some text", stored=10, resolved=40)

    assert host._resolve_bookmark_target("start") == 40
    assert host._bookmarks["start"] == 40
    assert host.saves == 1, "the re-anchored offset must survive a restart"
    assert host.captured == [("start", 40)]


def test_a_bookmark_that_has_not_moved_writes_nothing(_resolves_to) -> None:
    _resolves_to(10)
    host = _BookmarkHost("some text", stored=10, resolved=10)

    assert host._resolve_bookmark_target("start") == 10
    assert host.saves == 0


def test_the_list_asks_for_the_resolved_position_not_the_stored_one() -> None:
    """A source contract: the loop must go through the resolver."""
    source = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    listing = source[source.index("    def list_bookmarks(self)") :][:1600]
    assert "position = self._resolve_bookmark_target(name)" in listing
    assert "position = self._bookmarks[name]" not in listing


def test_converting_to_rich_then_applies_the_command_that_asked() -> None:
    """R11, as a source contract over the four commands that offer the prompt."""
    root = Path(__file__).resolve().parents[3] / "quill" / "ui"
    frame = (root / "main_frame.py").read_text(encoding="utf-8")
    headings = (root / "main_frame_headings.py").read_text(encoding="utf-8")

    for attr in ("apply_bold", "apply_italic", "apply_underline"):
        assert f'self._rich_toggle_run_attr("{attr}")' in frame
    # And none of the four may still return without doing anything.
    assert frame.count('if choice == "rich":') == 3
    assert 'if choice == "rich":' in headings
    assert 'self._rich_format_command("set_heading"' in headings


def test_the_tray_dialog_does_not_speak_over_the_reader() -> None:
    """C8: the slot readout on a list move is a label change, not an announcement."""
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "copy_tray_dialog.py"
    ).read_text(encoding="utf-8")
    load = source[source.index("    def _load_slot(self") :][:900]
    assert "self._set_status_quiet(" in load
    assert "self._set_status(" not in load
