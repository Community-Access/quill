"""Braille Mode cues and detailed status through the real MainFrame mixins.

The core decisions are tested in ``tests/unit/core/test_braille_settings_behaviour.py``;
this proves the shell actually feeds them: a caret move in a braille file
speaks a crossing only when its setting is on, the explicit page commands are
not echoed, and Read Detailed Status reports the proofing companion file.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.braille_cues import page_break_mode
from quill.core.braille_position import BraillePositionResolver
from quill.core.brf_document import BRFDocument
from quill.core.brf_sidecar import BRFSidecar, write_sidecar
from quill.core.settings import Settings
from quill.ui.main_frame_braille_phase2 import BraillePhase2CommandsMixin

# Two pages split by a form feed; page 2 opens on print page 7 and holds a
# 45-cell line against a 40-cell page width.
_TEXT = "------#6\nfirst page\n\x0c------#7\n" + "x" * 45 + "\nend\n"


class _Editor:
    def __init__(self) -> None:
        self.pos = 0

    def GetCurrentPos(self) -> int:
        return self.pos


class _Host(BraillePhase2CommandsMixin):
    def __init__(self, settings: Settings, path: Path | None = None) -> None:
        self.settings = settings
        self.editor = _Editor()
        self.document = SimpleNamespace(path=path, text=_TEXT)
        self.spoken: list[str] = []
        self._status_message = ""
        doc = BRFDocument.from_text_and_suffix(_TEXT, ".brf")
        self._resolver = BraillePositionResolver(doc, mode=page_break_mode(settings))

    def _active_brf_resolver(self) -> object:
        return self._resolver

    def _announce(self, message: str, **_kwargs: object) -> None:
        self._status_message = message
        self.spoken.append(message)

    def move(self, offset: int) -> None:
        self.editor.pos = offset
        self._maybe_announce_braille_movement()


_PAGE_TWO = _TEXT.index("------#7")
_LONG_LINE = _TEXT.index("x" * 45)


def test_caret_cues_are_silent_by_default() -> None:
    host = _Host(Settings())
    host.move(0)
    host.move(_PAGE_TWO)
    host.move(_LONG_LINE)
    assert host.spoken == []


def test_page_change_setting_speaks_the_new_page() -> None:
    host = _Host(Settings(braille_auto_announce_page_changes=True))
    host.move(0)
    host.move(_PAGE_TWO)
    assert host.spoken == ["Braille page 2."]


def test_print_page_setting_speaks_the_new_print_page() -> None:
    host = _Host(Settings(braille_auto_announce_print_page_changes=True))
    host.move(0)
    host.move(_PAGE_TWO)
    assert host.spoken == ["Print page 7."]


def test_overflow_setting_warns_on_a_long_line() -> None:
    host = _Host(Settings(braille_auto_announce_line_overflow=True))
    host.move(_PAGE_TWO)
    host.move(_LONG_LINE)
    host.move(_LONG_LINE + 3)
    assert host.spoken == ["Line too long: 45 cells, limit 40."]


def test_page_command_reply_is_not_repeated_by_the_cue() -> None:
    host = _Host(Settings(braille_auto_announce_page_changes=True))
    host.move(0)
    host._status_message = "Braille page 2 of 2."  # what Next Braille Page said
    host.move(_PAGE_TWO)
    assert host.spoken == []


def test_detailed_status_reports_proofing_from_the_companion_file(tmp_path: Path) -> None:
    brf = tmp_path / "book.brf"
    brf.write_text(_TEXT, encoding="ascii")
    sidecar = BRFSidecar()
    sidecar.proofing.last_proofed_braille_page = 1
    sidecar.proofing.pages_needing_review = [2]
    write_sidecar(brf, sidecar)

    on = _Host(Settings(braille_status_verbosity="detailed"), path=brf)
    position = on._resolver.resolve(_PAGE_TWO)
    text = on._compose_detailed_status(on._resolver, position)
    assert "Last proofed page: 1" in text
    assert "One page marked needs review" in text

    off = _Host(
        Settings(braille_status_verbosity="detailed", braille_include_proofing_status=False),
        path=brf,
    )
    text = off._compose_detailed_status(off._resolver, position)
    assert "proofed" not in text


def test_detailed_status_without_a_saved_file_says_nothing_about_proofing() -> None:
    host = _Host(Settings(braille_status_verbosity="detailed"))
    position = host._resolver.resolve(0)
    assert "proofed" not in host._compose_detailed_status(host._resolver, position)
    assert host.spoken == []
