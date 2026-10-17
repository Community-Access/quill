"""QUILL's own Office readers first; MarkItDown only when they fail (2026-10-16).

Measured that evening (``docs/design/2026-10-16-editor-completion-measurements.md``):
opening a .docx from source cost 12 to 17 seconds on a cold start, nearly all
of it importing MarkItDown. QUILL's own readers keep the same structure (and
on the committed corpus, more of it), so they now go first everywhere, and
``markitdown`` is imported only on the fallback.

The import check runs in a fresh interpreter, because this test process has
very likely imported markitdown already for some other test.
"""

from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

from quill.io.docconvert import TIER_MARKITDOWN, TIER_OWN_READER, _Deps, convert_document
from quill.io.office_text import (
    ENGINE_MARKITDOWN,
    OfficeReadError,
    read_office_text_preferring_own,
)
from quill.io.office_word import number_ordered_items, read_docx_xml

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tests" / "corpus" / "office"

_OPEN_IN_A_FRESH_PROCESS = r"""
import json, sys
from pathlib import Path
from quill.io.open_read import read_open_document
from quill.core.lite.open_prepare import prepare
results = {}
for name in sys.argv[1:]:
    path = Path(name)
    document, _ = read_open_document(path, path.suffix.lower())
    prepare(path, "plain")
    results[path.name] = str(document.source_metadata.get("engine", ""))
print(json.dumps({"engines": results, "markitdown": "markitdown" in sys.modules,
                  "magika": "magika" in sys.modules}))
"""


def _never_markitdown(path: Path) -> str:
    raise AssertionError(f"MarkItDown was asked to read {path.name}")


# ------------------------------------------------------- the import itself


