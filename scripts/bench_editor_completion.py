"""Measure the three editor-completion checks of 2026-10-16 (items 37, 41, 45).

Run from a source checkout, with the worktree on ``PYTHONPATH``::

    python scripts/bench_editor_completion.py all --runs 3
    python scripts/bench_editor_completion.py open --runs 5 --json open.json
    python scripts/bench_editor_completion.py reading --megabytes 8
    python scripts/bench_editor_completion.py lists --entries 20000

Nothing here types, clicks or shows a window. The reading section builds QUILL's
real Rich Edit surface in memory (the same control the unit tests build) and
never shows it, so it is safe beside a running screen reader.

**Cold and warm.** A *cold* figure is a fresh Python process: it pays for
importing QUILL and the reader's libraries and for reading the file once, which
is what the first open after starting the app costs. A *warm* figure is a second
read in a process that has already done one -- every later open in the same
session. The first cold run also pays for the operating system loading the
libraries off disk, so the median of several runs is what is reported.

**What this does not measure.** The installed and portable builds load their
libraries from a frozen bundle rather than a source tree, so their cold numbers
differ (usually faster to import, slower on first launch after install). Run
this same script's method by hand there -- start the app, open the file, time to
the first line being read -- and record it beside the source numbers. The design
note ``docs/design/2026-10-16-editor-completion-measurements.md`` has the method
and the numbers this script produced.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))


def _median_ms(samples: list[float]) -> float:
    return round(statistics.median(samples) * 1000.0, 2)


def _time(fn: Callable[[], Any], runs: int) -> tuple[float, Any]:
    samples: list[float] = []
    result: Any = None
    for _ in range(max(1, runs)):
        start = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - start)
    return _median_ms(samples), result


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _long_markdown(megabytes: float) -> str:
    """A long Markdown book: headings every forty lines, prose between."""
    sentence = (
        "The quick brown fox reads the long chapter aloud while the listener "
        "follows along with a braille display and a cup of tea. "
    )
    target = int(megabytes * 1024 * 1024)
    parts: list[str] = []
    size = 0
    chapter = 0
    while size < target:
        chapter += 1
        block = [f"# Chapter {chapter}\n\n"]
        for section in range(1, 4):
            block.append(f"## Section {chapter}.{section}\n\n")
            for _ in range(12):
                block.append(sentence * 3 + "\n\n")
        text = "".join(block)
        parts.append(text)
        size += len(text)
    return "".join(parts)


def _write_docx(path: Path, paragraphs: int) -> None:
    import docx  # python-docx

    document = docx.Document()
    for index in range(paragraphs):
        if index % 25 == 0:
            document.add_heading(f"Heading {index // 25 + 1}", level=1)
        document.add_paragraph(
            f"Paragraph {index}: the committee met on Tuesday and agreed the "
            "budget, the timetable and who brings the biscuits next week."
        )
    document.save(str(path))


def _write_pdf(path: Path, pages: int) -> None:
    import pymupdf

    document = pymupdf.open()
    for number in range(1, pages + 1):
        page = document.new_page()
        lines = [f"Page {number}"] + [
            f"Line {line} of page {number}: plain text a reader can extract."
            for line in range(1, 40)
        ]
        page.insert_text((50, 60), "\n".join(lines), fontsize=10)
    document.save(str(path))
    document.close()


def _write_fake_doc(path: Path) -> None:
    """An OLE2 header and nothing else: enough to reach the .doc reader chain.

    A real Word 97 file cannot be written from Python without Word or
    LibreOffice, so this measures the time to the *answer* (converted, or a
    sentence saying what is missing), which is what a person waits through.
    """
    path.write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + b"\0" * 4088)


# --------------------------------------------------------------------------- #
# Item 41: opening .doc, .docx and PDF
# --------------------------------------------------------------------------- #

_COLD_OPEN = r"""
import json, sys, time
t0 = time.perf_counter()
from quill.io.open_read import read_open_document
t1 = time.perf_counter()
from pathlib import Path
p = Path(sys.argv[1])
status = "opened"
engine = ""
chars = 0
try:
    doc, _ = read_open_document(p, p.suffix.lower())
    engine = str(doc.source_metadata.get("engine", ""))
    chars = len(doc.text)
