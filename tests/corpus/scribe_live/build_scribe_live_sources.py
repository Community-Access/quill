"""Make the test documents the Scribe live regression run sends.

Run from the repository root::

    python tests/corpus/scribe_live/build_scribe_live_sources.py

Everything here is ours: the text is written for these files (the Riverbend
Community Tool Library is invented, and so is every name and number in it),
the pictures are drawn by this script, and the files are dedicated to the
public domain (CC0 1.0). Nothing comes from Pneuma's corpus or from Scribe.

Most files are written with the libraries the development venv has
(python-docx, openpyxl, python-pptx, Pillow, PyMuPDF) or by hand (RTF, EPUB,
MOBI, DCX, DjVu). The legacy and OpenDocument Office files (DOC, ODT, XLS,
ODS, PPT, ODP) are saved by Microsoft Office from our own DOCX, XLSX and PPTX
over COM; on a computer without Office those are skipped and named. The
expected outcome and page count of each file live in
``quill/tools/scribe_live/sources.py``; this script only makes the files.
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from quill.tools.scribe_live.sources import LOCKED_PDF_TEST_PASSWORD  # noqa: E402

sys.path.insert(0, str(HERE))
from scribe_live_handmade import (  # noqa: E402
    BULLETS,
    CHART_ALT,
    LINK,
    SECTIONS,
    SPANISH,
    STEPS,
    TABLE,
    TITLE,
    _dcx,
    _djvu,
    build_epub,
    build_mobi,
    chart_png,
    page_image,
)

#: The only name any test document carries in its metadata: never the name of
#: whoever ran this script, their Windows account or their computer (the files
#: are public). ``tests/unit/tools/test_scribe_live_sources_privacy.py`` checks.
AUTHOR = "QUILL test documents"


def _neutral_core(props: object) -> None:
    """python-docx and python-pptx core properties: ours, not the library's
    template author ("python-docx", "Steve Canny")."""
    for name in ("author", "last_modified_by"):
        setattr(props, name, AUTHOR)
    props.comments = ""  # type: ignore[attr-defined]


def _office_neutral(document: object) -> None:
    """Office over COM: neutral author fields, and Office's own Remove Personal
    Information on save, so the saving user's name is never written."""
    props = document.BuiltInDocumentProperties  # type: ignore[attr-defined]
    for name in ("Author", "Last Author", "Company", "Manager"):
        try:
            props(name).Value = AUTHOR
        except Exception:  # noqa: BLE001 - a format without that property
            pass
    try:
        document.RemovePersonalInformation = True  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - not every program has it
        pass


_ODF_PERSONAL = re.compile(
    r"<(dc:creator|meta:initial-creator)>[^<]*</\1>|<meta:user-defined[^>]*/>"
)


def _odf_neutral(path: Path) -> None:
    """An OpenDocument file's meta.xml: the creators set to ours."""
    with zipfile.ZipFile(path) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    with zipfile.ZipFile(path, "w") as target:
        for info, data in entries:
            if info.filename == "meta.xml":
                text = data.decode("utf-8")
                text = _ODF_PERSONAL.sub(
                    lambda m: f"<{m.group(1)}>{AUTHOR}</{m.group(1)}>" if m.group(1) else "",
                    text,
                )
                data = text.encode("utf-8")
            kind = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            target.writestr(info, data, compress_type=kind)


def _set_alt(picture_run: object, title: str, description: str) -> None:
    doc_pr = picture_run._r.xpath(".//wp:docPr")[0]  # type: ignore[attr-defined]
    if description:
        doc_pr.set("descr", description)
        doc_pr.set("title", title)
    else:
        for name in ("descr", "title"):
            doc_pr.attrib.pop(name, None)


def _hyperlink(paragraph: object, text: str, url: str) -> None:
    from docx.opc.constants import RELATIONSHIP_TYPE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    part = paragraph.part  # type: ignore[attr-defined]
    rel = part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rel)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "Hyperlink")
    props.append(style)
    run.append(props)
    node = OxmlElement("w:t")
    node.text = text
    run.append(node)
    link.append(run)
    paragraph._p.append(link)  # type: ignore[attr-defined]


def _header_row(table: object) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    row = table.rows[0]._tr  # type: ignore[attr-defined]
    props = row.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    props.append(header)


