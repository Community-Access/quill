"""Real RTF tables in the editor, pipe rows where tables are passed on (quill.io.rtf_tables).

The fixtures are what RichEdit 10.0.26100 really writes: the first for a document
with pipe rows (one cell bold), the second for a native table.
"""

from __future__ import annotations

from pathlib import Path

from quill.io import rtf_tables

PIPE_RTF = (
    "{\\rtf1\\ansi\\deff0\\nouicompat{\\fonttbl{\\f0\\fswiss Segoe UI;}}\r\n"
    "{\\*\\generator Riched20 10.0.26100}\\viewkind4\\uc1 \r\n"
    "\\pard\\f0\\fs18\\lang1033 Intro line\\par\r\n"
    "| Name | Role |\\par\r\n"
    "| --- | --- |\\par\r\n"
    "| Ann | \\b Lead\\b0  |\\par\r\n"
    "After\\par\r\n"
    "}\r\n"
)

NATIVE_RTF = (
    "{\\rtf1\\ansi\\deff0\\nouicompat{\\fonttbl{\\f0\\fnil Arial;}}\r\n"
    "\\pard\\f0\\fs24\\lang1033 Before\\par\r\n"
    "\\trowd\\trgaph10\\trpaddl10\\trpaddr10\\trpaddfl3\\trpaddfr3\r\n"
    "\\cellx2000\\cellx4000 \r\n"
    "\\pard\\intbl Name\\cell Role\\cell\\row\\trowd\\trgaph10\\trpaddl10\\trpaddr10\r\n"
    "\\cellx2000\\cellx4000 \r\n"
    "\\pard\\intbl Ann\\cell\\b Lead\\b0\\cell\\row \r\n"
    "\\pard After\\par\r\n"
    "}\r\n"
)


def test_pipe_rows_become_a_real_table_with_its_header_row() -> None:
    out = rtf_tables.pipe_rows_to_rtf_tables(PIPE_RTF)
    assert out.count("\\trowd") == 2  # the separator is not a row
    assert out.count("\\trhdr") == 1
    assert "{Name}\\cell {Role}\\cell \\row" in out
    assert "{\\b Lead\\b0}\\cell" in out  # the formatting crosses with the text
    assert "| --- |" not in out and "| Name |" not in out
    # Everything around the table is untouched, and the next paragraph leaves it.
    assert out.startswith(PIPE_RTF[: PIPE_RTF.index("| Name")])
    assert "\\pard After\\par" in out


def test_a_real_table_becomes_pipe_rows_the_keys_read() -> None:
    out = rtf_tables.rtf_tables_to_pipe_rows(NATIVE_RTF)
    assert "\\pard | {Name} | {Role} |\\par" in out
    assert "\\pard | {Ann} | {\\b Lead\\b0} |\\par" in out
    assert "\\trowd" not in out and "\\cell" not in out
    # Every real table's first row is its header.
    assert out.count("| --- | --- |") == 1


def test_the_header_row_round_trips() -> None:
    back = rtf_tables.rtf_tables_to_pipe_rows(rtf_tables.pipe_rows_to_rtf_tables(PIPE_RTF))
    assert "\\pard | --- | --- |\\par" in back
    assert back.count("\\pard | ") == 3


def test_a_pipe_inside_a_cell_stays_cell_text_both_ways() -> None:
    rtf = "{\\rtf1 \\trowd\\trhdr\\cellx100\\pard\\intbl a|b\\cell\\row \\pard x\\par}"
    piped = rtf_tables.rtf_tables_to_pipe_rows(rtf)
    assert "{a\\\\|b}" in piped  # the editor's escaped pipe
    again = rtf_tables.pipe_rows_to_rtf_tables(piped)
    assert "{a|b}\\cell" in again
    assert again.startswith("{\\rtf1 ")  # a table first in the file keeps the header


def test_a_table_at_the_start_keeps_the_document_header() -> None:
    rtf = "{\\rtf1\\ansi{\\fonttbl{\\f0 Arial;}}\\pard | a | b |\\par | c | d |\\par}"
    out = rtf_tables.pipe_rows_to_rtf_tables(rtf)
    assert out.startswith("{\\rtf1\\ansi{\\fonttbl{\\f0 Arial;}}\\pard ")
    assert out.count("{") == out.count("}")
    assert out.count("\\row") == 2


def test_braces_do_not_pile_up_across_saves_and_opens() -> None:
    text = PIPE_RTF
    for _ in range(3):
        text = rtf_tables.rtf_tables_to_pipe_rows(rtf_tables.pipe_rows_to_rtf_tables(text))
    assert "{{" not in text.split("\\viewkind4", 1)[1]
    assert "\\pard | {Name} | {Role} |\\par" in text


def test_one_pipe_line_is_not_a_table() -> None:
    rtf = "{\\rtf1 \\pard a | b\\par After\\par}"
    assert rtf_tables.pipe_rows_to_rtf_tables(rtf) == rtf


def test_a_file_without_pipes_opens_as_itself(tmp_path: Path) -> None:
    plain = "{\\rtf1 \\pard Hello\\par}"
    target = tmp_path / "a.rtf"
    target.write_bytes(plain.encode("latin-1"))
    rtf_tables.mark_header_rows_in_file(str(target))
    assert target.read_bytes() == plain.encode("latin-1")
    with rtf_tables.pipe_rows_as_tables(str(target)) as readable:
        assert readable == str(target)


def test_pipe_rows_open_as_real_tables_through_a_copy(tmp_path: Path) -> None:
    target = tmp_path / "t.rtf"
    target.write_bytes(PIPE_RTF.encode("latin-1"))
    with rtf_tables.pipe_rows_as_tables(str(target)) as readable:
        assert readable != str(target)
        assert b"\\trowd" in Path(readable).read_bytes()
    assert target.read_bytes() == PIPE_RTF.encode("latin-1")  # never rewritten on open


def test_the_saved_file_gets_its_header_rows_back(tmp_path: Path) -> None:
    target = tmp_path / "n.rtf"
    target.write_bytes(NATIVE_RTF.encode("latin-1"))
    rtf_tables.mark_header_rows_in_file(str(target))
    saved = target.read_bytes().decode("latin-1")
    assert saved.count("\\trhdr") == 1  # the first row only
    assert saved.index("\\trhdr") < saved.index("Name")


def test_two_tables_each_get_a_header_row() -> None:
    one = (
        "\\trowd\\cellx100 \\pard\\intbl a\\cell\\row \\trowd\\cellx100 \\pard\\intbl b\\cell\\row "
    )
    rtf = "{\\rtf1 " + one + "\\pard Between\\par " + one + "}"
    marked = rtf_tables.mark_header_rows(rtf)
    assert marked.count("\\trhdr") == 2
    assert rtf_tables.mark_header_rows(marked) == marked  # idempotent


def test_tables_hand_out_as_pipe_rows_and_plain_rtf_is_untouched() -> None:
    data = NATIVE_RTF.encode("latin-1")
    assert b"\\pard | {Name} | {Role} |\\par" in rtf_tables.tables_to_pipe_rows_bytes(data)
    plain = b"{\\rtf1 \\pard Hello\\par}"
    assert rtf_tables.tables_to_pipe_rows_bytes(plain) is plain


def test_non_ascii_bytes_survive_untouched() -> None:
    data = PIPE_RTF.replace("Intro", "Caf\\'e9").encode("latin-1")
    out = rtf_tables.pipe_rows_to_tables_bytes(data)
    assert b"Caf\\'e9" in out