except Exception as exc:
    status = type(exc).__name__ + ": " + str(exc)[:160]
t2 = time.perf_counter()
print(json.dumps({"import_s": t1 - t0, "read_s": t2 - t1, "status": status,
                  "engine": engine, "chars": chars,
                  "markitdown_imported": "markitdown" in sys.modules}))
"""


def bench_open(runs: int, work: Path) -> dict[str, Any]:
    fixtures = {
        "docx": work / "bench.docx",
        "pdf": work / "bench.pdf",
        "doc": work / "bench.doc",
    }
    _write_docx(fixtures["docx"], 1500)
    _write_pdf(fixtures["pdf"], 60)
    _write_fake_doc(fixtures["doc"])
    # The committed Office corpus (tests/corpus/office): a workbook and a deck,
    # so the reader order is measured for every format it changes, not only Word.
    corpus = _ROOT / "tests" / "corpus" / "office"
    for name in ("budget.xlsx", "deck.pptx", "minutes.odt"):
        if (corpus / name).is_file():
            fixtures[name.rsplit(".", 1)[1]] = corpus / name
    results: dict[str, Any] = {}
    env_path = str(_ROOT)
    for kind, path in fixtures.items():
        cold_import: list[float] = []
        cold_read: list[float] = []
        last: dict[str, Any] = {}
        for _ in range(runs):
            proc = subprocess.run(
                [sys.executable, "-c", _COLD_OPEN, str(path)],
                capture_output=True,
                text=True,
                cwd=env_path,
                env={**__import__("os").environ, "PYTHONPATH": env_path},
                timeout=600,
            )
            line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
            last = json.loads(line)
            cold_import.append(float(last.get("import_s", 0.0)))
            cold_read.append(float(last.get("read_s", 0.0)))
        from quill.io.open_read import read_open_document

        def _read(p: Path = path) -> str:
            try:
                document, _ = read_open_document(p, p.suffix.lower())
            except Exception as exc:  # noqa: BLE001 - a refusal is a result here
                return type(exc).__name__
            return str(document.source_metadata.get("engine", ""))

        _read()  # the first in-process read is the cold one; warm starts after
        warm_ms, warm_engine = _time(_read, runs)
        results[kind] = {
            "bytes": path.stat().st_size,
            "cold_import_ms": _median_ms(cold_import),
            "cold_read_ms": _median_ms(cold_read),
            "warm_read_ms": warm_ms,
            "status": last.get("status", ""),
            "engine": last.get("engine", "") or warm_engine,
            "chars": last.get("chars", 0),
            "markitdown_imported": last.get("markitdown_imported", None),
        }
    results["dependencies"] = _dependency_report()
    return results


def _dependency_report() -> dict[str, str]:
    """Which optional readers are present, so slow and missing are told apart."""
    import importlib.util

    report: dict[str, str] = {}
    for module in ("markitdown", "magika", "onnxruntime", "docx", "pymupdf", "pypdf"):
        report[module] = "present" if importlib.util.find_spec(module) else "missing"
    try:
        from quill.core.external_tools import libreoffice_executable

        report["libreoffice"] = "present" if libreoffice_executable() else "missing"
    except Exception:  # noqa: BLE001
        report["libreoffice"] = "unknown"
    return report


# --------------------------------------------------------------------------- #
# Item 37: reading a long document, guarded and not
# --------------------------------------------------------------------------- #


def bench_reading(runs: int, work: Path, megabytes: float) -> dict[str, Any]:
    import wx

    from quill.core.document import Document
    from quill.core.markdown_sections import parse_heading_blocks
    from quill.io.open_read import read_open_document
    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    path = work / "long-book.md"
    text = _long_markdown(megabytes)
    path.write_text(text, encoding="utf-8", newline="\n")
    results: dict[str, Any] = {"bytes": path.stat().st_size}

    read_ms, (document, _book) = _time(lambda: read_open_document(path, ".md"), runs)
    results["read_file_ms"] = read_ms

    app = wx.App(False)
    frame = wx.Frame(None)
    editor = create_richedit_rtf(wx, frame, wx.TE_MULTILINE)

    results["set_value_ms"], _ = _time(lambda: editor.SetValue(document.text), 1)
    results["set_editable_false_ms"], _ = _time(lambda: editor.SetEditable(False), runs)
    results["get_value_ms"], value = _time(editor.GetValue, runs)
    results["text_compare_ms"], _ = _time(lambda: value == document.text, runs)
    results["heading_parse_ms"], headings = _time(
        lambda: list(parse_heading_blocks(value, "markdown")), 1
    )
    results["headings"] = len(headings)

    # One heading-navigation keypress with a warm cache, the way the browse
    # cache validates today (read the control, compare the text) and the way a
    # guarded document can (its text cannot change, so the document's own
    # string is the text and identity answers the question).
    cache = {"text": value}

    def _step_control() -> int:
        current = editor.GetValue()
        assert cache["text"] == current
        editor.SetInsertionPoint(headings[len(headings) // 2].start)
        return editor.GetInsertionPoint()

    guarded_doc = Document(text=value, path=path)
    cache_guarded = {"text": guarded_doc.text}

    def _step_guarded() -> int:
        current = guarded_doc.text
        assert cache_guarded["text"] is current
        editor.SetInsertionPoint(headings[len(headings) // 2].start)
        return editor.GetInsertionPoint()

    results["nav_step_reading_control_ms"], _ = _time(_step_control, runs * 5)
    results["nav_step_guarded_identity_ms"], _ = _time(_step_guarded, runs * 5)
    results["set_editable_true_ms"], _ = _time(lambda: editor.SetEditable(True), runs)
    frame.Destroy()
    app.Destroy()
    return results


# --------------------------------------------------------------------------- #
# Item 45: large snippet and abbreviation libraries
# --------------------------------------------------------------------------- #

_COLD_LISTS = r"""
import json, sys, time
from pathlib import Path
t0 = time.perf_counter()
from quill.core.snippets import load_snippet_library, search_snippets
t1 = time.perf_counter()
library = load_snippet_library(Path(sys.argv[1]))
t2 = time.perf_counter()
search_snippets(library.snippets, "")
t3 = time.perf_counter()
print(json.dumps({"import_s": t1 - t0, "load_s": t2 - t1, "first_list_s": t3 - t2,
                  "count": len(library.snippets)}))