def _language(document: object, tag: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    document.core_properties.language = tag  # type: ignore[attr-defined]
    _neutral_core(document.core_properties)  # type: ignore[attr-defined]
    styles = document.styles.element  # type: ignore[attr-defined]
    defaults = styles.find(qn("w:docDefaults"))
    rpr = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:val"), tag)


def build_structured_docx(target: Path) -> None:
    import docx
    from docx.shared import Inches

    document = docx.Document()
    document.core_properties.title = TITLE
    _language(document, "en-US")
    document.add_heading(TITLE, level=1)
    for heading, paragraphs in SECTIONS:
        document.add_heading(heading, level=2)
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
    document.add_heading("How it works", level=2)
    for step in STEPS:
        document.add_paragraph(step, style="List Number")
    for item in BULLETS:
        document.add_paragraph(item, style="List Bullet")
    document.add_paragraph("Power tools", style="List Bullet 2")
    table = document.add_table(rows=len(TABLE), cols=3)
    table.style = "Table Grid"
    for r, row in enumerate(TABLE):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    _header_row(table)
    document.add_heading("Loans this year", level=2)
    run = document.add_paragraph().add_run()
    run.add_picture(io.BytesIO(chart_png()), width=Inches(4))
    _set_alt(run, "Loans chart", CHART_ALT)
    document.add_paragraph("Figure 1. Loans per month.", style="Caption")
    run = document.add_paragraph().add_run()
    run.add_picture(io.BytesIO(chart_png()), width=Inches(3))
    _set_alt(run, "", "")  # a picture with no alt text at all
    paragraph = document.add_paragraph("To help at the desk, see ")
    _hyperlink(paragraph, *LINK)
    document.save(str(target))


def build_tables_docx(target: Path) -> None:
    import docx

    document = docx.Document()
    _language(document, "en-US")
    document.add_heading("Tool library tables", level=1)
    document.add_heading("Loans by branch and season", level=2)
    table = document.add_table(rows=5, cols=4)
    table.style = "Table Grid"
    table.cell(0, 0).merge(table.cell(1, 0)).text = "Branch"
    table.cell(0, 1).merge(table.cell(0, 3)).text = "Loans"
    for c, season in enumerate(("Spring", "Summer", "Autumn"), 1):
        table.cell(1, c).text = season
    for r, (branch, *values) in enumerate(
        (("North", "120", "180", "90"), ("South", "75", "110", "60"), ("River", "40", "65", "30")),
        2,
    ):
        table.cell(r, 0).text = branch
        for c, value in enumerate(values, 1):
            table.cell(r, c).text = value
    _header_row(table)
    document.add_heading("A table with no header row", level=2)
    plain = document.add_table(rows=2, cols=2)
    plain.style = "Table Grid"
    for r, row in enumerate((("Keys", "At the desk"), ("First aid kit", "By the door"))):
        for c, value in enumerate(row):
            plain.cell(r, c).text = value
    document.add_page_break()
    document.add_heading("Volunteers by day", level=2)
    week = document.add_table(rows=4, cols=3)
    week.style = "Table Grid"
    for r, row in enumerate(
        (("Day", "Morning", "Evening"), ("Tuesday", "-", "Ana, Femi")),
    ):
        for c, value in enumerate(row):
            week.cell(r, c).text = value
    week.cell(2, 0).text = "Thursday"
    week.cell(2, 1).merge(week.cell(3, 1)).text = "Closed"
    week.cell(2, 2).text = "Lee"
    week.cell(3, 0).text = "Saturday"
    week.cell(3, 2).text = "Ana, Lee, Sam"
    _header_row(week)
    document.save(str(target))


def build_spanish_docx(target: Path) -> None:
    import docx

    document = docx.Document()
    document.core_properties.title = SPANISH[0][0]
    _language(document, "es-ES")
    for text, level in SPANISH:
        if level:
            document.add_heading(text, level=level)
        else:
            document.add_paragraph(text)
    document.save(str(target))


_OMML = (
    '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
    "<m:oMath><m:r><m:t>x=</m:t></m:r><m:f><m:num><m:r><m:t>-b±</m:t></m:r><m:rad>"
    '<m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e><m:sSup><m:e><m:r><m:t>b</m:t>'
    "</m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup><m:r><m:t>-4ac</m:t></m:r>"
    "</m:e></m:rad></m:num><m:den><m:r><m:t>2a</m:t></m:r></m:den></m:f></m:oMath></m:oMathPara>"
)


def build_math_docx(target: Path) -> None:
    import docx
    from docx.oxml import parse_xml

    document = docx.Document()
    _language(document, "en-US")
    document.add_heading("Sharing the tile saw fairly", level=1)
    document.add_paragraph(
        "Each household's turn comes round once every n days, where n is the number of "
        "households waiting. The quadratic formula below sets the loan length:"
    )
    paragraph = document.add_paragraph()
    paragraph._p.append(parse_xml(_OMML))
    document.add_paragraph("With a = 1, b = -7 and c = 12, the two answers are 3 and 4 days.")
    document.save(str(target))


def _story_pdf(target: Path, html: str, *, title: str, password: str = "") -> None:
    import pymupdf

    story = pymupdf.Story(html=html)
    writer_buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(writer_buffer)
    rect = pymupdf.paper_rect("letter")
    where = rect + (54, 54, -54, -54)
    more = True
    while more:
        device = writer.begin_page(rect)
        more, _filled = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()
    document = pymupdf.open("pdf", writer_buffer.getvalue())
    document.set_metadata({"title": title, "author": AUTHOR, "creator": AUTHOR, "producer": AUTHOR})
    options: dict[str, object] = {"garbage": 3, "deflate": True}
    if password:
        options.update(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password + "-owner"
        )
    document.save(str(target), **options)


def _structured_html(long: bool = False) -> str:
    parts = [f"<h1>{TITLE}</h1>"]
    for heading, paragraphs in SECTIONS:
        parts.append(f"<h2>{heading}</h2>")
        parts += [f"<p>{p}</p>" for p in paragraphs]
    parts.append("<ol>" + "".join(f"<li>{s}</li>" for s in STEPS) + "</ol>")
    parts.append("<ul>" + "".join(f"<li>{b}</li>" for b in BULLETS) + "</ul>")
    rows = "".join(
        "<tr>" + "".join(f"<{'th' if r == 0 else 'td'}>{v}</{'th' if r == 0 else 'td'}>"
                         for v in row) + "</tr>"
        for r, row in enumerate(TABLE)
    )  # fmt: skip
    parts.append(f"<table border='1'>{rows}</table>")
    if long:
        for number in range(1, 61):
            parts.append(f"<h2>Part {number}: the {_ORDINALS[number % 10]} shelf</h2>")
            parts += [
                f"<p>Shelf {number} holds tools numbered {number * 10} to {number * 10 + 9}. "
                + " ".join(p for _h, ps in SECTIONS for p in ps)
                + "</p>"
            ] * 2
    return "<body>" + "".join(parts) + "</body>"


_ORDINALS = ("tenth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
             "eighth", "ninth")  # fmt: skip


def build_pdfs(folder: Path) -> None:
    _story_pdf(folder / "q02-structured.pdf", _structured_html(), title=TITLE)
    _story_pdf(folder / "q24-long-report.pdf", _structured_html(long=True), title=TITLE)
    _story_pdf(
        folder / "q28-locked.pdf",
        _structured_html(),
        title=TITLE,
        password=LOCKED_PDF_TEST_PASSWORD,
    )


def build_images(folder: Path) -> None:
    page = page_image()
    second = page_image(["This is the second page of the scan."])
    page.convert("RGB").save(folder / "q03-page.jpg", quality=80)
    page.save(folder / "q04-page.gif")
    page.save(folder / "q05-page.png")
    page.save(
        folder / "q06-pages.tif", save_all=True, append_images=[second], compression="tiff_lzw"
    )
    page.convert("1").save(folder / "q07-page.bmp")  # one bit a pixel: a fax-like scan
    page.save(folder / "q08-page.pcx")
    (folder / "q09-pages.dcx").write_bytes(_dcx([page, second]))
    page.save(folder / "q10-page.jp2")
    (folder / "q11-page.djvu").write_bytes(_djvu(page))


def build_rtf(target: Path) -> None:
    rows = "".join(
        "\\trowd\\trhdr" * (r == 0) + ("\\trowd" if r else "")
        + "\\cellx3000\\cellx6000\\cellx9000"
        + "".join(f"\\pard\\intbl {v}\\cell" for v in row) + "\\row"
        for r, row in enumerate(TABLE)
    )  # fmt: skip
    body = [
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}",
        "{\\stylesheet{\\s1 heading 1;}{\\s2 heading 2;}}",
        f"\\pard\\s1\\b\\fs36 {TITLE}\\b0\\fs24\\par",
    ]
    for heading, paragraphs in SECTIONS:
        body.append(f"\\pard\\s2\\b\\fs28 {heading}\\b0\\fs24\\par")
        body += [f"\\pard {p}\\par" for p in paragraphs]
    body += [f"\\pard\\fi-360\\li720 {n}.\\tab {s}\\par" for n, s in enumerate(STEPS, 1)]
    body += [rows, "\\pard\\par}"]
    target.write_text("\n".join(body), encoding="ascii")


