"""``quill --notes list|check|clear FILE``: in-file notes from the command line.

The review loop PlanCake (Andre of Oire Software) built its command line for:
somebody reads an AI-written plan and leaves notes in it, then the assistant
reads the notes, works through them, and proves none are left. Only notes
written *into* the file (``<!-- quill-note: ... -->``, see
:mod:`quill.core.inline_notes_file`) are seen here; private sidecar notes stay
private by design.

Actions and exit codes, which are the contract a script relies on:

``list``  prints every note, one per paragraph, with its line and the text it
          is on (``--json`` for a machine-readable list). Exit 0.
``check`` prints how many notes are left. Exit 0 when there are none, 3 when
          there are some.
``clear`` removes every note and saves the file in its own encoding and line
          endings. Exit 0.

Any action exits 1 when the file cannot be read or written, and 2 for a usage
mistake. Output is plain text, no colour and no decoration.
"""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from quill.core.inline_notes_file import remove_all_file_notes
from quill.core.inline_notes_list import collect_rows, rows_as_json, rows_as_text
from quill.core.storage import write_bytes_atomic

__all__ = ["EXIT_ERROR", "EXIT_NOTES_LEFT", "EXIT_OK", "EXIT_USAGE", "run"]

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NOTES_LEFT = 3

_HTML_SUFFIXES = {".html", ".htm", ".xhtml"}


def _kind_for(path: Path) -> str:
    return "html" if path.suffix.lower() in _HTML_SUFFIXES else "markdown"


def _read(path: Path) -> tuple[str, str, str]:
    """``(text with LF endings, encoding, original newline)``."""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - cp1252 only fails on five undefined bytes
        text, encoding = raw.decode("latin-1"), "latin-1"
    if encoding == "utf-8-sig" and not raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8"
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), encoding, newline


def _attach_parent_console() -> None:
    """Give a windowed build (QuillLite.exe has no console) somewhere to print.

    A GUI executable starts with no standard output at all, so ``list`` would
    print into nothing. Attaching to the console that launched it -- the
    Command Prompt or PowerShell window the person typed into -- is how the
    output reaches them. Anywhere else this does nothing.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        if ctypes.windll.kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
            stream = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115 - process lifetime
            sys.stdout = stream
            sys.stderr = stream
    except Exception:  # noqa: BLE001 - no console is the same as before
        pass


def run(argv: Sequence[str], out: TextIO | None = None, err: TextIO | None = None) -> int:
    """Run one notes action; return the exit code."""
    if out is None and sys.stdout is None:
        _attach_parent_console()
    out = out if out is not None else (sys.stdout or io.StringIO())
    err = err if err is not None else (sys.stderr or io.StringIO())
    parser = argparse.ArgumentParser(
        prog="quill --notes",
        description="List, check or clear the notes written into a Markdown or HTML file.",
    )
    parser.add_argument("action", choices=("list", "check", "clear"))
    parser.add_argument("file", type=Path)
    parser.add_argument("--json", action="store_true", help="list: print JSON instead of text")
    try:
        args = parser.parse_args(list(argv))
    except SystemExit as stop:
        return EXIT_USAGE if stop.code else EXIT_OK
    path: Path = args.file
    kind = _kind_for(path)
    try:
        text, encoding, newline = _read(path)
    except OSError as error:
        print(f"Cannot read {path}: {error.strerror or error}", file=err)
        return EXIT_ERROR
    rows = collect_rows(text, [], kind)
    if args.action == "list":
        if args.json:
            out.write(rows_as_json(rows, str(path)))
        elif rows:
            out.write(rows_as_text(rows))
        else:
            print("No notes in this file.", file=out)
        return EXIT_OK
    if args.action == "check":
        count = len(rows)
        if not count:
            print("No notes left.", file=out)
            return EXIT_OK
        print(f"{count} note{'s' if count != 1 else ''} left.", file=out)
        return EXIT_NOTES_LEFT
    cleared, count = remove_all_file_notes(text, kind)
    if count:
        try:
            write_bytes_atomic(path, cleared.replace("\n", newline).encode(encoding))
        except (OSError, UnicodeEncodeError) as error:
            print(f"Cannot write {path}: {error}", file=err)
            return EXIT_ERROR
    print(f"{count} note{'s' if count != 1 else ''} removed.", file=out)
    return EXIT_OK