"""


def _snippet_payload(entries: int) -> dict[str, Any]:
    words = ["meeting", "notes", "invoice", "reply", "thanks", "agenda", "address", "signature"]
    snippets = []
    for index in range(entries):
        first = words[index % len(words)]
        second = words[(index // len(words)) % len(words)]
        snippets.append({
            "id": f"s{index}",
            "name": f"{first.title()} {second} {index}",
            "trigger": f";{first[:3]}{index}",
            "body": f"Dear colleague, about the {first} and the {second}. " * 6,
            "description": f"A {first} about {second}",
            "tags": [first, second],
        })
    return {"version": 1, "snippets": snippets}


def bench_lists(runs: int, work: Path, entries: int) -> dict[str, Any]:
    from quill.core.snippets import load_snippet_library, search_snippets

    path = work / "snippets.json"
    path.write_text(json.dumps(_snippet_payload(entries)), encoding="utf-8")
    results: dict[str, Any] = {"entries": entries, "bytes": path.stat().st_size}

    cold: list[dict[str, Any]] = []
    for _ in range(runs):
        proc = subprocess.run(
            [sys.executable, "-c", _COLD_LISTS, str(path)],
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(_ROOT)},
            timeout=600,
        )
        cold.append(json.loads((proc.stdout.strip().splitlines() or ["{}"])[-1]))
    results["cold_import_ms"] = _median_ms([float(c.get("import_s", 0)) for c in cold])
    results["cold_load_ms"] = _median_ms([float(c.get("load_s", 0)) for c in cold])
    results["cold_first_list_ms"] = _median_ms([float(c.get("first_list_s", 0)) for c in cold])

    results["warm_load_ms"], library = _time(lambda: load_snippet_library(path), runs)
    snippets = library.snippets
    # One keystroke of incremental filtering: each prefix of a two-word name.
    query = "meeting notes"
    per_key: list[float] = []
    for end in range(1, len(query) + 1):
        ms, _ = _time(lambda q=query[:end]: search_snippets(snippets, q), runs)
        per_key.append(ms)
    results["filter_per_key_median_ms"] = round(statistics.median(per_key), 2)
    results["filter_per_key_max_ms"] = round(max(per_key), 2)
    results["matches_meeting_notes"] = len(search_snippets(snippets, "meeting notes"))
    results["matches_notes_meeting"] = len(search_snippets(snippets, "notes meeting"))
    results.update(_bench_list_controls(runs, [s.name for s in snippets]))
    results.update(_bench_abbreviations(runs, work, entries))
    return results


def _bench_list_controls(runs: int, labels: list[str]) -> dict[str, Any]:
    """Refilling the on-screen list, which is what every keystroke also pays.

    The ListBox is the searchable picker's (Insert Snippet and its siblings);
    the ListCtrl is the Abbreviations manager's four-column report list.
    """
    import wx

    app = wx.App(False)
    frame = wx.Frame(None)
    listbox = wx.ListBox(frame)
    report = wx.ListCtrl(frame, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    for column, title in enumerate(("Abbreviation", "Expansion", "On", "Category")):
        report.InsertColumn(column, title)
    out: dict[str, Any] = {}
    out["listbox_fill_all_ms"], _ = _time(lambda: listbox.Set(labels), runs)
    out["listbox_fill_tenth_ms"], _ = _time(lambda: listbox.Set(labels[::10]), runs)

    def _fill_report(rows: list[str]) -> None:
        report.DeleteAllItems()
        for index, label in enumerate(rows):
            report.InsertItem(index, label)
            report.SetItem(index, 1, label)
            report.SetItem(index, 2, "Y")
            report.SetItem(index, 3, "General")

    def _fill_report_frozen(rows: list[str]) -> None:
        report.Freeze()
        try:
            _fill_report(rows)
        finally:
            report.Thaw()

    out["listctrl_fill_all_ms"], _ = _time(lambda: _fill_report(labels), runs)
    out["listctrl_fill_all_frozen_ms"], _ = _time(lambda: _fill_report_frozen(labels), runs)

    # After (2026-10-16): the picker fills at most SHOWN_LIMIT rows, and the
    # Abbreviations manager is a virtual list that is only told a row count.
    from quill.ui.searchable_picker import SHOWN_LIMIT
    from quill.ui.virtual_report_list import VirtualReportList

    out["picker_fill_capped_ms"], _ = _time(lambda: listbox.Set(labels[:SHOWN_LIMIT]), runs)
    virtual = VirtualReportList(frame, [("Abbreviation", 120)], lambda row, _col: labels[row])
    out["virtual_list_fill_all_ms"], _ = _time(
        lambda: virtual.show_rows(len(labels), select=0), runs
    )
    frame.Destroy()
    app.Destroy()
    return out


def _bench_abbreviations(runs: int, work: Path, entries: int) -> dict[str, Any]:
    from quill.core.abbreviations import load_abbreviation_library

    folder = work / "abbr"
    folder.mkdir(exist_ok=True)
    rows = [
        {
            "id": f"a{index}",
            "abbreviation": f"abbr{index}",
            "expansion": f"Expansion number {index} for the meeting notes",
            "category": "General" if index % 2 else "Work",
        }
        for index in range(entries)
    ]
    (folder / "abbreviations.json").write_text(
        json.dumps({"version": 2, "abbreviations": rows}), encoding="utf-8"
    )
    out: dict[str, Any] = {}
    out["abbreviations_load_ms"], library = _time(lambda: load_abbreviation_library(folder), runs)
    out["abbreviations_loaded"] = len(library.abbreviations)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("section", choices=["open", "reading", "lists", "all"])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--megabytes", type=float, default=8.0)
    parser.add_argument("--entries", type=int, default=10000)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    report: dict[str, Any] = {"python": sys.version.split()[0], "platform": sys.platform}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if args.section in {"open", "all"}:
            report["open"] = bench_open(args.runs, work)
        if args.section in {"reading", "all"}:
            report["reading"] = bench_reading(args.runs, work, args.megabytes)
        if args.section in {"lists", "all"}:
            report["lists"] = bench_lists(args.runs, work, args.entries)
    text = json.dumps(report, indent=2)
    print(text)
    if args.json is not None:
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