def build_txt(target: Path) -> None:
    lines = [TITLE, ""]
    for heading, paragraphs in SECTIONS:
        lines += [heading, ""] + [p + "\n" for p in paragraphs]
    target.write_text("\n".join(lines), encoding="utf-8")


def build_xlsx(target: Path) -> None:
    import openpyxl

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Loans"
    for row in TABLE:
        sheet.append(row)
    budget = book.create_sheet("Budget")
    for row in (("Item", "Cost"), ("New drill bits", 45), ("Ladder repair", 120), ("Total", 165)):
        budget.append(row)
    book.properties.title = "Tool library budget"
    book.properties.creator = AUTHOR
    book.properties.lastModifiedBy = AUTHOR
    book.save(str(target))


def build_pptx(target: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[0])
    slide.shapes.title.text = TITLE
    slide.placeholders[1].text = "A year of lending"
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = "How it works"
    body = slide.placeholders[1].text_frame
    body.text = STEPS[0]
    for step in STEPS[1:]:
        body.add_paragraph().text = step
    slide = deck.slides.add_slide(deck.slide_layouts[5])
    slide.shapes.title.text = "Loans and waiting lists"
    shape = slide.shapes.add_table(len(TABLE), 3, Inches(1), Inches(2), Inches(8), Inches(2))
    for r, row in enumerate(TABLE):
        for c, value in enumerate(row):
            shape.table.cell(r, c).text = value
    picture = slide.shapes.add_picture(io.BytesIO(chart_png()), Inches(6), Inches(4.5), Inches(3))
    picture._element.nvPicPr.cNvPr.set("descr", CHART_ALT)
    _neutral_core(deck.core_properties)
    deck.save(str(target))


