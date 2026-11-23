"""QUILL Lite opens a Kindle (MOBI) book as Markdown, says its one note, and never
writes it back."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.lite.open_prepare import PLAIN, prepare
from quill.io.mobi_html import HEADINGS_INFERRED_NOTE
from tests.unit.io.mobi_fixture import PNG_PIXEL, build_mobi

BOOK = '<p><font size="6"><b>Garden</b></font></p><p>Text.</p><p><img recindex="00001"></p>'


def _opened(lite_window: Any, tmp_path: Path) -> tuple[Any, Path]:
    path = tmp_path / "garden.mobi"
    original = build_mobi(BOOK, pictures=(PNG_PIXEL,))
    path.write_bytes(original)
    window = lite_window("")
    assert window._commit_load(path, prepare(path, PLAIN))
    return window, path


def test_a_kindle_book_opens_as_markdown_and_says_its_note_once(
    lite_window: Any, tmp_path: Path
) -> None:
    window, _path = _opened(lite_window, tmp_path)
    assert window.control.GetValue().startswith("# Garden\n\nText.\n\n![Picture 1](")
    assert window.document_language() == "markdown"  # the heading keys work
    assert window.announcements.count(HEADINGS_INFERRED_NOTE) == 1


def test_save_goes_to_save_as_with_a_markdown_name(
    lite_window: Any, lite_dialogs: Any, tmp_path: Path
) -> None:
    window, path = _opened(lite_window, tmp_path)
    original = path.read_bytes()
    assert window.proposed_name_for_mode() == "garden.md"
    went: list[bool] = []
    window.cmd_save_as = lambda: went.append(True) or False
    window.cmd_save()
    assert went == [True] and path.read_bytes() == original
    said = lite_dialogs.opened[-1][1][0]
    assert said.startswith(
        "garden.mobi was opened as extracted text. QUILL Lite cannot write .mobi"
    )


def test_saving_elsewhere_takes_the_pictures_along(lite_window: Any, tmp_path: Path) -> None:
    window, _path = _opened(lite_window, tmp_path)
    target = tmp_path / "elsewhere" / "garden.md"
    target.parent.mkdir()
    window._write_to(target, window.control.GetValue(), as_rich=False)
    assert "![Picture 1](garden_pictures/picture-1.png)" in target.read_text(encoding="utf-8")
    assert (target.parent / "garden_pictures" / "picture-1.png").read_bytes() == PNG_PIXEL
