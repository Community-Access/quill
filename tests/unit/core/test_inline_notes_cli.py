"""``quill --notes list|check|clear``: output and exit codes are the contract."""

from __future__ import annotations

import io
import json

from quill.core.inline_notes_cli import EXIT_NOTES_LEFT, EXIT_OK, EXIT_USAGE, run
from quill.core.inline_notes_list import collect_rows, rows_as_markdown

DOC = "# Plan\n\nBack up first.\n<!-- quill-note: and the database -->\n\n- [ ] Ship\n"


def _run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    code = run(list(argv), out=out, err=io.StringIO())
    return code, out.getvalue()


def test_list_check_clear(tmp_path) -> None:
    path = tmp_path / "plan.md"
    path.write_bytes(DOC.replace("\n", "\r\n").encode("utf-8"))

    code, out = _run("list", str(path))
    assert code == EXIT_OK
    assert out == 'Note 1, line 3, on "Back up first.":\nand the database\n'

    code, out = _run("list", str(path), "--json")
    assert json.loads(out)["notes"][0] == {
        "note": "and the database",
        "line": 3,
        "on": "Back up first.",
        "orphaned": False,
        "in_file": True,
    }

    assert _run("check", str(path)) == (EXIT_NOTES_LEFT, "1 note left.\n")
    assert _run("clear", str(path)) == (EXIT_OK, "1 note removed.\n")
    assert path.read_bytes() == DOC.replace("<!-- quill-note: and the database -->\n", "").replace(
        "\n", "\r\n"
    ).encode("utf-8"), "line endings kept"
    assert _run("check", str(path)) == (EXIT_OK, "No notes left.\n")
    assert _run("list", str(path)) == (EXIT_OK, "No notes in this file.\n")


def test_errors_and_usage(tmp_path) -> None:
    assert _run("check", str(tmp_path / "missing.md"))[0] == 1
    assert _run("frobnicate", "x.md")[0] == EXIT_USAGE


def test_markdown_export_names_each_note() -> None:
    rows = collect_rows(DOC, [], "markdown")
    text = rows_as_markdown(rows, "Plan")
    assert text.startswith("# Inline notes: Plan\n\n## Note 1 (line 3)\n\n> Back up first.")