def build_refusals(folder: Path) -> None:
    (folder / "q29-web-page.html").write_text(
        f"<!DOCTYPE html><html lang='en'><head><title>{TITLE}</title></head><body>"
        f"<h1>{TITLE}</h1><p>{SECTIONS[0][1][0]}</p></body></html>",
        encoding="utf-8",
    )
    (folder / "q30-not-a-pdf.pdf").write_text(
        "This file is plain text with a .pdf name. Scribe should refuse it.\n", encoding="utf-8"
    )


def build_with_office(folder: Path) -> list[str]:
    """DOC and ODT from q01, XLS and ODS from q17, PPT and ODP from q20, saved by Office."""
    try:
        import win32com.client
    except ImportError:
        return ["q12 .doc", "q14 .odt", "q16 .xls", "q18 .ods", "q19 .ppt", "q21 .odp"]
    skipped: list[str] = []
    opendocuments: list[Path] = []  # rewritten once Office has let go of them
    jobs = (
        ("Word.Application", "q01-structured.docx", (("q12-structured.doc", 0),
                                                     ("q14-structured.odt", 23))),
        ("Excel.Application", "q17-budget.xlsx", (("q16-budget.xls", 56), ("q18-budget.ods", 60))),
        ("PowerPoint.Application", "q20-talk.pptx", (("q19-talk.ppt", 1), ("q21-talk.odp", 35))),
    )  # fmt: skip
    for program, source, targets in jobs:
        try:
            app = win32com.client.DispatchEx(program)
        except Exception:  # noqa: BLE001 - Office is not installed
            skipped += [name for name, _f in targets]
            continue
        try:
            path = str(folder / source)
            if program.startswith("Word"):
                app.Visible = False
                document = app.Documents.Open(path, ReadOnly=True)
            elif program.startswith("Excel"):
                app.DisplayAlerts = False
                document = app.Workbooks.Open(path, ReadOnly=True)
            else:
                document = app.Presentations.Open(path, True, False, False)
            _office_neutral(document)
            for name, file_format in targets:
                out = folder / name
                out.unlink(missing_ok=True)
                if program.startswith("Word"):
                    document.SaveAs2(str(out), FileFormat=file_format)
                elif program.startswith("Excel"):
                    document.SaveAs(str(out), FileFormat=file_format)
                    document.Close(False)
                    document = app.Workbooks.Open(path, ReadOnly=True)
                    _office_neutral(document)
                else:
                    document.SaveAs(str(out), file_format)
                if out.suffix in (".odt", ".ods", ".odp"):
                    opendocuments.append(out)
            document.Close() if not program.startswith("Excel") else document.Close(False)
        finally:
            app.Quit()
    for path in opendocuments:
        _odf_neutral(path)
    return skipped


def main() -> int:
    folder = HERE
    build_structured_docx(folder / "q01-structured.docx")
    build_pdfs(folder)
    build_images(folder)
    build_rtf(folder / "q13-structured.rtf")
    build_txt(folder / "q15-notes.txt")
    build_xlsx(folder / "q17-budget.xlsx")
    build_pptx(folder / "q20-talk.pptx")
    build_epub(folder / "q22-story.epub")
    build_mobi(folder / "q23-story.mobi")
    build_tables_docx(folder / "q25-tables.docx")
    build_spanish_docx(folder / "q26-spanish.docx")
    build_math_docx(folder / "q27-math.docx")
    build_refusals(folder)
    skipped = build_with_office(folder)
    if skipped:
        print("Microsoft Office was not available, so these were not made: " + ", ".join(skipped))
    print(f"Made the Scribe live-run sources in {folder}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