def test_opening_office_files_never_imports_markitdown() -> None:
    """File > Open (QUILL) and open_prepare (QUILL Lite), in a clean interpreter."""
    files = [CORPUS / name for name in ("report.docx", "budget.xlsx", "deck.pptx", "minutes.odt")]
    proc = subprocess.run(
        [sys.executable, "-c", _OPEN_IN_A_FRESH_PROCESS, *map(str, files)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    found = json.loads(proc.stdout.strip().splitlines()[-1])
    assert found["markitdown"] is False
    assert found["magika"] is False
    assert found["engines"]["report.docx"] in {"python-docx", "word-xml"}
    assert found["engines"]["budget.xlsx"] in {"openpyxl", "sheet-xml"}
    assert found["engines"]["deck.pptx"] == "slide-xml"


# ------------------------------------------------------------ every entry


@pytest.mark.parametrize("name", ["report.docx", "budget.xlsx", "deck.pptx", "scores.ods"])
def test_own_reader_answers_without_asking_markitdown(name: str) -> None:
    found = read_office_text_preferring_own(CORPUS / name, markitdown=_never_markitdown)
    assert found.engine != ENGINE_MARKITDOWN
    assert found.reader_label.startswith("QUILL's own")
    assert found.own_reader_failure == ""


def test_import_convert_reads_word_with_quill_first() -> None:
    outcome = convert_document(CORPUS / "report.docx", deps=_Deps(markitdown=_never_markitdown))
    assert outcome.tier == TIER_OWN_READER
    assert outcome.reader == "QUILL's own Word reader"


def test_file_open_classic_path_reads_word_with_quill_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.io.structured as structured

    monkeypatch.setattr(structured, "convert_with_markitdown", _never_markitdown)
    document = structured.read_structured_document(CORPUS / "report.docx")
    assert document.source_metadata["reader"] == "QUILL's own Word reader"


def test_markitdown_first_setting_is_still_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Word reading engine = "MarkItDown first" keeps the old order for Word."""
    import quill.io.structured as structured

    asked: list[str] = []

    def _stand_in(path: Path) -> str:
        asked.append(path.name)
        return "# From MarkItDown\n"

    monkeypatch.setattr(structured, "convert_with_markitdown", _stand_in)
    document = structured.read_structured_document(CORPUS / "report.docx", docx_engine="markitdown")
    assert asked == ["report.docx"]
    assert document.source_metadata["engine"] == "markitdown"
    # ...and only for Word: a workbook still reads with QUILL's own reader.
    sheet = structured.read_structured_document(CORPUS / "budget.xlsx", docx_engine="markitdown")
    assert asked == ["report.docx"]
    assert sheet.source_metadata["reader"] == "QUILL's own Excel reader"


def test_lite_open_prepare_reads_word_with_quill_first(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.io.office_text as office_text
    from quill.core.lite.open_prepare import read_office_for_open

    monkeypatch.setattr(office_text, "_default_markitdown", _never_markitdown)
    assert read_office_for_open(CORPUS / "report.docx").startswith("# Quarterly Report")


def test_web_pages_still_try_markitdown_first() -> None:
    outcome = convert_document(
        Path("page.html"), deps=_Deps(markitdown=lambda path: "# From MarkItDown\n")
    )
    assert outcome.tier == TIER_MARKITDOWN


# --------------------------------------------------------------- fallback


def _write_textless_docx(path: Path) -> Path:
    body = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p/></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", body)
    return path


def test_markitdown_stands_in_when_quill_finds_nothing(tmp_path: Path) -> None:
    path = _write_textless_docx(tmp_path / "empty.docx")
    found = read_office_text_preferring_own(path, markitdown=lambda p: "Text MarkItDown found\n")
    assert found.engine == ENGINE_MARKITDOWN
    assert found.reader_label == "MarkItDown"
    assert "no text in it" in found.own_reader_failure
    assert found.metadata()["own_reader_failure"] == found.own_reader_failure


def test_when_both_fail_the_person_hears_quills_sentence(tmp_path: Path) -> None:
    path = _write_textless_docx(tmp_path / "empty.docx")

    def _fails(p: Path) -> str:
        raise ImportError("markitdown not available")

    with pytest.raises(OfficeReadError) as caught:
        read_office_text_preferring_own(path, markitdown=_fails)
    assert "no text in it to read" in caught.value.sentence
    assert "markitdown" not in caught.value.sentence.lower()


def test_a_locked_file_is_never_offered_to_markitdown() -> None:
    with pytest.raises(OfficeReadError) as caught:
        read_office_text_preferring_own(CORPUS / "locked.docx", markitdown=_never_markitdown)
    assert "password-protected" in caught.value.sentence


def test_intake_report_says_why_quills_reader_stood_aside(tmp_path: Path) -> None:
    from quill.core.document import Document
    from quill.core.intake import build_intake_report

    path = _write_textless_docx(tmp_path / "empty.docx")
    found = read_office_text_preferring_own(path, markitdown=lambda p: "Found\n")
    report = build_intake_report(
        Document(text=found.text, path=path, source_metadata=found.metadata())
    )
    assert "Read by: MarkItDown" in report
    assert "QUILL's own reader: not used." in report


# ----------------------------------------------- the gaps the comparison found


def test_numbered_items_count_per_run_and_level() -> None:
    lines = [
        "1. one",
        "1. two",
        "   1. nested one",
        "   1. nested two",
        "1. three\\",
        "continued",
        "1. four",
        "- a bullet",
        "1. restart",
        "",
        "1. new list",
    ]
    assert number_ordered_items(lines) == [
        "1. one",
        "2. two",
        "   1. nested one",
        "   2. nested two",
        "3. three\\",
        "continued",
        "4. four",
        "- a bullet",
        "1. restart",
        "",
        "1. new list",
    ]


_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _math_docx(path: Path, math: str) -> Path:
    """A real Word package (python-docx) whose one paragraph ends in *math*."""
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Formula: MATH_GOES_HERE")
    document.save(str(path))
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    # Declare the math prefix on the equation itself, whatever the root declares.
    tag = "<m:oMathPara" if math.startswith("<m:oMathPara") else "<m:oMath"
    math = math.replace(tag, f'{tag} xmlns:m="{_M}"', 1)
    xml = re.sub(
        r"Formula: MATH_GOES_HERE(</w:t></w:r>)", r"Formula: \1" + math.replace("\\", "\\\\"), xml
    )
    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return path


def _r(text: str) -> str:
    return f"<m:r><m:t>{text}</m:t></m:r>"


@pytest.mark.parametrize(
    ("math", "expected"),
    [
        (
            f"<m:oMath><m:sSup><m:e>{_r('a')}</m:e><m:sup>{_r('2')}</m:sup></m:sSup>"
            f"{_r('+')}<m:sSup><m:e>{_r('b')}</m:e><m:sup>{_r('2')}</m:sup></m:sSup></m:oMath>",
            "\\(a^{2}+b^{2}\\)",
        ),
        (
            f"<m:oMath><m:f><m:num>{_r('1')}</m:num><m:den>{_r('2')}</m:den></m:f></m:oMath>",
            "\\(\\frac{1}{2}\\)",
        ),
        (
            f"<m:oMath><m:rad><m:deg/><m:e>{_r('x')}</m:e></m:rad></m:oMath>",
            "\\(\\sqrt{x}\\)",
        ),
        (
            '<m:oMath><m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr>'
            f"<m:sub>{_r('i=1')}</m:sub><m:sup>{_r('n')}</m:sup><m:e>{_r('i')}</m:e>"
            "</m:nary></m:oMath>",
            "\\(\\sum_{i=1}^{n} i\\)",
        ),
        (
            f"<m:oMath><m:d><m:e>{_r('x+1')}</m:e></m:d></m:oMath>",
            "\\((x+1)\\)",
        ),
        (
            f"<m:oMathPara><m:oMath><m:func><m:fName>{_r('sin')}</m:fName>"
            f"<m:e>{_r('x')}</m:e></m:func></m:oMath></m:oMathPara>",
            "$$\\sin x$$",
        ),
    ],
    ids=["superscripts", "fraction", "root", "sum", "brackets", "display-function"],
)
@pytest.mark.parametrize("blocked", [False, True], ids=["python-docx", "word-xml"])
def test_word_equations_are_kept_as_latex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, math: str, expected: str, blocked: bool
) -> None:
    """MarkItDown kept equations and QUILL's reader dropped them; now both keep them."""
    from quill.io.office_text import read_office_text

    path = _math_docx(tmp_path / "math.docx", math)
    if blocked:
        monkeypatch.setitem(sys.modules, "docx", None)
    found = read_office_text(path)
    assert found.engine == ("word-xml" if blocked else "python-docx")
    assert found.text == f"Formula: {expected}\n"


def test_xml_reader_and_python_docx_agree_on_pictures(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    from quill.io.docx_text import read_docx_text

    def _chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    image = tmp_path / "dot.png"
    image.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        + _chunk(b"IEND", b"")
    )
    document = docx.Document()
    document.add_paragraph("Before the picture.")
    document.add_picture(str(image))
    path = tmp_path / "picture.docx"
    document.save(str(path))
    # python-docx writes no description; give the picture one, as Word's
    # Alt Text pane does.
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    xml = re.sub(r'\sdescr="[^"]*"', "", parts["word/document.xml"].decode("utf-8"))
    xml = re.sub(r"(<wp:docPr\b)", r'\1 descr="A red dot"', xml, count=1)
    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)

    assert "[Image: A red dot]" in (read_docx_text(path) or "")
    assert "[Image: A red dot]" in read_docx_xml(path)
