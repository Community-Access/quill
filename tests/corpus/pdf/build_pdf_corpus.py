"""Build the small PDF corpus the PDF reader's tests read (tests/corpus/pdf).

Run from the repository root::

    python tests/corpus/pdf/build_pdf_corpus.py

Every file is drawn with pypdf alone (no reportlab in the venv), from content
streams written out by hand, so each one is a few kilobytes and its text, page
order and outline are known exactly. The expectations live in the tests
(``tests/unit/io/test_pdf_corpus.py``); this script only makes the files.

The fonts are the standard Helvetica, never embedded, except where a page needs
a ``/ToUnicode`` map that deliberately breaks the text (``damaged_encoding``).
``build_long`` makes the large documents the latency budget is measured on; the
tests call it into a temporary folder rather than committing a big file.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

HERE = Path(__file__).resolve().parent

#: The password on ``encrypted.pdf``. A fixture value, not a secret.
FIXTURE_PASSWORD = "quill-fixture"

PROSE = (
    "The committee met on a Tuesday, which was unusual, and agreed that the",
    "report would be circulated before the end of the month. Nobody objected",
    "to the timetable, although two members asked that the appendix be read",
    "aloud at the next meeting so that everyone could follow the figures.",
)

_Line = tuple[float, float, str]  # x, y, text


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(lines: Iterable[_Line], *, size: int = 11, spacing: float = 0.0) -> str:
    parts = []
    for x, y, text in lines:
        tc = f"{spacing} Tc " if spacing else ""
        parts.append(f"BT /F1 {size} Tf {tc}{x} {y} Td ({_escape(text)}) Tj ET")
    return "\n".join(parts)


def _block(x: float, top: float, lines: Sequence[str], *, leading: float = 14.0) -> list[_Line]:
    return [(x, top - index * leading, text) for index, text in enumerate(lines)]


class _Builder:
    """A PdfWriter with one shared Helvetica and pages from content strings."""

    def __init__(self) -> None:
        self.writer = PdfWriter()
        self.helvetica = self.writer._add_object(
            DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            })
        )

    def page(self, content: str, *, font: object | None = None, image: bool = False) -> None:
        page = self.writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        stream.set_data(content.encode("latin-1"))
        page[NameObject("/Contents")] = self.writer._add_object(stream)
        resources = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font or self.helvetica})
        })
        if image:
            resources[NameObject("/XObject")] = DictionaryObject({
                NameObject("/Im1"): self._gray_image()
            })
        page[NameObject("/Resources")] = resources

    def _gray_image(self) -> object:
        """A 16 x 16 grey square: a page that is a picture and nothing else."""
        image = DecodedStreamObject()
        image.set_data(bytes((index * 7) % 256 for index in range(256)))
        image.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(16),
            NameObject("/Height"): NumberObject(16),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        })
        return self.writer._add_object(image)

    def font_with_unicode_map(self, mapping: dict[int, int]) -> object:
        """Helvetica whose ``/ToUnicode`` says each code means ``mapping[code]``.

        Codes not in *mapping* map to themselves, so only the named letters are
        damaged. This is how a real PDF ends up reading as replacement
        characters or private-use codepoints: the glyphs draw correctly, and the
        map that says what they mean is wrong.
        """
        entries = [f"<{code:02X}> <{mapping.get(code, code):04X}>" for code in range(0x20, 0x7F)]
        chunks = [entries[start : start + 90] for start in range(0, len(entries), 90)]
        body = "\n".join(
            f"{len(chunk)} beginbfchar\n" + "\n".join(chunk) + "\nendbfchar" for chunk in chunks
        )
        cmap = (
            "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
            "1 begincodespacerange\n<00> <FF>\nendcodespacerange\n"
            f"{body}\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
        )
        stream = DecodedStreamObject()
        stream.set_data(cmap.encode("ascii"))
        return self.writer._add_object(
            DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                NameObject("/ToUnicode"): self.writer._add_object(stream),
            })
        )

    def save(self, path: Path) -> Path:
        with path.open("wb") as handle:
            self.writer.write(handle)
        return path


# -- the corpus ---------------------------------------------------------------- #


def clean_prose(path: Path) -> Path:
    build = _Builder()
    build.page(
        _stream([
            (72, 720, "Chapter One"),
            *_block(72, 690, PROSE),
            *_block(
                72,
                620,
                (
                    "In 2024 the library lent 1,234 books, and the inter-",
                    "national exchange added ISBN 978-0-306-40615-7 to the catalogue.",
                ),
            ),
        ])
    )
    build.page(
        _stream(
            _block(
                72,
                720,
                (
                    "The second page continues the minutes. The treasurer reported a",
                    "balance of 4,512.75 pounds, which the members accepted without a",
                    "vote, and the meeting closed at four.",
                ),
            )
        )
    )
    return build.save(path)


LEFT_COLUMN = (
    "The river rose slowly through the night",
    "and by morning the lower fields were under",
    "water. Farmers moved their animals to the",
    "high ground before the bridge was closed.",
    "Nobody was hurt, and the council thanked",
    "the volunteers who worked until dawn.",
)
RIGHT_COLUMN = (
    "Repairs to the bridge will begin in spring",
    "once the engineers have finished their",
    "survey. The road to the village remains",
    "open, although drivers are asked to use",
    "the eastern route while the work is done.",
    "A public meeting is planned for March.",
)


def two_columns(path: Path) -> Path:
    build = _Builder()
    build.page(
        _stream([
            (72, 730, "Flood Report"),
            *_block(50, 700, LEFT_COLUMN),
            *_block(320, 700, RIGHT_COLUMN),
        ])
    )
    return build.save(path)


def numbered_list(path: Path) -> Path:
    build = _Builder()
    build.page(
        _stream(
            _block(
                72,
                720,
                (
                    "Before the meeting every member should read the following papers",
                    "1. The minutes of the previous meeting, including the long appendix",
                    "on the budget and the notes from the visiting auditor.",
                    "2. The treasurer's report for the third quarter of the year.",
                    "3. The proposal to extend the opening hours of the reading room.",
                    "- Bring a copy of the agenda.",
                    "- Arrive by ten o'clock.",
                ),
            )
        )
    )
    return build.save(path)


def letter_spaced(path: Path) -> Path:
    """A spaced display title, then a paragraph drawn with wide character spacing.

    pdfplumber reads the wide-spaced paragraph one letter at a time ("H e l l o
    w o r l d"), because the gaps between its letters are wider than its word
    tolerance; pypdf reads the same strings whole. A reader that kept the first
    non-empty answer kept the letters.
    """
    build = _Builder()
    title = _stream([(72, 720, "C H A P T E R   O N E")], size=16)
    spaced = _stream(
        _block(72, 680, ("Wide letters are hard to read", "when every one stands alone")),
        spacing=6.0,
    )
    build.page(title + "\n" + spaced)
    return build.save(path)


TABLE_ROWS = (
    ("Northern regional distribution centre and warehouse", "1,250", "18.75", "23,437.50"),
    ("Southern regional distribution centre and warehouse", "980", "18.75", "18,375.00"),
)


def table_rows(path: Path) -> Path:
    build = _Builder()
    lines: list[_Line] = [(72, 730, "Quarterly stock")]
    for index, row in enumerate(TABLE_ROWS):
        y = 700 - index * 16
        for x, cell in zip((40, 330, 400, 470), row, strict=True):
            lines.append((x, y, cell))
    build.page(_stream(lines, size=10))
    return build.save(path)


def damaged_encoding(path: Path) -> Path:
    build = _Builder()
    broken = build.font_with_unicode_map({code: 0xFFFD for code in range(0x21, 0x7F)})
    private = build.font_with_unicode_map({ord("x"): 0xE123})
    build.page(_stream(_block(72, 720, PROSE[:2])), font=broken)
    build.page(_stream([(72, 720, "The next box holds a sign that has no letter.")]), font=private)
    build.page(_stream(_block(72, 720, PROSE[2:])))
    return build.save(path)


def nested_outline(path: Path) -> Path:
    build = _Builder()
    build.page(
        _stream([
            (72, 720, "Part One"),
            *_block(72, 690, PROSE),
            (72, 600, "Chapter 1"),
            *_block(72, 570, PROSE[:2]),
        ])
    )
    build.page(_stream([*_block(72, 720, PROSE), (72, 640, "Summary"), (72, 620, "Short.")]))
    build.page(
        _stream([
            *_block(72, 720, PROSE[:2]),
            (72, 680, "Chapter 2"),
            *_block(72, 650, PROSE),
            (72, 580, "Summary"),
            (72, 560, "Shorter."),
        ])
    )
    writer = build.writer
    part = writer.add_outline_item("Part One", 0)
    chapter_1 = writer.add_outline_item("Chapter 1", 0, parent=part)
    writer.add_outline_item("Summary", 1, parent=chapter_1)
    writer.add_outline_item("Not on the page", 1, parent=chapter_1)
    chapter_2 = writer.add_outline_item("Chapter 2", 2, parent=part)
    writer.add_outline_item("Summary", 2, parent=chapter_2)
    return build.save(path)


def blank_edges(path: Path) -> Path:
    build = _Builder()
    build.page("")
    build.page(_stream(_block(72, 720, PROSE)))
    build.page("")
    return build.save(path)


def mixed_scan(path: Path) -> Path:
    build = _Builder()
    build.page(_stream(_block(72, 720, PROSE[:2])))
    build.page("q 300 0 0 300 150 250 cm /Im1 Do Q", image=True)
    build.page(_stream(_block(72, 720, PROSE[2:])))
    return build.save(path)


def encrypted(path: Path) -> Path:
    build = _Builder()
    build.page(_stream([(72, 720, "Private minutes"), *_block(72, 690, PROSE)]))
    build.page(_stream(_block(72, 720, PROSE[:2])))
    build.writer.add_outline_item("Private minutes", 0)
    build.writer.encrypt(FIXTURE_PASSWORD, algorithm="AES-128")
    return build.save(path)


CORPUS = {
    "clean_prose.pdf": clean_prose,
    "two_columns.pdf": two_columns,
    "numbered_list.pdf": numbered_list,
    "letter_spaced.pdf": letter_spaced,
    "table_rows.pdf": table_rows,
    "damaged_encoding.pdf": damaged_encoding,
    "nested_outline.pdf": nested_outline,
    "blank_edges.pdf": blank_edges,
    "mixed_scan.pdf": mixed_scan,
    "encrypted.pdf": encrypted,
}


def build_long(path: Path, pages: int, *, spaced: bool = False) -> Path:
    """A long document for the latency budget: *pages* pages of the minutes.

    ``spaced`` draws every page with wide character spacing, so every page is
    questionable and pays for every extractor: the worst case.
    """
    build = _Builder()
    for number in range(1, pages + 1):
        lines = [(72, 740, f"Page {number}"), *_block(72, 710, PROSE * 6)]
        build.page(_stream(lines, spacing=6.0 if spaced else 0.0))
    return build.save(path)


def main(argv: Sequence[str] = ()) -> int:
    target = Path(argv[0]) if argv else HERE
    target.mkdir(parents=True, exist_ok=True)
    for name, make in CORPUS.items():
        made = make(target / name)
        print(f"{made.name}: {made.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = ["CORPUS", "FIXTURE_PASSWORD", "build_long", "main"]
