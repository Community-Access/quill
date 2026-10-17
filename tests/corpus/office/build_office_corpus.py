"""Build the small Office corpus QUILL's own Office readers are tested on.

Run from the repository root::

    python tests/corpus/office/build_office_corpus.py

The Word, Excel and PowerPoint files are written by the libraries Office
users' files most often resemble (python-docx, openpyxl, python-pptx); the
OpenDocument files are written by hand, as a zip of ``content.xml``, because
no ODF writer is installed in the development venv. Each file is a few
kilobytes and its text is known exactly. The expectations live in the tests
(``tests/unit/io/test_office_corpus.py``); this script only makes the files.

``locked.docx`` and ``legacy.doc`` are not real documents: they start with the
eight bytes of an OLE compound file, which is what a password-protected
modern file and a Word 97-2003 file both are on disk. That is all the readers
look at before refusing them.
"""

from __future__ import annotations

import datetime as dt
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
_FIXED = dt.datetime(2026, 10, 16, 12, 0, 0)
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def build_docx(target: Path) -> None:
    import docx

    document = docx.Document()
    document.core_properties.created = _FIXED
    document.core_properties.modified = _FIXED
    document.add_paragraph("Quarterly Report", style="Title")
    document.add_heading("Summary", level=1)
    document.add_paragraph("Sales rose in every region this quarter.")
    paragraph = document.add_paragraph("First line of the address")
    paragraph.add_run().add_break()
    paragraph.add_run("Second line of the address")
    document.add_heading("Highlights", level=2)
    document.add_paragraph("North grew fastest", style="List Bullet")
    document.add_paragraph("South held steady", style="List Bullet")
    document.add_paragraph("Hire two editors", style="List Number")
    document.add_paragraph("Open the Leeds office", style="List Number")
    table = document.add_table(rows=3, cols=2)
    for row, (region, total) in enumerate([
        ("Region", "Total"),
        ("North", "1,200"),
        ("South | West", "950"),
    ]):
        table.cell(row, 0).text = region
        table.cell(row, 1).text = total
    document.add_paragraph("End of report.")
    document.save(str(target))


def build_xlsx(target: Path) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.properties.created = _FIXED
    workbook.properties.modified = _FIXED
    budget = workbook.active
    budget.title = "Budget"
    budget.append(["Item", "Amount", "Paid"])
    budget.append(["Rent", 950, True])
    budget.append(["Snacks", 12.5, False])
    budget.append(["Due", dt.date(2026, 11, 1), None])
    notes = workbook.create_sheet("Notes")
    notes.append(["Note"])
    notes.append(["Pay rent | early"])
    workbook.save(str(target))


def build_pptx(target: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    deck = Presentation()
    deck.core_properties.created = _FIXED
    deck.core_properties.modified = _FIXED
    title_layout, content_layout, title_only = (
        deck.slide_layouts[0],
        deck.slide_layouts[1],
        deck.slide_layouts[5],
    )

    opening = deck.slides.add_slide(title_layout)
    opening.shapes.title.text = "Welcome"
    opening.placeholders[1].text = "A short talk"

    agenda = deck.slides.add_slide(content_layout)
    agenda.shapes.title.text = "Agenda"
    body = agenda.placeholders[1].text_frame
    body.text = "Results"
    nested = body.add_paragraph()
    nested.text = "By region"
    nested.level = 1
    body.add_paragraph().text = "Questions"
    agenda.notes_slide.notes_text_frame.text = "Keep this under five minutes."

    figures = deck.slides.add_slide(title_only)
    figures.shapes.title.text = "Figures"
    shape = figures.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(6), Inches(1.5))
    for row, cells in enumerate([("Region", "Total"), ("North", "1,200")]):
        for column, text in enumerate(cells):
            shape.table.cell(row, column).text = text

    # Show "Figures" second although it was made third: the reader must follow
    # the presentation's slide list, not the slide files' numbers.
    slide_list = deck.slides._sldIdLst
    entries = list(slide_list)
    slide_list.remove(entries[2])
    slide_list.insert(1, entries[2])
    deck.save(str(target))


