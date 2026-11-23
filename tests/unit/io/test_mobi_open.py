"""A Kindle (MOBI) book opens in QUILL and QUILL Lite, and is never written back."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.io.mobi_html import HEADINGS_INFERRED_NOTE
from quill.io.mobi_open import is_mobi_path, read_mobi_document
from tests.unit.io.mobi_fixture import PNG_PIXEL, build_mobi

BOOK = (
    '<p><font size="6"><b>Garden Handbook</b></font></p><p>How it works.</p>'
    '<p><img recindex="00001"></p><p><font size="4"><b>Rules</b></font></p><p>Be kind.</p>'
)


def _book(folder: Path, name: str = "garden.mobi", html: str = BOOK) -> Path:
    path = folder / name
    path.write_bytes(build_mobi(html, pictures=(PNG_PIXEL,), exth={524: "en"}))
    return path


def test_a_book_opens_as_markdown_with_its_pictures_beside_it(tmp_path: Path) -> None:
    path = _book(tmp_path)
    document = read_mobi_document(path)
    assert document.text == (
        "# Garden Handbook\n\nHow it works.\n\n"
        "![Picture 1](garden_pictures/picture-1.png)\n\n## Rules\n\nBe kind.\n"
    )
    assert (tmp_path / "garden_pictures" / "picture-1.png").read_bytes() == PNG_PIXEL
    assert document.path == path and not document.modified
    meta = document.source_metadata
    assert meta["source_kind"] == "mobi" and meta["language"] == "en"
    assert meta["headings_inferred"] == 2 and meta["picture_count"] == 1
    assert meta["open_note"] == HEADINGS_INFERRED_NOTE


def test_a_name_with_spaces_gives_a_link_markdown_can_follow(tmp_path: Path) -> None:
    document = read_mobi_document(_book(tmp_path, "my garden.mobi"))
    assert "![Picture 1](my%20garden_pictures/picture-1.png)" in document.text


def test_a_book_without_pictures_or_headings_writes_nothing_and_says_nothing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "plain.mobi"
    path.write_bytes(build_mobi("<p>Just text.</p>"))
    document = read_mobi_document(path)
    assert document.text == "Just text.\n"
    assert "open_note" not in document.source_metadata
    assert sorted(p.name for p in tmp_path.iterdir()) == ["plain.mobi"]


def test_pictures_go_to_quills_folder_when_the_books_cannot_be_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _book(tmp_path)
    beside = tmp_path / "garden_pictures"
    real_mkdir = Path.mkdir

    def refuse(self: Path, *args: object, **kwargs: object) -> None:
        if self == beside:
            raise PermissionError("read-only")
        real_mkdir(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "mkdir", refuse)
    document = read_mobi_document(path, pictures_root=tmp_path / "data")
    saved = next((tmp_path / "data").rglob("picture-1.png"))
    assert f"![Picture 1]({saved.as_uri()})" in document.text


def test_only_mobi_and_prc_are_kindle_books() -> None:
    assert is_mobi_path("a.MOBI") and is_mobi_path("b.prc")
    assert not is_mobi_path("c.azw3") and not is_mobi_path("d.epub")


# ------------------------------------------------------------- QUILL's paths


def test_quills_open_reads_it_on_a_worker_and_save_goes_to_save_as(tmp_path: Path) -> None:
    from quill.io.export import EXPORT_ONLY_SUFFIXES
    from quill.io.open_read import OFFICE_STREAM_SUFFIXES, read_open_document

    path = _book(tmp_path, "garden.prc")
    document, extra = read_open_document(path, ".prc")
    assert extra is None and document.text.startswith("# Garden Handbook")
    assert {".mobi", ".prc"} <= OFFICE_STREAM_SUFFIXES & EXPORT_ONLY_SUFFIXES


def test_a_refused_book_reaches_quill_as_its_sentence(tmp_path: Path) -> None:
    from quill.io.mobi_read import MobiDrmError
    from quill.io.open_read import read_open_document

    path = tmp_path / "locked.mobi"
    path.write_bytes(build_mobi("<p>x</p>", encryption=1))
    with pytest.raises(MobiDrmError, match="locked.mobi is locked with DRM"):
        read_open_document(path, ".mobi")


def test_heading_navigation_treats_the_book_as_markdown() -> None:
    from quill.core.links import infer_markup_kind
    from quill.core.lite.filetypes import markup_language_for

    assert infer_markup_kind(Path("a.mobi")) == "markdown" == markup_language_for("b.prc")


def test_quill_says_the_note_once_with_the_open() -> None:
    from quill.ui.main_frame_braille import BrailleCommandsMixin

    host = BrailleCommandsMixin.__new__(BrailleCommandsMixin)
    document = SimpleNamespace(
        source_metadata={"source_kind": "mobi", "open_note": HEADINGS_INFERRED_NOTE},
        name="garden.mobi",
    )
    message = host._brf_open_message(document, Path("garden.mobi"))
    assert message == f"Opened garden.mobi. {HEADINGS_INFERRED_NOTE}"


def test_quills_open_dialog_offers_kindle_books() -> None:
    source = Path("quill/ui/main_frame_simple_open.py").read_text(encoding="utf-8")
    assert '"Kindle books (*.mobi;*.prc)|*.mobi;*.prc|' in source
    assert source.count("*.epub;*.mobi;*.prc;") == 2  # Supported files, label and pattern


# -------------------------------------------------------------- QUILL Lite


def test_lite_prepares_the_same_markdown_and_note(tmp_path: Path) -> None:
    from quill.core.lite.open_prepare import PLAIN, RICH, prepare, prepare_in_background

    path = _book(tmp_path)
    prepared = prepare(path, RICH)  # a rich window still gets the book as text
    assert prepared.mode == PLAIN
    assert prepared.text == read_mobi_document(path).text
    assert prepared.open_note == HEADINGS_INFERRED_NOTE
    assert prepare_in_background(path)


def test_lite_reports_a_refusal_as_the_readers_sentence(tmp_path: Path) -> None:
    from quill.core.lite.open_prepare import PLAIN, prepare

    path = tmp_path / "new.mobi"
    path.write_bytes(build_mobi("<p>x</p>", version=8))
    with pytest.raises(OSError) as raised:
        prepare(path, PLAIN)
    assert str(raised.value).startswith(
        "[QUILL-IO-MOBI-KF8] new.mobi is a newer Kindle book (AZW3)"
    )
    with pytest.raises(FileNotFoundError):
        prepare(tmp_path / "gone.mobi", PLAIN)


def test_lite_offers_kindle_books_and_never_writes_one_back() -> None:
    from quill.apps.lite_window_pdf import is_read_only_source
    from quill.core.lite.filetypes import OPEN_WILDCARD

    assert "Kindle books, opened as Markdown (*.mobi;*.prc)|*.mobi;*.prc|" in OPEN_WILDCARD
    assert OPEN_WILDCARD.split("|")[1].endswith(";*.mobi;*.prc")
    assert is_read_only_source("garden.mobi") and is_read_only_source("garden.PRC")


def test_a_large_random_book_opens_within_its_bounds(tmp_path: Path) -> None:
    path = tmp_path / "big.mobi"
    words = " ".join(os.urandom(4).hex() for _ in range(20_000))
    path.write_bytes(build_mobi(f"<p>{words}</p>", compression=1))  # 45 records
    assert len(read_mobi_document(path).text) == len(words) + 1


# ------------------------------------------------------- Scribe's result


def test_scribes_kindle_book_opens_in_quill_lite(tmp_path: Path) -> None:
    from quill.apps.lite_window_scribe import LiteScribeHost
    from quill.core.scribe.results import default_action

    opened: list[Path] = []
    host = LiteScribeHost(SimpleNamespace(open_path=opened.append))
    host._hold = lambda opening, _phrase: opening()  # after the sentence, at once here
    path = _book(tmp_path)
    assert default_action("mobi") == "editor"
    said = host.scribe_open_result(SimpleNamespace(), "mobi", path)
    assert said == "The Kindle book is open in QUILL Lite" and opened == [path]
    labels = [label for label, _run in host.scribe_next_steps(SimpleNamespace(), {"mobi": path})]
    assert labels == ["Open the Kindle Book in QUILL Lite"]


def test_other_apps_open_scribes_kindle_book_in_the_editor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_app_host

    launched: list[Path] = []
    monkeypatch.setattr(scribe_app_host, "open_in_editor", lambda p: launched.append(p) or "QUILL")
    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "QUILL")
    path = _book(tmp_path)
    assert scribe_app_host.open_elsewhere("mobi", path) == "The Kindle book is open in QUILL"
    steps = scribe_app_host.elsewhere_steps(SimpleNamespace(), {"mobi": path}, print)
    assert [label for label, _run in steps] == ["Open the Kindle Book in QUILL"]
    assert launched == [path]


def test_quills_next_steps_open_scribes_kindle_book(tmp_path: Path) -> None:
    from quill.ui.main_frame_scribe import QuillScribeHost

    opened: list[Path] = []
    frame = SimpleNamespace(open_file=opened.append, settings=SimpleNamespace(ai_connection="off"))
    host = QuillScribeHost(frame)
    path = _book(tmp_path)
    assert host.scribe_open_result(SimpleNamespace(open_as=""), "mobi", path) == (
        "The Kindle book is open in QUILL"
    )
    steps = dict(host.scribe_next_steps(SimpleNamespace(), {"mobi": path}))
    assert list(steps) == ["Open the Kindle Book (MOBI)"]
    steps["Open the Kindle Book (MOBI)"]()
    assert opened == [path, path]