_ODF_NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
    'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"'
)


def _write_odf(target: Path, mimetype: str, body: str) -> None:
    content = (
        f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {_ODF_NS} '
        f'office:version="1.3"><office:body>{body}</office:body></office:document-content>'
    )
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
        'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.3"><manifest:file-entry manifest:full-path="/" '
        f'manifest:media-type="{mimetype}"/><manifest:file-entry '
        'manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        "</manifest:manifest>"
    )
    stamp = _FIXED.timetuple()[:6]
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype", stamp), mimetype)
        for name, data in (("content.xml", content), ("META-INF/manifest.xml", manifest)):
            info = zipfile.ZipInfo(name, stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)


def build_odt(target: Path) -> None:
    _write_odf(
        target,
        "application/vnd.oasis.opendocument.text",
        "<office:text>"
        '<text:h text:outline-level="1">Minutes</text:h>'
        "<text:p>Present:<text:s/>everyone.</text:p>"
        '<text:h text:outline-level="2">Actions</text:h>'
        "<text:list><text:list-item><text:p>Book the hall</text:p>"
        "<text:list><text:list-item><text:p>Ask about ramps</text:p></text:list-item>"
        "</text:list></text:list-item>"
        "<text:list-item><text:p>Send the agenda</text:p></text:list-item></text:list>"
        "<table:table><table:table-row><table:table-cell><text:p>Who</text:p>"
        "</table:table-cell><table:table-cell><text:p>When</text:p></table:table-cell>"
        "</table:table-row><table:table-row><table:table-cell><text:p>Sam</text:p>"
        "</table:table-cell><table:table-cell><text:p>Friday</text:p></table:table-cell>"
        "</table:table-row></table:table>"
        "<text:p>Line one<text:line-break/>Line two</text:p>"
        "</office:text>",
    )


def build_ods(target: Path) -> None:
    _write_odf(
        target,
        "application/vnd.oasis.opendocument.spreadsheet",
        "<office:spreadsheet>"
        '<table:table table:name="Scores">'
        "<table:table-row><table:table-cell><text:p>Name</text:p></table:table-cell>"
        "<table:table-cell><text:p>Score</text:p></table:table-cell>"
        '<table:table-cell table:number-columns-repeated="16380"/></table:table-row>'
        "<table:table-row><table:table-cell><text:p>Ada</text:p></table:table-cell>"
        "<table:table-cell><text:p>91</text:p></table:table-cell></table:table-row>"
        '<table:table-row table:number-rows-repeated="1048570"><table:table-cell/>'
        "</table:table-row>"
        "</table:table>"
        '<table:table table:name="Empty"/>'
        "</office:spreadsheet>",
    )


def build_odp(target: Path) -> None:
    _write_odf(
        target,
        "application/vnd.oasis.opendocument.presentation",
        "<office:presentation>"
        '<draw:page draw:name="page1">'
        '<draw:frame presentation:class="title"><draw:text-box><text:p>Hello'
        "</text:p></draw:text-box></draw:frame>"
        '<draw:frame presentation:class="outline"><draw:text-box><text:p>First point'
        "</text:p><text:p>Second point</text:p></draw:text-box></draw:frame>"
        "<presentation:notes><draw:frame><draw:text-box><text:p>Smile.</text:p>"
        "</draw:text-box></draw:frame></presentation:notes>"
        "</draw:page>"
        '<draw:page draw:name="page2"><draw:frame presentation:class="outline">'
        "<draw:text-box><text:p>No title here</text:p></draw:text-box></draw:frame>"
        "</draw:page>"
        "</office:presentation>",
    )


def build_ole(target: Path) -> None:
    target.write_bytes(_OLE_MAGIC + bytes(504))


def main() -> int:
    builders = {
        "report.docx": build_docx,
        "budget.xlsx": build_xlsx,
        "deck.pptx": build_pptx,
        "minutes.odt": build_odt,
        "scores.ods": build_ods,
        "talk.odp": build_odp,
        "locked.docx": build_ole,
        "legacy.doc": build_ole,
    }
    for name, build in builders.items():
        build(HERE / name)
        print(f"wrote {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
